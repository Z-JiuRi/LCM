# [P29] DeepBeam: Deep Waveform Learning for Coordination-Free Beam Management in mmWave Networks

> 核验/解读日期：2026-10-20。对应综述编号 `P29`，BibTeX key：`polese2021deepbeam`。

## 1. 文献信息与阅读边界

- 作者/机构：Polese, Michele and Restuccia, Francesco and Melodia, Tommaso。
- 载体与年份：Proceedings of the Twenty-second International Symposium on Theory, Algorithmic Foundations, and Protocol Design for Mobile Networks and Mobile Computing；2021。
- 类型：method + experimental dataset。
- 阅读深度：B：原始摘要、版本和正式 DOI；未逐图复核全文。
- 原始来源：[正式 DOI](https://doi.org/10.1145/3466772.3467035)；[公开论文](https://arxiv.org/abs/2012.14350)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

DeepBeam 研究 mmWave 链路建立和维护中的波束管理开销。传统显式协调、导频和扫描占用空口时间；其目标是从已有传输中识别发射波束及到达角信息，减少 TX/RX 为波束发现专门协调的需要。

## 3. 方法与工作流程

方法用 CNN 学习波形层特征，利用不同波束图案在接收波形中的可区分影响，推断发射端正在使用的波束与 AoA，并将 SNR 关联到候选波束。它不是简单用 GPS 分类 beam index，也不是模型版本切换协议。波形指纹与硬件、码本和接收配置相关，这些在生命周期视角中应成为依赖项。

## 4. 实验证据、结果与局限

摘要描述超过 4 TB 的实测 mmWave 波形、60.48 GHz 相控阵及 58 GHz 自定义全数字设备。5/12/24 波束条件下准确率最高分别约 96%/84%/77%；12 波束特定默认 NR 扫描比较中时延最多降至约 1/7。这些数字对应不同条件，不能平均或外推成所有 beam management 的收益。正式 DOI 为 10.1145/3466772.3467035。

## 5. 对 LCMAgent 的具体影响

适合作为被管理波束功能和低开销证据来源，但它的核心贡献不是部署后 LCM。LCMAgent 可研究硬件/码本变化后是否重校准、何时扩展扫描和何时禁用波形模型。必须将原文“少显式协调”的执行收益与新增管理开销分别计量。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 核对数据划分是否跨设备、位置和接收增益，再讨论分布漂移。
- 固定码本大小与扫描配置后比较时延，不混用 5/12/24 波束成绩。
- 用设备或码本变更构造生命周期事件，记录实测而非仅预测的 beam quality。

## 7. 引用与导航

### 公开代码

[DeepBeam 官方代码与数据仓库](https://github.com/wineslab/deepbeam) 的 README 明确对应本文并链接关联数据集。GitHub 标注 MIT。数据集另有外部下载入口；浅克隆代码仓库不会自动获取大体量波形数据。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `polese2021deepbeam`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
