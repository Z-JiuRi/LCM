import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.city'

"""Reusable top-view rendering for metre-based, synthetic city variants.

This module does not import assemble_city or its layout globals. Pillow and
Shapely are the only non-standard dependencies. Existing scene files are never
read or changed: the caller supplies the geometry and chooses an output folder.
"""

import math
import random
from collections.abc import Mapping
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep


FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"
MAP_PIXELS = 4000
HEIGHT_BINS = (
    (12, "<12 m", "#adb9bd"),
    (25, "12–25 m", "#90a6ad"),
    (60, "25–60 m", "#698891"),
    (120, "60–120 m", "#3f626e"),
    (math.inf, "≥120 m", "#244b5b"),
)
PAPER = "#f7f6f0"
GROUND = "#e4e8de"
INK = "#294750"
MUTED = "#576d73"


def _parts(geometry, kinds):
    """Recursively flatten Multi*/GeometryCollection, including empty results."""
    if geometry is None or geometry.is_empty:
        return
    if geometry.geom_type in kinds:
        yield geometry
    elif hasattr(geometry, "geoms"):
        for part in geometry.geoms:
            yield from _parts(part, kinds)


def _asset_table(assets):
    if isinstance(assets, Mapping):
        return assets
    # Preserve the original contiguous list contract, while also accepting
    # explicit non-contiguous ids when the caller supplies them in a list.
    return {asset.get("id", index): asset for index, asset in enumerate(assets)}


def _height_color(height):
    return next(color for upper, _, color in HEIGHT_BINS if height < upper or upper == math.inf)


def _font(size):
    # Do not silently replace the requested Chinese font with a bitmap font
    # that cannot display the labels. Report a useful error on other systems.
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except OSError as error:
        raise OSError("Rendering requires Hiragino Sans GB at " + FONT_PATH) from error


