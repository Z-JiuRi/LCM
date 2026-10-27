#!/usr/bin/env python3
"""Build or serve the read-only city viewer using the existing lcm Conda env."""
import argparse
import gzip
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import urlsplit
from zipfile import BadZipFile

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / 'visualizer/scene-web'
DATA = ROOT / 'data/cities'


def json_payload(value):
    """Strict JSON: nonfinite gains are converted to None by their producer."""
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode('utf-8')


def result_path(root, value, base=None):
    """Never follow report/metadata paths or symlinks outside the registered run."""
    path = Path(value)
    path = (path if path.is_absolute() else (base or root)/path).resolve()
    if not path.is_relative_to(root):
        raise ValueError('RT artifact path escapes the registered results directory')
    return path


def finite_positions(value, label):
    import numpy as np
    positions = np.asarray(value)
    if positions.ndim != 2 or positions.shape[1] != 3 or not np.isfinite(positions).all():
        raise ValueError(f'{label} must contain finite XYZ positions')
    return positions


def gain_db(value):
    import math
    value = float(value)
    return 10 * math.log10(value) if math.isfinite(value) and value > 0 else None


def convert_rt_batch(arrays, sector_id, tx_position, positions, expected_indices=None):
    """Convert every valid native synthetic-array path; never synthesize paths.

    Sionna RT 2.2 Paths.vertices is [depth, RX, TX, path, XYZ], and
    preview.py::plot_paths traverses TX -> increasing depth -> RX. Its
    InteractionType constants are 1 specular, 2 diffuse, 4 refraction (thin-slab
    transmission), 8 diffraction. NONE=0 marks padding, not a vertex at origin.
    Saved passband_coefficients removes the singleton TX axis: [U,R,T,P].
    """
    import numpy as np
    positions = finite_positions(positions, 'UE positions')
    tx = finite_positions(np.asarray(tx_position)[None, :], 'TX position')[0]
    indices = np.asarray(arrays['ue_indices'])
    valid = np.asarray(arrays['path_valid'])
    events = np.asarray(arrays['interactions'])
    vertices = np.asarray(arrays['vertices_m'])
    coefficients = np.asarray(arrays['passband_coefficients'])
    if (indices.ndim != 1 or not np.issubdtype(indices.dtype, np.integer)
            or np.any(indices < 0) or np.any(indices >= len(positions))
            or len(np.unique(indices)) != len(indices)):
        raise ValueError('Invalid batch UE indices')
    if expected_indices is not None and not np.array_equal(indices, expected_indices):
        raise ValueError('Batch UE indices do not match metadata range')
    if valid.ndim != 2 or valid.shape[0] != len(indices) or valid.dtype != np.bool_:
        raise ValueError('Expected path_valid [UE,path] boolean mask')
    ues, paths = valid.shape
    if (events.ndim != 4 or events.shape[1:] != (ues, 1, paths)
            or not np.issubdtype(events.dtype, np.integer) or np.any(events < 0)
            or vertices.shape != (*events.shape, 3)):
        raise ValueError('Expected native interactions/vertices [depth,UE,1,path,(XYZ)]')
    if (coefficients.ndim != 4 or coefficients.shape[0] != ues
            or coefficients.shape[-1] != paths or min(coefficients.shape[1:3]) < 1
            or not np.issubdtype(coefficients.dtype, np.number)):
        raise ValueError('Expected passband_coefficients [UE,RX_ant,TX_ant,path]')
    rays = []
    for ue, index in enumerate(indices):
        # Compute only one receiver's antenna-average powers at a time.
        with np.errstate(over='ignore', invalid='ignore'):
            power = np.mean(np.abs(coefficients[ue].astype(np.complex128))**2, axis=(0, 1))
        for path in np.flatnonzero(valid[ue]):
            codes = events[:, ue, 0, path]
            active = codes != 0
            interior = vertices[:, ue, 0, path][active]
            if not np.isfinite(interior).all():
                raise ValueError('Nonfinite interaction vertex on a valid path')
            rays.append(dict(sector_id=sector_id, ue_index=int(index),
                             power_gain_db=gain_db(power[path]),
                             points=[tx.tolist(), *interior.tolist(), positions[index].tolist()],
                             interactions=codes[active].tolist()))
    return dict(rays=rays, tx_position=tx.tolist(), rx_positions=positions[indices].tolist())


