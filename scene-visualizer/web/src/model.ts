export type Vec3 = [number, number, number];
export interface Tile { id: string; name: string; center: [number, number]; size: [number, number]; color: string }
export interface Building { id: string; name: string; tileId: string; position: Vec3; size: Vec3; material: string }
export interface RadioNode { id: string; name: string; position: Vec3 }
export interface Results {
  provenance: string; date: string; carrierGHz: number; txAntennas: number; subcarriers: number;
  beamPowers: number[][]; bestBeams: number[];
}
export interface SceneData {
  schemaVersion: 1; name: string; units: 'm'; coordinateSystem: 'z-up';
  tiles: Tile[]; buildings: Building[]; transmitters: RadioNode[]; receivers: RadioNode[];
  trajectory: { name: string; positions: Vec3[]; kind: 'sampled-positions'; results: Results | null };
  resultsValid: boolean;
}
export type Selection = { kind: 'tile' | 'building' | 'transmitter' | 'receiver'; id: string } | null;

const finite = (x: unknown): x is number => typeof x === 'number' && Number.isFinite(x) && Math.abs(x) <= 1e6;
const vector = (v: unknown, n: number): v is number[] => Array.isArray(v) && v.length === n && v.every(finite);
function assert(ok: unknown, message: string): asserts ok { if (!ok) throw new Error(message); }