def render_city(output, size, seed, labels, assets, instances, footprints,
                roads, parks, green_path, qa):
    """Write annotated, clean and <=1600-pixel preview PNGs; return their Paths.

    Parameters
    ----------
    output : str | pathlib.Path
        Destination directory. Only the three named PNG outputs are written.
    size : float
        Square map side length in metres, normally 1000 or 2000. Coordinates
        are local east/north metres in [0, size]; north is up.
    seed : int
        Local deterministic landscape seed; global random state is untouched.
    labels : iterable
        Caller-positioned (east, north, text) tuples. Alternatively dictionaries
        with east, north, text and optional font_size (clamped to 24–46 px).
        Label centres stay at the input coordinates; no automatic repositioning.
    assets : list[dict] | dict[id, dict]
        Assets have height_m and source. Contiguous-id lists from assemble_city
        are accepted, as are id-keyed dictionaries.
    instances : iterable[dict]
        Each record has asset, referring to its asset id.
    footprints : iterable[Shapely geometry]
        Complete 2D footprints in the same order as instances.
    roads : iterable[dict]
        Original layout records: line (Shapely line), width (metres), kind.
        Serialized records with points and width_m are also accepted.
    parks : Shapely geometry
        Polygon/MultiPolygon green areas, including holes.
    green_path : Shapely geometry | None
        Designed park/greenway centreline(s), clipped to parks for display.
    qa : mapping | None
        Existing 2D placement checks. Only overlap, parcel-boundary, road and
        park intrusion counts are displayed; no RT or 3D success is inferred.

    The clean image is the 4000 x 4000 map without labels or furniture. The
    annotated image adds the caller's labels, title, used-source/instance counts,
    height legend, north arrow, two metre axes and explicit synthetic/RT notes.
    Shadows, trees and park paths are illustrative, not source geometry or QA.
    """
    size = float(size)
    if not math.isfinite(size) or size <= 0:
        raise ValueError("size must be a finite positive side length in metres")
    instances, footprints, roads = list(instances), list(footprints), list(roads)
    if len(instances) != len(footprints):
        raise ValueError("instances and footprints must have identical lengths")
    assets = _asset_table(assets)
    heights = [float(assets[item["asset"]]["height_m"]) for item in instances]
    if any(not math.isfinite(height) or height < 0 for height in heights):
        raise ValueError("asset height_m must be finite and nonnegative")
    sources = {assets[item["asset"]]["source"] for item in instances}
    output = Path(output)
    boundary = box(0, 0, size, size)
    parks = Polygon() if parks is None else parks.intersection(boundary)
    scale = MAP_PIXELS / size
    image = Image.new("RGB", (MAP_PIXELS, MAP_PIXELS), GROUND)
    draw = ImageDraw.Draw(image)

    def project(point):
        return point[0] * scale, (size - point[1]) * scale

    def polygon(shape, fill, outline=None):
        # Clip decorative shadows/edge geometry too. A local mask preserves the
        # existing background through polygon holes instead of filling them
        # with a fixed ground colour (important for parks and courtyard roofs).
        for part in _parts(shape.intersection(boundary), {"Polygon"}):
            points = [project(point) for point in part.exterior.coords]
            if not part.interiors:
                draw.polygon(points, fill=fill, outline=outline)
                continue
            min_x, min_y, max_x, max_y = part.bounds
            left = max(0, math.floor(min_x * scale) - 2)
            top = max(0, math.floor((size - max_y) * scale) - 2)
            right = min(MAP_PIXELS, math.ceil(max_x * scale) + 3)
            bottom = min(MAP_PIXELS, math.ceil((size - min_y) * scale) + 3)
            if right <= left or bottom <= top:
                continue
            mask = Image.new("L", (right - left, bottom - top), 0)
            mask_draw = ImageDraw.Draw(mask)
            local = lambda coords: [(x - left, y - top) for x, y in map(project, coords)]
            mask_draw.polygon(local(part.exterior.coords), fill=255)
            for ring in part.interiors:
                mask_draw.polygon(local(ring.coords), fill=0)
            image.paste(fill, (left, top, right, bottom), mask)
            if outline:
                draw.line(points, fill=outline, width=1)
                for ring in part.interiors:
                    draw.line([project(point) for point in ring.coords], fill=outline, width=1)

    road_records = []
    for road in roads:
        line = road.get("line")
        if line is None:
            line = LineString(road["points"])
        width = float(road["width"] if "width" in road else road["width_m"])
        if not math.isfinite(width) or width <= 0:
            raise ValueError("road width must be positive metres")
        road_records.append((line, width, road.get("kind", "street")))
    road_mask = unary_union([line.buffer(width / 2, cap_style=2)
                             for line, width, _ in road_records])

    polygon(parks, "#c3d5b8", "#b8cbb0")
    tree_rng = random.Random(int(seed) + 1)
    # Allocate samples per usable park area, not a fixed city-wide attempt count.
    # This preserves landscape density when changing from 1 km to 2 km.
    tree_area = parks.difference(road_mask).buffer(-max(2.0, size * .002))
    if green_path is not None and not green_path.is_empty:
        tree_area = tree_area.difference(green_path.buffer(2.5))
    for part in _parts(tree_area, {"Polygon"}):
        target = min(30000, round(part.area / 450.0))
        if target == 0:
            continue
        prepared = prep(part)
        min_x, min_y, max_x, max_y = part.bounds
        ratio = (max_x - min_x) * (max_y - min_y) / part.area
        attempts = min(1000000, math.ceil(target * ratio * 3) + 100)
        count = 0
        for _ in range(attempts):
            east = tree_rng.uniform(min_x, max_x)
            north = tree_rng.uniform(min_y, max_y)
            if not prepared.contains(Point(east, north)):
                continue
            x, y = project((east, north))
            radius = max(1.5, min(6.5, tree_rng.uniform(.9, 1.6) * scale))
            draw.ellipse((x - radius, y - radius, x + radius, y + radius),
                         fill=tree_rng.choice(("#adc69e", "#9fba94", "#b4cba7")))
            count += 1
            if count >= target:
                break

    # Subtle inset walking loops give separate parks a readable internal layer.
    # These decorative paths are synthetic, not added to caller geometry/QA.
    paths = []
    for part in _parts(parks, {"Polygon"}):
        if part.area >= 8000:
            inset = part.buffer(-min(22.0, math.sqrt(part.area) * .10))
            if not inset.is_empty:
                paths.append(inset.boundary)
    if green_path is not None:
        paths.append(green_path.intersection(parks))
    for path in paths:
        for part in _parts(path, {"LineString", "LinearRing"}):
            points = [project(point) for point in part.coords]
            draw.line(points, fill="#aebeaa", width=max(2, round(2.8 * scale)), joint="curve")
            draw.line(points, fill="#ede8d0", width=max(1, round(1.8 * scale)), joint="curve")

    # Local streets sit underneath arterials; cream carriageways contrast with
    # green verges without black outlines or oversized labels.
    for line, width, kind in sorted(road_records, key=lambda road: road[2] != "street"):
        verge = 5 if kind == "street" else 9
        polygon(line.buffer((width + verge) / 2, cap_style=2),
                "#c4c9c4" if kind == "street" else "#bac2bc")
        polygon(line.buffer(width / 2, cap_style=2), "#f7f5ec")
        if kind != "street":
            for part in _parts(line, {"LineString", "LinearRing"}):
                draw.line([project(point) for point in part.coords], fill="#d3dbc8",
                          width=max(1, round(2 * scale)), joint="curve")

    order = sorted(range(len(instances)), key=lambda index: heights[index])
    for index in order:
        height = heights[index]
        if height > 16:
            polygon(affinity.translate(footprints[index], height * .28, -height * .42), "#bac1b9")
    for index in order:
        polygon(footprints[index], _height_color(heights[index]), "#687d83")

    # Do not write until input validation and map rendering have succeeded.
    output.mkdir(parents=True, exist_ok=True)
    paths_out = {"annotated": output / "city-topview.png",
                 "clean": output / "city-topview-clean.png",
                 "preview": output / "city-topview-preview.png"}
    image.save(paths_out["clean"])
    left, right, header, footer = 150, 100, 200, 350
    annotated = Image.new("RGB", (MAP_PIXELS + left + right,
                                  MAP_PIXELS + header + footer), PAPER)
    annotated.paste(image, (left, header))
    draw = ImageDraw.Draw(annotated)

    for entry in labels or ():
        if isinstance(entry, Mapping):
            east, north, text = entry["east"], entry["north"], str(entry["text"])
            font_size = max(24, min(46, int(entry.get("font_size", 42))))
        else:
            east, north, text = entry
            text, font_size = str(text), 42
        if not (0 <= east <= size and 0 <= north <= size):
            raise ValueError("label coordinates must lie inside the map")
        x, y = project((east, north))
        x, y = x + left, y + header
        text_font = _font(font_size)
        bbox = draw.textbbox((0, 0), text, font=text_font)
        width, height = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rounded_rectangle((x - width / 2 - 12, y - height / 2 - 10,
                                x + width / 2 + 12, y + height / 2 + 10),
                               radius=6, fill="#f7f6ef")
        draw.text((x - width / 2 - bbox[0], y - height / 2 - bbox[1]),
                  text, font=text_font, fill=INK)

    size_km = size / 1000
    title = {1000: "一公里混合城区", 2000: "两公里混合城区"}.get(size, f"{size_km:g} 公里混合城区")
    draw.text((left, 30), "LCMAgent  /  " + title, font=_font(56), fill="#203d47")
    draw.text((left, 111),
              f"{size_km:g} × {size_km:g} km  ·  {len(sources)} 组 DeepMIMO 来源  ·  "
              f"{len(instances):,} 个建筑几何实例  ·  合成混合街区",
              font=_font(30), fill=MUTED)
    # An explicit north arrow, rather than relying on the font's arrow glyph.
    arrow_x, arrow_y = left + MAP_PIXELS - 40, 95
    draw.text((arrow_x, 30), "N", font=_font(30), fill=INK, anchor="mt")
    draw.line((arrow_x, arrow_y + 45, arrow_x, arrow_y - 15), fill=INK, width=4)
    draw.polygon(((arrow_x, arrow_y - 29), (arrow_x - 10, arrow_y - 10),
                  (arrow_x + 10, arrow_y - 10)), fill=INK)
    draw.rectangle((left, header, left + MAP_PIXELS, header + MAP_PIXELS), outline="#9daea7", width=2)

    step = 200 if size <= 1000 else 500
    ticks = [float(value) for value in range(0, math.floor(size) + 1, step)]
    if not math.isclose(ticks[-1], size):
        ticks.append(size)
    tick_font = _font(25)
    for metre in ticks:
        x, y = project((metre, 0))
        x, y = left + x, header + y
        draw.line((x, y, x, y + 12), fill=MUTED, width=2)
        draw.text((x, y + 19), f"{metre:g}", font=tick_font, fill=MUTED, anchor="mt")
        x, y = project((0, metre))
        x, y = left + x, header + y
        draw.line((x - 12, y, x, y), fill=MUTED, width=2)
        draw.text((x - 23, y), f"{metre:g}", font=tick_font, fill=MUTED, anchor="rm")
    draw.text((left + MAP_PIXELS, header + MAP_PIXELS + 55), "东向 / m",
              font=_font(23), fill=MUTED, anchor="rt")
    draw.text((left - 20, header - 36), "北向 / m", font=_font(23), fill=MUTED, anchor="rt")

    footer_y = header + MAP_PIXELS + 105
    draw.text((left, footer_y), "建筑高度", font=_font(27), fill=INK)
    legend_x = left + 160
    entries = [(label, color) for _, label, color in HEIGHT_BINS]
    entries += [("公园 / 绿廊", "#c3d5b8"), ("合成道路", "#f7f5ec")]
    for label, color in entries:
        draw.rectangle((legend_x, footer_y + 4, legend_x + 36, footer_y + 31),
                       fill=color, outline="#9daea7")
        draw.text((legend_x + 49, footer_y), label, font=_font(26), fill=MUTED)
        legend_x += 275
    qa = qa or {}
    checks = (("building_overlap_pairs", "重叠对"),
              ("outside_parcel_buildings", "越界"),
              ("buildings_intersecting_road_carriageways", "侵入道路"),
              ("buildings_intersecting_parks", "侵入公园"))
    qa_text = "  ·  ".join(f"{label} {qa[key] if key in qa else '未提供'}" for key, label in checks)
    draw.text((left, footer_y + 56), "二维 QA（仅平面完整轮廓）：" + qa_text,
              font=_font(25), fill=MUTED)
    draw.text((left, footer_y + 104),
              "DeepMIMO 源建筑轮廓与高度重组；道路、公园和绿廊为合成设计。树点、阴影与公园小径仅为示意。",
              font=_font(25), fill=MUTED)
    draw.text((left, footer_y + 151),
              "非既有真实城市 · QA 仅二维放置/相交检查 · 尚未进行 RT 验证、信道重算或最终三维网格验证。",
              font=_font(25), fill=MUTED)
    annotated.save(paths_out["annotated"])
    annotated.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    annotated.save(paths_out["preview"])
    return paths_out
