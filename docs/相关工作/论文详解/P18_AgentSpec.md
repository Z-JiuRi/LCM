# [P18] AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents

> 核验/解读日期：2026-10-20。对应综述编号 `P18`，BibTeX key：`wang2026agentspec`。

## 1. 文献信息与阅读边界

- 作者/机构：Wang, Haoyu and Poskitt, Christopher M. and Sun, Jun。
- 载体与年份：Proceedings of the 2026 IEEE/ACM 48th International Conference on Software Engineering；2026。
- 类型：system / runtime enforcement。
- 阅读深度：B：公开论文的问题、结构化规则及正式出版信息。
- 原始来源：[正式 DOI](https://doi.org/10.1145/3744916.3764546)；[公开论文](https://arxiv.org/abs/2503.18666)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

AgentSpec 研究如何对 LLM Agent 的工具行为施加可定制运行时约束。自然语言计划看似合理，不代表它满足应用权限或安全条件；运行时规则因此不能只寄托于 prompt 中的“请谨慎”。

## 3. 方法与工作流程

机制将触发、谓词和处置表达为结构化规则，在动作边界执行检查。关键是将决策提议与允许执行分离，方便领域人员调整策略。规则执行与证据获取是两个问题：谓词需要真实、当前的状态，给旧状态做再严格检查也可能得出错误放行。

## 4. 实验证据、结果与局限

公开稿 2025 年发布，已有 ICSE 2026 页码 2938–2950。当前未重审全部领域实验，不把其案例成功率当成无线模型发布的保障。通用运行时约束不等于实时无线配置正确、跨端提交原子或传感器测量真实。

## 5. 对 LCMAgent 的具体影响

LCMAgent 的 schema、权限、预算和动作白名单应视为基建与共享基线，而非主要创新。可研究的是证据何时过期、哪些检查必须重新测量、何时选择升级人工，以及模型配置变化如何撤销旧许可。LLM 不应有权关闭这些守卫来提高完成率。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 把每项硬约束写成可测试谓词，标明状态来源和失效条件。
- 与相同规则系统比较，隔离 Agent 选择证据的新增价值。
- 测试规则本身遗漏状态或错误信任旧工具结果的情况。

## 7. 引用与导航

### 公开代码

[AgentSpec 项目仓库](https://github.com/haoyuwang99/AgentSpec) 公开了规则运行时和示例。GitHub 未检测到 SPDX 许可证；代码公开可访问不自动授权再发布或商用。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `wang2026agentspec`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
