# LCM 四场景工作台

日期：2026-10-26。Python 管理本地场景、校验与导出，Three.js 提供浏览器三维交互。三个城市场景是 DeepMIMO 官方预览建筑素材的合成重组，不是完整真实城市复原；本工具不代表 LCMAgent 运行时。

## 一个入口

从仓库根目录运行（也可使用 run.py 的绝对路径从任意目录运行）：

```sh
python3 scene-studio/run.py serve
```

打开 **http://127.0.0.1:8766/**。首次构建或修改前端后：

```sh
npm install --prefix scene-studio/web
python3 scene-studio/run.py build
python3 scene-studio/run.py serve --port 8766
```

`serve` 仅需 Python 标准库，不启动 Node/Vite，不下载数据，不重新布局，不计算信道。前端构建需要 Node.js 和 npm（版本要求见[前端依赖](web/package.json)）。默认只监听本机。

## Conda 环境

本机已创建 `lcm` 环境，Python 3.11，项目按可编辑方式安装；包含几何依赖、Sionna RT 2.2.0 和 Playwright。激活后使用 `python`，避免误用系统 Python 3.9：

```sh
conda activate lcm
python scene-studio/run.py test
python scene-studio/run.py serve --port 8768
```

端口已占用时可直接打开已有服务，或换端口；创建环境不会解除端口占用。前端构建依然使用本机 Node.js/npm，不需要在 conda 内重复安装。

新机器可在本目录使用[环境定义](environment.yml)创建；或从仓库根运行：

```sh
conda create -n lcm python=3.11 pip -y
conda activate lcm
python -m pip install -e './scene-studio[rt]' playwright
```

不为查看网页安装完整 TensorFlow/Sionna PHY 或下载 DeepMIMO 信道包；RT 扩展仅用于已有小规模核验及后续开发。

## 四种场景

| 场景 | 实例数 | 独立源资产 | 当前数据状态 |
|---|---:|---:|---|
| 四建筑接缝测试，80×50 m | 4 | 4 | 小规模真实RT/CSI及波束摘要 |
| 一公里，1×1 km | 665 | 435 | 默认环境增强：平地分区、5源植被体＋155合成树；可切换正式基线；未重算信道 |
| 两公里，2×2 km | 2,306 | 890 | 环境增强：7源植被体＋827合成树；可切换正式基线；未重算信道 |
| 四公里，4×4 km | 13,838 | 1,317 | 环境增强：7源植被体＋2,893合成树；可切换正式基线；未重算信道 |

三个城市现在默认加载正式下载几何匹配版本，保留原预览快照和完全相同的布局。每个资产保存正式三维面、源对象ID及面材料键；每个实例位置、旋转保持不变。地面为合成平地，不引入源地形或TX/RX/信道。源材料参数已关联，但尚未转换并验证为RT后端材质；显示颜色仅作示意。详情见[正式资源整合说明](OFFICIAL_INTEGRATION.md)。

三种城市均有[环境增强版](ENVIRONMENT_CITIES.md)，[一公里详细说明](ENVIRONMENT_1KM.md)保留。36个下载terrain均为Z=0，没有凭空生成源坡地；增加地表分区及明确来源/合成标记的植被，RT禁用以待正确的植被传播适配。15项单元测试覆盖三尺度环境，三城市环境/基线切换与PNG下载均通过。

```sh
conda activate lcm
python scene-studio/run.py enhance-environment --size 1000
python scene-studio/run.py enhance-environment --size 2000
python scene-studio/run.py enhance-environment --size 4000
python scene-studio/run.py build
```

## 操作

- 左侧切换四种场景；左键拖动旋转、滚轮缩放、右键拖动平移。
- 三维透视／正交俯视切换，适配全景，点击建筑查看来源、高度、位置、旋转与地块，聚焦选中对象。
- 图层控制建筑、道路、公园、地块边界、参考网格和片区标签；建筑可按高度着色。
- 保存三维画布 PNG；图片不含界面控件。
- 四建筑场景展示原有采样位置回放与真实波束摘要；完整编辑功能保留在[原编辑器入口](web/editor.html)。原DeepMIMO选型页保留在[辅助入口](web/deepmimo.html)。

## 目录职责

