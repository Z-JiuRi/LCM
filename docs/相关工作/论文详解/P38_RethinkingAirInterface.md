# [P38] Position Paper: Rethinking AI/ML for Air Interface in Wireless Networks

> 核验/解读日期：2026-10-20。对应综述编号 `P38`，BibTeX key：`kontes2025rethinkingairinterface`。

## 1. 文献信息与阅读边界

- 作者/机构：Kontes, Georgios and Michalopoulos, Diomidis S. and Ghimire, Birendra and Mutschler, Christopher。
- 载体与年份：ICML 2025 Workshop on Foundation Models for Telecommunications；2025。
- 类型：position paper / workshop。
- 阅读深度：A：公开全文的范围、标准化观点和研究挑战。
- 原始来源：[公开论文](https://arxiv.org/abs/2506.11466)；[原始材料/作者入口](https://icml.cc/virtual/2025/48597)。
- 书目状态：Workshop position paper; not an ICML main-conference paper

## 2. 问题、对象与前提

这篇立场论文强调 AI/ML 与无线空口结合需要跨学科理解，不能照搬视觉或语言领域的训练/评估习惯。它梳理 3GPP 讨论、用例、架构和技术需求，适合作为问题地图而不是某个算法的定量基线。

## 3. 方法与工作流程

文章从空口 AI/ML 场景与部署约束出发，组织数据、架构、协作及研究机会。观点型论文的机制主要是问题分解和框架主张，不应虚构成已经实现统一模型、端到端协议或全场景实验。对单侧/双侧及标准与实现的区分尤其值得用于整理 LCMAgent 的术语。

## 4. 实验证据、结果与局限

载体是 ICML 2025 Workshop on Foundation Models for Telecommunications，并非 ICML 主会。预印本 2506.11466 提供可核验原文。其开放挑战不是排他性新颖性证明，也不能用作者观点代替具体 TR/TS 条款。

## 5. 对 LCMAgent 的具体影响

它支持 LCMAgent 采用功能级视角、重视真实数据和部署代价，但不能支撑“所有问题都适合 Agent”。项目应从问题地图中选择可测量的一条决策链，以波束和 CSI 的不同耦合方式验证，再谨慎讨论定位/接收机扩展。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 将论文每个挑战映射到可观察状态、具体动作和实验指标。
- 所有标准化断言回查固定规范版本，不仅引用立场论文。
- 区分研究倡议、已实现能力与项目后续假设。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `kontes2025rethinkingairinterface`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
