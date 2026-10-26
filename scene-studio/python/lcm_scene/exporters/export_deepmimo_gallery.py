import sys
from pathlib import Path
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = 'lcm_scene.exporters'

"""Convert cached official geometry to the separate, read-only scene gallery format."""
import json,hashlib
from pathlib import Path
import numpy as np
from ..paths import REPO_ROOT, SOURCE_ROOT, WEB_ROOT
ROOT = REPO_ROOT
SRC = SOURCE_ROOT
DST = WEB_ROOT / "public/scenes/deepmimo"
CONFIG=[
('asu_campus_3p5','ASU 校园','01 / 首个实验','CSI 压缩 · 空间漂移',3.5,'先固定同一个 BS，在校园不同空间块训练和测试。适合比较保持、补测、重新校准与模型切换的证据成本。','静态采样网格没有物理时间轴。空间分布变化不代表模型一定退化；以独立测试区域的 NMSE / SGCS 和测量预算判断。'),
('asu_campus_3p5_dyn','ASU 动态校园','02 / 动态扩展','证据时效 · 移动 TX',3.5,'已抽查第 1 / 51 / 100 个快照：建筑和 RX 网格相同，一个 3 m 高 TX 移动、另一个 20 m 高 TX 固定。适合研究移动链路下的证据时效、复测与恢复。','仅展示原包 3 个快照，非连续动画；不能称为已验证的移动遮挡场景。物理帧间隔尚未确认；静态 ASU 也不是严格配对基线。'),
('o1_28','O1 城市街道','03 / 波束主场景','多站点 · 路口转向',28,'用空间连续且可通行的位置序列，研究波束预测模型的跨区域选择、稀疏扫描和传统扫描回退；后续再扩展多 BS。','静态网格不是实测移动轨迹。18 个 TX 的编号需以包内 set 映射为准；展示采样点不代表同时在线用户。'),
('o1b_28','O1 遮挡变体','03b / 遮挡压力测试','遮挡 · 反射面变化',28,'与 O1 系列一起用于受控域变化研究；先对齐 BS、RX 坐标、高度、材料和追踪参数，再比较候选模型与补测策略。','O1B 还增加反射面；与 O1 的网格、高度和反射阶数可能不同。不能把直接比较解释为仅增加遮挡的因果效应。'),
('boston5g_3p5','Boston 城市街区','04 / 外部泛化','复杂轮廓 · 跨地图测试',3.5,'在开发流程冻结后，用独立城市地图检验 CSI 模型选择和证据策略的迁移。与 ASU 同为 3.5 GHz，先保持阵列、带宽和任务一致。','与 ASU 的追踪设置也不同，因此跨数据集差异包含仿真配置影响。本页只展示当前选中 TX/RX 链路的采样点。'),
('city_99_shanghai_3p5','上海城市片区','05 / 可选扩展','多 BS · 第二个城市域',3.5,'有余力时再加入第二个城市域，检查选择策略是否只适用于一张外部地图；适合后续多站点实验。','目录报告 3 个 TX；当前官网预览接口只返回选中链路的 1 个 TX。没有在本次选型中验证信道质量或泛化收益。')]
def load_npz(path):
 with np.load(path,allow_pickle=False) as a:return a[a.files[0]].tolist()
def preview_frame(name):
 s=json.loads((SRC/(name+'-preview.json')).read_text());objs=[]
 for kind in ['buildings','terrain']:
  for i,obj in enumerate(s[kind]):
   faces=[]
   for face in obj:
    f=[p[:] for p in face]
    while f and f[-1]==[0,0,0]:f.pop() # API stores faces with zero padding.
    if len(f)>=3:faces.append(f)
   if faces:objs.append({'name':f'{kind}_{i}','kind':kind,'faces':faces})
 return {'name':'官网静态预览','objects':objs,'tx':[s['tx_pos']], 'rx':list(s['rx_pos'].values()),'rxIds':list(s['rx_pos']),'selectedLink':s.get('selectedTxRxSet')}
def archive_frames(name):
 base=SRC/name;idx=json.loads((base/'archive-index.json').read_text());frames=[]
 for folder in idx['selectedFrames']:
  d=base/folder;vertices=load_npz(d/'vertices.npz');objects=json.loads((d/'objects.json').read_text());objs=[]
  for obj in objects:
   objs.append({'name':obj['name'],'kind':'terrain' if 'terrain' in obj.get('label','').lower() else 'buildings','faces':[[vertices[v] for v in face] for face in obj['face_vertex_idxs']]})
  tx=[]
  for path in sorted(d.glob('tx_pos*_r000.npz')):
   points=load_npz(path)
   if points and isinstance(points[0],(int,float)):points=[points]
   for p in points:
    if p not in tx:tx.append(p)
  paths=sorted(d.glob('rx_pos*_r000.npz'));rx=load_npz(paths[0]) if paths else []
  stride=max(1,len(rx)//1800);sample=rx[::stride]
  frames.append({'name':f"原包快照 {idx['frames'].index(folder)+1} / {len(idx['frames'])}",'archiveFolder':folder,'objects':objs,'tx':tx,'rx':sample,'rxIds':list(range(0,len(rx),stride)),'selectedLink':paths[0].stem if paths else '', 'sourceRxCount':len(rx)})
 return frames
def main():
 CAT=json.loads((SRC/"catalog.json").read_text())
 DST.mkdir(parents=True, exist_ok=True)
 entries=[]
 for name,title,priority,task,freq,why,limit in CONFIG:
  if (SRC/(name+'-preview.json')).exists():frames=[preview_frame(name)];kind='official-preview-api'
  elif (SRC/name/'archive-index.json').exists():frames=archive_frames(name);kind='official-archive-members'
  else:print('SKIP missing geometry',name);continue
  records=[x for x in CAT if x['linkName']==name and x.get('subMenu')=='v4']
  meta=records[-1];data={'id':name,'frames':frames,'sourceKind':kind,'date':'2026-10-25','coordinateSystem':'z-up','units':'m'}
  for frame in frames:
   assert frame['objects'] and frame['tx']
   assert all(np.isfinite(p).all() for o in frame['objects'] for f in o['faces'] for p in f)
  (DST/(name+'.json')).write_text(json.dumps(data,separators=(',',':'),ensure_ascii=False))
  entries.append({'id':name,'title':title,'priority':priority,'task':task,'frequency':freq,'why':why,'limit':limit,'source':f'https://www.deepmimo.net/scenarios/v4/{name}','version':meta['download'][0]['version'],'catalogTx':meta['advancedParameters']['numTx'],'catalogRx':meta['features']['numRx'],'frames':len(frames),'sourceKind':kind})
  print(name,'objects',len(frames[0]['objects']),'tx',len(frames[0]['tx']),'rx preview',len(frames[0]['rx']),'frames',len(frames))
 (DST/'catalog.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2))
 files=[p for p in SRC.rglob('*') if p.is_file() and p.name!='manifest.json']
 (SRC/'manifest.json').write_text(json.dumps({'date':'2026-10-25','source':'https://www.deepmimo.net','licenseNote':'Third-party DeepMIMO scene assets; original terms apply. Local research visualization, no ownership or license reassignment.','files':{str(p.relative_to(SRC)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}},indent=2))


if __name__ == "__main__":
 main()
