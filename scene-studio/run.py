#!/usr/bin/env python3
"""One entry point for the consolidated workspace; serve uses Python stdlib only."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'python'))


class Handler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-cache')
        super().end_headers()


def main():
    if len(sys.argv)>1 and sys.argv[1]=='download-city':
        from lcm_scene.sources.download_city_geometry import main as download_main
        old=sys.argv
        try:
            sys.argv=[old[0],*old[2:]]
            return_code=download_main()
        finally:
            sys.argv=old
        raise SystemExit(return_code)
    if len(sys.argv)>1 and sys.argv[1]=='integrate-city':
        from lcm_scene.city.integrate_official import main as integrate_main
        old=sys.argv
        try:
            sys.argv=[old[0],*old[2:]]
            integrate_main()
        finally:
            sys.argv=old
        return
    if len(sys.argv)>1 and sys.argv[1]=='enhance-environment':
        from lcm_scene.city.enhance_environment import main as enhance_main
        old=sys.argv
        try:
            sys.argv=[old[0],*old[2:]]
            enhance_main()
        finally:
            sys.argv=old
        return
    parser = argparse.ArgumentParser(description='LCM 四场景工作台；download-city / integrate-city / enhance-environment --help')
    subs = parser.add_subparsers(dest='command',required=True)
    serve = subs.add_parser('serve',help='提供已构建网页，不重建城市或计算信道')
    serve.add_argument('--port',type=int,default=8766)
    serve.add_argument('--host',default='127.0.0.1')
    subs.add_parser('prepare',help='从已保存场景导出浏览器数据')
    subs.add_parser('build',help='导出浏览器数据并构建前端')
    subs.add_parser('validate',help='检查三种城市已导出的二维几何')
    subs.add_parser('test',help='运行Python单元测试')
    generate = subs.add_parser('generate',help='显式重新生成城市（会更新对应数据）')
    generate.add_argument('--size',type=int,choices=[1000,2000,4000],required=True)
    subs.add_parser('verify-test',help='显式重新运行四建筑RT核验，需Sionna依赖')
    trial=subs.add_parser('trial-city',help='在一公里完整几何上进行少量接收点RT/CSI试算')
    trial.add_argument('--output',type=Path)
    trial.add_argument('--budgets',type=int,nargs='+',default=[20000,100000,1000000])
    legacy = subs.add_parser('tool',help='辅助来源/审计/导出工具；按需网络访问')
    legacy.add_argument('name')
    legacy.add_argument('args',nargs=argparse.REMAINDER)
    args=parser.parse_args()
    if args.command in ('prepare','build'):
        from prepare_viewer import prepare
        prepare()
        if args.command == 'build':
            npm=shutil.which('npm')
            if not npm:
                parser.error('构建需要Node/npm；已构建页面的serve命令不需要Node')
            subprocess.run([npm,'run','build'],cwd=ROOT/'web',check=True)
    elif args.command == 'serve':
        dist=ROOT/'web/dist'
        if not (dist/'index.html').is_file():
            parser.error('请先运行 python3 scene-studio/run.py build')
        server=ThreadingHTTPServer((args.host,args.port),partial(Handler,directory=str(dist)))
        print(f'LCM Scene Studio: http://{args.host}:{server.server_port}/',flush=True)
        print('四种场景可鼠标旋转、缩放、平移；查看不运行射线追踪。',flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    elif args.command == 'test':
        subprocess.run([sys.executable,'-m','unittest','discover','-s',str(ROOT/'tests'),'-v'],cwd=ROOT,check=True)
    else:
        from lcm_scene import api
        if args.command == 'validate':
            api.validate_exports()
        elif args.command == 'generate':
            api.generate(args.size)
        elif args.command == 'verify-test':
            api.verify_test()
        elif args.command == 'trial-city':
            from lcm_scene.verification.city_trial import run
            output=args.output or ROOT/'generated/rt/city-1km-trial-v2'
            run(output.resolve(),args.budgets)
        elif args.command == 'tool':
            api.run_legacy(args.name,args.args)


if __name__ == '__main__':
    main()
