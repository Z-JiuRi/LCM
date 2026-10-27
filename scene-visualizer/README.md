# LCM 场景可视化工作台

更新：2026-10-27。Python 管理本地场景与导出，Three.js 提供四场景浏览和保留的编辑器。城市是 DeepMIMO 官方建筑素材的合成重组，不是真实城市完整复原，也不是 LCMAgent 运行时。

## 启动与准备

在仓库根目录运行已构建页面：

```sh
python3 scene-visualizer/run.py serve --port 8767
```

打开 **http://127.0.0.1:8767/**。`serve` 只需 Python 标准库，默认仅监听本机；不下载、不重新布局、不生成 UE 或信道。端口已占用时使用已有服务或显式换端口。

首次安装、修改前端或需要重新导出时：

```sh
# Python 3.11+；已有合适环境可直接安装，不必重复创建
python3 -m venv scene-visualizer/.venv
source scene-visualizer/.venv/bin/activate
python -m pip install -e ./scene-visualizer
npm install --prefix scene-visualizer/web
# 仅在 UE 网格缺失、环境几何变化或需重新生成时运行
python scene-visualizer/prepare_ue.py
python scene-visualizer/run.py build
python scene-visualizer/run.py serve --port 8767
```

前端需要 Node.js（Vite 要求 20.19+ 或 22.12+）和 npm，版本见[依赖清单](<web/package.json>)。也可使用[Conda 环境定义](<environment.yml>)；日常查看/几何导出不需要 Sionna、TensorFlow 或源信道包。可选 RT 依赖仅供独立小规模核验，配置见[Python 项目定义](<pyproject.toml>)，不属于当前操作流程。

## 当前数据

| 场景 | 建筑实例 / 独立资产 | BS / 扇区 | 5 m UE 候选点 |
|---|---:|---:|---:|
| 四建筑接缝测试，80×50 m | 4 / 4 | 原核验 1 TX | 原静态/移动采样，不是城市网格 |
| 1×1 km | 665 / 435 | 6 / 18 | 29,726 |
| 2×2 km | 2,306 / 890 | 23 / 69 | 114,688 |
| 4×4 km | 13,838 / 1,317 | 72 / 216 | 449,988 |

城市默认为环境增强＋需求驱动 BS 规划，可切换正式建筑基线。36 个源 terrain 都是 Z=0；地表分区、合成树和布局是项目设计，源植被体另有来源标记。正式几何和面材料已关联，但植被 RT 禁用，电磁材料适配与传播验证未完成。

BS 是 500 m 参考尺度、合成需求驱动的非均匀规划，不是运营商部署或 RF 覆盖/容量认证；350 m 距离与 600 Mbps 单站预算只是规划代理，建筑需求 35%/65% 室外/室内拆分未经验证。详见[BS 部署规则与证据](<BS_DEPLOYMENT.md>)。

UE 是高度 1.5 m、建筑净距 2 m、植被净距 1 m 的 **5 m 候选测量网格**，不是实际人口、轨迹、服务扇区指派或已计算 CSI。计数依据：[1 km 清单](<data/scenes/ue-candidates/city-1km/manifest.json>)、[2 km 清单](<data/scenes/ue-candidates/city-2km/manifest.json>)、[4 km 清单](<data/scenes/ue-candidates/city-4km/manifest.json>)。当前城市流程没有重算 RT/CSI；四建筑结果和历史一公里稀疏试算不能推广为当前三城验证。

## 数据生成与核心工具

- [UE 生成器](<prepare_ue.py>)：默认生成三城 5 m 候选网格；调用[共享几何工具](<../scripts/city_geometry.py>)，保存 NPY、清单及浏览器 float32 XYZ 数据，不运行 RT。
- [查看器导出器](<prepare_viewer.py>)：从保存的场景导出浏览器数据，读取 UE 清单并检查环境源哈希；不重新布置建筑，也不会自动生成 UE。`run.py prepare` 等价于运行此导出器；`run.py build` 先导出，再执行前端构建。
- [统一命令入口](<run.py>)与[Python 核心工具](<python/lcm_scene/>)：下载、正式资源整合、环境增强、BS 部署、校验和显式生成；修改几何的命令不是查看页面的前置步骤。
- [网页源码](<web/src/>)与[编辑器说明](<web/README.md>)：相机、图层、点选、PNG 导出和 JSON v1 约定。原[编辑器](<web/editor.html>)及[DeepMIMO 选型页](<web/deepmimo.html>)保留。

环境变化后，应按需要重新部署 BS、生成 UE，再导出/构建，避免旧派生数据。只更新浏览器 JSON 可运行：

```sh
python scene-visualizer/prepare_viewer.py
# 或 python scene-visualizer/run.py prepare
python scene-visualizer/run.py test
python scene-visualizer/run.py validate
```

2026-10-27 本轮已完成三城 UE 网格生成、前端构建、19 项查看器测试和14 项 CSI 合成测试；浏览器复验三城点数/坐标、图层切换、相机、基线切换及 BS 点选通过，无页面错误。没有运行新 RT。见[清理与验证记录](<generated/reports/ue-display-cleanup.json>)、[UE 浏览器记录](<generated/browser/ue/acceptance.json>)。

## 来源、历史与边界

- [城市下载指南](<DOWNLOAD_CITY.md>)：当前 36 来源、108 文件、7,073,019 字节的实测整合记录，以及早期 30 来源统计、探测失败和传输/额度 caveat。
- [正式资源整合](<OFFICIAL_INTEGRATION.md>)与[三尺度环境说明](<ENVIRONMENT_CITIES.md>)：源对象匹配、材料、合成地表/植被及历史几何检查。
- [原城市设计与来源](<data/deepmimo-scenes/city-design/README.md>)、[尺度变体](<data/deepmimo-scenes/city-design/VARIANTS.md>)：保留来源与设计历史；四公里旧快照与当前缓存重新生成结果可能不同，不应默默覆盖。
- [四建筑核验](<data/scenes/test-4buildings/README.md>)与[历史一公里最终 RT 试算](<generated/rt/city-1km-trial-final/README.md>)：后者是 665 建筑、1 TX/32 RX、假设混凝土下的稀疏试算，不是当前正式材料/环境/BS/UE 网格的信道；未认证传播收敛。
- [迁移校验基线](<generated/reports/migration-snapshots.json>)与[历史验收记录](<generated/reports/validation.md>)：保留原快照和测试证据；历史路径/端口/测试数量不作为当前状态承诺，当前命令以本页为准。

二维重叠/越界检查不证明三维水密性、道路连通或传播正确性。相机旋转/缩放不改变物理几何；编辑器修改几何或设备会使旧波束结果失效。DeepMIMO 源数据、Three.js、Sionna RT 和其他第三方依赖的来源/许可仍适用，完整数据再分发许可审查尚未完成，不将其描述为项目原创资产或已获无限制授权。
