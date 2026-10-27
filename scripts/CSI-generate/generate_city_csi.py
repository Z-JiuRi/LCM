#!/usr/bin/env python3
"""Static outdoor CSI: RT paths -> raw CFR -> serving-sector feedback samples.

Project implementation, not an official DeepMIMO script.

Default scientific contract: physical baseband CIR from
paths.cir(normalize_delays=False), centered frequency offsets, unit scale,
and no absolute-delay clipping. H(nu) = sum_p a_BB[p] exp(-j2*pi*nu*tau[p]).
Learning timing alignment / RMS normalization is a separate reversible step.

Coefficient semantics, frequency grid, scale and delay window are independent.
Raw-passband compatibility remains explicit; it is NOT claimed to reproduce
an entire official DeepMIMO converter. Raw paths.a is retained in every batch.
Source-informed propagation is a documented cross-backend model, not a claim
of equivalence to InSite or of converged ray search.

No path is evidence of no path FOUND under this configuration, not proof of
physical blockage. Fixed samples_per_src is NEVER multiplied by RX batch size.
Run --dry-run first. Existing output directories are refused; raw data retained.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import sys
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, wait, FIRST_COMPLETED
from contextlib import ExitStack
import shutil
import warnings
import inspect

# Set before NumPy/Sionna import; workers use spawn (not fork accelerator state).
for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ.setdefault(key, '1')
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GEOMETRY = ROOT/'data/csi/city-1km-geometry'
DEFAULT_DEPLOYMENT = ROOT/'data/cities/city-1km/bs-deployment.json'


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024*1024), b''): h.update(part)
    return h.hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def _save_path_batch(path, raw, compression):
    start = time.perf_counter()
    save = np.savez_compressed if compression == 'compressed' else np.savez
    save(path, **raw)
    written = time.perf_counter()
    digest = sha256(path)
    return dict(sha256=digest, write_seconds=written-start,
                hash_seconds=time.perf_counter()-written)


def parse_cpu_set(spec):
    cpus=set()
    try:
        for part in spec.split(','):
            ends=part.split('-')
            if len(ends)==1:cpus.add(int(ends[0]))
            elif len(ends)==2:
                first,last=map(int,ends)
                if last<first:raise ValueError('reversed CPU range')
                cpus.update(range(first,last+1))
            else:raise ValueError('invalid CPU range')
    except (ValueError,TypeError) as exc:
        raise ValueError(f'Invalid CPU set: {spec}') from exc
    if not cpus or min(cpus)<0:raise ValueError('CPU set must be nonnegative and nonempty')
    return cpus


def _init_worker(device, cpu_set=None):
    # Spawn imports CPU NumPy first; all accelerator imports occur later.
    if device is not None:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(device)
    if cpu_set is not None:
        cpus=parse_cpu_set(cpu_set)
        if not hasattr(os,'sched_setaffinity') or not cpus.issubset(os.sched_getaffinity(0)):
            raise ValueError('Requested CPU set exceeds the process allocation')
        os.sched_setaffinity(0,cpus)


def selected_devices(tokens):
    """Explicit selection must stay inside the scheduler's inherited allocation."""
    if tokens is None:
        return None
    if not tokens or len(set(tokens)) != len(tokens) or any(not str(t).strip() for t in tokens):
        raise ValueError('GPU identifiers must be nonempty and unique')
    inherited = os.environ.get('CUDA_VISIBLE_DEVICES')
    if inherited is not None:
        allowed = [x.strip() for x in inherited.split(',') if x.strip()]
        if any(token not in allowed for token in tokens):
            raise ValueError('GPU selection must use identifiers already in CUDA_VISIBLE_DEVICES; use UUIDs consistently')
    return tokens


def run_sector_tasks(tasks, workers, devices=None):
    """Dynamically feed one sector at a time to each pinned, persistent process."""
    if not tasks:
        return []
    if devices is None:
        if workers == 1:
            return [_worker(task) for task in tasks]
        with ProcessPoolExecutor(max_workers=min(workers,len(tasks)),
                                 mp_context=mp.get_context('spawn')) as pool:
            return list(pool.map(_worker, tasks, chunksize=1))
    results = []
    pending_tasks = iter(tasks)
    cpu_sets=tasks[0].get('config',{}).get('cpu_sets') or [None]*len(devices)
    with ExitStack() as stack:
        executors = [stack.enter_context(ProcessPoolExecutor(
            max_workers=1, mp_context=mp.get_context('spawn'),
            initializer=_init_worker, initargs=(device,cpu_sets[index])))
            for index,device in enumerate(devices[:len(tasks)])]
        inflight = {executor.submit(_worker, next(pending_tasks)): executor for executor in executors}
        try:
            while inflight:
                done, _ = wait(inflight, return_when=FIRST_COMPLETED)
                for future in done:
                    executor = inflight.pop(future)
                    results.append(future.result())
                    task = next(pending_tasks, None)
                    if task is not None:
                        inflight[executor.submit(_worker, task)] = executor
        except BaseException:
            for future in inflight:
                future.cancel()
            raise
    return results


def storage_estimate(n_ues, n_sectors, n_antennas, n_sc):
    per_link = n_antennas*n_sc*np.dtype(np.complex64).itemsize
    sectors = n_ues*n_sectors*per_link
    # Serving CSI + all-UE real/imag parcel arrays. Paths are unknown a priori.
    total = sectors + 2*n_ues*per_link + 2*n_ues*n_sectors*8 + n_ues*256
    return dict(sector_cfr_bytes=sectors, known_output_estimate_bytes=total,
                raw_path_bytes='unknown; can greatly exceed this estimate')


def require_disk_space(output, required, reserve_gib):
    parent = output
    while not parent.exists():
        parent = parent.parent
    free = shutil.disk_usage(parent).free
    if free < required + reserve_gib*2**30:
        raise ValueError(f'Insufficient output space: free={free/2**30:.1f} GiB, '
                         f'known outputs~{required/2**30:.1f} GiB plus reserve={reserve_gib:g} GiB; '
                         'raw path storage is additional')
    return free


