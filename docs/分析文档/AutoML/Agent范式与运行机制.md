# Agent for AutoML 的范式与运行机制

> 整理日期：2026-10-25。原文整理；未新增文献核验或实验结果。原章节编号保留，便于核对旧稿。

[文档导航](../../README.md) · [原稿章节对照](../../整理说明.md)

与经典优化器的分工见[分工分析](传统AutoML与Agent的分工.md)，代表论文见[相关工作](../../相关工作/AutoML/Agent代表论文.md)。五种范式与六条主线来自不同分析维度，下面分别保留其原始分类。

---

> 来源：`AutoML_Agentic_AutoML_Research_Report_2026-10-22_v3_AutoResearch_Ecosystem.md`；2026-10-22 V3。

<a id="s7"></a>

## 7. Agent for AutoML 的定义、范式与架构

<a id="s7-1"></a>

### 7.1 Agent 的最小闭环

一个可运行的 ML Agent 不等于“使用了 LLM”。最低结构应为：

```text
Observe（任务、数据模式、已有结果）
  ↓
Plan（下一步可执行且有预算的动作）
  ↓
Act（调用探查工具、训练器、评估器或代码执行器）
  ↓
Validate（由工具计算真实反馈及错误）
  ↓
Reflect / Update State（保留成功/失败经验，调整假设）
  ↺
```

上述闭环可追溯到 ReAct 与 Reflexion 等通用语言 Agent 思路，但其迁入 AutoML 时，**真实实验的计算成本、验证集统计偏差和数据安全**使问题显著更复杂。[R35]–[R36]

<a id="s7-2"></a>

### 7.2 研究范式分类：六条主线

| 范式 | 决策对象 | 代表工作 | 强项 | 弱点 |
|---|---|---|---|---|
| 自然语言包装器 | AutoML API 与默认 preset | 轻量 LLM+AutoML Demo | 易用和快速交付 | 研究贡献有限 |
| 工具编排与计划生成 | 数据处理/模型训练工作流 | AutoML-Agent | 全流程、模块分工 | 编排可靠性与成本 |
| 检索与案例推理 | 类似任务的已知方案 | DS-Agent | 快速迁移、减少凭空规划 | 经验库质量与迁移误差 |
| 代码空间树搜索 | 代码补丁和实验分支 | AIDE | 能跳出静态超参空间 | 代码风险、搜索成本 |
| 研究/开发双层循环 | 高层假设与实现任务 | R&D-Agent、ML-Master | 反思和经验累积 | 真实归因、复杂状态管理 |
| 训练型 Agent Policy | 状态到行动的决策策略 | ML-Agent、DeepAnalyze | 可能降低推理成本、跨任务迁移 | 环境数据采集、奖励设计、OOD |

<a id="s7-3"></a>

### 7.3 单 Agent 与多 Agent

**单 Agent + 工具**：上下文统一、易追踪、成本低，适合固定预算与标准表格任务。但任务过长可能出现上下文拥堵、错误复用和策略漂移。

**多 Agent**：按 Planner、Data Agent、Feature Agent、Model Agent、Code Agent、Evaluator 分工，可并行探索或实现专业角色。但 agent 数量增加会提升 token 成本、通信延迟、相互矛盾和责任归因难度。

**架构决策原则**：只有当任务之间有明确的数据/工具边界、可以并行或具有独立的验收准则时，多 Agent 才有实际收益。一个 LLM 多次角色扮演不自动等于更强的模型能力。

<a id="s7-4"></a>

### 7.4 一套实用的状态机

```text
TASK_RECEIVED
   │
   ▼
POLICY_CHECK ──不合规──► REJECT / REQUEST_APPROVAL
   │
   ▼
DATA_PROFILE ──错误──► RECOVER_OR_ESCALATE
   │
   ▼
VALIDATION_DESIGN ──不可证伪──► HUMAN_REVIEW
   │
   ▼
BASELINE_FIT ──失败──► DIAGNOSE / FALLBACK
   │
   ▼
PLAN_CANDIDATES → EXPERIMENT_QUEUE → EVALUATE
                            ▲                 │
                            └─ FEEDBACK ←─────┘
                                                │
                                        BUDGET_OR_GOAL_MET
                                                │
                                                ▼
                                       FINAL_TEST / AUDIT
                                                │
                                                ▼
                                       REGISTER / APPROVAL
                                                │
                                                ▼
                                          DEPLOY / MONITOR
```

**原则**：最终测试集不在开放式反馈循环中；试验失败可以继续，但泄漏和权限违规应立即终止或转人工。

<a id="s7-5"></a>

### 7.5 Agent 的行动空间如何定义

