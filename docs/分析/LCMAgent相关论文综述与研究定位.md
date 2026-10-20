# LCMAgent 相关论文深度综述与研究定位

> 更新日期：2026-10-20。本文是面向项目决策的专题调研，不声称穷尽全部文献。“已有工作覆盖”需要来源；“尚未验证”“建议研究”是项目判断或待检验假设，不等于已证明的新颖性。书目、版本和阅读深度见第 16 节。本次扩展至波束管理、定位、神经接收机、链路自适应与干扰预测；汇总 40 篇论文、2 份标准文件及 1 份会议讨论材料。所有条目均对应 [BibTeX 与索引](../相关工作/参考文献.md) 和 [逐篇详解](../相关工作/论文详解/README.md)；已确认的公开代码见 [仓库清单与浅克隆脚本](../相关工作/公开代码.md)。

## 1. 核心结论：从 CSI 配对推广到无线 AI 功能生命周期

### 1.1 最重要的修正不是多加几篇 Agent 论文

上一版主要围绕无线 LLM Agent 展开，容易把“这些 Agent 论文没有实现的东西”误当成“整个领域没有实现的东西”。真正的直接相关工作不仅来自 Agent 社区，还包括无线 AI/ML 生命周期、波束预测的模型选择与适配、神经接收机的部署后监测、资源受限在线微调、CSI 双侧互操作、统计决策与分布式恢复。只把 CSI 编码器/解码器当管理对象，会遗漏大量更直接的竞争工作。

| 上一版容易形成的认识 | 本轮核验后的认识 | 对 LCMAgent 的影响 |
|---|---|---|
| 双侧模型生命周期主要是本项目提出的组合问题 | TR 38.843 已讨论 LCM、标识、端网协作、监测、切换和 fallback；Huang 等专门讨论互操作 AI-native RAN 的 LCM [S01, P01] | 不能把“生命周期闭环”或“端网配对”作为首次贡献 |
| gNB 和 UE 各有可调用组件就足够区别于现有 Agent | Dual-MCP 已在 gNB 与 UE 两端部署 MCP server，由云端 LLM 协调并保留人工审批 [P12] | 双侧工具化、日志与人机协作不是空白 |
| 规划与执行分离、确定性安全门是核心新意 | A1gent、Net Analyzer、AgentSpec 已分别提供相邻机制 [P11, P16, P18] | 这些应成为基础设施和强基线 |
| CSI 研究基本只优化重构误差 | 已有性能监测、训练—监测—更新一体化、跨厂商原型和 OTA 吞吐量评估 [P02–P04] | 必须比较非 LLM 的直接竞争者 |
| 准备—激活—回退状态机就能构成协议贡献 | 事务提交与故障恢复是成熟问题；近期无线 LCM 论文也讨论 pair consistency、超时与本地 fallback [P05, P20] | 要证明无线约束下的新增性质或性能，不只是画状态图 |

**结论：LCMAgent 可以做波束管理，而且不必以双侧配对为前提。建议定位为“预算约束与状态不确定条件下，无线 AI 功能的证据驱动生命周期决策与可靠执行”。** CSI 配对是特殊用例，而非项目定义。需要同时防止另一种泛化过度：不能用一套指标、一种标签或同一安全语义覆盖所有无线功能。

本次新增的直接近邻改变了创新边界：Sun 等已研究波束模型选择与监测 [P26]；Go 等已给出网络主导、UE 测试和报告的波束模型适配 [P27]；VERITAS 已研究神经接收机的变化检测、传统接收机复核和再训练 [P36]；LightTune 已研究 UE 轻量在线微调及链路自适应 [P40]。因此，“把 LCM 用到非 CSI”“发现退化就更新”“端网协同选模型”均不能单独充当贡献。

### 1.2 推荐的主问题

> 对已经具备模型仓库、兼容性检查、监测、回退和确定性执行器的系统，在端网信息分散、证据获取有代价、设备状态变化及消息可能丢失的条件下，如何决定下一步采集什么证据，何时选择、重新校准、适配、激活或禁用哪个无线 AI 功能，以及何时等待、拒绝或回退，使错误发布和业务损失受控，同时减少监测、通信和 UE 计算成本？

有三个必须分开证明的层次：

1. **系统正确性**：输入、输出与无线配置兼容；双侧 CSI 另需配对一致；过期证据和授权不能复用；失败有明确恢复路径。单侧模型不应被强行加入 encoder/decoder 提交协议。
2. **决策有效性**：相同执行基础设施下，比固定阈值、序贯检测、主动测量和非 LLM 规划器更有效地使用有限证据。
3. **Agent 必要性**：面对异构工具和组合任务时，LLM 的优势是否超过推理成本与额外故障面。

第一层不能自动证明第二层，第二层不能自动证明第三层。若只有第一层成立，应定位为安全 LCM 系统，而不是强行宣称 Agent 决策创新。

## 2. 研究边界、术语和证据规则

### 2.1 四类“双侧/多 Agent”不能混为一谈

| 概念 | 实际含义 | 不自动意味着什么 |
|---|---|---|
| 双侧 AI/ML 模型 | 如 UE encoder 与 gNB decoder 联合完成 CSI 压缩/重建 | 两端各有 LLM，或两端各自训练 |
| 分布式控制组件 | 两端各有执行器、工具服务或验证器 | 两个组件都自主推理 |
| 多 Agent 编排 | 多个规划/任务实体协商、分工和调用工具 | 已解决配对、跨厂商训练或崩溃恢复 |
| 联邦/分割训练 | 参数、梯度或中间表示跨节点协作产生模型 | 已完成上线后的联合激活、切换和回退 |

“UE 轻量 Runtime”应明确指工具接口、本地状态、预算执行和验证逻辑。没有自主规划时，不应为强调“双 Agent”而包装成第二个 LLM Agent。

### 2.2 三个平面与多种时间尺度

以下是项目建议的划分，不是声称标准要求如此部署：

```text
管理/推理平面：模型仓库、训练验证、慢速 LCM 规划、审计
    ↓ 提交有边界的候选计划
端网协调平面：功能/配置绑定、证据交换、资源确认、激活与恢复状态
    ↓ 由确定性执行器放行动作
无线执行平面：波束预测/切换、CSI 编解码、定位/接收处理、预置本地 fallback
```

训练、下载与复杂推理可以慢；已部署模型的禁用、局部切换和失效保护可能需要更快。P01 区分 OAM 与 RAN-local LCM，P05 分析纠正动作延迟。这些支持分层，不支持把统一的“秒级 Agent 闭环”套到所有无线动作上。

### 2.3 来源、阅读深度与否定性结论

- **标准来源**：区分 TR 研究报告、TS 技术规范及会议讨论稿。“讨论过”不等于“强制规范”。
- **论文来源**：优先原文、出版社、作者机构与官方会议记录。Crossref 核验书目，不代替实验原文。
- **A：全文相关章节**：阅读方法、实验或限制中的相关部分，不表示逐项复算。
- **B：摘要/书目/局部原始材料**：只据此说明范围，不复原未开放算法。
- **C：原有本地阅读 + 公开记录补查**：保留上一版结论，不伪装为本轮重新完整复现。
- **未找到不是不存在**：对 B/C 级来源写“本轮未确认”，不在矩阵中直接打“没有”。

截至日期是检索边界，不是所有网页最新版的保证。公开稿、early access 和卷期年份可能不同；只查到“2026”而没有具体出版日时，不凭 DOI 年份断言已在某日正式见刊。

### 2.4 “单侧推理”与“单侧管理”不同

模型只在 UE 或 gNB 一侧运行，仍可能需要另一侧提供测量、候选模型、配置、标签或激活许可。波束模型可在 UE 推理、由网络提供候选及适配信息；定位可由网络融合多点观测；UE 的 BLER 预测可借助延迟反馈更新。管理协作不等于神经网络成对部署。[P27, P33, P40]

还须区分三个动作：**切换无线波束**、**切换预测模型**、**改变测量/码本配置**。第一个可能需要很快执行，第二个属于模型 LCM，第三个会改变模型适用条件。LLM 不应逐时隙决定波束或逐符号解调；它可配置慢速策略和证据预算，快速闭环仍由本地算法执行。这是项目设计建议，不是这些论文已证明的统一架构。

## 3. 标准和基础框架：哪些问题其实已经存在

### 3.1 TR 38.843：不能把框架待细化当成标准没有 LCM

本地原始文件 `标准文件/38843-j00.pdf` 首页为 **3GPP TR 38.843 V19.0.0，2025-09，Release 19**。本轮核对范围、LCM、协作和 CSI 规范影响内容，不只依据目录。[S01]

| 原文位置 | 与本项目相关的内容 | 正确使用方式 |
|---|---|---|
| §4.2–4.4 | LCM 形式、标识、附加条件、数据收集与协作 | 作为问题与对象模型起点 |
| §5.1.2 | CSI 跨厂商协作及可行性 | 区分训练互操作与上线事务 |
| §6.2 | 泛化、独立训练、分布不匹配、复杂度与性能 | 不只做同分布精度实验 |
| §7.1.2，尤其 §7.1.2.1 | 监测、fallback、量化与反馈格式对齐等潜在规范影响 | 区分已有议题、研究选项和已规范要求 |

该报告并非只研究 CSI：§5.2/§6.3 研究波束管理，§5.3/§6.4 研究定位精度增强，§7.1.3/§7.1.4 分别讨论相关规范影响。波束评估区分测量集合 Set B、目标集合 Set A，以及空间/时间预测；定位评估另含非理想标签、微调与泛化。报告也涉及网络/UE 侧监测和网络控制，以及量化、反馈大小和模型配对相关对齐。项目需要给出可执行机制与实验，但不能再写“现有标准没有考虑端网模型协同”。[S01]

### 3.2 TS 28.105：管理对象也不是白纸

本轮读取 ETSI 发布的 **TS 128 105 V18.4.0，2024-07，对应 3GPP TS 28.105 Release 18**。这是固定的可复核版本，不声称它是检索日最新版。[S02]

相关位置包括 §4a.0、§6.1、§6.4、§6.5，以及 §7.2a.2.3 的 `MLModelCoordinationGroup`。后者描述可联合训练、联合测试并协调推理的模型组；加载和更新也有请求、过程与状态对象。[S02]

对 LCMAgent 的含义：

1. “模型组”“加载状态”“更新请求/报告”不能单独作为新概念。
2. 可映射现有管理对象，但不能据此声称 TS 已规定本文的 UE 资源预留或跨端提交协议。
3. 管理面状态完成，不等于数据面已安全切到正确的 encoder/decoder 配对，实验应区分。

### 3.3 R1-2508811：保留材料，控制证据等级

本地 `标准文件/R1-2508811.pdf` 及第三章解读用于理解 6GR 评估、LCM 与数据收集的讨论边界。[D01] 本轮不把所有提案升级为标准要求，也未核验其后的全部会议决定。

