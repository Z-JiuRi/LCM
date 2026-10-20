# [P24] Agentic AI for ISAC: Analysis, Framework, and Case Study

> 核验/解读日期：2026-10-20。对应综述编号 `P24`，BibTeX key：`xie2026agenticisac`。

## 1. 文献信息与阅读边界

- 作者/机构：Xie, Wenwen and Sun, Geng and Zhang, Chuang and Liu, Xuejie and Kim, Dong In。
- 载体与年份：公开稿 / arXiv；2026。
- 类型：survey / framework / case study。
- 阅读深度：B：公开摘要与 v2 版本，未全面复审案例。
- 原始来源：[公开论文](https://arxiv.org/abs/2512.15044)。
- 书目状态：arXiv v2 dated 2026-06-27; first posted in 2025; final venue not independently verified

## 2. 问题、对象与前提

该工作讨论 Agentic AI 在通感一体化 ISAC 中的分析、框架和案例。ISAC 同时牵涉通信与感知目标，适合说明无线 Agent 的功能空间不应局限于 CSI 压缩，但不能因为场景广就推导模型 LCM 已被解决。

## 3. 方法与工作流程

应分别辨识 Agent 接收的任务、感知/通信工具、目标冲突与动作执行边界。本轮未充分核验案例细节，故不虚构特定雷达波形、调度算法或收益数字。多目标协同与模型版本一致性也不是同一个问题。

## 4. 实验证据、结果与局限

公开首稿 2025 年，当前记录有 2026-06-27 v2；正式出版未独立确认。框架和案例只能支持其实际设定，不能证明跨传感器失准、标签缺失和恶劣天气下仍然可靠。

## 5. 对 LCMAgent 的具体影响

LCMAgent 的可扩展对象可包括感知辅助波束模型和 ISAC 功能，但应先明确传感器校准、时间对齐、隐私与失效回退。共享管理骨架不代表通信吞吐和感知精度可用一个未经解释的标量统一，更不代表 LLM 可接管高速波形处理。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 补齐案例的输入、动作和执行环境，区分概念图与可运行系统。
- 为感知丢失、遮挡和校准偏差分别设计故障。
- 将通信与感知指标分列，说明多目标权衡而非随意加权。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `xie2026agenticisac`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
