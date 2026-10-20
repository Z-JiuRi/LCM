# [P19] Quickest Change Detection with Controlled Sensing

> 核验/解读日期：2026-10-20。对应综述编号 `P19`，BibTeX key：`veeravalli2024controlledsensing`。

## 1. 文献信息与阅读边界

- 作者/机构：Veeravalli, Venugopal V. and Fellouris, Georgios and Moustakides, George V.。
- 载体与年份：IEEE Journal on Selected Areas in Information Theory；2024。
- 类型：theory / proof。
- 阅读深度：B：公开问题设定、WCC 方法与定理适用范围。
- 原始来源：[公开论文](https://arxiv.org/abs/2310.17223)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

Quickest Change Detection with Controlled Sensing 联合处理何时宣布变化与下一步选择哪种观测。它是“主动补测”最直接的方法基础之一：观测不是被动、同质且无成本地到达，选择会影响检测速度和误报。

## 3. 方法与工作流程

论文研究受控感知的 quickest change detection，提出 WCC，并在有限动作、变化后参数等设定下分析最坏情形检测时延与误报约束，建立渐近最优性质。需要把假设中的观测分布、可选动作集合和参数可辨识性具体写出，不能只引用“最优”二字。

## 4. 实验证据、结果与局限

理论结论具有严格条件，不自动覆盖状态不断漂移、UE 可拒绝、标签长期延迟、观测相关以及测量时模型又被更新的情况。2023 是公开稿首发，正式载体为 IEEE Journal on Selected Areas in Information Theory 2024；二者不应混写。

## 5. 对 LCMAgent 的具体影响

LCMAgent 若主张自主选择证据，不能只比固定周期采样。至少需要受控观测/序贯检测的适配基线，或者清楚说明哪些假设使直接使用不可行。Agent 的可能价值在异构工具、语义依赖和组合任务，而非重新发明已有观测选择问题。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 列出无线任务与理论模型的观测依赖、动作和变化参数映射。
- 在同一误报约束下比较检测时延与观测成本。
- 单列不满足独立性或参数假设的实验，不借原定理声称形式保证。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `veeravalli2024controlledsensing`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
