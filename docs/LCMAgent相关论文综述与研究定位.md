
# BS/UE 双 Agent 相关论文综述与研究定位

## 1. 文档目的

本文围绕同目录下的《BS-UE 双 Agent 协同分析与设计》，整理与以下问题直接相关的论文和论文型材料：

1. 无线网络中的 LLM Agent 如何感知状态、规划工作流、调用工具和执行动作。
2. 网络侧 Agent 如何处理证据不足、动作不可执行、配置冲突和运行时退化。
3. 无线 AI/ML 模型，特别是 CSI 等端网协作模型，如何处理模型位置、资源约束、数据分布变化和模型效果。
4. 现有工作是否已经覆盖 BS 全局 Agent 与 UE 本地 Runtime 共同完成模型评估、配对激活、监测、切换和回退。

本文不是无线 Agent 文献的系统综述，也不把所有出现“Agent”“LLM”或“AI”的论文都视为同类工作。重点是判断现有机制哪些可以吸收到 BS/UE 双 Agent 设计中，哪些只能作为背景，哪些会误导研究问题。

本文的分析截至 **2026 年 10 月 19 日**。论文的出版状态按可核验的论文首页、PDF 元数据、会议/期刊信息或公开预印本记录区分。未能确认正式出版状态的材料不计入“已发表论文”结论。

## 2. 先给结论

### 2.1 直接相关的正式出版论文很少，但局部机制已经存在

本地材料中可以确认与本设计直接相关的正式出版论文主要包括：

| 论文 | 出版状态 | 对本设计最有价值的部分 |
|---|---|---|
| Mfula and Nurminen, *Adaptive Root Cause Analysis for Self-Healing in 5G Networks* | IEEE HPCS 2017 正式会议论文 | 证据驱动的故障检测、概率化根因诊断、动作后 KPI 验证和持续学习 |
| Wu et al., *LLM-Driven Agentic AI Approach to Enhanced O-RAN Resilience in Next-Generation Networks* | IEEE INFOCOM Workshops 2025 正式 workshop 论文 | 网络切片资源管理、LLM Agent 与 O-RAN/xApp 的结合、动态场景中的韧性目标 |
| Fang et al., *OnlineCritic-xApp: Online Learning for LLM-Assisted RAN Slice Resource Management* | IEEE INFOCOM 2026 正式会议论文 | LLM 只提出候选动作，轻量在线 Critic 和确定性可行性门负责筛选与回退 |

这些论文证明了“无线网络中使用 Agent 或 LLM，并把输出放进受约束控制环”是可研究、可实验的方向，但它们并没有完整实现本文关注的端网双侧模型生命周期。

### 2.2 预印本已经覆盖了不少单侧机制

WirelessAgent、WirelessAgent++、WirelessOpsAgent、Net Analyzer rApp、Agentic AI for ISAC、LLM CSI Feedback 等材料分别覆盖了：

- 无线任务的感知、记忆、规划和工具调用；
- 自动工作流搜索和工作流基准；
- 动作证据、执行契约、故障修复和 Unsafe APPLY 控制；
- O-RAN 非实时 RIC 中的事件分析、工具门控和人工审批；
- ISAC 中的意图到工作流映射；
- LLM 参与 CSI 压缩/重建模型的数值建模。

因此，单纯提出“一个带工具的无线 LLM Agent”“一个带安全门的工作流 Agent”或“一个使用 LLM 的 CSI 模型”都不足以构成 BS/UE 双 Agent 研究的核心新意。

### 2.3 仍然缺少的组合问题

从已阅读的论文看，尚未发现一篇材料同时把以下内容作为一个可执行的端网协同问题来处理：

```text
BS 全局 Agent
    观察多 UE/多小区状态，规划模型评估、数据采集和版本切换

UE 本地 Runtime
    在本地数据、内存、功耗、版本和安全约束下确认是否可运行

结构化模型生命周期协议
    共同准备、共同激活、版本配对、监测、回退和事务一致性

确定性执行门
    阻止未经验证、过期、越权或资源超预算的动作
```

因此，本文设计仍有研究空间，但研究贡献不能只写成“BS 和 UE 各放一个 Agent”。真正需要验证的是：在端网信息不完整、设备异构、数据不能全部上传的条件下，分层双侧协同是否能减少错误发布、切换失败和不必要的数据采集，同时不超过可接受的通信、推理和设备开销。

## 3. 文献范围与证据分层

### 3.1 本地材料来源

本次主要使用 `/Users/z-jiuri/workspace/AI4WC/方向文档/reference/pdfs/` 中的 PDF，以及本地已有的文献阅读索引。重点文件包括：

- `2505.01074.pdf`：WirelessAgent。
- `2603.00501.pdf`：WirelessAgent++。
- `2608.08277.pdf`：WirelessOpsAgent。
- `2603.13775.pdf`：LLM-Based Net Analyzer rApp。
- `2501.10630.pdf`：LLM for Massive MIMO CSI Feedback。
- `2512.15044.pdf`：Agentic AI for ISAC。
- `OnlineCritic-xApp_Online_Learning_for_LLM-Assisted_RAN_Slice_Resource_Management.pdf`。
- `LLM-Driven_Agentic_AI_Approach_to_Enhanced_O-RAN_Resilience_in_Next-Generation_Networks.pdf`。
- `Adaptive_Root_Cause_Analysis_for_Self-Healing_in_5G_Networks.pdf`。
- `ORCA_INFOCOM26.pdf`。

