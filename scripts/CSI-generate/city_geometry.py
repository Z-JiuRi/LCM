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


_TOPOLOGY_COUNTS = (
    "vertices", "triangles", "edges", "boundary_edges", "boundary_edges_world_z0",
    "interior_edges", "nonmanifold_edges", "winding_conflict_edges",
    "coplanar_interior_edges", "noncoplanar_interior_edges",
    "source_face_internal_edges", "cross_material_edges",
    "cross_material_coplanar_edges", "cross_material_noncoplanar_edges",
    "cross_group_edges", "cross_group_coplanar_edges", "cross_group_noncoplanar_edges",
    "degenerate_triangles", "near_degenerate_triangle_count",
    "upward_triangles", "downward_triangles", "vertical_triangles",
)
_NEAR_DEGENERATE_AREA_M2 = 1e-6  # Diagnostic only; never delete or move a source triangle.


def _sum_topology(records: Iterable[dict]) -> dict:
    total = dict.fromkeys(_TOPOLOGY_COUNTS, 0)
    minimum_areas = []
    for record in records:
        for key in _TOPOLOGY_COUNTS:
            total[key] += record[key]
        if record["min_triangle_area_m2"] is not None:
            minimum_areas.append(record["min_triangle_area_m2"])
    total["min_triangle_area_m2"] = min(minimum_areas) if minimum_areas else None
    return total


def mesh_topology(vertices: np.ndarray, triangles: np.ndarray,
                  material_keys: list[str] | None = None,
                  group_keys: list | None = None, source_faces: list | None = None) -> dict:
    """Diagnose indexed adjacency; never move vertices or change triangle winding.

    Coplanarity uses |dot(n0,n1)| >= 1-1e-10 (also for reversed winding).
    It is a diagnostic angular tolerance, NOT a coordinate welding tolerance.
    Cross-material/group counts concern physical shared edges with exactly two
    incident triangles; nonmanifold edges are counted separately and fail gates.
    Independent building instances must be indexed separately before this call.
    """
    vertices = np.asarray(vertices, dtype=float).reshape(-1, 3)
    triangles = np.asarray(triangles, dtype=np.int64).reshape(-1, 3)
    result = dict.fromkeys(_TOPOLOGY_COUNTS, 0)
    result.update(vertices=len(vertices), triangles=len(triangles), min_triangle_area_m2=None)
    if not len(triangles):
        return result
    points = vertices[triangles]
    normals = np.cross(points[:, 1] - points[:, 0], points[:, 2] - points[:, 0])
    lengths = np.linalg.norm(normals, axis=1)
    valid = lengths > 1e-12
    normals[valid] /= lengths[valid, None]
    result["degenerate_triangles"] = int(np.count_nonzero(~valid))
    result["near_degenerate_triangle_count"] = int(np.count_nonzero(lengths / 2 <= _NEAR_DEGENERATE_AREA_M2))
    result["min_triangle_area_m2"] = float(np.min(lengths) / 2)
    result["upward_triangles"] = int(np.count_nonzero(valid & (normals[:, 2] > 1e-10)))
    result["downward_triangles"] = int(np.count_nonzero(valid & (normals[:, 2] < -1e-10)))
    result["vertical_triangles"] = int(np.count_nonzero(valid & (np.abs(normals[:, 2]) <= 1e-10)))
    edges = {}
    for face, indices in enumerate(triangles):
        for a, b in zip(indices, np.roll(indices, -1)):
            a, b = int(a), int(b)
            edges.setdefault((min(a, b), max(a, b)), []).append((face, a < b))
    result["edges"] = len(edges)
    for (a, b), incident in edges.items():
        if len(incident) == 1:
            result["boundary_edges"] += 1
            result["boundary_edges_world_z0"] += int(vertices[a, 2] == vertices[b, 2] == 0.0)
        elif len(incident) > 2:
            result["nonmanifold_edges"] += 1
        else:
            (f0, forward0), (f1, forward1) = incident
            result["interior_edges"] += 1
            result["winding_conflict_edges"] += int(forward0 == forward1)
            coplanar = abs(float(np.dot(normals[f0], normals[f1]))) >= 1.0 - 1e-10
            suffix = "coplanar_edges" if coplanar else "noncoplanar_edges"
            result["coplanar_interior_edges" if coplanar else "noncoplanar_interior_edges"] += 1
            if source_faces is not None and source_faces[f0] == source_faces[f1]:
                result["source_face_internal_edges"] += 1
            if material_keys is not None and material_keys[f0] != material_keys[f1]:
                result["cross_material_edges"] += 1
                result["cross_material_" + suffix] += 1
            if group_keys is not None and group_keys[f0] != group_keys[f1]:
                result["cross_group_edges"] += 1
                result["cross_group_" + suffix] += 1
    return result


