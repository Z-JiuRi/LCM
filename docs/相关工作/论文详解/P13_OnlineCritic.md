# [P13] OnlineCritic-xApp: Online Learning for LLM-Assisted RAN Slice Resource Management

> 核验/解读日期：2026-10-20。对应综述编号 `P13`，BibTeX key：`fang2026onlinecritic`。

## 1. 文献信息与阅读边界

- 作者/机构：Fang, Zhou and Dang, Shuping and Zhang, Zhenrong and Zhang, Yan。
- 载体与年份：IEEE INFOCOM 2026 - IEEE Conference on Computer Communications；2026。
- 类型：pure method / xApp。
- 阅读深度：C：正式书目与既有本地阅读；本轮未复核完整实现和全部数值。
- 原始来源：[正式 DOI](https://doi.org/10.1109/INFOCOM59046.2026.11571592)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

OnlineCritic-xApp 将在线学习 critic 与 LLM 辅助 RAN 切片资源管理结合，研究候选资源动作的评价。其核心背景是网络环境变化时，纯离线评价或自由生成动作未必可靠。

## 3. 方法与工作流程

可确认的研究轴是 LLM 候选与在线学习评价环节的结合。本次没有重新逐项审计 critic 的输入、更新周期、训练损失和可行性边界，因此不把学习型评分器写成硬约束求解器，也不补写未经核对的动作投影机制。读者应回到正文区分 critic 预测、可行性检查和最终执行。

## 4. 实验证据、结果与局限

已核实为 IEEE INFOCOM 2026 正式论文及 DOI。书目确认不能替代算法精读；当前不摘录吞吐、效用或收敛百分比。尤其不能把切片环境中 critic 的经验成功率直接当成跨端模型发布的安全保证。

## 5. 对 LCMAgent 的具体影响

它适合作为“LLM 产生候选 + 外部评价器”的近邻，而不是 CSI 互操作或波束 LCM 的直接替代。LCMAgent 若使用学习式验收器，也须回答评价器是否过期、是否存在系统性误判，以及何时值得请求额外测量。学习分数应与确定性配置/权限约束分层。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 补读 critic 的更新、训练数据及测试隔离，核验是否有在线信息泄漏。
- 比较固定 critic、在线 critic 与确定性约束共享下的策略。
- 单独测评价器误判与最终执行违规，不能只看平均网络效用。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `fang2026onlinecritic`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
