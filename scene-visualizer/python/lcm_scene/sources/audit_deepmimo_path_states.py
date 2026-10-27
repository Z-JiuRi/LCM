import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.sources'

import argparse
import concurrent.futures
import hashlib
import importlib.util
import io
import json
import re
import struct
import threading
import time
import urllib.error
import urllib.parse
import zlib
from pathlib import Path

import numpy as np
from scipy.io import loadmat

from .audit_deepmimo_scenarios import BASE, DATE, OUT, ROOT, canonical_records, request


from .fetch_deepmimo_geometry import RemoteZip


DOWNLOAD_LOCK = threading.Lock()
NEXT_DOWNLOAD_TIME = 0


def open_archive(name):
    global NEXT_DOWNLOAD_TIME
    with DOWNLOAD_LOCK:
        time.sleep(max(0, NEXT_DOWNLOAD_TIME - time.monotonic()))
        url = BASE + "/api/download/secure?" + urllib.parse.urlencode({"filename": name + ".zip"})
        try:
            info = json.loads(request(url))
            NEXT_DOWNLOAD_TIME = time.monotonic() + 4
        except urllib.error.HTTPError as error:
            if error.code == 429:
                retry_after = error.headers.get("Retry-After", "60")
                delay = float(retry_after) if retry_after.isdigit() else 60
                NEXT_DOWNLOAD_TIME = time.monotonic() + max(60, delay)
            raise
    return RemoteZip(name, {"size": int(info["fileSize"]), "url": urllib.parse.urljoin(BASE, info["redirectUrl"])})


def extract(archive, member, target):
    if target.exists():
        content = target.read_bytes()
    else:
        entry = archive.entries[member]
        if entry["compressed"] > 24_000_000:
            raise ValueError(f"Selective member exceeds 24 MB download limit: {member}")
        offset = entry["offset"]
        header = struct.unpack("<4s5H3L2H", archive.read(offset, offset + 29))
        start = offset + 30 + header[-2] + header[-1]
        compressed = archive.read(start, start + entry["compressed"] - 1)
        if entry["method"] == 8:
            content = zlib.decompress(compressed, -15)
        elif entry["method"] == 0:
            content = compressed
        else:
            raise ValueError(f"Unsupported ZIP method: {entry['method']}")
        if len(content) != entry["size"] or zlib.crc32(content) != entry["crc"]:
            raise ValueError("ZIP size or CRC mismatch")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    if member.endswith(".mat"):
        arrays = {key: value for key, value in loadmat(io.BytesIO(content)).items() if not key.startswith("__")}
        if len(arrays) != 1:
            raise ValueError("Expected one MAT array")
        return next(iter(arrays.values())), hashlib.sha256(content).hexdigest()
    with np.load(io.BytesIO(content), allow_pickle=False) as arrays:
        if len(arrays.files) != 1:
            raise ValueError("Expected one NPZ array")
        return arrays[arrays.files[0]], hashlib.sha256(content).hexdigest()


