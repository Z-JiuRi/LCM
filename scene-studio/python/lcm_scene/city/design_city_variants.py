import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.city'

"""Independent metric 1 km and 2 km designs using existing preview-derived assets.
Run from repository root with uv run --with numpy --with scipy --with pillow --with shapely python ...
"""
import argparse
import gzip
import json
import math
import random
from collections import Counter
from pathlib import Path

import numpy as np
from shapely import affinity, get_parts, make_valid
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, split, unary_union

from . import assemble_city as core
from .compact_layout import polygons, preserve_group, smooth, source_gap_corridors

from ..paths import CITY_ROOT
ROOT = CITY_ROOT


def layout(size, source_assets, seed):
    boundary = box(0, 0, size, size)
    rng = random.Random(seed)
    if size == 1000:
        # A compact, whole-building subset: never scale or cut a source building.
        group = preserve_group('boston5g_3p5', (570, 550), -12, source_assets)
        selection = box(400, 395, 750, 705)
        group['placements'] = [p for p in group['placements'] if selection.covers(p['footprint'])]
        group['shape'] = unary_union([p['footprint'] for p in group['placements']]).convex_hull.buffer(23)
        group['selection_note'] = 'Whole-building compact subset within target window [400,395,750,705] m; not the full Boston group.'
        groups = [group]
        trunks = [([(0, 320), (260, 380), (540, 330), (800, 350), (1000, 450)], 22),
                  ([(300, 0), (340, 250), (340, 550), (300, 800), (390, 1000)], 22),
                  ([(0, 800), (260, 735), (530, 790), (770, 770), (1000, 880)], 18),
                  ([(840, 0), (790, 240), (820, 500), (840, 750), (790, 1000)], 18),
                  ([(0, 100), (250, 210), (610, 180), (1000, 250)], 16)]
        park_points = [[(70, 850), (200, 805), (265, 865), (225, 970), (70, 960)],
                       [(470, 40), (610, 35), (670, 130), (565, 175), (465, 120)]]
        green_points = [(980, 0), (940, 240), (935, 500), (975, 730), (1000, 1000)]
        labels = [(565, 560, '紧凑商务核心'), (160, 540, '低层生活街区'),
                  (550, 880, '中高层住宅'), (600, 245, '混合商业街'),
                  (160, 920, '社区公园'), (885, 610, '绿廊住区')]
        regions = {'fine': box(0, 260, 280, 790), 'lowrise': box(0, 0, 290, 250),
                   'towers': box(350, 780, 810, 1000), 'mixed': box(300, 0, 850, 350)}
        green_width = 23
    else:
        groups = [preserve_group('boston5g_3p5', (1110, 1000), -12, source_assets),
                  preserve_group('asu_campus_3p5', (470, 1580), 8, source_assets)]
        trunks = [([(0, 410), (430, 510), (870, 440), (1420, 520), (2000, 690)], 26),
                  ([(560, 0), (650, 430), (600, 850), (550, 1150), (900, 1550), (970, 2000)], 24),
                  ([(0, 1090), (410, 1200), (860, 1380), (1420, 1350), (2000, 1510)], 24),
                  ([(1720, 0), (1590, 510), (1660, 990), (1610, 1460), (1780, 2000)], 22),
                  ([(0, 180), (530, 220), (1100, 210), (1570, 320), (2000, 260)], 18),
                  ([(0, 780), (400, 800), (770, 620), (1330, 660), (2000, 920)], 18),
                  ([(0, 1920), (520, 1880), (1020, 1740), (1500, 1820), (2000, 1750)], 18),
                  ([(220, 0), (250, 530), (300, 970), (130, 1360), (150, 2000)], 18)]
        park_points = [[(1110, 1570), (1350, 1530), (1490, 1630), (1450, 1880), (1210, 1940), (1080, 1780)],
                       [(60, 870), (190, 830), (340, 910), (300, 1090), (90, 1080)],
                       [(910, 40), (1070, 50), (1190, 160), (1060, 330), (900, 270)]]
        green_points = [(1910, 0), (1830, 490), (1850, 870), (1930, 1180), (1860, 1570), (1990, 2000)]
        labels = [(1110, 1000, 'Boston 商务核心'), (470, 1580, '大学 · 研究园区'),
                  (350, 590, '紧凑低层社区'), (380, 170, '低层居住区'),
                  (1300, 1730, '城市公园'), (1450, 1460, '次级商业中心'),
                  (1470, 360, '中高层住宅'), (1710, 1120, '绿廊混合住区')]
        regions = {'campus': box(0, 1250, 840, 2000), 'fine': box(0, 360, 550, 1200),
                   'lowrise': box(0, 0, 600, 350), 'secondary': box(1300, 1250, 1800, 1740),
                   'towers': box(1150, 0, 1790, 650), 'mixed': box(600, 0, 1150, 600)}
        green_width = 38
    for group in groups:
        assert boundary.covers(group['shape']), group['source']
    group_mask = unary_union([g['shape'] for g in groups])
    green_path = LineString(smooth(green_points))
    parks = unary_union([green_path.buffer(green_width), *[Polygon(smooth(p, closed=True)) for p in park_points]]).intersection(boundary).difference(group_mask.buffer(15))
    roads = []
    for index, (points, width) in enumerate(trunks):
        line = LineString(smooth(points)).intersection(boundary).difference(group_mask)
        for part in get_parts(line):
            if isinstance(part, LineString) and part.length > 3:
                roads.append({'line': part, 'width': width, 'kind': 'arterial' if index < 3 else 'collector'})
    for group in groups:
        roads.append({'line': LineString(group['shape'].exterior.coords), 'width': 14, 'kind': 'collector'})
    def role_at(point):
        for role, shape in regions.items():
            if shape.covers(point):
                return role
        return 'midrise'
    districts = sorted(polygonize(unary_union([r['line'] for r in roads] + [boundary.boundary])), key=lambda p: (p.centroid.y, p.centroid.x))
    leaves = []
    def subdivide(shape, depth, district, preferred=None):
        role = role_at(shape.representative_point())
        target = {'fine': 11000, 'lowrise': 14500, 'mixed': 14000, 'midrise': 17000, 'secondary': 19000, 'towers': 23000, 'campus': 23000}[role]
        coords = list(shape.minimum_rotated_rectangle.exterior.coords)
        edges = [(math.dist(a, b), math.degrees(math.atan2(b[1]-a[1], b[0]-a[0]))) for a, b in zip(coords, coords[1:])]
        longest, axis = max(edges)
        angle = axis if preferred is None else preferred
        if depth >= 9 or shape.area < target*rng.uniform(1.15, 1.7) or min(e[0] for e in edges) < 72:
            leaves.append({'shape': shape, 'role': role, 'angle': angle, 'district': district})
            return
        for _ in range(6):
            theta = math.radians(axis+90+rng.uniform(-15,15))
            direction = np.array([math.cos(theta), math.sin(theta)])
            normal = np.array([-direction[1], direction[0]])
            origin = np.array(shape.centroid.coords[0])+normal*rng.uniform(-.12,.12)*longest
            cut = LineString([origin-direction*size*3, origin+normal*rng.uniform(-8,8), origin+direction*size*3])
            pieces = polygons(split(shape, cut))
            if len(pieces) != 2 or min(p.area for p in pieces) < target*.25:
                continue
            for part in get_parts(cut.intersection(shape)):
                if isinstance(part, LineString) and part.length > 3:
                    roads.append({'line': part, 'width': 9 if role in ('fine','lowrise') else 11, 'kind': 'street'})
            for piece in pieces:
                subdivide(piece, depth+1, district, angle+rng.uniform(-3,3))
            return
        leaves.append({'shape': shape, 'role': role, 'angle': angle, 'district': district})
    for index, district in enumerate(districts):
        if group_mask.covers(district.representative_point()):
            continue
        for part in polygons(make_valid(district.difference(parks))):
            if part.area > 800:
                subdivide(part, 0, index)
    mask = unary_union([r['line'].buffer(r['width']/2+2.5, cap_style=2) for r in roads])
    parcels = []
    for leaf in leaves:
        for part in polygons(make_valid(leaf['shape'].difference(mask).difference(group_mask).buffer(-2))):
            if part.area > 800:
                parcels.append({**leaf, 'shape':part, 'role':role_at(part.representative_point())})
    for group in groups:
        parcels.append({'shape':group['shape'].buffer(-9), 'role':'campus' if group['source']=='asu_campus_3p5' else 'core', 'angle':group['rotation_z_deg'], 'district':-1, 'preserved_group':group})
        roads.extend(source_gap_corridors(group))
    return boundary, roads, parks, parcels, green_path, labels


