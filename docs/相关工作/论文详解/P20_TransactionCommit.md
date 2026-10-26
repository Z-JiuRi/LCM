# [P20] Consensus on transaction commit

> 核验/解读日期：2026-10-20。对应综述编号 `P20`，BibTeX key：`gray2006transactioncommit`。

## 1. 文献信息与阅读边界

- 作者/机构：Gray, Jim and Lamport, Leslie。
- 载体与年份：ACM Transactions on Database Systems；2006。
- 类型：theory / protocol。
- 阅读深度：B：作者机构原始记录及核心协议问题。
- 原始来源：[正式 DOI](https://doi.org/10.1145/1132863.1132867)；[原始材料/作者入口](https://www.microsoft.com/en-us/research/publication/consensus-on-transaction-commit/)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

Consensus on Transaction Commit 讨论分布式事务提交如何在参与方与协调者可能故障时形成一致决定。它提醒无线模型部署设计不能凭 PREPARE、COMMIT、ACK 三个消息名就宣布一种新的可靠协议。

## 3. 方法与工作流程

经典事务提交分析需要明确持久状态、崩溃、消息传播以及决定恢复，并将传统两阶段提交的阻塞问题与基于共识的提交联系起来。事务决定一致与无线数据面同时生效仍不同：后者还有旧数据包、新模型、配置切换和时钟误差。不能把数据库提交性质未经映射直接搬到 UE/gNB。

## 4. 实验证据、结果与局限

这是正式 ACM TODS 2006 理论/协议论文，不提供无线 KPI 实验。适用性质依赖故障与通信假设；有永久分区时不应同时口头许诺无条件一致、可用和有界时延。具体系统要声明是在保证原子决定、有限错配窗口还是最终恢复。

## 5. 对 LCMAgent 的具体影响

对于双侧 CSI，协议必须防止 encoder/decoder 在同一数据流语义上失配；单侧波束则主要是模型与码本/测量 epoch 绑定，不需要照搬双参与者事务。LCMAgent 的新意应在无线约束下的可验证性质或风险—成本收益，而不是泛化的事务术语。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 画出每个持久化点和消息丢失后的恢复路径。
- 分别测试协调者崩溃、UE 重启、重复消息和旧 epoch 重放。
- 分开报告控制面提交决定与实际数据路径生效时间。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `gray2006transactioncommit`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
