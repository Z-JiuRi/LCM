"""CPU-only source audit/profile tests; no Sionna, accelerator or ray tracing."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import propagation_profiles as P


def params_fixture(*, diffuse=False):
    """Small fixture following inspected downloaded standard/raw key paths."""
    return {
        "version": "fixture",
        "rt_params": {
            "frequency": 3.5e9, "max_path_depth": 7, "max_reflections": 6,
            "max_diffractions": 1, "max_scattering": int(diffuse),
            "max_transmissions": 0, "num_rays": 259200, "synthetic_array": True,
            "diffuse_reflections": 2,
            "raw_params": {
                "waveform": {"CarrierFrequency": 3.5e9, "bandwidth": 10e6},
                "antenna": {"type": "isotropic", "polarization": "vertical"},
                "model": {"max_reflections": 6, "max_wedge_diffractions": 1,
                          "max_transmissions": 0, "ray_spacing": 0.25},
                "diffuse_scattering": {"enabled": diffuse, "diffuse_reflections": 2,
                                       "final_interaction_only": True},
                "apg_acceleration": {"path_depth": 50},
            },
        },
        "materials": {"material_0": {"scattering_model": "directive", "scattering_coefficient": 0.2}},
    }


class SourceAuditTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def save_source(self, source, params=None):
        path = self.root / "data/deepmimo" / source / "params.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(params_fixture() if params is None else params), encoding="utf-8")
        return path

    def test_only_selected_sources_are_read(self):
        selected = self.save_source("selected")
        unselected = self.save_source("not_selected")
        unselected.write_text("broken JSON deliberately not read", encoding="utf-8")
        read = P._read_json
        with patch.object(P, "_read_json", wraps=read) as reader:
            audit = P.source_audit(["selected", "selected"], self.root)
        reader.assert_called_once_with(selected)
        self.assertEqual(audit["source_names"], ["selected"])
        self.assertEqual(audit["aggregate"]["source_count"], 1)
        row = audit["sources"][0]
        self.assertEqual(row["params_file"], "data/deepmimo/selected/params.json")
        self.assertEqual(row["standard"]["max_path_depth"], 7)
        self.assertEqual(row["raw"]["apg_path_depth"], 50)
        self.assertEqual(row["raw_field_paths"]["diffuse_enabled"], "rt_params.raw_params.diffuse_scattering.enabled")
        self.assertNotIn("raw_params", row["standard"])
        json.dumps(audit, allow_nan=False)

    def test_manifest_names_are_authoritative_and_order_stable(self):
        self.save_source("beta")
        self.save_source("alpha", params_fixture(diffuse=True))
        audit = P.source_audit({"source_names": ["beta", "alpha", "beta"],
                                "source_scene": "does-not-exist.json.gz"}, self.root)
        self.assertEqual(audit["source_names"], ["alpha", "beta"])
        self.assertEqual(audit["aggregate"]["diffuse_enabled_sources"], ["alpha"])
        self.assertEqual(audit["aggregate"]["diffuse_disabled_sources"], ["beta"])
        self.assertEqual(audit["aggregate"]["standard_values"]["frequency"], [3.5e9])

    def test_global_disable_is_not_material_none_or_zero(self):
        self.save_source("selected")
        audit = P.source_audit("selected", self.root)
        row = audit["sources"][0]
        self.assertFalse(row["diffuse_enabled"])
        self.assertEqual(row["standard"]["diffuse_reflections"], 2)
        self.assertEqual(row["material_scattering_model_counts"], {"directive": 1})
        metadata = P.profile_metadata({}, audit)
        policy = metadata["material_scattering_policy"]
        self.assertFalse(policy["source_global_disabled_forces_zero"])
        self.assertEqual(policy["globally_disabled_source_adaptations"], ["selected"])
        self.assertTrue(policy["adaptation_is_assumption"])

    def test_nested_raw_values_fallback(self):
        params = params_fixture()
        raw = params["rt_params"]["raw_params"]
        raw["studyarea"] = {key: {"values": raw.pop(key)}
                            for key in ("model", "diffuse_scattering", "apg_acceleration")}
        self.save_source("nested", params)
        row = P.source_audit(["nested"], self.root)["sources"][0]
        self.assertFalse(row["diffuse_enabled"])
        self.assertEqual(row["raw"]["max_diffractions"], 1)
        self.assertEqual(row["raw_field_paths"]["diffuse_enabled"],
                         "rt_params.raw_params.studyarea.diffuse_scattering.values.enabled")

    def test_raw_duplicates_and_standard_disagreement_are_exposed(self):
        params = params_fixture()
        raw = params["rt_params"]["raw_params"]
        raw["studyarea"] = {"diffuse_scattering": {"values": {"enabled": True}}}
        raw["model"]["max_reflections"] = 4
        self.save_source("conflict", params)
        audit = P.source_audit(["conflict"], self.root)
        row = audit["sources"][0]
        self.assertIsNone(row["diffuse_enabled"])
        self.assertEqual(row["standard"]["max_reflections"], 6)
        self.assertEqual(row["raw"]["max_reflections"], 4)
        self.assertEqual({item["kind"] for item in row["conflicts"]}, {"raw_duplicates", "standard_vs_raw"})
        self.assertEqual(audit["aggregate"]["diffuse_unknown_sources"], ["conflict"])
        self.assertEqual(audit["aggregate"]["sources_with_conflicts"], ["conflict"])

    def test_absent_enable_is_unknown_not_inferred_from_budgets(self):
        params = params_fixture(diffuse=True)
        del params["rt_params"]["raw_params"]["diffuse_scattering"]["enabled"]
        self.save_source("missing", params)
        row = P.source_audit(["missing"], self.root)["sources"][0]
        self.assertEqual(row["standard"]["max_scattering"], 1)
        self.assertEqual(row["raw"]["diffuse_reflections"], 2)
        self.assertIsNone(row["diffuse_enabled"])
        self.assertNotIn("diffuse_enabled", row["raw"])

    def test_nonboolean_enable_stays_unknown(self):
        params = params_fixture()
        params["rt_params"]["raw_params"]["diffuse_scattering"]["enabled"] = "false"
        self.save_source("text", params)
        self.assertIsNone(P.source_audit("text", self.root)["sources"][0]["diffuse_enabled"])

    def test_scene_uses_instantiated_assets_and_terrain_material_sources(self):
        for name in ("used", "ground"):
            self.save_source(name)
        scene = {
            "assets": [{"id": 1, "source": "used", "face_material_keys": ["wall"]},
                       {"id": 2, "source": "unused"}],
            "instances": [{"asset": 1}],
            "materials": {"wall": {"source_scene": "used"},
                          "floor": {"source_scene": "ground"},
                          "unused": {"source_scene": "unused"}},
            "environment": {"terrain": {"triangle_material_keys": ["floor"]},
                            "vegetation_assets": [{"source": "disabled_foliage"}]},
        }
        before = deepcopy(scene)
        audit = P.source_audit(scene, self.root)
        self.assertEqual(audit["source_names"], ["ground", "used"])
        self.assertEqual(scene, before)
        path = self.root / "scene.json.gz"
        path.write_bytes(gzip.compress(json.dumps(scene).encode()))
        self.assertEqual(P.source_audit(path, self.root), audit)

    def test_manifest_file_and_empty_selection(self):
        path = self.root / "geometry-manifest.json"
        path.write_text(json.dumps({"source_names": []}), encoding="utf-8")
        audit = P.source_audit(str(path), self.root)
        self.assertEqual(audit["source_names"], [])
        self.assertEqual(audit["aggregate"]["source_count"], 0)
        self.assertEqual(audit["aggregate"]["standard_values"], {})

    def test_old_manifest_requires_explicit_provenance(self):
        with self.assertRaisesRegex(ValueError, "source_names"):
            P.source_audit({"source_scene": "exists-or-not.json.gz"}, self.root)

    def test_source_name_path_escape_rejected(self):
        for name in ("../outside", "a/b", "a\\b", "", ".", "..", 23, "bad\x00name"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                P.source_audit([name], self.root)

    def test_missing_corrupt_or_schema_invalid_selected_sources_fail(self):
        with self.assertRaises(FileNotFoundError):
            P.source_audit(["missing"], self.root)
        invalid = self.save_source("broken")
        invalid.write_text("[", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            P.source_audit(["broken"], self.root)
        self.save_source("no_rt", {"version": "fixture"})
        with self.assertRaisesRegex(ValueError, "rt_params"):
            P.source_audit(["no_rt"], self.root)


class ProfileTests(unittest.TestCase):
    def test_source_informed_defaults(self):
        config = P.apply_profile({})
        self.assertEqual(config["propagation_profile"], "source-informed")
        self.assertEqual(config["carrier_hz"], 3.5e9)
        self.assertEqual(config["max_depth"], 7)
        self.assertTrue(config["diffraction"])
        self.assertTrue(config["diffuse_reflection"])
        self.assertTrue(config["synthetic_array"])
        self.assertFalse(config["edge_diffraction"])
        self.assertFalse(config["refraction"])
        self.assertNotIn("samples_per_src", config)
        self.assertNotIn("num_antennas", config)
        self.assertNotIn("tx_pattern", config)

    def test_legacy_defaults(self):
        config = P.apply_profile({"propagation_profile": "legacy"})
        self.assertEqual(config["max_depth"], 3)
        self.assertFalse(config["diffraction"])
        self.assertFalse(config["diffuse_reflection"])
        self.assertFalse(config["edge_diffraction"])
        self.assertFalse(config["refraction"])
        self.assertTrue(config["synthetic_array"])

    def test_none_resolves_but_explicit_false_and_zero_are_preserved(self):
        args = {"propagation_profile": "source-informed", "carrier_hz": None,
                "max_depth": 0, "diffraction": False, "diffuse_reflection": False,
                "num_antennas": 32, "tx_pattern": "tr38901", "samples_per_src": 12345}
        before = dict(args)
        config = P.apply_profile(args)
        self.assertEqual(args, before)
        self.assertEqual(config["carrier_hz"], 3.5e9)
        self.assertEqual(config["max_depth"], 0)
        self.assertFalse(config["diffraction"])
        self.assertFalse(config["diffuse_reflection"])
        self.assertEqual(config["num_antennas"], 32)
        self.assertEqual(config["tx_pattern"], "tr38901")
        self.assertEqual(config["samples_per_src"], 12345)

    def test_namespace_and_explicit_boolean_overrides(self):
        args = SimpleNamespace(propagation_profile="legacy", diffraction=True,
                               diffuse_reflection=True, edge_diffraction=True, refraction=True)
        config = P.apply_profile(args)
        self.assertTrue(config["diffraction"])
        self.assertTrue(config["edge_diffraction"])
        self.assertTrue(config["refraction"])
        self.assertFalse(hasattr(args, "max_depth"))

    def test_bad_profile_or_controls_rejected(self):
        invalid = [
            {"propagation_profile": "imaginary"}, {"max_depth": -1},
            {"max_depth": 2.5}, {"max_depth": True}, {"carrier_hz": float("nan")},
            {"carrier_hz": float("inf")}, {"carrier_hz": 0}, {"carrier_hz": True},
            {"diffraction": "false"}, {"synthetic_array": 1},
            {"edge_diffraction": True, "diffraction": False},
        ]
        for config in invalid:
            with self.subTest(config=config), self.assertRaises(ValueError):
                P.apply_profile(config)

    def test_metadata_keeps_raybudget_task_owned_and_labels_assumptions(self):
        config = {"samples_per_src": 100000, "max_num_paths_per_src": 200000,
                  "max_depth": 5, "num_antennas": 64}
        metadata = P.profile_metadata(config)
        self.assertFalse(metadata["source_evidence_attached"])
        self.assertEqual(metadata["effective"]["max_depth"], 5)
        self.assertEqual(metadata["values_differing_from_defaults"], {"max_depth": 5})
        self.assertEqual(metadata["ray_budget_policy"]["samples_per_src"], 100000)
        self.assertIn("heuristic", metadata["ray_budget_policy"]["kind"])
        self.assertEqual(metadata["ray_budget_policy"]["source_num_rays_values"], [])
        self.assertNotIn("num_antennas", metadata["effective"])
        json.dumps(metadata, allow_nan=False)


class DownloadedEvidenceTests(unittest.TestCase):
    @unittest.skipUnless(all((P.REPO_ROOT / "data/deepmimo" / name / "params.json").is_file()
                             for name in ("asu_campus_3p5", "boston5g_3p5", "city_0_newyork_3p5")),
                         "downloaded DeepMIMO evidence not present")
    def test_actual_selected_source_standard_and_raw_metadata(self):
        names = ["asu_campus_3p5", "boston5g_3p5", "city_0_newyork_3p5"]
        audit = P.source_audit(names)
        rows = {row["source"]: row for row in audit["sources"]}
        self.assertEqual(audit["source_names"], sorted(names))
        self.assertEqual(rows["asu_campus_3p5"]["standard"]["max_path_depth"], 7)
        self.assertEqual(rows["city_0_newyork_3p5"]["standard"]["max_path_depth"], 4)
        boston = rows["boston5g_3p5"]
        self.assertFalse(boston["raw"]["diffuse_enabled"])
        self.assertEqual(boston["standard"]["diffuse_reflections"], 2)
        self.assertEqual(boston["standard"]["max_scattering"], 0)
        self.assertEqual(audit["aggregate"]["standard_values"]["frequency"], [3.5e9])
        self.assertEqual(audit["aggregate"]["standard_values"]["num_rays"], [259200])
        self.assertEqual(audit["aggregate"]["sources_with_conflicts"], [])


if __name__ == "__main__":
    unittest.main()