class RTResult:
    """Read-only registration; cache only the manifest, convert one NPZ per request."""

    def __init__(self, root, city_data=None):
        import numpy as np
        self.root = Path(root).resolve()
        city_data = DATA if city_data is None else Path(city_data)
        report = json.loads(result_path(self.root, 'report.json').read_text(encoding='utf-8'))
        geometry = report['geometry_manifest']
        self.city_id = Path(geometry['source_scene']).parent.name
        if not re.fullmatch(r'city-(?:1|2|4)km', self.city_id):
            raise ValueError('RT source scene does not identify a supported city')
        # Viewer matching is deliberately limited to city id and catalog extent.
        # Do not load the full scene or introduce viewer-side asset hashing.
        catalog = json.loads((city_data/'catalog.json').read_text(encoding='utf-8'))
        entries = [entry for entry in catalog if entry.get('id') == self.city_id]
        if len(entries) != 1:
            raise ValueError('RT source city must identify exactly one catalog entry')
        extent = np.asarray(geometry.get('extent_m'), dtype=float)
        canonical_extent = np.asarray(entries[0].get('extent_m'), dtype=float)
        if (extent.shape != (4,) or not np.isfinite(extent).all()
                or not np.all(extent[2:] > extent[:2])
                or not np.array_equal(extent, canonical_extent)):
            raise ValueError(f'RT source extent differs from the displayed {self.city_id}')
        if report.get('status') != 'complete':
            raise ValueError('Only completed saved RT results can be registered')
        self.positions = finite_positions(np.load(result_path(self.root, 'ue_positions.npy'),
                                                   mmap_mode='r', allow_pickle=False), 'UE positions')
        self.sectors = {}
        batches = []
        sectors = report['raw_sectors']
        if not isinstance(sectors, list) or not sectors:
            raise ValueError('Completed RT report has no saved sectors')
        ids = []
        for result in sectors:
            index = result['index']
            if type(index) is not int or index < 0 or index in self.sectors:
                raise ValueError('Invalid or repeated RT sector index')
            folder = result_path(self.root, result['folder'])
            metadata = json.loads(result_path(self.root, 'metadata.json', folder).read_text(encoding='utf-8'))
            sector = result['sector']
            if sector != metadata['sector']:
                raise ValueError('RT sector metadata does not match report')
            if not isinstance(sector['id'], (str, int)) or sector['id'] in ids:
                raise ValueError('Invalid or repeated RT sector id')
            ids.append(sector['id'])
            finite_positions(np.asarray(sector['position_m'])[None, :], 'TX position')
            records = metadata['batches']
            if not isinstance(records, list):
                raise ValueError('RT batch metadata must be a list')
            self.sectors[index] = dict(folder=folder, sector=sector, batches=records)
            cursor = 0
            for batch_index, batch in enumerate(records):
                result_path(self.root, batch['file'], folder)
                start, stop = batch['start'], batch['stop']
                if (type(start) is not int or type(stop) is not int or start != cursor
                        or not start < stop <= len(self.positions)):
                    raise ValueError('RT batch ranges must cover sampled UEs once in order')
                cursor = stop
                entry = dict(sector_id=sector['id'], batch_index=batch_index,
                             url=f'/scenes/{self.city_id}-rt/{index}/{batch_index}.json')
                count = batch.get('diagnostics', {}).get('returned_valid_paths')
                if type(count) is int and count >= 0:
                    entry['path_count'] = count
                batches.append(entry)
            if cursor != len(self.positions):
                raise ValueError('RT batch ranges do not cover all sampled UEs')
        coverage, association_note = self._coverage(ids)
        self.manifest = dict(
            available=True, run_label=f'{self.root.parent.name}/{self.root.name}',
            scope=f'{len(self.positions)} sampled UE positions; {len(sectors)} saved sectors; '
                  'all saved valid paths, not a full-city coverage certification',
            ue_count=len(self.positions), sector_count=len(sectors), batches=batches,
            coverage=coverage,
            notes=[association_note,
                   'Result-to-city matching uses the source city id and catalog extent only; '
                   'this is not hash validation or certification of identical scene geometry.',
                   'Only saved valid paths are shown, without top-K filtering or ray truncation. '
                   'Uncomputed and invalid padded paths are not fabricated.',
                   'Interaction codes: 1 specular reflection; 2 diffuse reflection; '
                   '4 refraction/thin-slab transmission; 8 diffraction.',
                   'Null gain means no positive finite saved path power; it is not a measured outage. '
                   'Coverage is sampled positions only, not interpolated or normalized CSI.']
                  + [str(note) for note in report.get('backend_limitations', [])])
        self.manifest_payload = json_payload(self.manifest)

    def _coverage(self, sector_ids):
        import numpy as np
        owner = None
        association = result_path(self.root, 'association.npz')
        if association.exists():
            with np.load(association, allow_pickle=False) as saved:
                owner = saved['serving_sector_index']
                if (owner.shape != (len(self.positions),) or not np.issubdtype(owner.dtype, np.integer)
                        or np.any(owner < -1) or np.any(owner >= len(self.sectors))):
                    raise ValueError('Invalid saved serving-sector association')
                if 'sector_ids' in saved and saved['sector_ids'].tolist() != sector_ids:
                    raise ValueError('Saved association sector order does not match report')
        best = np.zeros(len(self.positions), dtype=np.float64)
        for row, sector in enumerate(self.sectors.values()):
            with np.load(result_path(self.root, 'link_stats.npz', sector['folder']), allow_pickle=False) as saved:
                gain = saved['path_gain_linear']
                if gain.shape != best.shape:
                    raise ValueError('Link statistics do not match UE positions')
                usable = np.isfinite(gain) & (gain > 0)
                selected = usable & ((owner == row) if owner is not None else (gain > best))
                np.copyto(best, gain, where=selected)
        note = ('Serving sectors are taken from saved association; path gain comes from link_stats.'
                if owner is not None else
                'No saved association: serving sectors use the best finite positive path gain across saved sectors.')
        return dict(positions=self.positions.tolist(), gain_db=[gain_db(value) for value in best],
                    metric='Serving path gain (dB)',
                    note='noncoherent antenna-averaged sum path power; sampled positions only'), note

    def batch(self, sector_index, batch_index):
        import numpy as np
        sector = self.sectors.get(sector_index)
        if sector is None or not 0 <= batch_index < len(sector['batches']):
            raise FileNotFoundError('Unknown saved RT sector or batch')
        record = sector['batches'][batch_index]
        path = result_path(self.root, record['file'], sector['folder'])
        with np.load(path, allow_pickle=False) as arrays:
            return convert_rt_batch(arrays, sector['sector']['id'], sector['sector']['position_m'],
                                    self.positions, np.arange(record['start'], record['stop']))


