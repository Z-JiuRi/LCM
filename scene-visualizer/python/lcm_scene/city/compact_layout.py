import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.city'

import math
import random

import numpy as np
from scipy.spatial import Voronoi
from shapely import affinity, get_parts, make_valid
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, split, unary_union


SIZE = 4000
SEED = 26102604
BOUNDARY = box(0, 0, SIZE, SIZE)
LABELS = [
    (2070, 2180, "Boston 核心街区"), (3040, 2970, "次级商务中心"),
    (1010, 3270, "大学 · 研究园区"), (840, 2040, "紧凑低层社区"),
    (1780, 790, "南部老街区"), (2790, 1800, "中高层组团"),
    (580, 3750, "北部居住社区"), (770, 690, "低层居住社区"),
    (3620, 700, "就业 · 服务园区"), (2170, 3670, "城市公园"),
    (1490, 1470, "混合商业街"), (3060, 3630, "北部中层社区"),
]
REGIONS = {
    "core": Polygon([(1530, 1820), (1840, 1630), (2540, 1770), (2700, 2230), (2450, 2620), (1740, 2720), (1470, 2270)]),
    "secondary": Polygon([(2680, 2700), (3080, 2500), (3490, 2820), (3450, 3210), (3090, 3410), (2650, 3150)]),
    "campus": Polygon([(520, 2900), (930, 2800), (1520, 3000), (1450, 3550), (900, 3660), (460, 3380)]),
    "employment": Polygon([(3340, 210), (4000, 120), (4000, 1310), (3540, 1440), (3210, 930)]),
    "towers": unary_union([Polygon([(2540, 1430), (2950, 1250), (3310, 1710), (3260, 2240), (2740, 2480), (2510, 2120)]), Polygon([(1560, 2800), (1920, 2670), (2390, 2980), (2490, 3300), (1940, 3340), (1540, 3160)])]),
    "fine": unary_union([Polygon([(250, 1780), (720, 1530), (1300, 1760), (1450, 2330), (1130, 2770), (330, 2590), (80, 2250)]), Polygon([(1250, 80), (2300, 60), (2670, 620), (2230, 1110), (1720, 1240), (1250, 980)])]),
    "lowrise": unary_union([Polygon([(0, 0), (1200, 0), (1290, 900), (890, 1370), (0, 1510)]), Polygon([(0, 3370), (550, 3420), (1300, 3660), (1470, 4000), (0, 4000)])]),
}
TRUNKS = [
    [(0, 350), (640, 680), (1120, 1070), (1540, 1510), (1750, 1870), (2220, 2330), (2720, 2800), (3240, 3200), (4000, 3570)],
    [(0, 2740), (650, 2620), (1120, 2340), (1620, 2290), (2130, 2510), (2710, 2500), (3380, 2260), (4000, 2020)],
    [(1250, 0), (1310, 500), (1590, 1050), (1680, 1700), (1860, 2310), (1740, 2970), (1510, 3490), (1640, 4000)],
    [(4000, 900), (3430, 1030), (2940, 1370), (2450, 1690), (1850, 1950), (1320, 1690), (710, 1620), (0, 1760)],
    [(0, 3550), (490, 3410), (860, 3060), (1520, 2940), (2190, 3050), (2920, 3510), (3560, 3620), (4000, 3740)],
    [(2710, 0), (2600, 480), (2770, 1040), (3170, 1700), (3370, 2260), (3480, 2770), (3380, 3390), (3560, 4000)],
    [(390, 0), (390, 710), (520, 1240), (710, 1620), (560, 2060), (650, 2620), (520, 3100), (240, 3650), (180, 4000)],
    [(4000, 3000), (3450, 2810), (2920, 2620), (2400, 2760), (2050, 3270), (2150, 4000)],
]


def polygons(shape):
    if isinstance(shape, Polygon):
        return [shape]
    return [part for part in get_parts(shape) if isinstance(part, Polygon)]


