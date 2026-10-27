import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.sources'

import argparse
import concurrent.futures
import gzip
import hashlib
import html
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path


from ..paths import REPO_ROOT, CLASSIFICATION_ROOT, RESEARCH_ROOT
ROOT = REPO_ROOT
OUT = CLASSIFICATION_ROOT
BASE = "https://www.deepmimo.net"
DATE = "2026-10-25"


def plain(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", str(value or "")))).strip()


def request(url):
    for attempt in range(2):
        try:
            with urllib.request.urlopen(url, timeout=40) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in (502, 503, 504) or attempt:
                raise
            time.sleep(2)


def cached_json(path, url):
    if path.exists():
        return json.loads(gzip.decompress(path.read_bytes()))
    content = request(url)
    parsed = json.loads(content)
    if isinstance(parsed, dict) and "error" in parsed:
        raise ValueError(str(parsed))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(content, mtime=0))
    return parsed


def canonical_records(catalog):
    grouped = {}
    for item in catalog:
        grouped.setdefault((item["subMenu"], item["linkName"]), []).append(item)
    records = []
    for key, versions in grouped.items():
        selected = max(versions, key=lambda item: str(item.get("createdAt", "")))
        records.append((selected, [item["_id"] for item in versions]))
    return records


def components(item):
    return {part["name"]: plain(part.get("description")) for part in item.get("keyComponents", [])}


def coordinates(value):
    if isinstance(value, list):
        if len(value) == 3 and all(isinstance(number, (int, float)) for number in value):
            if all(math.isfinite(number) for number in value) and any(value):
                yield value
        else:
            for child in value:
                yield from coordinates(child)


def extent(points):
    if not points:
        return None
    return [round(max(point[axis] for point in points) - min(point[axis] for point in points), 3) for axis in range(3)]


def terrain_elevation(value, position):
    if not isinstance(value, list) or not value:
        return []
    if isinstance(value[0], list) and len(value[0]) == 3 and all(isinstance(number, (int, float)) for number in value[0]):
        vertices = list(coordinates(value))
        elevations = []
        if len(vertices) < 3:
            return elevations
        origin = vertices[0]
        for index in range(1, len(vertices) - 1):
            second, third = vertices[index:index + 2]
            determinant = (second[1] - third[1]) * (origin[0] - third[0]) + (third[0] - second[0]) * (origin[1] - third[1])
            if abs(determinant) < 1e-9:
                continue
            weight_first = ((second[1] - third[1]) * (position[0] - third[0]) + (third[0] - second[0]) * (position[1] - third[1])) / determinant
            weight_second = ((third[1] - origin[1]) * (position[0] - third[0]) + (origin[0] - third[0]) * (position[1] - third[1])) / determinant
            weight_third = 1 - weight_first - weight_second
            if min(weight_first, weight_second, weight_third) >= -1e-7:
                height = weight_first * origin[2] + weight_second * second[2] + weight_third * third[2]
                if height <= position[2]:
                    elevations.append(height)
        return elevations
    return [height for child in value for height in terrain_elevation(child, position)]


