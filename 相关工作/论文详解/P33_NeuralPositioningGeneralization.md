# [P33] Spatial and Temporal Generalization of CSI-based Neural Positioning

> 核验/解读日期：2026-10-20。对应综述编号 `P33`，BibTeX key：`muller2026neuralpositioning`。

## 1. 文献信息与阅读边界

- 作者/机构：Müller, Till-Yannic and Zumegen, Frederik and Wiesmayr, Reinhard and Studer, Christoph。
- 载体与年份：公开稿 / arXiv；2026。
- 类型：method + real-world evaluation。
- 阅读深度：A：公开全文的三数据集、架构与空间/时间留出协议。
- 原始来源：[公开论文](https://arxiv.org/abs/2606.18150)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

该工作研究 CSI 神经定位能否推广到未见位置、轨迹和采集日期。传统随机划分相邻 CSI 快照容易呈现乐观结果，不能反映真实系统跨空间及跨时间使用的要求。

## 3. 方法与工作流程

比较常规 MLP 与提出的 Transformer 架构，使用三个室内/室外真实 Wi-Fi 和 5G NR 数据集。设计包括留出空间区域、完整留出连续 UE 轨迹，以及对相隔一周的采集活动做训练/测试组合。评价绝对位置误差及其统计分布，而非只看神经网络训练损失。

## 4. 实验证据、结果与局限

在论文所考察设置下，两种架构均能实现空间和时间泛化，Transformer 以更少参数得到更好的定位精度。不能把论文动机歪曲成“实验证明跨日期必然崩溃”。数据集数量、环境与时间跨度限制了外推；一周后的成功不能保证跨楼宇、锚点重布或硬件替换同样可用。

## 5. 对 LCMAgent 的具体影响

最有价值的是评估协议。LCMAgent 的定位更新应按区域、轨迹和日期验收；没有在线位置真值时，CSI 漂移只能提供代理证据。还应管理锚点/坐标、时间同步和校准，使证据与实际定位语义绑定；这些是项目扩展，不能说原文已实现生命周期 Agent。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 优先复用其三类留出协议，分别报告均值和高分位位置误差。
- 区分代理漂移指标、少量锚点真值和真实用户定位误差。
- 注入锚点坐标偏差与采集配置改变，比较校准、换模型和额外测量。

## 7. 引用与导航

### 公开代码

[neural-positioning-transformer](https://github.com/IIP-Group/neural-positioning-transformer) 是作者组的仓库，README 链接到本文，含数据集构造与模型脚本；GitHub 未检测到 SPDX 许可证。本次未运行代码，须保留论文的空间、轨迹和时间留出评估，避免只使用随机 CSI 快照切分。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `muller2026neuralpositioning`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