### 3.2 状态分类

本文使用以下三种状态：

| 状态 | 含义 | 使用方式 |
|---|---|---|
| 正式出版 | PDF 或元数据明确给出会议/期刊、年份和 DOI 或正式出版标识 | 可以作为已发表论文证据，但仍需区分期刊、正式会议和 workshop |
| 公开预印本 | 具有 arXiv 标识或公开预印本版本，但没有在本轮材料中确认正式会议/期刊出版 | 可以分析方法，不写成已发表论文 |
| 本地稿件/状态未核验 | 本地 PDF 存在，但不能仅凭文件名确认会议录、期刊或 DOI | 只作为候选工作或补充阅读，不能用于“已有正式工作证明”的断言 |

### 3.3 重要边界

- 标准文件不是论文，不列入论文统计。
- 内部 `claude_results`、`agent_projects` 和设计文档不是外部文献证据，只用于理解研究问题。
- arXiv 版本中的实验结果可以用于方法比较，但不能自动写成同行评审结论。
- 单篇论文的实验环境、调用时延、模型能力和数据集不能直接移植为本项目的预期收益。

## 4. 论文总览

### 4.1 正式出版论文

| 编号 | 论文 | 年份/载体 | 主要对象 | 与 BS/UE 设计的关系 | 可吸收机制 |
|---|---|---|---|---|---|
| P01 | Harrison Mfula, Jukka K. Nurminen, “Adaptive Root Cause Analysis for Self-Healing in 5G Networks” | 2017, IEEE International Conference on High Performance Computing & Simulation | LTE-A/5G 网络故障和自愈 | 不涉及 LLM 或 UE 本地 Agent，但提供成熟的诊断-动作-验证闭环 | 概率化证据、缺失数据处理、动作后 KPI 验收、持续更新 |
| P02 | Xingqi Wu, Yuhui Wang, Junaid Farooq, Juntao Chen, “LLM-Driven Agentic AI Approach to Enhanced O-RAN Resilience in Next-Generation Networks” | 2025, IEEE INFOCOM Workshops | O-RAN 切片资源管理和韧性 | 网络侧 LLM/xApp，偏资源分配，不处理 UE 模型配对 | 把 Agent 输出绑定到无线业务 KPI 和韧性目标 |
| P03 | Zhou Fang, Shuping Dang, Zhenrong Zhang, Yan Zhang, “OnlineCritic-xApp: Online Learning for LLM-Assisted RAN Slice Resource Management” | 2026, IEEE INFOCOM | O-RAN xApp 和非平稳切片控制 | 只在网络侧闭环，但与“Agent 提案 + 确定性安全门”高度相关 | 候选动作、轻量 Critic、实时测量反馈、预算修复和安全回退 |

P02 的本地 PDF 元数据给出 DOI `10.1109/INFOCOMWKSHPS65812.2025.11152722`。P03 的本地 PDF 元数据给出 DOI `10.1109/INFOCOM59046.2026.11571592`。P01 的本地 PDF 明确标出 IEEE HPCS 2017 和论文题名，但本轮不额外推断未在本地材料中明确显示的 DOI。

### 4.2 公开预印本和方法近邻

| 编号 | 论文 | 状态 | 主要贡献 | 本文使用方式 |
|---|---|---|---|---|
| P04 | Jingwen Tong et al., “WirelessAgent: Large Language Model Agents for Intelligent Wireless Networks” | arXiv 预印本，2505.01074 | 感知、记忆、规划、行动四模块；LangGraph 工作流；网络切片案例 | 用于定义网络 Agent 的基本能力，不把四模块直接当成双侧架构 |
| P05 | Jingwen Tong et al., “WirelessAgent++: Automated Agentic Workflow Design and Benchmarking for Wireless Networks” | arXiv 预印本，2603.00501 | 将工作流表示为可执行代码，用 MCTS 搜索工作流，并提出 WirelessBench | 用于工作流搜索和基准设计；不能代替模型生命周期协议 |
| P06 | Zijian Lu et al., “WirelessOpsAgent: A Benchmark and Agent Design for Action Assurance in Wireless Networks” | arXiv 预印本，2608.08277 | WirelessOptBench、执行契约、证据检查、可修复支持失败和 Unsafe APPLY 控制 | 是当前最接近动作安全门的近邻，但仍以无线网络操作为对象，不是端网模型事务 |
| P07 | Tuan V. Ngo et al., “LLM-Based Net Analyzer rApp for Explainable and Safe Automation in O-RAN Non-RT RIC” | arXiv 预印本，2603.13775 | 事件触发、批处理推理、日志工具、配置工具、人工批准、O-RAN 测试床 | 用于说明推理和执行应分离，并把审批/工具门纳入系统边界 |
| P08 | Wenwen Xie et al., “Agentic AI for ISAC: Analysis, Framework, and Case Study” | arXiv 预印本，2512.15044 | ISAC 的 Agentic AI 分析、框架和案例 | 用于说明 Agent 可以位于高层任务和资源优化环，但不作为双侧 LCM 证据 |
| P09 | Yiming Cui et al., “Exploring the Potential of Large Language Models for Massive MIMO CSI Feedback” | arXiv 预印本，2501.10630 | 预训练 LLM 参与 CSI 压缩/重建，使用预处理、嵌入、冻结 LLM 和后处理 | 用于 CSI 用例的模型位置、资源和泛化讨论；不是 Agent 协同论文 |
| P10 | Dae Cheol Kwon, Xinyu Zhang, “Open RAN Conflict Agents: Detecting and Mitigating xApp Conflicts with Generative Agents” | 本地稿件，文件名含 INFOCOM26，但正式出版状态未在本轮核验 | 用生成式 Agent 分析 xApp 控制冲突，结合符号推理和检索 | 只能作为冲突管理候选机制，不写成已发表证据 |

