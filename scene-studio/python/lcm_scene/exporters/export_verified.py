import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.exporters'

"""Export the real map-stitching verification arrays to a browser-friendly scene.

Run from the repository root:
uv run --with numpy python tools/scene-studio/scripts/export_verified.py
Geometry and antenna configuration mirror output/verification/map-stitching/verify.py.
This exporter does not calculate or synthesize channel measurements.
"""
import json
from pathlib import Path
import numpy as np

from ..paths import WEB_ROOT, REPO_ROOT, TEST_SCENE_ROOT
APP = WEB_ROOT
ROOT = REPO_ROOT
SOURCE = TEST_SCENE_ROOT

def main():
    samples = np.load(SOURCE / 'samples.npz', allow_pickle=False)
    result = json.loads((SOURCE / 'results.json').read_text())
    buildings = []
    for prefix, offset in [('a', 0), ('b', 40)]:
        for direction, center, size in [
            ('north', [-22.5, 14, 6], [15, 12, 12]),
            ('south', [-20, -14, 4.5], [16, 12, 9]),
        ]:
            buildings.append(dict(id=f'{prefix}_{direction}', name=f'{prefix.upper()} · {"北侧" if direction == "north" else "南侧"}建筑', tileId=f'tile_{prefix}', position=[center[0] + offset, *center[1:]], size=size, material='concrete'))

    scene = dict(
        schemaVersion=1, name='双街区接缝场景', units='m', coordinateSystem='z-up',
        tiles=[dict(id='tile_a', name='街区 A', center=[-20, 0], size=[40, 50], color='#e0e8ed'), dict(id='tile_b', name='街区 B', center=[20, 0], size=[40, 50], color='#e5ecec')],
        buildings=buildings,
        transmitters=[dict(id='bs', name='BS-01', position=[-35, 0, 6])],
        receivers=[dict(id=f'ue_{i}', name=f'UE-{i+1:02}', position=p.tolist()) for i, p in enumerate(samples['static_positions'])],
        trajectory=dict(name='跨接缝位置序列', kind='sampled-positions', positions=[[float(x), 0, 1.5] for x in samples['trajectory_x']], results=dict(
            provenance=f'Sionna RT {result["sionna_rt"]} · scene-studio/data/scenes/test-4buildings/samples.npz', date='2026-10-25', carrierGHz=3.5, txAntennas=8, subcarriers=32,
            beamPowers=samples['beam_powers'].tolist(), bestBeams=samples['best_beams'].tolist(),
        )), resultsValid=True,
    )
    target=APP/'public/scenes/verified-street.json'
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(scene,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(target.relative_to(ROOT))


if __name__ == "__main__":
    main()
