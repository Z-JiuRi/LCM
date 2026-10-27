import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.city'

import argparse
import gzip
import hashlib
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely import affinity, get_parts, make_valid, prepare
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

from .screen_city_sources import CACHE, GROUPS
from .compact_layout import BOUNDARY, LABELS, SEED, SIZE, create_layout


from ..paths import CITY_ROOT
OUTPUT = CITY_ROOT
RNG = random.Random(SEED)
FAMILIES = {key[0]: names for key, names in GROUPS.items()}
ROLE_FAMILIES = {
    "core": "AACB", "secondary": "CCBE", "towers": "BBHE",
    "midrise": "DDHHE", "mixed": "EECD", "fine": "FFFGE",
    "lowrise": "GGGGF", "campus": "IIIHE", "employment": "JJHE",
}
ROLE_TARGETS = {"core": .48, "secondary": .44, "towers": .36, "midrise": .45, "mixed": .43, "fine": .44, "lowrise": .32, "campus": .28, "employment": .38}


def polygon_parts(geometry):
    if isinstance(geometry, Polygon):
        return [geometry]
    return [part for part in get_parts(geometry) if isinstance(part, Polygon)]


def load_assets():
    assets = []
    source_assets = defaultdict(list)
    rejected = Counter()
    for source in [name for names in FAMILIES.values() for name in names]:
        raw = json.loads(gzip.decompress((CACHE / f"{source}.json.gz").read_bytes()))
        seen = set()
        for object_index, building in enumerate(raw.get("buildings", [])):
            faces = []
            for face in building:
                cleaned = [point for point in face]
                while cleaned and cleaned[-1] == [0, 0, 0]:
                    cleaned.pop()
                if len(cleaned) >= 3:
                    faces.append(np.asarray(cleaned, dtype=float))
            if not faces:
                continue
            points = np.concatenate(faces)
            height = float(np.ptp(points[:, 2]))
            if height < 2.5:
                continue
            signature = hashlib.sha256(np.unique(np.round(points, 4), axis=0).astype("<f8").tobytes()).hexdigest()
            if signature in seen:
                rejected["duplicate_source_object"] += 1
                continue
            seen.add(signature)
            projected = []
            for face in faces:
                shape = make_valid(Polygon(face[:, :2]))
                projected.extend(part for part in polygon_parts(shape) if part.area > .1)
            shape = unary_union(projected)
            if not isinstance(shape, Polygon) or not shape.is_valid:
                rejected["non_single_valid_footprint"] += 1
                continue
            minimum_x, minimum_y, maximum_x, maximum_y = shape.bounds
            if not 22 < shape.area < 25000 or max(maximum_x - minimum_x, maximum_y - minimum_y) > 300:
                rejected["size_gate"] += 1
                continue
            center_x, center_y = shape.centroid.coords[0]
            base_z = float(points[:, 2].min())
            normalized = affinity.translate(shape, -center_x, -center_y)
            rectangle = list(shape.minimum_rotated_rectangle.exterior.coords)
            edges = [(math.dist(first, second), math.atan2(second[1] - first[1], second[0] - first[0])) for first, second in zip(rectangle, rectangle[1:])]
            orientation = math.degrees(max(edges)[1]) % 90
            asset = {
                "id": len(assets), "source": source, "source_object_index": object_index,
                "source_origin_m": [center_x, center_y, base_z], "height_m": height,
                "footprint": normalized, "area": shape.area, "orientation": orientation,
                "faces": [np.round(face - np.array([center_x, center_y, base_z]), 4).tolist() for face in faces],
            }
            assets.append(asset)
            source_assets[source].append(asset)
    return assets, source_assets, rejected


