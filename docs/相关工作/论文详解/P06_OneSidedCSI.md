# [P06] Deep Learning for CSI Feedback: One-Sided Model and Joint Multi-Module Learning Perspectives

> 核验/解读日期：2026-10-20。对应综述编号 `P06`，BibTeX key：`guo2025onesidedcsi`。

## 1. 文献信息与阅读边界

- 作者/机构：Guo, Yiran and Chen, Wei and Sun, Feifei and Cheng, Jiaming and Matthaiou, Michail and Ai, Bo。
- 载体与年份：IEEE Communications Magazine；2025。
- 类型：survey / perspectives。
- 阅读深度：B：公开摘要、作者机构说明及题名核验。
- 原始来源：[公开论文](https://arxiv.org/abs/2405.05522)。
- 书目状态：Public manuscript first posted in 2024; final volume and pages not independently verified

## 2. 问题、对象与前提

该工作从 one-sided model 与 joint multi-module learning 重新审视深度学习 CSI 反馈，提醒读者“AI CSI”并不自动等于双方各运行一个神经网络。部署形式、训练方式和无线处理模块之间的学习耦合需要分开讨论。

## 3. 方法与工作流程

核心阅读轴是：哪些处理可以只在一侧增强，哪些需多模块共同优化，以及这种选择如何影响接口、训练和部署约束。多模块联合学习不必等于两个 LLM Agent 协商；同样，单侧模型不代表其数据、配置或测量完全不需要网络协作。当前解读限于可核验的观点，不补写网络结构或训练损失细节。

## 4. 实验证据、结果与局限

这是方法视角和部署路线的参考，不应当成新型端网提交协议或故障恢复实证。本次未重新核对全部数值实验，故不列收益百分比。公开稿日期与后续期刊出版年份应分别记录，不能仅根据 arXiv 首稿年份引用正式卷期。

## 5. 对 LCMAgent 的具体影响

对 LCMAgent 最重要的作用是纠正范围：功能契约是共同层，双侧 PairManifest 只是特例。波束、定位和接收机也可成为单侧推理、跨端管理的对象。评估应显式比较单侧和双侧的管理成本，而非假定双 Agent 是唯一合理架构。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 逐个用例画推理位置、训练位置、测量来源和控制权限四张映射。
- 比较单侧增强与双侧压缩时匹配反馈预算和目标指标。
- 把 joint learning、joint activation 和 multi-agent planning 三个术语分别定义。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `guo2025onesidedcsi`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
