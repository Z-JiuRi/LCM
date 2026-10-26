# Agentic AutoML 代表论文与训练型 Agent

> 整理日期：2026-10-25。原文整理；未新增文献核验或实验结果。原章节编号保留，便于核对旧稿。

[文档导航](../../README.md) · [原稿章节对照](../../整理说明.md)

---

> 来源：`AutoML_Agentic_AutoML_Research_Report_2026-10-22_v3_AutoResearch_Ecosystem.md`；2026-10-22 V3。

<a id="s8"></a>

## 8. Agentic AutoML 代表论文逐篇解读

> 阅读本节时应格外注意：部分工作优化的是预测分数，部分优化的是全流程成功率，另一些优化的是数据科学任务完成率。**同名“success rate / accuracy / medal rate”不具备天然可比性。**

<a id="s8-1"></a>

### 8.1 MLAgentBench：先定义什么叫“Agent 会做机器学习实验”

**文献**：Huang, Vora, Liang & Leskovec，*MLAgentBench: Evaluating Language Agents on Machine Learning Experimentation*，ICML 2024。[R20]

**研究问题**：给模型代码仓库、训练数据、任务目标和文件/命令工具，LLM Agent 能否自主读代码、训练模型、分析结果、进行改动并迭代实验？

**框架**：构造 13 个 ML 实验任务（从 CIFAR-10 模型改进到更接近当代研究任务的 BabyLM 等），允许 agent 读写文件、执行代码、观察命令输出。研究者基于 ReAct 思路组织代码执行与反馈流程。

**论文中的关键结果**：其所评估 agent 里，Claude 3 Opus Agent 平均成功率为 **37.5%**；成功率在不同任务上差距极大，较旧、成熟任务与较新的任务出现显著差异。

**方法价值**：明确提出“ML agent = 具备行动与真实反馈的实验者”，有助于区别通用问答能力与端到端工程能力。

**局限**：13 个任务对泛化结论还不足够；成功与否依赖成功阈值、代理工具能力、基础模型版本、训练预算、benchmark 发布与模型预训练时间。不能把 37.5% 类比为所有 ML 工程任务的成功概率。

**可复现建议**：固定 task snapshot、模型版本、系统指令、实验环境、执行时长，保留每次 action trace；同时观察**成功率、改善量、token 成本、GPU 小时、运行中断比例**。

<a id="s8-2"></a>

### 8.2 DS-Agent：把 Kaggle 的案例当“经验”而不只是提示词

**文献**：Guo et al., *DS-Agent: Automated Data Science by Empowering Large Language Models with Case-Based Reasoning*，ICML 2024。[R21]

**问题**：LLM 即使能生成代码，也可能制定不合理的实验计划，导致无效反复。

**方法**：利用 Case-Based Reasoning（CBR），从类似数据科学案例中检索可迁移的策略；开发阶段用反馈迭代积累经验，部署阶段用更简化的案例适配提升较低资源条件下的 one-pass 可用性。

**论文中的主张**：论文摘要报告 GPT-4 的开发阶段成功率为 100%，并报告部署阶段跨替代基础模型的平均 one-pass 成功率提升。**这属于作者定义的特定 benchmark/阶段指标**，不是所有真实业务数据科学任务都能完全自动成功。

**独特价值**：让“检索什么经验”成为搜索质量的一部分，可缩短无效 trial。

**局限**：案例来源的分布偏差、先验泄漏、相似度估计和解决方案移植的依赖环境都会影响效果。

**实现启示**：案例至少要包含**任务定义、数据统计、验证策略、核心特征变换、模型家族、收益和失败警告**。召回候选后执行约束过滤，再让 Agent 在本地验证，绝不直接复制高分 Kaggle 脚本里的目标编码或泄漏操作。

<a id="s8-3"></a>

### 8.3 AutoML-Agent：面向完整 Pipeline 的多智能体协作

**文献**：Trirat, Jeong & Hwang，*AutoML-Agent: A Multi-Agent LLM Framework for Full-Pipeline AutoML*，ICML 2025；arXiv 首发于 2024 年 10 月。[R22]