| 层级 | 可用动作 | 校验方式 |
|---|---|---|
| 数据 | `inspect_schema`、`profile_missingness`、`detect_target_leakage` | 只读、审计日志、schema |
| 实验 | `create_split`、`register_baseline`、`propose_trial` | split policy、预算、参数边界 |
| 计算 | `run_trial`、`resume_trial`、`cancel_trial` | 容器隔离、资源配额、超时 |
| 诊断 | `fetch_metrics`、`compare_runs`、`inspect_errors` | 结构化返回、不显示测试标签 |
| 知识 | `retrieve_prior_runs`、`write_hypothesis` | 权限隔离、元数据溯源 |
| 交付 | `register_model`、`request_deploy` | 验收门槛、人类审批 |

在严格生产系统中，尽量让 Agent 调用**类型化工具 API**，而不是向 shell 发送不受约束的命令。自由写代码可在隔离实验环境试验，不宜默认具有外部网络、系统凭据、真实生产数据写入能力。

<a id="s7-6"></a>

### 7.6 记忆类型与数据结构

建议区分：

- **Working Memory**：当前任务假设、剩余预算、最优候选、失败的分支；
- **Episodic Memory**：以 experiment ID 为键的实验轨迹、错误、修复方式、指标；
- **Semantic Memory**：算法知识、文档、训练经验总结、模型适用边界；
- **Meta-Memory**：哪些记忆在什么类型的任务中实际帮助了选择。

只存文字摘要容易产生“结论无法验证”的问题。核心记录应保留源码/commit、数据快照标识、split seed、超参、环境镜像 digest、运行产物及评测程序版本。

---

> 来源：`AutoML与Agent-AutoML调研.md`；2026-10-20 摘要级调研。

<a id="q3"></a>

## 3. Agent for AutoML 的五种范式

| 范式 | 代表工作 | 机制 | 已有证据 | 主要失效模式 |
|---|---|---|---|---|
| **P1 LLM 当搜索算子** | LLAMBO `2312.04528`、AgentHPO `2402.01881`、Optuna vs Code Llama `2504.06006` | 用数据集/模型描述提示 LLM 直接提配置，按历史迭代 | 小预算下宣称匹配或超过 BO；微调小模型可降低算力 | 增益多来自热启动先验；跨 trial 状态跟踪差；易 OOM（§4） |
| **P2 LLM 做代码级管线搜索** | AIDE `2502.13138`、SELA `2410.17238`、I-MCTS `2502.14693`、AutoML-Agent `2410.02958`(ICML'25)、MLE-STAR `2506.15692`、R&D-Agent `2505.14738`、MLZero `2505.13941`、iML `2602.13937` | 把方案表示成可执行代码，用树搜索/多 agent/消融定位做迭代 | MLE-bench 类基准上铜牌级比例、金牌数等结果级指标 | 结果级指标掩盖方法学错误；harness 复杂度未必带来增益（§4） |
| **P3 LLM 造空间、经典器搜索** | Agentic Search Spaces `2609.16309`、AgentNAS `2607.07984`、NOVA `2606.27243` | agent 生成模块候选/带槽脚手架 → 有界空间 → HPO/NAS 联合优化 | 45 数据集 +0.6%（小中型回归 2.0%）；17 任务三阶段可单独归因 | 依赖经典优化器的可靠性与预算执行 |
| **P4 LLM 当评估者/审计者** | Evaluation Agent `2602.22442`、Silent Failures `2610.14115`、MLE-InsightBench `2610.04927` | 旁观式评估中间决策、构造可控失效测试、控制洞见来源 | 故障决策检测 F1 0.919；220 任务失效模式统计 | 评估者本身也是 LLM，需要独立校准 |
| **P5 端到端 AI 科学家** | MLR-Bench `2505.19955`、RE-Bench `2411.15114`、FunSearch(Nature 2023)、AlphaEvolve `2506.13131` | 想法→实验→写作全链路；或"提议 + 自动评估器 + 进化" | RE-Bench：61 位专家 71 次 8h 尝试，82% 非零、24% 达强参考解 | 评测与真实科研价值之间的鸿沟；评审依赖 LLM |

**范式差异的要点**：P1/P2 的收益是**在给定空间内搜得更好**；P3 的收益是**把空间本身做大但仍有界**；P4 的收益是**让前三种可被审计**。P2 是当下论文最拥挤的一格，P3 和 P4 才是空白较多的位置。

---

<!-- 本页使用的引用定义；书目详情由对应资料索引维护。 -->
[R35]: https://mlanthology.org/iclr/2023/yao2023iclr-react/ "Yao et al. — ReAct"
[R36]: https://mlanthology.org/neurips/2023/shinn2023neurips-reflexion/ "Shinn et al. — Reflexion"