### 4.3 相关但不纳入核心结论的材料

`2609.06174.pdf`、`2609.27337.pdf`、`2607.16269.pdf`、`2604.19599.pdf`、`LLM-Driven_Agentic_AI_Approach...pdf` 等材料可以帮助理解自动研究、可检查 xApp、ISAC 编译器和闭环推理，但其中若为预印本、概念稿或未核验会议版本，只能用于方法启发。本文不把它们合并进“正式出版论文数量”，也不据此宣称相关方向已经被完整解决。

## 5. 正式出版论文详解

### 5.1 P01：Adaptive Root Cause Analysis for Self-Healing in 5G Networks

#### 5.1.1 论文解决什么问题

论文针对蜂窝网络故障检测和根因分析，使用网络测量、告警、配置和 KPI 等信息进行自动诊断。其核心不是生成自然语言，而是把故障诊断转化为可解释的概率推理问题，并在纠正动作后继续通过 KPI 判断动作是否有效。

#### 5.1.2 可吸收到双 Agent 设计的机制

1. **证据不是附属信息**：诊断结论必须有测量、配置或告警证据支撑。
2. **允许信息不完整**：网络运行中很难得到完整观测，系统应显式表示不确定性，而不是强迫 Agent 给出确定结论。
3. **动作后再次验证**：完成切换、更新或修复后，必须检查目标 KPI 是否恢复。
4. **知识持续更新**：历史故障和动作效果可以进入后续诊断，但更新过程需要可审计。

#### 5.1.3 对 BS/UE 双 Agent 的直接启示

BS Agent 可以负责跨 UE 的异常归因和补测规划；UE Runtime 可以报告本地可验证事实，例如当前模型版本、输入数据质量、内存余量、推理时延、功耗状态和本地 KPI。二者结合后，模型切换不应只有“切换成功/失败”两种状态，而应记录：

```text
触发证据 -> 候选动作 -> 本地约束检查 -> 激活结果 -> 运行 KPI -> 是否确认有效
```

#### 5.1.4 不能直接照搬的内容

- 论文的贝叶斯诊断框架不能自动替代 LLM Agent。
- 网络故障 RCA 的标签、故障拓扑和 KPI 不能直接当作 AI/ML 模型 LCM 的数据结构。
- 论文中的实验准确率不代表双 Agent 的模型发布准确率。

### 5.2 P02：LLM-Driven Agentic AI Approach to Enhanced O-RAN Resilience

#### 5.2.1 论文解决什么问题

论文面向 O-RAN 网络切片资源管理，利用 LLM-driven Agent 处理动态服务需求和资源分配问题，并在 OAIC 测试床上评估平均数据率、切片可靠性和系统响应性。

#### 5.2.2 可吸收机制

- Agent 的目标应以无线业务结果表述，而不只是语言任务正确率。
- 资源分配问题必须同时考虑吞吐量、可靠性和响应时间。
- Agent 需要面对非平稳流量和无线环境，静态离线策略不能作为唯一基线。
- O-RAN 的 xApp/rApp 形态说明网络侧 Agent 可以嵌入现有控制栈，而不必直接替代底层控制器。

#### 5.2.3 对本文设计的限制性启示

这类工作主要位于网络侧，UE 通常被抽象为业务需求、切片流量或观测对象。它没有解决：

- UE 能否运行某个模型；
- UE 是否允许上传某类本地数据；
- BS 与 UE 的模型版本是否配对；
- 一端激活成功、另一端失败时如何回退；
- 模型切换后由哪一侧确认端到端 KPI。

因此，O-RAN Agent 不能直接等同于 BS/UE 双 Agent。它更适合作为 BS Agent 的网络侧实现参考。

### 5.3 P03：OnlineCritic-xApp

#### 5.3.1 论文解决什么问题

论文研究非平稳无线信道和流量变化下的 O-RAN 切片资源管理。LLM 生成少量候选分配方案，但不直接决定最终动作；系统通过实时测量训练轻量在线 Critic，对候选方案重新排序，并用确定性预算检查和安全回退保证可执行性。

#### 5.3.2 对双 Agent 设计最重要的启示

P03 直接支持以下设计原则：

```text
LLM/Agent：提出候选策略
在线 Critic：根据实时测量评估候选策略
确定性检查器：检查资源预算和动作格式
安全回退：候选无效或质量不足时保持可运行策略
```

这个分工比“让 LLM 直接下发动作”更适合作为 BS/UE 协同的基础。对应到本文：

- BS Agent 可以提出模型切换、补测或数据采集候选方案。
- Evaluation Engine 或轻量 Critic 根据实验和运行反馈评估候选方案。
- UE Runtime 负责本地能力、版本、资源和隐私检查。
- Deterministic Execution Gate 决定是否放行。
- Fallback Controller 保证 Agent 不可用时系统仍然可运行。

