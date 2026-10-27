#!/usr/bin/env python3
"""Static outdoor CSI: RT paths -> raw CFR -> serving-sector feedback samples.

Project implementation, not an official DeepMIMO script.

Phase convention (matches DeepMIMO v4 Sionna converter, sionna_paths.py:274-275):
    H[k] = Σ_p  a_p  ·  exp(-j2π·k·B/N·τ_p) / sqrt(N)

where a_p = paths.a (the Sionna passband coefficient, WITHOUT carrier phase),
and k·B/N is the baseband subcarrier offset from DC.  This is numerically
identical to what DeepMIMO stores when using Sionna RT as the back-end tracer.

paths.cir() is NOT used for coefficient extraction; it adds exp(-j2π·f_c·τ)
which would shift the effective sampling grid to the absolute carrier frequency.
paths.tau / paths.valid are used directly alongside paths.a.

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
from concurrent.futures import ProcessPoolExecutor, as_completed

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
    powers = np.mean(np.abs(a.astype(np.complex128))**2, axis=(1, 2))
    powers = np.where(valid, powers, 0.)
    nonzero = valid & (powers > 0)
    strongest = powers.max(axis=1, initial=0.)
    significant = nonzero & (powers >= strongest[:, None]*10**(-significant_db/10))
    refs = np.min(np.where(significant, tau, np.inf), axis=1, initial=np.inf)
    refs = np.where(np.isfinite(refs), refs, np.nan)
    return powers.sum(axis=1), refs, valid.sum(axis=1).astype(np.int32)


def synthesize_cfr(a, tau, valid, frequencies, n_fft=1024, bandwidth=20e6, convention='deepmimo'):
    """Sum Sionna antenna-resolved paths. Default matches DM OFDM scale/window.

    No top-25 path truncation. In deepmimo mode raw paths with tau>=N/B are
    excluded only from synthesized CFR and counted; still saved in raw batches.
    centered mode uses Sionna-like unscaled CFR and retains absolute delays.
    """
    if a.ndim != 4 or tau.shape != valid.shape or a.shape[-1] != tau.shape[-1]:
        raise ValueError('Inconsistent synthesis shapes')
    keep = valid.copy()
    dropped = np.zeros(len(tau), dtype=np.int32)
    if convention == 'deepmimo':
        over = valid & (tau >= n_fft/bandwidth)
        dropped = over.sum(axis=1).astype(np.int32); keep &= ~over
        scale = 1/math.sqrt(n_fft)
    elif convention == 'centered': scale = 1.
    else: raise ValueError('Unknown synthesis convention')
    output = np.zeros((*a.shape[:3], len(frequencies)), dtype=np.complex64)
    # Bound the phase intermediate even when diffuse paths are numerous.
    for start in range(0, a.shape[-1], 128):
        stop = start+128
        delays = np.where(keep[:, start:stop], tau[:, start:stop], 0.)
        response = np.exp(-2j*np.pi*delays[..., None]*np.asarray(frequencies))
        coefficients = np.where(keep[:, None, None, start:stop], a[..., start:stop], 0.)
        output += (np.einsum('urmp,upk->urmk', coefficients, response, optimize=True)*scale).astype(np.complex64)
    if not np.isfinite(output).all(): raise ValueError('Nonfinite synthesized CSI')
    return output, dropped


def align_and_normalize(H, tau_ref, frequencies):
    """H=[UE,TX_ant,freq]; inverse requires retained tau_ref and RMS."""
    if H.ndim != 3 or len(H) != len(tau_ref) or not np.isfinite(tau_ref).all():
        raise ValueError('Invalid CSI or reference delays')
    corrected = H*np.exp(2j*np.pi*np.asarray(tau_ref)[:, None, None]*np.asarray(frequencies))
    rms = np.sqrt(np.mean(np.abs(corrected)**2, axis=(1, 2), dtype=np.float64))
    if not np.isfinite(rms).all() or np.any(rms <= 0): raise ValueError('Zero/nonfinite CSI cannot be normalized')
    return (corrected/rms[:, None, None]).astype(np.complex64), rms


def split_indices(positions, seed=42, mode='spatial', block_m=100.):
    """Assign before valid-link filtering; complete XY blocks stay together.

    Spatial block split prevents identical blocks crossing sets, but is not a
    buffered geographic holdout nor a claim of independent channel samples.
    """
    rng = np.random.default_rng(seed)
    if mode == 'random':
        groups = np.arange(len(positions)); inverse = groups
    elif mode == 'spatial':
        if block_m <= 0: raise ValueError('Positive spatial block size required')
        groups, inverse = np.unique(np.floor(np.asarray(positions)[:, :2]/block_m).astype(np.int64), axis=0, return_inverse=True)
    else: raise ValueError('Unknown split mode')
    n = len(groups); perm = rng.permutation(n)
    end_train = int(.8*n); end_val = end_train+int(.1*n)
    labels = np.full(n, 2, dtype=np.int8)
    labels[perm[:end_train]] = 0; labels[perm[end_train:end_val]] = 1
    return labels[inverse]


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
                    scattering_coefficient=float(m['scattering_coefficient']),
                    xpd_coefficient=float(m['xpd_coefficient']), scattering_pattern=m['scattering_pattern'], **kwargs)
        objects.append(rt.SceneObject(name=f'mesh_{index}', fname=str(geometry/group['obj']), radio_material=material))
    scene.add(objects); scene.frequency=config['carrier_hz']; scene.bandwidth=config['bandwidth_hz']
    scene.tx_array=rt.PlanarArray(num_rows=1, num_cols=config['num_antennas'], horizontal_spacing=.5,
                                vertical_spacing=.5, pattern=config['tx_pattern'], polarization='V')
    scene.rx_array=rt.PlanarArray(num_rows=1, num_cols=1, pattern='iso', polarization='V')
    return scene


def _worker(task):
    """One sector per spawn worker; arrays go to disk, not IPC or global RAM."""
    import mitsuba as mi
    config=task['config']; mi.set_variant(config['variant'])
    import sionna.rt as rt
    geometry=Path(task['geometry']); output=Path(task['output']); sector=task['sector']
    manifest=json.loads((geometry/'geometry-manifest.json').read_text())
    positions=np.load(output/'ue_positions.npy', mmap_mode='r', allow_pickle=False)
    folder=output/'raw'/f"sector-{task['index']:03d}"; folder.mkdir(parents=True, exist_ok=False)
    scene=build_scene(geometry, manifest, config)
    orientation=[math.radians(float(sector['azimuth_deg'])), math.radians(float(sector['downtilt_deg'])), 0.]
    scene.add(rt.Transmitter('tx', list(map(float, sector['position_m'])), orientation=orientation, power_dbm=config['tx_power_dbm']))
    solver=rt.PathSolver(deterministic=True); options=solver_options(config, task['index'])
    _, frequencies=frequency_plan(config['bandwidth_hz'], config['n_fft'], config['n_sc'], config['convention'])
    H=np.lib.format.open_memmap(folder/'csi.npy', mode='w+', dtype=np.complex64,
                                shape=(len(positions),1,config['num_antennas'],config['n_sc']))
    gain=np.zeros(len(positions)); reference=np.full(len(positions),np.nan)
    counts=np.zeros(len(positions),np.int32); clipped=np.zeros(len(positions),np.int32)
    start_time=time.perf_counter(); batches=[]
    for start in range(0,len(positions),config['chunk']):
        stop=min(start+config['chunk'],len(positions)); names=[f'rx_{i}' for i in range(start,stop)]
        scene.add([rt.Receiver(name, list(map(float,pos))) for name,pos in zip(names,positions[start:stop])])
        try:
            paths=solver(scene, **options)
            # Use raw paths.a (passband coefficient, no carrier phase added).
            # Shape (synthetic_array=True): [U, RX_ant, TX, TX_ant, P]
            # tau/valid layout: [U, TX, P]  -> squeeze TX dim (single TX per worker).
            a_np = (np.asarray(paths.a[0]) + 1j*np.asarray(paths.a[1]))  # [U,RX_ant,TX,TX_ant,P]
            a = a_np[:, :, 0, :, :]                                        # [U,RX_ant,TX_ant,P]
            tau = np.asarray(paths.tau, dtype=np.float64)[:, 0, :]        # [U,P]
            valid = np.asarray(paths.valid, dtype=bool)[:, 0, :]           # [U,P]
            gain[start:stop],reference[start:stop],counts[start:stop]=path_statistics(a,tau,valid,config['significant_db'])
            cfr,clipped[start:stop]=synthesize_cfr(a,tau,valid,frequencies,config['n_fft'],config['bandwidth_hz'],config['convention'])
            H[start:stop]=cfr
            raw=dict(ue_indices=np.arange(start,stop),passband_coefficients=a.astype(np.complex64),
                     path_delays_s=tau, path_valid=valid,
                     theta_t_rad=np.asarray(paths.theta_t), phi_t_rad=np.asarray(paths.phi_t),
                     theta_r_rad=np.asarray(paths.theta_r), phi_r_rad=np.asarray(paths.phi_r),
                     interactions=np.asarray(paths.interactions), vertices_m=np.asarray(paths.vertices))
            filename=f'paths-{start:07d}-{stop:07d}.npz'
            np.savez_compressed(folder/filename, **raw)
            batches.append(dict(file=filename,start=start,stop=stop,path_slots=valid.shape[-1],sha256=sha256(folder/filename)))
            H.flush()
            print(f"[{sector['id']}] {stop}/{len(positions)} RX; paths={int(valid.sum())}",flush=True)
            del paths,a_np,a,cfr,raw
        finally:
            for name in names: scene.remove(name)
    H.flush(); del H
    np.savez(folder/'link_stats.npz',path_gain_linear=gain,tau_ref_s=reference,path_counts=counts,delay_window_clipped=clipped,
             no_path_found=counts==0)
    summary=dict(sector=sector,solver_options=options,orientation_rad=orientation,config=config,batches=batches,
                 versions={'sionna_rt':rt.__version__,'mitsuba':mi.__version__},seconds=time.perf_counter()-start_time,
                 csi_axes=['ue','rx_ant','tx_ant','frequency'],csi_sha256=sha256(folder/'csi.npy'))
    write_json(folder/'metadata.json',summary)
    return dict(index=task['index'],folder=str(folder),sector=sector,seconds=summary['seconds'])


def export_feedback(output, results, positions, config):
    """Associate by sum of antenna-averaged linear PATH power, not sum|H|.

    Equal TX powers by default; otherwise scores include TX power. No coherent
    precoding gain or load/interference-aware association is claimed.
    """
    n=len(positions); scores=np.zeros((len(results),n)); stats=[]
    for row,result in enumerate(results):
        with np.load(Path(result['folder'])/'link_stats.npz',allow_pickle=False) as z:
            item={k:z[k].copy() for k in z.files}
        stats.append(item)
        scores[row]=item['path_gain_linear']*10**((config['tx_power_dbm']-30)/10)
    owner=np.argmax(scores,axis=0); active=np.max(scores,axis=0)>0
    found_any=np.any(np.array([item['path_counts'] for item in stats])>0,axis=0)
    owner[~active]=-1
    labels=split_indices(positions,config['seed'],config['split_mode'],config['block_m'])
    refs=np.full(n,np.nan); rms=np.full(n,np.nan); cfr_energy=np.zeros(n); counts=np.zeros(n,np.int32)
    clipped=np.zeros(n,np.int32); raw_selected=np.zeros(n,np.float64)
    # Disk backed: no multi-sector full CSI tensor in parent RAM.
    serving=np.lib.format.open_memmap(output/'serving_csi.npy', mode='w+',dtype=np.complex64,
                                    shape=(n,1,config['num_antennas'],config['n_sc']))
    serving[:]=0
    for row,result in enumerate(results):
        idx=np.flatnonzero(owner==row)
        if not len(idx):continue
        source=np.load(Path(result['folder'])/'csi.npy',mmap_mode='r',allow_pickle=False)
        refs[idx]=stats[row]['tau_ref_s'][idx]; counts[idx]=stats[row]['path_counts'][idx]
        clipped[idx]=stats[row]['delay_window_clipped'][idx]; raw_selected[idx]=stats[row]['path_gain_linear'][idx]
        for start in range(0,len(idx),128):
            batch=idx[start:start+128]; values=np.asarray(source[batch])
            serving[batch]=values; cfr_energy[batch]=np.mean(np.abs(values.astype(np.complex128))**2,axis=(1,2,3))
    serving.flush()
    usable=active & np.isfinite(refs) & (cfr_energy>0)
    _,frequencies=frequency_plan(config['bandwidth_hz'],config['n_fft'],config['n_sc'],config['convention'])
    splits={}
    for split,label in [('train',0),('val',1),('test',2)]:
        idx=np.flatnonzero(usable & (labels==label))
        target=output/f'{split}.npy'; shape=(len(idx),2,config['num_antennas'],config['n_sc'])
        if len(idx):
            data=np.lib.format.open_memmap(target,mode='w+',dtype=np.float32,shape=shape)
            for start in range(0,len(idx),128):
                batch=idx[start:start+128]
                norm,scale=align_and_normalize(np.asarray(serving[batch,0]),refs[batch],frequencies)
                data[start:start+len(batch),0]=norm.real; data[start:start+len(batch),1]=norm.imag
                rms[batch]=scale
            data.flush();del data
        else:np.save(target,np.empty(shape,np.float32))
        np.savez(output/f'{split}_aux.npz',ue_indices=idx,ue_positions_m=positions[idx],
                 serving_sector_index=owner[idx],tau_ref_s=refs[idx],rms=rms[idx],
                 path_gain_linear=raw_selected[idx],mean_cfr_gain=cfr_energy[idx],path_counts=counts[idx])
        splits[split]=dict(count=len(idx),shape=list(shape),sha256=sha256(target))
    del serving
    np.savez(output/'association.npz',serving_sector_index=owner,active_path_link=active,feedback_usable=usable,
             no_path_found_all_sectors=~found_any,zero_power_despite_valid_paths=found_any & ~active,
             split_label=labels,tau_ref_s=refs,rms=rms,
             sector_scores_watt_equivalent=scores,path_counts=counts,delay_window_clipped=clipped,
             frequencies_hz=frequencies,sector_ids=np.array([r['sector']['id'] for r in results]))
    return dict(ue_candidates=n,valid_path_ues=int(found_any.sum()),positive_path_power_ues=int(active.sum()),feedback_samples=int(usable.sum()),
                no_path_found_all_sectors=int((~found_any).sum()),
                zero_power_despite_valid_paths=int((found_any & ~active).sum()),
                selected_cfr_unusable=int((active & ~usable).sum()),splits=splits)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--geometry',type=Path,default=DEFAULT_GEOMETRY)
    p.add_argument('--deployment',type=Path,default=DEFAULT_DEPLOYMENT)
    p.add_argument('--output',type=Path,default=ROOT/'data/csi/city-1km-feedback')
    p.add_argument('--chunk',type=int,default=32)
    p.add_argument('--samples-per-src',type=int,default=100000,help='Fixed ray directions per TX source per call; never scaled by RX count')
    p.add_argument('--workers',type=int,default=2,help='Spawn workers; shared accelerator/RAM may limit speedup')
    p.add_argument('--limit-sectors',type=int);p.add_argument('--limit-ues',type=int,help='Seeded subset for a genuinely small test')
    p.add_argument('--max-depth',type=int,default=3);p.add_argument('--max-num-paths-per-src',type=int,default=200000)
    p.add_argument('--num-antennas',type=int,default=32);p.add_argument('--n-fft',type=int,default=1024)
    p.add_argument('--n-sc',type=int,default=64);p.add_argument('--carrier-hz',type=float,default=3.5e9)
    p.add_argument('--bandwidth-hz',type=float,default=20e6);p.add_argument('--tx-power-dbm',type=float,default=44.)
    p.add_argument('--tx-pattern',choices=['tr38901','iso'],default='tr38901')
    p.add_argument('--variant',default='metal_ad_mono_polarized' if sys.platform=='darwin' else 'cuda_ad_mono_polarized')
    for flag in ['diffraction','edge-diffraction','diffuse-reflection','refraction']:
        p.add_argument('--'+flag,action='store_true',help='Enable explicitly; material/geometry validation and memory budget still required')
    p.add_argument('--significant-db',type=float,default=25.);p.add_argument('--seed',type=int,default=42)
    p.add_argument('--convention',choices=['deepmimo','centered'],default='deepmimo')
    p.add_argument('--split-mode',choices=['spatial','random'],default='spatial')
    p.add_argument('--block-m',type=float,default=100.);p.add_argument('--dry-run',action='store_true')
    args=p.parse_args(argv)
    for key in ['chunk','samples_per_src','workers','max_num_paths_per_src','num_antennas','n_fft','n_sc']:
        if getattr(args,key)<1:p.error(f'{key} must be positive')
    if args.max_depth<0 or args.seed<0 or not math.isfinite(args.significant_db) or args.significant_db<0:p.error('Invalid depth, seed or significant path threshold')
    if not math.isfinite(args.carrier_hz) or args.carrier_hz<=0 or not math.isfinite(args.tx_power_dbm):p.error('Invalid carrier or TX power')
    if not math.isfinite(args.block_m) or args.block_m<=0:p.error('Invalid spatial block size')
    for key in ['limit_ues','limit_sectors']:
        if getattr(args,key) is not None and getattr(args,key)<1:p.error(f'{key} must be positive')
    if args.edge_diffraction and not args.diffraction:p.error('--edge-diffraction requires --diffraction')
    frequency_plan(args.bandwidth_hz,args.n_fft,args.n_sc,args.convention)
    geometry=args.geometry.resolve();output=args.output.resolve();deployment=args.deployment.resolve()
    manifest=json.loads((geometry/'geometry-manifest.json').read_text())
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
    print(json.dumps(dict(ue_candidates=len(positions),sectors=len(sectors),raw_csi_per_sector=[len(positions),1,args.num_antennas,args.n_sc],
                         feedback_shape=['N_valid',2,args.num_antennas,args.n_sc],config=config),ensure_ascii=False,indent=2),flush=True)
    if args.dry_run:return 0
    if output.exists():p.error('Output already exists. Choose a new directory; existing results are never overwritten')
    output.mkdir(parents=True,exist_ok=False)
    np.save(output/'ue_positions.npy',positions);np.save(output/'source_ue_indices.npy',idx)
    bins,frequencies=frequency_plan(args.bandwidth_hz,args.n_fft,args.n_sc,args.convention)
    report=dict(status='running',input_hashes={'geometry_manifest':sha256(geometry/'geometry-manifest.json'),
                'ue_candidates':sha256(geometry/'ue_candidates.npy'),'deployment':sha256(deployment)},config=config,
                geometry_manifest=manifest,sectors=sectors,selected_subcarrier_indices=bins.tolist(),frequencies_hz=frequencies.tolist(),
                limitations=['Synthetic outdoor sampling positions, not measured users or concurrent demand.',
                'No-path means no path found under specified solver/options; no physical blockage or convergence certification.',
                'Sionna CIR includes pattern/array responses; this is not a byte-identical DeepMIMO export/converter.',
                'No SINR, scheduling, estimation noise, quantization or verified service capacity.',
                'Spatial split holds whole blocks but has no guard band; nearby blocks may have correlated channels.',
                'Raw CIR paths may be many; disk use and shared accelerator memory must be budgeted.',
                'Material adaptation is recorded in geometry manifest; foliage not simulated.'])
    write_json(output/'report.json',report)
    tasks=[dict(geometry=str(geometry),output=str(output),index=i,sector=s,config=config) for i,s in enumerate(sectors)]
    started=time.perf_counter()
    try:
        if args.workers==1:results=[_worker(task) for task in tasks]
        else:
            results=[]
            with ProcessPoolExecutor(max_workers=min(args.workers,len(tasks)),mp_context=mp.get_context('spawn')) as pool:
                futures=[pool.submit(_worker,t) for t in tasks]
                for future in as_completed(futures):results.append(future.result())
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
