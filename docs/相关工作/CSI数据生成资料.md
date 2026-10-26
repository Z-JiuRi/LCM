# CSI 数据生成：QuaDRiGa 与 DeepMIMO 资料及核验记录

> 检索日期：2026-10-25。目的：为 CSI 压缩反馈的数据生成选择工具、确认 API 和建立可追溯方案。本次阅读官方文档、指定版本源码及论文相关章节；未运行生成器或复现论文数值。

## 1. 工具版本与证据边界

| 工具 | 本次固定范围 | 已检查 | 尚未完成 |
|---|---|---|---|
| DeepMIMO | v4.0.5；commit `48945c29b47c537bf2ea82a929c33bd6ff7aac31` | release、打包配置、load/trim/compute_channels、OFDM 和动态教程 | 安装、下载完整地图、实际信道生成 |
| QuaDRiGa | 官方 main commit `277866650eb115adb5b3e8ac252b0d1df073596d`；附 2.8.1-0 手册 | 官方能力描述、空间一致性/时间演化教程、阵列/布局/fr 源码 | MATLAB/Octave 运行、完整手册逐页审计 |
| 本地 CsiNet | 仓库已有第三方目录 | README、only-test 输入/输出和评价代码 | 旧依赖复现、权重与新数据兼容验证 |

查询采用公开关键词：`QuaDRiGa official spatial consistency frequency response track`、`DeepMIMO v4 channel generation Doppler dynamic scenarios`、`DeepMIMO CSI feedback zone-specific`、论文题名和 API 名。检索范围优先官方仓库/文档、arXiv 和作者原文；搜索片段只用于发现入口，不作为技术依据。

## 2. 官方文档与源码入口

