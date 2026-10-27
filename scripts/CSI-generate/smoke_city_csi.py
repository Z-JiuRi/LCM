#!/usr/bin/env python3
"""Explicit bounded REAL-RT smoke: analytic free space + a few city links.

Never run automatically with unit tests. Requires prepared v2 geometry.
Does not establish convergence, coverage, or InSite/DeepMIMO equivalence.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys
import time
import numpy as np
import generate_city_csi as G


def free_space_check(variant):
    import mitsuba as mi
    mi.set_variant(variant)
    import sionna.rt as rt
    scene=rt.Scene();scene.frequency=3.5e9
    scene.tx_array=rt.PlanarArray(num_rows=1,num_cols=1,pattern='iso',polarization='V')
    scene.rx_array=rt.PlanarArray(num_rows=1,num_cols=1,pattern='iso',polarization='V')
    scene.add(rt.Transmitter('tx',[0,0,2]))
    distances=np.array([10.,20.])
    for i,d in enumerate(distances):scene.add(rt.Receiver(f'rx{i}',[float(d),0,2]))
    paths=rt.PathSolver(deterministic=True)(scene,max_depth=0,samples_per_src=16,
        max_num_paths_per_src=32,los=True,specular_reflection=False,diffuse_reflection=False,
        diffraction=False,refraction=False,synthetic_array=True,seed=42)
    raw,a,tau,valid=G.extract_coefficients(paths,'physical-baseband')
    if not np.array_equal(valid.sum(axis=1),np.ones(2,dtype=int)):
        raise AssertionError('Free-space fixture must produce exactly one LOS path per link')
    c=299792458.;wavelength=c/3.5e9
    expected_amplitude=wavelength/(4*np.pi*distances)
    measured=np.sqrt(np.sum(abs(a[:,0,0])**2,axis=-1))
    np.testing.assert_allclose(measured,expected_amplitude,rtol=3e-5,atol=1e-10)
    actual_tau=np.sum(np.where(valid,tau,0),axis=1)
    np.testing.assert_allclose(actual_tau,distances/c,rtol=3e-6,atol=1e-12)
    # Independent carrier phase formula from raw a; backend uses float32 phase.
    expected=raw*np.exp(-2j*np.pi*3.5e9*np.where(valid,tau,0))[:,None,None,:]
    phase_nmse=float(np.sum(abs(expected-a)**2)/np.sum(abs(a)**2))
    if phase_nmse>1e-6:raise AssertionError(f'Carrier phase check failed: {phase_nmse}')
    _,f=G.frequency_plan(convention='centered')
    h,_=G.synthesize_cfr(a,tau,valid,f,convention='centered',normalization='unit',delay_window='none')
    check=G.compare_native_cfr(paths,h,f,'unit',1024)
    if check['relative_squared_error']>1e-6:raise AssertionError(check)
    return dict(status='passed',distances_m=distances.tolist(),measured_amplitudes=measured.tolist(),
        expected_friis_amplitudes=expected_amplitude.tolist(),carrier_phase_formula_nmse=phase_nmse,
        native_cfr_check=check,versions={'sionna_rt':rt.__version__,'mitsuba':mi.__version__},
        limitations='Analytic LOS and same-path CFR checks only; no multipath convergence test')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--geometry',type=Path,required=True)
    p.add_argument('--deployment',type=Path,default=G.DEFAULT_DEPLOYMENT)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--variant',default='metal_ad_mono_polarized' if sys.platform=='darwin' else 'cuda_ad_mono_polarized')
    p.add_argument('--ues',type=int,default=8);p.add_argument('--sectors',type=int,default=2)
    p.add_argument('--samples',type=int,default=2000)
    args=p.parse_args(argv)
    if not 1<=args.ues<=16 or not 1<=args.sectors<=2 or not 1<=args.samples<=5000:
        p.error('Smoke hard limits: 1..16 UE, 1..2 sectors, 1..5000 samples')
    out=args.output.resolve()
    if out.exists():p.error('Output already exists; choose a new directory')
    if not (args.geometry/'geometry-manifest.json').is_file():p.error('Prepared geometry missing')
    out.mkdir(parents=True,exist_ok=False);start=time.perf_counter()
    result=dict(status='running',scope='bounded real RT, not convergence certified')
    G.write_json(out/'smoke-summary.json',result)
    try:
        result['free_space']=free_space_check(args.variant)
        G.main(['--geometry',str(args.geometry),'--deployment',str(args.deployment),'--output',str(out/'city'),
            '--variant',args.variant,'--limit-ues',str(args.ues),'--limit-sectors',str(args.sectors),
            '--chunk','2','--samples-per-src',str(args.samples),'--max-num-paths-per-src','20000',
            '--propagation-profile','source-informed','--max-depth','7',
            '--check-native-cfr','--async-write','--disk-reserve-gib','1'])
        report=json.loads((out/'city/report.json').read_text())
        checks=[]
        for sector in report['raw_sectors']:
            meta=json.loads((Path(sector['folder'])/'metadata.json').read_text())
            checks.extend(b['native_cfr_check'] for b in meta['batches'])
        result.update(status='passed',city_counts=report['counts'],city_native_cfr_checks=checks,
            seconds=time.perf_counter()-start,
            notes=['Low ray budget deliberately tests plumbing, not no-path classification or search convergence.',
                   'Native CFR comparison uses the same traced paths; it is not an independent RT oracle.'])
    except BaseException as exc:
        result.update(status='failed',error=f'{type(exc).__name__}: {exc}',seconds=time.perf_counter()-start)
        G.write_json(out/'smoke-summary.json',result);raise
    G.write_json(out/'smoke-summary.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=='__main__':raise SystemExit(main())