建议写：“以 NR AI/ML LCM 为起点，研究端网协同证据与发布机制。”不宜写：“标准要求 BS/UE 分别部署 Agent，本文负责实现。”

## 4. 第一组直接近邻：生命周期与双侧模型互操作

这一组比多数通用 Agent 论文更直接决定定位，应放在 Related Work 前部。

### 4.1 P01：AI/ML Life-Cycle Management for Interoperable AI-Native RAN

**来源与类型**：Huang 等；2025 首稿，2026-08-26 v3；公开稿注明被 *IEEE Communications Standards Magazine* 接收。类型：survey + framework。[P01]

**机制**：衔接管理、数据、训练/适配、存储、推理及监测，区分慢速 OAM 和较快 RAN-local 控制，并讨论双侧 CSI 跨厂商兼容性。全文 §IV 直接提出监测开销、输入分布变化和智能决策问题。

**证据边界**：其 CSI 环境切换案例不是对 UE 异构、并发事务和部分失败的完整评估。案例还说明：环境改变后，失配模型的绝对 KPI 也可能提高，不能只用“当前 KPI 比过去差”识别失配。

**定位影响**：不能把“监测、模型切换和跨厂商配对串成 LCM 闭环”当新意。可以进一步研究怎样用有限成本获得足够证据、把决策连接到可恢复执行，但这是待验证的具体化。

### 4.2 P02：Demonstrating Interoperable Channel State Feedback Compression with Machine Learning

**来源与类型**：Korpi 等；2025 公开稿，*IEEE Wireless Communications* 正式记录，2026 卷期。类型：method + system。[P02]

**机制**：不同厂商不公开彼此模型，仍可顺序训练可互操作的 UE encoder 和 gNB decoder，并用原型设备做 OTA 评估，同时看重构指标和下行吞吐量。

**数值与限制**：全文报告相对 Type I 反馈约 30%–100%、平均约 60% 的吞吐量增益，但也指出对照为宽带预编码，ML 方案为子带预编码，比较条件影响增益。不能直接当成纯压缩模型收益。

**定位影响**：两端配对、模型保密和实机收益已有强先例。LCMAgent 应把兼容配对作为输入条件，研究何时上线、需补测多少、失败如何恢复，不重新声称首次实现互操作。

### 4.3 P03：Performance Monitoring-Enabled Reliable AI-Based CSI Feedback

**来源与类型**：Guo、Ma、Wen、Jin；*IEEE Transactions on Wireless Communications*，2025 卷期，DOI 含 2024。类型：method。[P03]

**已核验机制**：不是只在 BS 看 KPI，而是在发送 CSI codeword 前，由 UE 运行经知识蒸馏训练的轻量 proxy decoder，近似 BS decoder，从而本地估计反馈质量。摘要报告低质量样本检测率接近 95%，但本轮未复核其判定阈值、误报率和全部场景，不能把该数字当成无条件保证。

**重要区别**：这种 proxy 是信号处理/监测模型，不是 LLM Agent；它已经提供“UE 本地、低复杂度、无需搬运完整 BS decoder 的质量证据”。若 LCMAgent 也用本地轻量模型验收候选，应比较代理误差、跨版本有效性和实际成本，而不是把本地证据首次归给 Agent。

**定位影响**：若主贡献是“不上传全部原始 CSI 的低开销监测”，必须先读透此类工作并按相同监测预算比较，不能只与无监测 CsiNet 比。全文复核前，算法级差异保持待定。

### 4.4 P04：Scenario-Aware Framework for DL-Based CSI Feedback With Unified Training, Monitoring, and Updating

**来源与类型**：Li 等；*IEEE Internet of Things Journal*，2025。类型：method。[P04]

**已核验机制**：统一处理训练数据偏差、部署期 OOD 检测和避免遗忘的更新。出版社摘要介绍基于 Softmax/energy 的检测与更新策略。

**结果边界**：摘要报告特定随机偏差设置下最高 4.65 dB NMSE 改进；不是任意场景保证。本轮未复核所有切分、对照与计算代价。

**定位影响**：“发现漂移后切换/更新”本身不新。需要研究在双方都具备监测和更新时，跨端事实、证据时效和发布失败是否仍造成额外问题。

### 4.5 P05：Toward a Layer-2 Trigger for AI/ML Lifecycle Management in 6G

**来源与类型**：2026-09-13 公开预印本。类型：method + framework。[P05]

**问题**：纠正命令太晚到达，监测发现问题也未必挽救业务。论文讨论配对一致性、目标激活时刻、确认、超时及本地 fallback，与本项目事务/恢复叙事直接重叠。

**结果与限制**：150 个 PPO 候选，每个 20 个匹配噪声实现的替代环境实验中，零附加延迟时 blending 的累计 SLA deficit 为 7.57，hard cutover 为 47.02；40 个附加控制步时升至 44.38。控制步未映射为毫秒，不能推断物理 6G 时延上界或 L2 必然必要。

**定位影响**：pair ID、ACK、超时和快速 fallback 不再是未被讨论的概念。可以补充实际编码/解码链中的故障证据，或在明确假设下证明性质。

### 4.6 P06：Deep Learning for CSI Feedback: One-Sided Model and Joint Multi-Module Learning Perspectives

**来源与类型**：2024 公开稿，*IEEE Communications Magazine* 2025。类型：survey。[P06]

**启示**：双侧深度模型的维护和厂商协作有负担，单侧方法可能绕开部分负担；联合优化反馈、估计、编码/预编码等模块，可能比单个重构指标更重要。

**反证压力**：若单侧模型在相同反馈预算和业务 KPI 下足够好，复杂双侧 LCM 未必划算。应分别比较：同一双侧模型的不同管理器，以及不同模型部署架构的系统总收益。前者隔离管理贡献，后者检验应用价值，不能混为一张排名。

## 5. 第二组直接近邻：无线 Agent、双端工具与安全执行

### 5.1 P07/P08：WirelessAgent 与 WirelessAgent++

**WirelessAgent** 将无线任务接到感知、记忆、规划和工具调用；2025 公开稿已有 *China Communications* 2026 正式记录。[P07] 上一版一律归为预印本的分类应更新。

**WirelessAgent++** 研究自动工作流设计与 WirelessBench，使用 maturity-aware critic、三类经验回放和收敛检测，不只是固定 prompt。基准覆盖知识题、网络切片和移动业务保障；工作流搜索的改进不能直接等同于有丢包/崩溃的端网发布收益。[P08]

**项目应吸收与区分**：

- 复用工具接口、任务分解、工作流搜索与多骨干评估。
- 另外证明执行时证据仍有效、两侧兼容、失联后可恢复。
- 若本项目有确定性 guard，给基线同样的 guard，再比较规划；否则可能只是“有验证器优于无验证器”。

### 5.2 P09：WirelessOpsAgent 与 WirelessOptBench

**机制**：关注 proposal-time 正确、execution-time 失效，使用证据/契约决定 `APPLY/HOLD/RETRY/ESCALATE`，支持修复后复核。[P09]

**实验辨析**：Table III 每个骨干/方法 600 episodes；Claude 上 Unsafe APPLY 从 82.2% 降到 10.3%，分母是全部 episodes，不是全部 APPLY。仍有剩余违规；§V-D 披露 conflict/provenance 切片的 frozen evaluator 混淆，不能把局部“零误放行”读成普遍安全。

**定位影响**：动作证据、新鲜度、局部修复和执行前复核已有直接近邻。受控 benchmark 不等于生产故障分布；论文将执行器安全和并发控制列于评估之外。端网并发、配对和真实链路可以成为范围差异，但不是贬低其贡献的理由。

### 5.3 P10：AgentRAN

**已覆盖**：分层多 Agent、自然语言意图、跨时间尺度/空间/协议层组织，以及真实 5G testbed 演示；2025 公开稿，作者项目列有 *IEEE Communications Magazine* 2026 DOI。[P10]

**比较方式**：Agent 数量、分层编排和多目标控制不是空白。跨时间尺度架构也不意味着每次 LLM 请求都达到物理层时限。应比较具体模型发布任务，不能用“它管网络、我们管模型”一句话结束。

**未确认**：是否实现与本文完全相同的配对版本恢复语义；不能仅凭摘要写“没有”。

### 5.4 P11：A1gent

**机制**：非实时 rApp 将意图编译为有类型 A1 策略，近实时 xApp 通过确定性循环执行，使用 guardrail 与固定优先级冲突合并。已有 ICC 2026 正式记录及公开稿。[P11]

**定位影响**：“LLM 只提议，执行器控制”已有强先例；冲突合并也不是拼接各 Agent 建议。有效差异是模型对生命周期、两端隐含状态与可恢复提交。

**证据边界**：可审计、确定性不自动等于所有调度/并发/故障下有形式安全证明。比较要分列可检查规则、故障覆盖和已证明性质。

### 5.5 P12：Dual-MCP——上一版遗漏严重的双端架构近邻

**来源与类型**：Baena、Mandal、Koutsonikolas；*ACM MobiHoc 2025* 两页 demo，391–392。类型：system/tool。[P12]

**已覆盖**：gNB 和 UE 各暴露 MCP 工具，云端 LLM 编排跨端动作，执行前人工批准；论文还声明前后条件检查、可逆执行与日志。不能声称这些是 LCMAgent 首创。

**需要区分**：工具服务器不是两套自主 LLM；跨端重配置演示不自动等于完整 encoder/decoder 生命周期事务。文中对“formal”“rollback”的表述也不能代替完整协议、故障模型与证明。两页 demo 提供实现先例，不足以证明长期故障恢复和大规模收益。

**建议比较**：在 Dual-MCP 式端网编排上使用相同模型仓库/执行能力，再逐项增加配对契约、时效证据、提交恢复和主动补测，定位新增价值。

### 5.6 P13：OnlineCritic-xApp

保留原文 INFOCOM 2026 正式论文，研究 LLM 辅助切片资源管理与在线学习 Critic。[P13] 原有本地阅读中“候选动作需外部评价/可行性控制”的启示仍有价值。

本轮未重新审计全部实验和实现，不补造收益，不把学习式 Critic 的经验效果等同于跨端发布硬安全。适合作为“LLM 候选 + 筛选器”近邻，不是双侧 LCM 的直接替代。

### 5.7 P14/P15：ORCA 与 PACIFISTA

**ORCA** 用生成式 Agent 检测、缓解 xApp 冲突。[P14] 本轮找到作者公开记录，正式载体独立核验不足，不根据 `ORCA_INFOCOM26.pdf` 文件名判定主会出版。

**PACIFISTA** 不依赖 LLM，通过 sandbox profiling、图和统计方法发现、刻画 O-RAN 应用冲突；公开记录对应 *IEEE Transactions on Mobile Computing* 2025。[P15]

