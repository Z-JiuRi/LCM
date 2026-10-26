import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.city'

import gzip
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import ConvexHull, QhullError

from .inspect_candidates import CACHE, ROOT, vertices


from ..paths import CITY_ROOT
OUTPUT = CITY_ROOT
GROUPS = {
    "A_highrise_core": ["boston5g_3p5", "city_5_philadelphia_3p5", "city_32_sydney_3p5"],
    "B_tower_clusters": ["city_30_singapore_3p5", "city_90_nanjing_3p5", "city_92_sãopaulo_3p5", "city_99_shanghai_3p5"],
    "C_secondary_centers": ["city_2_chicago_3p5", "city_17_seattle_3p5", "city_50_edinburgh_3p5", "city_56_montreal_3p5"],
    "D_compact_midrise": ["city_24_cairo_3p5", "city_27_rio_de_janeiro_3p5", "city_28_mumbai_3p5", "city_55_madrid_3p5"],
    "E_mixed_transition": ["city_10_austin_3p5", "city_43_cape_town_3p5", "city_98_guangzhou_3p5", "city_100_bogotá_3p5"],
    "F_fine_grain_lowrise": ["city_0_newyork_3p5", "city_6_miami_3p5", "city_21_taito_city_3p5", "city_41_kyoto_3p5"],
    "G_lowrise_neighborhoods": ["city_1_losangeles_3p5", "city_8_dallas_3p5", "city_11_santaclara_3p5", "city_14_charlotte_3p5", "city_18_denver_3p5", "city_38_toronto_3p5"],
    "H_midrise_groups": ["city_15_indianapolis_3p5", "city_53_sankt-peterburg_3p5", "city_69_warszawa_3p5", "city_102_huanggang_3p5"],
    "I_campus": ["asu_campus_3p5"],
    "J_large_low_midrise": ["city_4_phoenix_3p5", "city_19_oklahoma_3p5"],
}
RESERVES = ["city_64_new_york_3p5", "city_31_barcelona_3p5", "city_33_hong_kong_3p5", "city_45_stockholm_3p5", "city_13_columbus_3p5", "city_7_sandiego_3p5"]


def digest_geometry(objects):
    nonempty = [points for points in objects if len(points)]
    if not nonempty:
        return None
    origin = np.concatenate(nonempty).min(axis=0)
    object_hashes = []
    for points in nonempty:
        unique = np.unique(np.round(points - origin, 6), axis=0)
        object_hashes.append(hashlib.sha256(unique.astype("<f8").tobytes()).hexdigest())
    return hashlib.sha256("|".join(sorted(object_hashes)).encode()).hexdigest()


def inspect(path, records):
    name = path.name.removesuffix(".json.gz")
    preview = json.loads(gzip.decompress(path.read_bytes()))
    objects = []
    polygons = []
    heights = []
    hull_fallbacks = 0
    for building in preview.get("buildings", []):
        points = np.asarray(list(vertices(building)), dtype=float)
        if points.size == 0 or not np.isfinite(points).all():
            continue
        objects.append(points)
        height = float(np.ptp(points[:, 2]))
        if height < 2.5:
            continue
        horizontal = np.unique(points[:, :2], axis=0)
        if len(horizontal) < 3:
            continue
        try:
            hull = ConvexHull(horizontal)
        except QhullError:
            continue
        footprint = horizontal[hull.vertices]
        base_faces = []
        for face in building:
            face_points = np.asarray(list(vertices(face)), dtype=float)
            if face_points.size and len(np.unique(face_points[:, :2], axis=0)) >= 3:
                if np.ptp(face_points[:, 2]) < 1e-5 and abs(face_points[0, 2] - points[:, 2].min()) < 1e-5:
                    base_faces.append(face_points[:, :2])
        if base_faces:
            footprint = max(base_faces, key=len)
        else:
            hull_fallbacks += 1
        heights.append(height)
        polygons.append((footprint, height))
    summary = {
        "name": name,
        "cache_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "building_vertex_signature": digest_geometry(objects),
        "signature_scope": "Translation-normalized vertex sets per preview object, rounded to 1e-6 m; not topology/material/terrain equivalence, and not rotation-invariant.",
        "catalog_has_rt_source": [record.get("hasRtSource") for record in records if record.get("linkName") == name],
        "positive_height_preview_objects": len(polygons),
        "footprint_convex_hull_fallback_objects": hull_fallbacks,
    }
    if heights:
        points = np.concatenate([polygon for polygon, height in polygons])
        dimensions = np.ptp(points, axis=0)
        summary.update({
            "height_p50_p90_max_m": np.percentile(heights, [50, 90, 100]).round(2).tolist(),
            "building_xy_extent_m": dimensions.round(2).tolist(),
            "building_bbox_area_km2": round(float(np.prod(dimensions)) / 1e6, 6),
        })
    return summary, polygons


