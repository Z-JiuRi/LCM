# [P11] Agentic Open RAN: A Deterministic and Auditable Framework for Intent-Driven Radio Control

> 核验/解读日期：2026-10-20。对应综述编号 `P11`，BibTeX key：`li2026agenticopenran`。

## 1. 文献信息与阅读边界

- 作者/机构：Li, Hengxu and Xu, Dongkuan and Chen, Mingzhe and Liu, Yuchen。
- 载体与年份：ICC 2026 - IEEE International Conference on Communications；2026。
- 类型：system / framework。
- 阅读深度：A：公开稿的意图、类型化接口、确定性执行与冲突合并机制。
- 原始来源：[正式 DOI](https://doi.org/10.1109/ICC59461.2026.11586905)；[公开论文](https://arxiv.org/abs/2604.13384)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

该工作针对自然语言意图驱动 RAN 控制中的可审计性与执行不确定性，提出 Agentic Open RAN / A1gent。它直接挑战“LLM 负责慢规划、确定性逻辑负责执行就是新贡献”的说法。

## 3. 方法与工作流程

Non-RT 侧将意图转成类型化 A1 表达，Near-RT 侧确定性执行，多个动作由固定优先级合并。LLM 输出不直接成为任意控制命令；控制接口和仲裁规则给出边界。需要区分类型正确、规则可审计以及所有并发/故障下有形式证明，这三者并不等价。

## 4. 实验证据、结果与局限

已有 ICC 2026 正式出版信息。本轮核对的是核心流程与公开稿，不据此宣布其对 UE 崩溃、消息重排或配对 CSI 更新具有完整保障。实验中的可行性或收益必须限制在论文的控制对象和负载范围。

## 5. 对 LCMAgent 的具体影响

确定性执行器、权限与动作合并应作为 LCMAgent 的共享基础设施。新问题可在于前置证据如何生成及失效、多个 UE 的资源如何预留，以及激活结果是否真的进入数据路径。对单侧波束模型，固定优先级规则还须与测量/码本配置变更顺序结合。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 记录意图到 A1 的字段与约束，禁止直接把自由文本转命令。
- 用同一动作合并器测试固定规则和 LLM 策略。
- 测试并发模型更新、资源撤销和配置 epoch 变更，区分已有能力与新增扩展。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `li2026agenticopenran`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
