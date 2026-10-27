import './app.css';
import { CityViewport } from './city-viewport';
import type { CatalogEntry, CityData, InspectObject, Layer, UESampling } from './types';

const $ = <T extends HTMLElement = HTMLElement>(selector: string) =>
  document.querySelector<T>(selector)!;
const escape = (value: unknown) => String(value ?? '—').replace(/[&<>"']/g, character => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[character]!));
const format = (value: number) => value.toLocaleString('zh-CN', { maximumFractionDigits: 2 });
const record = (value: unknown) => escape(
  typeof value === 'object' && value !== null ? JSON.stringify(value) : value,
);
const row = (label: string, value: string) => `<dt>${escape(label)}</dt><dd>${value}</dd>`;
const layers: [Layer, string][] = [
  ['buildings', '建筑'], ['terrain', '地形'], ['roads', '道路'], ['parks', '公园'],
  ['vegetation', '全部植被'], ['source_vegetation', '源植被简化体'],
  ['synthetic_vegetation', '合成树'], ['bs', 'BS 站点'], ['sectors', '扇区方向'],
  ['ue', 'UE 候选点'], ['labels', '标签'], ['boundaries', '建筑边界'],
  ['grid', '参考网格'], ['parcels', '地块'],
];

async function json<T>(url: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`加载失败 HTTP ${response.status}：${url}`);
  return response.json();
}

async function loadPositions(sampling: UESampling, signal: AbortSignal): Promise<Float32Array> {
  if (!Number.isSafeInteger(sampling.count) || sampling.count < 0) {
    throw new Error('UE 候选点数量无效');
  }
  const response = await fetch(sampling.positions_url, { signal });
  if (!response.ok) throw new Error(`UE 采样加载失败 HTTP ${response.status}`);
  const buffer = await response.arrayBuffer();
  if (buffer.byteLength !== sampling.count * 12) throw new Error('UE 采样文件大小不匹配');
  const view = new DataView(buffer);
  const positions = new Float32Array(sampling.count * 3);
  for (let i = 0; i < positions.length; i++) {
    const value = view.getFloat32(i * 4, true);
    if (!Number.isFinite(value)) throw new Error(`UE 坐标无效：分量 ${i}`);
    positions[i] = value;
  }
  return positions;
}

function inspector(object: InspectObject | null) {
  $('#focus').toggleAttribute('disabled', !object);
  if (!object) {
    $('#inspector').innerHTML = '<p class="note">点击建筑、植被或 BS 查看属性。</p>';
    return;
  }
  const planning = object.radioPlanning;
  const details = [
    row('位置 X / Y / Z', `${object.position.map(format).join(' / ')} m`),
    row('高度', `${format(object.height)} m`),
    row('旋转', `${format(object.rotation)}°`),
    row('来源', record(object.source)),
    row('源对象', record(object.sourceObject)),
  ];
  if (object.officialObjectId !== undefined) details.push(row('官方对象 ID', escape(object.officialObjectId)));
  if (object.officialObjectName) details.push(row('官方对象名称', escape(object.officialObjectName)));
  if (object.officialObjectIndex !== undefined) details.push(row('官方对象索引', escape(object.officialObjectIndex)));
  if (object.placement) details.push(row('安装 / 放置', escape(object.placement)));
  if (object.provenance) details.push(row('出处', escape(object.provenance)));
  if (planning) {
    details.push(
      row('选址原因', escape(planning.reason)),
      row('方位角（东起逆时针）', planning.azimuths.map(value => `${format(value)}°`).join(' / ')),
      row('下倾角', planning.downtilts.map(value => `${format(value)}°`).join(' / ')),
    );
  }
  const materials = (object.materialRecords ?? []).map(({ key, record: material }) => `
    <details><summary>${escape(material?.name ?? key)}</summary><dl>
      ${row('面材料键', escape(key))}
      ${material ? [
        row('材料 ID', escape(material.id)),
        row('相对介电常数 εr', record(material.permittivity)),
        row('电导率 σ（S/m）', record(material.conductivity)),
        row(material.thickness_m !== undefined ? '厚度（m）' : '厚度（源记录）', record(material.thickness_m ?? material.thickness)),
        row('参考频率（Hz）', record(material.reference_frequency_hz)),
        row('来源场景', escape(material.source_scene)),
        row('材料出处', record(material.provenance)),
      ].join('') : row('材料记录', '未提供')}
    </dl></details>`).join('');
  $('#inspector').innerHTML = `
    <h3>${escape(object.title)}</h3><p class="note">${escape(object.kind)} · ${escape(object.role)}</p>
    <dl>${details.join('')}</dl>
    ${planning ? '<p class="note">BS 为规划站址；箭头仅示意朝向，不代表覆盖。RF 覆盖、容量与信道未验证。</p>' : ''}
    ${materials ? `<h3>源面材料</h3>${materials}<p class="note">保留源参数与面关联；不代表已用于 RT。</p>` : ''}`;
}

async function start() {
  const catalog = await json<CatalogEntry[]>('/scenes/catalog.json');
  if (!catalog.length) throw new Error('场景目录为空');
  $('#app').innerHTML = `
    <header><h1>LCM Scene Visualizer</h1><span>城市几何 · 只读可视化</span></header>
    <main>
      <aside class="left">
        <h2>城市场景</h2>
        <div class="scene-list">${catalog.map(entry => `
          <button class="scene-card" data-scene="${escape(entry.id)}">
            <strong>${escape(entry.title)}</strong>
            <small>${format(entry.instance_count)} 建筑 · ${format(entry.extent_m[2] - entry.extent_m[0])} × ${format(entry.extent_m[3] - entry.extent_m[1])} m</small>
          </button>`).join('')}</div>
        <h2>显示图层</h2>
        <div class="layers">${layers.map(([id, label]) => `
          <label><span>${label}</span><input type="checkbox" data-layer="${id}" ${id === 'parcels' ? '' : 'checked'}></label>`).join('')}
          <label><span>按建筑高度着色</span><input id="height-color" type="checkbox" checked></label>
        </div>
        <p class="note">米制坐标：X 东 / Y 北 / Z 上。布局与环境为合成设计；地形为平坦 z=0。</p>
      </aside>
      <section class="viewer">
        <div class="scene-heading"><h2 id="title">加载中</h2><span id="status" role="status"></span></div>
        <div class="toolbar">
          <div><button id="perspective" class="active" aria-pressed="true">透视</button><button id="top" aria-pressed="false">正交俯视</button></div>
          <div><button id="fit">适配</button><button id="focus" disabled>聚焦选择</button><button id="capture">PNG 截图</button></div>
        </div>
        <div id="stage"><div id="loading" role="status">正在加载场景…</div></div>
        <p class="stage-help">左键旋转 · 滚轮缩放 · 中键 / 右键平移 · 点击对象查看属性</p>
        <p id="stats" class="note"></p>
        <p class="note">源植被为简化体，合成树非实测植被；蓝色 UE 点为候选采样位置，非真实订户或 RT 结果。</p>
      </section>
      <aside class="right">
        <h2>对象属性</h2><div id="inspector"></div>
        <section class="scene-info"><h2>场景信息</h2><div id="scene-info"></div></section>
        <p class="note">保留建筑与材料来源；来源许可审计待完成。本页面不计算射线追踪或信道。</p>
      </aside>
    </main>`;

  const viewport = new CityViewport($('#stage'));
  let current: CatalogEntry | undefined;
  let controller: AbortController | undefined;
  let version = 0;
  let top = false;

  async function select(id: string) {
    const entry = catalog.find(item => item.id === id);
    if (!entry) return;
    controller?.abort();
    controller = new AbortController();
    const { signal } = controller;
    const request = ++version;
    $('#loading').hidden = false;
    $('#loading').textContent = '正在加载场景…';
    $('#status').textContent = '加载中';
    document.querySelectorAll<HTMLButtonElement>('[data-scene]').forEach(button => {
      const active = button.dataset.scene === id;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
    try {
      const [data, positions] = await Promise.all([
        json<CityData>(entry.data_url, signal),
        entry.ue_sampling ? loadPositions(entry.ue_sampling, signal) : undefined,
      ]);
      if (signal.aborted || request !== version) return;
      viewport.setCity(data, entry, positions);
      viewport.fit(top);
      current = entry;
      inspector(null);
      $('#title').textContent = entry.title;
      $('#status').textContent = entry.status;
      const counts = viewport.diagnostics();
      $('#stats').textContent = `${format(counts.instanceCount)} 建筑 · ${format(counts.assetMeshes)} 共享资产 · ${format(counts.terrainTriangles)} 地形三角 · ${format(counts.vegetationCount)} 植被 · ${format(counts.bsSiteCount)} BS / ${format(counts.sectorCount)} 扇区 · ${format(counts.uePointCount)} UE 候选点`;
      const sampling = entry.ue_sampling;
      $('#scene-info').innerHTML = `<dl>
        ${row('来源场景', format(entry.source_count))}
        ${row('源材料记录', format(Object.keys(data.materials ?? {}).length))}
        ${sampling ? [
          row('UE 候选位置', format(sampling.count)),
          row('网格间距 / 高度', `${format(sampling.spacing_m)} / ${format(sampling.ue_height_m)} m`),
          row('建筑 / 植被净空', `${format(sampling.building_clearance_m)} / ${format(sampling.vegetation_clearance_m)} m`),
        ].join('') : ''}
      </dl>${data.source_notice ? `<p class="note">${escape(data.source_notice)}</p>` : ''}`;
      const ueToggle = $<HTMLInputElement>('[data-layer="ue"]');
      ueToggle.disabled = !sampling;
      viewport.setLayer('ue', Boolean(sampling) && ueToggle.checked);
      $('#loading').hidden = true;
    } catch (error) {
      if (signal.aborted || request !== version) return;
      $('#loading').textContent = error instanceof Error ? error.message : String(error);
      $('#status').textContent = '加载失败';
      console.error(error);
    }
  }

  Object.defineProperty(window, '__LCM_SCENE_DIAGNOSTICS__', {
    get: () => Object.freeze({ sceneId: current?.id, ...viewport.diagnostics() }),
    configurable: true,
  });
  viewport.onSelect = inspector;
  inspector(null);
  document.querySelectorAll<HTMLButtonElement>('[data-scene]').forEach(button => {
    button.onclick = () => void select(button.dataset.scene!);
  });
  document.querySelectorAll<HTMLInputElement>('[data-layer]').forEach(input => {
    input.onchange = () => viewport.setLayer(input.dataset.layer as Layer, input.checked);
  });
  $('#height-color').onchange = () => viewport.setHeightColor($<HTMLInputElement>('#height-color').checked);
  function setView(value: boolean) {
    top = value;
    viewport.fit(top);
    for (const [id, active] of [['top', top], ['perspective', !top]] as const) {
      $(`#${id}`).classList.toggle('active', active);
      $(`#${id}`).setAttribute('aria-pressed', String(active));
    }
  }
  $('#perspective').onclick = () => setView(false);
  $('#top').onclick = () => setView(true);
  $('#fit').onclick = () => viewport.fit(top);
  $('#focus').onclick = () => viewport.focusSelection();
  $('#capture').onclick = () => {
    const link = document.createElement('a');
    link.href = viewport.screenshot();
    link.download = `${current?.id ?? 'scene'}-${top ? 'top' : '3d'}.png`;
    link.click();
  };
  window.addEventListener('pagehide', () => {
    controller?.abort();
    viewport.dispose();
  });
  await select(catalog[0].id);
}

start().catch(error => {
  $('#app').innerHTML = `<div class="fatal"><h1>无法打开场景</h1><p>${escape(error instanceof Error ? error.message : error)}</p></div>`;
  console.error(error);
});