**启示**：共享 BS decoder、GPU/内存、监测资源和并发更新也会冲突。每个 UE 局部验证成功，全局仍可能超预算。必须有资源仲裁器，并比较“不用 LLM 但有 sandbox/冲突管理”的方案。

### 5.8 P16/P17：Net Analyzer rApp 与 O-RAN Resilience

**Net Analyzer** 在真实 O-RAN testbed 的 ping-pong handover 场景中，串联事件解释、日志核查、工具访问和显式人工批准。[P16] 支持解释/动作分离，不证明全自动无审批同样安全。

**O-RAN Resilience** 为 INFOCOM Workshops 2025 正式 workshop 论文，研究 LLM Agent 与 O-RAN 韧性。[P17] 保留为网络侧背景，不把 workshop 案例升级为端网发布一般性结论。

## 6. 第三组方法基础：决定贡献是否成立

### 6.1 P18：AgentSpec——运行时约束不是新的 Agent 概念

AgentSpec 以结构化规则描述触发、谓词与处置，对 Agent 做运行时约束；2025 公开稿，已有 ICSE 2026 出版信息。[P18]

schema、权限、预算和拦截应尽量确定性化。规则完全可枚举时，必须问为何需要 LLM。规则引擎能检查已有事实，但证据从何获得、何时失效、是否代表当前本地资源，是另一层问题。

### 6.2 P19：Quickest Change Detection with Controlled Sensing

Veeravalli、Fellouris、Moustakides 联合研究“何时宣布变化”与“下一步选什么观测动作”。WCC 在有限动作和变化后参数等假设下分析最坏检测时延、误报约束及渐近最优性；正式载体为 *IEEE Journal on Selected Areas in Information Theory* 2024。[P19]

主动补测不能只和固定采样比较。应比较序贯检测/受控观测，或解释其假设为何不适用：标签延迟、不同隐私代价、UE 可拒绝、观测期间状态变化等。不能把经典问题换名成“Agent 自主感知”。

### 6.3 P20：Consensus on Transaction Commit

Gray 与 Lamport 说明协调者故障、提交决定和恢复是成熟分布式问题。[P20] `PREPARE/COMMIT/ACK` 三个消息名不构成新事务协议。

必须明确追求原子提交、可检测配对安全、有限不一致窗口还是最终恢复；声明崩溃、消息丢失、分区、持久日志、时钟和重试假设。没有这些，不能声称“共同激活保证一致性”。

### 6.4 P21：InvaRAN——验证器本身也会出错

USENIX Security 2026 正式论文，以动态推断不变量和测试发现 O-RAN 控制器逻辑问题。官方摘要报告 9 个此前未知问题，含 7 个逻辑问题、2 个内存问题。[P21]

应测试 validator 的状态遗漏、单位/语义错配、并发和罕见恢复路径，而不仅测 LLM 能否输出合法 JSON。动态不变量提供测试线索，不自动等于完整形式证明。

## 7. 非 CSI 功能与直接近邻：波束、定位、接收机及统计监测

### 7.1 先区分执行模型、Agent 与管理问题

| 文献 | 实际贡献 | 本项目中的角色 |
|---|---|---|
| P22 CsiNet | 深度学习 CSI 压缩/重建与波束成形效果 | 固定配对模型用例；不能因为它没有 Agent 就证明新 LCM 必要 |
| P23 LLM CSI Feedback | 将 LLM 适配到 CSI 数值压缩/重构 | 信号处理模型路线，不等于管理生命周期 |
| P24 Agentic AI for ISAC | 感知—推理—动作框架与 ISAC 案例 | 第二用例候选；多一个案例不自动证明泛化 |
| P25 Adaptive RCA | 早期 5G 自愈与自适应根因分析 | 诊断与动作后验证并非 LLM 时代才出现 |

对应原始记录见 [P22–P25]。不能混淆“模型用了 LLM”“系统用了 Agent”“两端各有模型”三个类别。

### 7.2 波束管理：不仅“能应用”，而是已经存在直接 LCM 研究

**P26，模型选择与监测。** Chen Sun 等正式发表于 *IEEE Open Journal of the Communications Society* **5:38–50，2024**，早期 DOI 为 2023。补读作者接受稿后可确认，它不仅讨论分区专用模型优于其统一模型的实例，还分别预测 AI 和传统 BM 的 RSRP：如果两者同时变差，回退可能无益；只有 AI 相对失效才更支持切换。其 3 dB drop 轨迹案例把回退从 294 次减到 264 次，约减少 10%。这不是任意场景保证，但已覆盖“环境变差≠模型错误”的重要区分，因此不能将退化归因或避免无效切换本身称为新问题。[P26]

**P27，网络主导的模型适配。** 原始会议论文给出：网络发现退化并请求 UE 信息，UE 报告能力及当前情形，网络下发候选/测试数据等适配信息，UE 测试推荐模型并报告选择，网络确认激活。仿真使用 54 个模型、5,000 个推理步，比较无 LCM、仅 dataset ID 与所提适配；测试监测间隔和退化阈值。实验适配阶段使用当前扇区随机抽取的 5,000 个位置作为评估数据，这是很强的信息条件，不能默认真实 UE 能零成本得到。可以研究标签不足、补测成本、候选测试预算和过期证据，但必须在同等证据可得性下比较。[P27]

**P29/P30/P31，执行模型与真实数据。** DeepBeam 从已有传输的原始波形学习波束及 AoA 特征，重点是降低显式协调/扫描开销，不是模型版本治理。DeepSense 6G 提供真实多模态感知—通信数据，是候选实验资源而非完整在线 LCM 环境。Vladimirov 与 Laskov 用该数据分析地理位置误差、任务定义、归一化和数据漂移对预测波束的影响，提醒不能靠换网络结构掩盖标签与评估问题。[P29–P31]

**可管理对象。** 不仅是权重，还包括输入波束测量集合、目标码本、天线/射频配置、传感器时间对齐、有效场景和校准版本。模型可继续输出合法 beam index，却已对应错误物理波束；只有 schema 校验不够。定位驱动的波束预测还会受定位偏差影响，因此必须区分模型失效与传感器失效。

**建议闭环。** 小规模 top-K 复核 → 风险增大时扩展参考信号扫描 → 判断继续、换模型、校准传感器或退回传统扫描。评价至少同时报告 top-K、相对最优波束的功率/速率损失、失联/波束失败、测量资源与切换振荡；不能用 top-1 准确率替代业务结果。具体损失和预算是项目实验定义，不能冒充标准统一要求。

### 7.3 定位：管理对象包括坐标、锚点与校准，不是另一种 CSI 重构

**P32，Channel Charting。** 从 CSI 的局部几何关系构建低维信道图，解决相对空间结构学习，不应直接写成具有绝对坐标精度保证的定位器。LCMAgent 若管理此类功能，图的参考系、邻域和后续绝对坐标映射都要版本化。[P32]

**P33，真实空间和时间泛化。** 对三组真实 Wi-Fi/5G NR 数据比较 MLP 与 Transformer，分别测试未见区域、完整留出轨迹以及相隔一周的采集活动。观察到两种架构在这些条件下均可泛化，Transformer 用更少参数取得更好的定位精度。因此不能反向歪曲成“所有模型跨时间一定崩溃”。真正可借鉴的是评估协议：按区域、轨迹、采集日期留出，而非随机打散相邻 CSI 快照。[P33]

**建议闭环。** 管理坐标系、锚点几何、时钟/硬件校准、输入 CSI/测量配置和不确定度。证据动作可为请求额外定位测量、采集少量已知位置锚点、重新校准或扩大预测区域。必须说明真值由何处提供；没有在线真值时，只能用代理检测，不能凭 CSI 分布变化宣称已经测得定位误差。评价用米制误差分位数、覆盖率、可用率与定位测量代价，不和 CSI 的 dB 误差直接相加。

### 7.4 接收机与链路自适应：已有“检测—复核—更新”的强基线

**P34/P35，执行功能。** DeepRx 学习从接收频域信号和导频到比特软信息的映射；DeepWiPHY 在 IEEE 802.11ax 场景研究学习式接收处理及实测数据。它们适合提供被管理的神经功能，但静态 BER/BLER 优势不是跨环境可靠部署证明；两者协议与数据条件也不可互换。[P34, P35]

**P36，VERITAS。** 已有部署后测量与恢复框架：持续监测接收导频分布，疑似变化时暂时启动传统参考接收机并行处理，比较两者对同一输入的比特概率，必要时触发有限再训练。论文分别评估信道类型、速度、时延扩展变化；摘要报告检测准确率约 99%、97%、78%，不是所有漂移下的统一安全率；正文结论对时延扩展另列 true OOD detection 为 69%，需区分口径，不能拼成最好成绩。传统接收机不是无误真值，双路运行也有计算代价。LCMAgent 若只把这三步改成工具调用，不足以形成方法贡献。[P36]

**P40，LightTune。** 应引用 2026-05-21 的扩展稿 *LightTune: Lightweight Forward-Only Online Fine-Tuning with Applications to Link Adaptation*，而不是混用早期会议稿数值。它用 forward-forward 层局部更新、阈值触发和逐样本选择实现不依赖反向传播、无需经验回放缓存的在线适配；需要延迟到达的监督指标。应用是 **BLER 预测辅助链路自适应**，不是直接学习 I/Q 解码。扩展稿报告平均 BLER 预测误差最多降低 43.5%，相对传统表式 OLLA 的平均吞吐量最多提高 15.5%；早期会议稿相应吞吐量上限为 9.5%。另需注意 arXiv 摘要元数据写 48.8%，与扩展 v2 正文摘要的 43.5% 不一致；此处按正文引用，不合并取最高值。这些是特定仿真比较，不是可直接迁移的保证；扩展稿页面的占位 DOI 不能当正式 DOI。[P40]

**研究空间。** 需要比较连续/阈值触发微调、分布检测 + 参考接收机复核、模型库切换与停用，而非只有“旧模型不更新”。可研究何时值得支付参考解码/标注/训练成本、何时验收新版本、适配损坏如何恢复。译码器的实时期限、BLER 与算力占用必须进入约束；逐包路径不得等待远端 LLM。

### 7.5 干扰预测与统计可靠性：监测不能只靠 LLM 描述异常

**P28，统计监测。** Kaswan 等在 ICC Workshops 2024 以干扰预测研究三种信息条件：直接比较输入/输出统计；引入反向模型比较重建输入；延迟真值可得后检测预测误差。作者上传全文使用 KS 等检验，并比较均值、方差、高阶矩及联合统计。它已提供非 LLM、按信息可得性分层的监测路线。比较须匹配标签条件、样本数和误报，不可只拿其中最强方案与零标签弱基线对照；重复监测与时间相关性也不能从单次检验显著性直接推出长期保证。[P28]