def frequency_plan(bandwidth=20e6, n_fft=1024, n_sc=64, convention='deepmimo'):
    if not math.isfinite(bandwidth) or bandwidth <= 0 or n_fft < 1 or n_sc < 1 or n_fft % n_sc:
        raise ValueError('Positive bandwidth, FFT and selected count required; FFT must be divisible by selected count')
    bins = np.arange(0, n_fft, n_fft//n_sc, dtype=np.int32)
    offsets = bins.astype(np.float64)
    if convention == 'centered': offsets -= n_fft//2
    elif convention != 'deepmimo': raise ValueError('Unknown frequency convention')
    return bins, offsets*(bandwidth/n_fft)


def path_statistics(a, tau, valid, significant_db=25.):
    """a=[UE,RX,TX_ant,path], tau/valid=[UE,path]. No padded-path energy."""
    if a.ndim != 4 or tau.shape != valid.shape or a.shape[0] != len(tau) or a.shape[-1] != tau.shape[1]:
        raise ValueError('Inconsistent CIR/path shapes')
    if not np.isfinite(a).all() or np.any(valid & (~np.isfinite(tau) | (tau < 0))):
        raise ValueError('Nonfinite coefficients or invalid physical delays')
    # Keep the complex128 reference accumulation without promoting the entire
    # antenna-by-path tensor at once (large diffuse batches can be enormous).
    powers = np.empty(tau.shape, dtype=np.float64)
    for start in range(0, a.shape[-1], 128):
        values = a[..., start:start+128].astype(np.complex128)
        powers[:, start:start+128] = np.mean(np.abs(values)**2, axis=(1, 2))
    powers = np.where(valid, powers, 0.)
    nonzero = valid & (powers > 0)
    strongest = powers.max(axis=1, initial=0.)
    significant = nonzero & (powers >= strongest[:, None]*10**(-significant_db/10))
    refs = np.min(np.where(significant, tau, np.inf), axis=1, initial=np.inf)
    refs = np.where(np.isfinite(refs), refs, np.nan)
    return powers.sum(axis=1), refs, valid.sum(axis=1).astype(np.int32)


def synthesize_cfr(a, tau, valid, frequencies, n_fft=1024, bandwidth=20e6, convention='deepmimo',
                   normalization=None, delay_window=None):
    """Synthesize supplied antenna-resolved coefficients with explicit scale/window.

    No top-K truncation. Legacy Python callers omitting normalization/window
    inherit old convention behavior; CLI passes all independent options.
    Accumulate in complex128 then cast once to complex64.
    """
    if a.ndim != 4 or tau.shape != valid.shape or a.shape[-1] != tau.shape[-1]:
        raise ValueError('Inconsistent synthesis shapes')
    if convention not in ('deepmimo','centered'):raise ValueError('Unknown synthesis convention')
    # None supports legacy Python callers only. CLI always passes both explicitly.
    normalization=normalization or ('ofdm' if convention=='deepmimo' else 'unit')
    delay_window=delay_window or ('fft' if convention=='deepmimo' else 'none')
    if normalization not in ('unit','ofdm') or delay_window not in ('none','fft'):
        raise ValueError('Unknown scale/window contract')
    keep = valid.copy()
    dropped = np.zeros(len(tau), dtype=np.int32)
    if delay_window == 'fft':
        over = valid & (tau >= n_fft/bandwidth)
        dropped = over.sum(axis=1).astype(np.int32); keep &= ~over
    scale = 1/math.sqrt(n_fft) if normalization=='ofdm' else 1.
    output = np.zeros((*a.shape[:3], len(frequencies)), dtype=np.complex128)
    # Bound the phase intermediate even when diffuse paths are numerous.
    for start in range(0, a.shape[-1], 128):
        stop = start+128
        delays = np.where(keep[:, start:stop], tau[:, start:stop], 0.)
        response = np.exp(-2j*np.pi*delays[..., None]*np.asarray(frequencies))
        coefficients = np.where(keep[:, None, None, start:stop], a[..., start:stop], 0.)
        output += np.einsum('urmp,upk->urmk', coefficients, response, optimize=True)*scale
    if not np.isfinite(output).all(): raise ValueError('Nonfinite synthesized CSI')
    return output.astype(np.complex64), dropped


def extract_coefficients(paths, mode='physical-baseband'):
    """Synthetic-array, one-TX layout. Invalid padded paths stay masked."""
    raw=np.asarray(paths.a[0])+1j*np.asarray(paths.a[1])
    tau=np.asarray(paths.tau,dtype=np.float64)
    valid=np.asarray(paths.valid,dtype=bool)
    if raw.ndim!=5 or raw.shape[2]!=1 or tau.ndim!=3 or tau.shape[1]!=1:
        raise ValueError('Expected synthetic-array one-TX path layout')
    raw=raw[:,:,0,:,:];tau=tau[:,0,:];valid=valid[:,0,:]
    if mode=='raw-passband':return raw,raw,tau,valid
    if mode!='physical-baseband':raise ValueError('Unknown coefficient mode')
    cir,delays=paths.cir(normalize_delays=False,num_time_steps=1,out_type='numpy')
    cir=np.asarray(cir);delays=np.asarray(delays,dtype=np.float64)
    if cir.shape!=(*raw.shape[:2],1,*raw.shape[2:],1):
        raise ValueError(f'Unexpected CIR shape: {cir.shape}')
    if delays.shape!=(tau.shape[0],1,tau.shape[1]) or not np.array_equal(delays[:,0,:],tau):
        raise ValueError('CIR unexpectedly altered absolute propagation delays')
    return raw,cir[:,:,0,:,:,0],tau,valid


def compare_native_cfr(paths, cfr, frequencies, normalization, n_fft):
    """Opt-in limited diagnostic; requires no artificial delay window."""
    native=np.asarray(paths.cfr(frequencies=frequencies,normalize_delays=False,
                               normalize=False,out_type='numpy'))[:,:,0,:,0,:]
    if normalization=='ofdm':native=native/math.sqrt(n_fft)
    error=np.sum(np.abs(cfr.astype(np.complex128)-native)**2,dtype=np.float64)
    energy=np.sum(np.abs(native.astype(np.complex128))**2,dtype=np.float64)
    nmse=float(error/energy) if energy>0 else (0. if error==0 else None)
    return dict(relative_squared_error=nmse,max_absolute_error=float(np.max(abs(cfr-native),initial=0.)),
                reference='Sionna Paths.cfr normalize_delays=False normalize=False; not independent RT')


def path_diagnostics(a,tau,valid,interactions,cap):
    powers=np.empty(tau.shape,np.float64)
    for start in range(0,a.shape[-1],128):
        powers[:,start:start+128]=np.mean(abs(a[...,start:start+128].astype(np.complex128))**2,axis=(1,2))
    powers=np.where(valid,powers,0.)
    total=powers.sum(axis=1)
    mean=np.sum(powers*np.where(valid,tau,0.),axis=1)/np.where(total>0,total,1.)
    spread=np.sqrt(np.sum(powers*(np.where(valid,tau,mean[:,None])-mean[:,None])**2,axis=1)/np.where(total>0,total,1.))
    present=total>0
    # Native layout [depth,U,TX,P]. Count physical nonzero events on valid
    # paths only; padding/NONE is not evidence of a propagation interaction.
    if interactions.ndim==4 and interactions.shape[1:]==(len(valid),1,valid.shape[-1]):
        events=interactions[:, :, 0, :][np.broadcast_to(valid,(interactions.shape[0],*valid.shape))]
    else:
        events=np.empty(0,dtype=np.uint32)  # Non-native mocks/unknown layouts explicitly uncounted.
    values,counts=np.unique(events[events!=0],return_counts=True)
    return dict(returned_valid_paths=int(valid.sum()),max_paths_per_ue=int(valid.sum(axis=1).max(initial=0)),
                returned_to_source_cap_ratio=float(valid.sum()/cap),
                candidate_saturation='unknown: final valid paths do not expose discarded candidate occupancy',
                interaction_code_counts={str(int(k)):int(v) for k,v in zip(values,counts)},
                mean_rms_delay_spread_s=float(np.mean(spread[present])) if present.any() else None,
                no_path_ues=int((~valid.any(axis=1)).sum()))


def align_and_normalize(H, tau_ref, frequencies):
    """H=[UE,TX_ant,freq]; inverse requires retained tau_ref and RMS."""
    if H.ndim != 3 or len(H) != len(tau_ref) or not np.isfinite(tau_ref).all():
        raise ValueError('Invalid CSI or reference delays')
    corrected = H*np.exp(2j*np.pi*np.asarray(tau_ref)[:, None, None]*np.asarray(frequencies))
    rms = np.sqrt(np.mean(np.abs(corrected)**2, axis=(1, 2), dtype=np.float64))
    if not np.isfinite(rms).all() or np.any(rms <= 0): raise ValueError('Zero/nonfinite CSI cannot be normalized')
    return (corrected/rms[:, None, None]).astype(np.complex64), rms


def solver_options(config, sector_index):
    """One fixed source budget for EVERY batch, including the final short one."""
    return dict(samples_per_src=config['samples_per_src'], max_depth=config['max_depth'],
                max_num_paths_per_src=config['max_num_paths_per_src'], los=True,
                specular_reflection=True, diffuse_reflection=config['diffuse_reflection'],
                diffraction=config['diffraction'], edge_diffraction=config['edge_diffraction'],
                diffraction_lit_region=True, refraction=config['refraction'],
                synthetic_array=True, seed=config['seed']+sector_index)


def build_scene(geometry, manifest, config):
    import mitsuba as mi
    mi.set_variant(config['variant'])
    import sionna.rt as rt
    scene = rt.Scene(); by_key = {m['key']: m for m in manifest['materials']}
    objects = []
    for index, group in enumerate(manifest['groups']):
        m = by_key[group['material_key']]
        # A unique material name per mesh avoids registration collisions.
        kwargs = dict(m.get('scattering_kwargs', {}))
        material = rt.RadioMaterial(name=f'material_{index}', relative_permittivity=float(m['permittivity']),
                    conductivity=float(m['conductivity']), thickness=float(m['thickness']),
                    scattering_coefficient=(0. if group.get('role')=='terrain' and config.get('terrain_scattering','off')=='off'
                                            else float(m['scattering_coefficient'])),
                    xpd_coefficient=float(m['xpd_coefficient']), scattering_pattern=m['scattering_pattern'], **kwargs)
        # Sionna's filename helper defaults flip_normals=True. Load explicitly
        # to retain exported winding/shared indices and avoid global welding.
        mesh=mi.load_dict({'type':'obj','filename':str(geometry/group['obj']),
                           'face_normals':True,'flip_normals':False})
        objects.append(rt.SceneObject(name=f'mesh_{index}', mi_mesh=mesh,
                                      radio_material=material,remove_duplicate_vertices=False))
    scene.add(objects); scene.frequency=config['carrier_hz']; scene.bandwidth=config['bandwidth_hz']
    scene.tx_array=rt.PlanarArray(num_rows=1, num_cols=config['num_antennas'], horizontal_spacing=.5,
                                vertical_spacing=.5, pattern=config['tx_pattern'], polarization='V')
    scene.rx_array=rt.PlanarArray(num_rows=1, num_cols=1, pattern='iso', polarization='V')
    return scene


# Process-local only: never pickle or share a scene between accelerator workers.
_SCENE_CACHE = None


def _worker(task):
    """Process one sector sequentially using this pinned process's static scene."""
    global _SCENE_CACHE
    start_time=time.perf_counter()
    timings={key:0. for key in ('rtsetup','solve','transfer','stats','synthesis','write','hash')}
    config=task['config']; geometry=Path(task['geometry']).resolve()
    output=Path(task['output']); sector=task['sector']
    flush_batches=config.get('flush_batches',8)
    if flush_batches < 1:raise ValueError('flush_batches must be positive')
    compression=config.get('raw_compression','compressed')
    if compression not in ('compressed','stored'):raise ValueError('Invalid raw compression')
    scene=None; H=None; writer=None; pending=None; batches=[]

    def record_write(saved,record):
        if isinstance(saved,dict):
            record['sha256']=saved['sha256']
            timings['write']+=saved.get('write_seconds',0.)
            timings['hash']+=saved.get('hash_seconds',0.)
        else:record['sha256']=saved
        batches.append(record)

    def finish_write():
        nonlocal pending
        if pending is None:return
        future,record=pending
        record_write(future.result(),record)
        pending=None

    try:
        setup_start=time.perf_counter()
        # The spawn initializer must bind GPU visibility before these imports.
        import mitsuba as mi
        if mi.variant() is None:mi.set_variant(config['variant'])
        elif mi.variant()!=config['variant']:
            raise RuntimeError('Worker Mitsuba variant differs from requested variant')
        import sionna.rt as rt
        init_signature=inspect.signature(rt.PathSolver.__init__)
        if 'deterministic' not in init_signature.parameters and not any(
                p.kind==inspect.Parameter.VAR_KEYWORD for p in init_signature.parameters.values()):
            raise RuntimeError(f'Sionna RT {rt.__version__} lacks deterministic PathSolver support; '
                               'prepare the matching tested RT environment rather than silently changing reproducibility')
        signature=inspect.signature(rt.PathSolver.__call__)
        if not any(p.kind==inspect.Parameter.VAR_KEYWORD for p in signature.parameters.values()):
            unsupported=set(solver_options(config,task['index']))-set(signature.parameters)
            if unsupported:
                raise RuntimeError(f'Sionna RT {rt.__version__} lacks required solver parameters {sorted(unsupported)}; '
                                   'use a matching tested environment, never silently drop physics flags')
        manifest_text=(geometry/'geometry-manifest.json').read_text()
        manifest=json.loads(manifest_text)
        scene_config={key:config.get(key) for key in ('variant','carrier_hz','bandwidth_hz','num_antennas','tx_pattern','terrain_scattering')}
        cache_key=(str(geometry),manifest_text,json.dumps(scene_config,sort_keys=True))
        cache_hit=_SCENE_CACHE is not None and _SCENE_CACHE['key']==cache_key
        if not cache_hit:
            _SCENE_CACHE=None
            scene=build_scene(geometry,manifest,config)
            _SCENE_CACHE={'key':cache_key,'scene':scene}
        else:scene=_SCENE_CACHE['scene']
        if scene.transmitters or scene.receivers:
            raise RuntimeError('Cached worker scene contains stale radio devices')
        positions=np.load(output/'ue_positions.npy',mmap_mode='r',allow_pickle=False)
        folder=output/'raw'/f"sector-{task['index']:03d}"; folder.mkdir(parents=True,exist_ok=False)
        orientation=[math.radians(float(sector['azimuth_deg'])),math.radians(float(sector['downtilt_deg'])),0.]
        # The outer finally also covers partial device-add failures.
        scene.add(rt.Transmitter('tx',list(map(float,sector['position_m'])),orientation=orientation,power_dbm=config['tx_power_dbm']))
        solver=rt.PathSolver(deterministic=True); options=solver_options(config,task['index'])
        _,frequencies=frequency_plan(config['bandwidth_hz'],config['n_fft'],config['n_sc'],config['convention'])
        H=np.lib.format.open_memmap(folder/'csi.npy',mode='w+',dtype=np.complex64,
                                    shape=(len(positions),1,config['num_antennas'],config['n_sc']))
        gain=np.zeros(len(positions)); reference=np.full(len(positions),np.nan)
        counts=np.zeros(len(positions),np.int32); clipped=np.zeros(len(positions),np.int32)
        if config.get('async_write',False):writer=ThreadPoolExecutor(max_workers=1)
        timings['rtsetup']+=time.perf_counter()-setup_start
        for batch_index,start in enumerate(range(0,len(positions),config['chunk'])):
            stop=min(start+config['chunk'],len(positions)); names=[f'rx_{i}' for i in range(start,stop)]
            try:
                scene.add([rt.Receiver(name,list(map(float,pos))) for name,pos in zip(names,positions[start:stop])])
                tick=time.perf_counter(); paths=solver(scene,**options)
                timings['solve']+=time.perf_counter()-tick
                tick=time.perf_counter()
                raw_a,a,tau,valid=extract_coefficients(paths,config.get('coefficient_mode','raw-passband'))
                timings['transfer']+=time.perf_counter()-tick
                tick=time.perf_counter()
                gain[start:stop],reference[start:stop],counts[start:stop]=path_statistics(a,tau,valid,config['significant_db'])
                timings['stats']+=time.perf_counter()-tick
                tick=time.perf_counter()
                cfr,clipped[start:stop]=synthesize_cfr(a,tau,valid,frequencies,config['n_fft'],config['bandwidth_hz'],config['convention'],
                                                     config.get('normalization'),config.get('delay_window'))
                native_check=None
                if config.get('check_native_cfr',False):
                    native_check=compare_native_cfr(paths,cfr,frequencies,config['normalization'],config['n_fft'])
                    if native_check['relative_squared_error'] is None or native_check['relative_squared_error']>config['native_cfr_nmse_tolerance']:
                        raise ValueError(f'Native CFR numerical check failed: {native_check}')
                timings['synthesis']+=time.perf_counter()-tick
                tick=time.perf_counter(); H[start:stop]=cfr
                timings['write']+=time.perf_counter()-tick
                # Wait BEFORE constructing another raw dictionary: a single
                # writer can own at most one raw batch, never an unbounded queue.
                finish_write()
                tick=time.perf_counter()
                raw=dict(ue_indices=np.arange(start,stop),passband_coefficients=raw_a.astype(np.complex64),
                          channel_coefficients=a.astype(np.complex64),coefficient_mode=np.array(config.get('coefficient_mode','raw-passband')),
                         path_delays_s=tau.copy(),path_valid=valid.copy(),
                         theta_t_rad=np.array(paths.theta_t,copy=True),phi_t_rad=np.array(paths.phi_t,copy=True),
                         theta_r_rad=np.array(paths.theta_r,copy=True),phi_r_rad=np.array(paths.phi_r,copy=True),
                         interactions=np.array(paths.interactions,copy=True),vertices_m=np.array(paths.vertices,copy=True))
                timings['transfer']+=time.perf_counter()-tick
                filename=f'paths-{start:07d}-{stop:07d}.npz'
                record=dict(file=filename,start=start,stop=stop,path_slots=valid.shape[-1],
                            diagnostics=path_diagnostics(a,tau,valid,raw['interactions'],config['max_num_paths_per_src']),
                            native_cfr_check=native_check)
                if writer is None:record_write(_save_path_batch(folder/filename,raw,compression),record)
                else:pending=(writer.submit(_save_path_batch,folder/filename,raw,compression),record)
                if (batch_index+1)%flush_batches==0:
                    tick=time.perf_counter(); H.flush(); timings['write']+=time.perf_counter()-tick
                print(f"[{sector['id']}] {stop}/{len(positions)} RX; paths={int(valid.sum())}",flush=True)
                del paths,raw_a,a,tau,valid,cfr,raw
            finally:
                # A failed list add can leave a prefix registered in the scene.
                scene.remove(names)
        finish_write()
        if writer is not None:writer.shutdown(wait=True); writer=None
        tick=time.perf_counter(); H.flush(); del H; H=None
        np.savez(folder/'link_stats.npz',path_gain_linear=gain,tau_ref_s=reference,path_counts=counts,delay_window_clipped=clipped,
                 no_path_found=counts==0)
        timings['write']+=time.perf_counter()-tick
        tick=time.perf_counter(); csi_digest=sha256(folder/'csi.npy')
        timings['hash']+=time.perf_counter()-tick
        timings['total']=time.perf_counter()-start_time
        summary=dict(sector=sector,solver_options=options,orientation_rad=orientation,config=config,batches=batches,
                     versions={'sionna_rt':rt.__version__,'mitsuba':mi.__version__},seconds=timings['total'],timings=timings,
                     timing_note='Host wall times; async write overlaps compute, lazy device work may be charged to transfer. Total excludes metadata JSON and cleanup.',
                     execution={'pid':os.getpid(),'cuda_visible_devices':os.environ.get('CUDA_VISIBLE_DEVICES'),
                                'variant':mi.variant(),'scene_cache_hit':cache_hit,
                                 'cpu_affinity':sorted(os.sched_getaffinity(0)) if hasattr(os,'sched_getaffinity') else None},
                     csi_axes=['ue','rx_ant','tx_ant','frequency'],csi_sha256=csi_digest)
        write_json(folder/'metadata.json',summary)
        return dict(index=task['index'],folder=str(folder),sector=sector,seconds=summary['seconds'],timings=timings,
                    execution=summary['execution'])
    except BaseException:
        _SCENE_CACHE=None  # Never reuse potentially damaged accelerator state.
        raise
    finally:
        try:
            if writer is not None:writer.shutdown(wait=True)
        finally:
            try:
                if H is not None:H.flush()
            finally:
                if scene is not None:
                    try:
                        scene.remove(list(scene.receivers)); scene.remove('tx')
                    except BaseException:
                        _SCENE_CACHE=None
                        raise


def export_feedback(output, results, positions, config):
    """Associate by sum of antenna-averaged linear PATH power, not sum|H|.

    Equal TX powers by default; otherwise scores include TX power. No coherent
    precoding gain or load/interference-aware association is claimed.
    """
    n=len(positions); export_chunk=config.get('export_chunk',128)
    if export_chunk < 1:raise ValueError('export_chunk must be positive')
    # Retain every actual score on disk without an in-RAM sector-by-UE table.
    scores=np.lib.format.open_memmap(output/'sector_scores.npy',mode='w+',dtype=np.float64,
                                    shape=(len(results),n))
    best=np.zeros(n); owner=np.full(n,-1,dtype=np.int64); found_any=np.zeros(n,dtype=bool)
    refs=np.full(n,np.nan); rms=np.full(n,np.nan); cfr_energy=np.zeros(n); counts=np.zeros(n,np.int32)
    clipped=np.zeros(n,np.int32); raw_selected=np.zeros(n,np.float64)
    tx_power=10**((config['tx_power_dbm']-30)/10)
    for row,result in enumerate(results):
        with np.load(Path(result['folder'])/'link_stats.npz',allow_pickle=False) as z:
            gain=z['path_gain_linear']; sector_counts=z['path_counts']
            np.multiply(gain,tx_power,out=scores[row])
            found_any |= sector_counts>0
            # Strict improvement preserves argmax's first-sector tie rule;
            # zero-power links never acquire an owner or selected statistics.
            better=scores[row]>best
            np.copyto(best,scores[row],where=better); owner[better]=row
            np.copyto(refs,z['tau_ref_s'],where=better)
            np.copyto(counts,sector_counts,where=better)
            np.copyto(clipped,z['delay_window_clipped'],where=better)
            np.copyto(raw_selected,gain,where=better)
            del gain,sector_counts,better
    scores.flush()
    active=best>0
    del best
    assignment_path=output/'ue_parcel_index.npy'
    catalog_path=output/'parcel-catalog.json'
    if not assignment_path.is_file() or not catalog_path.is_file():
        raise ValueError('Actual parcel membership is required before feedback export')
    labels=np.load(assignment_path,allow_pickle=False)
    parcel_catalog=json.loads(catalog_path.read_text())
    if labels.shape!=(n,) or labels.dtype.kind not in 'iu':raise ValueError('Parcel membership length/type mismatch')
    expected_groups=list(range(len(parcel_catalog['groups'])))
    if [item['group_index'] for item in parcel_catalog['groups']]!=expected_groups or np.any(labels<0) or np.any(labels>=len(expected_groups)):
        raise ValueError('Invalid parcel group indices; refusing to drop unassigned UE rows')
    for item in parcel_catalog['groups']:
        folder=Path(item['directory'])
        if folder.name!=str(folder) or str(folder) in ('.','..'):raise ValueError('Invalid parcel directory')
    # Disk backed: no multi-sector full CSI tensor in parent RAM.
    serving=np.lib.format.open_memmap(output/'serving_csi.npy', mode='w+',dtype=np.complex64,
                                    shape=(n,1,config['num_antennas'],config['n_sc']))
    serving[:]=0
    for row,result in enumerate(results):
        idx=np.flatnonzero(owner==row)
        if not len(idx):continue
        source=np.load(Path(result['folder'])/'csi.npy',mmap_mode='r',allow_pickle=False)
        for start in range(0,len(idx),export_chunk):
            batch=idx[start:start+export_chunk]; values=np.asarray(source[batch])
            serving[batch]=values; cfr_energy[batch]=np.mean(np.abs(values.astype(np.complex128))**2,axis=(1,2,3))
        del source,values
    serving.flush()
    usable=active & np.isfinite(refs) & (cfr_energy>0)
    _,frequencies=frequency_plan(config['bandwidth_hz'],config['n_fft'],config['n_sc'],config['convention'])
    groups={}
    parcels_dir=output/'parcels';parcels_dir.mkdir(exist_ok=False)
    source_indices=np.load(output/'source_ue_indices.npy',allow_pickle=False) if (output/'source_ue_indices.npy').is_file() else np.arange(n)
    for item in parcel_catalog['groups']:
        label=item['group_index'];idx=np.flatnonzero(labels==label)
        folder=parcels_dir/item['directory'];folder.mkdir(exist_ok=False)
        target=folder/'csi.npy';shape=(len(idx),2,config['num_antennas'],config['n_sc'])
        if len(idx):
            data=np.lib.format.open_memmap(target,mode='w+',dtype=np.float32,shape=shape)
            data[:]=0  # Explicit placeholder only; usable mask is authoritative.
            for start in range(0,len(idx),export_chunk):
                batch=idx[start:start+export_chunk];keep=usable[batch]
                if not keep.any():continue
                selected=batch[keep]
                norm,scale=align_and_normalize(np.asarray(serving[selected,0]),refs[selected],frequencies)
                rows=np.arange(start,start+len(batch))[keep]
                data[rows,0]=norm.real;data[rows,1]=norm.imag;rms[selected]=scale
            data.flush();del data
        else:np.save(target,np.empty(shape,np.float32))
        np.savez(folder/'ue.npz',ue_indices=idx,source_ue_indices=source_indices[idx],ue_positions_m=positions[idx],
                 parcel_index=labels[idx],serving_sector_index=owner[idx],feedback_usable=usable[idx],
                 active_path_link=active[idx],no_path_found_all_sectors=~found_any[idx],
                 zero_power_despite_valid_paths=(found_any & ~active)[idx],
                 tau_ref_s=refs[idx],rms=rms[idx],path_gain_linear=raw_selected[idx],
                 mean_cfr_gain=cfr_energy[idx],path_counts=counts[idx],delay_window_clipped=clipped[idx])
        metadata=dict(item,ue_count=len(idx),usable_count=int(usable[idx].sum()),shape=list(shape),
                      invalid_csi_policy='Zero placeholder; consult ue.npz feedback_usable, never interpret as measured zero channel.',
                      sha256=sha256(target))
        write_json(folder/'metadata.json',metadata)
        groups[item['directory']]=dict(count=len(idx),usable_count=int(usable[idx].sum()),shape=list(shape),sha256=metadata['sha256'])
    del serving
    np.savez(output/'association.npz',serving_sector_index=owner,active_path_link=active,feedback_usable=usable,
             no_path_found_all_sectors=~found_any,zero_power_despite_valid_paths=found_any & ~active,
             parcel_index=labels,tau_ref_s=refs,rms=rms,
             sector_scores_watt_equivalent=scores,path_counts=counts,delay_window_clipped=clipped,
             frequencies_hz=frequencies,sector_ids=np.array([r['sector']['id'] for r in results]))
    del scores
    return dict(ue_candidates=n,valid_path_ues=int(found_any.sum()),positive_path_power_ues=int(active.sum()),feedback_samples=int(usable.sum()),
                no_path_found_all_sectors=int((~found_any).sum()),
                zero_power_despite_valid_paths=int((found_any & ~active).sum()),
                selected_cfr_unusable=int((active & ~usable).sum()),saved_ue_rows=n,grouping='actual_scene_parcels',parcel_groups=groups)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--geometry',type=Path,default=DEFAULT_GEOMETRY)
    p.add_argument('--deployment',type=Path,default=DEFAULT_DEPLOYMENT)
    p.add_argument('--output',type=Path,default=ROOT/'data/csi/city-1km-feedback')
    p.add_argument('--chunk',type=int,default=32)
    p.add_argument('--samples-per-src',type=int,default=100000,help='Fixed ray directions per TX source per call; never scaled by RX count')
    p.add_argument('--workers',type=int,default=1,help='Unpinned spawn processes; prefer --gpus for explicit one-process-per-GPU scheduling')
    p.add_argument('--gpus',nargs='+',help='Explicit CUDA device IDs/UUIDs; one persistent process per device, respects inherited CUDA_VISIBLE_DEVICES')
    p.add_argument('--cpu-sets',nargs='+',help='Optional per-GPU CPU affinity, e.g. 0-11 12-23 24-47; Linux only, one set per --gpus entry')
    p.add_argument('--raw-compression',choices=['compressed','stored'],default='compressed',help='Same arrays: compressed saves disk, stored removes ZIP compression CPU cost')
    p.add_argument('--async-write',action='store_true',help='Overlap one bounded path-file write with the next batch compute')
    p.add_argument('--flush-batches',type=int,default=8,help='Flush CSI mmap every this many batches and always at sector completion; not resume support')
    p.add_argument('--export-chunk',type=int,default=128,help='CPU-only feedback/export batch, does not change RT receiver batches')
    p.add_argument('--disk-reserve-gib',type=float,default=20.,help='Minimum free space beyond known CFR outputs; path storage is not included in estimate')
    p.add_argument('--limit-sectors',type=int);p.add_argument('--limit-ues',type=int,help='Seeded subset for a genuinely small test')
    p.add_argument('--propagation-profile',choices=['source-informed','legacy'],default='source-informed')
    p.add_argument('--max-depth',type=int);p.add_argument('--max-num-paths-per-src',type=int,default=200000)
    p.add_argument('--terrain-scattering',choices=['off','source-material'],default='off',help='Off: S=0 for terrain, source ground-scattering baseline; explicit cross-backend adaptation')
    p.add_argument('--allow-unverified-topology',action='store_true',help='Explicit diagnostic-only override of diffraction topology gate; never certifies fidelity')
    p.add_argument('--num-antennas',type=int,default=32);p.add_argument('--n-fft',type=int,default=1024)
    p.add_argument('--n-sc',type=int,default=64);p.add_argument('--carrier-hz',type=float)
    p.add_argument('--bandwidth-hz',type=float,default=20e6);p.add_argument('--tx-power-dbm',type=float,default=44.)
    p.add_argument('--tx-pattern',choices=['tr38901','iso'],default='tr38901')
    p.add_argument('--variant',default='metal_ad_mono_polarized' if sys.platform=='darwin' else 'cuda_ad_mono_polarized')
    for flag in ['diffraction','edge-diffraction','diffuse-reflection','refraction']:
        p.add_argument('--'+flag,action=argparse.BooleanOptionalAction,default=None,help='Override profile mechanism; geometry/material checks still required')
    p.add_argument('--significant-db',type=float,default=25.);p.add_argument('--seed',type=int,default=42)
    p.add_argument('--convention',choices=['deepmimo','centered'],default='centered',help='Frequency grid ONLY: nonnegative FFT bins or centered offsets')
    p.add_argument('--coefficient-mode',choices=['physical-baseband','raw-passband'],default='physical-baseband')
    p.add_argument('--normalization',choices=['unit','ofdm'],default='unit',help='Unit channel or 1/sqrt(N) discrete OFDM scale')
    p.add_argument('--delay-window',choices=['none','fft'],default='none',help='Keep all delays or clip absolute tau>=N/B from CFR only')
    p.add_argument('--check-native-cfr',action='store_true',help='Compare physical output with Sionna CFR; extra cost, intended for bounded smoke')
    p.add_argument('--native-cfr-nmse-tolerance',type=float,default=1e-6)
    p.add_argument('--dry-run',action='store_true')
    from propagation_profiles import apply_profile, source_audit, profile_metadata
    supplied=p.parse_args(argv)
    args=argparse.Namespace(**apply_profile(supplied))
    if args.check_native_cfr and (args.coefficient_mode!='physical-baseband' or args.delay_window!='none'):
        p.error('--check-native-cfr requires physical-baseband and no delay window')
    if not math.isfinite(args.native_cfr_nmse_tolerance) or args.native_cfr_nmse_tolerance<=0:p.error('Invalid native CFR tolerance')
    for key in ['chunk','samples_per_src','workers','max_num_paths_per_src','num_antennas','n_fft','n_sc','flush_batches','export_chunk']:
        if getattr(args,key)<1:p.error(f'{key} must be positive')
    if args.max_depth<0 or args.seed<0 or not math.isfinite(args.significant_db) or args.significant_db<0:p.error('Invalid depth, seed or significant path threshold')
    if not math.isfinite(args.carrier_hz) or args.carrier_hz<=0 or not math.isfinite(args.tx_power_dbm):p.error('Invalid carrier or TX power')
    for key in ['limit_ues','limit_sectors']:
        if getattr(args,key) is not None and getattr(args,key)<1:p.error(f'{key} must be positive')
    if args.edge_diffraction and not args.diffraction:p.error('--edge-diffraction requires --diffraction')
    if not math.isfinite(args.disk_reserve_gib) or args.disk_reserve_gib<0:p.error('disk-reserve-gib must be finite and nonnegative')
    try: devices=selected_devices(args.gpus)
    except ValueError as exc:p.error(str(exc))
    if devices and not args.variant.startswith('cuda'):p.error('--gpus requires a CUDA Mitsuba variant')
    if devices and args.workers!=1:p.error('--gpus already creates one worker per device; leave --workers at 1')
    if args.cpu_sets:
        if not devices or len(args.cpu_sets)!=len(devices):p.error('--cpu-sets needs one entry per GPU')
        try:cpu_sets=[parse_cpu_set(spec) for spec in args.cpu_sets]
        except ValueError as exc:p.error(str(exc))
        if not hasattr(os,'sched_getaffinity'):p.error('--cpu-sets requires Linux affinity support')
        if any(not cpus.issubset(os.sched_getaffinity(0)) for cpus in cpu_sets):p.error('CPU set exceeds current allocation')
        if sum(map(len,cpu_sets))!=len(set().union(*cpu_sets)):p.error('Per-GPU CPU sets must not overlap')
    if not devices and args.workers>1 and args.variant.startswith('cuda'):
        warnings.warn('Unpinned CUDA workers may all use the same GPU; use --gpus for multiple cards')
    frequency_plan(args.bandwidth_hz,args.n_fft,args.n_sc,args.convention)
    geometry=args.geometry.resolve();output=args.output.resolve();deployment=args.deployment.resolve()
    manifest=json.loads((geometry/'geometry-manifest.json').read_text())
    topology=manifest.get('topology',{})
    gate='edge_diffraction_ready' if args.edge_diffraction else 'diffraction_ready'
    if args.diffraction and not topology.get(gate,False):
        failures=topology.get('edge_diffraction_gate_failures' if args.edge_diffraction else 'strict_gate_failures',["missing v2 topology"])
        message=f'Geometry does not pass requested diffraction topology checks: {failures}'
        if not args.allow_unverified_topology:p.error(message+'; regenerate/repair geometry or explicitly use diagnostic override')
        warnings.warn(message+'; diagnostic override recorded')
    try:evidence=source_audit(manifest)
    except (ValueError,OSError) as exc:p.error(f'Invalid source provenance: {exc}')
    for group in manifest['groups']:
        path=(geometry/group['obj']).resolve()
        if not path.is_relative_to(geometry) or not path.is_file():p.error('Invalid/missing geometry mesh')
        if group.get('sha256') and group['sha256']!=sha256(path):p.error('Mesh hash mismatch; rebuild geometry')
    positions=np.load(geometry/'ue_candidates.npy',allow_pickle=False)
    if positions.ndim!=2 or positions.shape[1]!=3 or not np.isfinite(positions).all() or not len(positions):p.error('Invalid UE position array')
    if manifest.get('ue_candidates_sha256') and manifest['ue_candidates_sha256']!=sha256(geometry/'ue_candidates.npy'):p.error('UE hash mismatch')
    if args.limit_ues and args.limit_ues<len(positions):
        idx=np.sort(np.random.default_rng(args.seed).choice(len(positions),args.limit_ues,replace=False)); positions=positions[idx]
    else:idx=np.arange(len(positions))
    dep=json.loads(deployment.read_text());sectors=dep['sectors'][:args.limit_sectors]
    if not sectors or len({s['id'] for s in sectors})!=len(sectors):p.error('Missing/duplicate sectors')
    for sector in sectors:
        if not np.isfinite(sector['position_m']).all() or not math.isfinite(sector['azimuth_deg']) or not math.isfinite(sector['downtilt_deg']):p.error('Invalid sector geometry')
    config={k:v for k,v in vars(args).items() if k not in ['geometry','output','deployment','dry_run','limit_ues','limit_sectors']}
    provenance=profile_metadata(config,evidence)
    provenance['channel_contract']={k:config[k] for k in ('coefficient_mode','convention','normalization','delay_window')}
    provenance['terrain_policy']='Terrain S=0 when off; disables diffuse and returns energy to specular. Not identical to toggling source global diffuse flag.'
    provenance['material_frequency_policy']='Preserve source constant permittivity/conductivity; no automatic frequency rescaling.'
    provenance['material_frequency_mismatches']=[dict(material_key=m['key'],reference_hz=m['reference_frequency_hz'],carrier_hz=args.carrier_hz)
        for m in manifest.get('materials',[]) if m.get('reference_frequency_hz') and not math.isclose(m['reference_frequency_hz'],args.carrier_hz,rel_tol=1e-6)]
    if provenance['material_frequency_mismatches']:
        warnings.warn(f'{len(provenance["material_frequency_mismatches"])} materials use fixed source parameters at a different reference frequency; see model_provenance')
    from parcel_groups import assign_parcels, parcels_from_manifest
    try:parcel_labels,parcel_catalog=assign_parcels(positions,parcels_from_manifest(manifest))
    except (ValueError,OSError) as exc:p.error(f'Invalid parcel geometry: {exc}')
    estimate=storage_estimate(len(positions),len(sectors),args.num_antennas,args.n_sc)
    print(json.dumps(dict(ue_candidates=len(positions),sectors=len(sectors),raw_csi_per_sector=[len(positions),1,args.num_antennas,args.n_sc],
                         feedback_shape=['N_ue_in_parcel',2,args.num_antennas,args.n_sc],parcel_groups=len(parcel_catalog['groups']),storage_estimate=estimate,config=config),ensure_ascii=False,indent=2),flush=True)
    if args.dry_run:return 0
    if output.exists():p.error('Output already exists. Choose a new directory; existing results are never overwritten')
    try:require_disk_space(output,estimate['known_output_estimate_bytes'],args.disk_reserve_gib)
    except ValueError as exc:p.error(str(exc))
    output.mkdir(parents=True,exist_ok=False)
    np.save(output/'ue_positions.npy',positions);np.save(output/'source_ue_indices.npy',idx)
    np.save(output/'ue_parcel_index.npy',parcel_labels)
    write_json(output/'parcel-catalog.json',parcel_catalog)
    bins,frequencies=frequency_plan(args.bandwidth_hz,args.n_fft,args.n_sc,args.convention)
    report=dict(status='running',input_hashes={'geometry_manifest':sha256(geometry/'geometry-manifest.json'),
                'ue_candidates':sha256(geometry/'ue_candidates.npy'),'deployment':sha256(deployment)},config=config,
                geometry_manifest=manifest,sectors=sectors,parcel_catalog=parcel_catalog,selected_subcarrier_indices=bins.tolist(),frequencies_hz=frequencies.tolist(),
                limitations=['Synthetic outdoor sampling positions, not measured users or concurrent demand.',
                'No-path means no path found under specified solver/options; no physical blockage or convergence certification.',
                'Sionna CIR includes pattern/array responses; this is not a byte-identical DeepMIMO export/converter.',
                'No SINR, scheduling, estimation noise, quantization or verified service capacity.',
                'Actual parcel grouping retains all UEs; no train/val/test split or independence claim.',
                'Raw CIR paths may be many; disk use and shared accelerator memory must be budgeted.',
                'Material adaptation is recorded in geometry manifest; foliage not simulated.'])
    report.update(schema_version=3,grouping='actual_scene_parcels',source_evidence=evidence,model_provenance=provenance,storage_estimate=estimate,
                  validation_status='not_convergence_certified',
                  backend_limitations=['At most one diffraction per path; no diffuse-diffraction combined paths.',
                                       'Thin-slab transmission only; vegetation propagation absent.',
                                       'Per-source candidate capacity shared across RX batch; occupancy not exposed.',
                                       'Synthetic-array plane-wave approximation; near-field comparison not performed.'])
    write_json(output/'report.json',report)
    tasks=[dict(geometry=str(geometry),output=str(output),index=i,sector=s,config=config) for i,s in enumerate(sectors)]
    started=time.perf_counter()
    try:
        results=run_sector_tasks(tasks,args.workers,devices)
        results.sort(key=lambda r:r['index'])
        counts=export_feedback(output,results,positions,config)
        report.update(status='complete',counts=counts,seconds=time.perf_counter()-started,raw_sectors=results)
        write_json(output/'report.json',report)
        print(json.dumps(counts,ensure_ascii=False,indent=2),flush=True)
    except Exception as exc:
        report.update(status='failed',error=f'{type(exc).__name__}: {exc}')
        write_json(output/'report.json',report);raise
    return 0


if __name__=='__main__':
    raise SystemExit(main())
