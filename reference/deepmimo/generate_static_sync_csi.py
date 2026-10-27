#!/usr/bin/env python3
"""Generate static, timing-aligned DeepMIMO CSI-feedback data.

This is deliberately independent from ``multi_speed``. Each sample is one
UE-to-serving-BS static link and has one receive antenna and a 32-element BS
ULA. Each scenario directory contains only ``train.npy``, ``val.npy``, and
``test.npy``. Their shape is [N, 2, 32, 64] (real/imag), and the split is a
seeded random 8:1:1 split over valid UE links.

The implementation follows the scenario-level multiprocessing/NFS-safe claim
pattern used by datasets/deepmimo/multi_speed, but has no speed dimension.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import socket
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "2")

import deepmimo as dm
from deepmimo import config


SCENARIOS_DIR = Path("/nfs5/zxd/Huawei/datasets/deepmimo/deepmimo_scenarios")
OUT_ROOT = Path("/nfs5/zxd/Huawei/datasets/deepmimo/new")

BS_ANT_SHAPE = (32, 1)
UE_ANT_SHAPE = (1, 1)
BANDWIDTH_HZ = 20e6
N_FFT = 1024
N_SC = 64
SELECTED_SUBCARRIERS = np.arange(0, N_FFT, N_FFT // N_SC, dtype=np.int32)
SIGNIFICANT_PATH_DB = 25.0
EPS = 1e-12
SPLIT_RATIOS = (0.8, 0.1, 0.1)
SPLIT_SEED = 42
UE_CAP_MAX = 50_000
UE_SAMPLE_SEED = 42
CHUNK = 1024

CLAIM_DIR_NAME = ".claim"
STALE_CLAIM_SEC = 12 * 3600
SPLITS = ("train", "val", "test")


def discover_scenarios(scenarios_dir: Path) -> list[str]:
    """Return DeepMIMO city scenario variants supported by this project."""
    suffixes = ("_3p5", "_28", "_3p5_s", "_3p5_lwm")
    return sorted(
        p.name
        for p in scenarios_dir.iterdir()
        if p.is_dir() and p.name.startswith("city_") and p.name.endswith(suffixes)
    )


def _as_dataset_list(loaded) -> list:
    # Dataset.__getattr__ can raise KeyError, so do not use hasattr(loaded,
    # "datasets") here.
    return list(loaded.datasets) if type(loaded).__name__ == "MacroDataset" else [loaded]


def serving_bs_indices(datasets: list) -> tuple[np.ndarray, np.ndarray]:
    """Choose one serving BS per UE from sum of linear ray powers."""
    n_ue = int(datasets[0].n_ue)
    power_sum = np.full((len(datasets), n_ue), -np.inf, dtype=np.float64)
    for b, ds in enumerate(datasets):
        p_db = np.asarray(ds.power, dtype=np.float64)
        p_lin = np.where(np.isfinite(p_db), 10.0 ** (p_db / 10.0), 0.0)
        total = p_lin.sum(axis=-1)
        power_sum[b] = np.where(total > 0.0, total, -np.inf)
    serving = np.argmax(power_sum, axis=0).astype(np.int32)
    active = np.max(power_sum, axis=0) > 0.0
    serving[~active] = -1
    return serving, active


def random_split(n: int, *, seed: int) -> dict[str, np.ndarray]:
    """Seeded random 8:1:1 split over the active links."""
    if n < 3:
        idx = np.arange(n, dtype=np.int64)
        return {"train": idx, "val": idx[:0], "test": idx[:0]}
    rng = np.random.default_rng(seed)
    perm = rng.permutation(n)
    train_end = int(SPLIT_RATIOS[0] * n)
    val_end = train_end + int(SPLIT_RATIOS[1] * n)
    return {
        "train": np.sort(perm[:train_end]).astype(np.int64),
        "val": np.sort(perm[train_end:val_end]).astype(np.int64),
        "test": np.sort(perm[val_end:]).astype(np.int64),
    }


def make_channel_params(n_paths: int) -> dm.ChannelParameters:
    return dm.ChannelParameters(
        bs_antenna={
            "shape": np.array(BS_ANT_SHAPE),
            "spacing": 0.5,
            "rotation": np.array([0.0, 0.0, 0.0]),
            "radiation_pattern": "isotropic",
        },
        ue_antenna={
            "shape": np.array(UE_ANT_SHAPE),
            "spacing": 0.5,
            "rotation": np.array([0.0, 0.0, 0.0]),
            "radiation_pattern": "isotropic",
        },
        doppler=False,
        num_paths=int(n_paths),
        freq_domain=True,
        ofdm={
            "subcarriers": N_FFT,
            "selected_subcarriers": SELECTED_SUBCARRIERS,
            "bandwidth": BANDWIDTH_HZ,
            "rx_filter": 0,
        },
    )


def significant_first_path_delay(ds, ue_idx: np.ndarray) -> np.ndarray:
    """Earliest path no more than SIGNIFICANT_PATH_DB below the strongest ray."""
    delay = np.asarray(ds.delay[ue_idx], dtype=np.float64)
    power = np.asarray(ds.power[ue_idx], dtype=np.float64)
    strongest = np.nanmax(power, axis=1, keepdims=True)
    significant = np.isfinite(delay) & np.isfinite(power) & (power >= strongest - SIGNIFICANT_PATH_DB)
    tau = np.min(np.where(significant, delay, np.inf), axis=1)
    # Active serving links always have at least one valid path.  This fallback
    # makes the invariant explicit if a malformed scenario violates it.
    fallback = np.nanmin(np.where(np.isfinite(delay), delay, np.nan), axis=1)
    tau = np.where(np.isfinite(tau), tau, fallback)
    if not np.all(np.isfinite(tau)):
        raise ValueError("serving link without a finite path delay")
    return tau.astype(np.float64)


def timing_align_and_normalize(H: np.ndarray, tau_ref_s: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Remove common propagation delay and RMS-normalize each UE link.

    DeepMIMO forms its OFDM phase using ``exp(-j*2*pi*k/N*delay/Ts)``.
    Multiplying by the conjugate-delay phase below converts each path delay
    from tau to tau-tau_ref, without modifying angles or relative multipath.
    """
    freq_hz = SELECTED_SUBCARRIERS.astype(np.float64) * (BANDWIDTH_HZ / N_FFT)
    correction = np.exp(1j * 2.0 * np.pi * tau_ref_s[:, None] * freq_hz[None, :]).astype(np.complex64)
    H_sync = H * correction[:, None, :]
    rms = np.sqrt(np.mean(np.abs(H_sync) ** 2, axis=(1, 2), dtype=np.float64))
    rms = np.maximum(rms, EPS).astype(np.float32)
    H_norm = H_sync / rms[:, None, None]
    return H_norm.astype(np.complex64, copy=False), rms