**研究问题**：多数传统 AutoML 工具只能自动化模型选择等部分环节，需要用户仍具备相当技术经验；能否从自然语言需求出发，自动完成数据检索、预处理、模型设计、执行到部署准备？

**结构特点**：

1. **Manager / 协同**：解析需求、组织阶段与专职 agent；
2. **Retrieval-Augmented Planning（RAP）**：借助检索增强的多方案规划，而非一次性生成单计划；
3. **任务分解**：将数据预处理、模型设计等交给专门 agent；
4. **并行方案探索**：提高候选策略覆盖度；
5. **多阶段验证**：在执行前/中/后以及实现验证阶段发现问题并反馈代码生成过程。

**证据**：论文在 **7 类下游任务、14 个数据集** 上实验，报告其全流程自动化成功率和跨模态适用性方面的优势。[R22]

**重要边界**：研究中的“deployment-ready”是作者定义的可交付产物及验证，不应直接等同于企业安全审计、线上数据漂移治理、A/B 测试、可回滚的生产上线系统。

**官方实现与许可**：公开仓库为 `DeepAuto-AI/automl-agent`，仓库标明 **CC BY-NC 4.0（禁止直接商用）**；企业应用之前必须逐项审查仓库及依赖的许可条款。[R23]

**核心值得借鉴的原则**：

- 多个候选计划能抵御单次规划失误；
- 以真实执行结果驱动下一步；
- 子任务职责应清晰；
- 验证流程必须是显式模块，而非让一个 agent 在末尾说“通过”。

<a id="s8-4"></a>

### 8.4 AutoKaggle：强调验证、调试与可人工干预的多 Agent 流程

**文献**：Li et al., *AutoKaggle: A Multi-Agent Framework for Autonomous Data Science Competitions*，2024 年 arXiv，ICLR 2025 Workshop。[R24]

**核心机制**：自动化数据处理—特征工程—建模阶段，整合代码执行、调试、单元测试与可自定义工作流，强调在每个阶段支持人的介入。

**论文披露**：作者使用 **8 个 Kaggle 竞赛** 模拟真实工作流；摘要中报告 validation submission rate **0.85** 和综合分数 **0.82**。必须按作者的度量定义理解，不应把两个数字解释成通用算法胜率或 Kaggle 铜牌率。

**启示**：在以代码为行动媒介的 Agent 中，**单元测试 + 运行验证**应与模型指标同等重要。许多失败是 train/test 列不匹配、日期格式错误、特征泄漏、提交文件格式错误，而不是模型本身性能差。

<a id="s8-5"></a>

### 8.5 Data Interpreter：复杂数据分析任务需要依赖图与分步验证

**文献**：Hong et al., *Data Interpreter: An LLM Agent for Data Science*，Findings of ACL 2025。[R25]

**方法**：通过分层图建模（hierarchical graph-based modeling）表示任务依赖关系，并采用逐步验证与修订，让数据分析任务的复杂、非线性流程能被管理。

**论文披露**：在其选择的数据分析、机器学习和开放任务 benchmark 上报告明显提升；这些增幅来自不同任务集和基线，不能拿其中的“accuracy”数值与 MLE-bench 的奖牌率相比。

**启示**：当 Agent 不只是改超参数，还需要做多表连接、特征提取、统计检验、训练与报告时，**有向依赖图**比单纯的循环聊天记录更适合作为可复盘执行计划。

<a id="s8-6"></a>

### 8.6 AIDE：以代码空间上的树搜索替代单链条试错

**文献**：Jiang et al., *AIDE: AI-Driven Exploration in the Space of Code*，arXiv 2025；官方代码 `WecoAI/aideml`。[R26]

**核心思想**：把候选机器学习解决方案表达为不同代码版本，每个版本是搜索树里的节点；LLM 根据父节点和执行反馈产生新的补丁或候选分支，系统追踪性能并选择后续扩展路线。

**与传统 BO 的本质差异**：

