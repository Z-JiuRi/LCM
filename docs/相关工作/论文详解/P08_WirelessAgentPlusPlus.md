# [P08] WirelessAgent++: Automated Agentic Workflow Design and Benchmarking for Wireless Networks

> 核验/解读日期：2026-10-20。对应综述编号 `P08`，BibTeX key：`tong2026wirelessagentplusplus`。

## 1. 文献信息与阅读边界

- 作者/机构：Tong, Jingwen and Li, Zijian and Liu, Fang and Guo, Wei and Zhang, Jun。
- 载体与年份：公开稿 / arXiv；2026。
- 类型：method + benchmark。
- 阅读深度：A：公开全文的搜索机制、WirelessBench 和报告指标。
- 原始来源：[公开论文](https://arxiv.org/abs/2603.00501)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

该工作研究无线 Agent 工作流如何自动设计，而非仅凭人工固定 prompt。它将任务理解、工具调用和工作流结构优化联系起来，因此“自动规划多步无线流程”不能作为 LCMAgent 独有能力。

## 3. 方法与工作流程

方法使用 MCTS 搜索工作流，结合 penalized Boltzmann、成熟度感知 critic、三类 replay 与收敛判断。其核心对象是工作流候选及评价反馈，不是 UE/gNB 模型对提交协议。性能来自搜索、评估与工作流改进的组合，不能只与无工具单轮 LLM 比较。

## 4. 实验证据、结果与局限

WirelessBench 包含 WCHW 1,392 项、WCNS 1,000 项和 WCMSA 1,000 项，文中对应成绩为 78.37%、90.95%、97.07%。这些是各任务设定的准确率，不是安全发布率，也不表示 97.07% 的模型更新在故障下成功。应进一步核对搜索成本、评价器和训练测试隔离。

## 5. 对 LCMAgent 的具体影响

它是工作流搜索的强近邻。LCMAgent 可考察面对异构证据工具时，动态工作流是否比固定补测流程更省成本；但必须在同一冻结执行层上比较，并将 workflow search 开销纳入。若每个用例只有固定两步流程，工作流搜索或多 Agent 的必要性可能很弱。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 保持 benchmark 三类任务及分母分开，不把多个准确率混为总安全率。
- 测试固定工作流、自动搜索工作流及非 LLM 规划器。
- 计入搜索阶段与部署阶段各自的 token、工具次数和尾延迟。

## 7. 引用与导航

### 公开代码

[WirelessAgent-R2](https://github.com/jwentong/WirelessAgent-R2) 的 README 描述 MCTS 工作流搜索、WirelessBench 和项目结果，作为本论文公开代码仓库；GitHub 标注 MIT。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `tong2026wirelessagentplusplus`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
