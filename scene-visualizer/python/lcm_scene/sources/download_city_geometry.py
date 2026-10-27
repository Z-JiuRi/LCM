"""Download resources for saved 1/2/4 km cities (default: 4 km).
Default offline inventory; --probe reads archive metadata; --download extracts
geometry/topology/material parameters only. Original channel arrays are excluded.
No automatic full-ZIP fallback, quota bypass or TLS verification disabling.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
import zipfile

if not __package__:
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
    __package__='lcm_scene.sources'
from ..paths import SOURCE_ROOT, city_directory, PREVIEW_CACHE

BASE='https://www.deepmimo.net'


class QuotaError(RuntimeError):
    pass


def response(url,headers=None):
    try:
        return urllib.request.urlopen(urllib.request.Request(url,headers=headers or {}),timeout=60)
    except urllib.error.HTTPError as error:
        if error.code in (403,429):
            raise QuotaError(f'HTTP {error.code}: '+error.read(4096).decode('utf-8',errors='replace')) from error
        raise


class RangeFile(io.RawIOBase):
    """Seekable bounded HTTP file: zipfile handles ZIP64 and decompression/CRC."""
    def __init__(self,url,size):
        self.url=url
        self.size=int(size)
        self.position=0
        self.network_bytes=0
        self.block_start=-1
        self.block=b''
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position
    def seek(self,offset,whence=0):
        target=offset if whence==0 else self.position+offset if whence==1 else self.size+offset
        if target<0: raise ValueError('negative seek')
        self.position=target
        return target
    def read(self,n=-1):
        if n is None or n<0: n=self.size-self.position
        n=min(n,self.size-self.position)
        if n<=0: return b''
        output=bytearray()
        while len(output)<n:
            if not self.block_start<=self.position<self.block_start+len(self.block):
                start=self.position
                end=min(self.size-1,start+max(65536,n-len(output))-1)
                with response(self.url,{'Range':f'bytes={start}-{end}'}) as r:
                    # Check before reading: never accidentally download a whole archive.
                    expected=f'bytes {start}-{end}/{self.size}'
                    if r.status!=206 or r.headers.get('Content-Range')!=expected:
                        raise ValueError('Server did not honor exact HTTP Range; no full-ZIP fallback')
                    self.url=r.url
                    self.block=r.read(end-start+2)
                if len(self.block)!=end-start+1: raise ValueError('Truncated range')
                self.network_bytes+=len(self.block)
                self.block_start=start
            start=self.position-self.block_start
            piece=self.block[start:start+n-len(output)]
            output.extend(piece)
            self.position+=len(piece)
        return bytes(output)


def safe_target(folder,name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or '\\' in name or ':' in name:
        raise ValueError(f'Unsafe archive member: {name}')
    target=(folder/Path(*p.parts)).resolve()
    if not target.is_relative_to(folder.resolve()): raise ValueError('Path escapes output folder')
    return target


def selected(name,include_positions=False):
    leaf=PurePosixPath(name).name.lower()
    # Deliberately excludes aoa/aod/power/phase/delay/channel/inter matrices.
    if leaf in ('objects.json','params.json','materials.json','materials.mtl','license','license.txt','license.md','notice','notice.txt'):
        return True
    if re.fullmatch(r'vertices(?:_[a-z0-9_-]+)?\.(?:npz|npy|mat)',leaf): return True
    if include_positions and re.fullmatch(r'(?:tx|rx)_(?:pos|loc)(?:_[a-z0-9_-]+)?\.(?:npz|npy|mat)',leaf): return True
    return False


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''): h.update(block)
    return h.hexdigest()


def dump(path,data):
    # Read existing UTF-8 metadata before replacing it; preserve source snapshots.
    if path.exists(): path.read_text()
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def run(args):
    manifest=json.loads(args.manifest.read_text())
    sources=sorted(manifest['source_usage'])
    if args.only:
        unknown=set(args.only)-set(sources)
        if unknown: raise ValueError(f'Not used by selected city: {sorted(unknown)}')
        sources=[s for s in sources if s in args.only]
    args.output.mkdir(parents=True,exist_ok=True)
    report_path=args.output/'download-plan.json'
    previous=json.loads(report_path.read_text()) if report_path.exists() else {}
    entries=previous.get('scenes',{})
    results=dict(entries)
    for source in sources:
        results.setdefault(source,{'status':'not_probed'})
    report={'date_utc':datetime.now(timezone.utc).isoformat(),'manifest':str(args.manifest.resolve()),
            'manifest_sha256':sha256(args.manifest),'source_count':len(sources),
            'scope':'Official geometry/topology/material parameters only; no source channel arrays',
            'city_size_m':args.size,
            'license':'Original source terms apply; permission and source-to-preview ID matching require separate verification.',
            'scenes':results}
    for source in sources:
        preview=PREVIEW_CACHE/f'{source}.json.gz'
        results[source]['local_preview_bytes']=preview.stat().st_size if preview.exists() else None
        if not (args.probe or args.download): continue
        row=results[source]
        if args.download and row.get('status')=='downloaded' and row.get('members'):
            folder=args.output/source
            hashes=row.get('sha256',{})
            complete=all(safe_target(folder,n).is_file() and safe_target(folder,n).stat().st_size==m['uncompressed_bytes'] and hashes.get(n)==sha256(safe_target(folder,n)) for n,m in row['members'].items())
            if complete and (not args.include_positions or row.get('include_positions')):
                print(source,'verified local files; no network request',flush=True)
                continue
        if results[source].get('members') and not args.download and not args.refresh:
            print(source,'cached inventory',flush=True)
            continue
        try:
            filename=source+'.zip'
            api=BASE+'/api/download/secure?'+urllib.parse.urlencode({'filename':filename})
            with response(api) as r: info=json.loads(r.read(1024*1024))
            if 'error' in info: raise RuntimeError(str(info))
            url=urllib.parse.urljoin(BASE,info['redirectUrl'])
            size=int(info['fileSize'])
            remote=RangeFile(url,size)
            with zipfile.ZipFile(remote) as archive:
                members=[i for i in archive.infolist() if not i.is_dir() and selected(i.filename,args.include_positions)]
                row={'status':'probed','archive_bytes':remote.size,'api_url':api,'include_positions':args.include_positions,
                     'members':{i.filename:{'compressed_bytes':i.compress_size,'uncompressed_bytes':i.file_size,'crc32':i.CRC} for i in members},
                     'selected_compressed_bytes':sum(i.compress_size for i in members),
                     'selected_uncompressed_bytes':sum(i.file_size for i in members),
                     'full_uncompressed_bytes':sum(i.file_size for i in archive.infolist() if not i.is_dir()),
                     'full_member_count':sum(not i.is_dir() for i in archive.infolist())}
                if not any(PurePosixPath(i.filename).name.lower()=='objects.json' for i in members):
                    row['warning']='objects.json absent: cannot assume complete mesh topology'
                if args.download:
                    available=shutil.disk_usage(args.output).free
                    if row['selected_uncompressed_bytes']>args.max_scene_mib*1024**2:
                        raise ValueError('Selected members exceed --max-scene-mib safety limit')
                    if row['selected_uncompressed_bytes']>available*.9:
                        raise ValueError('Insufficient free disk space')
                    folder=args.output/source
                    folder.mkdir(exist_ok=True)
                    hashes={}
                    old=results[source].get('sha256',{})
                    row['sha256']=hashes
                    results[source]=row
                    for item in members:
                        target=safe_target(folder,item.filename)
                        if target.exists():
                            if target.stat().st_size==item.file_size and old.get(item.filename)==sha256(target):
                                hashes[item.filename]=old[item.filename]
                                continue
                            raise ValueError(f'Existing unverified file: {target}; not overwriting')
                        target.parent.mkdir(parents=True,exist_ok=True)
                        # Exclusive creation. On failure leave .partial for inspection,
                        # never silently treat it as a completed member.
                        partial=target.with_name(target.name+'.partial')
                        if partial.exists():
                            # An interrupted ZIP member restarts from its beginning;
                            # completed files remain verified and are not downloaded again.
                            assert partial.resolve().is_relative_to(folder.resolve())
                            partial.stat()
                        with partial.open('wb') as out,archive.open(item) as src:
                            shutil.copyfileobj(src,out,length=1024*1024)
                        if partial.stat().st_size!=item.file_size: raise ValueError('Extracted size mismatch')
                        assert partial.resolve().is_relative_to(folder.resolve()) and not target.exists()
                        partial.rename(target)
                        hashes[item.filename]=sha256(target)
                        report['scenes']=results
                        dump(report_path,report)
                    row['sha256']=hashes
                    row['status']='downloaded'
                row['network_bytes_this_run']=remote.network_bytes
                results[source]=row
                print(source,row['status'],'ZIP',row['archive_bytes'],'geometry packed/unpacked',row['selected_compressed_bytes'],row['selected_uncompressed_bytes'],flush=True)
        except QuotaError as error:
            results[source]['error']=str(error)
            report['stopped_reason']=str(error)
            print('STOP:',error,file=sys.stderr)
            break
        except (OSError,ValueError,zipfile.BadZipFile,RuntimeError) as error:
            results[source]['error']=str(error)
            report['stopped_reason']=str(error)
            print('STOP:',source,error,file=sys.stderr)
            break
        finally:
            report['scenes']=results
            dump(report_path,report)
    known=[results[s] for s in sources if 'archive_bytes' in results[s]]
    report['totals']={'probed_scenes':len(known),'required_scenes':len(sources),
        'complete_inventory':len(known)==len(sources),
        'archive_bytes_known':sum(r['archive_bytes'] for r in known),
        'selected_compressed_bytes_known':sum(r.get('selected_compressed_bytes',0) for r in known),
        'selected_uncompressed_bytes_known':sum(r.get('selected_uncompressed_bytes',0) for r in known),
        'full_uncompressed_bytes_known':sum(r.get('full_uncompressed_bytes',0) for r in known),
        'full_uncompressed_inventory_complete':all('full_uncompressed_bytes' in r for r in known) and len(known)==len(sources),
        'local_preview_bytes':sum(r.get('local_preview_bytes') or 0 for r in results.values())}
    dump(report_path,report)
    print(json.dumps(report['totals'],ensure_ascii=False,indent=2))
    print('Report:',report_path)
    return 2 if 'stopped_reason' in report else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--size',type=int,choices=[1000,2000,4000],default=4000,help='City extent in meters; default 4000')
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--output',type=Path,default=Path('./data'),help='Download directory relative to current working directory (default: ./data/)')
    parser.add_argument('--probe',action='store_true',help='Authorize URLs and fetch ZIP directory only; may count against official quota')
    parser.add_argument('--download',action='store_true',help='Extract selected geometry/metadata files; complete verified files skipped')
    parser.add_argument('--only',nargs='+',help='Restrict to named sources used by the city')
    parser.add_argument('--refresh',action='store_true',help='Refresh cached inventory; never overwrites downloaded geometry')
    parser.add_argument('--include-positions',action='store_true',help='Also fetch source TX/RX coordinates for reference (not reused as city deployment)')
    parser.add_argument('--max-scene-mib',type=float,default=512)
    args=parser.parse_args()
    args.manifest=args.manifest or city_directory(args.size)/'assembled-city-manifest.json'
    args.output=args.output.resolve()
    return run(args)


if __name__=='__main__':
    sys.exit(main())