| 维度 | BO/TPE | AIDE 代码树搜索 |
|---|---|---|
| 搜索点 | 有类型的超参向量 | 可执行代码版本或补丁 |
| 邻域 | 定义好的参数空间距离 | LLM 语义修改、祖先/分支关系 |
| 搜索表达能力 | 较低到中等，可解释性较强 | 能修改数据处理和方法本身 |
| 搜索稳定性 | 依赖目标函数与代理模型 | 依赖代码可执行性、LLM 能力和日志 |
| 验证 | 常为同一目标函数 | 需先安全运行，再计算真实分数 |

**值得强调的工程机制**：搜索树要保存成功节点和失败节点；失败原因应结构化标记（syntax/runtime/OOM/metric/data error），否则 Agent 会重复无效尝试。

**局限**：模型可能在反复试验中对验证集过拟合，生成不安全或不可复现的代码；搜索树的收益必须与单一路径、相等预算下的 Optuna、手工强 baseline 比较。AIDE 官方仓库将自身描述为可研究与拓展的参考实现，不保证在所有业务中独立替代 MLOps 平台。[R26]

<a id="s8-7"></a>

### 8.7 R&D-Agent：把“研究假设”和“开发实现”拆成可迭代能力

**文献**：Yang et al., *R&D-Agent: An LLM-Agent Framework Towards Autonomous Data Science*，2025 年技术报告；官方仓库由 Microsoft 维护。[R27]

**主要思路**：将数据科学研发过程规范化，拆分高层 research/idea proposal 与 development/implementation，再根据实验反馈重复迭代；不仅生成脚本，还关注假设质量与可落地性。

**区别**：AIDE 的基本对象是代码搜索树，R&D-Agent 更着重把“提出可检验想法”和“落实实现”拆为不同功能，因而有利于研究不同环节的瓶颈：好想法没被正确实现，还是正确实现了坏想法？

**结果口径提醒**：技术报告、GitHub README 不同时间展示的 MLE-bench 成绩可能不一致，而且 README 的“当前领先”等字样随榜单变化会过期；本报告不将项目自报的一个数值视为所有版本的定论。[R27], [R31]

**推荐消融**：固定 development agent、比较人工 idea / LLM idea / 检索 idea；再固定 research agent、比较单次生成 / 多轮修复 / 执行级测试；只有这样才能区分两个模块的真实贡献。

<a id="s8-8"></a>

### 8.8 ML-Master：并行探索之后如何有效利用记忆

**文献**：Liu et al., *ML-Master: Towards AI-for-AI via Integration of Exploration and Reasoning*，arXiv 2025。[R33]

**问题**：并行探索带来大量轨迹，但如果把所有日志塞入 LLM 上下文，既昂贵又容易被无关信息干扰。

**方法**：设计选择性作用域的记忆（selectively scoped memory），把并行分支经验筛选成有用知识，供更高层的后续推理使用；实现探索与推理相互促进。

**论文报告**：在 MLE-bench 上报告 **29.3% 平均奖牌率**，并强调在 **12 小时预算**下得到该结果；不能与不同实验条件、不同模型版本或榜单时间的成绩直接对比。

**贡献**：为长运行 Agent 的“经验总结质量”提供研究切口：哪些失败模式值得存入长期记忆，哪些局部结果会污染全局决策？

<a id="s8-9"></a>

### 8.9 Agent K：结构化推理与长短期记忆的探索性路线

**文献**：Grosnit et al., *Large Language Models Orchestrating Structured Reasoning Achieve Kaggle Grandmaster Level*，2024 年 arXiv。[R34]

论文介绍 Agent K v1.0，强调结构化推理、长短期记忆与环境奖励驱动的经验更新，作为自动化数据科学竞赛策略的探索。标题中的“Grandmaster Level”是其论文主张，**不应自动推导为该 Agent 在开放真实世界里拥有 Kaggle Grandmaster 人类级别的全方位能力**。在进一步引用其结果前应核查任务集、竞赛时间与对照条件。

<a id="s8-10"></a>

### 8.10 横向比较：八类系统的真正贡献

