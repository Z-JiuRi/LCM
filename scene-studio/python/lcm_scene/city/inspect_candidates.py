import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.city'

import gzip
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.spatial import ConvexHull


from ..paths import CITY_ROOT, REPO_ROOT, PREVIEW_CACHE
ROOT = REPO_ROOT
CACHE = PREVIEW_CACHE
NAMES = [
    "boston5g_3p5", "city_5_philadelphia_3p5", "city_2_chicago_3p5", "city_99_shanghai_3p5",
    "city_17_seattle_3p5", "city_10_austin_3p5", "asu_campus_3p5", "city_6_miami_3p5",
    "city_1_losangeles_3p5", "city_11_santaclara_3p5", "city_8_dallas_3p5", "city_0_newyork_3p5",
]


def vertices(value):
    if not isinstance(value, list):
        return
    if len(value) == 3 and all(isinstance(number, (int, float)) for number in value):
        if any(value):
            yield value
    else:
        for child in value:
            yield from vertices(child)


def main():
    image = Image.new("RGB", (1800, 1350), "#f5f6f7")
    draw = ImageDraw.Draw(image)
    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
    title_font = ImageFont.truetype(font_path, 19)
    detail_font = ImageFont.truetype(font_path, 16)
    summaries = []
    for index, name in enumerate(NAMES):
        preview = json.loads(gzip.decompress((CACHE / (name + ".json.gz")).read_bytes()))
        objects = []
        for building in preview.get("buildings", []):
            points = np.asarray(list(vertices(building)))
            if points.size == 0:
                continue
            height = float(np.ptp(points[:, 2]))
            horizontal = np.unique(points[:, :2], axis=0)
            if height < 2.5 or len(horizontal) < 3:
                continue
            try:
                hull = ConvexHull(horizontal)
            except Exception:
                continue
            objects.append({"height": height, "polygon": horizontal[hull.vertices], "area": float(hull.volume)})
        points = np.concatenate([item["polygon"] for item in objects])
        minimum, maximum = points.min(axis=0), points.max(axis=0)
        dimensions = maximum - minimum
        heights = np.asarray([item["height"] for item in objects])
        summary = {"name": name, "positive_height_objects": len(objects), "height_min_median_max_m": [round(float(value), 2) for value in (heights.min(), np.median(heights), heights.max())], "building_xy_extent_m": dimensions.round(2).tolist(), "convex_footprint_area_sum_m2": round(sum(item["area"] for item in objects), 2), "note": "Preview objects with height >=2.5 m; convex XY diagnostic footprints, not land-use labels or lossless geometry."}
        summaries.append(summary)
        left, top = (index % 4) * 450, (index // 4) * 450
        draw.text((left + 15, top + 12), name, font=title_font, fill="#172334")
        draw.text((left + 15, top + 39), f"{len(objects)} objects | H50 {np.median(heights):.1f}m | Hmax {heights.max():.1f}m", font=detail_font, fill="#435265")
        draw.text((left + 15, top + 61), f"Building extent {dimensions[0]:.0f} x {dimensions[1]:.0f} m", font=detail_font, fill="#435265")
        scale = min(410 / dimensions[0], 335 / dimensions[1])
        offset = np.asarray([left + 225, top + 267])
        center = (minimum + maximum) / 2
        for item in sorted(objects, key=lambda item: item["height"]):
            projected = (item["polygon"] - center) * np.asarray([scale, -scale]) + offset
            color = "#bcc8ce" if item["height"] < 10 else "#71a9ad" if item["height"] < 25 else "#d7a365" if item["height"] < 60 else "#a65354"
            draw.polygon([tuple(point) for point in projected], fill=color, outline="#52606b")
    output = CITY_ROOT
    image.save(output / "candidate-footprints.png")
    (output / "candidate-geometry-summary.json").write_text(json.dumps(summaries, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summaries, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
