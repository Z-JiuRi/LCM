"""Export the exact CSI candidate grid for visualization, without RT/mesh export."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'scripts'))
from city_geometry import build_ue_grid, load_scene


def prepare_ue(kms=(1,2,4), spacing=5.):
    public = ROOT/'web/public/scenes'
    public.mkdir(parents=True, exist_ok=True)
    records = {}
    for km in kms:
        source = ROOT/f'data/scenes/environment-cities/city-{km}km/assembled-city.scene.json.gz'
        scene = load_scene(source)
        positions, stats = build_ue_grid(scene,spacing,1.5,2.,1.,tuple(scene['ground']['extent_m']))
        output = ROOT/f'data/scenes/ue-candidates/city-{km}km'
        output.mkdir(parents=True,exist_ok=True)
        np.save(output/'ue_candidates.npy',positions)
        binary=positions.astype('<f4').tobytes()
        (public/f'city-{km}km-ue.f32').write_bytes(binary)
        record = dict(count=len(positions),spacing_m=spacing,ue_height_m=1.5,
                      building_clearance_m=2.,vegetation_clearance_m=1.,
                      positions_url=f'/scenes/city-{km}km-ue.f32',
                      format='little-endian-float32-xyz',source_scene_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                      positions_sha256=hashlib.sha256(binary).hexdigest(),
                      generator='scripts/city_geometry.py:build_ue_grid',grid_stats=stats,
                      status='Candidate sounding positions only; no channels or serving-sector assignment computed.')
        (output/'manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
        records[f'city-{km}km']=record
        print(f'city-{km}km: {len(positions):,} UE candidates, {spacing:g}m grid, {len(binary):,} display bytes',flush=True)
    return records


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--km',type=int,nargs='+',choices=[1,2,4],default=[1,2,4])
    parser.add_argument('--spacing',type=float,default=5.)
    args=parser.parse_args();prepare_ue(args.km,args.spacing)
