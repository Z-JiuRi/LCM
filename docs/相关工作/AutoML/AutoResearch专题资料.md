# AutoResearch 原版比较专题资料

> 整理日期：2026-10-25。原文整理；未新增文献核验或实验结果。原章节编号保留，便于核对旧稿。

[文档导航](../../README.md) · [原稿章节对照](../../整理说明.md)

---

> 来源：`AutoML_Agentic_AutoML_Research_Report_2026-10-22_v3_AutoResearch_Ecosystem.md`；2026-10-22 V3。

<a id="s21-19"></a>

### 21.19 本章主要资料与延伸阅读（逐项可追溯）

这些为**新增章节的独立引用**；原报告[第 19 章](参考资料.md#s19)的 [R01]–[R58] 仍保留，部分内容与此处互相补充。

| 编号 | 资料 | 类型与本章使用理由 |
|---|---|---|
| [AR01] | [Karpathy — autoresearch 官方仓库 README](https://github.com/karpathy/autoresearch) | **一手代码说明**：文件职责、五分钟训练、`val_bpb`、平台边界 |
| [AR02] | [Karpathy — `program.md` 原始实验协议](https://raw.githubusercontent.com/karpathy/autoresearch/master/program.md) | **一手控制规则**：可编辑文件、Git、结果记录、回滚、不断运行 |
| [AR03] | [Ferreira et al. (2026), *Can LLMs Beat Classical Hyperparameter Optimization Algorithms? A Study on autoresearch*](https://arxiv.org/abs/2603.24647) | **论文实验**：固定 HP、代码编辑、混合优化比较；建议核对版本 v5 |
| [AR04] | [Ferreira et al. — 官方复现代码和结果](https://github.com/ferreirafabio/autoresearch-automl) | **一手研究仓库**：实验表格、方法分类、预算、OOM、Centaur |
| [AR05] | [Jiang et al. (2025), *AIDE: AI-Driven Exploration in the Space of Code*](https://arxiv.org/abs/2502.13138) | **论文**：代码空间树搜索与实验复用的先例 |
| [AR06] | [Trirat et al. (ICML 2025), *AutoML-Agent*](https://proceedings.mlr.press/v267/trirat25a.html) | **会议论文**：从数据到部署的多 Agent AutoML 工作流 |
| [AR07] | [Chun et al. (2026), *Recovering Wasted Compute in Autoresearch Agents*](https://arxiv.org/abs/2608.10424) | **论文**：重复 debug、低效搜索、共享失败经验 |
| [AR08] | [Yang et al. (2026), *Scaling Automatic Research Agents via World Models*](https://arxiv.org/abs/2608.12564) | **论文**：用世界模型减轻训练自主研究 Agent 的环境执行瓶颈 |
| [AR09] | [He et al. (2026), *The Greatness of Science Cannot Be Planned: Agentic Auto-Research is Fuzz Testing*](https://arxiv.org/abs/2608.09855) | **论文/方法论**：coverage 风格探索信号、受保护最终证据 |
| [AR10] | [Li et al. (2026), *Auto-RecSys: Harnessing Autonomous Research Agents for Industry-Scale Recommender System*](https://arxiv.org/abs/2609.10922) | **论文**：多天训练、异步集群、双循环记忆 |
| [AR11] | [Gu et al. (2026), *SAGE-Loop*](https://arxiv.org/abs/2609.12455) | **论文**：纠错闭环与自适应模型集成 |
| [AR12] | [IntologyAI — NanoGPT-Bench](https://github.com/IntologyAI/NanoGPT-Bench) | **基准项目**：自动研究 agent 与人类长期算法改进的差距；实验条件不同不可与 AR04 混比 |
| [AR13] | [Lu et al. (2024), *The AI Scientist*](https://arxiv.org/abs/2408.06292) | **论文**：更完整的科研构思—实验—成文流程 |
| [AR14] | [Hutter et al. (eds.), *AutoML: Methods, Systems, Challenges*](https://www.automl.org/book/) | **权威专著**：避免把 AutoML 缩写成“只调超参数” |
| [AR15] | [Siegel et al., *CORE-Bench*（2026 修订）](https://arxiv.org/abs/2409.11363) | **基准论文**：科学研究复现与优化试验是不同能力 |

> **阅读次序**：先看 [AR01] 和 [AR02] 彻底理解原版 autoresearch 的边界；再读 [AR03][AR04] 理解经典 HPO 和 Agent 的真实差距；用 [AR05][AR06] 定位它与原有 Agentic AutoML 的关系；读 [AR07]–[AR11] 判断 2026 年后续研究解决了哪些新瓶颈；最后参考 [AR12][AR15] 反思自主研究的评测与可信性。

---

<!-- 本页使用的引用定义；书目详情由对应资料索引维护。 -->
[AR01]: https://github.com/karpathy/autoresearch
[AR02]: https://raw.githubusercontent.com/karpathy/autoresearch/master/program.md
[AR03]: https://arxiv.org/abs/2603.24647
[AR04]: https://github.com/ferreirafabio/autoresearch-automl
[AR05]: https://arxiv.org/abs/2502.13138
[AR06]: https://proceedings.mlr.press/v267/trirat25a.html
[AR07]: https://arxiv.org/abs/2608.10424
[AR08]: https://arxiv.org/abs/2608.12564
[AR09]: https://arxiv.org/abs/2608.09855
[AR10]: https://arxiv.org/abs/2609.10922
[AR11]: https://arxiv.org/abs/2609.12455
[AR12]: https://github.com/IntologyAI/NanoGPT-Bench
[AR13]: https://arxiv.org/abs/2408.06292
[AR14]: https://www.automl.org/book/
[AR15]: https://arxiv.org/abs/2409.11363
[R01]: https://www.automl.org/book/ "Hutter, Kotthoff, Vanschoren (eds.) — AutoML: Methods, Systems, Challenges"
[R58]: https://aws.amazon.com/blogs/machine-learning/use-autogluon-tabular-in-aws-marketplace/ "AWS — AutoGluon-Tabular in AWS Marketplace"
