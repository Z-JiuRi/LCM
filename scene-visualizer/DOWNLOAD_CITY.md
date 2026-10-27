# 城市 DeepMIMO 几何下载

更新：2026-10-27；统计与整合记录日期：2026-10-26。统一说明 1/2/4 km 城市使用的正式几何。脚本默认 `--size 4000`，只选择实际使用来源的对象、顶点、参数以及独立材料/许可文件（若存在），不提供完整 ZIP 或 `--full` 下载模式。

## 当前实测与历史统计

**后续正式整合已读取本仓库根 data 下的 36 个下载来源，共 108 个几何/参数文件、7,073,019 字节（约 7.073 MB）。**依据为[整合总表](<data/scenes/official-cities/integration-summary.json>)和[正式资源整合说明](<OFFICIAL_INTEGRATION.md>)。这是真实文件逻辑大小，不是网络传输量或磁盘分配大小，也不代表历史下载计划的每个条目已被同步为完成状态。

| 城市 | 实际来源 | 匹配资产 / 建筑实例 |
|---|---:|---:|
| 1×1 km | 30 | 435 / 665 |
| 2×2 km | 32 | 890 / 2,306 |
| 4×4 km | 36 | 1,317 / 13,838 |

### 早期 30 来源目录实测

一公里曾逐一取得 30 个官方 ZIP 目录，选中 90 个文件：每来源各一份对象、参数、顶点，顶点格式为 25 个 MAT、5 个 NPZ。

| 内容 | 实测逻辑字节数 | 十进制大小 |
|---|---:|---:|
| 30 个完整 ZIP（含源路径数据，仅作对照） | 1,027,407,069 | 1.027 GB |
| 所选几何/参数 ZIP 压缩成员合计 | 660,548 | 0.661 MB |
| 所选文件解压后合计 | 6,112,454 | 6.112 MB |

依据：[一公里历史下载计划](<data/deepmimo-scenes/source/city-1km-official/download-plan.json>)、[目录探测日志](<generated/reports/city-1km-download-probe.log>)。当时建议预留 20–50 MB；简单 665 建筑 OBJ 约 0.38 MB，不代表正式精细网格或后续 RT 输出大小。

四公里包含上述 30 来源，另加 `asu_campus_3p5`、`city_19_oklahoma_3p5`、`city_32_sydney_3p5`、`city_4_phoenix_3p5`、`city_5_philadelphia_3p5`、`city_90_nanjing_3p5`。早期新增 6 来源在重定向处遭遇 TLS EOF/非 ZIP 内容，脚本安全停止；当时完整 36 来源大小尚未知。曾按均值外推压缩约 0.793 MB、解压约 7.335 MB，保守规划压缩 1–2 MB、解压 8–15 MB。**这些只是历史估算，不是新增来源实测上限，也不是当前仍缺 6 来源的状态。**后续本地整合记录已给出上方最终实测大小。

保留证据：[四公里历史下载计划](<data/deepmimo-scenes/source/city-4km-official/download-plan.json>)、[探测日志](<generated/reports/city-4km-download-probe.log>)、[新增来源探测日志](<generated/reports/city-4km-extra-probe.log>)。早期仅探测阶段及成员下载失败不能写成“下载全部成功”；当时 4 项下载单元测试与原有 9 项测试通过，也是历史测试记录，不是本次重新运行结果。

## 使用

在仓库根目录运行；[下载工具](<python/lcm_scene/sources/download_city_geometry.py>)仅需 Python 3.11 标准库，不需 DeepMIMO 包：

```sh
# 离线报告，默认四公里；不发网络请求
python scene-visualizer/run.py download-city
# 探测官方 ZIP 目录，可能消耗授权额度
python scene-visualizer/run.py download-city --size 4000 --probe
# 下载所选几何/参数，跳过已有且校验通过的文件
python scene-visualizer/run.py download-city --size 4000 --download
# 单来源测试
python scene-visualizer/run.py download-city --size 4000 --download --only asu_campus_3p5
python scene-visualizer/run.py download-city --size 1000 --download --only boston5g_3p5
# 一公里、两公里使用各自清单
python scene-visualizer/run.py download-city --size 1000 --download
python scene-visualizer/run.py download-city --size 2000 --download
```

也可直接调用工具：

```sh
python scene-visualizer/python/lcm_scene/sources/download_city_geometry.py --size 1000 --download
```

**当前默认输出为相对运行目录的 `./data`**，从仓库根执行即根 data；不是早期指南的内部历史计划目录。每来源一个子目录，下载计划记录大小、状态及哈希。`--output` 可指定其他位置；换目录后需要重新取得目录信息。`--include-positions` 可额外取源 TX/RX（默认不取，大小需重新统计），这些坐标不能直接作为重组城市部署；`--max-scene-mib` 默认 512，用于拒绝意外大文件。

## 传输、存储与安全

- 脚本用 HTTP Range 和 Python zipfile，支持 ZIP64/CRC；未正确返回 206/Content-Range 时拒绝，不退化为完整包下载。
- 只解压白名单文件，不保存完整 ZIP，不取 power/phase/delay/AoA/AoD/inter/channel。缺少原 RT 工程时不能声称取得完整源工程。
- 每完成文件保存 SHA256；续跑核验后跳过，不覆盖已有但未获脚本验证的正式文件。未完成的 `.partial` 成员从头读取，不是压缩流字节级续传。
- 403/429、TLS、传输或 ZIP 异常停止并记录原因（退出码 2）；网络/额度恢复后再运行，不轮换身份、不绕过限额、不关闭 TLS。源名字和重音字符会 URL 编码，拒绝路径穿越。
- ZIP 尾目录、局部文件头和 64 KiB 块预读增加网络流量；压缩成员之和不是严格传输量，通常为数 MB 量级。网站还可能按完整包大小扣授权额度，不能用选择性传输量代替官方额度规则。
- 建议预留 50–100 MB 供几何、元数据和简单网格处理；OBJ/PLY 转换、材质处理、密集 RT/CSI 输出另计。统计对应当时官方版本，后续版本可能变化。

## 来源与传播边界

源信道对应原布局和 TX/RX，不能拼接用于重组城市。原预览几何已能在假设材料下做小规模试算，正式下载不是该历史试算的必要前置；它用于补全来源几何与材料元数据。

下载不会自动替换场景。正式对象 ID 与预览索引需几何匹配，网格闭合/法线与电磁参数/频率响应需另行检查；并非每包都有独立材料文件或完整电磁参数。当前匹配结果见[正式整合说明](<OFFICIAL_INTEGRATION.md>)。下载/匹配完成不等于材料适配、RT 收敛、完整源工程或许可审查完成，源许可与再分发条件始终适用。
