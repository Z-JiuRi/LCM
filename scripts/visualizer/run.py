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

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / 'visualizer/scene-web'
DATA = ROOT / 'data/cities'


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

    def send_data(self, payload, content_type, head, compressed=False):
        self.send_response(200)
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
    server = ThreadingHTTPServer((args.host, args.port), Handler)
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