| 研究 | 主体创新 | 反馈机制 | 搜索空间 | 主要适用问题 | 证据出处 |
|---|---|---|---|---|---|
| MLAgentBench | 标准化 ML 实验任务和评测 | 执行结果/目标阈值 | 代码与工具动作 | 能否完成 ML 实验 | [R20] |
| DS-Agent | 基于案例的经验检索与适配 | 开发阶段迭代反馈 | 方案/代码 | 提升规划合理性 | [R21] |
| AutoML-Agent | RAP、多 Agent、验证链 | 执行与实现检验 | 全流程任务计划 | 自然语言到模型成果 | [R22] |
| AutoKaggle | 工具箱、单测、调试、可干预 | 流水线验证/提交 | 数据科学工作流 | Kaggle 风格任务 | [R24] |
| Data Interpreter | 层次依赖图与逐步验证 | 步骤级检查 | 多步骤分析任务 | 复杂数据分析 | [R25] |
| AIDE | 代码空间的树搜索 | 子节点执行与指标 | 程序代码 | 机器学习工程改进 | [R26] |
| R&D-Agent | 研究/开发职责拆分 | 假设实现与评估 | 假设＋代码 | 长周期 ML 研发 | [R27] |
| ML-Master | 选择性作用域记忆 | 并行经验与结果整合 | 实验方案树 | 长期、多分支搜索 | [R33] |

**横向判断**：AutoML-Agent 更接近**端到端工作流架构**；AIDE 更接近**开放式候选代码优化器**；R&D-Agent 更接近**可检验的研究工作流管理器**；ML-Master 侧重**轨迹与记忆效率**。因此最好将它们看作可以部分组合的不同层面，而不是互相替代的单一排行榜候选。

---

<a id="s9"></a>

## 9. 2026 年的新进展：训练型 ML Agent

<a id="s9-1"></a>

### 9.1 ML-Agent（ICML 2026）：从 prompt 工程过渡到 policy learning

**文献**：Liu et al., *ML-Agent: Reinforcing LLM Agents for Autonomous Machine Learning Engineering*，ICML 2026。[R28]

**问题界定**：大量 ML Agent 依赖大闭源模型的推理能力。小模型难以从历史动作中泛化，闭源大模型调用又贵，随着任务和试验数扩大成本显著上升。

**主要方法（以正式摘要为准）**：

1. **Exploration-enriched Fine-tuning**：增强初始探索数据与行动多样性；
2. **Step-wise Reinforcement Learning**：在单步动作粒度构造训练，改善体验采集效率；
3. **ML-specific Reward Module**：把异质的训练反馈统一为可优化的奖励。

**论文披露**：以大约 **7B 的 Qwen-2.5** 为骨干，仅在 **9 个 ML 任务**训练，报告可达到与使用更大商业模型的部分 agent 相近的表现且计算成本更低。该主张取决于论文给定任务/资源/版本，并不意味着 7B 模型在所有通用软件工程任务上等效更大型闭源模型。

**为什么重要**：过去 AutoML 主要训练“预测模型”，LLM agent 主要在运行时决定实验；现在可把大量 **ML 实验轨迹直接作为训练 agent policy 的经验**，形成第二层的自动化。

**研究机会**：如何形成 reward？如果简单给 AUC 改进奖励，会鼓励验证集过拟合；若加入成本、安全、策略合法性和泛化，又面临 sparse reward 和信用分配问题。更稳健的目标可写为：

$$
r_t = \Delta q_{valid} - \lambda_c\cdot c_t - \lambda_r\cdot\mathrm{risk}_t - \lambda_v\cdot\mathrm{violations}_t
$$

其中设计 $\lambda$ 应经人工审核，并明确测试集不参与策略在线奖励。上式为本报告提出的设计示例，不是 ML-Agent 论文的原始公式。

<a id="s9-2"></a>

### 9.2 DeepAnalyze（ICML 2026）：从预制工作流到通用数据科学能力

**文献**：Zhang et al., *DeepAnalyze: Agentic Large Language Models for Autonomous Data Science*，ICML 2026。[R29]

