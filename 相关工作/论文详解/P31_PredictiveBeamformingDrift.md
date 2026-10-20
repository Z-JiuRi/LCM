# [P31] Challenges of Predictive Beamforming Using Geographical Positioning: Insights from the DeepSense Dataset

> 核验/解读日期：2026-10-20。对应综述编号 `P31`，BibTeX key：`vladimirov2025predictivebeamforming`。

## 1. 文献信息与阅读边界

- 作者/机构：Vladimirov, Rodion and Laskov, Pavel。
- 载体与年份：2025 16th IFIP Wireless and Mobile Networking Conference (WMNC)；2025。
- 类型：empirical analysis / benchmark study。
- 阅读深度：A：IFIP 公开原始论文，核对动机、任务因素与漂移结论。
- 原始来源：[正式 DOI](https://doi.org/10.23919/WMNC67099.2025.11299263)；[原始材料/作者入口](https://opendl.ifip-tc6.org/db/conf/wmnc/wmnc2025/1571178178.pdf)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

Vladimirov 与 Laskov 最初希望系统比较 DeepSense 上的预测波束方法，却发现地理位置输入的不精确、任务构造和数据漂移会主导结果。研究重点不是继续堆网络，而是识别位置辅助波束形成究竟在哪些条件下有效。

## 3. 方法与工作流程

论文围绕任务定义、归一化、输入模态和数据漂移四个因素分析。地理坐标与最佳波束并非一一对应，有限定位精度和传播多径会形成不可忽略的歧义；改变训练/测试组织也会改变泛化难度。应结合时间和场景研究漂移，而不是只随机抽取近邻快照。

## 4. 实验证据、结果与局限

原文指出所考察位置辅助方法的准确率呈现平台期，且数据漂移造成显著下降。这个结论限于代表性 DeepSense 设置，不意味着全部多模态波束学习已无潜力。正式会议为 WMNC 2025；完整方法比较的设置须连同模型输入和评价任务一起引用，不摘不明分母的提升。

## 5. 对 LCMAgent 的具体影响

LCMAgent 不能把任何性能下降都诊断为“换一个更大模型”。可能需要定位校准、补充测量、增大候选波束集合或退回扫描。本文为主动证据的必要性提供实证动机，却不提供本项目的最优采样或发布协议。应将传感器误差与模型适用性分别作为隐藏状态。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 复现其任务定义、归一化和时间切分，避免只复现一个分类数字。
- 独立注入 GPS 偏差、时延与信道场景变化，检查诊断是否混淆。
- 比较换模型、重新校准和扩展扫描的风险—成本，而不是预设正确动作一定更新。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `vladimirov2025predictivebeamforming`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