/** Local, explicit interchange format; arbitrary JSON is never executed. */
export function parseScene(raw: unknown): SceneData {
  assert(raw && typeof raw === 'object', '场景必须是 JSON 对象。');
  const s = raw as SceneData;
  assert(s.schemaVersion === 1 && s.units === 'm' && s.coordinateSystem === 'z-up', '需要 schemaVersion=1、米制、z-up 的 Scene Studio 场景。');
  assert(typeof s.name === 'string' && s.name.length <= 120, '场景名称无效。');
  const ids = new Set<string>();
  function identity(o: {id: string; name: string}) {
    assert(o && typeof o.id === 'string' && /^[a-zA-Z0-9_-]{1,80}$/.test(o.id) && !ids.has(o.id), '对象 ID 必须唯一，且仅包含字母、数字、下划线或连字符。');
    assert(typeof o.name === 'string' && o.name.length <= 100, '对象名称无效。'); ids.add(o.id);
  }
  assert(Array.isArray(s.tiles) && s.tiles.length > 0 && s.tiles.length <= 100, '场景需要 1–100 个街区。');
  for (const t of s.tiles) {
    identity(t); assert(vector(t.center, 2) && vector(t.size, 2) && t.size.every(x => x > 0), '街区坐标或尺寸无效。');
    assert(typeof t.color === 'string' && /^#[0-9a-f]{6}$/i.test(t.color), '街区颜色需要六位十六进制格式。');
  }
  assert(Array.isArray(s.buildings) && s.buildings.length <= 10000, '建筑数量需不超过 10,000。');
  const tileIds = new Set(s.tiles.map(t => t.id));
  for (const b of s.buildings) {
    identity(b); assert(vector(b.position, 3) && vector(b.size, 3) && b.size.every(x => x > 0) && tileIds.has(b.tileId), '建筑坐标、尺寸或所属街区无效。');
    assert(typeof b.material === 'string' && b.material.length <= 80, '材料名称无效。');
  }
  for (const key of ['transmitters', 'receivers'] as const) {
    assert(Array.isArray(s[key]) && s[key].length <= 10000, '设备数量需不超过 10,000。');
    for (const n of s[key]) { identity(n); assert(vector(n.position, 3), '设备坐标无效。'); }
  }
  assert(s.trajectory && s.trajectory.kind === 'sampled-positions' && typeof s.trajectory.name === 'string' && s.trajectory.name.length <= 120 && Array.isArray(s.trajectory.positions) && s.trajectory.positions.length > 0 && s.trajectory.positions.length <= 20000 && s.trajectory.positions.every(p => vector(p, 3)), '轨迹需包含 1–20,000 个有效位置。');
  assert(typeof s.resultsValid === 'boolean', '缺少结果有效性标记。');
  const r = s.trajectory.results;
  if (r !== null) {
    assert(r && typeof r.provenance === 'string' && r.provenance.length <= 500 && typeof r.date === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(r.date), '结果来源或日期无效。');
    assert(finite(r.carrierGHz) && r.carrierGHz > 0 && Number.isInteger(r.txAntennas) && r.txAntennas > 0 && Number.isInteger(r.subcarriers) && r.subcarriers > 0, '无线配置无效。');
    assert(Array.isArray(r.beamPowers) && r.beamPowers.length === s.trajectory.positions.length && Array.isArray(r.bestBeams) && r.bestBeams.length === r.beamPowers.length, '结果数量与轨迹位置不匹配。');
    const count = r.beamPowers[0]?.length;
    assert(count > 0 && count <= 512, '波束数量需为 1–512。');
    for (const [i, powers] of r.beamPowers.entries()) {
      assert(vector(powers, count) && powers.every(x => x >= 0), '波束增益包含无效数值。');
      const beam = r.bestBeams[i];
      assert(Number.isInteger(beam) && beam >= 0 && beam < count, '最佳波束索引越界。');
      assert(powers[beam] === Math.max(...powers), '最佳波束与增益数据不一致。');
    }
  }
  return structuredClone(s);
}

export function bounds(s: SceneData) {
  return {
    minX: Math.min(...s.tiles.map(t => t.center[0] - t.size[0] / 2)),
    maxX: Math.max(...s.tiles.map(t => t.center[0] + t.size[0] / 2)),
    minY: Math.min(...s.tiles.map(t => t.center[1] - t.size[1] / 2)),
    maxY: Math.max(...s.tiles.map(t => t.center[1] + t.size[1] / 2)),
  };
}
export function plannedTrajectory(s: SceneData): Vec3[] {
  const b = bounds(s), y = (b.minY + b.maxY) / 2;
  return Array.from({length: 61}, (_, i) => [b.minX + 5 + (b.maxX - b.minX - 10) * i / 60, y, 1.5]);
}
export function trajectoryLength(points: Vec3[]) { return points.slice(1).reduce((sum, p, i) => sum + Math.hypot(...p.map((x,j) => x - points[i][j])), 0); }
export function moveTile(s: SceneData, id: string, next: [number, number]) {
  const t = s.tiles.find(x => x.id === id)!;
  const dx = next[0] - t.center[0], dy = next[1] - t.center[1]; t.center = next;
  for (const b of s.buildings.filter(x => x.tileId === id)) { b.position[0] += dx; b.position[1] += dy; }
  s.resultsValid = false;
}
export function addTile(s: SceneData): string {
  const base = s.tiles[s.tiles.length - 1], box = bounds(s);
  const suffix = crypto.randomUUID().slice(0, 8), id = `tile_${suffix}`;
  const center: [number, number] = [box.maxX + base.size[0] / 2, base.center[1]];
  s.tiles.push({...structuredClone(base), id, name: `街区 ${s.tiles.length + 1}`, center});
  for (const [i, b] of s.buildings.filter(x => x.tileId === base.id).entries()) {
    s.buildings.push({...structuredClone(b), id: `building_${suffix}_${i}`, name: `建筑 ${s.buildings.length + 1}`, tileId: id, position: [b.position[0] + center[0] - base.center[0], b.position[1], b.position[2]]});
  }
  s.resultsValid = false; return id;
}
export function seamStatus(s: SceneData): string {
  if (s.tiles.length === 1) return '单街区';
  // Deliberately a 2D, axis-aligned footprint check; not propagation validation.
  const adjacent = new Map(s.tiles.map(t => [t.id, [] as string[]]));
  for (let i=0;i<s.tiles.length;i++) for(let j=i+1;j<s.tiles.length;j++) {
    const a=s.tiles[i],b=s.tiles[j];
    const ox=(a.size[0]+b.size[0])/2-Math.abs(a.center[0]-b.center[0]);
    const oy=(a.size[1]+b.size[1])/2-Math.abs(a.center[1]-b.center[1]);
    if(ox>0.001 && oy>0.001) return '存在地面重叠';
    if((Math.abs(ox)<0.001 && oy>0.001)||(Math.abs(oy)<0.001 && ox>0.001)) { adjacent.get(a.id)!.push(b.id); adjacent.get(b.id)!.push(a.id); }
  }
  const seen=new Set<string>(), queue=[s.tiles[0].id];
  while(queue.length) {const id=queue.pop()!;if(seen.has(id))continue;seen.add(id);queue.push(...adjacent.get(id)!);}
  return seen.size===s.tiles.length?'地面边界相接':'存在分离街区';
}