#### 5.3.3 不能直接照搬的内容

- P03 的动作是 PRB 分配，不是模型版本事务。
- 其在线 Critic 的输入和反馈周期不能直接当作 UE 模型运行监测周期。
- “LLM 每个控制周期最多调用一次”的设定属于其具体实验约束，不应未经测量移植到本项目。

## 6. 预印本和方法近邻详解

### 6.1 P04：WirelessAgent

WirelessAgent 将无线 Agent 分为感知、记忆、规划和行动四个模块，并使用外部工具、知识库和工作流处理网络切片等任务。它说明无线 Agent 的核心不应是裸 LLM，而应是能访问多模态状态、历史记忆和领域工具的工作流系统。

对本文有三点价值：

1. **感知和行动必须模块化**：BS Agent 应通过结构化状态和工具得到观测，不应依赖自然语言描述中的隐含事实。
2. **工作流需要明确角色和阶段**：模型评估、准备、激活、监测和回退可以定义成不同工作流节点。
3. **多模态数据需要适配层**：CSI、无线测量和设备资源状态不能直接假设 LLM 原生理解，应先经专用编码、统计摘要或工具处理。

它没有提供 BS/UE 双侧事务，也没有解决 UE 本地隐私、设备能力和模型配对。因此，本文只吸收其“Agent = LLM + 记忆 + 工具 + 工作流”的系统观，不把它作为端网双 Agent 的完整方案。

### 6.2 P05：WirelessAgent++

WirelessAgent++ 把 Agentic Workflow 表示成可执行代码，并使用面向无线任务的 MCTS 搜索工作流，还构建了覆盖知识推理、工具使用和多步决策的 WirelessBench。

对本文的启示是：

- 工作流本身可以成为可比较、可搜索和可复现实验对象。
- Agent 的提升不应只通过单个任务答案评估，还要测量多步决策、工具调用和约束满足。
- 双 Agent 研究可以把“是否需要 UE 参与”“何时补测”“何时切换模型”等作为工作流决策，而不是把双侧固定成两个永远同时工作的 LLM。

但 WirelessAgent++ 的工作流搜索不能代替模型 LCM 协议。协议中的版本、权限、证据、事务和回退条件仍应由固定 schema 和确定性检查器约束。

### 6.3 P06：WirelessOpsAgent

WirelessOpsAgent 关注一个关键问题：提案阶段看起来正确的无线动作，在执行时可能因为证据过期、状态冲突或依赖不满足而变得不安全。它提出 WirelessOptBench，将无线任务转化为带执行状态、证据新鲜度、依赖顺序、资源冲突和可用性约束的动作决策，并在可修复的支持失败后重新验证。

这与本文的模型发布问题高度相似：候选模型可能在离线评估中表现良好，但在实际 UE 上可能存在版本不一致、输入契约不满足、内存不足、功耗策略禁止、适用场景不成立或本地证据过期等问题。

可直接吸收的设计：

| WirelessOpsAgent 机制 | BS/UE 模型生命周期对应物 |
|---|---|
| execution contract | 模型输入输出、版本、能力和资源契约 |
| evidence freshness | 设备能力、运行 KPI、模型状态和数据质量的有效期 |
| dependency/order | 先安装权重、再校验、再准备、最后共同激活 |
| repairable support failure | 补采本地摘要、重新协商版本或降低模型配置 |
| Unsafe APPLY Rate | 错误发布率、单侧激活率、无效切换率 |
| safe progress | 在无法升级时保持旧模型或传统算法运行 |

需要注意的是，WirelessOpsAgent 的动作安全是网络运维动作安全；本文需要进一步证明端网模型事务中的版本配对和本地状态约束是否能形成新的可测量问题。

### 6.4 P07：LLM-Based Net Analyzer rApp

Net Analyzer rApp 将 LLM 放入 O-RAN Non-RT RIC，采用事件触发、批处理推理、日志/配置工具、人工批准和最终状态验证的流程。其明确强调推理和执行分离，LLM 不直接接触实时系统，也不直接执行自由格式动作。

这支持本文的四个边界：

1. BS Agent 可以承担慢速网络分析和生命周期编排，但不进入时隙级控制环。
2. 工具调用应有范围、参数和返回 schema。
3. 高风险动作需要执行前批准或等价的确定性门控。
4. 动作完成后必须回到可观测状态，验证系统是否达到预期。

该工作是网络侧运维自动化，不能证明 UE 侧需要完整 LLM，也不能证明双侧模型事务已经被解决。

### 6.5 P08：Agentic AI for ISAC

Agentic AI for ISAC 讨论把 Agentic AI 用于感知通信一体化系统的任务理解、资源优化和案例验证。它的价值主要在于说明无线 Agent 可以参与多目标任务和动态环境决策，而不是只做网络运维。

对本文的限制性启示是：ISAC、CSI、波束管理和切片管理都可以作为用例，但它们不自动构成同一个模型生命周期问题。每个用例必须单独定义：

- 模型在 UE、BS 还是两侧；
- 输入输出和模型版本如何配对；
- 哪些 KPI 属于模型层、链路层和系统层；
- 本地数据是否能离开 UE；
- 失败后是否能切回传统算法。

