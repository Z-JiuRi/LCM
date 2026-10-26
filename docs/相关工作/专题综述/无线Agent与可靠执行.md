# 无线 Agent 与可靠执行相关工作

> 整理日期：2026-10-25。原文整理；未新增文献核验或实验结果。原章节编号保留，便于核对旧稿。

[文档导航](../../README.md) · [原稿章节对照](../../整理说明.md)

---

> 来源：`LCMAgent相关论文综述与研究定位.md`；原 LCMAgent 草案/调研。

<a id="s5"></a>

## 5. 第二组直接近邻：无线 Agent、双端工具与安全执行

<a id="s5-1"></a>

### 5.1 P07/P08：WirelessAgent 与 WirelessAgent++

**WirelessAgent** 将无线任务接到感知、记忆、规划和工具调用；2025 公开稿已有 *China Communications* 2026 正式记录。[P07] 上一版一律归为预印本的分类应更新。

**WirelessAgent++** 研究自动工作流设计与 WirelessBench，使用 maturity-aware critic、三类经验回放和收敛检测，不只是固定 prompt。基准覆盖知识题、网络切片和移动业务保障；工作流搜索的改进不能直接等同于有丢包/崩溃的端网发布收益。[P08]

**项目应吸收与区分**：

- 复用工具接口、任务分解、工作流搜索与多骨干评估。
- 另外证明执行时证据仍有效、两侧兼容、失联后可恢复。
- 若本项目有确定性 guard，给基线同样的 guard，再比较规划；否则可能只是“有验证器优于无验证器”。

<a id="s5-2"></a>

### 5.2 P09：WirelessOpsAgent 与 WirelessOptBench

**机制**：关注 proposal-time 正确、execution-time 失效，使用证据/契约决定 `APPLY/HOLD/RETRY/ESCALATE`，支持修复后复核。[P09]

**实验辨析**：Table III 每个骨干/方法 600 episodes；Claude 上 Unsafe APPLY 从 82.2% 降到 10.3%，分母是全部 episodes，不是全部 APPLY。仍有剩余违规；§V-D 披露 conflict/provenance 切片的 frozen evaluator 混淆，不能把局部“零误放行”读成普遍安全。

**定位影响**：动作证据、新鲜度、局部修复和执行前复核已有直接近邻。受控 benchmark 不等于生产故障分布；论文将执行器安全和并发控制列于评估之外。端网并发、配对和真实链路可以成为范围差异，但不是贬低其贡献的理由。

<a id="s5-3"></a>

### 5.3 P10：AgentRAN

**已覆盖**：分层多 Agent、自然语言意图、跨时间尺度/空间/协议层组织，以及真实 5G testbed 演示；2025 公开稿，作者项目列有 *IEEE Communications Magazine* 2026 DOI。[P10]

**比较方式**：Agent 数量、分层编排和多目标控制不是空白。跨时间尺度架构也不意味着每次 LLM 请求都达到物理层时限。应比较具体模型发布任务，不能用“它管网络、我们管模型”一句话结束。

**未确认**：是否实现与本文完全相同的配对版本恢复语义；不能仅凭摘要写“没有”。

<a id="s5-4"></a>

### 5.4 P11：A1gent

**机制**：非实时 rApp 将意图编译为有类型 A1 策略，近实时 xApp 通过确定性循环执行，使用 guardrail 与固定优先级冲突合并。已有 ICC 2026 正式记录及公开稿。[P11]

**定位影响**：“LLM 只提议，执行器控制”已有强先例；冲突合并也不是拼接各 Agent 建议。有效差异是模型对生命周期、两端隐含状态与可恢复提交。

**证据边界**：可审计、确定性不自动等于所有调度/并发/故障下有形式安全证明。比较要分列可检查规则、故障覆盖和已证明性质。

<a id="s5-5"></a>

### 5.5 P12：Dual-MCP——上一版遗漏严重的双端架构近邻

**来源与类型**：Baena、Mandal、Koutsonikolas；*ACM MobiHoc 2025* 两页 demo，391–392。类型：system/tool。[P12]

**已覆盖**：gNB 和 UE 各暴露 MCP 工具，云端 LLM 编排跨端动作，执行前人工批准；论文还声明前后条件检查、可逆执行与日志。不能声称这些是 LCMAgent 首创。

**需要区分**：工具服务器不是两套自主 LLM；跨端重配置演示不自动等于完整 encoder/decoder 生命周期事务。文中对“formal”“rollback”的表述也不能代替完整协议、故障模型与证明。两页 demo 提供实现先例，不足以证明长期故障恢复和大规模收益。

**建议比较**：在 Dual-MCP 式端网编排上使用相同模型仓库/执行能力，再逐项增加配对契约、时效证据、提交恢复和主动补测，定位新增价值。

<a id="s5-6"></a>

### 5.6 P13：OnlineCritic-xApp

保留原文 INFOCOM 2026 正式论文，研究 LLM 辅助切片资源管理与在线学习 Critic。[P13] 原有本地阅读中“候选动作需外部评价/可行性控制”的启示仍有价值。