def _indexed_asset(asset: dict) -> tuple[np.ndarray, np.ndarray, list[str], list[int]]:
    """Index exact local coordinates once; no tolerance weld or winding repair."""
    faces, keys = asset["faces"], asset.get("face_material_keys")
    if keys is None or len(keys) != len(faces):
        raise ValueError(f"Missing/mismatched face material keys for {asset['id']}")
    vertices, triangles, materials, source_faces = [], [], [], []
    index = {}
    for face_index, (raw, key) in enumerate(zip(faces, keys)):
        if not isinstance(key, str) or not key:
            raise ValueError("Material keys must be nonempty strings")
        try:
            face_triangles = _triangulate_face(raw)
        except ValueError as error:
            raise ValueError(f"{asset['id']} face {face_index}: {error}") from error
        for triangle in face_triangles:
            indices = []
            for vertex in triangle:
                coordinate = tuple(vertex)
                if coordinate not in index:
                    index[coordinate] = len(vertices)
                    vertices.append(vertex)
                indices.append(index[coordinate])
            triangles.append(indices)
            materials.append(key)
            source_faces.append(face_index)
    return (np.asarray(vertices, dtype=float).reshape(-1, 3),
            np.asarray(triangles, dtype=np.int64).reshape(-1, 3), materials, source_faces)


def export_buildings(scene: dict, out_dir: Path, group_by_material: bool = True,
                     *, diagnostics: dict | None = None) -> list[dict]:
    """Share exact vertices per INSTANCE and material, never across buildings.

    OBJ files may contain multiple instances of one material, but each instance
    has a disjoint index range even when its coordinates coincide with another.
    Physical adjacency is diagnosed before material partitioning; unsupported
    cross-material wedges remain explicit, not silently assigned one material.
    """
    if not group_by_material:
        raise ValueError("Disabling per-face material grouping is unsupported")
    assets = {a["id"]: a for a in scene["assets"]}
    indexed_assets, buckets, physical = {}, {}, []
    omitted = mixed = affected = 0
    issues = []
    for instance_index, instance in enumerate(scene["instances"]):
        asset = assets[instance["asset"]]
        if asset["id"] not in indexed_assets:
            indexed_assets[asset["id"]] = _indexed_asset(asset)
        local_vertices, all_triangles, all_materials, all_faces = indexed_assets[asset["id"]]
        theta = math.radians(float(instance.get("rotation_z_deg", 0.0)))
        rotation = np.array([[math.cos(theta), -math.sin(theta), 0.0],
                             [math.sin(theta), math.cos(theta), 0.0], [0.0, 0.0, 1.0]])
        position = np.asarray(instance["position_m"], dtype=float)
        if position.shape != (3,) or not np.isfinite(position).all() or not np.isfinite(rotation).all():
            raise ValueError("Invalid building transform")
        world_vertices = local_vertices @ rotation.T + position
        # Omission is by complete source FACE, not triangle: near-planar faces
        # accepted by the numeric planarity tolerance must not be partly removed.
        triangle_at_z0 = np.all(world_vertices[all_triangles, 2] == 0.0, axis=1)
        face_at_z0 = {}
        for face, at_z0 in zip(all_faces, triangle_at_z0):
            face_at_z0[face] = face_at_z0.get(face, True) and bool(at_z0)
        omitted_faces = {face for face, at_z0 in face_at_z0.items() if at_z0}
        keep = np.asarray([face not in omitted_faces for face in all_faces], dtype=bool)
        omitted += len(omitted_faces)
        triangles = all_triangles[keep]
        materials = [all_materials[i] for i in np.flatnonzero(keep)]
        source_faces = [all_faces[i] for i in np.flatnonzero(keep)]
        mixed += int(len(set(materials)) > 1)
        used, inverse = np.unique(triangles, return_inverse=True)
        topology = mesh_topology(world_vertices[used], inverse.reshape(-1, 3), materials,
                                 materials, source_faces)
        physical.append(topology)
        if any(topology[k] for k in ("nonmanifold_edges", "winding_conflict_edges",
                                    "cross_material_edges", "degenerate_triangles")):
            affected += 1
            if len(issues) < 20:
                issues.append({"instance_index": instance_index, "asset_id": asset["id"],
                               "source_name": asset.get("source"), "topology": topology})
        for key in sorted(set(materials)):
            selection = [i for i, material in enumerate(materials) if material == key]
            used, inverse = np.unique(triangles[selection], return_inverse=True)
            bucket = buckets.setdefault(key, {"vertices": [], "triangles": [], "faces": 0,
                                              "source_faces": [], "instance_ranges": []})
            vertex_start, triangle_start = len(bucket["vertices"]), len(bucket["triangles"])
            bucket["vertices"].extend(world_vertices[used])
            bucket["triangles"].extend(inverse.reshape(-1, 3) + vertex_start)
            bucket["source_faces"].extend((instance_index, source_faces[i]) for i in selection)
            bucket["faces"] += len({source_faces[i] for i in selection})
            bucket["instance_ranges"].append({"instance_index": instance_index,
                "asset_id": asset["id"], "vertex_start": vertex_start, "vertex_count": len(used),
                "triangle_start": triangle_start, "triangle_count": len(selection)})
    groups = []
    for key, bucket in sorted(buckets.items()):
        name = _safe_name(key)
        obj_path = out_dir / f"group_building_{name}.obj"
        vertices, triangles = np.asarray(bucket["vertices"]), np.asarray(bucket["triangles"], dtype=np.int64)
        _write_obj(obj_path, vertices, triangles)
        groups.append({"material_key": key, "material_name": name, "obj": obj_path.name,
                       "role": "building", "vertices": len(vertices), "triangles": len(triangles),
                       "instances": len(bucket["instance_ranges"]), "faces": bucket["faces"],
                       "instance_ranges": bucket["instance_ranges"],
                       "topology": mesh_topology(vertices, triangles, source_faces=bucket["source_faces"]),
                       "world_z0_faces_omitted_total": omitted})
    if diagnostics is not None:
        diagnostics.update(building_physical=_sum_topology(physical),
                           building_exported=_sum_topology(g["topology"] for g in groups),
                           mixed_material_building_instances=mixed,
                           building_instances_with_topology_issues=affected,
                           building_issue_examples=issues, world_z0_faces_omitted=omitted)
    return groups


