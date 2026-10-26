# [P07] WirelessAgent: Large language model agents for intelligent wireless networks

> 核验/解读日期：2026-10-20。对应综述编号 `P07`，BibTeX key：`tong2026wirelessagent`。

## 1. 文献信息与阅读边界

- 作者/机构：Tong, Jingwen and Guo, Wei and Shao, Jiawei and Wu, Qiong and Li, Zijian and Lin, Zehong and Zhang, Jun。
- 载体与年份：China Communications；2026。
- 类型：system / agent framework。
- 阅读深度：B：公开论文摘要、结构及正式出版记录；未重新审计全部性能实验。
- 原始来源：[正式 DOI](https://doi.org/10.23919/JCC.FA.2025-0163.202603)；[公开论文](https://arxiv.org/abs/2505.01074)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

WirelessAgent 将 LLM Agent 引入无线任务理解、推理与工具使用，回应传统控制流程难以处理自然语言需求和多种专业任务的问题。它属于通用无线智能体近邻，但研究对象不自动包含无线模型生命周期事务。

## 3. 方法与工作流程

可核验的框架关注领域知识、任务规划和与无线工具交互。理解论文时要分离“能够形成可执行任务链”与“部署动作在旧状态、并发和丢包下仍安全”。语言正确性、工具输出正确性和实际网络生效是三个不同层次，不能用一类测试成绩替代另一类。

## 4. 实验证据、结果与局限

正式记录已进入 China Communications 2026 年 3 月卷期，不应只写 2025 arXiv，也不能误标主会。当前未重审实验协议，故不引用未经核对的提升比例。任务完成或答题得分并不等于实际模型发布的安全率。

## 5. 对 LCMAgent 的具体影响

适合提供通用 Agent 基线和无线工具接口参照；LCMAgent 的差异不应是“也能读无线日志”，而应是功能版本、配置依赖、证据预算和执行后状态验证。公平比较须给通用 Agent 同样模型库、工具和确定性验证器，否则容易把工具工程收益误归给新决策方法。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 建立同工具、同模型、同预算的任务集，区分知识问答和实际控制。
- 单列工具错误、旧证据误用与执行不生效，不只记最终文本。
- 保留拒绝、升级人工和工具失败样本，避免只统计成功轨迹。

## 7. 引用与导航

### 公开代码

预印本链接到 [WirelessAgent_R1](https://github.com/jwentong/WirelessAgent_R1)，属于该工作的公开项目仓库。GitHub 页面未检测到 SPDX 许可证；可浅克隆阅读，不应默认可再发布或商用。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `tong2026wirelessagent`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