def build(size, assets, source_assets, rejected):
    seed = 26102600 + size//1000
    output = ROOT/f'city-{size//1000}km'
    output.mkdir(exist_ok=True)
    boundary, roads, parks, parcels, green_path, labels = layout(size, source_assets, seed)
    core.RNG = random.Random(seed)
    core.BOUNDARY = boundary
    print(f'Building {size} m design: {len(parcels)} parcels', flush=True)
    instances, footprints, usage = core.assemble(assets, source_assets, parcels)
    qa = core.validate(assets, instances, footprints, parcels, roads, parks)
    qa['outside_city_buildings'] = sum(not boundary.buffer(.001).covers(f) for f in footprints)
    for key in ('building_overlap_pairs','outside_parcel_buildings','buildings_intersecting_road_carriageways','buildings_intersecting_parks','outside_city_buildings'):
        assert qa[key] == 0, qa
    used = {i['asset'] for i in instances}
    groups = [{k:v for k,v in p['preserved_group'].items() if k not in ('shape','placements')} | {'retained_object_count':len(p['preserved_group']['placements'])} for p in parcels if 'preserved_group' in p]
    manifest = {'date':'2026-10-26','seed':seed,'units':'m','extent_m':[0,0,size,size],
                'coordinate_system':'local Cartesian; X east, Y north, Z up',
                'status':'Synthetic city design from preview-derived geometry, not validated RT.',
                'reference':'../README.md; original 4 km city retained unchanged',
                'layout':'Independent metric road/park/parcel design; source buildings are not scaled.',
                'transform':'world_xyz = Rz(rotation_z_deg) @ asset_local_xyz + position_m; no scaling',
                'source_snapshot_date':'2026-10-25','source_license_status':'Original terms apply; full reuse/redistribution audit pending.',
                'synthetic_components':['roads','parks','ground','parcels','instance placement'],
                'excluded_components':['source terrain','source materials','TX/RX','channels'],
                'asset_count':len(used),'instance_count':len(instances),'source_usage':dict(usage),
                'placement_counts':dict(Counter(i['placement'] for i in instances)),
                'rejected_source_objects':dict(rejected),'preserved_groups':groups,'validation':qa}
    geometry = [{k:v for k,v in a.items() if k not in ('footprint','orientation')} | {'footprint':core.serialize_polygon(a['footprint'])} for a in assets if a['id'] in used]
    scene = {'manifest':manifest,'assets':geometry,'instances':instances,
             'roads':[{'points':np.round(np.asarray(r['line'].coords),3).tolist(),'width_m':r['width'],'kind':r['kind']} for r in roads],
             'parks':[core.serialize_polygon(p) for p in polygons(parks)],
             'parcels':[{'footprint':core.serialize_polygon(p['shape']),'role':p['role']} for p in parcels],
             'ground':{'extent_m':[0,0,size,size],'elevation_m':0},'green_path':np.round(np.asarray(green_path.coords),3).tolist()}
    (output/'assembled-city.scene.json.gz').write_bytes(gzip.compress(json.dumps(scene,ensure_ascii=False,separators=(',',':')).encode(),mtime=0))
    (output/'assembled-city-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    view = {'manifest':manifest,'buildings':[{'points':np.round(np.asarray(f.exterior.coords),3).tolist(),'holes':[np.round(np.asarray(h.coords),3).tolist() for h in f.interiors], 'height':round(assets[i['asset']]['height_m'],2),'source':assets[i['asset']]['source'],'object':assets[i['asset']]['source_object_index'],'parcel':i['parcel']} for i,f in zip(instances,footprints)],'roads':scene['roads'],'parks':scene['parks'],'labels':labels}
    (output/'assembled-city.view.json').write_text(json.dumps(view,ensure_ascii=False,separators=(',',':')))
    # Reuse the inspected viewer template; only dimension/title/cache key changes.
    html = (ROOT/'city-viewer.html').read_text()
    title = '一公里' if size == 1000 else '两公里'
    html = html.replace('四公里',title).replace('4×4公里',f'{size//1000}×{size//1000}公里').replace('4 × 4 km',f'{size//1000} × {size//1000} km')
    html = html.replace('citySize=4000',f'citySize={size}').replace('centerX=2000, centerY=2000',f'centerX={size/2}, centerY={size/2}').replace('compact4',f'design{size}')
    (output/'city-viewer.html').write_text(html)
    from .render_city_variants import render_city
    render_city(output,size,seed,labels,assets,instances,footprints,roads,parks,green_path,qa)
    print(json.dumps({'size':size,'instances':len(instances),'sources':len(usage),'validation':qa},ensure_ascii=False,indent=2),flush=True)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size',type=int,choices=[1000,2000],action='append')
    args = parser.parse_args()
    assets, source_assets, rejected = core.load_assets()
    for size in args.size or [1000,2000]:
        build(size,assets,source_assets,rejected)


if __name__ == '__main__':
    main()
