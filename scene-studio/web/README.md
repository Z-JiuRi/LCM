# LCM Scene Studio

日期：2026-10-25。状态：可运行的地图可视化与编辑原型；尚未连接在线射线追踪、CSI 数据生成或 LCMAgent 决策系统。

使用 Three.js、TypeScript 和 Vite。仓库没有现成前端框架，因此采用独立的浏览器应用，直接读取上一轮核验生成的几何和波束样本。

## 启动

在本目录运行：

```bash
npm install
npm run dev
```

默认地址为 `http://127.0.0.1:5173`。需要 Node.js 20.19+ 或 22.12+；本次使用 Node.js 24.14.1。

```bash
npm run build
npm run preview
```

应用不需要后端服务、API 密钥或外部字体服务；开发依赖首次安装需要网络。导入文件在浏览器内读取，不上传。修改保留在当前页面内存中，离开页面前请导出 JSON。

## 统一四场景首页（2026-10-26）

- `/` 为统一只读浏览器，读取 `/scenes/catalog.json`：四建筑核验、1 km / 665 建筑实例、2 km / 2,306 建筑实例、4 km / 13,838 建筑实例。
- `/editor.html` 保留原完整编辑器及 Scene Studio JSON v1 导入导出；`/deepmimo.html` 保留原独立 DeepMIMO 选型页。生产构建为三个 HTML 入口。
- 城市数据读取解压后的 assembled-city JSON；建筑源多边形按主平面投影三角化，每个资产只创建一次几何，再以 `InstancedMesh` 共享，不用方盒或俯视纹理替代。实例保留原始米制位置及 Z 轴旋转，内部映射为 `[x,z,-y]`。
- 首页支持鼠标旋转 / 滚轮缩放 / 右键平移、透视 / 正交俯视、适配、建筑实例或核验设备选择、聚焦、PNG 截图、建筑 / 道路 / 带孔洞公园 / 地块 / 合并建筑边界 / 网格 / 标签图层、五档蓝灰建筑高度色。PNG 只包含 WebGL 画布，不含 HTML 标签。
- 四建筑测试保留原 1 个 TX、8 个静态 RX、9 个移动采样位置及真实波束摘要。城市没有信道、TX / RX 或轨迹，不生成替代数据；其道路、公园、地块和布局是可视化合成设计，不是电磁材料配置，微小图层显示偏移不是物理几何。
- 大场景按资产组织实例，建筑边界合并为线段；最多创建 80 个场景标签 DOM，不为上万建筑生成标签。切换释放几何、材质和实例缓冲，取消过期请求，视口按需渲染并保留鼠标阻尼。
- 浏览器只读诊断可通过 `window.__LCM_SCENE_DIAGNOSTICS__` 查看当前场景、相机模式、资产 mesh 数、实例数、三角形数、标签数及渲染资源统计。该接口不修改场景。

本轮前端验证：`npm run build` 的 TypeScript 检查与三入口 Vite 构建通过。浏览器交互和性能需要另行按具体环境记录，不把构建通过视为城市级性能已经验证。

## 原编辑器已实现

- 透视与俯视、旋转/缩放/平移、适配场景、聚焦移动 UE、地图图片导出。
- 建筑、静态 UE、移动轨迹、网格、标签和设备示意连线的图层控制。
- 点击场景或资源列表选择对象；编辑街区位置、建筑中心/尺寸及收发设备位置。
- 复制末尾街区并向东拼接，建筑随所属街区移动；最多保留 30 步撤销。
- 轴对齐矩形地面的相接、重叠、分离检查。该检查不证明道路或无线传播连续性。
- 已仿真位置序列逐点回放、进度拖动、倍速显示、步进；另有无信道结果的全街区几何预览轨迹。
- 真实波束样本的宽带平均增益和最佳波束展示。
- JSON 导入、格式检查和完整往返导出；错误文件不替换当前场景。
- 几何或设备发生修改后，将已有结果标记为失效并停止展示；撤销到原始几何时恢复相应状态。

导出的 PNG 包含三维画布，不包含 HTML 标签或界面控件。

## 数据来源和边界

内置地图对应 [地图合并最小核验](../../output/verification/map-stitching/README.md)：两个 $40\times50\,\mathrm{m}$ 的场景、四栋建筑、一个基站、八个静态 UE 位置，以及跨越 $x=0$ 接缝的九个移动位置。

浏览器内置的 [verified-street.json](public/scenes/verified-street.json) 由 [export_verified.py](scripts/export_verified.py) 读取真实 `samples.npz` 生成，保留原波束增益与索引；没有用前端随机数模拟测量结果。建筑几何和无线配置与核验脚本一致。

从仓库根目录重新生成该 JSON：

```bash
uv run --with numpy python tools/scene-studio/scripts/export_verified.py
```