### 6.6 P09：LLM for Massive MIMO CSI Feedback

CSI 论文把预训练 LLM 用于 CSI 压缩/重建，设计了预处理、嵌入、冻结 LLM 和后处理模块，并在 QuaDRiGa 生成的 3GPP UMi LOS 场景上使用 NMSE、GCS 和场景泛化进行评估。

它对本文的价值不在于“CSI 应该使用 LLM”，而在于暴露了模型部署所必须面对的实际问题：

- CSI 是高维数值输入，必须经过专门的表示适配；
- 大模型参数量和推理成本会影响 UE 侧可部署性；
- 训练/验证场景与保留场景之间存在分布偏移；
- 只看 NMSE 不足以证明反馈开销、链路性能、吞吐量和设备成本上的端到端收益；
- UE 与 BS 之间可能需要成对的编码、反馈和重建模型。

这正是本文选择 CSI 作为示例而不把 CSI 作为固定锚点的原因。CSI 适合展示端网模型配对，但不能预先假定它一定是最适合验证双 Agent 价值的唯一用例。

## 7. 主题综合

### 7.1 无线 LLM Agent：已经有“规划和工具”，缺少“端网共同状态”

WirelessAgent 系列和 Net Analyzer rApp 说明网络 Agent 的典型能力包括：

- 读取结构化或多模态状态；
- 选择工作流；
- 调用日志、仿真、配置和评估工具；
- 生成候选动作或解释；
- 在执行前进行审批或安全检查；
- 在执行后检查结果。

但这些工作通常把环境看成网络侧可观测对象。UE 侧更多是被控制设备或数据源，而不是拥有独立本地约束、隐私策略、模型版本和快速回退能力的协同实体。

### 7.2 O-RAN Agent：已有网络侧位置，不等于 BS/UE 双侧位置

O-RAN 的 rApp/xApp 架构适合承载 BS/gNB 侧 Agent，尤其是非实时的模型评估、配置建议、资源管理和故障分析。它解决的是网络侧控制应用如何接入 RIC 和现有接口，而不是端网模型如何共同激活。

因此，在本文设计中：

- BS Agent 可以参考 rApp/xApp 的部署位置和工具边界。
- UE Runtime 不应被强行映射为一个 xApp。
- BS-UE 协议需要单独定义，不能假定 O-RAN 控制接口已经提供模型配对事务。

### 7.3 在线 Critic 和安全门：是已有可复用基线，不是本文全部创新

OnlineCritic-xApp 和 WirelessOpsAgent 都说明了一个可靠模式：

```text
生成/规划组件 != 最终执行组件
```

本文应该直接采用这一模式，把 LLM Agent 限制在候选方案生成、证据组织、补测规划和慢速决策上。最终放行仍由：

- schema 校验；
- 版本兼容性检查；
- UE 本地资源和隐私检查；
- 评估阈值检查；
- 权限和状态检查；
- 回退路径检查；

共同决定。

### 7.4 CSI/ISAC 论文：提供用例和指标，不提供生命周期方案

CSI 和 ISAC 论文可以帮助选择模型输入输出、场景和指标，但不能替代：

- 模型注册；
- 模型卡和证据对象；
- 配对关系；
- 共同准备与共同激活；
- 运行时监测；
- 模型切换和回退。

因此，CSI 在本文中应保持为一个用例，而不是架构锚点或唯一研究贡献。

## 8. 与现有 BS/UE 双 Agent 设计的差异矩阵

| 能力/问题 | 现有代表性工作 | 本设计状态 | 是否需要新研究 |
|---|---|---|---|
| 无线任务感知、记忆、规划、行动 | WirelessAgent | BS Agent 已包含，工具接口需结构化 | 不是单独创新点 |
| 自动工作流搜索 | WirelessAgent++ | 可用于补测和切换流程生成 | 需要限定搜索空间并做消融 |
| 执行证据和动作契约 | WirelessOpsAgent | 迁移到模型契约和端网事务 | 需要定义模型场景下的新证据对象 |
| 工具门控和人工批准 | Net Analyzer rApp | 保留为高风险操作门 | 可作为安全基线，不应宣称原创 |
| 网络侧资源管理 | O-RAN Resilience、OnlineCritic-xApp | 可作为 BS 侧用例 | 不是双 Agent 独有问题 |
| xApp/rApp 冲突 | ORCA 候选工作 | 可扩展到多 UE/多模型冲突 | 需要正式验证后再写入核心贡献 |
| CSI 数值重建 | LLM CSI Feedback | 作为用例和模型层基线 | 需要补上端到端 KPI 和部署成本 |
| 根因诊断和动作后验证 | Adaptive RCA | 作为监测和验收机制 | 应映射到模型退化和切换失败 |
| UE 本地隐私/资源/版本检查 | 现有材料覆盖不足 | UE Runtime 的核心职责 | 是双侧架构的重要研究空间 |
| BS-UE 模型配对事务 | 现有材料覆盖不足 | 由结构化协议和状态机处理 | 是最直接的研究空白 |
| 端网共同激活与回退 | 现有材料覆盖不足 | 作为核心实验对象 | 需要定义新指标和故障注入 |

## 9. 对现有设计文档的具体保留与修改建议

### 9.1 应保留的核心结构

现有设计中的以下内容与论文证据一致，应继续保留：

