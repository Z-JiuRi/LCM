# [P10] AgentRAN: An Agentic AI Architecture for Autonomous Control of Open 6G Networks

> 核验/解读日期：2026-10-20。对应综述编号 `P10`，BibTeX key：`elkael2026agentran`。

## 1. 文献信息与阅读边界

- 作者/机构：Elkael, Maxime and D'Oro, Salvatore and Bonati, Leonardo and Polese, Michele and Lee, Yunseong and Furueda, Koichiro and Melodia, Tommaso。
- 载体与年份：IEEE Communications Magazine；2026。
- 类型：system / architecture。
- 阅读深度：B：公开记录、架构与官方代码入口；未运行代码。
- 原始来源：[正式 DOI](https://doi.org/10.1109/MCOM.001.2500563)；[公开论文](https://arxiv.org/abs/2508.17778)。
- 书目状态：Journal DOI verified; final volume, issue, and pagination not independently verified

## 2. 问题、对象与前提

AgentRAN 讨论开放 6G 网络的 Agentic 控制架构，重点在意图、分层网络控制与无线工具的衔接。其价值是把智能体置于可实现的开放 RAN 控制栈，而不是单独做领域问答。

## 3. 方法与工作流程

阅读时应检查任务在不同控制层如何分解、LLM 所在时间尺度以及实际网络动作如何执行。分层 Agent 并不自动具有 UE 侧模型状态，也不自动解决模型库版本、输入配置和数据面激活的一致性。需要按控制对象逐项比较，而不是看到“hierarchical agents”就判定与 LCMAgent 完全相同或完全不同。

## 4. 实验证据、结果与局限

公开工作包含真实 5G 演示及代码入口，正式 DOI 对应 IEEE Communications Magazine 2026，精确卷期未在本次独立确认。原型存在不等于仓库已安装、第三方环境已可复现；本轮未执行该项目，也不引用未核对的收益。

## 5. 对 LCMAgent 的具体影响

它是总体架构和真实无线工具的强参照。LCMAgent 应复用相同分层原则，将差异放在模型功能契约与证据决策，而非把“全局规划、局部执行”当首创。单侧波束功能可以先以网络 Agent + UE runtime 实现，不必机械地复制两套大模型。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 核对控制接口、实际硬件和时间尺度，避免把慢速 Agent 放入逐时隙路径。
- 审查代码版本、依赖与许可证后再声明可复现。
- 在同样工具层上比较，隔离接口工程与决策算法收益。

## 7. 引用与导航

### 公开代码

[AgentRAN 仓库](https://github.com/wineslab/agentran) 标注 MIT，并指向论文；其 README 将 [OAI 配套 fork](https://github.com/wineslab/oai-release-agentRAN/tree/dl-lua-scheduler) 列为配套 RAN 栈，本次将两者分别列入浅克隆清单。尚未安装或运行该代码。配套 fork 的 GitHub API 许可字段为 `NOASSERTION`，README 引用上游 OAI Public 许可，请下载前检查具体文件许可。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `elkael2026agentran`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