def write_split_cfr(out_dir: Path, split: str, indices: np.ndarray, H: np.ndarray) -> dict:
    """Chunk-write one [N,2,32,64] float32 CFR file atomically."""
    n = len(indices)
    cfr_tmp = out_dir / f".{split}.tmp.npy"
    cfr_out = np.lib.format.open_memmap(cfr_tmp, mode="w+", dtype=np.float32, shape=(n, 2, 32, N_SC))
    for start in range(0, n, CHUNK):
        end = min(start + CHUNK, n)
        h = H[indices[start:end]]
        cfr_out[start:end, 0] = h.real
        cfr_out[start:end, 1] = h.imag
    cfr_out.flush()
    del cfr_out
    os.replace(cfr_tmp, out_dir / f"{split}.npy")
    return {"n": int(n), "shape": [int(n), 2, 32, N_SC]}


def scenario_done(out_dir: Path) -> bool:
    return all((out_dir / f"{split}.npy").is_file() and (out_dir / f"{split}.npy").stat().st_size > 128 for split in SPLITS)


def remove_legacy_outputs(out_dir: Path) -> None:
    """Remove only files produced by the earlier, superseded layout."""
    legacy = ["DONE", "meta.json"]
    for split in SPLITS:
        legacy.extend([f"{split}_cfr.npy", f"{split}_ad32.npy", f"{split}_aux.npz"])
    for name in legacy:
        (out_dir / name).unlink(missing_ok=True)