**P37，事后共形可靠性。** 当系统先受候选集合大小、资源或可达增益约束，再估计选择后集合的遗漏概率，不能直接套用“预设置信度”的普通做法。Su 等研究 backward CP、相关变体与 PAC 共形方法，在窄带干扰检测、近场定位和码本波束识别中检验事后风险估计。其统计保证依赖论文的数据/校准抽样假设；distribution-free 不等于任意时间漂移、相关观测与反复自适应选择下都成立。[P37]

P19/P28/P37 分别提供观测选择、运行监测和风险校准的非 LLM 基础。LCMAgent 可以调用这些方法，但不能把“得到一个置信度”当成新算法，也不能让 LLM 自报信心替代校准风险。

### 7.6 标准观点与跨模拟器泛化：扩大范围也要控制论断

P38 是 ICML 2025 电信基础模型 **workshop** 的立场论文，讨论空口 AI/ML 架构、数据与标准化问题，不是 ICML 主会方法论文。P39 的当前公开版本题名为 *AI/ML for Mobile Networks: Release 19 Status and Future Challenges*；结合 DeepMIMO 与 QuaDRiGa 的 CSI 案例，比较跨场景/跨模拟器零样本迁移和目标域微调。它支持把数据构造、域差异与联合性能—成本指标写进协议，但 CSI 案例不证明波束、定位或接收机的跨用例收益。标准进度必须回到具体规范版本，不能把综述文字当规范条款。[P38, P39]

### 7.7 用例选择矩阵：共享管理骨架，不共享所有安全语义

| 用例 | 典型执行位置与协作 | 关键绑定对象 | 高价值证据与代价 | 直接基线 | 首轮可行性与边界 |
|---|---|---|---|---|---|
| 波束预测/管理 | UE 或网络侧推理；测量、候选与激活可跨端 | Set A/B、码本、天线、位置/感知校准 | top-K 实测、扩展扫描；参考信号与传感器成本 | P26/P27；传统扫描；P37 风险校准 | 建议作为单侧模型主用例；真实离线轨迹不等于在线控制证据 |
| 双侧 CSI 反馈 | UE encoder / gNB decoder | latent、量化、反馈与模型配对 | proxy/shadow 重构、配对验证；反馈/UE 算力 | P02–P06 | 建议作为强耦合对照用例，体现配对事务特有难点 |
| 定位/信道图 | UE、网络或多点融合 | 坐标系、锚点、时钟、CSI 特征 | 真值锚点、额外测量、校准；标签昂贵 | P32/P33/P37 | 适合空间/时间漂移；先确认标签与轨迹可用性 |
| 神经接收机 | 接收端本地实时推理 | 波形、导频、MCS、天线、软输出语义 | 参考接收机、CRC/软信息；双路计算 | P34–P36 | 安全和时限强，需链路级仿真，不能只做表格推理 |
| BLER 预测/链路自适应 | UE/网络预测 + 本地调度使用 | 反馈时延、MCS 集合、特征归一化 | 延迟标签、受限在线更新 | P40；表式 OLLA | 低成本适配近邻强；须隔离预测改善与调度收益 |
| 干扰预测 | 网络侧或 UE 测量协作 | 测量窗口、频带、干扰负载与配置 | 额外观测、统计检验；无线测量成本 | P28/P19/P37 | 适合误报—漏报—时延研究；不是已有跨用例效果 |

## 8. 统一比较：重叠在哪一层，证据在哪一层

**明确**＝来源明确研究；**部分**＝相邻能力或受限范围；**未核**＝本轮不足以判断，不等于没有。表内能力限于论文自身场景，不是同一测试集上的性能排名。

| 工作 | 双侧组件/模型 | LLM 编排 | 配对/互操作 | 执行时证据/门控 | 失败/恢复 | 证据形态 |
|---|---|---|---|---|---|---|
| S01 / P01 | 明确 | 非必要 | 明确 | 监测/适用性框架 | 切换/fallback；事务性质另论 | 标准研究、框架/案例 |
| P02 互操作 | 明确 | 非重点 | 明确 | 非主要评估点 | 未核 | 原型、OTA |
| P03/P04 | CSI 反馈系统 | 非重点 | 未核 | 模型性能/OOD 监测 | 更新/可靠性 | 摘要所述数值实验 |
| P05 L2 Trigger | 明确讨论 | 非重点 | 一致性要求 | KPI 触发 | 超时、本地 fallback 等 | 替代控制环境 |
| P07/P08 | 无线任务/工作流 | 明确 | 未核 | 部分 | 不等于崩溃恢复 | 任务/工作流实验 |
| P09 WirelessOps | 无线运维 | 明确 | 非主要对象 | 明确 | 证据修复/重试 | 受控 execution-state benchmark |
| P10 AgentRAN | 分层网络控制 | 明确 | 未核 | 部分 | 未核 | 真实 5G 演示 |
| P11 A1gent | RIC 分层 | 明确 | 非主要对象 | 明确 | 不等于跨端事务恢复 | 框架与实验 |
| P12 Dual-MCP | gNB/UE 工具明确 | 明确 | 模型 LCM 未确认 | 条件检查、人工控制 | 可逆操作声明 | 两页实机 demo |
| P13 OnlineCritic | 网络切片 | 明确 | 非主要对象 | 候选筛选/可行性 | 不等于 UE 回退 | 本地阅读 + 正式记录 |
| P14/P15 | 多 xApp | 前者是、后者非必要 | 非主要对象 | 冲突管理 | 冲突缓解 | 作者材料 / sandbox、testbed |
| P16 Net Analyzer | 网络 rApp | 明确 | 非主要对象 | 工具门控/审批 | 受控修复 | 真实 testbed |
| P18 AgentSpec | 通用工具边界 | 明确 | 非主要对象 | 明确 | 规则处置 | 多领域评估 |
| P19 受控检测 | 观测动作 | 不需要 | 非研究对象 | 序贯决策 | 非发布恢复 | 理论 + 仿真 |
| P20 事务提交 | 分布式参与方 | 不需要 | 非无线语义 | 提交条件 | 明确 | 协议/理论 |
| P26/P27 | 波束管理，含端网协作 | 不需要 | 非 latent 配对 | 双性能预测、候选评估 | 回退/适配/激活 | 已读相关全文与仿真；未运行代码 |
| P36/P40 | 接收机 / BLER 预测 | 不需要 | 非主要对象 | 复核 / 阈值触发 | 再训练 / 在线微调 | 仿真；非同一协议场景 |
| P37 | 干扰/定位/波束预测集 | 不需要 | 非研究对象 | 统计风险估计 | 非发布恢复协议 | 理论 + 数值评估 |
| LCMAgent 拟研究 | 无线功能，含单侧与双侧 | 必要性待证 | 已有基础 | 有代价且会失效的跨端证据 | 明确假设下的恢复 | 尚无本项目结果，不填“优于” |

**定位判断**：有希望的交叉点不是任意单列，而是“已有监测、适配与安全执行基础上，选择有成本的证据和生命周期动作，并保证其配置绑定与故障恢复”。这仍是研究假设，不是排他性首次结论。

## 9. 把“协同”转成可检查的问题

以下是项目建议建模，不是声称文献已经实现。

### 9.1 发布对象是功能契约，配对只是一种特例

```text
FunctionManifest = {
  use_case, model_digest, inference_placement,
  input_output_schema, radio_config_dependencies,
  measurement_policy, sensor_or_anchor_calibration,
  scenario_scope, validation_and_calibration_provenance,
  resource_requirements, monitor_policy, fallback,
  optional_pair_binding
}
```

波束模型绑定码本与测量集合，定位模型绑定坐标/锚点，接收模型绑定导频和软输出语义；这些不能压成 encoder/decoder pair。单侧功能可以先完成本地安全更新，再按实际需要协调测量或网络配置。只有确需联合推理的功能才扩展为下面的配对契约。此处为项目建模建议，不是标准化新对象。

**双侧 CSI 特例：**

```text
PairManifest = {
  encoder_digest, decoder_digest,
  compatibility_family, input_output_schema,
  quantization, latent_layout, feedback_config,
  preprocessing, supported_scenarios,
  resource_requirements, fallback_pair,
  validation_provenance
}
```

仅有相同 `model_id` 不够：同维度 latent 可能语义不同；同权重在不同归一化、量化、码本/反馈配置下也可能不兼容。字段是本项目建议，应映射现有对象，不能创造一个同名“新标准”。[S01, S02, P02]

### 9.2 证据绑定主体、时间、配置与适用范围

```text
Evidence = {
  subject, function_manifest_digest, optional_pair_digest, config_epoch,
  observation_window, generated_at, expires_at,
  source, measurement_method, sample_count,
  uncertainty, resource_reservation,
  permitted_use
}
```

不只是给 observation 加 timestamp，还要回答：

- 谁产生、验证与撤销证据？来源身份可信是否意味着测量真实？
- shadow test 和实际激活是否使用相同配置？
- 测量之后温度、内存、业务负载是否已变化？
- 同一资源余额是否被多个事务重复使用？
- 能否跨 UE、小区、session 或模型复用证据？

P09 的契约检查直接相关，但它假设暴露的元数据/来源信息正确，不评估执行器安全与并发控制。`source` 字段或签名本身不证明物理事实真实。[P09]

### 9.3 明确决策与成本

隐藏状态包括本地温度/内存、实际模型配置、环境分布和消息状态；动作包括继续运行、补测、重新校准、选模型、有限微调、准备/提交、等待、拒绝和 fallback。不同用例的业务损失需要各自归一化或单独报告；不能把米、dB 和 BLER 原始量直接求和。

```text
最小化：业务退化损失 + 监测/反馈成本 + UE 计算能耗
        + 下载/切换成本 + Agent 推理/工具开销

约束：功能/无线配置兼容，必要时配对兼容；权限有效、资源可行、证据有效
      隐私/数据政策满足、fallback 可执行
```

不能把所有约束塞进奖励函数就声称硬安全。应区分结构性拦截、统计风险与业务容忍度；没有数据时不要指定看似精确的权重。优先报告 Pareto 曲线和成本分项。

### 9.4 双侧特例：“共同激活”要写性质，不只写状态名

| 性质 | 可执行解释 | 前提 |
|---|---|---|
| Pair safety | 数据的 epoch/配对标识属于接收端接受的兼容集合，否则拒绝/走非 AI 路径 | 实验数据路径可识别配置；不声称已有标准字段 |
| No stale authorization | 旧资源确认、旧 session 或过期测量不能授权新事务 | epoch/nonce、有效期与撤销语义明确 |
| Idempotence | 重复消息不导致重复激活、下载或扣预算 | 稳定事务 ID 和去重状态 |
| Crash recovery | 重启后从持久状态确认已完成/未完成 | 不能以 LLM 对话记忆替代日志 |
| Resource safety | 并发事务不超卖 UE 内存或共享 decoder 资源 | 验证与预留有确定性协调 |
| Recoverability | 在声明假设下恢复兼容配对或非 AI 模式 | 旧模型保留、fallback 可用、重连策略明确 |