- [统一Python入口](run.py)：serve、prepare、build、validate、test，以及显式生成与RT核验。
- [Python工具](python/lcm_scene/)：城市布局、资产读取、导出、来源审计和四建筑验证。旧数据目录中只留轻量兼容脚本，不维护重复实现。
- [网页源码](web/src/)：统一三维工作台与保留的辅助页面。
- [来源与城市数据](data/deepmimo-scenes/)：原始缓存、分类结果、城市快照和图像。
- [四建筑测试数据](data/scenes/test-4buildings/)：原始CSI、运行记录、核验说明。
- [迁移快照校验](generated/reports/migration-snapshots.json)：场景、图像和原测试结果的SHA256基线。
- [浏览器派生数据](web/public/scenes/catalog.json)：四场景目录；城市JSON由[快照导出工具](prepare_viewer.py)从保存的压缩场景导出。

旧 `tools/scene-studio`、`output/deepmimo-scenes` 和 `output/verification/map-stitching` 为指向新目录的兼容链接，不再是第二套实体数据。其他研究文档和无关输出未迁移。原说明中的历史旧路径可通过兼容链接继续访问。

## 校验与显式生成

几何依赖按需使用uv，不影响纯Python网页服务：

```sh
uv run --with numpy --with scipy --with pillow --with shapely python scene-studio/run.py test
uv run --with numpy --with scipy --with pillow --with shapely python scene-studio/run.py validate
python3 scene-studio/run.py prepare
```

以下命令会更新数据，应仅在确实需要时执行：

```sh
uv run --with numpy --with scipy --with pillow --with shapely python scene-studio/run.py generate --size 1000
# --size 2000 或 4000；不会自动重算信道。
uv run --python 3.11 --with 'sionna-rt==2.2.0' python scene-studio/run.py verify-test
```

四公里历史快照和当前缓存资产读取结果可能存在差异；迁移保留的是原快照，并未重新生成四公里布局。源预览缓存来自2026-10-25采集记录，来源条款仍适用，完整再分发许可审查未完成。

## 一公里信道试算（2026-10-26）

已在完整665个建筑实例上完成1个TX、32个RX的真实Sionna RT稀疏试算。3.5GHz、8×1阵列、64频点、LOS与最多2次镜面反射；100万射线样本预算找到60条有效路径，16个RX有非零CSI，另16个没有找到路径。材料是假设混凝土，不是源材料；尚未认证传播收敛。独立结果未自动接入网页，网页的城市卡片仍表示原几何数据状态。

见[试算说明与数据](generated/rt/city-1km-trial-final/README.md)。包括最终NPZ、逐RX CSV、采样图和配置记录。新增测试后当前Python测试总数为9项。

```sh
conda activate lcm
python scene-studio/run.py trial-city --output scene-studio/generated/rt/my-city-trial
```

## 城市正式几何下载（默认四公里）

脚本只下载对象、顶点、材料/参数，不提供完整信道包下载。默认按4×4km的36来源；支持--size 1000/2000/4000。四公里已有30来源实测解压6.11MB，新增6来源受远端传输异常影响尚未核实，整体规划估算约8–15MB，不能称为精确总量。见[四公里下载说明](DOWNLOAD_CITY_4KM.md)及[一公里实测说明](DOWNLOAD_CITY_1KM.md)。

```sh
conda activate lcm
python scene-studio/run.py download-city
python scene-studio/run.py download-city --download
```

官网传输错误或403/429会安全停止，不绕过限额。目录探测成功不等于下载完成，实际状态见下载计划。本次下载单元测试4项通过，与原9项合计13项。

## 边界

- 浏览器三维展示不等于RT网格、电磁材料或城市信道已验证。
- 城市已有二维重叠/越界检查；尚未验证道路连通、建筑入口、三维水密性与传播收敛。
- 四建筑结果的真实测试范围见[核验说明](data/scenes/test-4buildings/README.md)。不将它扩展宣称为城市级信道验证。
- 旋转、缩放仅改变相机；不会改变原场景几何。原编辑器中的修改会使已有波束结果失效。
- Three.js、Sionna RT及Python依赖为第三方工具，保留原许可与来源。

迁移和浏览器验收实际结果见[验证记录](generated/reports/validation.md)。TypeScript/Vite 构建、7 项 Python 测试和四场景 Chrome 交互复验均已通过，原场景与测试结果的 21 个快照校验和保持不变。当前会话查看地址为 **http://127.0.0.1:8767/**；以后可按上方命令自行启动。

浏览器验收可复现：

```sh
uv run --with playwright python scene-studio/tests/browser_check.py --url http://127.0.0.1:8767
```

需本机安装 Chrome；脚本会保存截图和下载证据到 `generated/browser/`，但不生成或修改城市几何与信道。
