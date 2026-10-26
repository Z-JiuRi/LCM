# [P15] PACIFISTA: Conflict Evaluation and Management in Open RAN

> 核验/解读日期：2026-10-20。对应综述编号 `P15`，BibTeX key：`brachdelprever2025pacifista`。

## 1. 文献信息与阅读边界

- 作者/机构：Brach del Prever, Pietro and D'Oro, Salvatore and Bonati, Leonardo and Polese, Michele and Tsampazi, Maria and Lehmann, Heiko and Melodia, Tommaso。
- 载体与年份：IEEE Transactions on Mobile Computing；2025。
- 类型：system / conflict management。
- 阅读深度：B：公开摘要、版本与方法框架。
- 原始来源：[正式 DOI](https://doi.org/10.1109/TMC.2025.3570632)；[公开论文](https://arxiv.org/abs/2405.04395)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

PACIFISTA 研究 Open RAN 多应用间的冲突评估和管理，不依赖通用 LLM。多个 xApp/rApp 对同一网络状态产生相互作用时，只做单应用性能评估不足以发现组合退化。

## 3. 方法与工作流程

核心路线是通过 sandbox profiling 观察应用行为，再用图与统计方法刻画冲突，借助 Colosseum/OpenRAN Gym 相关环境评价。其作用对象是应用行为及共享网络控制，不应误写为专门解决 encoder/decoder 兼容性。

## 4. 实验证据、结果与局限

公开稿有 2024 首稿、2025 修订和 IEEE Transactions on Mobile Computing 2025 的出版记录。当前未重审全部图表，不引用具体降低冲突的数值；测试平台存在也不意味着本地已成功运行。冲突推断的覆盖范围取决于沙箱中实际探索的状态和负载。

## 5. 对 LCMAgent 的具体影响

这是 LCMAgent 不可省略的非 LLM 系统基线。模型生命周期的多 UE 资源竞争可采用 profiling 和确定性仲裁，不必全部交给 Agent。真正要比较的是在相同资源仲裁器上，证据选择和候选规划是否更有效，而不是有冲突管理与无冲突管理的差别。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 明确 sandbox 是否包含目标无线功能的算力、测量与激活开销。
- 在共享仲裁器下比较规则、统计策略和 LLM。
- 留出未见应用组合及负载，避免只复测已经 profiling 的配置。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `brachdelprever2025pacifista`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
