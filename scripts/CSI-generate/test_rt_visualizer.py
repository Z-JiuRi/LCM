"""Synthetic saved-array/HTTP-handler tests only: no RT, build, or listening server."""
import gzip
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

SPEC = importlib.util.spec_from_file_location('rt_visualizer', Path(__file__).resolve().parents[1]/'visualizer/run.py')
V = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(V)


def native_arrays(start=0):
    valid = np.array([[True, True, False], [True, False, True]])
    events = np.zeros((4, 2, 1, 3), dtype=np.uint32)
    vertices = np.full((*events.shape, 3), np.nan, dtype=np.float32)
    events[0, 0, 0, 1] = 1
    events[2, 0, 0, 1] = 8
    vertices[0, 0, 0, 1] = [2, 3, 4]
    vertices[2, 0, 0, 1] = [5, 6, 7]
    # An invalid padded path is not a ray, even if it has nonzero events.
    events[:, 0, 0, 2] = 2
    coefficients = np.ones((2, 2, 2, 3), dtype=np.complex64)
    coefficients[:, :, 1, :] = 3j
    coefficients[1, :, :, 2] = 0
    return dict(ue_indices=np.arange(start, start+2), path_valid=valid,
                interactions=events, vertices_m=vertices,
                passband_coefficients=coefficients,
                channel_coefficients=np.full_like(coefficients, 1000))


class MemorySocket:
    def __init__(self, request):
        self.request = request
        self.response = bytearray()

    def makefile(self, *args):
        return io.BytesIO(self.request)

    def sendall(self, data):
        self.response.extend(data)


def request(path, results=None, method='GET'):
    connection = MemorySocket(f'{method} {path} HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n'.encode())
    with patch.object(V.Handler, 'log_message'):
        V.Handler(connection, ('127.0.0.1', 12345), SimpleNamespace(rt_results=results or {}))
    header, body = bytes(connection.response).split(b'\r\n\r\n', 1)
    lines = header.decode().split('\r\n')
    status = int(lines[0].split()[1])
    headers = dict(line.split(': ', 1) for line in lines[1:])
    return status, headers, body