def export_terrain(scene: dict, out_dir: Path, *, diagnostics: dict | None = None) -> list[dict]:
    """Keep source indexing and diagnose physical edges BEFORE role/material splits."""
    terrain = scene.get("environment", {}).get("terrain")
    if not terrain:
        if diagnostics is not None:
            diagnostics.update(terrain_physical=_sum_topology([]), terrain_exported=_sum_topology([]))
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
        indexed = inverse.reshape(-1, 3)
        _write_obj(obj_path, vertices[used], indexed)
        groups.append({"material_key": key, "material_name": name, "terrain_role": role,
                       "role": "terrain", "obj": obj_path.name, "vertices": len(used),
                       "triangles": len(local_triangles),
                       "topology": mesh_topology(vertices[used], indexed)})
    if diagnostics is not None:
        diagnostics.update(terrain_physical=mesh_topology(vertices, triangles, material_keys,
                                                         list(zip(roles, material_keys))),
                           terrain_exported=_sum_topology(g["topology"] for g in groups))
    return groups


def _topology_gate(diagnostics: dict) -> dict:
    """Conservative diffraction gate; an export is diagnostic, not RT approval.

    Boundaries alone do not fail ordinary wedge diffraction (world-z0 building
    bottoms are deliberately open). Split coplanar seams do fail free-edge
    diffraction because native per-shape adjacency sees them as screen edges.
    """
    failures, edge_failures, warnings = [], [], []
    for role in ("building", "terrain"):
        physical = diagnostics[role + "_physical"]
        for count in ("nonmanifold_edges", "winding_conflict_edges", "degenerate_triangles"):
            if physical[count]:
                failures.append(f"{role}_{count}")
        if physical["cross_group_noncoplanar_edges"]:
            failures.append(f"{role}_unsupported_cross_group_wedges")
        if physical["boundary_edges"]:
            warnings.append(f"{role}_physical_open_boundaries")
        if physical["cross_group_coplanar_edges"]:
            edge_failures.append(f"{role}_split_coplanar_seams_are_false_free_edges")
        if physical["near_degenerate_triangle_count"]:
            warnings.append(f"{role}_source_near_degenerate_triangles_preserved")
        if role == "terrain" and physical["downward_triangles"]:
            warnings.append("terrain_source_downward_triangles_preserved")
    diagnostics.update(
        diffraction_ready=not failures, strict_gate_failures=failures,
        edge_diffraction_ready=not (failures or edge_failures),
        edge_diffraction_gate_failures=failures + edge_failures, warnings=warnings,
        unsupported_cross_material_wedges=sum(diagnostics[r + "_physical"]["cross_material_noncoplanar_edges"]
                                              for r in ("building", "terrain")),
        indexing="Exact source coordinates within each building instance/material; disjoint indices across instances. Terrain retains source vertex indexing.",
        coplanar_normal_dot_tolerance=1e-10,
        near_degenerate_area_threshold_m2=_NEAR_DEGENERATE_AREA_M2,
        numerical_precision_warning="Topology and areas are computed from source float64 coordinates. Mitsuba/Sionna typically loads float32 vertices; near-collinear slivers may change normal direction or collapse there. No automatic removal, upward flip, coordinate rounding or outward-normal repair is applied.",
        scope="Exported triangles after world-z0 omission. Physical building adjacency is checked within each instance before material splitting. No inter-building, building/terrain intersection, T-junction, self-intersection or outward-normal proof.",
        native_material_limitation="Sionna 2.2 uses one RadioMaterialBase BSDF per mesh; built-in RadioMaterial uses the same material for both wedge faces. Cross-shape wedges are unsupported; no material averaging or custom heterogeneous diffraction is applied.",
    )
    return diagnostics