**研究问题**：许多旧式数据 agent 强依赖预定义的工作流，在复杂、开放式数据研究任务中表现有限。能否训练模型在真实数据环境里逐步掌握自主分析工作？

**方法**：课程式训练，合成与真实数据绑定的高质量轨迹，覆盖从数据问答到开放式数据研究的不同技能层级；以更少参数的 agentic 模型承载跨任务工作流能力。

**论文披露**：在 **13 项 benchmark** 上，**8B 规模**的 DeepAnalyze 在作者的实验设定下优于基于更大型闭源模型的若干 workflow agents。注意“自主数据科学”比自动监督学习建模更广，不应直接将它的 benchmark 成绩换算成 AutoGluon 对比胜率。

**价值**：为全流程 Agent 训练提供了路径：不是无限增加 orchestrator 的提示词，而是学习“识别数据 → 计划动作 → 获取反馈 → 修正计划”的统一策略。

<a id="s9-3"></a>

### 9.3 2026 年应如何理解两条路线

| 维度 | ML-Agent | DeepAnalyze |
|---|---|---|
| 主要问题 | Autonomous ML Engineering | Autonomous Data Science |
| 训练突破 | 在线交互 RL、step-wise reward | 课程式 agentic 训练、数据轨迹合成 |
| 论文报告的骨干规模 | ~7B | ~8B |
| 重心 | 模型实验优化行动 | 数据处理、问答、研究报告的广泛任务 |
| 适用研究问题 | Agent 如何更高效选择下一试验 | Agent 如何泛化到复杂长流程任务 |
| 核心风险 | reward hacking / 样本效率 | 数据污染 / 任务间泛化 / 长链可靠性 |

**趋势性判断（报告观点）**：未来系统会把“可训练的实验策略”和“不可绕过的确定性评估器”结合。前者扩大探索效率，后者避免 reward hacking 与脆弱的视觉/语言评估。

<a id="s9-4"></a>

### 9.4 与 2026 年 AutoML 会议方向的联系

AutoML 2026 官方 Call for Papers 把 **Agentic AutoML**、**AutoML for Large Language Models and vice versa**、**Foundation Models for AutoML and vice versa** 明确列为方法轨道的主题方向。这印证它已成为学术会议积极接纳的方向，但这本身**并不证明相关系统已经成熟或具有统一性能领先性**。[R42]

<!-- 本页使用的引用定义；书目详情由对应资料索引维护。 -->
[R20]: https://proceedings.mlr.press/v235/huang24y.html "Huang et al. — MLAgentBench"
[R21]: https://proceedings.mlr.press/v235/guo24b.html "Guo et al. — DS-Agent"
[R22]: https://proceedings.mlr.press/v267/trirat25a.html "Trirat et al. — AutoML-Agent (ICML 2025)"
[R23]: https://github.com/DeepAuto-AI/automl-agent "AutoML-Agent — Official Implementation"
[R24]: https://mlanthology.org/iclrw/2025/li2025iclrw-autokaggle/ "Li et al. — AutoKaggle"
[R25]: https://aclanthology.org/2025.findings-acl.1016/ "Hong et al. — Data Interpreter"
[R26]: https://arxiv.org/abs/2502.13138 "Jiang et al. — AIDE"
[R27]: https://arxiv.org/abs/2505.14738 "Yang et al. — R&D-Agent"
[R28]: https://proceedings.mlr.press/v306/liu26i.html "Liu et al. — ML-Agent (ICML 2026)"
[R29]: https://proceedings.mlr.press/v306/zhang26aq.html "Zhang et al. — DeepAnalyze (ICML 2026)"
[R33]: https://arxiv.org/abs/2506.16499 "Liu et al. — ML-Master"
[R34]: https://arxiv.org/abs/2411.03562 "Grosnit et al. — Agent K"
[R42]: https://2026.automl.cc/call-for-papers/ "AutoML 2026 — Call for Papers"
[R31]: https://github.com/openai/mle-bench/ "OpenAI — MLE-bench Official Repository & Leaderboard"
