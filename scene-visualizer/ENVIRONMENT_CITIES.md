# 三尺度环境增强版本

更新：2026-10-27；环境生成与历史验证：2026-10-26。统一一公里初版及后续两公里/四公里扩展说明。保持正式建筑基线、建筑 XYZ/旋转/尺寸、道路、公园和地块布局不变，没有新 RT 或 CSI。

| 地图 | 建筑实例 | 地表三角 | 源 Boston 植被体保留 | 源植被排除 | 合成树 |
|---|---:|---:|---:|---:|---:|
| 1×1 km | 665 | 2,973 | 5 | 14 | 155 |
| 2×2 km | 2,306 | 16,154 | 7 | 12 | 827 |
| 4×4 km | 13,838 | 22,379 | 7 | 12 | 2,893 |

## 源资源审计与共用规则

- 对仓库根 data 中 36 个下载场景的对象和顶点核查：36 个 terrain 高程均为 Z=0，**没有起伏地形资源**。采用连续平地，不叠加 36 个共面源地面，不为展示效果虚构源坡地。
- 地表分道路、公园和其他地表，三角投影覆盖完整城市面积，分区无面积重叠。道路关联源 Taito 的 Asphalt_1GHz 数值，公园/其他地表关联 ITU Wet earth 3.5GHz 数值；这是新布局设计分配，不是新城实测材料，频率适配待验证。
- 只有 Boston 提供 19 个 vegetation 标签对象，均为高 25 m 的简化体积，所有源面引用 `material_0`（ITU Concrete）。它们不是 19 棵真实单株树或完整树冠电磁模型；不能套用混凝土就宣称考虑了植被衰减。
- 源植被按各城市 Boston 保留组团的旋转/平移变换、不缩放，并检查建筑、道路、边界和植被冲突。1 km 保留 5 个、2/4 km 各保留 7 个，其余逐对象记录排除原因。
- 合成公园/绿廊种植标记 `synthetic-design`，使用高 7/10/12 m 的三种共享资产、18 m 格点及确定性抖动；种子为 1 km `261026103`、2 km `261026104`、4 km `261026106`。各城市独立布置，不缩放一公里树阵。
- 植被底部 Z=0，树冠避让建筑、道路、绿廊路径和其他植被。合成格点最小间距约 12 m，大于最大树冠直径 8 m 加 1 m 间隔；源植被另做相交检查。

## 一公里初版与验证历史

一公里初版只新增环境版本，当时 2/4 km 未修改；之后才扩展三尺度，这不是当前仍只支持一公里的限制。665 个建筑及原布局保持不变。连续地表 2,973 三角，三角投影总面积和并集面积均为 1,000,000 m²，重叠/未覆盖面积约为 0（浮点误差级）。

Boston 源植被随保留组团旋转 −12°并平移，5 个通过建筑/道路避让，14 个冲突排除；另加 155 个合成树，合计 160 个植被实例。建筑与正式基线 assets/instances 逐项一致，植被/树冠侵入建筑和道路均为 0。

历史证据：

- [一公里测试日志](<generated/reports/environment-tests.log>)：当时 15 项通过，覆盖地表、材料、植被和快照。
- [一公里浏览器记录](<generated/browser/environment/acceptance.json>)：显示 2,973 地表三角/160 植被实例，切到基线为 0，再切回为 160；当时 2/4 km 建筑数不变，PNG 下载通过、pageerror 为 0。
- [一公里三维截图](<generated/browser/environment/enhanced-3d.png>)、[俯视截图](<generated/browser/environment/enhanced-top.png>)。
- [三尺度测试日志](<generated/reports/environment-all-tests.log>)：扩展后仍记录 15 项通过，覆盖三尺度面积、平地、材料引用、基线资产/实例一致性；当时生产构建通过。
- [三尺度浏览器验收](<generated/browser/all-environments/acceptance.json>)：三城版本切换和展示记录。

这些是保存的历史验证，不是本次文档整理重新运行的测试结果。

## 电磁边界

全部植被 `rt_enabled=false`。源简化体保留混凝土绑定仅供来源核查；合成树不捏造 εr/σ，记录 `Foliage model pending`。它们目前只进入几何/信息层，不是已应用的植被传播模型。旧一公里 RT 试算采用原基线，不能声称包含本次地表分区或植被。

增强版不等于起伏山坡，也不是源环境无损复原。若需起伏实验，应明确生成合成地形或引入真实 DEM 并设计建筑台地。下一步需选择/验证地表和植被电磁适配，再以相同 TX/RX 做基线对照 RT。

## 数据与复现

- [一公里环境版](<data/scenes/environment-cities/city-1km/assembled-city.scene.json.gz>)、[报告](<data/scenes/environment-cities/city-1km/environment-report.json>)。
- [两公里环境版](<data/scenes/environment-cities/city-2km/assembled-city.scene.json.gz>)、[报告](<data/scenes/environment-cities/city-2km/environment-report.json>)。
- [四公里环境版](<data/scenes/environment-cities/city-4km/assembled-city.scene.json.gz>)、[报告](<data/scenes/environment-cities/city-4km/environment-report.json>)。
- [正式建筑基线](<data/scenes/official-cities/>)与[构建工具](<python/lcm_scene/city/enhance_environment.py>)。

每份报告/场景包含地表顶点、三角、材质键、分类、共享植被资产/实例、源高程范围、文件哈希、排除原因、种植数量和 QA。只覆盖所选尺度的环境生成结果，不覆盖正式基线、原预览快照或其他城市。源许可仍适用，合成模型/材质分配与源记录须分开。

三城当前默认入口还包括后续 [BS 规划](<BS_DEPLOYMENT.md>)，可切换正式建筑基线；地表/道路/公园/源与合成植被可分开控制，中键/右键平移保留。以下是显式更新数据的复现命令，不是查看页面的必需步骤：

```sh
python scene-visualizer/run.py enhance-environment --downloads ./data --size 1000
python scene-visualizer/run.py enhance-environment --downloads ./data --size 2000
python scene-visualizer/run.py enhance-environment --downloads ./data --size 4000
# 环境变更后刷新依赖它的 BS 与 UE 派生数据
python scene-visualizer/run.py deploy-bs
python scene-visualizer/prepare_ue.py
python scene-visualizer/run.py build
python scene-visualizer/run.py test
python scene-visualizer/run.py serve --port 8767
```

通用安装与导出流程见[工作台首页说明](<README.md>)。以上环境、BS、UE 和构建流程不执行 RT。
