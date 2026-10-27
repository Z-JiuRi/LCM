"""Export source city surfaces and an outdoor UE candidate grid, without RT.

The scene is a synthetic planning layout, not a surveyed city. Region labels
are planning roles and candidates are sounding positions, not subscribers.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import gzip
import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

import numpy as np
from shapely import affinity, constrained_delaunay_triangles, get_parts
from shapely.geometry import Polygon
from shapely.ops import unary_union

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCENE = REPO_ROOT / "data/cities/city-1km/scene.json.gz"
DEFAULT_OUTPUT = REPO_ROOT / "data/csi/city-1km-geometry"
ASSUMED_CONCRETE = {
    "permittivity": 5.31, "conductivity": 0.08987, "thickness": 0.3,
    "scattering_model": "lambertian", "scattering_coefficient": 0.2,
    "cross_polarization_coefficient": 0.4,
}


@dataclass
class MaterialSpec:
    key: str
    group: str
    permittivity: float
    conductivity: float
    thickness: float
    scattering_coefficient: float
    xpd_coefficient: float
    scattering_pattern: str
    provenance: str
    reference_frequency_hz: float | None = None
    assumed: bool = False
    scattering_kwargs: dict = field(default_factory=dict)
    source_record: dict = field(default_factory=dict)
    scattering_assumptions: list[str] = field(default_factory=list)


def load_scene(scene_path: Path) -> dict:
    """Read the saved gzipped JSON scene (no propagation imports)."""
    return json.loads(gzip.decompress(Path(scene_path).read_bytes()))


def _triangulate_face(raw: np.ndarray) -> list[np.ndarray]:
    """Projected CDT, exact source 3D vertices, and source winding.

    Reject unsupported geometry instead of repairing it or using a convex fan.
    The absolute 1e-7 m planarity tolerance only permits numerical roundoff.
    Ground omission is an export policy applied separately in WORLD coordinates.
    """
    points = np.asarray(raw, dtype=float)
    if points.ndim != 2 or points.shape[1] != 3 or not np.isfinite(points).all():
        raise ValueError("Face vertices must be finite Nx3 coordinates")
    if len(points) > 3 and np.array_equal(points[0], points[-1]):
        points = points[:-1]
    if len(points) < 3:
        raise ValueError("Face has fewer than three vertices")
    normal = np.sum(np.cross(points - points[0], np.roll(points - points[0], -1, axis=0)), axis=0)
    norm = np.linalg.norm(normal)
    if norm < 1e-12:
        raise ValueError("Degenerate face normal")
    normal /= norm
    deviation = float(np.max(np.abs((points - points[0]) @ normal)))
    if deviation > 1e-7:
        raise ValueError(f"Nonplanar face: deviation {deviation:g} m")
    axes = [i for i in range(3) if i != int(np.argmax(np.abs(normal)))]
    flat = points[:, axes]
    polygon = Polygon(flat)
    if not polygon.is_valid or polygon.area <= 1e-12 or len(np.unique(flat, axis=0)) != len(flat):
        raise ValueError("Invalid or degenerate projected face")
    triangles = []
    projected = []
    for triangle in get_parts(constrained_delaunay_triangles(polygon)):
        ring = np.asarray(triangle.exterior.coords, dtype=float)[:-1]
        if ring.shape != (3, 2):
            raise ValueError("CDT returned a non-triangle")
        indices = []
        for q in ring:
            matches = np.flatnonzero(np.all(flat == q, axis=1))
            if len(matches) != 1:
                raise ValueError("CDT vertex does not map to an exact source 3D vertex")
            indices.append(int(matches[0]))
        tri = points[indices].copy()
        alignment = np.dot(np.cross(tri[1] - tri[0], tri[2] - tri[0]), normal)
        if abs(alignment) <= 1e-12:
            raise ValueError("CDT returned a degenerate triangle")
        if alignment < 0:
            tri = tri[[0, 2, 1]]
        triangles.append(tri)
        projected.append(triangle)
    if not triangles or not polygon.equals(unary_union(projected)):
        raise ValueError("CDT does not cover the source face")
    return triangles


def _placed_footprint(asset: dict, instance: dict) -> Polygon:
    footprint = asset["footprint"]
    polygon = Polygon(footprint["outer"], footprint.get("holes", []))
    if polygon.is_empty or not polygon.is_valid or polygon.area <= 0:
        raise ValueError(f"Invalid footprint for asset {asset.get('id')}")
    position = np.asarray(instance["position_m"], dtype=float)
    angle = float(instance.get("rotation_z_deg", 0.0))
    if position.shape != (3,) or not np.isfinite(position).all() or not math.isfinite(angle):
        raise ValueError("Invalid instance transform")
    polygon = affinity.rotate(polygon, angle, origin=(0, 0))
    return affinity.translate(polygon, *position[:2])


def building_footprints(scene: dict) -> list[Polygon]:
    assets = {a["id"]: a for a in scene["assets"]}
    return [_placed_footprint(assets[i["asset"]], i) for i in scene["instances"]]


def vegetation_footprints(scene: dict) -> list[Polygon]:
    """All vegetation excludes UE placement; foliage propagation is unsupported."""
    environment = scene.get("environment", {})
    assets = {a["id"]: a for a in environment.get("vegetation_assets", [])}
    if environment.get("rt_enabled") or any(a.get("rt_enabled") for a in assets.values()):
        raise ValueError("RT-enabled vegetation has no implemented foliage model")
    footprints = []
    for instance in environment.get("vegetation_instances", []):
        if instance.get("rt_enabled"):
            raise ValueError("RT-enabled vegetation has no implemented foliage model")
        if instance["asset"] not in assets:
            raise ValueError(f"Missing vegetation asset: {instance['asset']}")
        footprints.append(_placed_footprint(assets[instance["asset"]], instance))
    return footprints


def _write_obj(path: Path, vertices: np.ndarray, triangles: np.ndarray) -> None:
    """Round-trip double precision coordinates; preserve exact source vertices."""
    with path.open("x", encoding="utf-8") as handle:
        for vertex in vertices:
            handle.write("v " + " ".join(f"{v:.17g}" for v in vertex) + "\n")
        for triangle in triangles:
            handle.write("f " + " ".join(str(int(i) + 1) for i in triangle) + "\n")


def _safe_name(key: str) -> str:
    """Filesystem/RT identifier with a digest to avoid sanitized-name collisions."""
    label = "".join(c if c.isascii() and (c.isalnum() or c in "-_.") else "_" for c in key)
    return (label.strip("_.") or "unnamed")[:100] + "_" + hashlib.sha256(key.encode()).hexdigest()[:16]


def export_buildings(scene: dict, out_dir: Path, group_by_material: bool = True) -> list[dict]:
    """Export each face with its own material; never collapse mixed bindings."""
    if not group_by_material:
        raise ValueError("Disabling per-face material grouping is unsupported")
    assets = {a["id"]: a for a in scene["assets"]}
    buckets = {}
    omitted = 0
    for instance_index, instance in enumerate(scene["instances"]):
        asset = assets[instance["asset"]]
        faces = asset["faces"]
        material_keys = asset.get("face_material_keys")
        if material_keys is None:
            raise ValueError(f"Missing face material keys for {asset['id']}; use explicit assumed:concrete")
        if len(material_keys) != len(faces):
            raise ValueError(f"Face/material count mismatch for {asset['id']}")
        theta = math.radians(float(instance.get("rotation_z_deg", 0.0)))
        rotation = np.array([[math.cos(theta), -math.sin(theta), 0.0],
                             [math.sin(theta), math.cos(theta), 0.0], [0.0, 0.0, 1.0]])
        position = np.asarray(instance["position_m"], dtype=float)
        if position.shape != (3,) or not np.isfinite(position).all() or not np.isfinite(rotation).all():
            raise ValueError("Invalid building transform")
        for face_index, (raw, key) in enumerate(zip(faces, material_keys)):
            if not isinstance(key, str) or not key:
                raise ValueError("Material keys must be nonempty strings")
            # Validate BEFORE the only permitted omission. Local-z0 faces of
            # elevated instances remain in the exported scene.
            try:
                local = _triangulate_face(raw)
            except ValueError as error:
                raise ValueError(f"{asset['id']} face {face_index}: {error}") from error
            world = [tri @ rotation.T + position for tri in local]
            if all(np.all(tri[:, 2] == 0.0) for tri in world):
                omitted += 1
                continue
            bucket = buckets.setdefault(key, {"vertices": [], "triangles": [], "instances": set(), "faces": 0})
            for tri in world:
                offset = len(bucket["vertices"])
                bucket["vertices"].extend(tri)
                bucket["triangles"].append([offset, offset + 1, offset + 2])
            bucket["instances"].add(instance_index)
            bucket["faces"] += 1
    groups = []
    for key, bucket in sorted(buckets.items()):
        name = _safe_name(key)
        obj_path = out_dir / f"group_building_{name}.obj"
        triangles = np.asarray(bucket["triangles"], dtype=np.int64)
        _write_obj(obj_path, np.asarray(bucket["vertices"]), triangles)
        groups.append({"material_key": key, "material_name": name, "obj": obj_path.name,
                       "triangles": len(triangles), "instances": len(bucket["instances"]),
                       "faces": bucket["faces"], "world_z0_faces_omitted_total": omitted})
    return groups


def export_terrain(scene: dict, out_dir: Path) -> list[dict]:
    """Validate source triangle indices and their complete role/material binding."""
    terrain = scene.get("environment", {}).get("terrain")
    if not terrain:
        return []
    vertices = np.asarray(terrain["vertices"], dtype=float)
    raw_triangles = np.asarray(terrain["triangles"])
    if vertices.ndim != 2 or vertices.shape[1] != 3 or not np.isfinite(vertices).all():
        raise ValueError("Terrain vertices must be finite Nx3 coordinates")
    if raw_triangles.ndim != 2 or raw_triangles.shape[1] != 3 or raw_triangles.dtype.kind not in "iu":
        raise ValueError("Terrain triangle indices must be an integer Nx3 array")
    if np.any(raw_triangles < 0) or np.any(raw_triangles >= len(vertices)):
        raise ValueError("Terrain triangle index out of bounds")
    triangles = raw_triangles.astype(np.int64)
    if len(triangles) == 0:
        raise ValueError("Terrain contains no triangles")
    t = vertices[triangles]
    if np.any(np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1) <= 1e-12):
        raise ValueError("Degenerate terrain triangle")
    roles = terrain["triangle_roles"]
    material_keys = terrain["triangle_material_keys"]
    if len(roles) != len(triangles) or len(material_keys) != len(triangles):
        raise ValueError("Terrain triangle/role/material count mismatch")
    buckets = {}
    for index, (role, key) in enumerate(zip(roles, material_keys)):
        if not isinstance(role, str) or not role or not isinstance(key, str) or not key:
            raise ValueError("Terrain roles/material keys must be nonempty strings")
        buckets.setdefault((role, key), []).append(index)
    groups = []
    for (role, key), indices in sorted(buckets.items()):
        local_triangles = triangles[indices]
        used, inverse = np.unique(local_triangles, return_inverse=True)
        name = _safe_name(key)
        obj_path = out_dir / f"group_terrain_{_safe_name(role)}_{name}.obj"
        _write_obj(obj_path, vertices[used], inverse.reshape(-1, 3))
        groups.append({"material_key": key, "material_name": name, "terrain_role": role,
                       "obj": obj_path.name, "triangles": len(local_triangles)})
    return groups


def _number(record: dict, name: str, minimum: float, maximum: float | None = None) -> float:
    if name not in record or isinstance(record[name], bool):
        raise ValueError(f"Missing/invalid required material parameter {name}")
    try:
        value = float(record[name])
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid material parameter {name}") from error
    if not math.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"Material parameter {name} outside supported range")
    return value


def resolve_materials(scene: dict, used_keys: Iterable[str]) -> list[MaterialSpec]:
    """Translate supported scattering models, retaining every original record."""
    records = scene.get("materials", {})
    specs = []
    for key in sorted(set(used_keys)):
        assumed = key == "assumed:concrete" and key not in records
        if key not in records and not assumed:
            raise ValueError(f"Missing material record: {key}")
        record = deepcopy(ASSUMED_CONCRETE if assumed else records[key])
        epsilon = _number(record, "permittivity", 1.0)
        sigma = _number(record, "conductivity", 0.0)
        thickness = _number(record, "thickness", 0.0)
        assumptions = []
        model = record.get("scattering_model")
        kwargs = {}
        if model == "none":
            pattern = "lambertian"
            scattering = 0.0
            assumptions.append("Source scattering_model=none: diffuse scattering explicitly disabled (coefficient=0); original coefficient retained in source_record. Lambertian is an inactive API placeholder.")
        elif model in ("lambertian", "directive", "backscattering"):
            pattern = model
            scattering = _number(record, "scattering_coefficient", 0.0, 1.0)
            parameters = ("alpha_r",) if model == "directive" else (("alpha_r", "alpha_i", "lambda_param") if model == "backscattering" else ())
            for parameter in parameters:
                value = _number(record, parameter, 0.0 if parameter == "lambda_param" else 1.0,
                                1.0 if parameter == "lambda_param" else None)
                if parameter != "lambda_param":
                    if not value.is_integer():
                        raise ValueError(f"{parameter} must be an integer scattering exponent")
                    value = int(value)
                kwargs["lambda_" if parameter == "lambda_param" else parameter] = value
            if model == "directive":
                assumptions.append("Sionna directive uses alpha_r only; source alpha_i/lambda_param and other unused fields remain unmodified in source_record, not interpreted as backscattering.")
        else:
            raise ValueError(f"Unsupported scattering_model for {key}: {model!r}")
        if "cross_polarization_coefficient" in record:
            xpd = _number(record, "cross_polarization_coefficient", 0.0, 1.0)
        elif scattering == 0.0:
            xpd = 0.0
            assumptions.append("Missing cross-polarization coefficient: inactive zero assumed because diffuse scattering is disabled.")
        else:
            raise ValueError(f"Missing cross_polarization_coefficient for {key}")
        reference = _number(record, "reference_frequency_hz", 0.0) if record.get("reference_frequency_hz") is not None else None
        if reference is not None and reference <= 0:
            raise ValueError("Reference frequency must be positive")
        provenance = str(record.get("provenance") or record.get("name") or "scene material record")
        if assumed:
            provenance = "Explicit assumed:concrete fallback; ITU-concrete-like numerical and diffuse-scattering assumptions, not source measurements."
        specs.append(MaterialSpec(key, _safe_name(key), epsilon, sigma, thickness, scattering, xpd,
                                  pattern, provenance, reference, assumed, kwargs, record, assumptions))
    return specs


def build_ue_grid(scene: dict, spacing_m: float, ue_height_m: float,
                  building_clearance_m: float, vegetation_clearance_m: float,
                  extent_m: tuple[float, float, float, float]) -> tuple[np.ndarray, dict]:
    """Exclude all footprint interiors/boundaries even with zero clearance."""
    values = [spacing_m, ue_height_m, building_clearance_m, vegetation_clearance_m]
    if not all(math.isfinite(v) for v in values) or spacing_m <= 0 or any(v < 0 for v in values[1:]):
        raise ValueError("Spacing must be positive; UE height and clearances must be finite and nonnegative")
    if len(extent_m) != 4 or not all(math.isfinite(v) for v in extent_m):
        raise ValueError("Extent must contain four finite coordinates")
    x0, y0, x1, y1 = extent_m
    if x1 <= x0 or y1 <= y0:
        raise ValueError("Extent must have positive width and height")
    xs = x0 + (np.arange(int(np.floor((x1 - x0) / spacing_m))) + 0.5) * spacing_m
    ys = y0 + (np.arange(int(np.floor((y1 - y0) / spacing_m))) + 0.5) * spacing_m
    footprints = building_footprints(scene)
    vegetation = vegetation_footprints(scene)
    # Same exclusion rule as distance to the union, without measuring every
    # candidate against a city-sized multipolygon. Bounded vector batches and
    # STRtree nearest distances keep the 4 km / 5 m grid practical on a laptop.
    from shapely import points as make_points
    from shapely.strtree import STRtree
    obstacles = [(STRtree(polygons), clearance) for polygons, clearance in
                 ((footprints, building_clearance_m), (vegetation, vegetation_clearance_m)) if polygons]
    keep = []
    total = len(xs) * len(ys)
    for start in range(0, total, 20000):
        indices = np.arange(start, min(start + 20000, total))
        xy = np.column_stack((xs[indices % len(xs)], ys[indices // len(xs)]))
        probes = make_points(xy)
        accepted = np.ones(len(xy), dtype=bool)
        for tree, clearance in obstacles:
            pairs, distances = tree.query_nearest(probes, all_matches=False, return_distance=True)
            # Distance zero includes interiors AND boundaries, even at zero margin.
            rejected = (distances == 0) | (distances < clearance)
            accepted[pairs[0, rejected]] = False
        if accepted.any():
            keep.append(np.column_stack((xy[accepted], np.full(accepted.sum(), ue_height_m))))
    positions = np.concatenate(keep) if keep else np.empty((0, 3), dtype=float)
    return positions, {"grid_spacing_m": spacing_m, "grid_nodes_total": len(xs) * len(ys),
                       "ue_candidates": len(positions), "building_clearance_m": building_clearance_m,
                       "vegetation_clearance_m": vegetation_clearance_m, "ue_height_m": ue_height_m}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(scene_path: Path, out_dir: Path, spacing_m: float = 5.0,
            ue_height_m: float = 1.5, building_clearance_m: float = 2.0,
            vegetation_clearance_m: float = 1.0) -> dict:
    """Refuse existing output; export nonempty geometry/grid and content hashes."""
    scene_path, out_dir = Path(scene_path).resolve(), Path(out_dir).resolve()
    if out_dir.exists():
        raise FileExistsError(f"Refusing existing output directory: {out_dir}")
    raw = scene_path.read_bytes()
    scene = json.loads(gzip.decompress(raw))
    extent_m = tuple(float(v) for v in scene.get("ground", {}).get("extent_m", [0, 0, 1000, 1000]))
    positions, ue_stats = build_ue_grid(scene, spacing_m, ue_height_m, building_clearance_m,
                                      vegetation_clearance_m, extent_m)
    if len(positions) == 0:
        raise ValueError("No outdoor UE candidates; refusing empty export")
    # Validate material records before writing any geometry, including omitted faces.
    used_keys = []
    for asset in scene["assets"]:
        keys = asset.get("face_material_keys")
        if keys is None or len(keys) != len(asset["faces"]):
            raise ValueError(f"Missing/mismatched face material keys for {asset['id']}")
        used_keys.extend(keys)
    terrain = scene.get("environment", {}).get("terrain")
    if terrain:
        used_keys.extend(terrain["triangle_material_keys"])
    resolve_materials(scene, used_keys)
    out_dir.mkdir(parents=True, exist_ok=False)
    groups = export_buildings(scene, out_dir) + export_terrain(scene, out_dir)
    if not groups:
        raise ValueError("No geometry triangles; refusing empty export")
    materials = resolve_materials(scene, [g["material_key"] for g in groups])
    ue_path = out_dir / "ue_candidates.npy"
    np.save(ue_path, positions)
    for group in groups:
        group["sha256"] = _sha256(out_dir / group["obj"])
    hashes = {g["obj"]: g["sha256"] for g in groups}
    hashes[ue_path.name] = _sha256(ue_path)
    manifest = {
        "source_scene": str(scene_path), "scene_sha256": hashlib.sha256(raw).hexdigest(),
        "extent_m": list(extent_m), "groups": groups, "materials": [vars(m) for m in materials],
        "ue_stats": ue_stats, "ue_candidates_sha256": hashes[ue_path.name], "artifact_sha256": hashes,
        "assumptions": [
            "Geometry is a synthetic planning layout, not a surveyed city.",
            "Region labels are planning roles, not measured population; UE candidates are a sounding grid, not active subscribers.",
            "Source face winding preserved; no claim of outward normals or watertight meshes.",
            "Only building faces exactly coplanar with world z=0 are omitted to avoid duplicate ground surfaces; elevated local-z0 faces retained.",
            "Vegetation propagation is disabled and RT-enabled vegetation rejected; all vegetation footprints exclude UE candidates.",
            "Source material records are retained. Scattering translation is an explicit model assumption, not a validated source-equivalence claim.",
        ],
    }
    with (out_dir / "geometry-manifest.json").open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, default=DEFAULT_SCENE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--spacing", type=float, default=5.0, help="UE grid spacing in metres (default: 5)")
    parser.add_argument("--ue-height", type=float, default=1.5)
    parser.add_argument("--building-clearance", type=float, default=2.0)
    parser.add_argument("--vegetation-clearance", type=float, default=1.0)
    args = parser.parse_args()
    manifest = prepare(args.scene, args.output, args.spacing, args.ue_height,
                       args.building_clearance, args.vegetation_clearance)
    print(json.dumps({"output": str(args.output.resolve()), "groups": len(manifest["groups"]),
                      "ue_candidates": manifest["ue_stats"]["ue_candidates"]}))


if __name__ == "__main__":
    main()