def smooth(points, rounds=2, closed=False):
    current = np.asarray(points, dtype=float)
    if closed and np.allclose(current[0], current[-1]):
        current = current[:-1]
    for _ in range(rounds):
        result = [] if closed else [current[0]]
        pairs = zip(current, np.roll(current, -1, axis=0)) if closed else zip(current[:-1], current[1:])
        for first, second in pairs:
            result.extend([first * .75 + second * .25, first * .25 + second * .75])
        if not closed:
            result.append(current[-1])
        current = np.asarray(result)
    return np.vstack([current, current[0]]) if closed else current


def role_at(east, north):
    point = Point(east, north)
    for role, shape in REGIONS.items():
        if shape.contains(point):
            return role
    if any(LineString(points).distance(point) < 130 for points in TRUNKS[:4]):
        return "mixed"
    return "midrise"


def preserve_group(source, center, angle, source_assets):
    candidates = source_assets[source]
    source_shapes = [affinity.translate(asset["footprint"], *asset["source_origin_m"][:2]) for asset in candidates]
    bounds = unary_union(source_shapes).bounds
    origin = ((bounds[0] + bounds[2]) / 2, (bounds[1] + bounds[3]) / 2)
    cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    placements = []
    rejected_overlaps = []
    for asset in sorted(candidates, key=lambda item: item["area"], reverse=True):
        difference_x = asset["source_origin_m"][0] - origin[0]
        difference_y = asset["source_origin_m"][1] - origin[1]
        east = center[0] + cosine * difference_x - sine * difference_y
        north = center[1] + sine * difference_x + cosine * difference_y
        footprint = affinity.translate(affinity.rotate(asset["footprint"], angle, origin=(0, 0)), east, north)
        if any(footprint.intersection(placed["footprint"]).area > .001 for placed in placements):
            rejected_overlaps.append(asset["source_object_index"])
            continue
        placements.append({"asset": asset, "position": [east, north], "angle": angle, "footprint": footprint})
    envelope = unary_union([placement["footprint"] for placement in placements]).convex_hull.buffer(34, join_style=1)
    return {"source": source, "shape": envelope, "placements": placements, "source_center_m": origin, "target_center_m": center, "rotation_z_deg": angle, "overlapping_source_objects_excluded": rejected_overlaps}


def source_gap_corridors(group):
    samples = []
    owners = []
    for index, placement in enumerate(group["placements"]):
        ring = placement["footprint"].exterior
        for distance in np.arange(0, ring.length, 10):
            samples.append(ring.interpolate(distance).coords[0])
            owners.append(index)
    if len(samples) < 4:
        return []
    diagram = Voronoi(samples)
    obstacle = unary_union([placement["footprint"].buffer(5.5) for placement in group["placements"]])
    open_area = group["shape"].buffer(9).difference(obstacle)
    result = []
    for owners_pair, vertex_indices in zip(diagram.ridge_points, diagram.ridge_vertices):
        if -1 in vertex_indices or owners[owners_pair[0]] == owners[owners_pair[1]]:
            continue
        segment = LineString(diagram.vertices[vertex_indices]).intersection(open_area)
        for part in get_parts(segment):
            if isinstance(part, LineString) and part.length > 1:
                result.append({"line": part, "width": 7 if group["source"] == "boston5g_3p5" else 5, "kind": "inferred-passage"})
    return result


