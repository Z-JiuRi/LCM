"""Small CPU geometry/topology tests; no Sionna import and no ray tracing."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
import city_geometry as C


def cube_scene():
    # Outward-oriented faces. The base is elevated, so all six faces survive.
    vertices = np.array([[0, 0, 1], [2, 0, 1], [2, 2, 1], [0, 2, 1],
                         [0, 0, 3], [2, 0, 3], [2, 2, 3], [0, 2, 3]], float)
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
             [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    material = dict(permittivity=5.31, conductivity=.08987, thickness=.3,
                    scattering_model="none", scattering_coefficient=.2,
                    cross_polarization_coefficient=.4, reference_frequency_hz=3.5e9)
    return dict(assets=[dict(id="cube", source="test_source", faces=[vertices[f].tolist() for f in faces],
                            face_material_keys=["A"] * 6,
                            footprint={"outer": [[0, 0], [2, 0], [2, 2], [0, 2]]})],
                instances=[dict(asset="cube", position_m=[0, 0, 0], rotation_z_deg=0)],
                materials={"A": material, "B": deepcopy(material)}, environment={},
                ground={"extent_m": [0, 0, 10, 10]})


def read_obj(path):
    vertices, faces = [], []
    for line in path.read_text().splitlines():
        tag, *values = line.split()
        if tag == "v":
            vertices.append([float(v) for v in values])
        elif tag == "f":
            faces.append([int(v) - 1 for v in values])
    return np.asarray(vertices), np.asarray(faces)


class TopologyTests(unittest.TestCase):
    def export(self, scene, directory):
        diagnostics = {}
        groups = C.export_buildings(scene, directory, diagnostics=diagnostics)
        groups += C.export_terrain(scene, directory, diagnostics=diagnostics)
        return groups, C._topology_gate(diagnostics)

    def test_cube_shared_vertices_and_internal_diagonals(self):
        with tempfile.TemporaryDirectory() as d:
            groups, report = self.export(cube_scene(), Path(d))
            self.assertEqual(len(groups), 1)
            group = groups[0]
            vertices, faces = read_obj(Path(d) / group["obj"])
            self.assertEqual(vertices.shape, (8, 3))
            self.assertEqual(faces.shape, (12, 3))
            topology = group["topology"]
            self.assertEqual(topology["boundary_edges"], 0)
            self.assertEqual(topology["interior_edges"], 18)
            self.assertEqual(topology["coplanar_interior_edges"], 6)
            self.assertEqual(topology["source_face_internal_edges"], 6)
            self.assertEqual(topology["noncoplanar_interior_edges"], 12)
            self.assertEqual(topology["winding_conflict_edges"], 0)
            self.assertTrue(report["diffraction_ready"])
            self.assertTrue(report["edge_diffraction_ready"])
            # Positive signed volume confirms that the synthetic source winding
            # was not flipped, without claiming arbitrary real meshes are closed.
            p = vertices[faces]
            self.assertAlmostEqual(float(np.einsum("ij,ij->i", p[:, 0], np.cross(p[:, 1], p[:, 2])).sum() / 6), 8.)

    def test_coincident_independent_instances_are_not_welded(self):
        scene = cube_scene()
        scene["instances"].append(deepcopy(scene["instances"][0]))
        with tempfile.TemporaryDirectory() as d:
            groups, report = self.export(scene, Path(d))
            group = groups[0]
            vertices, faces = read_obj(Path(d) / group["obj"])
            self.assertEqual(vertices.shape, (16, 3))
            self.assertEqual(len(np.unique(vertices, axis=0)), 8)
            self.assertLess(faces[:12].max(), 8)
            self.assertGreaterEqual(faces[12:].min(), 8)
            self.assertEqual(group["instances"], 2)
            self.assertEqual(group["instance_ranges"][1]["vertex_start"], 8)
            self.assertEqual(report["building_physical"]["interior_edges"], 36)
            self.assertEqual(report["building_exported"]["nonmanifold_edges"], 0)

    def test_transform_preserves_exact_source_coordinates(self):
        scene = cube_scene()
        scene["instances"][0].update(rotation_z_deg=31., position_m=[123.5, -17., 8.])
        local, _, _, _ = C._indexed_asset(scene["assets"][0])
        theta = np.deg2rad(31.)
        # Use the same documented rigid transform, not rounding/tolerance welds.
        import math
        rotation = np.array([[math.cos(theta), -math.sin(theta), 0],
                             [math.sin(theta), math.cos(theta), 0], [0, 0, 1]])
        expected = local @ rotation.T + [123.5, -17., 8.]
        with tempfile.TemporaryDirectory() as d:
            groups, _ = self.export(scene, Path(d))
            vertices, _ = read_obj(Path(d) / groups[0]["obj"])
            np.testing.assert_array_equal(vertices, expected)

    def test_ground_bottom_omission_is_reported_not_fake_diagonals(self):
        scene = cube_scene()
        scene["instances"][0]["position_m"][2] = -1
        with tempfile.TemporaryDirectory() as d:
            groups, report = self.export(scene, Path(d))
            topology = groups[0]["topology"]
            self.assertEqual(topology["triangles"], 10)
            self.assertEqual(topology["boundary_edges"], 4)
            self.assertEqual(topology["boundary_edges_world_z0"], 4)
            self.assertEqual(topology["source_face_internal_edges"], 5)
            self.assertEqual(report["world_z0_faces_omitted"], 1)
            self.assertTrue(report["diffraction_ready"])

    def test_near_planar_face_is_not_partially_omitted(self):
        scene = cube_scene()
        scene["assets"][0]["faces"] = [[[0, 0, 0], [2, 0, 0], [2, 2, 1e-9], [0, 2, 0]]]
        scene["assets"][0]["face_material_keys"] = ["A"]
        with tempfile.TemporaryDirectory() as d:
            groups, report = self.export(scene, Path(d))
            self.assertEqual(groups[0]["triangles"], 2)
            self.assertEqual(report["world_z0_faces_omitted"], 0)

    def test_mixed_material_physical_wedges_fail_explicit_gate(self):
        scene = cube_scene()
        scene["assets"][0]["face_material_keys"][1] = "B"
        with tempfile.TemporaryDirectory() as d:
            groups, report = self.export(scene, Path(d))
            self.assertEqual({g["material_key"] for g in groups}, {"A", "B"})
            self.assertEqual(report["mixed_material_building_instances"], 1)
            self.assertEqual(report["building_physical"]["boundary_edges"], 0)
            self.assertEqual(report["building_exported"]["boundary_edges"], 8)
            self.assertEqual(report["building_physical"]["cross_material_noncoplanar_edges"], 4)
            self.assertEqual(report["unsupported_cross_material_wedges"], 4)
            self.assertFalse(report["diffraction_ready"])
            self.assertIn("building_unsupported_cross_group_wedges", report["strict_gate_failures"])
            self.assertEqual(report["building_issue_examples"][0]["asset_id"], "cube")

    def test_terrain_indexed_and_role_seams_reported(self):
        scene = cube_scene()
        scene["instances"] = []
        scene["environment"]["terrain"] = dict(vertices=[[0, 0, 0], [2, 0, 0], [2, 2, 0], [0, 2, 0]],
            triangles=[[0, 1, 2], [0, 2, 3]], triangle_roles=["park", "other"], triangle_material_keys=["A", "A"])
        with tempfile.TemporaryDirectory() as d:
            groups, report = self.export(scene, Path(d))
            self.assertEqual({g["terrain_role"] for g in groups}, {"park", "other"})
            self.assertTrue(all(g["role"] == "terrain" for g in groups))
            self.assertEqual(report["terrain_physical"]["interior_edges"], 1)
            self.assertEqual(report["terrain_physical"]["cross_material_edges"], 0)
            self.assertEqual(report["terrain_physical"]["cross_group_coplanar_edges"], 1)
            self.assertTrue(report["diffraction_ready"])
            self.assertFalse(report["edge_diffraction_ready"])
        scene["environment"]["terrain"]["triangle_roles"] = ["park", "park"]
        with tempfile.TemporaryDirectory() as d:
            groups, report = self.export(scene, Path(d))
            self.assertEqual(groups[0]["vertices"], 4)
            self.assertEqual(groups[0]["topology"]["boundary_edges"], 4)
            self.assertTrue(report["edge_diffraction_ready"])

    def test_cross_material_planar_seam_is_not_physical_wedge(self):
        scene = cube_scene()
        scene["instances"] = []
        scene["environment"]["terrain"] = dict(vertices=[[0, 0, 0], [2, 0, 0], [2, 2, 0], [0, 2, 0]],
            triangles=[[0, 1, 2], [0, 2, 3]], triangle_roles=["road", "park"], triangle_material_keys=["A", "B"])
        with tempfile.TemporaryDirectory() as d:
            _, report = self.export(scene, Path(d))
            self.assertEqual(report["terrain_physical"]["cross_material_coplanar_edges"], 1)
            self.assertEqual(report["unsupported_cross_material_wedges"], 0)
            self.assertTrue(report["diffraction_ready"])
            self.assertFalse(report["edge_diffraction_ready"])

    def test_winding_and_nonmanifold_are_diagnosed_not_repaired(self):
        vertices = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1]])
        triangles = np.array([[0, 1, 2], [0, 1, 3]])
        before = triangles.copy()
        topology = C.mesh_topology(vertices, triangles)
        self.assertEqual(topology["winding_conflict_edges"], 1)
        self.assertEqual(topology["coplanar_interior_edges"], 1)
        np.testing.assert_array_equal(triangles, before)
        topology = C.mesh_topology(vertices, np.vstack((triangles, [1, 0, 4])))
        self.assertEqual(topology["nonmanifold_edges"], 1)
        scene = cube_scene()
        scene["assets"][0]["faces"][1].reverse()
        with tempfile.TemporaryDirectory() as d:
            _, report = self.export(scene, Path(d))
            self.assertFalse(report["diffraction_ready"])
            self.assertIn("building_winding_conflict_edges", report["strict_gate_failures"])

    def test_near_degenerate_source_slivers_are_not_flipped(self):
        scene = cube_scene()
        scene["instances"] = []
        scene["environment"]["terrain"] = dict(vertices=[[0, 0, 0], [1, 0, 0], [2, -1e-8, 0]],
            triangles=[[0, 1, 2]], triangle_roles=["other"], triangle_material_keys=["A"])
        with tempfile.TemporaryDirectory() as d:
            groups, report = self.export(scene, Path(d))
            physical = report["terrain_physical"]
            self.assertEqual(physical["near_degenerate_triangle_count"], 1)
            self.assertAlmostEqual(physical["min_triangle_area_m2"], 5e-9)
            self.assertEqual(physical["downward_triangles"], 1)
            self.assertIn("terrain_source_near_degenerate_triangles_preserved", report["warnings"])
            self.assertIn("terrain_source_downward_triangles_preserved", report["warnings"])
            vertices, faces = read_obj(Path(d) / groups[0]["obj"])
            np.testing.assert_array_equal(vertices, scene["environment"]["terrain"]["vertices"])
            np.testing.assert_array_equal(faces, [[0, 1, 2]])

    def test_material_only_source_names_exclude_unused_records(self):
        scene = cube_scene()
        scene["instances"] = []
        scene["materials"]["A"]["source_scene"] = "terrain_only_source"
        scene["materials"]["B"]["source_scene"] = "unused_material_source"
        scene["environment"]["terrain"] = dict(vertices=[[0, 0, 0], [2, 0, 0], [2, 2, 0]],
            triangles=[[0, 1, 2]], triangle_roles=["park"], triangle_material_keys=["A"])
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "scene.json.gz"
            source.write_bytes(gzip.compress(json.dumps(scene).encode()))
            manifest = C.prepare(source, Path(d) / "geometry")
            self.assertEqual(manifest["source_names"], ["terrain_only_source"])

    def test_manifest_v2_sources_normals_frequency_warning(self):
        scene = cube_scene()
        unused = deepcopy(scene["assets"][0])
        unused.update(id="unused", source="not_used")
        scene["assets"].append(unused)
        scene["materials"]["A"]["reference_frequency_hz"] = 1e9
        scene["radio_deployment"] = {"sectors": [{"carrier_frequency_hz": 3.5e9}]}
        with tempfile.TemporaryDirectory() as d:
            source = Path(d) / "scene.json.gz"
            source.write_bytes(gzip.compress(json.dumps(scene).encode()))
            manifest = C.prepare(source, Path(d) / "geometry")
            self.assertEqual(manifest["schema_version"], 2)
            self.assertEqual(manifest["source_names"], ["test_source"])
            self.assertFalse(manifest["normals"]["flip_normals"])
            self.assertFalse(manifest["normals"]["winding_repaired"])
            self.assertTrue(manifest["normals"]["source_winding_preserved"])
            warning = manifest["source_frequency_warnings"][0]
            self.assertEqual(warning["code"], "source_target_frequency_mismatch")
            self.assertEqual(manifest["materials"][0]["conductivity"], .08987)
            self.assertEqual(manifest["materials"][0]["source_record"], scene["materials"]["A"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
