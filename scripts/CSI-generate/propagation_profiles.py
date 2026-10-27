"""CPU-only propagation policies and selected DeepMIMO source evidence.

This is a project policy layer, not a Wireless InSite -> Sionna converter.
Only sources explicitly selected by a scene/geometry manifest (or caller) are
read. No RT libraries, directory-wide discovery, or source material mutation.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
import gzip
import json
import math
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROFILE_DEFAULTS = {
    "source-informed": {
        "carrier_hz": 3.5e9, "max_depth": 7, "diffraction": True,
        "diffuse_reflection": True, "edge_diffraction": False,
        "refraction": False, "synthetic_array": True,
    },
    "legacy": {
        "carrier_hz": 3.5e9, "max_depth": 3, "diffraction": False,
        "diffuse_reflection": False, "edge_diffraction": False,
        "refraction": False, "synthetic_array": True,
    },
}
STANDARD_FIELDS = (
    "raytracer_name", "raytracer_version", "frequency", "max_path_depth",
    "max_reflections", "max_diffractions", "max_scattering", "max_transmissions",
    "diffuse_reflections", "diffuse_diffractions", "diffuse_transmissions",
    "diffuse_final_interaction_only", "diffuse_random_phases", "terrain_reflection",
    "terrain_diffraction", "terrain_scattering", "num_rays", "ray_casting_method",
    "synthetic_array", "ray_casting_range_az", "ray_casting_range_el",
)
# These are actual keys in downloaded params.json, not guessed Sionna names.
RAW_FIELDS = {
    "carrier_hz": ("waveform.CarrierFrequency",),
    "bandwidth_hz": ("waveform.bandwidth",),
    "antenna_type": ("antenna.type",),
    "antenna_polarization": ("antenna.polarization",),
    "max_reflections": ("model.max_reflections", "studyarea.model.values.max_reflections"),
    "max_diffractions": ("model.max_wedge_diffractions", "studyarea.model.values.max_wedge_diffractions"),
    "max_transmissions": ("model.max_transmissions", "studyarea.model.values.max_transmissions"),
    "ray_spacing": ("model.ray_spacing", "studyarea.model.values.ray_spacing"),
    "initial_ray_mode": ("model.initial_ray_mode", "studyarea.model.values.initial_ray_mode"),
    "terrain_diffractions": ("model.terrain_diffractions", "studyarea.model.values.terrain_diffractions"),
    "diffuse_enabled": ("diffuse_scattering.enabled", "studyarea.diffuse_scattering.values.enabled"),
    "diffuse_reflections": ("diffuse_scattering.diffuse_reflections", "studyarea.diffuse_scattering.values.diffuse_reflections"),
    "diffuse_diffractions": ("diffuse_scattering.diffuse_diffractions", "studyarea.diffuse_scattering.values.diffuse_diffractions"),
    "diffuse_transmissions": ("diffuse_scattering.diffuse_transmissions", "studyarea.diffuse_scattering.values.diffuse_transmissions"),
    "diffuse_final_interaction_only": ("diffuse_scattering.final_interaction_only", "studyarea.diffuse_scattering.values.final_interaction_only"),
    "apg_path_depth": ("apg_acceleration.path_depth", "studyarea.apg_acceleration.values.path_depth"),
}
CAVEATS = [
    "Evidence describes only the selected sources, not all downloaded DeepMIMO scenes.",
    "Standardized and raw source fields are retained separately; absent fields remain unknown.",
    "Sionna max_depth is a total interaction cap, not an equivalent encoding of separate Wireless InSite reflection/diffraction limits.",
    "Source num_rays/ray_spacing and Sionna samples_per_src are different controls; no equal-ray-count or equal-search-coverage claim is made.",
    "Source global diffuse enable and per-material scattering models are distinct; a disabled global switch does not imply every material coefficient is zero.",
    "Source antenna and bandwidth fields are evidence only, not task antenna/OFDM configuration defaults.",
]


def _read_json(path: Path) -> dict:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle)
    else:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _source_names(scene_or_source_names) -> list[str]:
    """Resolve explicit names, a source_names manifest, or instantiated scene assets.

    A source_scene path in an old geometry manifest is deliberately NOT followed:
    the manifest must declare its sources, or the caller must pass the scene.
    In a scene, unused library assets/materials and disabled vegetation do not
    contribute propagation sources. Terrain material provenance does contribute.
    """
    value = scene_or_source_names
    if isinstance(value, Path) or (isinstance(value, str) and value.endswith((".json", ".json.gz"))):
        value = _read_json(Path(value))
    if isinstance(value, Mapping):
        if "source_names" in value:
            value = value["source_names"]
        elif "assets" in value and "instances" in value:
            scene = value
            assets = {asset["id"]: asset for asset in scene["assets"]}
            names, material_keys = set(), set()
            for instance in scene["instances"]:
                try:
                    asset = assets[instance["asset"]]
                except KeyError as error:
                    raise ValueError("Scene instance refers to an unknown asset") from error
                if asset.get("source"):
                    names.add(asset["source"])
                material_keys.update(asset.get("face_material_keys", []))
            terrain = scene.get("environment", {}).get("terrain") or {}
            material_keys.update(terrain.get("triangle_material_keys", []))
            materials = scene.get("materials", {})
            for key in material_keys:
                source = materials.get(key, {}).get("source_scene")
                if source:
                    names.add(source)
            value = names
        else:
            raise ValueError("Expected geometry manifest source_names or scene assets/instances; regenerate old geometry metadata")
    if isinstance(value, str):
        value = [value]
    try:
        names = list(value)
    except TypeError as error:
        raise ValueError("Expected source-name iterable or scene/geometry manifest") from error
    for name in names:
        if (not isinstance(name, str) or not name or name in (".", "..")
                or "/" in name or "\\" in name or "\x00" in name):
            raise ValueError(f"Invalid DeepMIMO source name: {name!r}")
    return sorted(set(names))


def _lookup(mapping: Mapping, path: str):
    for key in path.split("."):
        if not isinstance(mapping, Mapping) or key not in mapping:
            return None
        mapping = mapping[key]
    return mapping


def _unique(values) -> list:
    result = []
    for value in values:
        if value not in result:
            result.append(value)
    return result


def _source_row(source: str, root: Path) -> dict:
    relative = Path("data/deepmimo") / source / "params.json"
    path = root / relative
    data = _read_json(path)
    rt = data.get("rt_params")
    if not isinstance(rt, Mapping):
        raise ValueError(f"Missing/invalid rt_params in {path}")
    raw_params = rt.get("raw_params", {})
    if not isinstance(raw_params, Mapping):
        raise ValueError(f"Invalid rt_params.raw_params in {path}")
    standard = {key: rt[key] for key in STANDARD_FIELDS if key in rt}
    raw, raw_paths, conflicts = {}, {}, []
    for field, paths in RAW_FIELDS.items():
        observations = [{"path": "rt_params.raw_params." + key, "value": _lookup(raw_params, key)}
                        for key in paths if _lookup(raw_params, key) is not None]
        if not observations:
            continue
        raw[field] = observations[0]["value"]
        raw_paths[field] = observations[0]["path"]
        if any(item["value"] != observations[0]["value"] for item in observations[1:]):
            conflicts.append({"field": field, "kind": "raw_duplicates", "observations": observations})
    comparisons = {"frequency": "carrier_hz", **{key: key for key in (
        "max_reflections", "max_diffractions", "max_transmissions", "diffuse_reflections",
        "diffuse_diffractions", "diffuse_transmissions", "diffuse_final_interaction_only")}}
    for field, raw_field in comparisons.items():
        if field in standard and raw_field in raw and standard[field] != raw[raw_field]:
            conflicts.append({"field": field, "kind": "standard_vs_raw",
                              "standard": standard[field], "raw": raw[raw_field]})
    materials = data.get("materials", {})
    if not isinstance(materials, Mapping):
        raise ValueError(f"Invalid materials object in {path}")
    model_counts = Counter(record.get("scattering_model", "unknown")
                           for record in materials.values() if isinstance(record, Mapping))
    row = {
        "source": source, "params_file": relative.as_posix(),
        "deepmimo_version": data.get("version"), "standard": standard,
        "raw": raw, "raw_field_paths": raw_paths, "conflicts": conflicts,
        "material_scattering_model_counts": dict(sorted(model_counts.items())),
    }
    # Missing, non-boolean, and contradictory raw enable values are unknown;
    # max_scattering or a diffuse_reflections budget is NOT an enable flag.
    enabled = raw.get("diffuse_enabled")
    contradictory_enable = any(c["field"] == "diffuse_enabled" for c in conflicts)
    row["diffuse_enabled"] = enabled if isinstance(enabled, bool) and not contradictory_enable else None
    return row


def source_audit(scene_or_source_names, root: Path = REPO_ROOT) -> dict:
    """Read only data/deepmimo/<selected source>/params.json under repository root.

    Input: explicit iterable of source names, a single source name, a scene dict,
    a geometry manifest dict with source_names, or a JSON(.gz) path to either.
    Missing/corrupt selected files raise rather than silently dropping evidence.
    An explicit empty source list is valid and produces zero-source evidence.
    """
    names = _source_names(scene_or_source_names)
    rows = [_source_row(name, Path(root)) for name in names]
    aggregate = {"source_count": len(rows)}
    for section in ("standard", "raw"):
        keys = sorted({key for row in rows for key in row[section]})
        aggregate[section + "_values"] = {
            key: _unique(row[section][key] for row in rows if key in row[section]) for key in keys}
    for label, value in (("enabled", True), ("disabled", False), ("unknown", None)):
        aggregate[f"diffuse_{label}_sources"] = [row["source"] for row in rows if row["diffuse_enabled"] is value]
    aggregate["sources_with_conflicts"] = [row["source"] for row in rows if row["conflicts"]]
    return {"schema_version": 1, "source_names": names, "sources": rows,
            "aggregate": aggregate, "caveats": list(CAVEATS)}


def apply_profile(args) -> dict:
    """Return a new config, filling only absent/None profile fields.

    Set argparse profile-controlled defaults to None before calling. Explicit
    False is an override, not a missing value. Antennas, OFDM and ray budgets
    stay caller-owned and are never inferred from a downloaded source.
    """
    config = dict(args) if isinstance(args, Mapping) else vars(args).copy()
    name = config.get("propagation_profile") or "source-informed"
    if name not in PROFILE_DEFAULTS:
        raise ValueError(f"Unknown propagation profile: {name!r}")
    config["propagation_profile"] = name
    for key, value in PROFILE_DEFAULTS[name].items():
        if config.get(key) is None:
            config[key] = value
    frequency, depth = config["carrier_hz"], config["max_depth"]
    if isinstance(frequency, bool) or not isinstance(frequency, (int, float)) or not math.isfinite(frequency) or frequency <= 0:
        raise ValueError("carrier_hz must be finite and positive")
    if isinstance(depth, bool) or not isinstance(depth, int) or depth < 0:
        raise ValueError("max_depth must be a nonnegative integer")
    for key in ("diffraction", "diffuse_reflection", "edge_diffraction", "refraction", "synthetic_array"):
        if not isinstance(config[key], bool):
            raise ValueError(f"{key} must be boolean")
    if config["edge_diffraction"] and not config["diffraction"]:
        raise ValueError("edge_diffraction requires diffraction")
    return config


def profile_metadata(config, audit: dict | None = None) -> dict:
    """Describe policy/evidence boundaries without making source equivalence claims."""
    resolved = apply_profile(config)
    name = resolved["propagation_profile"]
    defaults = PROFILE_DEFAULTS[name]
    evidence = audit.get("aggregate", {}) if audit else {}
    disabled = list(evidence.get("diffuse_disabled_sources", []))
    unknown = list(evidence.get("diffuse_unknown_sources", []))
    assumptions = [
        "source-informed is a fixed project policy informed by source settings, not a per-scene automatic reconstruction or a validated Wireless InSite reproduction.",
        "The source-informed default max_depth=7 is a chosen total interaction cap, not the observed maximum of the selected sources; it does not enforce six reflections plus one diffraction or reproduce each source's separate limits.",
        "A globally enabled diffuse solver retains the geometry's per-material model translation; it does not turn explicit scattering_model=none into an active model.",
        "Source global diffuse-disabled status is not used to force non-none material coefficients to zero; enabling diffuse on a mixed-source synthetic scene is a project adaptation assumption.",
        "Diffraction, edge diffraction, refraction, and diffuse scattering have backend-specific semantics; profile switches do not establish physical or path equivalence.",
        "Antenna count/pattern, positions and bandwidth/OFDM settings are task configuration, not inherited source antenna settings.",
    ]
    return {
        "schema_version": 1, "name": name, "defaults": dict(defaults),
        "effective": {key: resolved[key] for key in defaults},
        "values_differing_from_defaults": {key: resolved[key] for key in defaults if resolved[key] != defaults[key]},
        "source_evidence_attached": audit is not None,
        "source_count": evidence.get("source_count", 0),
        "ray_budget_policy": {
            "kind": "explicit_configurable_heuristic_not_source_equivalent",
            "samples_per_src": resolved.get("samples_per_src"),
            "max_num_paths_per_src": resolved.get("max_num_paths_per_src"),
            "source_num_rays_values": evidence.get("standard_values", {}).get("num_rays", []),
            "note": "Primary ray budget remains task-controlled; neither copied source num_rays nor equal numerical counts establish solver equivalence.",
        },
        "material_scattering_policy": {
            "policy": "retain_source_material_models_with_explicit_geometry_translation",
            "source_global_disabled_forces_zero": False,
            "global_diffuse_enabled": resolved["diffuse_reflection"],
            "globally_disabled_source_adaptations": disabled if resolved["diffuse_reflection"] else [],
            "source_global_status_unknown": unknown,
            "adaptation_is_assumption": True,
        },
        "assumptions": assumptions,
    }