def create_layout(source_assets):
    rng = random.Random(SEED)
    groups = [preserve_group("boston5g_3p5", (2070, 2180), -17, source_assets), preserve_group("asu_campus_3p5", (1010, 3270), 14, source_assets)]
    group_mask = unary_union([group["shape"] for group in groups])
    green_path = LineString(smooth([(3130, 0), (3020, 420), (3430, 1050), (3280, 1640), (3480, 2050), (3810, 2620), (4000, 3050)]))
    park_outlines = [
        [(1890, 3390), (2230, 3260), (2470, 3440), (2560, 3730), (2390, 4000), (2000, 3900), (1790, 3630)],
        [(220, 2700), (450, 2790), (680, 2710), (690, 2460), (510, 2370), (300, 2460)],
        [(2100, 1160), (2350, 1080), (2590, 1210), (2570, 1440), (2380, 1580), (2160, 1470)],
        [(100, 870), (240, 960), (270, 1250), (130, 1420), (0, 1310), (0, 960)],
    ]
    parks = unary_union([green_path.buffer(57), *[Polygon(smooth(points, closed=True)) for points in park_outlines]]).intersection(BOUNDARY).difference(group_mask.buffer(18))
    roads = []
    for index, points in enumerate(TRUNKS):
        centerline = LineString(smooth(points)).intersection(BOUNDARY).difference(group_mask)
        for part in get_parts(centerline):
            if isinstance(part, LineString) and part.length > 5:
                roads.append({"line": part, "width": 26 if index < 4 else 20, "kind": "arterial" if index < 4 else "collector"})
    for group in groups:
        roads.append({"line": LineString(group["shape"].exterior.coords), "width": 16, "kind": "collector"})
    primary_network = unary_union([road["line"] for road in roads] + [BOUNDARY.boundary])
    districts = sorted(polygonize(primary_network), key=lambda part: (part.centroid.y, part.centroid.x))
    leaves = []

    def subdivide(shape, depth, district_index, preferred_angle=None):
        center = shape.representative_point()
        role = role_at(center.x, center.y)
        target = {"core": 26000, "secondary": 26000, "towers": 36000, "midrise": 26000, "mixed": 20000, "fine": 14500, "lowrise": 20000, "campus": 38000, "employment": 37000}[role]
        rectangle = list(shape.minimum_rotated_rectangle.exterior.coords)
        edges = [(math.dist(first, second), math.degrees(math.atan2(second[1] - first[1], second[0] - first[0]))) for first, second in zip(rectangle, rectangle[1:])]
        longest, axis = max(edges)
        shortest = min(length for length, _ in edges)
        local_angle = axis if preferred_angle is None else preferred_angle
        if depth > 8 or shape.area < target * rng.uniform(1.15, 1.85) or shortest < 95:
            leaves.append({"shape": shape, "role": role, "angle": local_angle, "district": district_index})
            return
        for attempt in range(5):
            cut_angle = axis + 90 + rng.uniform(-18, 18)
            direction = np.array([math.cos(math.radians(cut_angle)), math.sin(math.radians(cut_angle))])
            normal = np.array([-direction[1], direction[0]])
            origin = np.array(shape.centroid.coords[0]) + normal * rng.uniform(-.13, .13) * longest
            bending = normal * rng.uniform(-13, 13)
            cutting_line = LineString([origin - direction * 12000, origin + bending, origin + direction * 12000])
            pieces = polygons(split(shape, cutting_line))
            if len(pieces) != 2 or min(piece.area for piece in pieces) < target * .23:
                continue
            street = cutting_line.intersection(shape)
            for part in get_parts(street):
                if isinstance(part, LineString) and part.length > 3:
                    roads.append({"line": part, "width": 10 if role in ("fine", "lowrise") else 13, "kind": "street"})
            for piece in pieces:
                subdivide(piece, depth + 1, district_index, local_angle + rng.uniform(-4, 4))
            return
        leaves.append({"shape": shape, "role": role, "angle": local_angle, "district": district_index})

    for district_index, district in enumerate(districts):
        if group_mask.covers(district.representative_point()):
            continue
        for part in polygons(make_valid(district.difference(parks))):
            if part.area > 1000:
                subdivide(part, 0, district_index)
    road_mask = unary_union([road["line"].buffer(road["width"] / 2 + 2.5, cap_style=2) for road in roads])
    parcels = []
    for leaf in leaves:
        shape = leaf["shape"].difference(road_mask).difference(group_mask).buffer(-2)
        for part in polygons(make_valid(shape)):
            if part.area > 1000:
                point = part.representative_point()
                parcels.append({**leaf, "shape": part, "role": role_at(point.x, point.y)})
    for group in groups:
        parcels.append({"shape": group["shape"].buffer(-11), "role": "core" if group["source"] == "boston5g_3p5" else "campus", "angle": group["rotation_z_deg"], "district": -1, "preserved_group": group})
        roads.extend(source_gap_corridors(group))
    return roads, parks, parcels, green_path
