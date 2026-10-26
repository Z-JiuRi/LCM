import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.city'

"""Validate saved, rounded exports independently of generation geometries."""
import gzip
import json
from pathlib import Path
from shapely import affinity
from shapely.geometry import Polygon, LineString, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

from ..paths import CITY_ROOT
ROOT = CITY_ROOT


def validate(directory, write_report=True):
    directory = Path(directory)
    scene = json.loads(gzip.decompress((directory/'assembled-city.scene.json.gz').read_bytes()))
    assets = {a['id']:a for a in scene['assets']}
    poly = lambda p: Polygon(p['outer'], p['holes'])
    footprints = []
    for instance in scene['instances']:
        shape = poly(assets[instance['asset']]['footprint'])
        shape = affinity.rotate(shape,instance['rotation_z_deg'],origin=(0,0))
        footprints.append(affinity.translate(shape,*instance['position_m'][:2]))
    assert all(f.is_valid for f in footprints)
    boundary = box(*scene['ground']['extent_m'])
    parcels = [poly(p['footprint']) for p in scene['parcels']]
    roads = unary_union([LineString(r['points']).buffer(r['width_m']/2,cap_style=2) for r in scene['roads']]).intersection(boundary)
    parks = unary_union([poly(p) for p in scene['parks']])
    tree = STRtree(footprints)
    result = {
        'instance_count':len(footprints),
        'building_overlap_pairs':sum(f.intersection(footprints[j]).area > .01 for i,f in enumerate(footprints) for j in tree.query(f,predicate='intersects') if j>i),
        'outside_city_buildings':sum(not boundary.buffer(.002).covers(f) for f in footprints),
        'outside_parcel_buildings':sum(not parcels[i['parcel']].buffer(.002).covers(f) for i,f in zip(scene['instances'],footprints)),
        'buildings_intersecting_road_carriageways':sum(f.intersection(roads).area > .01 for f in footprints if roads.intersects(f)),
        'buildings_intersecting_parks':sum(f.intersection(parks).area > .01 for f in footprints if parks.intersects(f)),
        'scope':'Saved rounded 2D geometries; area threshold 0.01 m2; boundary tolerance 0.002 m. No 3D/RT verification.'}
    for k,v in result.items():
        if k not in ('instance_count','scope'):
            assert v == 0,(directory,k,v)
    if write_report:
        (directory/'export-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(directory.name,result)
    return result


def main():
    import argparse
    from ..paths import city_directory
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', type=int, choices=(1000, 2000, 4000), action='append')
    parser.add_argument('--no-write', action='store_true')
    args = parser.parse_args()
    return {size: validate(city_directory(size), write_report=not args.no_write)
            for size in args.size or (1000, 2000, 4000)}


if __name__ == '__main__':
    main()