1. BS 侧采用全局 Agent，负责跨 UE 的慢速规划和生命周期编排。
2. UE 侧采用轻量 Runtime，不要求部署完整 LLM。
3. 实时控制和紧急回退不依赖 LLM。
4. LLM 只能通过结构化工具和 schema 访问系统。
5. 模型切换采用共同准备、共同激活和失败回退。
6. 证据对象、模型卡、数据血缘和运行监测属于核心系统对象。
7. 单侧模型是强基线，双侧模型是需要证明端到端价值的扩展。
8. CSI 只是示例用例，系统设计应适用于其他具有明确输入输出契约的无线 AI/ML 功能。

### 9.2 应避免夸大的表述

建议在所有后续版本中避免以下表述：

- “首次提出无线双 Agent 架构”。已有无线 Agent、O-RAN Agent 和多 Agent 近邻，不能只凭组件命名宣称首次。
- “LLM 负责安全执行”。已有论文明确把 LLM 与确定性门、在线 Critic、人工批准或安全回退分开。
- “Agent 可以直接理解 CSI”。CSI 论文恰好说明需要预处理、嵌入和专用数值适配。
- “联邦学习和差分隐私是第三章已经规定的实现”。它们可作为扩展，但不能写成现有标准的强制方案。
- “双 Agent 一定优于单 Agent”。必须用错误发布、切换失败、本地开销和业务 KPI 做对照实验。

### 9.3 建议补强的三个地方

#### A. 把“Agent 分工”改写成可检验的控制变量

至少比较以下四种配置：

| 配置 | BS 侧 | UE 侧 | 研究用途 |
|---|---|---|---|
| B0 | 传统规则/优化器 | 传统本地检查 | 非 Agent 基线 |
| B1 | 单 BS Agent | UE 被动执行 | 单侧 Agent 基线 |
| B2 | BS Agent | UE 确定性 Runtime | 推荐最小双侧方案 |
| B3 | BS Agent | UE 轻量模型/Agent | 受控双侧模型扩展 |

不要把 B3 作为默认方案。若 B2 已经获得大部分收益，B3 只增加成本而没有明显收益，应选择 B2 作为最终架构。

#### B. 把“安全”落到动作级指标

建议至少记录：

- Unsafe APPLY Rate：不满足证据或资源约束却被放行的比例；
- Version Mismatch Rate：BS 与 UE 模型版本或配置不一致的比例；
- Partial Activation Rate：一侧激活成功、另一侧失败的比例；
- Rollback Success Rate：失败后恢复到可运行旧版本的比例；
- Stale Evidence Rate：使用过期状态作决策的比例；
- Local Rejection Rate：UE 因本地约束拒绝候选动作的比例；
- Recovery Time：从异常触发到回退或确认恢复的时间。

#### C. 把“模型效果”扩展成端到端收益

CSI 等模型的评估不应只看 NMSE、准确率或重构误差。至少应同时记录：

- 反馈开销；
- 推理时延；
- UE 内存、算力和功耗；
- BS 侧处理开销；
- BLER、吞吐量、可靠性或定位/感知业务 KPI；
- 场景外泛化；
- 模型切换和回退期间的性能损失。

## 10. 建议的独立研究问题

### Q1：双侧本地验证是否减少错误发布

给定相同的 BS 候选模型和相同的网络侧证据，比较 UE 被动执行、UE 确定性 Runtime 和 UE 轻量 Agent 三种方案的错误发布率、拒绝率和额外开销。

### Q2：何时值得让 UE 参与模型决策

UE 侧参与应当有明确触发条件，例如：

- 本地资源约束是 BS 无法观测的；
- 本地数据不能上传；
- 模型输入质量只能在 UE 侧确认；
- 端网模型必须成对更新；
- 本地故障需要毫秒级或本地闭环回退。

实验需要证明：这些条件下，UE Runtime 的收益是否超过信令、计算和设备能耗成本。

### Q3：如何用最少数据补测支持共同激活

BS Agent 不应默认请求所有 UE 上传原始数据。可把候选补测动作限制为：

- 上传统计摘要；
- 上传错误计数和 KPI 窗口；
- 本地运行小规模 shadow evaluation；
- 仅上传模型输出与标签的聚合结果；
- 需要时再请求受控样本。

研究重点是比较全量采集、固定采样、规则补测和证据驱动补测在发布正确性、采集成本和隐私暴露上的差异。

### Q4：如何保证端网模型切换的事务一致性

切换事务应至少包含：

```text
Candidate
 -> Negotiated
 -> Prepared
 -> LocallyVerified
 -> Ready
 -> Activated
 -> Observed
 -> Accepted / RolledBack
```

每次状态转移都要有条件、超时和补偿动作。实验需要注入：

- UE 下载失败；
- BS 侧模型已变更；
- UE 版本不兼容；
- 本地资源不足；
- 运行 KPI 未达到阈值；
- 一侧激活成功、另一侧激活失败；
- Agent 或 API 不可用。

### Q5：双 Agent 是否真的优于单 Agent

最终主问题应写成可否证的形式：

> 在相同模型候选集、相同数据预算和相同回退能力下，BS Agent + UE Runtime 是否能相对于单 BS Agent 降低错误发布和恢复成本，并且不显著增加端网通信、推理和 UE 资源开销？

如果实验不能证明这一点，应把研究收缩为“BS Agent + UE 本地验证器的模型生命周期系统”，而不是继续强调双 Agent。

