import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.sources'

"""Fetch official preview geometry and selected ZIP members, never full CSI archives.
Run from repository root: uv run --with numpy python tools/scene-studio/scripts/fetch_deepmimo_geometry.py
Data remains third-party DeepMIMO material; see source/manifest.json and selection report.
"""
import concurrent.futures as cf
import hashlib, json, struct, urllib.request, urllib.parse, urllib.error, zlib
from pathlib import Path
from ..paths import REPO_ROOT, SOURCE_ROOT
ROOT = REPO_ROOT
OUT = SOURCE_ROOT
BASE='https://www.deepmimo.net'
def request(url, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}),timeout=60) as r:
        return r.read()
class RemoteZip:
    def __init__(self,name,location=None):
        self.name = name
        if location:
            self.size=int(location['size']);self.url=location['url']
        else:
            info=json.loads(request(BASE+'/api/download/secure?filename='+name+'.zip'))
            self.size=int(info['fileSize']); self.url=urllib.parse.urljoin(BASE,info['redirectUrl'])
        tail=self.read(max(0,self.size-65536),self.size-1)
        p=tail.rfind(b'PK\x05\x06'); h=struct.unpack_from('<4s4H2LH',tail,p)
        if h[6]==0xffffffff:raise ValueError('ZIP64 is not supported by this selective extractor')
        central=self.read(h[6],h[6]+h[5]-1);self.entries={};p=0
        while central[p:p+4]==b'PK\x01\x02':
            h=struct.unpack_from('<4s6H3L5H2L',central,p)
            n=central[p+46:p+46+h[10]].decode()
            self.entries[n]={'method':h[4],'crc':h[7],'compressed':h[8],'size':h[9],'offset':h[-1]}
            p+=46+h[10]+h[11]+h[12]
    def read(self,a,b):
        with urllib.request.urlopen(urllib.request.Request(self.url,headers={'Range':f'bytes={a}-{b}'}),timeout=60) as r:
            if r.status!=206 or r.headers.get('Content-Range','').split('/')[0]!=f'bytes {a}-{b}':
                raise ValueError('Server did not honor requested byte range')
            self.url=r.url
            return r.read()
    def extract(self,n):
        e=self.entries[n];a=e['offset'];h=self.read(a,a+29);v=struct.unpack('<4s5H3L2H',h)
        start=a+30+v[-2]+v[-1];data=self.read(start,start+e['compressed']-1)
        data=zlib.decompress(data,-15) if e['method']==8 else data
        if len(data)!=e['size'] or zlib.crc32(data)!=e['crc']:raise ValueError('ZIP CRC mismatch')
        path=OUT/self.name/n;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        return n

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    catalog=request(BASE+'/api/scenarios');(OUT/'catalog.json').write_bytes(catalog)
    for name in ['asu_campus_3p5','boston5g_3p5','city_99_shanghai_3p5']:
        path=OUT/(name+'-preview.json')
        if not path.exists():path.write_bytes(request(BASE+'/api/dataset/initial?'+urllib.parse.urlencode({'datasetName':name,'spacingX':12,'spacingY':12})))
        s=json.loads(path.read_text());assert 'buildings' in s
        print(name,'preview objects',len(s['buildings']),flush=True)
    for name in ['asu_campus_3p5_dyn','o1_28','o1b_28']:
        index=OUT/name/'archive-index.json'
        if index.exists():continue
        try:
            z=RemoteZip(name);z.name=name
        except urllib.error.HTTPError as error:
            print(name, 'unavailable: HTTP', error.code, '— no substitute geometry', flush=True)
            continue
        folders=sorted({n.rsplit('/',1)[0] for n in z.entries if n.endswith('objects.json')})
        selected=[folders[i] for i in sorted({0,len(folders)//2,len(folders)-1})]
        names=[n for n in z.entries if any(n.startswith(f+'/') for f in selected) and (n.endswith(('objects.json','params.json','vertices.npz')) or (n.rsplit('/',1)[-1].startswith(('rx_pos_', 'tx_pos_')) and n.endswith('.npz') and ('_r000' in n or '_r003' in n)))]
        print(name,'archive bytes',z.size,'frames',len(folders),'selected',len(selected),'members',len(names),flush=True)
        with cf.ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(z.extract,names))
        index.parent.mkdir(parents=True,exist_ok=True)
        index.write_text(json.dumps({'archiveBytes':z.size,'frames':folders,'selectedFrames':selected,'members':{n:z.entries[n] for n in names}},indent=2))
    files=[p for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json']
    (OUT/'manifest.json').write_text(json.dumps({'date':'2026-10-25','source':BASE,'note':'Official preview API / selective archive members; no CSI generated. Original data license is not replaced by project code license.','files':{str(p.relative_to(OUT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}},indent=2))
if __name__=='__main__':main()