def register_rt_results(paths, city_data=None):
    results = {}
    for path in paths:
        result = RTResult(path, city_data)
        if result.city_id in results:
            raise ValueError(f'Multiple RT runs registered for {result.city_id}; select one per city')
        results[result.city_id] = result
    return results


def build():
    npm = shutil.which('npm')
    if not npm:
        raise SystemExit('构建需要 Node.js/npm；已有构建只需 serve。')
    if not (FRONTEND/'node_modules/.bin/vite').is_file():
        subprocess.run([npm, 'install', '--no-package-lock', '--no-audit', '--no-fund'], cwd=FRONTEND, check=True)
    subprocess.run([npm, 'run', 'build'], cwd=FRONTEND, check=True)
    shutil.copyfile(FRONTEND/'node_modules/three/LICENSE', FRONTEND/'dist/THIRD-PARTY-LICENSE.txt')


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND/'dist'), **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def do_GET(self):
        self.respond(False)

    def do_HEAD(self):
        self.respond(True)

    def respond(self, head):
        path = urlsplit(self.path).path
        match = re.fullmatch(r'/scenes/(city-(?:1|2|4)km)-rt\.json', path)
        if match:
            result = getattr(self.server, 'rt_results', {}).get(match[1])
            payload = (result.manifest_payload if result is not None else json_payload(dict(
                available=False, reason='No saved RT results registered for this city; no tracing is run by the viewer.')))
            self.send_data(payload, 'application/json', head)
            return
        match = re.fullmatch(r'/scenes/(city-(?:1|2|4)km)-rt/(\d+)/(\d+)\.json', path)
        if match:
            result = getattr(self.server, 'rt_results', {}).get(match[1])
            try:
                if result is None:
                    raise FileNotFoundError('No saved RT results registered for this city')
                payload = json_payload(result.batch(int(match[2]), int(match[3])))
            except FileNotFoundError:
                self.send_data(json_payload(dict(error='Saved RT batch not found')), 'application/json', head, status=404)
            except (ValueError, TypeError, KeyError, IndexError, OSError, EOFError, BadZipFile) as error:
                # Do not leak report paths or filesystem details to HTTP clients.
                self.log_error('Invalid saved RT batch: %s', error)
                self.send_data(json_payload(dict(error='Invalid saved RT batch')), 'application/json', head, status=400)
            else:
                self.send_data(payload, 'application/json', head)
            return
        if path == '/scenes/catalog.json':
            self.send_data((DATA/'catalog.json').read_bytes(), 'application/json', head)
            return
        match = re.fullmatch(r'/scenes/(city-(?:1|2|4)km)(\.json|-ue\.f32)', path)
        if match:
            folder = DATA/match[1]
            if match[2] == '.json':
                data = (folder/'scene.json.gz').read_bytes()
                compressed = 'gzip' in self.headers.get('Accept-Encoding', '')
                self.send_data(data if compressed else gzip.decompress(data), 'application/json', head, compressed)
            else:
                import numpy as np
                positions = np.load(folder/'ue.npy', allow_pickle=False)
                self.send_data(positions.astype('<f4', copy=False).tobytes(), 'application/octet-stream', head)
            return
        if path.startswith('/scenes/'):
            self.send_error(404)
            return
        if head:
            super().do_HEAD()
        else:
            super().do_GET()

    def send_data(self, payload, content_type, head, compressed=False, status=200):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        if compressed:
            self.send_header('Content-Encoding', 'gzip')
        self.send_header('Vary', 'Accept-Encoding')
        self.end_headers()
        if not head:
            self.wfile.write(payload)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['serve', 'build'], nargs='?', default='serve')
    parser.add_argument('--port', type=int, default=8767)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--rt-results', type=Path, action='append', default=[], metavar='PATH',
                        help='Read a completed CSI output directory; repeat for different cities. Never runs RT.')
    args = parser.parse_args()
    if Path(sys.prefix).name != 'lcm' or not (Path(sys.prefix)/'conda-meta').is_dir():
        parser.error('请先 conda activate lcm；本项目不创建独立 .venv。')
    if args.command == 'build':
        build()
        return
    if not (FRONTEND/'dist/index.html').is_file():
        build()
    catalog = json.loads((DATA/'catalog.json').read_text())
    for entry in catalog:
        for name in ('scene.json.gz', 'ue.npy'):
            if not (DATA/entry['id']/name).is_file():
                parser.error(f"缺少场景数据：{entry['id']}/{name}")
    try:
        rt_results = register_rt_results(args.rt_results)
    except (ValueError, TypeError, KeyError, IndexError, OSError, EOFError, BadZipFile) as error:
        parser.error(f'无法读取 RT 结果：{error}')
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    server.rt_results = rt_results
    print(f'三城只读可视化：http://{args.host}:{args.port}/', flush=True)
    print('直接读取 data/cities；不下载、不生成场景、不计算信道。', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