本轮未重新审计全部实验和实现，不补造收益，不把学习式 Critic 的经验效果等同于跨端发布硬安全。适合作为“LLM 候选 + 筛选器”近邻，不是双侧 LCM 的直接替代。

<a id="s5-7"></a>

### 5.7 P14/P15：ORCA 与 PACIFISTA

**ORCA** 用生成式 Agent 检测、缓解 xApp 冲突。[P14] 本轮找到作者公开记录，正式载体独立核验不足，不根据 `ORCA_INFOCOM26.pdf` 文件名判定主会出版。

**PACIFISTA** 不依赖 LLM，通过 sandbox profiling、图和统计方法发现、刻画 O-RAN 应用冲突；公开记录对应 *IEEE Transactions on Mobile Computing* 2025。[P15]

**启示**：共享 BS decoder、GPU/内存、监测资源和并发更新也会冲突。每个 UE 局部验证成功，全局仍可能超预算。必须有资源仲裁器，并比较“不用 LLM 但有 sandbox/冲突管理”的方案。

<a id="s5-8"></a>

### 5.8 P16/P17：Net Analyzer rApp 与 O-RAN Resilience

**Net Analyzer** 在真实 O-RAN testbed 的 ping-pong handover 场景中，串联事件解释、日志核查、工具访问和显式人工批准。[P16] 支持解释/动作分离，不证明全自动无审批同样安全。

**O-RAN Resilience** 为 INFOCOM Workshops 2025 正式 workshop 论文，研究 LLM Agent 与 O-RAN 韧性。[P17] 保留为网络侧背景，不把 workshop 案例升级为端网发布一般性结论。

<a id="s6"></a>

## 6. 第三组方法基础：决定贡献是否成立

<a id="s6-1"></a>

### 6.1 P18：AgentSpec——运行时约束不是新的 Agent 概念

AgentSpec 以结构化规则描述触发、谓词与处置，对 Agent 做运行时约束；2025 公开稿，已有 ICSE 2026 出版信息。[P18]

schema、权限、预算和拦截应尽量确定性化。规则完全可枚举时，必须问为何需要 LLM。规则引擎能检查已有事实，但证据从何获得、何时失效、是否代表当前本地资源，是另一层问题。

<a id="s6-2"></a>

### 6.2 P19：Quickest Change Detection with Controlled Sensing

Veeravalli、Fellouris、Moustakides 联合研究“何时宣布变化”与“下一步选什么观测动作”。WCC 在有限动作和变化后参数等假设下分析最坏检测时延、误报约束及渐近最优性；正式载体为 *IEEE Journal on Selected Areas in Information Theory* 2024。[P19]

主动补测不能只和固定采样比较。应比较序贯检测/受控观测，或解释其假设为何不适用：标签延迟、不同隐私代价、UE 可拒绝、观测期间状态变化等。不能把经典问题换名成“Agent 自主感知”。

<a id="s6-3"></a>

### 6.3 P20：Consensus on Transaction Commit

Gray 与 Lamport 说明协调者故障、提交决定和恢复是成熟分布式问题。[P20] `PREPARE/COMMIT/ACK` 三个消息名不构成新事务协议。

必须明确追求原子提交、可检测配对安全、有限不一致窗口还是最终恢复；声明崩溃、消息丢失、分区、持久日志、时钟和重试假设。没有这些，不能声称“共同激活保证一致性”。

<a id="s6-4"></a>

### 6.4 P21：InvaRAN——验证器本身也会出错

USENIX Security 2026 正式论文，以动态推断不变量和测试发现 O-RAN 控制器逻辑问题。官方摘要报告 9 个此前未知问题，含 7 个逻辑问题、2 个内存问题。[P21]

应测试 validator 的状态遗漏、单位/语义错配、并发和罕见恢复路径，而不仅测 LLM 能否输出合法 JSON。动态不变量提供测试线索，不自动等于完整形式证明。

<!-- 本页使用的引用定义；书目详情由对应资料索引维护。 -->
[P07]: ../论文详解/P07_WirelessAgent.md
[P08]: ../论文详解/P08_WirelessAgentPlusPlus.md
[P09]: ../论文详解/P09_WirelessOpsAgent.md
[P10]: ../论文详解/P10_AgentRAN.md
[P11]: ../论文详解/P11_AgenticOpenRAN.md
[P12]: ../论文详解/P12_DualMCP.md
[P13]: ../论文详解/P13_OnlineCritic.md
[P14]: ../论文详解/P14_OpenRANConflictAgents.md
[P15]: ../论文详解/P15_PACIFISTA.md
[P16]: ../论文详解/P16_NetAnalyzer.md
[P17]: ../论文详解/P17_ORANResilience.md
[P18]: ../论文详解/P18_AgentSpec.md
[P19]: ../论文详解/P19_ControlledSensing.md
[P20]: ../论文详解/P20_TransactionCommit.md
[P21]: ../论文详解/P21_InvaRAN.md
