# [P25] Adaptive Root Cause Analysis for Self-Healing in 5G Networks

> 核验/解读日期：2026-10-20。对应综述编号 `P25`，BibTeX key：`mfula2017adaptiverca`。

## 1. 文献信息与阅读边界

- 作者/机构：Mfula, Harrison and Nurminen, Jukka K.。
- 载体与年份：2017 International Conference on High Performance Computing &amp; Simulation (HPCS)；2017。
- 类型：pure method / self-healing。
- 阅读深度：C：正式书目和既有材料；未重新全面审计算法。
- 原始来源：[正式 DOI](https://doi.org/10.1109/HPCS.2017.31)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

Adaptive Root Cause Analysis for Self-Healing in 5G Networks 属于自愈网络的根因分析传统。异常 KPI 到底来自模型、负载、信道还是配置，是生命周期决策前必须回答的问题；Agent 文献不是这一问题的起点。

## 3. 方法与工作流程

论文研究适应性根因分析用于 5G 自愈。本轮证据不足以逐项复述其推理图、学习更新或恢复流程，因此不猜测所用算法。更稳妥的阅读方式是检查异常观测如何映射到根因、适应性由什么驱动、标签或专家知识从何而来。

## 4. 实验证据、结果与局限

正式载体为 HPCS 2017，页码 136–143。没有本次重新核对的实验数字，不应以宽泛“显著提升诊断”替代数据。较早的网络自愈工作也不能直接保证现代无线 AI 模型的配置和资源约束。

## 5. 对 LCMAgent 的具体影响

其启示是避免“发现业务下降就更新模型”的单因果假设。LCMAgent 应区分输入变化、模型失配、SNR 变差和资源拥塞；否则会进行无效微调或频繁切换。非 LLM 根因策略可作为诊断基线，和后续生命周期执行层分开评价。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 补读根因标签、故障集合和适应机制，记录专家依赖。
- 构造 KPI 下降但模型无问题，以及模型失配但 KPI 上升的双向反例。
- 分别衡量诊断准确率、错误干预成本和最终业务恢复。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `mfula2017adaptiverca`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