class ConversionTests(unittest.TestCase):
    def setUp(self):
        self.arrays = native_arrays()
        self.positions = np.array([[10, 11, 1.5], [20, 21, 1.5]])
        self.tx = [0, 1, 25]

    def convert(self):
        return V.convert_rt_batch(self.arrays, 'sector-A', self.tx, self.positions)

    def test_all_valid_paths_native_order_padding_and_antenna_average(self):
        batch = self.convert()
        self.assertEqual(len(batch['rays']), 4)
        los, bounced, second_los, zero_power = batch['rays']
        self.assertEqual(los['points'], [self.tx, self.positions[0].tolist()])
        self.assertEqual(los['interactions'], [])
        self.assertEqual(bounced['points'], [self.tx, [2, 3, 4], [5, 6, 7], self.positions[0].tolist()])
        self.assertEqual(bounced['interactions'], [1, 8])
        self.assertEqual([r['ue_index'] for r in batch['rays']], [0, 0, 1, 1])
        self.assertAlmostEqual(second_los['power_gain_db'], 10*np.log10(5))
        self.assertIsNone(zero_power['power_gain_db'])
        self.assertEqual(batch['rx_positions'], self.positions.tolist())
        self.assertEqual(batch['tx_position'], self.tx)
        self.assertEqual(json.loads(V.json_payload(batch)), batch)

    def test_all_interaction_codes_and_origin_are_physical_when_nonzero(self):
        self.arrays['interactions'][:, 0, 0, 1] = [1, 2, 4, 8]
        self.arrays['vertices_m'][:, 0, 0, 1] = [[0, 0, 0], [1, 2, 3], [4, 5, 6], [7, 8, 9]]
        ray = self.convert()['rays'][1]
        self.assertEqual(ray['interactions'], [1, 2, 4, 8])
        self.assertEqual(ray['points'][1], [0, 0, 0])
        self.assertEqual(len(ray['points']), 6)

    def test_nonfinite_and_zero_power_become_null_without_dropping_valid_paths(self):
        self.arrays['passband_coefficients'][0, :, :, 0] = np.nan
        self.arrays['passband_coefficients'][0, :, :, 1] = np.inf
        payload = V.json_payload(self.convert())
        self.assertNotIn(b'NaN', payload)
        self.assertNotIn(b'Infinity', payload)
        rays = json.loads(payload)['rays']
        self.assertEqual(len(rays), 4)
        self.assertIsNone(rays[0]['power_gain_db'])
        self.assertIsNone(rays[1]['power_gain_db'])
        with self.assertRaises(ValueError):
            V.json_payload(dict(unconverted=float('nan')))

    def test_empty_saved_paths_do_not_fabricate_los(self):
        self.arrays['path_valid'] = np.zeros((2, 0), dtype=bool)
        self.arrays['interactions'] = np.zeros((7, 2, 1, 0), dtype=np.uint32)
        self.arrays['vertices_m'] = np.zeros((7, 2, 1, 0, 3))
        self.arrays['passband_coefficients'] = np.zeros((2, 1, 32, 0), dtype=np.complex64)
        self.assertEqual(self.convert()['rays'], [])

    def test_no_top_k_or_truncation(self):
        count = 1025
        self.arrays = dict(ue_indices=np.array([0]), path_valid=np.ones((1, count), dtype=bool),
                           interactions=np.zeros((0, 1, 1, count), dtype=np.uint32),
                           vertices_m=np.zeros((0, 1, 1, count, 3)),
                           passband_coefficients=np.ones((1, 1, 1, count), dtype=np.complex64))
        self.assertEqual(len(self.convert()['rays']), count)

    def test_malformed_layout_indices_and_active_vertices_are_rejected(self):
        cases = [dict(ue_indices=np.array([-1, 0])), dict(ue_indices=np.array([0, 0])),
                 dict(ue_indices=np.array([0., 1.])), dict(path_valid=np.ones((2, 3), dtype=int)),
                 dict(interactions=np.zeros((2, 3))), dict(vertices_m=np.zeros((4, 2, 1, 3, 2))),
                 dict(passband_coefficients=np.ones((2, 3)))]
        original = self.arrays
        for changes in cases:
            with self.subTest(changes=list(changes)):
                self.arrays = {**original, **changes}
                with self.assertRaises(ValueError):
                    self.convert()
        self.arrays = original
        self.arrays['vertices_m'][0, 0, 0, 1] = np.nan
        with self.assertRaisesRegex(ValueError, 'Nonfinite interaction'):
            self.convert()


class SavedRunTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='rt-visualizer-test-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.cities = self.base/'cities'
        self.canonical = self.cities/'city-1km/scene.json.gz'
        self.canonical.parent.mkdir(parents=True)
        source = gzip.compress(b'{"synthetic_test":true}', mtime=0)
        self.canonical.write_bytes(source)
        (self.cities/'catalog.json').write_text(json.dumps([
            dict(id='city-1km', extent_m=[0, 0, 1000, 1000])]))
        self.root = self.base/'runs/test-run'
        self.root.mkdir(parents=True)
        self.positions = np.array([[10, 11, 1.5], [20, 21, 1.5], [30, 31, 1.5], [40, 41, 1.5]])
        np.save(self.root/'ue_positions.npy', self.positions)
        self.report = dict(status='complete', geometry_manifest=dict(
            source_scene=str(self.canonical), extent_m=[0, 0, 1000, 1000]), raw_sectors=[])
        self.metadata = []
        for row, index in enumerate((3, 9)):
            folder = self.root/f'raw/sector-{index:03d}'
            folder.mkdir(parents=True)
            sector = dict(id=f'sector-{row}', position_m=[row, 1, 25])
            self.report['raw_sectors'].append(dict(index=index, folder=str(folder), sector=sector))
            records = []
            for batch in range(2):
                filename = f'paths-{batch}.npz'
                np.savez(folder/filename, **native_arrays(batch*2))
                records.append(dict(file=filename, start=batch*2, stop=batch*2+2,
                                    diagnostics=dict(returned_valid_paths=4)))
            metadata = dict(sector=sector, batches=records)
            self.metadata.append(metadata)
            (folder/'metadata.json').write_text(json.dumps(metadata))
            gain = [.01, .02, 0, np.nan] if row == 0 else [.1, .001, 0, np.inf]
            np.savez(folder/'link_stats.npz', path_gain_linear=np.array(gain))
        self.save_report()

    def save_report(self):
        (self.root/'report.json').write_text(json.dumps(self.report))

    def load(self):
        return V.RTResult(self.root, self.cities)

    def save_association(self, owners=(0, 1, -1, -1), ids=('sector-0', 'sector-1')):
        np.savez(self.root/'association.npz', serving_sector_index=np.array(owners), sector_ids=np.array(ids))

    def test_manifest_and_fallback_coverage_use_link_stats_not_csi(self):
        with patch.object(np, 'load', wraps=np.load) as loader:
            result = self.load()
        names = [Path(call.args[0]).name for call in loader.call_args_list]
        self.assertEqual(names, ['ue_positions.npy', 'link_stats.npz', 'link_stats.npz'])
        manifest = json.loads(result.manifest_payload)
        self.assertTrue(manifest['available'])
        self.assertEqual((manifest['ue_count'], manifest['sector_count']), (4, 2))
        self.assertEqual(len(manifest['batches']), 4)
        self.assertEqual(manifest['batches'][0]['url'], '/scenes/city-1km-rt/3/0.json')
        self.assertEqual(manifest['batches'][0]['path_count'], 4)
        coverage = manifest['coverage']
        self.assertEqual(coverage['positions'], self.positions.tolist())
        np.testing.assert_allclose(coverage['gain_db'][:2], [-10, 10*np.log10(.02)])
        self.assertEqual(coverage['gain_db'][2:], [None, None])
        self.assertEqual(coverage['metric'], 'Serving path gain (dB)')
        self.assertEqual(coverage['note'], 'noncoherent antenna-averaged sum path power; sampled positions only')
        self.assertIn('No saved association', manifest['notes'][0])

    def test_saved_owner_is_sector_row_not_sector_index_and_overrides_best(self):
        self.save_association()
        manifest = self.load().manifest
        self.assertEqual(manifest['coverage']['gain_db'], [-20, -30, None, None])
        self.assertIn('saved association', manifest['notes'][0])

    def test_bad_association_order_and_invalid_owner_rejected(self):
        self.save_association(ids=('sector-1', 'sector-0'))
        with self.assertRaisesRegex(ValueError, 'sector order'):
            self.load()
        self.save_association(owners=(3, 1, -1, -1))
        with self.assertRaisesRegex(ValueError, 'association'):
            self.load()

    def test_batch_loads_only_requested_npz_and_preserves_global_ue_indices(self):
        result = self.load()
        with patch.object(np, 'load', wraps=np.load) as loader:
            batch = result.batch(9, 1)
        self.assertEqual(len(loader.call_args_list), 1)
        self.assertEqual(Path(loader.call_args.args[0]), self.root/'raw/sector-009/paths-1.npz')
        self.assertEqual([r['ue_index'] for r in batch['rays']], [2, 2, 3, 3])
        self.assertEqual(batch['rx_positions'], self.positions[2:].tolist())
        self.assertEqual(batch['tx_position'], [1, 1, 25])

    def test_registration_is_read_only(self):
        files = [self.root/'report.json', self.root/'ue_positions.npy', self.root/'raw/sector-003/paths-0.npz', self.canonical]
        before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}
        result = self.load()
        result.batch(3, 0)
        after = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in files}
        self.assertEqual(before, after)

    def test_source_extent_city_and_completion_are_validated(self):
        cases = [(str(self.canonical), [0, 0, 2000, 2000], 'complete'),
                 (str(self.base/'wrong-city/scene.json.gz'), [0, 0, 1000, 1000], 'complete'),
                 (str(self.base/'city-2km/scene.json.gz'), [0, 0, 1000, 1000], 'complete'),
                 (str(self.canonical), [0, 0, 1000, 1000], 'running'),
                 (str(self.canonical), None, 'complete'),
                 (str(self.canonical), [0, 0, float('nan'), 1000], 'complete'),
                 (str(self.canonical), [1000, 0, 0, 1000], 'complete')]
        for source, extent, status in cases:
            with self.subTest(source=source, extent=extent, status=status):
                self.report['geometry_manifest'].update(source_scene=source, extent_m=extent)
                self.report['status'] = status
                self.save_report()
                with self.assertRaises(ValueError):
                    self.load()

    def test_registration_uses_catalog_without_reading_or_hashing_scene(self):
        original_open = Path.open

        def no_scene_open(path, *args, **kwargs):
            if path == self.canonical:
                raise AssertionError('Registration must not read the full city scene')
            return original_open(path, *args, **kwargs)

        # The independently generated CSI report can retain its original hash;
        # the read-only viewer deliberately does not verify or display it.
        self.report['geometry_manifest']['scene_sha256'] = 'not-a-viewer-check'
        self.save_report()
        with patch.object(Path, 'open', no_scene_open):
            manifest = self.load().manifest
        self.assertTrue(manifest['available'])
        self.assertIn('city id and catalog extent only', manifest['notes'][1])
        self.assertNotIn('scene_sha256', V.json_payload(manifest).decode())

    def test_outside_report_folder_and_batch_traversal_are_rejected(self):
        self.report['raw_sectors'][0]['folder'] = str(self.base)
        self.save_report()
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.load()
        self.report['raw_sectors'][0]['folder'] = str(self.root/'raw/sector-003')
        self.save_report()
        self.metadata[0]['batches'][0]['file'] = '../../../../outside.npz'
        (self.root/'raw/sector-003/metadata.json').write_text(json.dumps(self.metadata[0]))
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.load()

    def test_artifact_symlink_escape_is_rejected(self):
        (self.root/'outside-link.npz').symlink_to(self.base/'outside.npz')
        with self.assertRaisesRegex(ValueError, 'escapes'):
            V.result_path(self.root, 'outside-link.npz')

    def test_duplicate_city_registration_and_bad_batch_ranges_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Multiple RT runs'):
            V.register_rt_results([self.root, self.root], self.cities)
        self.metadata[0]['batches'][1]['start'] = 1
        (self.root/'raw/sector-003/metadata.json').write_text(json.dumps(self.metadata[0]))
        with self.assertRaisesRegex(ValueError, 'ranges'):
            self.load()

    def test_http_get_head_manifest_batch_and_unavailable(self):
        results = {'city-1km': self.load()}
        for path in ['/scenes/city-1km-rt.json', '/scenes/city-1km-rt/3/1.json', '/scenes/city-2km-rt.json']:
            with self.subTest(path=path):
                status, headers, body = request(path, results)
                self.assertEqual(status, 200)
                self.assertEqual(headers['Content-Type'], 'application/json')
                self.assertEqual(headers['Cache-Control'], 'no-store')
                self.assertEqual(int(headers['Content-Length']), len(body))
                self.assertIsInstance(json.loads(body), dict)
                head_status, head_headers, head_body = request(path, results, 'HEAD')
                self.assertEqual(head_status, status)
                self.assertEqual(head_headers['Content-Length'], headers['Content-Length'])
                self.assertEqual(head_body, b'')
        unavailable = json.loads(request('/scenes/city-1km-rt.json')[2])
        self.assertFalse(unavailable['available'])
        self.assertTrue(unavailable['reason'])

    def test_http_explicit_404_for_missing_and_traversal_paths(self):
        results = {'city-1km': self.load()}
        for path in ['/scenes/city-1km-rt/99/0.json', '/scenes/city-1km-rt/3/99.json',
                     '/scenes/city-2km-rt/3/0.json', '/scenes/city-1km-rt/../report.json',
                     '/scenes/city-1km-rt/%2e%2e/report.json']:
            with self.subTest(path=path):
                self.assertEqual(request(path, results)[0], 404)
        results['city-1km'].sectors[3]['batches'][0]['file'] = 'does-not-exist.npz'
        self.assertEqual(request('/scenes/city-1km-rt/3/0.json', results)[0], 404)

    def test_http_400_for_bad_npz_indices_or_escaping_metadata(self):
        results = {'city-1km': self.load()}
        path = self.root/'raw/sector-003/paths-0.npz'
        cases = ['corrupt', 'wrong-indices', 'escaping-metadata']
        for case in cases:
            with self.subTest(case=case):
                if case == 'corrupt':
                    path.write_bytes(b'invalid NPZ')
                elif case == 'wrong-indices':
                    np.savez(path, **native_arrays(2))
                else:
                    results['city-1km'].sectors[3]['batches'][0]['file'] = '../../../../outside.npz'
                status, _, body = request('/scenes/city-1km-rt/3/0.json', results)
                self.assertEqual(status, 400)
                self.assertEqual(json.loads(body), {'error': 'Invalid saved RT batch'})
                head_status, _, head_body = request('/scenes/city-1km-rt/3/0.json', results, 'HEAD')
                self.assertEqual(head_status, 400)
                self.assertEqual(head_body, b'')


if __name__ == '__main__':
    unittest.main()
