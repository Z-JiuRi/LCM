# [P14] Open RAN Conflict Agents: Detecting and Mitigating xApp Conflicts with Generative Agents

> 核验/解读日期：2026-10-20。对应综述编号 `P14`，BibTeX key：`kwonOpenRANConflictAgents`。

## 1. 文献信息与阅读边界

- 作者/机构：Kwon, Dae Cheol and Zhang, Xinyu。
- 载体与年份：Author publication listing；年份未独立核验。
- 类型：system / generative agents。
- 阅读深度：C：作者公开记录；正式载体和完整实验未独立核验。
- 原始来源：[原始材料/作者入口](https://xyzhang.ucsd.edu/)。
- 书目状态：Publication year, venue, and DOI not independently verified as of 2026-10-20

## 2. 问题、对象与前提

Open RAN Conflict Agents 研究多个 xApp 控制冲突的发现与缓解。网络上每个应用局部合理，并不代表共享无线资源和控制参数的整体行为合理；这与多 UE 同时更新模型时的全局资源冲突有相似结构。

## 3. 方法与工作流程

作者材料描述使用生成式 Agent 处理 xApp 冲突。本次未确认完整机制和正式出版信息，不能根据本地 PDF 文件名中的 INFOCOM26 推断主会录用，也不能把其能力与 PACIFISTA 合并成同一种算法。需要进一步核对冲突类型、状态输入、建议生成和执行仲裁分别由谁完成。

## 4. 实验证据、结果与局限

目前只保留可核查题名、作者和公开入口，不填写猜测 DOI、页码或年份。未核实不代表工作不存在或质量低，而是证据不足以支撑更强论断。不能在相关工作表中将未知能力填为“没有”。

## 5. 对 LCMAgent 的具体影响

LCMAgent 应考虑共享 decoder、GPU/内存、下载带宽与测量资源的竞争。生成式协商不能替代原子资源预留或确定性仲裁；可将该工作作为相邻冲突推理路线，与无 LLM 的 PACIFISTA 并列，而不是把全局冲突管理当成空白。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 向作者原始论文页核对出版信息与可用全文。
- 建立可复核的冲突标签，区分直接、间接和资源型冲突。
- 测试每 UE 都通过局部验证但全局超预算的组合场景。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `kwonOpenRANConflictAgents`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