def preview_summary(preview):
    groups = preview.get("metadata", {}).get("txRxSets", [])
    tx_sets = {group["tx_set"] for group in groups}
    rx_sets = {group["rx_set"]: group for group in groups}
    inferred_tx_positions = []
    for group in rx_sets.values():
        bounds = group.get("bounds", {})
        if group.get("totalUsers") == 1 and group["rx_set"] in tx_sets and all(axis in bounds for axis in ("x", "y", "z")):
            inferred_tx_positions.append({"set": group["rx_set"], "xyz": [bounds[axis][0] for axis in ("x", "y", "z")]})
    largest = max(groups, key=lambda group: group.get("totalUsers", 0), default={})
    grid_bounds = largest.get("bounds", {})
    grid_extent = [round(grid_bounds[axis][1] - grid_bounds[axis][0], 3) for axis in ("x", "y")] if all(axis in grid_bounds for axis in ("x", "y")) else None
    terrain = list(coordinates(preview.get("terrain", [])))
    ground_values = [point[2] for point in terrain]
    flat_ground = ground_values[0] if ground_values and max(ground_values) - min(ground_values) < 0.01 else None
    tx_pos = preview.get("tx_pos")
    tx_z = tx_pos[2] if isinstance(tx_pos, list) and len(tx_pos) == 3 and isinstance(tx_pos[2], (int, float)) else None
    local_elevations = terrain_elevation(preview.get("terrain", []), tx_pos) if tx_z is not None else []
    local_ground = max(local_elevations) if local_elevations else flat_ground
    agl = round(tx_z - local_ground, 3) if tx_z is not None and local_ground is not None else None
    building_objects = preview.get("buildings", [])
    heights = []
    for building in building_objects:
        vertices = list(coordinates(building))
        if vertices:
            heights.append(max(point[2] for point in vertices) - min(point[2] for point in vertices))
    heights.sort()
    powers = preview.get("power") or {}
    valid_users = [index for index, values in powers.items() if isinstance(values, list) and any(isinstance(value, (int, float)) and math.isfinite(value) for value in values)]
    return {
        "selected_link": preview.get("selectedTxRxSet"),
        "selected_tx_xyz_m": tx_pos,
        "selected_tx_z_m": tx_z,
        "flat_terrain_z_m": flat_ground,
        "terrain_z_under_selected_tx_m": local_ground,
        "selected_tx_agl_m": agl,
        "other_tx_positions_inferred_from_colocated_singleton_rx": inferred_tx_positions,
        "tx_sets": sorted(tx_sets),
        "largest_rx_grid_points_including_no_path": largest.get("totalUsers"),
        "largest_rx_grid_extent_m": grid_extent,
        "largest_rx_grid_z_m": grid_bounds.get("z"),
        "geometry_extent_m": extent(list(coordinates(building_objects)) + terrain),
        "preview_building_objects": len(building_objects),
        "object_height_min_median_max_m": [round(heights[0], 3), round(heights[len(heights) // 2], 3), round(heights[-1], 3)] if heights else None,
        "sampled_user_count": len(powers),
        "sampled_users_with_finite_power": len(valid_users),
        "sampled_users_without_finite_power": len(powers) - len(valid_users),
        "valid_sample_indices": valid_users,
    }


def legacy_height(item):
    station_text = " ".join(text for name, text in components(item).items() if re.search(r"base.station", name, re.I))
    match = re.search(r"[Hh]eight(?: of [^.]*?)?(?: is| are|:)?\s*(\d+(?:\.\d+)?)\s*m", station_text)
    if match:
        return float(match.group(1))
    if item["linkName"] == "Dynamic Doppler DD1":
        return 4.5
    return None


def classify(item, preview):
    name = item["linkName"]
    name_lower = name.lower()
    sections = components(item)
    description = plain(item.get("description"))
    explicit_indoor = bool(re.match(r"i[123](?:_|$)", name_lower)) or name == "Office Floor 1"
    if explicit_indoor:
        return "InH-like", "室内办公/会议室/走廊；以文字与几何为准，不采用错误的 outdoor 筛选标签"
    if "drone" in name_lower:
        return "空地/RIS", "含空中终端/飞行 RIS；不硬归入地面 UMa/UMi"
    if name == "asu_campus_3p5_dyn":
        return "混合部署", "原包抽查包含 z=3 m 移动 TX 和 z=20 m 固定 TX；按 TX 分开归类"
    height = preview.get("selected_tx_agl_m") if preview else None
    basis = "预览地形相对站高 AGL"
    if height is None:
        height = legacy_height(item)
        basis = "原条目明确写出的基站高度"
    if height is not None:
        if height <= 15:
            return "UMi-like", f"{basis}为 {height:g} m；低位城市/街道部署候选，不是标准符合性认证"
        if height >= 18:
            return "UMa-like", f"{basis}为 {height:g} m；高位城市部署候选，仍须核对相对屋顶高度和站间距"
        return "城市部署/待定", f"{basis}为 {height:g} m；不强制套入 UMa/UMi"
    if "florida" in name_lower:
        return "低层住宅/待定", "别墅几何素材；不是标准 RMa；须核对站点和地面高度"
    if name_lower.startswith(("o1", "o2")) or name == "Dynamic Doppler DD1":
        return "UMi-like候选", "旧版同名系列是低位街道部署；当前变体高度未取得，不能当已核验"
    if name_lower.startswith("asu_campus"):
        return "UMa-like候选", "校园高位站点几何候选；本变体实际高度尚待核验"
    if "boston" in name_lower:
        return "UMi-like候选", "旧版为 15 m 街道部署；本变体实际高度尚待核验"
    if name_lower.startswith("city_") or "tempe" in name_lower or item["subMenu"] == "v3/city_series":
        return "城市几何/部署待定", "城市名称不能确定 UMa/UMi；未取得可靠的地面相对站高"
    return "待定", description or "缺少部署信息"


def inspect_record(pair, fetch_previews):
    item, record_ids = pair
    name = item["linkName"]
    sections = components(item)
    preview = None
    error = None
    preview_path = OUT / "cache/previews" / (name + ".json.gz")
    url = BASE + "/api/dataset/initial?" + urllib.parse.urlencode({"datasetName": name, "spacingX": 30, "spacingY": 30})
    if item["subMenu"] == "v4":
        try:
            if preview_path.exists() or fetch_previews:
                preview = cached_json(preview_path, url)
                if "metadata" not in preview:
                    raise ValueError("Preview has no metadata")
            else:
                error = "预览未取得；初次抓取错误见 cache/preview-fetch.log"
        except Exception as failure:
            error = f"{type(failure).__name__}: {failure}"
    summary = preview_summary(preview) if preview and "metadata" in preview else None
    category, reason = classify(item, summary)
    warnings = []
    if len(record_ids) > 1:
        warnings.append(f"同版本同名目录记录重复 {len(record_ids)} 次；保留全部记录 ID")
    if category == "InH-like" and item.get("features", {}).get("environment") == "outdoor":
        warnings.append("目录 environment=outdoor 与室内场景身份冲突")
    if item.get("advancedParameters", {}).get("numTx") and summary and len(summary["tx_sets"]) != item["advancedParameters"]["numTx"]:
        warnings.append("目录发射点数量与预览 TX set 数不同；set 不一定只含一个 TX")
    if summary and summary["sampled_user_count"] and not summary["sampled_users_with_finite_power"]:
        warnings.append("本次稀疏预览没有有限功率样点；不能据此宣称整个场景无路径")
    evidence_text = " ".join([plain(item.get("description")), *map(plain, item.get("details") or []), *sections.values()])
    los_mentions = [sentence.strip() for sentence in re.split(r"(?<=[.!?])\s+", evidence_text) if re.search(r"\b(?:LOS|NLOS|LoS|NLoS)\b|line.of.sight|blockage", sentence, re.I)]
    if name == "ASU Campus":
        link_status = "原条目明确含 LoS/NLoS/无路径三类；旧版统计不能迁移到 v4"
    elif "Blockage" in name or name.lower().startswith(("o1b_", "i2")):
        link_status = "显式遮挡场景；LoS/NLoS 子集仍需按 TX 与有效路径判定"
    elif los_mentions:
        link_status = "原说明提及 LoS/NLoS/遮挡；不是整图单一标签"
    else:
        link_status = "LoS/NLoS 分布待路径核验；不能以有限功率判断直视"
    return {
        "name": name,
        "version": item["subMenu"],
        "record_ids": record_ids,
        "selected_record_id": item["_id"],
        "category": category,
        "classification_reason": reason,
        "link_status": link_status,
        "legacy_explicit_bs_height_m": legacy_height(item),
        "catalog_environment": item.get("features", {}).get("environment"),
        "features": item.get("features"),
        "advanced_parameters": item.get("advancedParameters"),
        "source_description": plain(item.get("description")),
        "source_details": [plain(detail) for detail in item.get("details") or []],
        "source_components": sections,
        "source_los_mentions": los_mentions,
        "has_rt_source_flag": item.get("hasRtSource"),
        "download": item.get("download"),
        "preview": summary,
        "preview_url": url if item["subMenu"] == "v4" else None,
        "preview_cache": str(preview_path.relative_to(ROOT)) if preview_path.exists() else None,
        "preview_error": error,
        "warnings": warnings,
    }


def render_report(document):
    records = document["records"]
    path_audits = {audit["name"]: audit for path in (OUT / "cache/path-arrays").glob("*/audit.json") if (audit := json.loads(path.read_text())).get("status") == "verified"}
    preview_count = sum(record["preview"] is not None for record in records)
    lines = [
        "# DeepMIMO 场景分类与几何拼接素材清单",
        "",
        f"核验日期：{DATE}。目录快照 SHA-256：`{document['catalog_sha256']}`。",
        "",
        "> 本清单服务于**几何拼接后重新计算信道**。没有新增拼接地图、没有重新仿真信道，也没有验证 LCMAgent 收益。UMa-like/UMi-like 是本项目的素材与原部署近似分类，不是 DeepMIMO 官方标签或 3GPP 符合性认证。",
        "",
        "## 1. 核验范围与关键结论",
        "",
        f"- 官方目录共 **{document['raw_catalog_records']} 条记录**，按 `(subMenu, linkName)` 去重后 **{document['unique_catalog_entries']} 个条目**：v4 为 196 个，旧版为 32 个；这不是 228 张独立几何地图。",
        f"- 逐项读取目录参数；取得 **{preview_count} 个 v4 场景预览**，读取站点位置、地形、建筑对象与网格范围；**{len(path_audits)} 个 v4 条目**读取了一个原始路径矩阵并统计 LoS/NLoS/无记录路径。没有将部分条目的核验写成全库核验。",
        "- 原始城市系列主要是低位部署，不能统称 UMa。`city_0_newyork_3p5` 的已读站点为 6 m；同名 `_s` 变体的预览站点为 z=20 m。**变体不仅可能改变频段，也可能改变追踪器、站点和几何表达。**",
        "- 上海样例原站 z=10 m，应归 UMi-like；ASU 校园原站 z=22 m，可作为 UMa-like 候选。几何拼接后重新布置站点时，分类需要重新确定。",
        "- 当前没有确认到一套明确按标准 RMa 或 InF 配置的现成条目；低层住宅、Florida villa 不能仅因建筑稀疏就叫 RMa。",
        "",
        "## 2. 分类规则",
        "",
        "1. **环境与部署**：I1/I2/I3、Office Floor 1 归 InH-like；飞行 RIS/无人机单列；室外依原站高、地形和部署说明分组。低位城市站高不超过 15 m 暂归 UMi-like；约 20 m 级及以上（本表启发式阈值 18 m）暂归 UMa-like；中间高度或证据缺失保留待定。这些阈值是项目筛选规则，不是 3GPP 的类别判据。",
        "2. **站高来源**：优先用预览 TX 坐标减去其垂足处最高地形表面高程；地形平坦时等价于减去平面高程。地形投影采用面片三角化，仅用于本次素材筛选，不是另一个经过验证的射线追踪器。无法取得地面时，不把世界坐标 z 自动当 AGL。旧版有明确高度文字时单独采用。",
        "3. **LoS/NLoS**：只在原始 `inter` 矩阵的有效路径上判断；出现交互码 0 记 LoS，有有效路径但无 0 记 NLoS，全无有效路径另记无记录路径。NaN 不当作零；无直达记录也可能受原始射线追踪范围和路径截断影响。",
        "4. **统计单位**：一个明确列名的 TX/RX 网格、一个快照，不是整个场景所有站点的聚合比例。多站场景可同时包含 LoS 与 NLoS，表中应读作 `UMi-LoS 子集 + UMi-NLoS 子集`，不能给整图强贴一个 LoS 标签。",
        "5. **未核验不填值**：HTTP 429、HTTP 500、缺失几何或不支持的归档格式均保留为未核验。官网 `environment` 把部分 I1/I2/I3 条目标成 outdoor，与室内说明冲突；本表采用实际场景身份而不是盲信筛选字段。",
        "",
        "## 3. 用于拼接的场景族",
        "",
        "| 场景族 | 本次分类 | 拼接素材用途与证据边界 |",
        "|---|---|---|",
        "| ASU Campus；`asu_campus_3p5` | UMa-like；LoS 与 NLoS 原始子集已确认 | 校园、中等高度楼群和开阔空间；22 m 站点。`_10cm` 未因同族而继承统计 |",
        "| `city_0…19_*_3p5_s`，共 20 个 Sionna 变体 | UMa-like 候选 | 已取得各自预览；选中 TX 的 z=20 m，局部地面约 0.3 m；与不带 `_s` 的原始低站版本分开 |",
        "| `city_0_newyork_new` | UMa-like 候选 | 20 m 站点的派生城市几何；不是默认 New York 条目的别名 |",
        "| 城市系列默认版本、28 GHz 版本及 `_lwm` | 以 UMi-like 为主，逐项见全表 | 初始城市组常为 6 m 站点，后续城市组常为 10 m；不同频段及追踪设置不能互相继承路径比例 |",
        "| Boston5G；`boston5g_*`；Boston5G RIS | UMi-like | 原站 15 m，适合高楼街道几何；RIS 原说明有 NLoS 用户，但不等于全部用户 NLoS |",
        "| O1 / `o1_*`；O1 Blockage / `o1b_*` | UMi-like／相应候选 | 街道、路口与显式遮挡面；现有变体下载限流者保留未核验 |",
        "| O2 Dynamic；Dynamic Doppler DD1 | UMi-like，动态街道 | 旧版说明为移动交通；前者 6 m，后者 4.5 m 基站；适合后续动态遮挡素材，不冒充已读全部时序 |",
        "| I1、I2、I3；Office Floor 1 | InH-like | 会议室、走廊与办公室；I2 是显式直达遮挡布局，不据此判整个网格全 NLoS |",
        "| Florida villa 系列 | 低层住宅几何；已取得低位站高者归 UMi-like | 多个派生/试验性条目；大网格不代表丰富建筑，更不自动等于 RMa |",
        "| `asu_campus_3p5_dyn` | 混合：低位移动 TX + 高位固定 TX | 先前原包抽查的两个 TX 分别在 z=3 m 与 z=20 m；不是已验证的移动建筑遮挡 |",
        "| O1 Drone / `o1_drone_200` | 空地/RIS | 单列，不套地面 UMa/UMi；只有需要无人机扩展时才纳入 |",
        "",
        "## 4. 原始路径核验结果",
        "",
        "下表的数量是原始文件中接收位置数，不是同时在线 UE 数，也不是重新仿真的结果。已读文件的名称、选择方法、dtype、SHA-256、TX 坐标和完整掩码说明见 [path-states.json](../../../scene-studio/data/deepmimo-scenes/classification/path-states.json)。不把下表比例外推到同族其他频段或其他 TX。",
        "",
        "| 条目 | LoS | NLoS | 无记录路径 | 网格位置总数 | 原始成员 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for name, audit in sorted(path_audits.items()):
        counts = audit["counts"]
        lines.append(f"| `{name}` | {counts['los']:,} | {counts['nlos']:,} | {counts['no_recorded_path']:,} | {counts['total_receiver_positions']:,} | `{audit['member']}` |")
    lines += ["", "## 5. 全量逐项分类", "", "`P`=取得官方预览；`R`=读取所列原始路径矩阵；`D`=仅目录或旧版文字。`L+N` 表示在该文件中确实发现两种子集，`待核验`不表示不存在。几何尺寸是预览建筑与地形的 XY 外包范围，不是有效用户区、覆盖半径或可直接拼接的矩形边界。完整参数见 [classification.json](../../../scene-studio/data/deepmimo-scenes/classification/classification.json)。", ""]
    for version in ("v2", "v3", "v3/city_series", "v4"):
        group = [record for record in records if record["version"] == version]
        lines += [f"### {version}（{len(group)} 项）", "", "| 场景 | 部署归类 | 原站 z / AGL（m） | LoS/NLoS | 预览几何宽×深（m） | 证据 |", "|---|---|---|---|---|---|"]
        for record in group:
            preview = record["preview"] or {}
            audit = path_audits.get(record["name"])
            height = f"{preview['selected_tx_z_m']:g} / {preview['selected_tx_agl_m']:g}" if preview.get("selected_tx_agl_m") is not None else (f"z={preview['selected_tx_z_m']:g}；AGL 未知" if preview.get("selected_tx_z_m") is not None else (f"说明高度 {record['legacy_explicit_bs_height_m']:g}" if record["legacy_explicit_bs_height_m"] is not None else "待核验"))
            dimensions = preview.get("geometry_extent_m")
            size = f"{dimensions[0]:.1f}×{dimensions[1]:.1f}" if dimensions else "未取得"
            states = "+".join(audit["observed_states"]) + "（R）" if audit else "待核验"
            if record["name"] == "ASU Campus":
                states = "LoS+NLoS（旧版说明）"
            elif not audit and ("Blockage" in record["name"] or record["name"].lower().startswith(("i2", "o1b_"))):
                states = "遮挡布局；子集待核验"
            evidence = ("P" if preview else "D") + ("+R" if audit else "")
            lines.append(f"| `{record['name']}` | {record['category']} | {height} | {states} | {size} | {evidence} |")
        lines.append("")
    lines += ["## 6. 重复、缺失与使用限制", ""]
    for record in records:
        if len(record["record_ids"]) > 1:
            lines.append(f"- `{record['name']}`：{len(record['record_ids'])} 条同版本同名记录；原始 ID 保留在 JSON，不当作不同地图。")
    missing = [record["name"] for record in records if record["version"] == "v4" and not record["preview"]]
    lines += [f"- 未取得预览的 {len(missing)} 个 v4 条目：" + "、".join(f"`{name}`" for name in missing) + "。",
        "- 目录中的 `hasRtSource`、预览几何、已下载的路径数组是不同证据层级；本次未逐包确认完整可重放的射线追踪工程。",
        "- 原始材料为第三方数据。目录、下载记录、版本、原始命名与文件哈希均保留；项目脚本不是 DeepMIMO 或射线追踪器的原创替代。",
        "- 对几何拼接，应按建筑/道路形态选素材，再统一部署宏站、微站和室内站点。不要因原数据被归 UMi-like 就排除其作为未来 UMa 几何素材。",
        "",
        "## 7. 来源与复核入口",
        "",
        "- [DeepMIMO 官方场景目录](https://www.deepmimo.net/scenarios)；[本次使用的官方目录 API](https://www.deepmimo.net/api/scenarios)。",
        "- [DeepMIMO 官方数据格式：交互码与文件组织](https://deepmimo.github.io/DeepMIMO/resources/specs.html)。",
        "- [3GPP TR 38.901 V19.1.0 / ETSI TR 138 901：场景与信道条件](https://www.etsi.org/deliver/etsi_tr/138900_138999/138901/19.01.00_60/tr_138901v190100p.pdf)。本表没有运行标准模型校准。",
        "- [源目录快照](../../../scene-studio/data/deepmimo-scenes/classification/catalog.json)、[逐项结构化证据](../../../scene-studio/data/deepmimo-scenes/classification/classification.json)、[原始路径统计](../../../scene-studio/data/deepmimo-scenes/classification/path-states.json)。",
        "- [此前动态 ASU 抽查记录](DeepMIMO场景选型.md#动态-asu-的实际核验)。",
        "",
        "复核命令（不会启动新的射线追踪）：",
        "",
        "```bash",
        "python3 tools/scene-studio/scripts/audit_deepmimo_scenarios.py --report-only",
        "uv run --with numpy --with scipy python tools/scene-studio/scripts/audit_deepmimo_path_states.py --cache-only",
        "```",
        "",
        "联网重取预览使用第一个脚本的 `--fetch-previews`；原始路径脚本建议用 `--names` 显式限定条目。请求受官网可用性和限流影响，不保证所有条目可下载。",
        ""]
    report = RESEARCH_ROOT / "DeepMIMO场景分类与几何拼接素材清单.md"
    report.write_text("\n".join(lines))
    print(report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch-previews", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args()
    if args.report_only:
        render_report(json.loads((OUT / "classification.json").read_text()))
        return
    OUT.mkdir(parents=True, exist_ok=True)
    catalog_path = OUT / "catalog.json"
    if not catalog_path.exists():
        catalog_path.write_bytes(request(BASE + "/api/scenarios"))
    catalog = json.loads(catalog_path.read_bytes())
    records = canonical_records(catalog)
    if args.limit:
        records = records[:args.limit]
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(inspect_record, pair, args.fetch_previews): pair[0]["linkName"] for pair in records}
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            if len(results) % 10 == 0 or result["preview_error"]:
                print(len(results), "/", len(records), result["name"], result["category"], result["preview_error"] or "", flush=True)
    order = {(item["subMenu"], item["linkName"]): index for index, (item, _) in enumerate(records)}
    results.sort(key=lambda result: order[(result["version"], result["name"])])
    document = {
        "date": DATE,
        "source": BASE + "/api/scenarios",
        "catalog_sha256": hashlib.sha256(catalog_path.read_bytes()).hexdigest(),
        "raw_catalog_records": len(catalog),
        "unique_catalog_entries": len(canonical_records(catalog)),
        "audited_entries": len(results),
        "preview_spacing_indices": [30, 30],
        "classification_is_project_heuristic_not_standard_certification": True,
        "category_counts": dict(Counter(result["category"] for result in results)),
        "records": results,
    }
    (OUT / "classification.json").write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: value for key, value in document.items() if key != "records"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