控制面 ACK 不保证后续数据使用正确配对。可研究双版本接收、显式 epoch 和过期数据处置，但必须算内存与尾延迟成本。

允许永久断连时，不能无条件同时承诺“两端立即共同完成”与“系统一直可用”。最后 ACK 或协调者失效后，应选择阻塞、保守 fallback 或有限旧版本窗口，并说明安全/活性的取舍。[P20]

### 9.5 非交换性与 TOCTOU 是关键难点

```text
检查资源 -> 下载 -> 再检查 -> 预留 -> 提交
```

与“检查资源 → 别的应用占用内存 → 提交”不同。类似地，旧量化配置上的 KPI 不能直接验收新配置。

因此要研究证据到动作之间的状态变化、并发和在途数据，而不只是在每个状态节点调用相同检查。InvaRAN 提醒我们测试验证器与状态假设本身，而不只测试 LLM JSON。[P21]

## 10. 哪些不能再宣称，哪些假设值得验证

### 10.1 新颖性负面清单

| 不宜单独作为贡献 | 先例 | 额外需要证明 |
|---|---|---|
| 双端组件 + LLM 编排 | Dual-MCP [P12] | 发布任务中的增量机制/收益 |
| 多 Agent、分层和工具调用 | P07/P08/P10 | 同工具、同预算下的决策增益 |
| LLM 提议、确定性执行 | P11/P18 | 跨端证据/并发/故障新增性质 |
| 监测后切换/更新 | P01/P03/P04/P26/P27/P36/P40 | 同监测预算下的风险—成本改善 |
| 推广到波束等单侧功能 | S01/P26/P27/P36/P40 | 不是新场景即可成立，须验证新增决策机制 |
| 两端模型配对/兼容 | S01/P02 | 新运行条件或失败语义 |
| PREPARE/COMMIT/ACK 与 rollback | P05/P20 | 明确假设下的性质或更低成本 |
| Agent 主动请求数据 | P09/P19 | 非 LLM 主动测量解释不了的收益 |
| 不传原始数据即“隐私保护” | 本地摘要和模型保密不等于形式隐私 | 威胁模型、泄露面与保护机制 |

### 10.2 主线 H1：预算约束下的证据驱动生命周期决策

**假设**：证据位置、代价、延迟和时效不同，按风险与信息价值选择补测、校准、模型切换或适配，能在相同用例风险目标下减少总成本。风险应按用例分别定义，不能将所有异常标成“应更新”。

**要击败**：规则 LCM、序贯检测/主动测量、确定性工作流，以及同样有 guard 和 fallback 的 Agent。

**可反证场景**：波束预测差是定位偏差，正确动作应校准；AI 与传统 BM 都差，切换无收益；定位模型跨日期仍可用，不应过度更新；接收机 OOD 但参考复核无性能劣势，应继续运行。这些都要纳入，而非只设计“检测后换模型即可获益”的数据。

**可能不成立**：动作空间小、统计模型已知、完整状态廉价可得。此时枚举/简单策略可能更好，应收缩而非故意削弱基线。

### 10.3 支撑 H2：function/config-aware、failure-aware 执行

**假设**：常规版本检查之外，绑定功能/配置契约、必要的双侧配对、资源预留、epoch 和恢复记录，可减少并发/崩溃/延迟造成的错误发布或缩短恢复。

这是系统机制贡献，不能自动归功于 LLM。同一执行层应配给不同规划器，再通过移除机制的消融检验独立价值。

### 10.4 条件 H3：LLM 是否值得保留

仅在工具、厂商能力或多步骤约束确实组合复杂时，检验 LLM 是否减少人工工作流开发、适应新工具或改善风险—成本。测试组合冻结后评估，不能用全部测试故障/工具模板调 prompt。

若非 LLM 规划器达到相同 Pareto 前沿，应定位为“证据驱动端网安全 LCM”，把 LLM 作为可选运维接口，而非论文成立前提。

### 10.5 三条可以具体做的非 CSI 路线

以下是由文献导出的**待验证机会**，不是声称无人研究。建议第一条为主线，其余作为扩展或替代，避免一次实现全部空口 AI。

| 路线 | 要回答的具体问题 | 最小可验证系统 | 必须正面比较 | 何种结果才有价值 |
|---|---|---|---|---|
| A. 预算感知波束 LCM | 当前预测差，是模型失配、定位/感知偏差还是传播本身变差？下一次应测 top-K、扩展扫描、校准还是换模型？ | 时间有序轨迹 + 候选模型库 + 可计价测量接口 + 传统扫描回退；随后补闭环仿真 | P26 双性能预测、P27 候选评估、固定/自适应测量与适用时的 P37 校准 | 在相同失联/速率损失约束下减少扫描、无效切换和总计算，而非仅提高分类率 |
| B. 定位辅助波束的依赖治理 | 定位模型/坐标或锚点改变后，波束模型是否仍有效？应该修上游还是换下游？ | 一个定位器 + 一个位置辅助波束器，显式绑定坐标、校准、时间戳与码本 | 各功能独立 LCM、全部联动更新、确定性依赖规则 | 更少级联失配与过度重训；必须有定位误差/测量真值，不能只用人为故障标签 |
| C. 选择“更新方式”而非只选模型 | 延迟标签和设备预算有限时，继续、换库中模型、LightTune 式微调、参考复核或停用，哪个更划算？ | 一个 BLER 预测或神经接收功能，限定候选动作与更新预算 | P36、P40、周期/阈值更新及无 LLM 成本敏感选择器 | 同业务风险下更低更新/复核代价，且错误适配可恢复；不以更多标签和算力换收益 |

第一条最贴近本次“波束管理也能做”的诉求；第二条更强调跨功能语义依赖；第三条更强调生命周期动作空间。三者共享证据和执行接口，但业务风险定义与验证器不同。只有在**冻结共享机制后**仍能迁移，才讨论通用性；为每个案例另写一套流程不能证明统一方法。

## 11. 实验必须拆开：架构、执行与 Agent 的价值

### 跨用例直接基线先于 Agent 消融

所有策略使用同一候选库、证据接口、执行器和预算；不能给 Agent 更多隐藏标签。波束至少比较无 LCM、dataset/context ID 选择、P27 式周期监测和候选评估；还需比较 P26 式 AI/传统 BM 双性能预测，避免无效 fallback；全文已补读但代码未复现。接收机比较 P36 式“检测 + 参考接收机复核 + 再训练”；链路适配比较 P40 式阈值触发微调、持续更新和表式 OLLA。统计层比较 P19 式受控观测思想及适用条件下的 P37 风险校准。以上复现/移植需分别说明忠实程度，不能只借用论文名称。


### 11.1 三条比较轴

| 轴 | 固定项 | 变化项 | 回答什么 |
|---|---|---|---|
| 模型部署架构 | 数据、反馈预算、负载、业务指标 | 单侧/双侧模型及管理总成本 | 双侧模型是否值得用 |
| 执行/恢复 | 同模型对、候选序列、轨迹、规划器 | 契约、预留、epoch、恢复机制 | 安全来自哪里 |
| 证据/规划 | 同模型库、验证器、执行器、工具、预算 | 规则、统计、确定性规划、LLM | Agent 是否额外有效 |

“单 BS Agent + 被动 UE”可做弱消融，不应是主要对手：合理的非 Agent 系统也会本地检查和回退。

### 11.2 建议基线

| 编号 | 基线 | 应给予的能力 |
|---|---|---|
| B0 | Rule-LCM | 双端检查、阈值监测、hysteresis、fallback |
| B1 | Statistical-LCM | 同执行层；变化检测、序贯测试、预算化监测 |
| B2 | Deterministic-Workflow | 同工具；DAG/状态机、条件分支、重试恢复 |
| B3 | Non-LLM Active Evidence | 同动作集；不确定性/信息价值/成本驱动补测 |
| B4 | Single-Planner + UE Validator | 网络 LLM；UE 确定性验证；公共执行层 |
| B5 | WirelessAgent++/Dual-MCP 式适配 | 同接口与执行层；标明复现或思想适配 |
| B6 | Evidence-Assured Agent | P09 式证据检查/修复，适配 LCM |
| B7 | LCMAgent | 公共执行层上的拟研究证据选择 |
| B8 | Oracle / Offline Bound | 明确完整状态/离线最优，不混入在线排名 |

不要求第一版复现所有论文，但至少要有 B0–B4 和一个最近 Agent 近邻。场景/代码不能直接运行时，写“思想适配”，不声称逐字复现。

### 11.3 公平性

- 同证据权限：不能只给 LCMAgent 本地温度/内存，让基线仅看 BS KPI。
- 同 guard：不能让基线绕过验证，却让 LCMAgent 受保护。
- 同模型库、预下载和 fallback 条件；下载成本一致计入。
- 比较固定预算及各自 Pareto 前沿，不靠多测量获胜。
- 同超时、重试、token 和 API 失败处理；失败不能从分母删除。
- 配对轨迹与随机种子；按独立 UE/场景轨迹算区间，不把相关快照当独立样本。
- 将验证器拦截收益和规划收益分开报告。

## 12. 证据获取本身也需要实验

### 12.1 从廉价摘要到高代价观测

下表为候选动作，不代表已有统一标准信令或设备实现。

| 动作 | 回答问题 | 成本/偏差 |
|---|---|---|
| 能力/模型摘要 | 模型配置是否存在、兼容 | 可能过期，不代表当前内存 |
| 资源测量与预留 | 激活期间资源是否可用 | TOCTOU、竞争、挤压其他业务 |
| 输入分布摘要 | 是否偏离训练区域 | OOD 不必然差，也可能泄露场景 |
| 小规模 shadow | 候选在近期本地样本表现 | 双跑能耗、代表性和选择偏差 |
| 稀疏参考测量/标签 | NMSE、SGCS 等是否退化 | 参考信号、反馈和标签消耗资源 |
| 链路/业务观测 | 吞吐量、BLER、SLA 是否改善 | SNR/调度/负载混淆，不能自动归因 |

上表是 CSI 特例。波束补测要记录扫描集合与开销；定位补测要交代锚点和真值来源；接收机复核要记录并行参考处理开销；BLER 在线适配要记录标签延迟、更新次数和预算。P26/P27/P36/P40 提供相应用例的直接竞争路线，P37 提供风险校准基础。

P01–P04 是监测/适配背景，P19 是观测选择基础。比较的是证据组合的决策价值，而非日志收了多少字段。

### 12.2 分开注入四类状态