| ID | 原始来源 | 类型、版本与用途 |
|---|---|---|
| D1 | [DeepMIMO v4.0.5 release](https://github.com/DeepMIMO/DeepMIMO/releases/tag/v4.0.5) | system/tool；确认此次使用版本，发布日 2026-08-25 |
| D2 | [Quickstart](https://www.deepmimo.net/docs/quickstart.html) | 官方教程；已有场景下载、加载及信道轴 |
| D3 | [Channel Generation](https://www.deepmimo.net/docs/tutorials/3_channel_generation.html) | 官方教程；阵列、OFDM、时域路径与频域输出的区别 |
| D4 | [v4.0.5 channel.py](https://github.com/DeepMIMO/DeepMIMO/blob/v4.0.5/deepmimo/generator/channel.py) | 固定源码；默认频点、参数、路径到频响和幅度约定 |
| D5 | [v4.0.5 dataset.py](https://github.com/DeepMIMO/DeepMIMO/blob/v4.0.5/deepmimo/datasets/dataset.py) | 固定源码；trim 返回新数据集、compute_channels 时间轴 |
| D6 | [v4.0.5 load.py](https://github.com/DeepMIMO/DeepMIMO/blob/v4.0.5/deepmimo/datasets/load.py) | 固定源码；TX/RX set 与最大路径数 |
| D7 | [Doppler & Mobility](https://www.deepmimo.net/docs/tutorials/5_doppler_mobility.html) | 官方教程；速度、Doppler 与时间参数 |
| D8 | [Dynamic Ray Tracing](https://www.deepmimo.net/docs/applications/5_dynamic_rt.html) | 官方示例；几何更新、逐帧追踪及 DynamicDataset |
| D9 | [v3→v4 migration](https://www.deepmimo.net/docs/tutorials/8_migration_guide.html) | 官方教程；数据结构及带宽等参数单位变化 |
| D10 | [安装说明](https://www.deepmimo.net/docs/installation.html) | 官方文档；Python 与可选射线追踪依赖 |
| Q1 | [QuaDRiGa 官方仓库](https://github.com/fraunhoferhhi/QuaDRiGa) | system/tool；MATLAB/Octave、2.8 系列能力与手册入口 |
| Q2 | [t13 空间一致性](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/tutorials/t13_spatial_consistency.m) | 固定教程；连续轨迹与场景参数 |
| Q3 | [t08 时间演化](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/tutorials/t08_time_evolution.m) | 固定教程；分段与信道演化 |
| Q4 | [qd_channel.fr](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/quadriga_src/%40qd_channel/fr.m) | 固定源码；带宽 Hz、载波索引约定与四维输出轴 |
| Q5 | [qd_arrayant.generate](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/quadriga_src/%40qd_arrayant/generate.m) | 固定源码；阵元、极化、频率和间距参数 |
| Q6 | [qd_layout.get_channels](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/quadriga_src/%40qd_layout/get_channels.m) | 固定源码；插值、分段生成与合并职责 |

在线教程可能随 main 更新。示例接口以指定 tag/commit 为锚，实际运行时仍需记录安装版本、依赖和场景文件哈希；不把教程中的旧默认值描述为永久 API。

## 3. 与 CSI 反馈最直接的论文

| 论文 | 出处/版本与类型 | 阅读范围及本次用途 |
|---|---|---|
| [DeepMIMO: A Generic Deep Learning Dataset for Millimeter Wave and Massive MIMO Applications](https://arxiv.org/abs/1902.06435) | 2019 ITA 公开稿；system/tool + dataset | 摘要及数据定义；理解参数化场景、位置与传播依赖，不将 2019 格式当 v4 API |
| [Deep Learning for Massive MIMO CSI Feedback](https://arxiv.org/html/1712.08919v4) | IEEE WCL 2018；arXiv v4；pure method | §II–IV；角–时延预处理、完美 CSI 假设和 COST 2100 数据来源 |
| [Zone-Specific CSI Feedback for Massive MIMO: A Situation-Aware Deep Learning Approach](https://arxiv.org/html/2401.07451v1) | 2024-01-15 公开稿；pure method | §III–VII；DeepMIMO Boston 场景、按区域选择模型和更新/传输代价 |

Zone-Specific 工作已经覆盖“区域不同使用不同 CSI 模型”及模型参数传输/更新率。因此本项目不能只凭跨区域换模型主张新颖性；可检验的增量是证据成本、更新时间窗口、受限适配和双端可靠发布，但这些仍需与近邻做公平比较。

## 4. 本次发现的实现陷阱

| 风险 | 原始证据 | 处理建议 |
|---|---|---|
| DeepMIMO 默认只输出一个频点 | D4 的 `selected_subcarriers` | 显式选择完整频率网格 |
| 路径轴被当成均匀时延轴 | D3/D5 | 先计算频域信道，或按 delay 正确栅格化 CIR |
| 以为 DeepMIMO 没有动态能力 | D7/D8 | 区分固定几何 Doppler 与逐场景几何更新 |
| fr 标量载波数被误当对称频带 | Q4 | 保存实际频率偏移，统一 FFT 顺序 |
| 将每米采样点数误当时间 | Q2/Q6 | 用位置、速度或 movement profile 建立时间戳 |
| 同形状直接加载旧 CsiNet 权重 | 论文与本地 only-test | 先对齐预处理/分布；新数据优先重训练 |
| 两生成器的绝对功率直接混合 | D4/Q4 | 先校准单路径、阵列方向图与功率归一 |

## 5. 来源许可与未决项

DeepMIMO v4.0.5 的 [LICENSE](https://github.com/DeepMIMO/DeepMIMO/blob/v4.0.5/LICENSE)是 Apache-2.0，然而[打包元数据](https://github.com/DeepMIMO/DeepMIMO/blob/v4.0.5/pyproject.toml)与 [PyPI 4.0.5 元数据](https://pypi.org/pypi/deepmimo/4.0.5/json)标 GPL-2.0-or-later。本文如实记录不一致；源码、发布包、模型和场景资产的许可应分别留档，不将仓库徽章替代全部资产条款。

[QuaDRiGa LICENSE](https://github.com/fraunhoferhhi/QuaDRiGa/blob/277866650eb115adb5b3e8ac252b0d1df073596d/QuaDRiGa_License.txt)明确限定非商业用途并规定再发布条件。该事实用于实验材料记录，不据此推断所有生成数据的条款。

首批场景以官方 quickstart 的 ASU 数据为候选；其完整压缩包、精确文件版本、空间分区边界、轨迹身份与实际有效样本数尚未下载检查。动态 ASU 场景页面可作发现入口，不能在未核读文件前承诺其每帧包含相同 UE 或足够的时间分辨率。

本次未做数值复现或方法质量评分。已完成官方/原始来源筛选、版本定位、跨来源实现差异核对；未覆盖所有 QuaDRiGa/DeepMIMO 应用论文。生成方案中的样本数、量化与预算设置都是待 pilot 调整的项目建议。

[候选数据方案](../分析文档/实验工具链/CSI压缩反馈数据生成方案.md) · [DeepMIMO 实操](../工程参考/CSI数据生成/DeepMIMO生成指南.md) · [QuaDRiGa 实操](../工程参考/CSI数据生成/QuaDRiGa生成指南.md)
