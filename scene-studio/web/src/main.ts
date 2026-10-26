import './style.css';
import { Viewport } from './viewport';
import { addTile, bounds, moveTile, parseScene, plannedTrajectory, seamStatus, trajectoryLength, type SceneData, type Selection, type Vec3 } from './model';

const paths: Record<string,string> = {
  cube:'m12 3 9 5v9l-9 5-9-5V8zm0 9 9-4M3 8l9 4v10',
  plus:'M12 5v14M5 12h14', chevron:'m9 5 7 7-7 7',
  upload:'M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5', download:'M12 3v13m-5-5 5 5 5-5M4 17v4h16v-4',
  grid:'M3 3h18v18H3zM3 9h18M3 15h18M9 3v18M15 3v18',
  building:'M5 21V4h10v17m0-12h5v12M3 21h19M8 8h4M8 12h4M8 16h4',
  radio:'M12 13v8m-4 0h8M8 10a6 6 0 0 1 0-8m8 0a6 6 0 0 1 0 8M5 13a10 10 0 0 1 0-14m14 0a10 10 0 0 1 0 14M12 5v2',
  point:'M12 3a7 7 0 0 1 7 7c0 5-7 11-7 11S5 15 5 10a7 7 0 0 1 7-7Zm0 4v6m-3-3h6',
  route:'M4 18c0-8 16 0 16-9S4 15 4 6M3 3h3v3H3zM18 18h3v3h-3z',
  layers:'m12 3 10 6-10 6L2 9zm-10 11 10 6 10-6M2 18l10 6 10-6',
  play:'m8 5 12 7-12 7z',pause:'M8 5v14M16 5v14',step:'m5 5 10 7-10 7zm13 0v14',
  reset:'M3 10a9 9 0 1 1 2 8M3 3v7h7',focus:'M8 3H3v5m13-5h5v5M3 16v5h5m8 0h5v-5M8 12h8M12 8v8',
  camera:'M3 7h4l2-3h6l2 3h4v14H3zm9 3a4 4 0 1 0 0 8 4 4 0 0 0 0-8',
  minus:'M5 12h14',info:'M12 11v6m0-10v1M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20',
  arrow:'M7 17 17 7M7 7h10v10', undo:'M3 10h11a6 6 0 0 1 0 12M3 10l6-6M3 10l6 6',close:'m6 6 12 12M6 18 18 6',
};
function icon(name:string) {return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${paths[name]??paths.cube}"/></svg>`;}
const esc=(s:string)=>s.replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const $=<T extends HTMLElement=HTMLElement>(s:string)=>document.querySelector<T>(s)!;
const format=(n:number)=>Number.isInteger(n)?String(n):n.toFixed(2).replace(/0+$/,'').replace(/\.$/,'');
const app=$('#app');

async function start() {
  const response=await fetch('/scenes/verified-street.json');if(!response.ok)throw new Error('无法加载内置场景。');
  const baseline=parseScene(await response.json());let data=structuredClone(baseline);
  let selection:Selection={kind:'tile',id:data.tiles[1].id};
  let mode:'verified'|'planned'='verified',index=0,playing=false,lastStep=0,interval=650;
  const history:SceneData[]=[];
  let toastTimer:number;

  app.innerHTML=`
  <header class="app-header">
    <a class="brand" href="/" aria-label="LCM Scene Studio 首页"><span class="brand-mark">${icon('cube')}</span><span>LCM <b>Scene Studio</b><small>无线场景工作台</small></span></a>
    <div class="header-center"><span class="workspace-dot"></span> 本地工作区 <span class="slash">/</span> <span>场景编辑器</span></div>
    <div class="header-actions"><button class="button subtle" id="import">${icon('upload')}导入场景</button><button class="button primary" id="export">${icon('download')}导出 JSON</button><button class="icon-button" id="help" aria-label="使用说明">${icon('info')}</button></div>
  </header>
  <div class="project-header"><div><div class="eyebrow">SCENE WORKSPACE <span>01</span></div><h1 id="scene-name"></h1></div><div class="project-meta"><span class="status-badge" id="result-status"></span><span class="project-dim" id="dimensions"></span></div></div>
  <main class="workspace">
    <aside class="left-panel">
      <div class="panel-heading"><h2>场景资源</h2><button class="icon-button small" id="add-tile" aria-label="新增街区" title="复制末尾街区并拼接到东侧">${icon('plus')}</button></div>
      <div class="resource-summary" id="resource-summary"></div>
      <div class="scene-tree" id="scene-tree"></div>
      <div class="layers-panel"><div class="section-label">${icon('layers')} 图层显示</div>
      ${[['buildings','建筑模型'],['receivers','静态 UE'],['trajectory','移动轨迹'],['grid','参考网格'],['labels','对象标注'],['connection','设备连线 · 示意']].map(([key,label])=>`<label class="layer-row"><span>${label}</span><input type="checkbox" data-layer="${key}" ${key==='connection'?'':'checked'}><span class="switch"></span></label>`).join('')}
      </div>
      <button class="source-card" id="source-info"><span class="source-icon">${icon('radio')}</span><span><b>数据来源与适用范围</b><small id="source-version"></small></span>${icon('arrow')}</button>
    </aside>
    <section class="center-panel" aria-label="地图和轨迹回放">
      <div class="stage-toolbar"><div class="view-toggle"><button class="active" id="perspective">${icon('cube')}透视</button><button id="top-view">${icon('grid')}俯视</button></div><div class="toolbar-right"><span id="seam-status"></span><button class="icon-button small" id="undo" aria-label="撤销修改" disabled>${icon('undo')}</button><button class="icon-button small" id="reset" aria-label="恢复内置场景" title="恢复内置场景">${icon('reset')}</button></div></div>
      <div class="stage" id="stage"><div class="stage-caption"><span class="dot teal"></span> 三维场景 <span class="caption-separator">·</span> <span id="scene-count"></span></div><div class="stage-tools"><button class="icon-button" id="fit" aria-label="适配整个场景" title="适配整个场景">${icon('focus')}</button><button class="icon-button" id="zoom-in" aria-label="放大">${icon('plus')}</button><button class="icon-button" id="zoom-out" aria-label="缩小">${icon('minus')}</button><span></span><button class="icon-button" id="screenshot" aria-label="保存地图图片" title="保存地图图片">${icon('camera')}</button></div>
      <div class="stage-bottom"><div class="axis-widget"><span class="axis-n">N</span><span class="axis-center">↗</span><span class="axis-z">Z ↑</span></div><div class="map-legend"><span><i class="legend-node blue"></i>静态 UE</span><span><i class="legend-node teal"></i>移动 UE</span><span><i class="legend-line"></i>街区边界</span></div><div class="map-units">单位 · 米</div></div></div>
      <div class="timeline"><div class="timeline-heading"><div class="timeline-title">${icon('route')}<h2>轨迹回放</h2><span class="tiny-badge" id="track-count"></span></div><select id="track-mode" aria-label="选择轨迹"><option value="verified">已仿真片段 · 2 m</option><option value="planned">全街区预览 · 无信道结果</option></select></div>
        <div class="playback"><button class="play-button" id="play" aria-label="播放轨迹">${icon('play')}</button><button class="icon-button" id="next" aria-label="下一个位置">${icon('step')}</button><span class="sample-index" id="sample-index"></span><input id="scrubber" type="range" min="0" max="8" value="0" step="1" aria-label="轨迹样本位置"><select id="speed" aria-label="回放速度"><option value="650">1×</option><option value="325">2×</option><option value="1300">0.5×</option></select></div>
        <div class="timeline-footer"><span id="position-readout"></span><button id="focus-ue">聚焦移动 UE ${icon('focus')}</button><span class="playback-note">按采样位置回放，非物理速度</span></div>
      </div>
    </section>
    <aside class="right-panel"><div class="panel-heading"><h2>对象属性</h2><span class="eyebrow">INSPECTOR</span></div><div id="inspector"></div>
      <section class="radio-panel"><div class="section-title"><h2>无线配置</h2><span class="tiny-badge">记录值</span></div><div class="radio-grid" id="radio-config"></div></section>
      <section class="beam-panel"><div class="section-title"><h2>波束增益</h2><span class="tiny-badge" id="beam-badge"></span></div><div id="beam-chart"></div><div class="beam-caption">固定 DFT 码本 · 相对信道增益 / dB</div></section>
      <div class="notice" id="notice"></div>
    </aside>
  </main>
  <footer class="statusbar"><span><i></i> <span id="save-status">内置场景已加载</span></span><span>拖动旋转 <em>·</em> 滚轮缩放 <em>·</em> 右键平移</span><span>坐标 X / Y / Z ↑ <em>·</em> Three.js</span></footer>
  <input id="file-input" type="file" accept=".json,application/json" hidden>
  <div id="toast" role="status" aria-live="polite"></div>
  <dialog id="help-dialog"><div class="dialog-heading"><span class="brand-mark">${icon('cube')}</span><h2>关于这个工作台</h2><button class="icon-button" id="close-help" aria-label="关闭说明">${icon('close')}</button></div>
    <p>用三维视图检查街区、设备和移动轨迹。点击地图或左侧对象，在右侧修改位置与尺寸；新增街区会复制末尾街区并放到东侧。</p>
    <h3>当前文件的来源记录</h3><p id="current-provenance"></p>
    <h3>内置样本</h3><p>内置场景对应 2026-10-25 的 Sionna RT 2.2.0 最小核验：两个 40 × 50 m 街区、4 栋建筑、8 个静态位置、9 个移动位置。波束数据直接导出自本地 <code>samples.npz</code>，不是前端生成的示例数值。</p>
    <h3>几何与信道分别管理</h3><p>地图编辑在浏览器中完成，不运行电磁仿真。修改几何或设备后，原波束结果停止显示；需要重新计算信道再导入。地面接缝检查只判断矩形边界，不验证道路、遮挡或传播连续性。</p>
    <h3>导入与导出</h3><p>支持 Scene Studio JSON v1，米制、Z 轴向上。导出包含几何、设备、轨迹和已有波束结果；完整复数 CSI 保留在原始 NPZ 中。暂不直接读取 Sionna XML、OBJ、GLB 或 DeepMIMO 场景包。</p>
    <p class="dialog-footnote">导入文件的来源由文件提供，不构成独立核验。预览轨迹没有信道结果；视觉道路与立面装饰不参与电磁计算。</p>
  </dialog>`;

  const viewport=new Viewport($('#stage'));
  const points=()=>mode==='verified'?data.trajectory.positions:plannedTrajectory(data);
  function toast(message:string) {$('#toast').textContent=message;$('#toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=window.setTimeout(()=>$('#toast').classList.remove('visible'),3200);}
  function setPlaying(value:boolean) {playing=value;$('#play').innerHTML=icon(value?'pause':'play');$('#play').setAttribute('aria-label',value?'暂停轨迹':'播放轨迹');lastStep=performance.now();}
  function remember() {history.push(structuredClone(data));if(history.length>30)history.shift();}
  function downloadable(content:Blob|string,name:string) {const url=typeof content==='string'?content:URL.createObjectURL(content);const a=document.createElement('a');a.href=url;a.download=name;a.click();if(typeof content!=='string')window.setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function selectedObject() {
    if(!selection)return null;
    const {kind,id}=selection;
    return (kind==='tile'?data.tiles:kind==='building'?data.buildings:kind==='transmitter'?data.transmitters:data.receivers).find(o=>o.id===id)??null;
  }
  function renderTree() {
    function row(kind:NonNullable<Selection>['kind'],id:string,name:string,ico:string,child=false) {return `<button class="tree-row ${child?'child':''} ${selection?.id===id?'selected':''}" data-select="${kind}:${id}" aria-pressed="${selection?.id===id}">${icon(ico)}<span>${esc(name)}</span>${selection?.id===id?'<i></i>':''}</button>`;}
    $('#scene-tree').innerHTML=data.tiles.map(t=>`<div class="tree-group">${row('tile',t.id,t.name,'layers')}${data.buildings.filter(b=>b.tileId===t.id).map(b=>row('building',b.id,b.name,'building',true)).join('')}</div>`).join('')+
      `<div class="tree-group"><div class="tree-category">收发设备 <span>${data.transmitters.length+data.receivers.length}</span></div>${data.transmitters.map(t=>row('transmitter',t.id,t.name,'radio')).join('')}${data.receivers.map(t=>row('receiver',t.id,t.name,'point',true)).join('')}</div>`;
  }
  function renderInspector() {
    const o=selectedObject();
    if(!o || !selection) {$('#inspector').innerHTML='<div class="empty-inspector">选择一个对象<br><small>点击地图中的建筑、街区或设备</small></div>';return;}
    const kind=selection.kind, position=kind==='tile'?[...(o as SceneData['tiles'][number]).center,0]:(o as {position:Vec3}).position;
    const labels={tile:'街区',building:'建筑',transmitter:'基站',receiver:'静态 UE'};
    const field=(key:string,label:string,value:number,min?:number)=>`<label class="number-field"><span>${label}</span><input type="number" step="0.25" ${min===undefined?'':`min="${min}"`} max="1000000" data-property="${key}" value="${format(value)}" aria-label="${labels[kind]}${label}"><i>m</i></label>`;
    $('#inspector').innerHTML=`<div class="object-card"><span class="object-symbol">${icon(kind==='tile'?'layers':kind==='building'?'building':kind==='transmitter'?'radio':'point')}</span><div><h3>${esc(o.name)}</h3><small>${labels[kind]} <span>·</span> ${esc(o.id)}</small></div></div><div class="property-label">位置 <span>世界坐标</span></div><div class="field-grid">${field('x','X',position[0])}${field('y','Y',position[1])}${kind==='tile'?'':field('z','Z',position[2])}</div>`+
      (kind==='building'?`<div class="property-label">建筑尺寸</div><div class="field-grid">${field('width','宽度',(o as SceneData['buildings'][number]).size[0],0.25)}${field('depth','进深',(o as SceneData['buildings'][number]).size[1],0.25)}${field('height','高度',(o as SceneData['buildings'][number]).size[2],0.25)}</div><div class="material-row"><span>电磁材料</span><b>${esc((o as SceneData['buildings'][number]).material)}</b></div>`:
       kind==='tile'?`<div class="property-label">街区范围</div><div class="tile-size">${(o as SceneData['tiles'][number]).size.map(format).join(' × ')} <span>m</span></div><p class="property-hint">移动街区会同步移动所属建筑。设备位置保持世界坐标。</p>`:'<p class="property-hint">修改设备位置后，需要重新计算信道。</p>');
  }
  function renderScene(fit=false) {
    viewport.setScene(data,fit);viewport.setPath(points(),mode==='planned');viewport.setSelection(selection);
    $('#scene-name').textContent=data.name;
    const b=bounds(data);$('#dimensions').textContent=`${format(b.maxX-b.minX)} × ${format(b.maxY-b.minY)} m`;
    const valid=data.resultsValid&&!!data.trajectory.results;
    $('#result-status').className=`status-badge ${valid?'':'warning'}`;$('#result-status').innerHTML=`<i></i>${valid?'附有仿真结果':'几何草案 · 待仿真'}`;
    $('#scene-count').textContent=`${data.tiles.length} 个街区 / ${data.buildings.length} 栋建筑`;
    $('#resource-summary').textContent=`${data.tiles.length} 个街区 · ${data.buildings.length} 栋建筑 · ${data.receivers.length} 个 UE`;
    $('#seam-status').textContent=seamStatus(data);$('#seam-status').title='仅检查轴对齐矩形地面的相接、重叠与分离，不验证无线传播';
    $('#undo').toggleAttribute('disabled',!history.length);
    const r=data.trajectory.results;
    $('#source-version').textContent=r?`位置样本 · ${r.date}`:'未附带仿真结果';
    $('#current-provenance').textContent=r?`${r.provenance}（${r.date}）${data.resultsValid?'':'；结果已标记为失效。'}`:'此文件没有附带信道或波束结果。';
    $('#radio-config').innerHTML=r?`<div><span>载频</span><b>${r.carrierGHz}<small> GHz</small></b></div><div><span>发射阵列</span><b>${r.txAntennas}<small> 阵元</small></b></div><div><span>频率采样</span><b>${r.subcarriers}<small> 个频点</small></b></div><div><span>接收天线</span><b>1<small> 阵元</small></b></div>`:'<p class="property-hint">未附带无线配置记录</p>';
    $('#notice').innerHTML=valid?`${icon('info')}<span>正在回放已有仿真样本。地图中的设备连线仅作位置示意。</span>`:`${icon('info')}<span>几何或设备已修改，或没有有效仿真结果。当前不显示原波束数据。</span>`;
    $('#notice').className=`notice ${valid?'':'warning'}`;
    const option=$<HTMLOptionElement>('#track-mode option[value="verified"]');option.textContent=`${data.trajectory.results?'仿真位置序列':'导入位置序列'} · ${format(trajectoryLength(data.trajectory.positions))} m`;
    renderTree();renderInspector();updatePosition();
  }
  function updatePosition() {
    const pp=points();index=Math.min(Math.max(index,0),pp.length-1);
    const p=pp[index];viewport.setPosition(p);
    const scrub=$<HTMLInputElement>('#scrubber');scrub.max=String(pp.length-1);scrub.value=String(index);scrub.style.setProperty('--progress',`${pp.length===1?0:index/(pp.length-1)*100}%`);
    $('#sample-index').innerHTML=`<b>${String(index+1).padStart(2,'0')}</b><span> / ${String(pp.length).padStart(2,'0')}</span>`;
    $('#track-count').textContent=`${pp.length} 个位置`;
    $('#position-readout').innerHTML=`<i class="dot teal"></i> UE <span>X <b>${format(p[0])}</b></span><span>Y <b>${format(p[1])}</b></span><span>Z <b>${format(p[2])}</b> m</span>`;
    const r=data.trajectory.results;
    if(mode==='planned' || !data.resultsValid || !r) {
      $('#beam-badge').textContent=mode==='planned'?'几何预览':'待仿真';
      $('#beam-chart').innerHTML=`<div class="chart-empty">${icon('radio')}<b>${mode==='planned'?'这条轨迹尚无信道结果':'等待新的仿真结果'}</b><span>${mode==='planned'?'选择已仿真片段查看波束增益':'需要基于当前几何重新计算'}</span></div>`;return;
    }
    const values=r.beamPowers[index].map(x=>10*Math.log10(Math.max(x,1e-30))),best=r.bestBeams[index];
    const lo=Math.floor(Math.min(...values)/10)*10,hi=Math.ceil(Math.max(...values)/10)*10+5;
    const span=Math.max(10,hi-lo),step=204/values.length;
    $('#beam-badge').textContent=`最优 B${best}`;
    $('#beam-chart').innerHTML=`<svg class="beam-svg" viewBox="0 0 254 140" role="img" aria-label="各波束相对信道增益，最优波束 B${best}">${[0,0.5,1].map(t=>`<line x1="38" y1="${12+t*99}" x2="245" y2="${12+t*99}" stroke="#e9edf1"/><text x="30" y="${15+t*99}" text-anchor="end" class="chart-tick">${Math.round(hi-t*span)}</text>`).join('')}${values.map((v,i)=>{const h=Math.max(2,(v-lo)/span*99);return `<rect x="${40+i*step}" y="${111-h}" width="${Math.max(1,step-7)}" height="${h}" rx="3" fill="${i===best?'#188c78':'#c4d7e3'}"><title>B${i}: ${v.toFixed(2)} dB</title></rect><text x="${40+i*step+(step-7)/2}" y="130" text-anchor="middle" class="chart-tick">${values.length>16?(i%Math.ceil(values.length/8)===0?i:''):`${i}`}</text>`;}).join('')}</svg><div class="best-beam"><span>最佳波束 <b>B${best}</b></span><strong>${values[best].toFixed(2)} <small>dB</small></strong></div>`;
  }

  viewport.onSelect=s=>{selection=s;viewport.setSelection(s);renderTree();renderInspector();};
  $('#scene-tree').addEventListener('click',e=>{const button=(e.target as HTMLElement).closest<HTMLButtonElement>('[data-select]');if(!button)return;const [kind,id]=button.dataset.select!.split(':');selection={kind:kind as NonNullable<Selection>['kind'],id};viewport.setSelection(selection);renderTree();renderInspector();});
  $('#inspector').addEventListener('change',e=>{
    const input=e.target as HTMLInputElement,key=input.dataset.property;if(!key||!selection)return;
    const value=Number(input.value);if(!input.value.trim()||!Number.isFinite(value)||Math.abs(value)>1e6||(['width','depth','height'].includes(key)&&value<0.25)||key==='z'&&value<0) {toast('请输入有效数值；尺寸至少为 0.25 m，高度不能为负。');renderInspector();return;}
    remember();setPlaying(false);
    const o=selectedObject()!;
    if(selection.kind==='tile') {const tile=o as SceneData['tiles'][number],next=[...tile.center] as [number,number];next[key==='x'?0:1]=value;moveTile(data,tile.id,next);}
    else if(['width','depth','height'].includes(key)) {const b=o as SceneData['buildings'][number];if(key==='height')b.position[2]+= (value-b.size[2])/2;b.size[{width:0,depth:1,height:2}[key]!]=value;}
    else (o as {position:Vec3}).position[{x:0,y:1,z:2}[key]!]=value;
    data.resultsValid=false;$('#save-status').textContent='有未导出的修改';renderScene();toast('几何已更新；原仿真结果已停用。');
  });
  document.querySelectorAll<HTMLInputElement>('[data-layer]').forEach(input=>input.addEventListener('change',()=>viewport.setLayer(input.dataset.layer as Parameters<Viewport['setLayer']>[0],input.checked)));
  $('#add-tile').onclick=()=>{if(data.tiles.length>=100){toast('当前原型最多支持 100 个街区。');return;}remember();setPlaying(false);selection={kind:'tile',id:addTile(data)};$('#save-status').textContent='有未导出的修改';renderScene(true);toast('已向东拼接一个街区，需重新仿真。');};
  $('#undo').onclick=()=>{const previous=history.pop();if(!previous)return;data=previous;setPlaying(false);if(!selectedObject())selection=null;renderScene();$('#save-status').textContent='已撤销上一步修改';};
  $('#reset').onclick=()=>{remember();data=structuredClone(baseline);selection={kind:'tile',id:data.tiles[1].id};mode='verified';$<HTMLSelectElement>('#track-mode').value=mode;index=0;setPlaying(false);renderScene(true);$('#save-status').textContent='已恢复内置场景';toast('已恢复内置场景；可撤销此操作。');};
  function view(top:boolean) {viewport.fit(top);$('#top-view').classList.toggle('active',top);$('#perspective').classList.toggle('active',!top);}
  $('#top-view').onclick=()=>view(true);$('#perspective').onclick=()=>view(false);$('#fit').onclick=()=>view(false);
  $('#zoom-in').onclick=()=>viewport.zoom(0.8);$('#zoom-out').onclick=()=>viewport.zoom(1.25);
  $('#screenshot').onclick=()=>{downloadable(viewport.screenshot(),'lcm-scene.png');toast('已导出地图图片（不包含界面标注）。');};
  $('#export').onclick=()=>{downloadable(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}),'lcm-scene.json');$('#save-status').textContent='场景已导出';toast('场景 JSON 已导出。');};
  $('#import').onclick=()=>$<HTMLInputElement>('#file-input').click();
  $('#file-input').addEventListener('change',async e=>{
    const input=e.target as HTMLInputElement,file=input.files?.[0];if(!file)return;
    try {if(file.size>20*1024*1024)throw new Error('场景文件不能超过 20 MB。');const imported=parseScene(JSON.parse(await file.text()));remember();data=imported;selection=null;mode='verified';$<HTMLSelectElement>('#track-mode').value=mode;index=0;setPlaying(false);renderScene(true);$('#save-status').textContent='已导入本地场景';toast('场景已导入；结果来源以文件记录为准。');}catch(error){toast(`导入失败：${error instanceof Error?error.message:'文件无效'}`);}finally{input.value='';}
  });
  $('#track-mode').addEventListener('change',e=>{mode=(e.target as HTMLSelectElement).value as typeof mode;index=0;setPlaying(false);viewport.setPath(points(),mode==='planned');updatePosition();});
  $('#play').onclick=()=>{if(!playing&&index===points().length-1)index=0;setPlaying(!playing);updatePosition();};
  $('#next').onclick=()=>{setPlaying(false);index=(index+1)%points().length;updatePosition();};
  $('#scrubber').addEventListener('input',e=>{setPlaying(false);index=Number((e.target as HTMLInputElement).value);updatePosition();});
  $('#speed').addEventListener('change',e=>{interval=Number((e.target as HTMLSelectElement).value);});
  $('#focus-ue').onclick=()=>viewport.focusPosition(points()[index]);
  const dialog=$<HTMLDialogElement>('#help-dialog');$('#help').onclick=$('#source-info').onclick=()=>dialog.showModal();$('#close-help').onclick=()=>dialog.close();dialog.addEventListener('click',e=>{if(e.target===dialog)dialog.close();});
  document.addEventListener('keydown',e=>{if(e.target instanceof HTMLInputElement||e.target instanceof HTMLSelectElement||dialog.open)return;if(e.code==='Space'){e.preventDefault();$('#play').click();}if(e.key==='Escape'){selection=null;viewport.setSelection(null);renderTree();renderInspector();}});
  function animate(t:number) {if(playing&&t-lastStep>=interval){index++;if(index>=points().length){index=points().length-1;setPlaying(false);}updatePosition();lastStep=t;}requestAnimationFrame(animate);}
  renderScene(true);requestAnimationFrame(animate);
}
start().catch(error=>{app.innerHTML=`<div class="fatal-error"><h1>场景暂时无法打开</h1><p>${esc(error instanceof Error?error.message:String(error))}</p><p>请使用支持 WebGL 的浏览器，并通过本地开发服务器打开。</p><button class="button primary" onclick="location.reload()">重新加载</button></div>`;console.error(error);});