def try_claim(out_dir: Path, stale_sec: float) -> bool:
    out_dir.mkdir(parents=True, exist_ok=True)
    if scenario_done(out_dir):
        return False
    claim = out_dir / CLAIM_DIR_NAME
    try:
        claim.mkdir()
    except FileExistsError:
        try:
            age = time.time() - claim.stat().st_mtime
        except OSError:
            age = 0.0
        if age < stale_sec:
            return False
        try:
            for child in claim.iterdir():
                child.unlink()
            claim.rmdir()
            claim.mkdir()
        except OSError:
            return False
    (claim / "owner.json").write_text(json.dumps({"host": socket.gethostname(), "pid": os.getpid(), "time": time.time()}) + "\n")
    return True


def release_claim(out_dir: Path) -> None:
    claim = out_dir / CLAIM_DIR_NAME
    try:
        for child in claim.iterdir():
            child.unlink()
        claim.rmdir()
    except OSError:
        pass


def generate_one_scenario(job: dict) -> dict:
    scen = job["scenario"]
    out_root = Path(job["out_root"])
    out_dir = out_root / scen
    t0 = time.time()
    claimed = False
    try:
        if job["skip_existing"] and scenario_done(out_dir):
            return {"scenario": scen, "skipped": True, "reason": "done", "seconds": 0.0}
        if job["use_claim"]:
            claimed = try_claim(out_dir, job["stale_claim_sec"])
            if not claimed:
                return {"scenario": scen, "skipped": True, "reason": "claimed_or_done", "seconds": 0.0}
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
        remove_legacy_outputs(out_dir)

        print(f"\n=== static-sync scenario {scen} ===", flush=True)
        config.set("scenarios_folder", job["scenarios_dir"])

        # Load only inexpensive data for serving-BS selection, then reload the
        # selected UE subset with its multipath matrices.
        loaded = dm.load(scen, matrices=["power", "rx_pos"])
        datasets = _as_dataset_list(loaded)
        serving_full, active_full = serving_bs_indices(datasets)
        active_global = np.flatnonzero(active_full)
        rng = np.random.default_rng(UE_SAMPLE_SEED)
        cap = int(job["ue_cap"])
        if len(active_global) > cap:
            keep_global = np.sort(rng.choice(active_global, cap, replace=False))
        else:
            keep_global = active_global
        rx_set_id = int(datasets[0].txrx.get("rx_set_id", 0))
        del loaded, datasets, serving_full

        loaded = dm.load(scen, rx_sets={rx_set_id: keep_global.tolist()})
        datasets = _as_dataset_list(loaded)
        serving, active = serving_bs_indices(datasets)
        active_idx = np.flatnonzero(active)
        if not len(active_idx):
            raise ValueError("no active UE after subset reload")
        split_idx = random_split(len(active_idx), seed=SPLIT_SEED)
        pos_active = -np.ones(int(datasets[0].n_ue), dtype=np.int64)
        pos_active[active_idx] = np.arange(len(active_idx), dtype=np.int64)

        H_all = np.empty((len(active_idx), 32, N_SC), dtype=np.complex64)
        for b, ds in enumerate(datasets):
            ue_b = np.flatnonzero(serving == b)
            if not len(ue_b):
                continue
            cp = make_channel_params(int(np.asarray(ds.delay).shape[-1]))
            # No times/num_timestamps argument: DeepMIMO v4 computes the one
            # static t=0 channel snapshot.
            H_b = np.asarray(ds.compute_channels(params=cp))
            if H_b.shape[1:] != (1, 32, N_SC):
                raise ValueError(f"unexpected DeepMIMO shape {H_b.shape}")
            tau_b = significant_first_path_delay(ds, ue_b)
            H_norm_b, _ = timing_align_and_normalize(H_b[ue_b, 0], tau_b)
            dest = pos_active[ue_b]
            H_all[dest] = H_norm_b
            print(f"[{scen}] BS={b} serving_UE={len(ue_b)}", flush=True)
            del H_b, H_norm_b

        split_summary = {name: write_split_cfr(out_dir, name, idx, H_all) for name, idx in split_idx.items()}
        del H_all
        if claimed:
            release_claim(out_dir)
            claimed = False
        return {"scenario": scen, "skipped": False, "seconds": time.time() - t0, "splits": split_summary}
    except Exception as exc:
        if claimed:
            release_claim(out_dir)
        return {"scenario": scen, "error": str(exc), "traceback": traceback.format_exc(), "seconds": time.time() - t0}


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate static timing-aligned DeepMIMO CSI feedback data")
    ap.add_argument("--scenarios-dir", default=str(SCENARIOS_DIR))
    ap.add_argument("--out", default=str(OUT_ROOT))
    ap.add_argument("--scenarios", nargs="*", default=None, help="scenario-name subset")
    ap.add_argument("--scenario-workers", type=int, default=3)
    ap.add_argument("--ue-cap", type=int, default=UE_CAP_MAX, help="maximum active UEs per scenario")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--no-claim", action="store_true")
    ap.add_argument("--stale-claim-hours", type=float, default=STALE_CLAIM_SEC / 3600.0)
    ap.add_argument("--shard", type=str, default=None, help="stable multi-server shard i/N, e.g. 0/4")
    ap.add_argument("--list-only", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if args.ue_cap <= 0 or args.scenario_workers <= 0:
        raise SystemExit("--ue-cap and --scenario-workers must be positive")

    scenarios_dir = Path(args.scenarios_dir)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)
    all_scenarios = discover_scenarios(scenarios_dir)
    if args.scenarios:
        requested = set(args.scenarios)
        scenarios = [s for s in all_scenarios if s in requested]
        missing = requested - set(scenarios)
        if missing:
            raise SystemExit(f"scenarios not found: {sorted(missing)}")
    else:
        scenarios = all_scenarios

    if args.shard:
        import hashlib
        try:
            shard_i_s, shard_n_s = args.shard.split("/")
            shard_i, shard_n = int(shard_i_s), int(shard_n_s)
        except ValueError as exc:
            raise SystemExit(f"--shard must be i/N, e.g. 0/4: {exc}")
        if shard_n <= 0 or not 0 <= shard_i < shard_n:
            raise SystemExit(f"invalid --shard {args.shard!r}")
        scenarios = [
            s for s in scenarios
            if int(hashlib.md5(s.encode("utf-8")).hexdigest()[:8], 16) % shard_n == shard_i
        ]
        print(f"shard {shard_i}/{shard_n}: {len(scenarios)} scenarios")

    print("========== static synchronized CSI plan ==========")
    print(f"scenarios: {len(scenarios)}  out: {out_root}")
    print(f"parallel scenario workers: {args.scenario_workers}; UE cap: {args.ue_cap}")
    print(f"CFR=[N,2,32,{N_SC}], random split=8:1:1, B={BANDWIDTH_HZ/1e6:g} MHz")
    if args.list_only or args.dry_run:
        print("\n".join(scenarios))
        return

    jobs = [{
        "scenario": s,
        "scenarios_dir": str(scenarios_dir),
        "out_root": str(out_root),
        "ue_cap": args.ue_cap,
        "skip_existing": args.skip_existing,
        "use_claim": not args.no_claim,
        "stale_claim_sec": args.stale_claim_hours * 3600.0,
    } for s in scenarios]
    t0 = time.time()
    ctx = mp.get_context("fork")
    results: list[dict] = []
    with ProcessPoolExecutor(max_workers=min(args.scenario_workers, len(jobs)), mp_context=ctx) as ex:
        futures = {ex.submit(generate_one_scenario, j): j["scenario"] for j in jobs}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"[main] {result['scenario']} err={result.get('error')} skip={result.get('skipped')} t={result['seconds']:.1f}s", flush=True)

    summary = {"n_scenarios": len(scenarios), "ok": sum("error" not in r for r in results), "failed": sum("error" in r for r in results), "skipped": sum(bool(r.get("skipped")) for r in results), "total_seconds": time.time() - t0}
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