1. 输入分布变，但模型仍满足业务目标：是否过度更新？
2. 模型失配，但绝对业务 KPI 未下降：阈值是否漏报？
3. SNR/负载使业务下降，模型没问题：是否误诊？
4. 模型/业务均退化，测量部分过期/丢失：能否补测与恢复？

不能只构造“OOD 标签出现，正确动作一定换模型”的合成任务。标签应由真实兼容性、资源与业务结果定义，不由为某 Agent 定制的规则循环论证。

### 12.3 切分与统计风险

训练、阈值校准、策略选择与测试分开；按场景/轨迹/UE/站点分组，不只随机打散高度相关快照。

主动采样改变观测分布；反复查看同一验证集、直到“看起来足够好”再停止，会破坏固定样本区间的解释。可采用预注册观察次数、独立验收集或适用序贯方法；未验证假设前不宣称形式风险保证。P19 是序贯背景，具体方案是本项目要求。

## 13. 故障与指标：避免安全率漂亮但系统不能用

### 13.1 故障矩阵

| 故障域 | 必须测试 | 观察点 |
|---|---|---|
| 模型/格式 | 错配、量化/latent 不一致、损坏 | 阻断与正确诊断 |
| 波束配置 | 码本索引重排、Set A/B 改变、位置/相机输入延迟 | 合法输出却物理含义错误；补测/撤销证据 |
| 定位依赖 | 锚点/坐标系变更、时钟与校准偏差、真值缺失 | 代理漂移与真实位置误差分开，避免误更新 |
| 接收/链路 | 导频/MCS/天线配置变化、CRC 或标签延迟 | 结构兼容、软输出语义、实时期限与更新验收 |
| 资源 | 准备后内存减少、温升、并发预留 | 重验/撤销、超预算 |
| 时效 | KPI 延迟/乱序、旧 session 重放 | 过期授权拒绝 |
| 消息 | READY/COMMIT/ACK 丢失/重复/重排 | 幂等、阻塞与恢复 |
| 崩溃 | UE/协调者在不同提交点重启 | 持久状态恢复，而非对话补事实 |
| 共享资源 | 多 UE 同时激活、共享 decoder 改变 | 跨 UE 失配与超卖 |
| 数据面 | 旧 epoch 数据在新模型后到达 | 误解码、过渡能力 |
| 回退 | 旧模型卸载、fallback 不可用/延迟 | 真实恢复，而非日志成功 |
| 决策/API | LLM 超时、JSON 错、工具失败/无权限 | HOLD/RETRY/fallback |
| 观测污染 | 单位错误、来源错误、工具返回恶意文本 | 数据不变指令，不越权 |

第一版可仅研究非恶意 crash/通信/资源故障；没有攻防实验，不宣称对被攻陷 BS 或恶意 UE 同样安全。

### 13.2 指标注明分母与窗口

| 指标 | 建议定义 | 防止误读 |
|---|---|---|
| Unsafe release / episodes | 违规发布事件 / 全决策事件 | 大量 HOLD 会稀释，须与下一项并列 |
| Unsafe release / releases | 违规发布 / 实际发布 | 与 P09 的分母不同 |
| Safe progress | 真可发布机会中按时安全完成比例 | 拒绝一切不能优胜 |
| Missed beneficial update | 有收益却未在有效窗口发布比例 | 捕捉过度保守；收益预先定义 |
| Configuration mismatch exposure | 功能/配置错配时长、受影响数据/推理量；CSI 另列 pair mismatch | 不只计次数，也不把所有用例写成模型对 |
| Effective activation | 实际数据路径使用目标功能版本及正确配置的时间 | API 成功不等于生效 |
| Recovery latency | 故障发生/可检测时刻至业务恢复，注明起点 | 不排除监测延迟 |
| Evidence cost | 无线资源、字节、UE 推理/能耗、测量次数 | 少传数据未必少耗资源 |
| End-to-end utility | 吞吐量/BLER/SLA deficit 与过渡损失 | NMSE 不等于业务收益 |
| Churn | 切换、反复回退、重复补测 | 揭示振荡 |
| Planner overhead | token、API 成本、时延分位数、工具与超时 | 不只报平均时间 |
| Rollback/recovery success | 声明故障集合和条件下的成功比例 | 不悄悄删除失联/无备用资源样本 |

P09 的 Unsafe APPLY 以全部 episodes 为分母；P05 的 control steps 无校准周期不能换成毫秒。[P05, P09]

### 13.3 三类必须同时报告的结果

1. **安全—进展**：违规发布与 safe progress，显示“全拒绝”退化解。
2. **风险—成本**：不同监测/反馈/能耗预算下的错误和业务损失，排除多采数据优势。
3. **故障强度—恢复**：按丢包、延迟、竞争与崩溃位置分层，显示假设边界。

本项目尚无这些实测；这是文献导出的证据要求，不是已有结果。

## 14. 实施顺序与收缩条件

### 14.1 不使用 LLM，先做对执行闭环

建议先做一个波束管理单侧功能，再做固定预训练 CSI 配对的强耦合对照；两者复用执行骨架，但保留各自测量、风险和回退语义。波束侧先在时间有序真实轨迹上验证证据策略，之后才接链路仿真/闭环环境；不能把离线 top-K 回放写成在线系统实测。提供传统扫描/非 AI 或已验证旧模型回退，做 manifest、epoch、验证、故障注入和业务观测。先确认能区分兼容/不兼容、过期/有效、资源足/不足，以及真实恢复和“日志完成”。

具体数据与工具复用同目录《LCMAgent实验数据与仿真工具链调研》。数据集名字不是实验自动可复现的保证。本轮检索与书目争议处理另见 [检索与核验记录](../相关工作/检索与核验记录.md)。

### 14.2 冻结执行层，比较证据策略

加入规则、变化检测、固定工作流和非 LLM 主动补测。至少出现非平凡权衡：不测有风险，全测太贵，错测延误恢复。若廉价阈值可完美分离全部场景，应检查设定是否太容易。

### 14.3 有理由再引入 LLM

给相同工具/预算，考察新组合、异构能力和跨步骤约束；分离公共 validator 与规划收益。

| 观察 | 定位 |
|---|---|
| 验证器获得绝大部分收益 | 安全发布/恢复系统，LLM 可选 |
| 非 LLM 主动测量相当且更便宜 | 证据选择/统计 LCM，不强推 Agent |
| 只改善自然语言便利性 | 运维接口/demo，不夸大算法贡献 |
| 同执行层上，新组合风险—成本显著改善 | 支持受限 Agent 决策贡献 |
| 双侧总收益不及单侧 | 限定适用区间或退回单侧管理 |

首轮建议用单侧波束与双侧 CSI 对照，验证共享机制和专用约束，而非另写一套 prompt 后并排。定位、接收机或 ISAC 作为后续扩展，应由标签可得性、耦合和故障语义决定。

## 15. 推荐研究定位与表述

### 15.1 建议主标题

**LCMAgent：预算约束与状态不确定条件下的无线 AI 功能证据驱动生命周期编排。**

不以“BS/UE 双 LLM Agent”为标题核心：它突出数量，与 Dual-MCP、AgentRAN 正面竞争，却弱化真正要测的风险/成本问题。

### 15.2 Related Work 结构

1. 无线 LCM/互操作：S01/S02、P01/P02，交代已有管理基础。
2. CSI 监测/漂移/更新：P03–P06，纳入非 Agent 竞争者与单侧替代。
3. 无线 Agent/安全控制：P07–P17，正面比较 Dual-MCP、A1gent、WirelessOpsAgent。
4. 非 CSI 执行与生命周期：P26–P36/P40，前置波束选择/适配与接收机恢复，纳入定位、真实数据及链路自适应。
5. 方法基础：P18–P21/P28/P37，交代约束、观测、统计监测、风险校准、事务和验证器测试；P38/P39 补充部署与泛化背景。

### 15.3 推荐段落

> 已有研究已建立无线 AI/ML 生命周期与跨厂商互操作框架，研究波束模型的选择、监测及端网适配，提出神经接收机的部署后复核与再训练，以及资源受限设备的轻量在线微调 [S01, S02, P01–P04, P26, P27, P36, P40]；无线 Agent 工作又提供工具编排、确定性门控及证据修复 [P09, P11, P12]。本研究不以双端部署、非 CSI 应用或安全门本身为新意，而关注其后的决策问题：在状态分散、证据有成本且会失效、配置可能变化及动作可能部分失败时，如何选择补测、校准、模型选择或适配，并将验收与可靠执行衔接。我们拟用单侧波束与双侧 CSI 的差异化约束检验共享机制，在同一执行层比较规则、统计方法、非 LLM 主动测量和受限 Agent，评估风险—业务损失—证据成本及 LLM 的增量价值。

这是研究计划。实验前不把“拟比较”“检验”改成“显著优于”“保证”或“首次”。

## 16. 参考文献、状态与复核入口

共 **40 项论文/论文型工作、2 项标准与 1 项已有会议讨论材料**。编号不代表质量排名；A/B/C 见 §2.3。“公开稿”不意味着一定没有正式版本。文中同时描述框架和实现等成分；书目中的类型按主要贡献归类为 survey、pure method、method + benchmark、system/tool 或 theory/proof。

### 16.1 标准与讨论材料