- 原始复数 CSI 仍保留在核验目录的 NPZ；浏览器 JSON 仅包含地图、设备、轨迹和波束摘要。
- 内置波束指标为 $10\log_{10}G_b$，其中 $G_b$ 是归一化 DFT 波束下的宽带平均信道增益；不能解释为以 dBm 标定的接收功率。
- 轨迹回放速度是界面速度，未指定用户真实运动速度或帧间物理时间；插入长轨迹预览不会生成对应 CSI。
- 立面条纹、屋顶饰面、道路色块、点标记和示意连线只为可读性服务，不属于额外的电磁几何或传播路径。
- 这里没有运行浏览器端射线追踪；任何几何修改都需要在 Sionna RT 等工具中重新计算。
- 尚未实现直接导入 Sionna XML、OBJ/PLY、GLB 或 DeepMIMO 场景包，也没有验证城市级模型的渲染性能。
- 导入文件中的来源和 `resultsValid` 由文件提供；它们不是经过应用独立验证的真实性证明。

## 场景 JSON v1

完整可导入示例见内置 JSON，TypeScript 定义和校验见 [model.ts](src/model.ts)。所有坐标均为米，$z$ 轴向上；浏览器内部统一映射为 Three.js 的 $y$ 轴向上，不修改导出的坐标。

| 字段 | 含义 |
| --- | --- |
| `schemaVersion`, `units`, `coordinateSystem` | 固定为 `1`、`m`、`z-up` |
| `tiles[]` | 街区 ID、名称、地面中心 `[x,y]`、范围 `[width,depth]`、显示色 |
| `buildings[]` | 建筑 ID、所属街区、中心 `[x,y,z]`、尺寸 `[width,depth,height]`、材料名称 |
| `transmitters[]`, `receivers[]` | 收发设备 ID、名称和世界坐标 |
| `trajectory.positions[]` | 按顺序排列的 UE 坐标；没有隐含时间间隔 |
| `trajectory.kind` | 固定为 `sampled-positions` |
| `trajectory.results` | 可为 `null`；否则包含来源、日期、无线配置、每位置波束增益和最佳索引 |
| `resultsValid` | 结果是否仍适用于当前场景；编辑动作会设为 `false` |

JSON v1 的无线摘要沿用当前核验的单接收天线配置，不包括天线完整方向图、极化、OFDM 和射线追踪参数；不是可直接运行的 Sionna 配置文件。后续后端适配器还需补齐这些参数和材料定义。

## 验证记录

2026-10-25 已完成：

- TypeScript 检查和 Vite 生产构建。
- 实际浏览器检查：修改建筑高度停用旧结果、撤销恢复、追加街区、切换预览/仿真轨迹、位置步进和播放。
- 实际文件下载后重新导入，几何与波束结果恢复；无效 JSON 导入不破坏当前场景。
- 数据检查：街区平移和复制、接缝检查、重复 ID/负尺寸/无效波束拒绝、JSON 往返一致性。
- 桌面及 390 px 小屏幕布局检查。

Three.js（MIT）和其他依赖均为第三方组件，具体版本固定在 `package.json` 和 `package-lock.json` 中；本工具不将它们描述为 LCMAgent 原创渲染器。

## DeepMIMO 场景选型展示

2026-10-25 新增独立只读页面：开发服务器的 `/deepmimo.html`。它直接渲染官方多边形面片，展示 ASU 校园、动态 ASU 的三个原始快照、Boston 和上海片区。原编辑器的 JSON v1 导入能力不变；面片数据不作为盒状建筑导入。

选型依据、原始来源、动态快照核验和未完成事项见[DeepMIMO 场景选型](../../docs/分析文档/LCMAgent/DeepMIMO场景选型.md)。原始来源位于 `output/deepmimo-scenes/source/`，派生的本地展示数据位于 `public/scenes/deepmimo/`。不使用远程图片或伪造信道指标。

```bash
# 从仓库根目录运行；抓取受官网可用性和限流影响，可复用已有缓存。
uv run --with numpy python tools/scene-studio/scripts/fetch_deepmimo_geometry.py
uv run --with numpy python tools/scene-studio/scripts/export_deepmimo_gallery.py
npm run build --prefix tools/scene-studio
```

本次 O1/O1B 下载受到 HTTP 429 限流，保留建议但不显示替代几何。动态 ASU 只抽取第 1、51、100 个快照；三者的建筑和 RX 抽样坐标相同，一个 TX 移动。未验证完整时序、物理帧间隔或模型性能。

本次展示页验证：TypeScript 检查与 Vite 双入口构建通过；实际浏览器检查了四个场景渲染、动态快照切换与俯视，未见控制台错误。界面截图保存在 `output/deepmimo-scenes/scene-studio.jpg`。浏览器自动化等待 PNG 下载事件超时，本次未确认“保存图片”的文件落盘；不将该项记为通过。