## 11. 建议的实验设计

### 11.1 用例层次

建议先使用一个端网模型配对明确、可模拟、可测量的用例，再扩展第二个用例验证通用性。CSI 可以作为第一候选，但不要在文档中预先规定 CSI 是唯一锚点。

第一用例应满足：

- 至少有一个 UE 侧或双侧 AI/ML 模型；
- 模型输入输出可以用 schema 描述；
- 可以构造版本不兼容、资源不足和数据分布偏移；
- 有传统算法或旧模型可回退；
- 可以同时测量模型、链路、系统和设备 KPI。

### 11.2 基线配置

| 基线 | 说明 |
|---|---|
| Rule-only | 固定阈值、规则和传统回退，不使用 LLM |
| Single-BS-Agent | BS Agent 负责所有规划，UE 不提供本地决策 |
| BS-Agent-plus-Validator | BS Agent 规划，UE 只执行确定性检查 |
| Symmetric-LLM | BS 和 UE 都运行受限 LLM，仅作为成本和收益上界/反例 |
| Oracle | 访问完整状态并使用真实最优或离线最优决策，用于估计上限 |

### 11.3 消融实验

至少需要做以下消融：

1. 去掉 UE 本地资源检查。
2. 去掉版本配对检查。
3. 去掉证据新鲜度检查。
4. 去掉在线 Critic 或运行后验收。
5. 去掉结构化协议，改为自然语言协商。
6. 去掉自动回退，只允许人工处理。
7. 把完整 LLM 放入 UE，测量收益是否覆盖额外成本。
8. 把 CSI 换成第二个无线 AI/ML 用例，观察设计是否仍成立。

### 11.4 评价指标

#### 正确性和安全性

- 错误发布率；
- Unsafe APPLY Rate；
- 版本不匹配率；
- 单侧激活率；
- 回退成功率；
- 过期证据使用率。

#### 生命周期性能

- 从异常触发到候选方案生成的时间；
- 从候选到共同激活的时间；
- 切换失败后的恢复时间；
- 不必要补测次数；
- 模型退化发现延迟。

#### 资源和业务成本

- BS Agent 推理调用次数和耗时；
- UE Runtime CPU、内存、能耗和信令开销；
- 数据上传量和隐私暴露范围；
- 业务吞吐量、可靠性、时延、BLER 或用例特定 KPI；
- 模型精度、泛化和推理成本。

## 12. 可形成的研究贡献边界

### 12.1 可以主张的贡献

在完成真实实验后，比较稳妥的贡献表述可以是：

1. 提出面向端网模型生命周期的分层 BS/UE 协同架构，其中 BS Agent 负责全局编排，UE Runtime 负责本地验证和回退。
2. 定义结构化的模型配对、共同准备、共同激活和回退事务。
3. 提出证据驱动的补测和数据最小化策略，减少不必要的 UE 原始数据上传。
4. 设计可复现实验基准，联合评估模型性能、业务 KPI、安全性和设备成本。
5. 通过故障注入证明本地验证和端网事务对错误发布、部分激活和恢复时间的影响。

### 12.2 不能单独作为贡献的内容

以下内容单独出现时不足以支撑强研究贡献：

- 把两个 LLM 分别放在 BS 和 UE；
- 给 Agent 增加 perception、memory、planning、action 四个名字；
- 给动作加一个 JSON schema；
- 用一个固定规则检查资源是否足够；
- 只在 CSI 仿真数据集上报告 NMSE 改善；
- 把已有的工具调用、人工审批或安全回退换一个命名；
- 只比较 LLM 与 prompt baseline，而没有单 BS、UE Runtime 和传统控制器基线。

## 13. 研究风险与止损条件

### 13.1 风险一：双 Agent 没有额外价值

如果 UE Runtime 只转发 BS 已知信息，或者本地约束很少触发，双侧拆分可能只是系统工程分层。止损方式是把研究目标收缩为“BS Agent + UE 确定性验证器”，不强行引入 UE LLM。

### 13.2 风险二：LLM 不在关键路径上

如果所有安全和控制结果都由固定规则完成，LLM 只生成说明文字，则应把贡献定位为生命周期编排和证据规划，而不是安全控制本身。

### 13.3 风险三：CSI 用例无法形成端到端收益

如果 CSI 只带来 NMSE 改善，却增加反馈、时延或 UE 能耗，不能把它作为双 Agent 的成功案例。应保留传统 CSI 方法作为基线，并考虑切换到模型配对和生命周期特征更明显的用例。

### 13.4 风险四：把预印本方法误写成已有共识

WirelessAgent 系列、WirelessOpsAgent、Net Analyzer rApp、Agentic AI for ISAC 和 LLM CSI Feedback 在本文中都按公开预印本或方法近邻处理。后续若查到正式出版版本，应补充正式载体和 DOI；在此之前不使用“已有论文证明该机制已成熟”的表述。

## 14. 最终定位建议

建议将本项目定位为：

> 面向无线 AI/ML 模型生命周期的端网协同安全编排：由 BS 侧全局 Agent 规划评估、补测和版本动作，由 UE 侧轻量 Runtime 根据本地资源、数据、隐私和版本事实进行确定性验证，双方通过结构化事务完成模型共同准备、激活、监测和回退。

