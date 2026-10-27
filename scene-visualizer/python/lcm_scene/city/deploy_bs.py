"""Replace city BS plans using a 500m reference and synthetic land-use demand."""
import argparse
from copy import deepcopy
import gzip
import hashlib
import json
from pathlib import Path
from shapely import affinity
from shapely.geometry import Polygon
from ..paths import STUDIO_ROOT


def footprint(asset, instance):
    p = Polygon(asset['footprint']['outer'], asset['footprint'].get('holes', []))
    return affinity.translate(affinity.rotate(p, instance['rotation_z_deg'], origin=(0, 0)), *instance['position_m'][:2])


def deploy(size, output_root, isd=500):
    from .demand_bs import build_plan
    folder = STUDIO_ROOT / f'data/scenes/environment-cities/city-{size//1000}km'
    raw = (folder / 'assembled-city.scene.json.gz').read_bytes()
    scene = json.loads(gzip.decompress(raw))
    baseline = deepcopy(scene)
    scene['radio_deployment'] = build_plan(scene, size, isd)
    summary = scene['radio_deployment']['summary']
    scene['manifest'].update(radio_deployment_summary=summary,
                            status='Environment city with synthetic land-use-demand BS plan; no RF coverage/capacity validation or new channels.')
    for key in ['assets', 'instances', 'roads', 'parks', 'parcels', 'environment']:
        assert scene[key] == baseline[key]
    output = output_root / f'city-{size//1000}km'
    output.mkdir(parents=True, exist_ok=True)
    (output / 'assembled-city.scene.json.gz').write_bytes(gzip.compress(json.dumps(scene, ensure_ascii=False, separators=(',', ':')).encode(), mtime=0))
    (output / 'assembled-city-manifest.json').write_text(json.dumps(scene['manifest'], ensure_ascii=False, indent=2)+'\n')
    radio = scene['radio_deployment']
    report = {'input_sha256': hashlib.sha256(raw).hexdigest(), **{k:v for k,v in radio.items() if k != 'demand_model'},
              'demand_model': {k:v for k,v in radio['demand_model'].items() if k not in ['cells','building_estimates']},
              'demand_report': 'ue-demand.json'}
    (output / 'bs-deployment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    (output / 'ue-demand.json').write_text(json.dumps(radio['demand_model'], ensure_ascii=False, indent=2)+'\n')
    view = json.loads((folder / 'assembled-city.view.json').read_text())
    view['manifest'] = scene['manifest']; view['radio_deployment'] = radio
    (output / 'assembled-city.view.json').write_text(json.dumps(view, ensure_ascii=False, separators=(',', ':')))
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size', type=int, nargs='+', choices=[1000,2000,4000], default=[1000,2000,4000])
    parser.add_argument('--isd', type=int, choices=[500], default=500, help='500m soft reference; this scenario does not support a fixed 200m layout.')
    parser.add_argument('--output', type=Path, default=STUDIO_ROOT/'data/scenes/deployed-cities')
    args = parser.parse_args()
    for size in args.size:
        deploy(size, args.output, args.isd)


if __name__ == '__main__':
    main()