def source_frequency_warnings(scene: dict, materials: list[MaterialSpec]) -> list[dict]:
    """Report source-reference mismatch/unknowns without rescaling any material."""
    frequencies = sorted({float(sector["carrier_frequency_hz"])
                          for sector in scene.get("radio_deployment", {}).get("sectors", [])
                          if isinstance(sector.get("carrier_frequency_hz"), (int, float))
                          and math.isfinite(sector["carrier_frequency_hz"])
                          and sector["carrier_frequency_hz"] > 0})
    warnings = []
    for material in materials:
        reference = material.reference_frequency_hz
        if reference is None:
            code = "missing_source_reference_frequency"
            message = "Source reference frequency is unspecified; frequency equivalence is unverified."
        elif not frequencies:
            code = "target_frequency_not_specified"
            message = "Exporter has no target carrier; compare source reference frequency with the requested RT carrier."
        elif any(f != reference for f in frequencies):
            code = "source_target_frequency_mismatch"
            message = "Source material reference differs from scene deployment carrier(s); parameters are retained, not rescaled."
        else:
            continue
        warnings.append({"material_key": material.key, "reference_frequency_hz": reference,
                         "scene_carrier_frequencies_hz": frequencies, "code": code, "message": message})
    return warnings


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
    topology = {}
    groups = (export_buildings(scene, out_dir, diagnostics=topology)
              + export_terrain(scene, out_dir, diagnostics=topology))
    _topology_gate(topology)
    if not groups:
        raise ValueError("No geometry triangles; refusing empty export")
    materials = resolve_materials(scene, [g["material_key"] for g in groups])
    ue_path = out_dir / "ue_candidates.npy"
    np.save(ue_path, positions)
    for group in groups:
        group["sha256"] = _sha256(out_dir / group["obj"])
    hashes = {g["obj"]: g["sha256"] for g in groups}
    hashes[ue_path.name] = _sha256(ue_path)
    used_asset_ids = {instance["asset"] for instance in scene["instances"]}
    source_names = {asset["source"] for asset in scene["assets"]
                    if asset["id"] in used_asset_ids and isinstance(asset.get("source"), str)
                    and asset["source"]}
    source_names.update(material.source_record["source_scene"] for material in materials
                        if isinstance(material.source_record.get("source_scene"), str)
                        and material.source_record["source_scene"])
    source_names = sorted(source_names)
    from parcel_groups import parcel_records
    manifest = {
        "parcels": parcel_records(scene),
        "schema_version": 2, "source_names": source_names, "topology": topology,
        "normals": {"source_winding_preserved": True, "face_normals": True,
                    "flip_normals": False, "outward_orientation_verified": False,
                    "winding_repaired": False},
        "source_frequency_warnings": source_frequency_warnings(scene, materials),
        "source_scene": str(scene_path), "scene_sha256": hashlib.sha256(raw).hexdigest(),
        "extent_m": list(extent_m), "groups": groups, "materials": [vars(m) for m in materials],
        "ue_stats": ue_stats, "ue_candidates_sha256": hashes[ue_path.name], "artifact_sha256": hashes,
        "assumptions": [
            "Geometry is a synthetic planning layout, not a surveyed city.",
            "Region labels are planning roles, not measured population; UE candidates are a sounding grid, not active subscribers.",
            "Source face winding preserved; no repair, tolerance welding, outward-normal proof or watertightness claim. Indexed adjacency diagnostics are not a full geometry validity proof.",
            "Loader must use face_normals=True, flip_normals=False and remove_duplicate_vertices=False; native SceneObject(fname=...) otherwise flips normals by default in installed Sionna 2.2.",
            "Material partitioning preserves exact tags but cannot represent native cross-material wedges. Consult strict diffraction and free-edge diffraction gates separately.",
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