这个定位吸收了现有论文已经证明有效的机制：无线工作流、工具门控、动作证据、在线 Critic、故障后验证和业务 KPI 评估；同时把研究问题收敛到现有材料没有完整覆盖的组合：

```text
端网两侧模型状态不一致
    + UE 本地事实不能完全被 BS 观测
    + 模型激活需要版本和能力配对
    + 失败后必须保持业务可运行
    + 需要同时控制数据、设备和网络成本
```

BS 和 UE 是否分别配置“Agent”，最终应根据实验结果决定。第一版实现优先采用 **BS 全局 Agent + UE 轻量确定性 Runtime**；只有当实验显示 UE 侧需要本地规划、压缩复杂证据或处理多步隐私策略时，才进一步引入受限 UE Agent。这样既保留双侧协同问题，又避免把“两个完整 LLM”误当成研究目标。

## 15. 参考文献与本地材料

### 15.1 正式出版论文

1. Harrison Mfula and Jukka K. Nurminen, “Adaptive Root Cause Analysis for Self-Healing in 5G Networks,” *2017 International Conference on High Performance Computing & Simulation (HPCS)*, 2017. 本地文件：`方向文档/reference/pdfs/Adaptive_Root_Cause_Analysis_for_Self-Healing_in_5G_Networks.pdf`。
2. Xingqi Wu, Yuhui Wang, Junaid Farooq, and Juntao Chen, “LLM-Driven Agentic AI Approach to Enhanced O-RAN Resilience in Next-Generation Networks,” *IEEE INFOCOM 2025 - IEEE Conference on Computer Communications Workshops*, 2025, DOI: `10.1109/INFOCOMWKSHPS65812.2025.11152722`. 公开记录：[DOI 页面](https://doi.org/10.1109/INFOCOMWKSHPS65812.2025.11152722)。本地文件：`方向文档/reference/pdfs/LLM-Driven_Agentic_AI_Approach_to_Enhanced_O-RAN_Resilience_in_Next-Generation_Networks.pdf`。
3. Zhou Fang, Shuping Dang, Zhenrong Zhang, and Yan Zhang, “OnlineCritic-xApp: Online Learning for LLM-Assisted RAN Slice Resource Management,” *IEEE INFOCOM 2026 - IEEE Conference on Computer Communications*, 2026, DOI: `10.1109/INFOCOM59046.2026.11571592`. 公开记录：[DOI 页面](https://doi.org/10.1109/INFOCOM59046.2026.11571592)。本地文件：`方向文档/reference/pdfs/OnlineCritic-xApp_Online_Learning_for_LLM-Assisted_RAN_Slice_Resource_Management.pdf`。

### 15.2 公开预印本和本地方法材料

4. Jingwen Tong et al., “WirelessAgent: Large Language Model Agents for Intelligent Wireless Networks,” arXiv:2505.01074, 2025. 公开记录：[arXiv 页面](https://arxiv.org/abs/2505.01074)。本地文件：`方向文档/reference/pdfs/2505.01074.pdf`。
5. Jingwen Tong et al., “WirelessAgent++: Automated Agentic Workflow Design and Benchmarking for Wireless Networks,” arXiv:2603.00501, 2026. 公开记录：[arXiv 页面](https://arxiv.org/abs/2603.00501)。本地文件：`方向文档/reference/pdfs/2603.00501.pdf`。
6. Zijian Lu et al., “WirelessOpsAgent: A Benchmark and Agent Design for Action Assurance in Wireless Networks,” arXiv:2608.08277, 2026. 公开记录：[arXiv 页面](https://arxiv.org/abs/2608.08277)。本地文件：`方向文档/reference/pdfs/2608.08277.pdf`。
7. Tuan V. Ngo et al., “LLM-Based Net Analyzer rApp for Explainable and Safe Automation in O-RAN Non-RT RIC,” arXiv:2603.13775, 2026. 公开记录：[arXiv 页面](https://arxiv.org/abs/2603.13775)。本地文件：`方向文档/reference/pdfs/2603.13775.pdf`。
8. Wenwen Xie et al., “Agentic AI for ISAC: Analysis, Framework, and Case Study,” arXiv:2512.15044, 2025/2026 version. 公开记录：[arXiv 页面](https://arxiv.org/abs/2512.15044)。本地文件：`方向文档/reference/pdfs/2512.15044.pdf`。
9. Yiming Cui et al., “Exploring the Potential of Large Language Models for Massive MIMO CSI Feedback,” arXiv:2501.10630, 2025. 公开记录：[arXiv 页面](https://arxiv.org/abs/2501.10630)。本地文件：`方向文档/reference/pdfs/2501.10630.pdf`。
10. Dae Cheol Kwon and Xinyu Zhang, “Open RAN Conflict Agents: Detecting and Mitigating xApp Conflicts with Generative Agents,” local file `方向文档/reference/pdfs/ORCA_INFOCOM26.pdf`; formal publication status not confirmed in this review.

## 16. 文档内引用的状态说明

本文把论文按“正式出版”“公开预印本”“本地状态未核验”分开，是为了避免把方法启发误写成同行评审共识。后续如果新增论文，应至少补充：正式题名、作者、年份、载体、DOI 或稳定公开记录、论文实际覆盖的 Agent 位置、是否有 UE 本地组件、是否有模型版本事务、是否有回退和正式实验。