- **[S01]** 3GPP. *TR 38.843 V19.0.0: Study on Artificial Intelligence (AI)/Machine Learning (ML) for NR air interface*. Release 19, 2025-09。technical report；A，相关章节。本地 `标准文件/38843-j00.pdf`；[规范档案](https://www.3gpp.org/ftp/Specs/archive/38_series/38.843/)。未逐项核验所有后续版本。
- **[S02]** 3GPP / ETSI. *TS 28.105 V18.4.0 / ETSI TS 128 105 V18.4.0: Artificial Intelligence/Machine Learning (AI/ML) management*. 2024-07。technical specification；A，相关对象/流程。[ETSI PDF](https://www.etsi.org/deliver/etsi_ts/128100_128199/128105/18.04.00_60/ts_128105v180400p.pdf)。
- **[D01]** *R1-2508811, AI/ML for 6GR, Moderator’s Summary, revision 4*。会议讨论材料，以已有文件为依据，不认定为最终规范。本地 `标准文件/R1-2508811.pdf`、`标准文件/R1-2508811-第三章详解.md`。

### 16.2 生命周期、互操作与 CSI

- **[P01]** Chu-Hsiang Huang, Yuan-Chih Fan Chiang, Chao-Kai Wen, Geoffrey Ye Li. *AI/ML Life-Cycle Management for Interoperable AI-Native RAN*. arXiv:2507.18538，2025 首稿；内容依据 2026-08-26 v3。公开稿注明 *IEEE Communications Standards Magazine* 接收；检出 DOI `10.1109/MCOMSTD.2026.3728497`，具体卷期日未确认。survey；A，§II–IV。[固定全文](https://arxiv.org/html/2507.18538v3)。
- **[P02]** Dani Korpi et al. *Demonstrating Interoperable Channel State Feedback Compression with Machine Learning*. 2025 公开稿；*IEEE Wireless Communications* 33(3), 126–133, 2026 卷期；DOI `10.1109/MWC.2025.3630622`。system/tool；A，训练、原型与限制。[全文](https://arxiv.org/html/2506.21796v1)；[正式记录](https://doi.org/10.1109/MWC.2025.3630622)。卷期与 online-first 年份区分。
- **[P03]** Jiajia Guo, Shaodan Ma, Chao-Kai Wen, Shi Jin. *Performance Monitoring-Enabled Reliable AI-Based CSI Feedback*. *IEEE Transactions on Wireless Communications*, 2025, 197–212；DOI `10.1109/TWC.2024.3490600`。pure method；B，不复原全部算法。[作者机构记录](https://researchportal.hkust.edu.hk/en/publications/performance-monitoring-enabled-reliable-ai-based-csi-feedback/)；[DOI](https://doi.org/10.1109/TWC.2024.3490600)。
- **[P04]** Haozhen Li, Xinyu Gu, Zhiling Du, Jiahui Chen, Zhenyu Liu, Lin Zhang. *Scenario-Aware Framework for DL-Based CSI Feedback With Unified Training, Monitoring, and Updating*. *IEEE Internet of Things Journal* 12(18), 37512–37528, 2025；DOI `10.1109/JIOT.2025.3585120`。pure method；B，出版社摘要/书目。[IEEE 记录](https://ieeexplore.ieee.org/document/11063393)。
- **[P05]** Dharmendra Kumar. *Toward a Layer-2 Trigger for AI/ML Lifecycle Management in 6G*. arXiv:2609.14517v1，2026-09-13。pure method；公开预印本，正式出版未确认；A，§3–5 与限制。[固定全文](https://arxiv.org/html/2609.14517v1)。
- **[P06]** *Deep Learning for CSI Feedback: One-Sided Model and Joint Multi-Module Learning Perspectives*. arXiv:2405.05522；*IEEE Communications Magazine*，2025。survey；B，摘要与作者解读。[公开记录](https://arxiv.org/abs/2405.05522)；[作者机构解读](https://research.samsung.com/blog/Deep-Learning-for-CSI-Feedback-One-Sided-Model-and-Joint-Multi-Module-Learning-Perspectives)。

### 16.3 无线 Agent 与安全编排

- **[P07]** Jingwen Tong et al. *WirelessAgent: Large Language Model Agents for Intelligent Wireless Networks*. arXiv:2505.01074，2025；*China Communications*，2026-03 正式记录，DOI `10.23919/JCC.FA.2025-0163.202603`。system/tool；B + 原有本地阅读。[公开记录](https://arxiv.org/abs/2505.01074)；[DOI](https://doi.org/10.23919/JCC.FA.2025-0163.202603)。
- **[P08]** Jingwen Tong et al. *WirelessAgent++: Automated Agentic Workflow Design and Benchmarking for Wireless Networks*. arXiv:2603.00501，2026。method + benchmark；按公开稿引用，不断言无正式版本；A，工作流/benchmark。[全文](https://arxiv.org/html/2603.00501v1)。
- **[P09]** Zijian Lu et al. *WirelessOpsAgent: A Benchmark and Agent Design for Action Assurance in Wireless Networks*. arXiv:2608.08277v1，2026。benchmark 名为 **WirelessOptBench**。method + benchmark；公开预印本；A，Table II/III、§V-D 与 §VI。[固定全文](https://arxiv.org/html/2608.08277v1)。
- **[P10]** *AgentRAN: An Agentic AI Architecture for Autonomous Control of Open 6G Networks*. arXiv:2508.17778，2025；作者项目列 *IEEE Communications Magazine*，2026，DOI `10.1109/MCOM.001.2500563`，具体卷期日未确认。system/tool；B，摘要与项目。[公开记录](https://arxiv.org/abs/2508.17778)；[作者项目](https://github.com/wineslab/agentran)。
- **[P11]** Hengxu Li, Dongkuan Xu, Mingzhe Chen, Yuchen Liu. *Agentic Open RAN: A Deterministic and Auditable Framework for Intent-Driven Radio Control*. ICC 2026；DOI `10.1109/ICC59461.2026.11586905`；arXiv:2604.13384。system/tool；A，架构、门控与冲突治理。[全文](https://arxiv.org/html/2604.13384v1)；[DOI](https://doi.org/10.1109/ICC59461.2026.11586905)。
- **[P12]** Eduardo Baena, Ankita Mandal, Dimitrios Koutsonikolas. *Demo: Human-in-the-Loop Agentic Reconfiguration of Edge 5G Networks via Dual-MCP and LLM Reasoning*. ACM MobiHoc 2025, 391–392；DOI `10.1145/3704413.3765314`。system/tool，demo；A，两页 PDF，不按长文证据强度评价。[作者 PDF](https://ece.northeastern.edu/fac-ece/dkoutsonikolas/publications/demo_mobihoc25.pdf)；[DOI](https://doi.org/10.1145/3704413.3765314)。
- **[P13]** Zhou Fang, Shuping Dang, Zhenrong Zhang, Yan Zhang. *OnlineCritic-xApp: Online Learning for LLM-Assisted RAN Slice Resource Management*. IEEE INFOCOM 2026；DOI `10.1109/INFOCOM59046.2026.11571592`。pure method；C，保留本地结论，未复算数值。[DOI](https://doi.org/10.1109/INFOCOM59046.2026.11571592)。
- **[P14]** Dae Cheol Kwon, Xinyu Zhang. *Open RAN Conflict Agents: Detecting and Mitigating xApp Conflicts with Generative Agents*. system/tool；C；作者公开材料，正式出版状态未独立确认。[作者主页](https://xyzhang.ucsd.edu/)。不以本地文件名作为出版证明。
- **[P15]** *PACIFISTA: Conflict Evaluation and Management in Open RAN*. arXiv:2405.04395，2024 首稿、2025 修订；公开记录列 *IEEE Transactions on Mobile Computing*，2025。system/tool；B，摘要与书目。[原始记录](https://arxiv.org/abs/2405.04395)。
- **[P16]** Tuan V. Ngo et al. *LLM-Based Net Analyzer rApp for Explainable and Safe Automation in O-RAN Non-RT RIC*. arXiv:2603.13775v1，2026-03-14。system/tool；按公开稿引用；A，方法、testbed 与审批边界。[固定全文](https://arxiv.org/html/2603.13775v1)。
- **[P17]** Xingqi Wu, Yuhui Wang, Junaid Farooq, Juntao Chen. *LLM-Driven Agentic AI Approach to Enhanced O-RAN Resilience in Next-Generation Networks*. IEEE INFOCOM Workshops 2025；DOI `10.1109/INFOCOMWKSHPS65812.2025.11152722`。system/tool；C，不声称新复算。[DOI](https://doi.org/10.1109/INFOCOMWKSHPS65812.2025.11152722)。

### 16.4 方法基础与背景

- **[P18]** *AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents*. arXiv:2503.18666，2025；公开记录列 ICSE 2026, 2938–2950。system/tool；B，摘要与出版信息。[公开记录](https://arxiv.org/abs/2503.18666)。
- **[P19]** Venugopal V. Veeravalli, Georgios Fellouris, George V. Moustakides. *Quickest Change Detection with Controlled Sensing*. *IEEE Journal on Selected Areas in Information Theory* 5, 1–11, 2024；arXiv:2310.17223。theory/proof；B，问题、方法与定理适用条件摘要。[公开记录](https://arxiv.org/abs/2310.17223)。
- **[P20]** Jim Gray, Leslie Lamport. *Consensus on Transaction Commit*. *ACM Transactions on Database Systems* 31(1), 133–160, 2006；DOI `10.1145/1132863.1132867`。theory/proof；B，作者机构记录与核心问题。[Microsoft Research 原始记录](https://www.microsoft.com/en-us/research/publication/consensus-on-transaction-commit/)；[DOI](https://doi.org/10.1145/1132863.1132867)。
- **[P21]** Tianchang Yang, Ali Ranjbar, Gang Tan, Syed Rafiul Hussain. *Invariant-Guided Logical Testing of Open RAN Controllers*. USENIX Security 2026, 711–730。system/tool；B，官方摘要及 artifact。[正式记录/PDF](https://www.usenix.org/conference/usenixsecurity26/presentation/yang-tianchang)；[artifact](https://github.com/SyNSec-den/INVARAN)。
- **[P22]** Chao-Kai Wen, Wan-Ting Shih, Shi Jin. *Deep Learning for Massive MIMO CSI Feedback*. *IEEE Wireless Communications Letters*，2018；arXiv:1712.08919，2017 首稿。pure method；B，摘要和书目。[公开记录](https://arxiv.org/abs/1712.08919)。
- **[P23]** Yiming Cui et al. *Exploring the Potential of Large Language Models for Massive MIMO CSI Feedback*. arXiv:2501.10630，2025-01-18。pure method；B，摘要；正式出版未确认。[公开记录](https://arxiv.org/abs/2501.10630)。
- **[P24]** Wenwen Xie et al. *Agentic AI for ISAC: Analysis, Framework, and Case Study*. arXiv:2512.15044，2025 首稿，2026-06-27 v2。survey；B，摘要与版本；正式出版未确认。[公开记录](https://arxiv.org/abs/2512.15044)。
- **[P25]** Harrison Mfula, Jukka K. Nurminen. *Adaptive Root Cause Analysis for Self-Healing in 5G Networks*. IEEE HPCS 2017；DOI `10.1109/HPCS.2017.31`。pure method；C，原有阅读 + 书目核验。[DOI](https://doi.org/10.1109/HPCS.2017.31)。

### 16.5 波束、定位、接收机、统计可靠性与部署扩展

- **[P26]** Sun, Chen and Zhao, Le and Cui, Tao and Li, Haojin and Bai, Yingshuang and Wu, Songtao and Tong, Qiang. *AI Model Selection and Monitoring for Beam Management in 5G-Advanced*. IEEE Open Journal of the Communications Society，2024。method / beam management；A。[原始记录](https://doi.org/10.1109/OJCOMS.2023.3337850)；[逐篇详解](../相关工作/论文详解/P26_BeamModelSelection.md)；BibTeX `sun2024beammodelmonitoring`。
- **[P27]** Go, Jewoo and Park, Taeje and Sung, Wonjin. *Model Adaptation for Lifecycle Management in AI-native 5G/6G Networks*. 2025 16th International Conference on Information and Communication Technology Convergence (ICTC)，2025。pure method / LCM procedure；A。[原始记录](https://doi.org/10.1109/ICTC66702.2025.11388480)；[逐篇详解](../相关工作/论文详解/P27_BeamLifecycleAdaptation.md)；BibTeX `go2025beamlifecycleadaptation`。
- **[P28]** Kaswan, Priyanka and Marzban, Mohamed F. and Nam, Wooseok and Akkarakaran, Sony and Luo, Tao. *Statistical AI/ML Model Monitoring for 5G/6G: Interference Prediction Case Study*. 2024 IEEE International Conference on Communications Workshops (ICC Workshops)，2024。pure method / monitoring；A。[原始记录](https://doi.org/10.1109/ICCWorkshops59551.2024.10615307)；[逐篇详解](../相关工作/论文详解/P28_StatisticalMonitoring.md)；BibTeX `kaswan2024statisticalmonitoring`。
- **[P29]** Polese, Michele and Restuccia, Francesco and Melodia, Tommaso. *DeepBeam: Deep Waveform Learning for Coordination-Free Beam Management in mmWave Networks*. Proceedings of the Twenty-second International Symposium on Theory, Algorithmic Foundations, and Protocol Design for Mobile Networks and Mobile Computing，2021。method + experimental dataset；B。[原始记录](https://doi.org/10.1145/3466772.3467035)；[逐篇详解](../相关工作/论文详解/P29_DeepBeam.md)；BibTeX `polese2021deepbeam`。
- **[P30]** Alkhateeb, Ahmed and Charan, Gouranga and Osman, Tawfik and Hredzak, Andrew and Morais, João and Demirhan, Umut and Srinivas, Nikhil. *DeepSense 6G: A Large-Scale Real-World Multi-Modal Sensing and Communication Dataset*. arXiv / 公开稿，2022。pure benchmark / dataset；B。[原始记录](https://arxiv.org/abs/2211.09769)；[逐篇详解](../相关工作/论文详解/P30_DeepSense6G.md)；BibTeX `alkhateeb2022deepsense6g`。
- **[P31]** Vladimirov, Rodion and Laskov, Pavel. *Challenges of Predictive Beamforming Using Geographical Positioning: Insights from the DeepSense Dataset*. 2025 16th IFIP Wireless and Mobile Networking Conference (WMNC)，2025。empirical analysis / benchmark study；A。[原始记录](https://doi.org/10.23919/WMNC67099.2025.11299263)；[逐篇详解](../相关工作/论文详解/P31_PredictiveBeamformingDrift.md)；BibTeX `vladimirov2025predictivebeamforming`。
- **[P32]** Studer, Christoph and Medjkouh, Saïd and Gönültaş, Emre and Goldstein, Tom and Tirkkonen, Olav. *Channel Charting: Locating Users Within the Radio Environment Using Channel State Information*. IEEE Access，2018。pure method；B。[原始记录](https://doi.org/10.1109/ACCESS.2018.2866979)；[逐篇详解](../相关工作/论文详解/P32_ChannelCharting.md)；BibTeX `studer2018channelcharting`。
- **[P33]** Müller, Till-Yannic and Zumegen, Frederik and Wiesmayr, Reinhard and Studer, Christoph. *Spatial and Temporal Generalization of CSI-based Neural Positioning*. arXiv / 公开稿，2026。method + real-world evaluation；A。[原始记录](https://arxiv.org/abs/2606.18150)；[逐篇详解](../相关工作/论文详解/P33_NeuralPositioningGeneralization.md)；BibTeX `muller2026neuralpositioning`。
- **[P34]** Honkala, Mikko and Korpi, Dani and Huttunen, Janne M. J.. *DeepRx: Fully Convolutional Deep Learning Receiver*. IEEE Transactions on Wireless Communications，2021。pure method / neural receiver；B。[原始记录](https://doi.org/10.1109/TWC.2021.3054520)；[逐篇详解](../相关工作/论文详解/P34_DeepRx.md)；BibTeX `honkala2021deeprx`。
- **[P35]** Zhang, Yi and Doshi, Akash and Liston, Rob and Tan, Wai-tian and Zhu, Xiaoqing and Andrews, Jeffrey G. and Heath, Robert W.. *DeepWiPHY: Deep Learning-Based Receiver Design and Dataset for IEEE 802.11ax Systems*. IEEE Transactions on Wireless Communications，2021。method + dataset；B。[原始记录](https://doi.org/10.1109/TWC.2020.3034610)；[逐篇详解](../相关工作/论文详解/P35_DeepWiPHY.md)；BibTeX `zhang2021deepwiphy`。
- **[P36]** Soltani, Nasim and Loehning, Michael and Chowdhury, Kaushik. *VERITAS: Verifying the Performance of AI-native Transceiver Actions in Base-Stations*. arXiv / 公开稿，2025。method / post-deployment recovery；A。[原始记录](https://arxiv.org/abs/2501.09761)；[逐篇详解](../相关工作/论文详解/P36_VERITAS.md)；BibTeX `soltani2025veritas`。
- **[P37]** Su, Xin and Zhu, Meiyi and Simeone, Osvaldo and Fischione, Carlo. *Post-Hoc Conformal Prediction for Reliable Wireless Communications*. arXiv / 公开稿，2026。theory + wireless applications；A。[原始记录](https://arxiv.org/abs/2609.26625)；[逐篇详解](../相关工作/论文详解/P37_PostHocConformal.md)；BibTeX `su2026posthocconformal`。
- **[P38]** Kontes, Georgios and Michalopoulos, Diomidis S. and Ghimire, Birendra and Mutschler, Christopher. *Position Paper: Rethinking AI/ML for Air Interface in Wireless Networks*. ICML 2025 Workshop on Foundation Models for Telecommunications，2025。position paper / workshop；A。[原始记录](https://arxiv.org/abs/2506.11466)；[逐篇详解](../相关工作/论文详解/P38_RethinkingAirInterface.md)；BibTeX `kontes2025rethinkingairinterface`。
- **[P39]** Gao, Yuan and Wu, Xinyi and Jiang, Jun and Hu, Bintao and Du, Jianbo and Ye, Qiang (John) and Zhang, Shunqing and Yu, F. Richard and Xu, Shugong. *AI/ML for Mobile Networks: Release 19 Status and Future Challenges*. IEEE Network，2026。survey + empirical case study；A。[原始记录](https://doi.org/10.1109/MNET.2026.3730405)；[逐篇详解](../相关工作/论文详解/P39_Release19Deployment.md)；BibTeX `gao2026release19`。
- **[P40]** Ali, Ramy E. and Penna, Federico. *LightTune: Lightweight Forward-Only Online Fine-Tuning with Applications to Link Adaptation*. arXiv / 公开稿，2026。pure method / online adaptation；A。[原始记录](https://arxiv.org/abs/2604.12406)；[逐篇详解](../相关工作/论文详解/P40_LightTune.md)；BibTeX `ali2026lighttune`。

全部 43 项的作者、载体、DOI/公开版本及 BibTeX 见 [统一参考文献](../相关工作/参考文献.md)；受限论文不伪装成全文精读。新增书目按 DOI 与原始版本复核；P26 的年份/卷页、P27 的作者、P29 的 DOI、P39 的版本题名/作者和 P40 的版本结果尤其作了纠正。

## 17. 检索记录、未解决项与结论置信度

### 17.1 检索路径

检索日期 **2026-10-20**。路径：“原有题名核验 → 非 Agent 直接近邻 → 参考文献追踪 → 方法基础补充 → 原始材料复核”。未将本地未公开设计段落粘贴到搜索引擎。代表性公开检索词：

```text
"AI/ML Life Cycle Management for Interoperable"
"Demonstrating Interoperable Channel State Feedback Compression"
"Performance Monitoring-Enabled Reliable AI-Based CSI Feedback"
"Scenario-Aware Framework for DL-Based CSI Feedback"
"Deep Learning for CSI Feedback: One-Sided Model"
"Toward a Layer-2 Trigger"
"WirelessAgent++" / "WirelessOpsAgent" / "OnlineCritic-xApp"
"AgentRAN" / "Agentic Open RAN" "Deterministic"
"Human-in-the-Loop Agentic Reconfiguration" / "Dual-MCP"
"Open RAN Conflict Agents" / "PACIFISTA"
"AgentSpec" / "Quickest Change Detection with Controlled Sensing"
"Consensus on Transaction Commit"
"Invariant-Guided Logical Testing of Open RAN Controllers"
"TS 28.105" site:etsi.org
"38.843" site:3gpp.org
"AI Model Selection and Monitoring for Beam Management"
"Model Adaptation for Lifecycle Management" beam
"Statistical AI/ML Model Monitoring" interference
"DeepBeam" / "DeepSense 6G" / "Challenges of Predictive Beamforming"
"Spatial and Temporal Generalization of CSI-based Neural Positioning"
"Channel Charting" / "DeepRx" / "DeepWiPHY"
"VERITAS" "AI-native" / "LightTune" "Forward-Only"
"Post-Hoc Conformal Prediction for Reliable Wireless Communications"
```

按题名、DOI/arXiv ID 去重，预印本与正式版本合并。发现来源可含索引，技术结论尽量回到原文/出版社/作者机构。排除质量不符材料，不以二手转述支撑核心新颖性。原位更新综述，同时以统一 BibTeX 和编号索引连接逐篇详解；同一工作的不同版本不重复计数。

### 17.2 未解决的核验项

1. **P03/P04 全文**：可确认是直接竞争者，但不能只凭摘要证明算法不重合。低开销监测若作主创新，必须优先补读。
2. **P13/P14/P17**：P14 正式载体未独立确认；P13/P17 本轮未复核全部数值与实现。
3. **代码可运行性**：找到项目不等于安装/跑通/核验许可证；本轮未执行第三方论文代码，未产生复现性能。
4. **标准后续修订**：固定核验具体版本，未穷尽截止日前 RAN1/RAN2/RAN4/SA5 所有决定；标准化主张仍需条款/版本审计。
5. **跨用例泛化**：本次已补波束、定位、接收机与链路自适应文献，但未运行跨用例系统；共享接口不等于决策策略可零样本迁移，耦合、标签、安全语义仍须分别验证。
6. **专利/厂商内部实现**：不在范围内，报告不能用于排他性知识产权判断。

### 17.3 最终置信度

- **高**：双侧部署、工具、LCM、安全门、互操作和监测更新都有先例；原定位过宽。
- **中**：有成本且会失效的跨端证据与可恢复发布结合，是值得具体化和验证的切入点，方法基础并不空白。
- **尚无证据**：LLM 或双 Agent 必然优于非 LLM 安全 LCM；本文不作此结论。

**保留全局规划与本地事实分离的架构，把管理对象从 CSI 配对扩展为无线 AI 功能：优先以波束管理和双侧 CSI 构成差异化验证，用定位/接收机/链路自适应检验扩展边界；把证据选择、适配验收、配置绑定和故障恢复作为实质问题，把 Agent 的收益作为需要证明的结果。**
