"""Read-only regression tests: never regenerate the saved city layouts."""
import gzip
import hashlib
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PYTHON_ROOT = Path(__file__).resolve().parents[1] / 'python'
sys.path.insert(0, str(PYTHON_ROOT))
from lcm_scene import api, paths


class PathsAndMigrationTests(unittest.TestCase):
    def test_paths_from_independent_cwd(self):
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run([sys.executable, '-c',
                'from lcm_scene.paths import *; print(CITY_ROOT); print(TEST_SCENE_ROOT)'],
                cwd=cwd, env={**os.environ, 'PYTHONPATH': str(PYTHON_ROOT)},
                capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.splitlines(), [str(paths.CITY_ROOT), str(paths.TEST_SCENE_ROOT)])
        self.assertEqual(paths.city_directory(4000), paths.CITY_ROOT)
        self.assertTrue(paths.TEST_SCENE_ROOT.is_relative_to(paths.DATA_ROOT))
        with self.assertRaises(ValueError):
            paths.city_directory(3000)

    def test_canonical_and_compatibility_modules(self):
        baseline = json.loads((PYTHON_ROOT / 'lcm_scene/migration-baseline.json').read_text())
        self.assertEqual(len(baseline), 13)
        for row in baseline:
            # Keep the baseline's historical paths intact after the directory rename.
            old = paths.STUDIO_ROOT / Path(row['original_path']).relative_to('scene-studio')
            canonical = paths.STUDIO_ROOT / Path(row['canonical_path']).relative_to('scene-studio')
            self.assertTrue(canonical.is_file())
            self.assertEqual(len(row['original_sha256']), 64)
            stub = old.read_text()
            self.assertIn('runpy.run_module', stub)
            self.assertLess(len(stub.splitlines()), 15)
            self.assertNotEqual(hashlib.sha256(old.read_bytes()).hexdigest(), row['original_sha256'])
            module = '.'.join(canonical.relative_to(PYTHON_ROOT).with_suffix('').parts)
            importlib.import_module(module)  # Includes optional RT module without importing RT.

    def test_imports_do_not_rewrite_snapshots(self):
        snapshots = list(paths.CITY_ROOT.glob('*.json*'))
        snapshots += list(paths.CITY_ROOT.glob('city-*km/*.json*'))
        snapshots += list(paths.TEST_SCENE_ROOT.glob('*'))
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in snapshots if p.is_file()}
        with tempfile.TemporaryDirectory() as cwd:
            script = 'import importlib; ' + '; '.join(
                f'importlib.import_module({module!r})' for module in
                [*api.LEGACY_MODULES.values(), 'lcm_scene.verification.verify',
                 'lcm_scene.city.design_city_variants'])
            subprocess.run([sys.executable, '-c', script], cwd=cwd,
                env={**os.environ, 'PYTHONPATH': str(PYTHON_ROOT)}, check=True)
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})

    def test_direct_and_legacy_entry_points_outside_cwd(self):
        modules = ['city/design_city_variants.py', 'city/assemble_city.py',
                   'city/validate_city_variants.py', 'sources/audit_deepmimo_scenarios.py',
                   'sources/audit_deepmimo_path_states.py']
        legacy = paths.CITY_ROOT / 'design_city_variants.py'
        with tempfile.TemporaryDirectory() as cwd:
            for entry in [*(PYTHON_ROOT / 'lcm_scene' / p for p in modules), legacy]:
                subprocess.run([sys.executable, str(entry), '--help'], cwd=cwd,
                               capture_output=True, text=True, check=True)

    def test_preserved_snapshot_hashes(self):
        inventory = paths.STUDIO_ROOT / 'generated/reports/migration-snapshots.json'
        self.assertTrue(inventory.is_file(), 'Parent snapshot inventory required')
        rows = json.loads(inventory.read_text())['files']
        self.assertGreaterEqual(len(rows), 21)
        for row in rows:
            if Path(row['path']).name == 'export-validation.json':
                continue
            target = paths.STUDIO_ROOT / row['path']
            with self.subTest(path=row['path']):
                self.assertTrue(target.is_file())
                self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), row['sha256'])


class SavedCityGeometryTests(unittest.TestCase):
    def test_asset_references_coordinates_heights_counts(self):
        import numpy as np
        for size in (1000, 2000, 4000):
            with self.subTest(size=size):
                directory = paths.city_directory(size)
                scene = json.loads(gzip.decompress((directory/'assembled-city.scene.json.gz').read_bytes()))
                manifest = scene['manifest']
                external = json.loads((directory/'assembled-city-manifest.json').read_text())
                view = json.loads((directory/'assembled-city.view.json').read_text())
                assets = {a['id']: a for a in scene['assets']}
                self.assertEqual(len(assets), len(scene['assets']))
                self.assertEqual(manifest['asset_count'], len(assets))
                self.assertEqual(manifest['instance_count'], len(scene['instances']))
                self.assertEqual(manifest['instance_count'], external['instance_count'])
                self.assertEqual(len(scene['instances']), len(view['buildings']))
                self.assertEqual(manifest['extent_m'], [0, 0, size, size])
                self.assertEqual(scene['ground']['extent_m'], manifest['extent_m'])
                self.assertEqual(manifest['units'], 'm')
                for asset in assets.values():
                    xyz = np.concatenate([np.asarray(f, dtype=float) for f in asset['faces']])
                    self.assertTrue(np.isfinite(xyz).all())
                    self.assertGreater(asset['height_m'], 0)
                    self.assertAlmostEqual(float(np.ptp(xyz[:, 2])), asset['height_m'], delta=.001)
                    self.assertEqual(len(asset['source_origin_m']), 3)
                for instance, building in zip(scene['instances'], view['buildings']):
                    self.assertIn(instance['asset'], assets)
                    position = np.asarray(instance['position_m'])
                    self.assertEqual(position.shape, (3,))
                    self.assertTrue(np.isfinite(position).all())
                    self.assertTrue(np.all(position[:2] >= 0) and np.all(position[:2] <= size))
                    self.assertEqual(position[2], 0)
                    self.assertTrue(np.isfinite(instance['rotation_z_deg']))
                    self.assertNotIn('scale', instance)
                    self.assertLess(instance['parcel'], len(scene['parcels']))
                    self.assertAlmostEqual(building['height'], assets[instance['asset']]['height_m'], delta=.01)

    def test_all_three_saved_exports(self):
        reports = api.validate_exports(write_report=False)
        self.assertEqual(set(reports), {1000, 2000, 4000})
        for report in reports.values():
            self.assertGreater(report['instance_count'], 0)
            for name, value in report.items():
                if name not in ('instance_count', 'scope'):
                    self.assertEqual(value, 0, name)


if __name__ == '__main__':
    unittest.main()