def render(names, inspections, target):
    columns = 4
    cell_width, cell_height = 440, 375
    rows = (len(names) + columns - 1) // columns
    image = Image.new("RGB", (columns * cell_width, rows * cell_height), "#f4f6f8")
    draw = ImageDraw.Draw(image)
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    title_font = ImageFont.truetype(font_path, 18)
    detail_font = ImageFont.truetype(font_path, 16)
    for index, name in enumerate(names):
        summary, polygons = inspections[name]
        left, top = index % columns * cell_width, index // columns * cell_height
        draw.text((left + 12, top + 10), name, font=title_font, fill="#172334")
        if not polygons:
            continue
        points = np.concatenate([polygon for polygon, height in polygons])
        minimum, maximum = points.min(axis=0), points.max(axis=0)
        dimensions = maximum - minimum
        heights = summary["height_p50_p90_max_m"]
        draw.text((left + 12, top + 36), f"H50 / H90 / Hmax: {heights[0]:.1f} / {heights[1]:.1f} / {heights[2]:.1f} m", font=detail_font, fill="#435265")
        draw.text((left + 12, top + 59), f"Extent: {dimensions[0]:.0f} x {dimensions[1]:.0f} m (panel-scaled)", font=detail_font, fill="#435265")
        scale = min((cell_width - 35) / dimensions[0], (cell_height - 110) / dimensions[1])
        center = (minimum + maximum) / 2
        offset = np.asarray([left + cell_width / 2, top + 225])
        for polygon, height in sorted(polygons, key=lambda item: item[1]):
            projected = (polygon - center) * np.asarray([scale, -scale]) + offset
            color = "#bdc9d0" if height < 10 else "#72abad" if height < 25 else "#d7a365" if height < 60 else "#a65354"
            draw.polygon([tuple(point) for point in projected], fill=color, outline="#52606b")
    image.save(target)


def main():
    records = json.loads((CACHE.parent.parent / "catalog.json").read_text())
    inspections = {}
    signatures = defaultdict(list)
    for path in sorted(CACHE.glob("*.json.gz")):
        summary, polygons = inspect(path, records)
        inspections[summary["name"]] = (summary, polygons)
        if summary["building_vertex_signature"]:
            signatures[summary["building_vertex_signature"]].append(summary["name"])
    names = [name for members in GROUPS.values() for name in members]
    assert len(names) == len(set(names)) == 36
    assert len(RESERVES) == len(set(RESERVES)) == 6
    assert not set(names).intersection(RESERVES)
    selected_signatures = [inspections[name][0]["building_vertex_signature"] for name in names + RESERVES]
    assert len(set(selected_signatures)) == len(names + RESERVES)
    assert all(inspections[name][1] for name in names + RESERVES)
    report = {
        "date": "2026-10-26",
        "status": "Morphology screening and proposed allocation, not imported RT-ready sources.",
        "source_snapshot_date": "2026-10-25",
        "preview_count": len(inspections),
        "selected_count": len(names),
        "groups": GROUPS,
        "reserves": RESERVES,
        "projection_note": "Largest available bottom face per positive-height object, otherwise XY convex hull. Panel scales vary. Diagnostic only; not final watertight scene geometry.",
        "identical_building_vertex_signature_groups": [members for members in signatures.values() if len(members) > 1],
        "selected_building_bbox_area_sum_km2": round(sum(inspections[name][0]["building_bbox_area_km2"] for name in names), 4),
        "area_warning": "Sum of selected scene building bounding boxes, not unique usable land area or lossless geometry area; duplicates, road gaps and cutting losses remain unmeasured.",
        "scenarios": [summary for summary, polygons in inspections.values()],
    }
    (OUTPUT / "expanded-source-screening.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    render(names[:20], inspections, OUTPUT / "expanded-footprints-centers.png")
    render(names[20:], inspections, OUTPUT / "expanded-footprints-neighborhoods.png")
    render(RESERVES, inspections, OUTPUT / "reserve-footprints.png")
    print(json.dumps({key: value for key, value in report.items() if key != "scenarios"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