def audit(item, preview_lookup):
    name = item["linkName"]
    directory = OUT / "cache/path-arrays" / name
    result_path = directory / "audit.json"
    if result_path.exists():
        cached = json.loads(result_path.read_text())
        if cached.get("status") == "verified":
            return cached
    result = {"name": name, "date": DATE, "source": BASE + "/api/download/secure?filename=" + name + ".zip", "status": "unavailable"}
    try:
        archive = open_archive(name)
        candidates = {member: entry for member, entry in archive.entries.items() if re.search(r"(?:^|/)inter_t\d+_tx\d+_r\d+\.(?:npz|mat)$", member)}
        if not candidates:
            raise ValueError("No supported inter_*.npz/.mat member in archive")
        selected = preview_lookup.get(name, {}).get("selected_link", "") or ""
        match = re.fullmatch(r"tx_(\d+)_rx_(\d+)", selected)
        preferred = {}
        if match:
            suffix = f"inter_t{int(match[1]):03d}_tx000_r{int(match[2]):03d}"
            preferred = {member: entry for member, entry in candidates.items() if member.rsplit('.', 1)[0].endswith(suffix)}
        if preferred:
            member = min(preferred)
            selection = "按预览默认 set 数字优先匹配；旧版编号不保证同义，以原始成员名和 TX 坐标为准；多快照包取字典序首快照"
        else:
            member = max(candidates, key=lambda key: candidates[key]["size"])
            selection = "未匹配到预览 set，选择归档中未压缩尺寸最大的 inter 成员；非全 TX 统计"
        array, digest = extract(archive, member, directory / member)
        tx_member = member.replace("inter_", "tx_pos_", 1)
        if tx_member in archive.entries:
            tx_positions, tx_digest = extract(archive, tx_member, directory / tx_member)
            result["raw_tx_positions_m"] = tx_positions.tolist()
            result["tx_sha256"] = tx_digest
        if array.ndim != 2:
            raise ValueError(f"Expected receiver × path matrix, got {array.shape}")
        valid = np.isfinite(array) & (array >= 0)
        mask_source = "inter 浮点矩阵：非有限值为缺失路径；非负有限交互码为有效路径"
        power_member = member.replace("inter_", "power_", 1)
        if not np.isnan(array).any() or array.dtype.kind not in "fc":
            if power_member not in archive.entries:
                raise ValueError("Interaction matrix has no NaN padding; no power matrix to disambiguate zero padding")
            powers, power_digest = extract(archive, power_member, directory / power_member)
            if powers.shape != array.shape:
                raise ValueError("Power/interaction matrix dimensions differ")
            valid &= np.isfinite(powers) & (powers != 0)
            mask_source = "联合 inter 与有限且非零的 dBm power 掩码；避免将零填充当直达路径"
            result["power_sha256"] = power_digest
        has_path = valid.any(axis=1)
        is_los = (valid & (array == 0)).any(axis=1)
        counts = {
            "los": int(is_los.sum()),
            "nlos": int((has_path & ~is_los).sum()),
            "no_recorded_path": int((~has_path).sum()),
            "total_receiver_positions": int(array.shape[0]),
        }
        assert counts["los"] + counts["nlos"] + counts["no_recorded_path"] == counts["total_receiver_positions"]
        states = []
        if counts["los"]:
            states.append("LoS")
        if counts["nlos"]:
            states.append("NLoS")
        if not states:
            states.append("无记录路径")
        result.update({"status": "verified", "member": member, "selection": selection, "counts": counts, "observed_states": states, "mask_source": mask_source, "inter_sha256": digest, "inter_dtype": str(array.dtype), "inter_shape": list(array.shape), "raw_cache": str((directory / member).relative_to(ROOT)), "archive_size_bytes": archive.size, "interpretation": "原始路径交互记录，不是重新仿真；有无直达记录受原始追踪与路径截断设置影响；统计只对应所列成员，不覆盖其他 TX/RX set 或其他快照"})
    except Exception as error:
        result["error"] = f"{type(error).__name__}: {error}"
    directory.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--names", nargs="*")
    parser.add_argument("--cache-only", action="store_true")
    args = parser.parse_args()
    catalog = json.loads((OUT / "catalog.json").read_text())
    records = [item for item, ids in canonical_records(catalog) if item["subMenu"] == "v4"]
    if args.names:
        records = [item for item in records if item["linkName"] in args.names]
    if args.cache_only:
        records = []
    classification = OUT / "classification.json"
    previews = {item["name"]: item.get("preview") or {} for item in json.loads(classification.read_text())["records"]} if classification.exists() else {}
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(audit, item, previews) for item in records]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(len(results), "/", len(records), result["name"], result["status"], result.get("counts", result.get("error")), flush=True)
    cached_results = [json.loads(path.read_text()) for path in (OUT / "cache/path-arrays").glob("*/audit.json")]
    cached_results.sort(key=lambda result: result["name"])
    output = {"date": DATE, "audit_scope": "已核验条目各选择一个 TX/RX 网格及一个快照；不计算跨 TX 汇总比例；未列出的条目尚未完成原始路径核验", "records": cached_results}
    (OUT / "path-states.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
