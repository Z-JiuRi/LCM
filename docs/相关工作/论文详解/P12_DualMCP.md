# [P12] Demo: Human-in-the-Loop Agentic Reconfiguration of Edge 5G Networks via Dual-MCP and LLM Reasoning

> 核验/解读日期：2026-10-20。对应综述编号 `P12`，BibTeX key：`baena2025dualmcp`。

## 1. 文献信息与阅读边界

- 作者/机构：Baena, Eduardo and Mandal, Ankita and Koutsonikolas, Dimitrios。
- 载体与年份：Proceedings of the Twenty-sixth International Symposium on Theory, Algorithmic Foundations, and Protocol Design for Mobile Networks and Mobile Computing；2025。
- 类型：demo / system。
- 阅读深度：A：作者公开的两页 MobiHoc demo 全文。
- 原始来源：[正式 DOI](https://doi.org/10.1145/3704413.3765314)；[原始材料/作者入口](https://ece.northeastern.edu/fac-ece/dkoutsonikolas/publications/demo_mobihoc25.pdf)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

论文展示通过 Dual-MCP 和 LLM 推理对边缘 5G 网络进行人机协同重配置。最直接的相关性是 gNB 和 UE 两端都暴露工具服务，因此“双侧组件可调用”或“云端 LLM 跨端协调”不能再被写成独有架构。

## 3. 方法与工作流程

原型使用 OAI gNB、USRP B210 和 Quectel UE，双方 MCP 工具由云端 LLM 编排，执行前保留人工批准。文中还提出前后条件、日志与可逆操作。MCP server 是工具边界，不等于每侧都有自主推理 LLM；不能把双端工具与双 Agent 混为一谈。

## 4. 实验证据、结果与局限

这是 MobiHoc 2025 的两页 demo，正式页码 391–392。它提供实机集成先例，却没有足够篇幅证明任意故障下的原子激活或长期恢复。文中的“formal”“rollback”表述应结合具体检查机制看，不能替代故障假设与证明。

## 5. 对 LCMAgent 的具体影响

公平基线可以是相同双端工具、相同人工/自动权限，再增加功能 manifest、证据时效、资源预留和恢复机制。若只展示模型下载与激活工具，研究层次可能仍接近 demo。非 CSI 用例也可借这一工具布局，但每类证据和回退需重新定义。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 复核真实工具权限、审批点和状态读取，区分演示脚本与自主控制。
- 在相同工具下比较无 manifest、静态 manifest 和时效证据策略。
- 注入执行到一半失败，观察真实网络状态而非仅看日志的 rollback 标签。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `baena2025dualmcp`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