def assemble(assets, source_assets, parcels):
    instances = []
    footprints = []
    usable_sources = {family: [source for source in sources if source_assets[source]] for family, sources in FAMILIES.items()}
    rotated_cache = {}
    source_usage = Counter()
    module_counter = 0
    for parcel_index, parcel in enumerate(parcels):
        shape = parcel["shape"]
        prepare(shape)
        role = parcel["role"]
        center = shape.centroid
        role_sources = list(dict.fromkeys(source for family in ROLE_FAMILIES[role] for source in usable_sources[family]))
        if "preserved_group" not in parcel:
            role_sources = [source for source in role_sources if source != "boston5g_3p5"]
        source = role_sources[(parcel_index // 3) % len(role_sources)]
        occupied = defaultdict(list)
        placed = []
        placed_area = 0
        target_area = shape.area * ROLE_TARGETS[role]

        def transform_asset(asset, angle):
            key = (asset["id"], round(angle, 3))
            if key not in rotated_cache:
                rotated_cache[key] = affinity.rotate(asset["footprint"], angle, origin=(0, 0))
            return rotated_cache[key]

        def place(asset, east, north, angle, mode, module_id):
            nonlocal placed_area
            candidate = affinity.translate(transform_asset(asset, angle), east, north)
            if not shape.contains(candidate):
                return False
            clearance = candidate.buffer(1.6, join_style=2)
            minimum_x, minimum_y, maximum_x, maximum_y = clearance.bounds
            bins = [(column, row) for column in range(math.floor(minimum_x / 35), math.floor(maximum_x / 35) + 1) for row in range(math.floor(minimum_y / 35), math.floor(maximum_y / 35) + 1)]
            neighbors = {index for key in bins for index in occupied[key]}
            if any(clearance.intersects(placed[index]) for index in neighbors):
                return False
            local_index = len(placed)
            placed.append(candidate)
            for key in bins:
                occupied[key].append(local_index)
            placed_area += candidate.area
            source_usage[asset["source"]] += 1
            instances.append({"asset": asset["id"], "position_m": [round(east, 3), round(north, 3), 0], "rotation_z_deg": round(angle, 3), "parcel": parcel_index, "role": role, "placement": mode, "module": module_id})
            footprints.append(candidate)
            return True

        if "preserved_group" in parcel:
            module_counter += 1
            for placement in parcel["preserved_group"]["placements"]:
                candidate = placement["footprint"]
                assert shape.covers(candidate)
                asset = placement["asset"]
                source_usage[asset["source"]] += 1
                instances.append({"asset": asset["id"], "position_m": [round(value, 6) for value in placement["position"]] + [0], "rotation_z_deg": placement["angle"], "parcel": parcel_index, "role": role, "placement": "preserved-source-group", "module": module_counter})
                footprints.append(candidate)
                placed_area += candidate.area
            parcel["building_area_m2"] = placed_area
            print(f"Preserved {parcel['preserved_group']['source']}: {len(parcel['preserved_group']['placements'])} objects", flush=True)
            continue

        for attempt in range(4):
            if placed_area >= target_area:
                break
            if attempt:
                source = RNG.choice(role_sources)
            candidates = source_assets[source]
            anchor = RNG.choice(candidates)
            angle = parcel["angle"] - anchor["orientation"] + (90 if attempt % 2 else 0)
            cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
            anchor_x, anchor_y = anchor["source_origin_m"][:2]
            anchor_target_x = center.x + RNG.uniform(-35, 35)
            anchor_target_y = center.y + RNG.uniform(-35, 35)
            module_counter += 1
            ordered = sorted(candidates, key=lambda asset: (asset["source_origin_m"][0] - anchor_x) ** 2 + (asset["source_origin_m"][1] - anchor_y) ** 2)
            for asset in ordered:
                difference_x, difference_y = asset["source_origin_m"][0] - anchor_x, asset["source_origin_m"][1] - anchor_y
                if abs(difference_x) + abs(difference_y) > 800:
                    continue
                east = anchor_target_x + cosine * difference_x - sine * difference_y
                north = anchor_target_y + sine * difference_x + cosine * difference_y
                place(asset, east, north, angle, "source-neighborhood", module_counter)
                if placed_area >= target_area:
                    break

        local_shape = affinity.rotate(shape, -parcel["angle"], origin=(center.x, center.y))
        minimum_x, minimum_y, maximum_x, maximum_y = local_shape.bounds
        infill = [asset for source in role_sources for asset in source_assets[source] if asset["area"] < min(4000, shape.area * .18)]
        if not infill:
            infill = [asset for source in FAMILIES["E"] for asset in source_assets[source] if asset["area"] < 1200]
        spacing = 17 if role in ("fine", "lowrise") else 26
        anchors = [(east + RNG.uniform(-4, 4), north + RNG.uniform(-4, 4)) for east in np.arange(minimum_x + 12, maximum_x - 8, spacing) for north in np.arange(minimum_y + 12, maximum_y - 8, spacing)]
        RNG.shuffle(anchors)
        cosine, sine = math.cos(math.radians(parcel["angle"])), math.sin(math.radians(parcel["angle"]))
        for local_x, local_y in anchors:
            if placed_area >= target_area:
                break
            east = center.x + cosine * (local_x - center.x) - sine * (local_y - center.y)
            north = center.y + sine * (local_x - center.x) + cosine * (local_y - center.y)
            for attempt in range(2):
                asset = RNG.choice(infill)
                angle = parcel["angle"] - asset["orientation"] + (90 if attempt else 0)
                if place(asset, east, north, angle, "recomposed-infill", None):
                    break
        parcel["building_area_m2"] = placed_area
        if parcel_index % 100 == 0:
            print(f"Parcels {parcel_index}/{len(parcels)}; buildings {len(instances)}", flush=True)
    return instances, footprints, source_usage


def serialize_polygon(shape):
    return {"outer": np.round(np.asarray(shape.exterior.coords), 3).tolist(), "holes": [np.round(np.asarray(ring.coords), 3).tolist() for ring in shape.interiors]}


def validate(assets, instances, footprints, parcels, roads, parks):
    tree = STRtree(footprints)
    overlapping_pairs = 0
    for index, footprint in enumerate(footprints):
        for other in tree.query(footprint, predicate="intersects"):
            if other > index and footprint.intersection(footprints[other]).area > .01:
                overlapping_pairs += 1
    outside = sum(not parcels[instance["parcel"]]["shape"].buffer(.001).covers(footprint) for instance, footprint in zip(instances, footprints))
    road_mask = unary_union([road["line"].buffer(road["width"] / 2, cap_style=2) for road in roads]).intersection(BOUNDARY)
    prepare(road_mask)
    road_intrusions = sum(footprint.intersection(road_mask).area > .01 for footprint in footprints if road_mask.intersects(footprint))
    park_intrusions = sum(footprint.intersection(parks).area > .01 for footprint in footprints if parks.intersects(footprint))
    role_areas = defaultdict(lambda: {"parcel_area_km2": 0, "building_area_km2": 0, "parcels": 0})
    for parcel in parcels:
        stats = role_areas[parcel["role"]]
        stats["parcel_area_km2"] += parcel["shape"].area / 1e6
        stats["building_area_km2"] += parcel["building_area_m2"] / 1e6
        stats["parcels"] += 1
    return {
        "building_overlap_pairs": overlapping_pairs, "outside_parcel_buildings": outside,
        "buildings_intersecting_road_carriageways": road_intrusions,
        "buildings_intersecting_parks": park_intrusions,
        "building_footprint_area_km2": round(sum(footprint.area for footprint in footprints) / 1e6, 4),
        "road_carriageway_union_km2": round(road_mask.area / 1e6, 4),
        "large_park_area_excluding_carriageways_km2": round(parks.difference(road_mask).area / 1e6, 4),
        "role_areas": role_areas,
        "scope": "2D complete-footprint placement and overlap checks only; no RT, watertight mesh, road routing or electromagnetic validation.",
    }


def render(assets, instances, footprints, roads, parks, green_path, qa):
    pixels = 6400
    margin, header, footer = 155, 250, 255
    image = Image.new("RGB", (pixels + margin * 2, pixels + header + footer), "#f7f6f0")
    draw = ImageDraw.Draw(image)
    font_path = "/System/Library/Fonts/Hiragino Sans GB.ttc"
    font = lambda size: ImageFont.truetype(font_path, size)
    scale = pixels / SIZE

    def project(point):
        return (margin + point[0] * scale, header + (SIZE - point[1]) * scale)

    def draw_polygon(shape, fill, outline=None):
        draw.polygon([project(point) for point in shape.exterior.coords], fill=fill, outline=outline)
        for ring in shape.interiors:
            draw.polygon([project(point) for point in ring.coords], fill="#e4e8de")

    draw.rectangle((margin, header, margin + pixels, header + pixels), fill="#e4e8de")
    for part in polygon_parts(parks):
        draw_polygon(part, "#c3d5b8")
    for road in roads:
        if road["kind"] == "street":
            points = [project(point) for point in road["line"].coords]
            draw.line(points, fill="#c4c9c4", width=max(1, round((road["width"] + 5) * scale)), joint="curve")
            draw.line(points, fill="#f7f5ec", width=max(1, round(road["width"] * scale)), joint="curve")
    for road in roads:
        if road["kind"] != "street":
            points = [project(point) for point in road["line"].coords]
            draw.line(points, fill="#bac2bc", width=round((road["width"] + 9) * scale), joint="curve")
            draw.line(points, fill="#f8f6ed", width=round(road["width"] * scale), joint="curve")
            draw.line(points, fill="#d3dbc8", width=max(1, round(3 * scale)), joint="curve")
    for part in get_parts(green_path.intersection(parks)):
        if isinstance(part, LineString):
            draw.line([project(point) for point in part.coords], fill="#ede8d0", width=5)
    tree_rng = random.Random(SEED + 1)
    park_prepared = parks.buffer(-12)
    prepare(park_prepared)
    for _ in range(34000):
        east, north = tree_rng.uniform(0, SIZE), tree_rng.uniform(0, SIZE)
        if park_prepared.contains(Point(east, north)):
            projected_x, projected_y = project((east, north))
            radius = tree_rng.uniform(2.2, 4.2)
            draw.ellipse((projected_x - radius, projected_y - radius, projected_x + radius, projected_y + radius), fill=tree_rng.choice(["#adc69e", "#9fba94", "#b4cba7"]))
    order = sorted(range(len(instances)), key=lambda index: assets[instances[index]["asset"]]["height_m"])
    for index in order:
        height = assets[instances[index]["asset"]]["height_m"]
        if height > 16:
            shadow = affinity.translate(footprints[index], height * .28, -height * .42)
            draw_polygon(shadow, "#bac1b9")
    for index in order:
        height = assets[instances[index]["asset"]]["height_m"]
        color = "#adb9bd" if height < 12 else "#90a6ad" if height < 25 else "#698891" if height < 60 else "#3f626e" if height < 120 else "#244b5b"
        draw_polygon(footprints[index], color, "#687d83")
    image.crop((margin, header, margin + pixels, header + pixels)).save(OUTPUT / "city-topview-clean.png")
    for east, north, label in LABELS:
        point_x, point_y = project((east, north))
        text_font = font(72)
        left, top, right, bottom = draw.textbbox((0, 0), label, font=text_font)
        width, height = right - left, bottom - top
        draw.rounded_rectangle((point_x - width / 2 - 19, point_y - height / 2 - 16, point_x + width / 2 + 19, point_y + height / 2 + 16), radius=7, fill="#f7f6ef")
        draw.text((point_x - width / 2, point_y - height / 2 - top), label, font=text_font, fill="#294750")
    draw.text((margin, 40), "LCMAgent  /  四公里混合城区", font=font(88), fill="#203d47")
    sources = len({assets[instance["asset"]]["source"] for instance in instances})
    draw.text((margin, 155), f"4 × 4 km  ·  {sources} 组 DeepMIMO 来源  ·  {len(instances):,} 个建筑几何实例  ·  非等距街区", font=font(40), fill="#576d73")
    draw.text((margin + pixels - 60, 115), "N ↑", font=font(45), fill="#294750")
    for kilometer in range(SIZE // 1000 + 1):
        point_x, point_y = project((kilometer * 1000, 0))
        draw.line([(point_x, point_y), (point_x, point_y + 12)], fill="#6f8083", width=2)
        draw.text((point_x - 18, point_y + 18), str(kilometer), font=font(26), fill="#576d73")
    footer_y = header + pixels + 85
    draw.text((margin, footer_y), "建筑高度", font=font(29), fill="#294750")
    for index, (label, color) in enumerate([("<12 m", "#adb9bd"), ("12–25 m", "#90a6ad"), ("25–60 m", "#698891"), ("60–120 m", "#3f626e"), ("≥120 m", "#244b5b"), ("公园 / 绿廊", "#c3d5b8")]):
        position = margin + 190 + index * 315
        draw.rectangle((position, footer_y + 2, position + 40, footer_y + 32), fill=color)
        draw.text((position + 55, footer_y), label, font=font(28), fill="#576d73")
    draw.text((margin, footer_y + 65), "真实源轮廓与尺寸；建筑和街坊重组。道路、绿地为新增设计。树点仅作景观示意。", font=font(29), fill="#576d73")
    draw.text((margin, footer_y + 113), "已生成统一坐标几何拼接原型 · 非既有真实城市 · 尚未重算信道 / 验证最终 RT 网格", font=font(28), fill="#576d73")
    image.save(OUTPUT / "city-topview.png")
    preview = image.copy()
    preview.thumbnail((2200, 2400), Image.Resampling.LANCZOS)
    preview.save(OUTPUT / "city-topview-preview.png")
    crop = (round(margin + 1550 * scale), round(header + (SIZE - 2700) * scale), round(margin + 2650 * scale), round(header + (SIZE - 1600) * scale))
    image.crop(crop).save(OUTPUT / "city-center-detail.png")


def render_saved():
    scene = json.loads(gzip.decompress((OUTPUT / "assembled-city.scene.json.gz").read_bytes()))
    assets = {asset["id"]: asset for asset in scene["assets"]}
    instances = scene["instances"]
    footprints = []
    for instance in instances:
        asset = assets[instance["asset"]]
        shape = Polygon(asset["footprint"]["outer"], asset["footprint"]["holes"])
        shape = affinity.rotate(shape, instance["rotation_z_deg"], origin=(0, 0))
        footprints.append(affinity.translate(shape, *instance["position_m"][:2]))
    roads = [{"line": LineString(road["points"]), "width": road["width_m"], "kind": road["kind"]} for road in scene["roads"]]
    parks = unary_union([Polygon(part["outer"], part["holes"]) for part in scene["parks"]])
    green_path = LineString(scene["green_path"])
    render(assets, instances, footprints, roads, parks, green_path, scene["manifest"]["validation"])


def main():
    # Smaller variants share assembly helpers; reset 4 km globals for API reuse.
    global RNG, BOUNDARY
    from .compact_layout import BOUNDARY as original_boundary
    RNG = random.Random(SEED)
    BOUNDARY = original_boundary
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-only", action="store_true")
    args = parser.parse_args()
    if args.render_only:
        render_saved()
        return
    assets, source_assets, rejected = load_assets()
    print(f"Loaded {len(assets)} assets from {len(source_assets)} sources; rejected {dict(rejected)}", flush=True)
    roads, parks, parcels, green_path = create_layout(source_assets)
    print(f"Created {len(parcels)} parcels, {len(roads)} road segments", flush=True)
    instances, footprints, source_usage = assemble(assets, source_assets, parcels)
    qa = validate(assets, instances, footprints, parcels, roads, parks)
    assert qa["building_overlap_pairs"] == 0, qa
    assert qa["outside_parcel_buildings"] == 0, qa
    assert qa["buildings_intersecting_road_carriageways"] == 0, qa
    assert qa["buildings_intersecting_parks"] == 0, qa
    used_assets = {instance["asset"] for instance in instances}
    manifest = {
        "date": "2026-10-26", "seed": SEED, "units": "m", "coordinate_system": "local Cartesian; X east, Y north, Z up",
        "extent_m": [0, 0, SIZE, SIZE], "status": "Assembled preview-derived geometry prototype, not a validated RT project.",
        "transform": "world_xyz = Rz(rotation_z_deg) @ asset_local_xyz + position_m; no scaling; each asset source origin is recorded",
        "source_snapshot_date": "2026-10-25", "source_license_status": "Original source terms remain applicable; full reuse/redistribution audit pending.",
        "synthetic_components": ["roads", "parks", "parcel layout", "instance placement"],
        "excluded_components": ["original source terrain", "source materials", "source TX/RX", "channels"],
        "asset_count": len(used_assets), "instance_count": len(instances), "source_usage": dict(source_usage),
        "placement_counts": dict(Counter(instance["placement"] for instance in instances)),
        "rejected_source_objects": dict(rejected), "validation": qa,
        "layout": "4000 m irregular collector network, recursive unequal street blocks, preserved screened Boston/ASU groups; not a scaled 10000 m grid",
        "preserved_groups": [{key: value for key, value in parcel["preserved_group"].items() if key not in ("shape", "placements")} | {"retained_object_count": len(parcel["preserved_group"]["placements"])} for parcel in parcels if "preserved_group" in parcel],
    }
    geometry_assets = [{key: value for key, value in asset.items() if key not in ("footprint", "orientation")} | {"footprint": serialize_polygon(asset["footprint"])} for asset in assets if asset["id"] in used_assets]
    scene = {
        "manifest": manifest, "assets": geometry_assets, "instances": instances,
        "roads": [{"points": np.round(np.asarray(road["line"].coords), 3).tolist(), "width_m": road["width"], "kind": road["kind"]} for road in roads],
        "parks": [serialize_polygon(part) for part in polygon_parts(parks)],
        "parcels": [{"footprint": serialize_polygon(parcel["shape"]), "role": parcel["role"]} for parcel in parcels],
        "ground": {"extent_m": [0, 0, SIZE, SIZE], "elevation_m": 0},
        "green_path": np.round(np.asarray(green_path.coords), 3).tolist(),
    }
    (OUTPUT / "assembled-city.scene.json.gz").write_bytes(gzip.compress(json.dumps(scene, ensure_ascii=False, separators=(",", ":")).encode(), mtime=0))
    (OUTPUT / "assembled-city-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    view = {"manifest": manifest, "buildings": [{"points": np.round(np.asarray(footprint.exterior.coords), 2).tolist(), "holes": [np.round(np.asarray(ring.coords), 2).tolist() for ring in footprint.interiors], "height": round(assets[instance["asset"]]["height_m"], 2), "source": assets[instance["asset"]]["source"], "object": assets[instance["asset"]]["source_object_index"], "parcel": instance["parcel"]} for instance, footprint in zip(instances, footprints)], "roads": scene["roads"], "parks": scene["parks"], "labels": LABELS}
    (OUTPUT / "assembled-city.view.json").write_text(json.dumps(view, ensure_ascii=False, separators=(",", ":")))
    render(assets, instances, footprints, roads, parks, green_path, qa)
    print(json.dumps(manifest, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
