import './app.css';
import { CityViewport, measureRTBatch } from './city-viewport';
import type { AvailableRTManifest, CatalogEntry, CityData, InspectObject, Layer, RTBatch, RTManifest, UESampling } from './types';

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
        <section class="rt-panel" aria-labelledby="rt-heading">
          <h2 id="rt-heading">已计算 RT · 只读参考</h2>
          <p class="note rt-scope">只显示已保存运行的采样结果，不代表全城传播、覆盖或容量已验证。</p>
          <p id="rt-availability" class="note" role="status">等待场景加载…</p>
          <div class="rt-controls">
            <label class="rt-toggle"><input id="rt-paths" type="checkbox" disabled><span>显示全部已计算RT路径</span></label>
            <label class="rt-sector">路径扇区<select id="rt-sector" disabled><option value="">全部已计算扇区</option></select></label>
            <label class="rt-toggle"><input id="rt-coverage" type="checkbox" disabled><span>显示功率参考 · 仅采样点</span></label>
          </div>
          <div id="rt-run" class="note"></div>
          <div id="rt-path-progress" hidden>
            <progress id="rt-progress" value="0" max="1" aria-label="RT 批次加载进度"></progress>
            <p id="rt-counts" class="note" role="status" aria-live="polite"></p>
          </div>
          <div id="rt-warning" class="rt-warning" hidden><p id="rt-warning-text"></p><button id="rt-continue">继续加载全部</button></div>
          <button id="rt-focus" class="rt-focus" disabled>聚焦 RT 采样范围</button>
          <div class="rt-legend" aria-label="RT 路径与采样图例">
            <span><i class="rt-swatch diffraction"></i>绕射 · 橙</span><span><i class="rt-swatch reflection"></i>反射 · 红</span>
            <span><i class="rt-swatch scatter"></i>散射 · 蓝</span><span><i class="rt-swatch transmit"></i>透射 · 紫</span>
            <span><i class="rt-swatch neutral"></i>直达 / 混合 / 未知 · 灰</span>
            <span><i class="rt-swatch tx"></i>TX 发射点 · 菱形</span><span><i class="rt-swatch rx"></i>RX 采样点 · 绿环</span>
            <span><i class="rt-swatch candidate"></i>UE 候选位置 · 小蓝点（非 RT）</span>
          </div>
          <p class="note">单一机制路径按机制着色；混合路径用灰线与实际交互点颜色，不将整条路径误归为一种机制。TX / RX 标记置顶显示，线段遵循场景遮挡。</p>
          <div id="rt-colorbar" hidden>
            <strong>Serving path gain (dB)</strong>
            <div class="rt-gradient" role="img" aria-label="采样增益从低到高的色标"></div>
            <div class="rt-range"><span id="rt-min">—</span><span id="rt-max">—</span></div>
            <p id="rt-coverage-note" class="note"></p>
          </div>
          <details id="rt-notes" hidden><summary>运行说明与边界</summary><ul></ul></details>
          <p class="note">“全部”指所选范围内全部已存路径；无 Top-K、功率阈值或静默截断。关闭路径选项可取消加载并释放路径资源。</p>
        </section>
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
  let rtManifest: AvailableRTManifest | undefined;
  let rtController: AbortController | undefined;
  let rtVersion = 0;
  let rtState: 'off' | 'loading' | 'paused' | 'complete' | 'error' = 'off';
  let rtDisplayBytes = 0;
  const rtPaths = $<HTMLInputElement>('#rt-paths');
  const rtCoverage = $<HTMLInputElement>('#rt-coverage');
  const rtSector = $<HTMLSelectElement>('#rt-sector');
  const displayBudgetStep = 64 * 1024 * 1024;

  function updateRTProgress(message: string) {
    const counts = viewport.rtDiagnostics();
    const progress = $<HTMLProgressElement>('#rt-progress');
    progress.max = Math.max(1, counts.rtBatchTotal);
    progress.value = counts.rtBatchCount;
    $('#rt-counts').textContent = `${message} · ${format(counts.rtBatchCount)} / ${format(counts.rtBatchTotal)} 批次 · ${format(counts.rtPathCount)} 路径 · ${format(counts.rtSegmentCount)} 线段`;
    $('#rt-focus').toggleAttribute('disabled', counts.rtPathCount === 0 && counts.rtTXCount === 0 && counts.rtCoverageCount === 0);
  }

  function stopRTPaths() {
    rtController?.abort();
    rtController = undefined;
    rtVersion++;
    viewport.clearRTPaths();
    rtState = 'off';
    rtDisplayBytes = 0;
    $('#rt-warning').hidden = true;
    $('#rt-path-progress').hidden = true;
    updateRTProgress('未启用');
  }

  function resetRT() {
    stopRTPaths();
    viewport.clearRTCoverage();
    rtManifest = undefined;
    rtPaths.checked = rtCoverage.checked = false;
    rtPaths.disabled = rtCoverage.disabled = rtSector.disabled = true;
    rtSector.innerHTML = '<option value="">全部已计算扇区</option>';
    $('#rt-run').textContent = '';
    $('#rt-colorbar').hidden = $('#rt-notes').hidden = true;
    $('#rt-focus').toggleAttribute('disabled', true);
    $('#rt-availability').textContent = '正在查询已计算 RT 结果…';
  }

  async function loadRTManifest(id: string, signal: AbortSignal, request: number) {
    try {
      const response = await fetch(`/scenes/${encodeURIComponent(id)}-rt.json`, { signal });
      if (signal.aborted || request !== version) return;
      if (response.status === 404) {
        $('#rt-availability').textContent = '当前服务未提供 RT 结果接口（旧服务兼容）；三城几何查看不受影响。';
        return;
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const manifest: RTManifest = await response.json();
      if (signal.aborted || request !== version) return;
      if (!manifest.available) {
        $('#rt-availability').textContent = manifest.reason || '此城市没有可展示的已计算 RT 结果。';
        return;
      }
      if (!Array.isArray(manifest.batches) || !manifest.coverage || !Array.isArray(manifest.coverage.positions) || !Array.isArray(manifest.coverage.gain_db) || !Array.isArray(manifest.notes)
        || !Number.isSafeInteger(manifest.ue_count) || manifest.ue_count < 0 || !Number.isSafeInteger(manifest.sector_count) || manifest.sector_count < 0
        || !manifest.batches.every(batch => typeof batch.url === 'string' && Number.isSafeInteger(batch.batch_index)))
        throw new Error('RT 索引格式不匹配');
      rtManifest = manifest;
      const sectors = [...new Set(manifest.batches.map(batch => String(batch.sector_id)))];
      rtSector.innerHTML = '<option value="">全部已计算扇区</option>' + sectors.map(id => `<option value="${escape(id)}">${escape(id)}</option>`).join('');
      rtSector.disabled = manifest.batches.length === 0;
      rtPaths.disabled = manifest.batches.length === 0;
      rtCoverage.disabled = manifest.coverage.positions.length === 0;
      $('#rt-availability').textContent = `已保存 ${format(manifest.batches.length)} 个批次；默认不加载路径。`;
      $('#rt-run').innerHTML = `<strong>${escape(manifest.run_label)}</strong><br>运行范围：${escape(manifest.scope)}<br>${format(manifest.ue_count)} 个 RT 采样 UE / ${format(manifest.sector_count)} 个已计算扇区；不是全城结果。`;
      $('#rt-notes').hidden = manifest.notes.length === 0;
      $('#rt-notes ul').innerHTML = manifest.notes.map(note => `<li>${escape(note)}</li>`).join('');
    } catch (error) {
      if (signal.aborted || request !== version) return;
      $('#rt-availability').textContent = `RT 索引暂不可用：${error instanceof Error ? error.message : String(error)}。几何展示不受影响。`;
    }
  }

  function confirmMoreRT(bytes: number, signal: AbortSignal, load: number): Promise<boolean> {
    rtState = 'paused';
    $('#rt-warning').hidden = false;
    $('#rt-warning-text').textContent = `显示数据估算将达 ${format(bytes / 1024 / 1024)} MiB（不含 JSON 解析等临时内存）。已暂停，尚未加载全部；继续可能增加内存占用。也可取消勾选路径释放资源。`;
    updateRTProgress('等待确认，当前仅为部分路径');
    return new Promise(resolve => {
      const button = $<HTMLButtonElement>('#rt-continue');
      const finish = (proceed: boolean) => {
        signal.removeEventListener('abort', abort);
        if (load === rtVersion) {
          button.onclick = null;
          $('#rt-warning').hidden = true;
        }
        resolve(proceed);
      };
      const abort = () => finish(false);
      button.onclick = () => finish(true);
      signal.addEventListener('abort', abort, { once: true });
      if (signal.aborted) abort();
    });
  }

  async function loadRTPaths() {
    stopRTPaths();
    const manifest = rtManifest;
    if (!rtPaths.checked || !manifest) return;
    const sector = rtSector.value;
    const batches = manifest.batches.filter(batch => !sector || String(batch.sector_id) === sector);
    rtController = new AbortController();
    const { signal } = rtController;
    const load = rtVersion;
    const cityRequest = version;
    const active = () => !signal.aborted && load === rtVersion && cityRequest === version && rtPaths.checked;
    let budget = displayBudgetStep;
    rtState = 'loading';
    viewport.setRTBatchTotal(batches.length);
    $('#rt-path-progress').hidden = false;
    updateRTProgress('开始逐批加载，当前尚未完整');
    try {
      for (const descriptor of batches) {
        if (!active()) return;
        updateRTProgress(`加载 ${descriptor.sector_id} / 批次 ${descriptor.batch_index}，当前仅为部分路径`);
        const batch = await json<RTBatch>(descriptor.url, signal);
        if (!active()) return;
        const measured = measureRTBatch(batch);
        const nextBytes = rtDisplayBytes + measured.displayBytes;
        if (nextBytes > budget) {
          if (!await confirmMoreRT(nextBytes, signal, load) || !active()) return;
          budget = nextBytes + displayBudgetStep;
          rtState = 'loading';
        }
        viewport.appendRTBatch(batch);
        rtDisplayBytes = nextBytes;
        updateRTProgress('逐批加载中，当前仅为部分路径');
        // Yield between batches; keep only the current JSON batch, not the whole run.
        await new Promise<void>(resolve => setTimeout(resolve, 0));
      }
      if (!active()) return;
      rtState = 'complete';
      updateRTProgress(sector ? `已完整加载所选扇区 ${sector} 的全部已存路径（非全城）` : '已完整加载本次运行的全部已存路径（非全城）');
    } catch (error) {
      if (!active()) return;
      rtState = 'error';
      updateRTProgress(`加载中止，当前仅为部分结果：${error instanceof Error ? error.message : String(error)}；关闭后重开可重试`);
    }
  }

  function showRTCoverage() {
    viewport.clearRTCoverage();
    $('#rt-colorbar').hidden = true;
    if (rtCoverage.checked && rtManifest) {
      try {
        if (rtManifest.coverage.positions.length * 48 > displayBudgetStep && !window.confirm('采样功率图层显示数据估算超过 64 MiB。继续显示全部采样点？不插值，也不抽样截断。')) {
          rtCoverage.checked = false;
          return;
        }
        viewport.setRTCoverage(rtManifest.coverage);
        const counts = viewport.rtDiagnostics();
        $('#rt-colorbar').hidden = false;
        $('#rt-min').textContent = counts.rtCoverageRange ? `${format(counts.rtCoverageRange[0])} dB` : '无有限值';
        $('#rt-max').textContent = counts.rtCoverageRange ? `${format(counts.rtCoverageRange[1])} dB` : '无有限值';
        $('.rt-gradient').hidden = counts.rtCoverageRange === null;
        $('.rt-gradient').classList.toggle('constant', Boolean(counts.rtCoverageRange && counts.rtCoverageRange[0] === counts.rtCoverageRange[1]));
        $('#rt-coverage-note').textContent = `${format(counts.rtCoverageCount)} 个运行采样位置，${format(counts.rtCoverageFiniteCount)} 个有限增益；灰色方点表示无有限增益。非相干、天线平均路径增益，非接收功率 dBm；只显示原采样点，不插值、不填充全城。色标按本次运行全部已计算扇区的 serving gain，不随路径扇区选择变化。${rtManifest.coverage.note}`;
      } catch (error) {
        rtCoverage.checked = false;
        viewport.clearRTCoverage();
        $('#rt-colorbar').hidden = false;
        $('.rt-gradient').hidden = true;
        $('#rt-min').textContent = $('#rt-max').textContent = '—';
        $('#rt-coverage-note').textContent = `采样功率图层不可用：${error instanceof Error ? error.message : String(error)}`;
      }
    }
    const counts = viewport.rtDiagnostics();
    $('#rt-focus').toggleAttribute('disabled', counts.rtPathCount === 0 && counts.rtTXCount === 0 && counts.rtCoverageCount === 0);
  }

  rtPaths.onchange = () => void loadRTPaths();
  rtSector.onchange = () => { if (rtPaths.checked) void loadRTPaths(); };
  rtCoverage.onchange = showRTCoverage;
  $('#rt-focus').onclick = () => viewport.focusRT();

  async function select(id: string) {
    const entry = catalog.find(item => item.id === id);
    if (!entry) return;
    controller?.abort();
    resetRT();
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
      void loadRTManifest(entry.id, signal, request);
    } catch (error) {
      if (signal.aborted || request !== version) return;
      $('#loading').textContent = error instanceof Error ? error.message : String(error);
      $('#status').textContent = '加载失败';
      console.error(error);
    }
  }

  Object.defineProperty(window, '__LCM_SCENE_DIAGNOSTICS__', {
    get: () => Object.freeze({
      sceneId: current?.id, ...viewport.diagnostics(),
      rtAvailable: Boolean(rtManifest), rtRunLabel: rtManifest?.run_label,
      rtScope: rtManifest?.scope, rtLoadState: rtState,
      rtSelectedSector: rtSector.value || 'all', rtPathsEnabled: rtPaths.checked,
      rtCoverageEnabled: rtCoverage.checked, rtDisplayBytes,
      rtProgress: { loaded: viewport.rtDiagnostics().rtBatchCount, total: viewport.rtDiagnostics().rtBatchTotal },
    }),
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
    rtController?.abort();
    viewport.dispose();
  });
  await select(catalog[0].id);
}

start().catch(error => {
  $('#app').innerHTML = `<div class="fatal"><h1>无法打开场景</h1><p>${escape(error instanceof Error ? error.message : error)}</p></div>`;
  console.error(error);
});
