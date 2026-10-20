# LCMAgent 架构设计草案

> **文档状态：预期架构与研究设计草案，尚未完成实现或验证。** 本文记录当前研究假设和候选方案，不是现有系统说明、已冻结的项目规范，也不是外部标准。文中的角色、接口、数据结构、协议、阈值、基线与时间尺度均可根据原型和实验结果调整。
>
> **仓库现状（2026-10-20）：** 当前仓库主要包含研究文档、标准资料和第三方公开代码材料；未发现 LCMAgent 自有运行时、协议执行器或实验实现。因此下文的架构和安全性质均不可视为已实现能力。
>
> 判断实现状态时，以代码、测试和实验记录为准。发现实现与草案不一致时，应先记录差异并评估设计，不应仅为符合草案而直接改动实现。
>
> 更新日期：2026-10-20

## 1. 核心定位

### 1.1 研究问题

**在端网信息分散、证据获取有代价、设备状态变化及消息可能丢失的条件下，如何决定下一步采集什么证据，何时选择、重新校准、适配、激活或禁用哪个无线 AI 功能，以及何时等待、拒绝或回退，使错误发布和业务损失受控，同时减少监测、通信和 UE 计算成本？**

### 1.2 系统定位

**预算约束与状态不确定条件下，无线 AI 功能的证据驱动生命周期决策与可靠执行。**

- **不是**：首次提出双侧模型生命周期、端网配对、监测更新、工具编排或安全门
- **而是**：在已有监测、适配与安全执行基础上，研究有成本且会失效的证据选择与可恢复发布机制

### 1.3 三层证明责任

1. **系统正确性**：输入输出与无线配置兼容；双侧 CSI 配对一致；过期证据不复用；失败有明确恢复路径
2. **决策有效性**：相同执行基础设施下，比固定阈值、序贯检测、主动测量和非 LLM 规划器更有效地使用有限证据
3. **Agent 必要性**：面对异构工具和组合任务时，LLM 优势超过推理成本与额外故障面

## 2. 架构分层

### 2.1 候选三平面设计

```text
┌─────────────────────────────────────────────────────────┐
│  管理/推理平面 (Management & Reasoning Plane)              │
│  • 模型仓库、训练验证、慢速 LCM 规划、审计                     │
│  • LLM Agent 规划器、工作流搜索                             │
│  • 时间尺度：秒到分钟                                       │
└────────────────────┬────────────────────────────────────┘
                     │ 提交有边界的候选计划
                     ↓
┌─────────────────────────────────────────────────────────┐
│  端网协调平面 (End-to-End Coordination Plane)             │
│  • 功能/配置绑定、证据交换、资源确认、激活与恢复状态             │
│  • 确定性执行器、配对一致性检查、事务协议                      │
│  • 时间尺度：数十毫秒到秒                                    │
└────────────────────┬────────────────────────────────────┘
                     │ 由确定性执行器放行动作
                     ↓
┌─────────────────────────────────────────────────────────┐
│  无线执行平面 (Wireless Execution Plane)                  │
│  • 波束预测/切换、CSI 编解码、定位/接收处理                    │
│  • 预置本地 fallback                                       │
│  • 时间尺度：毫秒级                                          │
└─────────────────────────────────────────────────────────┘
```

**关键约束**：
- LLM **不**逐时隙决定波束或逐符号解调
- LLM 配置慢速策略和证据预算，快速闭环由本地算法执行
- 已部署模型的禁用、局部切换和失效保护可能需要更快响应

### 2.2 时间尺度分离

| 平面 | 典型操作 | 时间尺度 | LLM 参与 |
|-----|---------|---------|---------|
| 管理/推理 | 模型训练、验证、选择策略规划 | 秒 - 分钟 | ✓ |
| 端网协调 | 证据交换、资源确认、配对提交、故障恢复 | 10ms - 秒 | 部分（规划阶段） |
| 无线执行 | 波束切换、CSI 编解码、符号检测 | < 10ms | ✗ |

## 3. 候选角色定义

### 3.1 网络侧 Agent (gNB Agent)

**部署位置**：基站或网络侧服务器

**核心职责**：
1. 维护全局模型仓库和兼容性知识库
2. 协调多 UE 的资源分配与冲突解决
3. 网络侧监测数据收集与分析
4. 发起端网协商与配对激活流程
5. 管理共享解码器（如 CSI decoder）资源

**工具接口**：
```yaml
Tools:
  - model_repository_query      # 查询模型库、兼容性
  - resource_monitor            # BS 资源（GPU、内存）监测
  - performance_kpi_query       # 吞吐量、BLER 等 KPI
  - ue_capability_request       # 请求 UE 能力和状态
  - pairing_proposal           # 提议配对方案
  - activation_command         # 发送激活指令
  - rollback_trigger           # 触发回退
```

**状态管理**：
- 当前活跃配对映射 `{UE_ID → (encoder_digest, decoder_digest, config_epoch)}`
- 资源预留记录
- 历史性能轨迹

### 3.2 UE 侧运行时 (UE Runtime)

**部署位置**：用户设备

**核心职责**：
1. 本地资源（内存、电量、温度）监测与保护
2. 候选模型本地验证（shadow test、proxy decoder）
3. 配对一致性检查与数据面 epoch 验证
4. 本地 fallback 执行
5. 证据生成与上报（受隐私和成本约束）

**工具接口**：
```yaml
Tools:
  - local_resource_check        # 内存、CPU、温度、电量
  - model_local_test           # shadow 推理测试
  - proxy_decoder_eval         # 轻量质量估计
  - input_distribution_summary # 输入统计摘要（不传原始数据）
  - compatibility_verify       # 检查配对标识、schema、epoch
  - fallback_execute           # 切换到 fallback 模型或传统方法
```

**重要设计决策**：
- **UE Runtime 不是第二个 LLM Agent**：它是确定性工具执行层
- 没有自主规划时，不为"双 Agent"强行包装
- 轻量级、低延迟、确定性响应优先

### 3.3 监督与审计层 (可选)

**部署位置**：运维中心或独立审计服务

**核心职责**：
1. 跨 UE、跨小区的性能监测与异常检测
2. 人工审批高风险操作（生产环境、大规模更新）
3. 日志聚合与根因分析
4. 合规性检查

**启示来源**：Net Analyzer rApp (P16)、Dual-MCP 人工审批 (P12)

## 4. 候选管理对象模型

### 4.1 功能契约 (Function Manifest)

适用于**单侧功能**（波束预测、定位、接收机等）：

```yaml
FunctionManifest:
  use_case: "beam_prediction" | "positioning" | "neural_receiver" | ...
  model_digest: <hash>
  inference_placement: "UE" | "gNB" | "distributed"

  # 输入输出约束
  input_output_schema:
    input_shape: [...]
    output_type: "beam_index" | "coordinates" | "soft_bits" | ...
    quantization: {...}

  # 无线配置依赖
  radio_config_dependencies:
    beam_codebook_id: <id>         # 波束：码本版本
    measurement_set: ["A", "B"]     # 波束：Set A/B 定义
    anchor_points: [...]            # 定位：锚点坐标
    coordinate_system: <ref>        # 定位：坐标系
    pilot_config: {...}             # 接收机：导频配置
    antenna_calibration: <version>  # 天线/射频校准

  # 场景与有效性
  scenario_scope:
    indoor_outdoor: "indoor" | "outdoor" | "both"
    speed_range: [0, 30]  # km/h
    frequency_band: "sub6" | "mmWave"

  validation_provenance:
    training_data: <source>
    validation_metrics: {...}
    last_calibration: <timestamp>

  # 资源与监测
  resource_requirements:
    memory_mb: 100
    inference_ms: 5
    energy_mj: 10

  monitor_policy:
    kpi: "top_k_accuracy" | "positioning_error" | "bler"
    threshold: {...}
    check_interval: 100  # 推理次数

  fallback:
    method: "traditional_scan" | "last_known_good" | "disabled"
    fallback_model_digest: <hash>
```

### 4.2 配对契约 (Pair Manifest)

适用于**双侧联合推理**（CSI encoder-decoder 等）：

```yaml
PairManifest:
  # 模型标识
  encoder_digest: <hash>
  decoder_digest: <hash>
  compatibility_family: <id>  # 兼容性组

  # 中间表示约束
  latent_layout:
    dimensions: [...]
    quantization: {...}
    semantic_version: <v>  # 避免同维度不同语义

  feedback_config:
    codebook_type: "Type I" | "Type II" | ...
    overhead_bits: 256

  # 预处理依赖
  preprocessing:
    normalization: "per_antenna" | "global"
    feature_extraction: <config>

  # 其他字段复用 FunctionManifest 结构
  supported_scenarios: {...}
  resource_requirements: {...}
  fallback_pair:
    encoder_digest: <hash>
    decoder_digest: <hash>

  validation_provenance: {...}
```

**关键原则**：
- 相同 `model_id` 不够：需检查 latent 语义、量化、预处理、反馈配置
- 配对只是功能管理的**特例**，不是项目定义

### 4.3 证据 (Evidence)

```yaml
Evidence:
  # 绑定
  subject: "UE_12345" | "gNB_Cell_7"
  function_digest: <hash>          # 或 pair_digest
  config_epoch: <version>          # 配置版本号

  # 时效
  observation_window: [start, end]
  generated_at: <timestamp>
  expires_at: <timestamp>

  # 来源与方法
  source: "ue_local" | "bs_kpi" | "shadow_test" | "reference_measurement"
  measurement_method: "proxy_decoder" | "top_k_scan" | "bler_observation"
  sample_count: 1000

  # 质量与成本
  uncertainty: {...}               # 统计不确定度
  resource_reservation:            # 保留资源量（并发控制）
    memory_mb: 50
    measurement_slots: 10

  # 权限
  permitted_use: "this_transaction_only" | "shared_ue_group" | ...
```

**关键问题**：
- 谁产生、验证与撤销证据？
- shadow test 和实际激活使用相同配置？
- 测量后温度、内存、业务负载是否已变化？
- 能否跨 UE、小区、session 复用证据？

## 5. 候选决策与执行流程

### 5.1 端网协商流程（双侧配对特例）

```text
[gNB Agent]                        [UE Runtime]

    │
    ├─ 1. 检测退化/触发条件
    │    (KPI 下降、环境变化、周期检查)
    │
    ├─ 2. 查询候选配对
    │    model_repository_query()
    │    → 候选: [(enc1, dec1), (enc2, dec2), ...]
    │
    ├─ 3. 请求 UE 能力与状态 ────────────►
    │                                      ├─ local_resource_check()
    │                                      ├─ 返回: 内存、电量、当前模型
    │    ◄────────────────────────────────┤
    │
    ├─ 4. 提议配对方案 ──────────────────►
    │    PREPARE(pair_manifest, enc_url)  │
    │                                      ├─ 5. 本地验证
    │                                      ├─   • 下载 encoder (如需)
    │                                      ├─   • compatibility_verify()
    │                                      ├─   • shadow_test()
    │                                      ├─   • proxy_decoder_eval()
    │                                      │
    │    ◄────────────────────────────────┼─ 6. READY(evidence) 或 REJECT
    │
    ├─ 7. 决策：COMMIT / HOLD / RETRY / ESCALATE
    │    (基于 evidence 新鲜度、资源、风险)
    │
    ├─ 8. (若 COMMIT) 预留资源
    │    resource_reservation.lock()
    │
    ├─ 9. COMMIT(transaction_id, epoch) ─►
    │                                      ├─ 10. 最终检查
    │                                      ├─   • resource_check() 再次确认
    │                                      ├─   • 持久化 epoch 到本地状态
    │                                      │
    │    ◄────────────────────────────────┼─ 11. ACK 或 ABORT
    │
    ├─ 12. (收到 ACK) 更新 gNB decoder
    │     持久化配对状态
    │
    └─ 13. 数据面：检查 epoch 一致性
         UE: if (received_epoch != local_epoch) → reject/fallback
```

**故障恢复点**：
- PREPARE 超时 → 重试或选择其他候选
- READY 未到达 → HOLD，等待或降级
- ACK 丢失 → UE 凭持久状态识别已完成；gNB 幂等重传
- 崩溃恢复 → 读取持久日志，确认 epoch 或回退

### 5.2 单侧功能更新流程（波束管理示例）

```text
[gNB Agent]                        [UE Runtime]

    │
    ├─ 1. UE 定期上报性能摘要（可选）
    │    • top-k 准确率下降
    │    • 输入分布统计
    │
    ├─ 2. gNB 监测网络侧信号
    │    • 波束失败率
    │    • 切换频率
    │
    ├─ 3. 决策：需要补测、校准还是换模型？
    │    (LLM 规划 或 规则/统计方法)
    │
    ├─ 4a. 若补测：扩展 top-K 或 full scan ─►
    │                                      ├─ 执行测量
    │    ◄────────────────────────────────┼─ 返回测量结果
    │
    ├─ 4b. 若校准：请求传感器/锚点校准 ───►
    │                                      ├─ 重新校准定位或天线
    │    ◄────────────────────────────────┼─ 确认
    │
    ├─ 4c. 若换模型：下发新模型 ──────────►
    │    包含 manifest + 模型文件           │
    │                                      ├─ 本地验证 → shadow test
    │    ◄────────────────────────────────┼─ READY 或 REJECT
    │
    ├─ 5. COMMIT / HOLD
    │
    └─ 6. 本地 fallback 能力
         UE 自主检测失效 → 切换到传统方法或旧模型
```

### 5.3 证据驱动决策流程

```text
输入：当前状态、候选动作集合、可用证据

[LLM Agent 或 决策器]
    │
    ├─ 1. 评估当前证据充分性
    │    • 证据是否过期？
    │    • 证据是否绑定正确的 config_epoch？
    │    • 不确定度是否可接受？
    │
    ├─ 2. 若证据不足，规划补测动作
    │    Decision: 补测什么？成本 vs 信息价值
    │    • 小规模 top-K 复核
    │    • 稀疏参考测量/标签
    │    • 请求 UE shadow test
    │
    ├─ 3. 执行补测（通过工具调用）
    │
    ├─ 4. 收集新证据后，重新评估
    │
    ├─ 5. 决策生命周期动作
    │    • 继续使用当前模型
    │    • 切换到候选模型 X
    │    • 触发有限微调（链路自适应场景）
    │    • 校准传感器/锚点（定位场景）
    │    • 等待更多证据
    │    • 拒绝并回退
    │
    ├─ 6. 提交执行（通过协调平面）
    │
    └─ 7. 监测执行结果，更新状态
```

**与基线比较**：
- 规则 LCM：固定阈值 + hysteresis
- 统计 LCM：变化检测 + 序贯检测
- 确定性工作流：DAG/状态机
- LCMAgent：考虑证据成本、时效、组合约束的动态规划

## 6. 待实现与验证的安全性目标

### 6.1 六大安全性质（双侧配对特例）

| 性质 | 可执行解释 | 前提 |
|-----|-----------|-----|
| **Pair safety** | 数据的 epoch/配对标识属于接收端接受的兼容集合，否则拒绝/走非 AI 路径 | 数据路径可识别配置 |
| **No stale authorization** | 旧资源确认、旧 session 或过期测量不能授权新事务 | epoch/nonce、有效期与撤销语义明确 |
| **Idempotence** | 重复消息不导致重复激活、下载或扣预算 | 稳定事务 ID 和去重状态 |
| **Crash recovery** | 重启后从持久状态确认已完成/未完成 | 不以 LLM 对话记忆替代日志 |
| **Resource safety** | 并发事务不超卖 UE 内存或共享 decoder 资源 | 验证与预留有确定性协调 |
| **Recoverability** | 在声明假设下恢复兼容配对或非 AI 模式 | 旧模型保留、fallback 可用、重连策略明确 |

### 6.2 确定性执行器 (Deterministic Executor)

**职责**：
- 拦截 LLM 提议的动作
- 执行硬约束检查（资源、兼容性、权限）
- 确保 TOCTOU 安全（Time-of-Check-Time-of-Use）
- 记录审计日志

**检查项**：
```python
class DeterministicExecutor:
    def validate_action(self, action, evidence):
        # 1. Schema 检查
        if not schema_valid(action.manifest):
            return REJECT("Invalid manifest")

        # 2. 兼容性检查
        if action.type == "pair_activation":
            if not compatible(encoder, decoder, latent_version):
                return REJECT("Incompatible pair")

        # 3. 资源检查
        if not resource_available(action.requirements):
            return HOLD("Insufficient resources")

        # 4. 证据时效检查
        if evidence.expires_at < now():
            return REJECT("Stale evidence")

        # 5. 配置绑定检查
        if evidence.config_epoch != current_epoch:
            return REJECT("Config mismatch")

        # 6. 权限检查
        if not authorized(action, context):
            return REJECT("Unauthorized")

        return COMMIT
```

### 6.3 故障注入测试矩阵

| 故障域 | 测试场景 | 预期行为 |
|-------|---------|---------|
| **模型/格式** | 错配、量化不一致、损坏 | 阻断与正确诊断 |
| **配置** | 码本索引重排、测量集改变 | 补测/撤销证据 |
| **依赖** | 锚点/坐标系变更、校准偏差 | 避免误更新 |
| **资源** | 准备后内存减少、并发预留 | 重验/撤销、拒绝超预算 |
| **时效** | KPI 延迟/乱序、旧 session 重放 | 拒绝过期授权 |
| **消息** | PREPARE/COMMIT/ACK 丢失/重复 | 幂等、阻塞与恢复 |
| **崩溃** | UE/协调者在不同提交点重启 | 持久状态恢复 |
| **数据面** | 旧 epoch 数据在新模型后到达 | 误解码检测、过渡能力 |

## 7. 实验与评估

### 7.1 基线比较

| 编号 | 基线 | 能力配置 |
|-----|------|---------|
| **B0** | Rule-LCM | 双端检查、阈值监测、hysteresis、fallback |
| **B1** | Statistical-LCM | 同执行层；变化检测、序贯测试、预算化监测 |
| **B2** | Deterministic-Workflow | 同工具；DAG/状态机、条件分支、重试恢复 |
| **B3** | Non-LLM Active Evidence | 同动作集；信息价值/成本驱动补测 |
| **B4** | Single-Planner + UE Validator | 网络 LLM；UE 确定性验证；公共执行层 |
| **B5** | WirelessAgent++/Dual-MCP 适配 | 同接口与执行层 |
| **B6** | Evidence-Assured Agent | P09 式证据检查/修复，适配 LCM |
| **B7** | LCMAgent | 公共执行层上的证据选择 |
| **B8** | Oracle / Offline Bound | 完整状态/离线最优 |

### 7.2 评估指标

| 指标 | 定义 | 目的 |
|-----|------|-----|
| **Unsafe release / episodes** | 违规发布事件 / 全决策事件 | 安全率 |
| **Unsafe release / releases** | 违规发布 / 实际发布 | 精确安全率 |
| **Safe progress** | 真可发布机会中按时安全完成比例 | 避免过度保守 |
| **Missed beneficial update** | 有收益却未在有效窗口发布比例 | 捕捉过度保守 |
| **Configuration mismatch exposure** | 功能/配置错配时长、受影响数据/推理量 | 实际影响 |
| **Recovery latency** | 故障至业务恢复时间 | 恢复效率 |
| **Evidence cost** | 无线资源、UE 推理/能耗、测量次数 | 成本控制 |
| **End-to-end utility** | 吞吐量/BLER/SLA deficit 与过渡损失 | 业务价值 |
| **Churn** | 切换、反复回退、重复补测 | 振荡检测 |
| **Planner overhead** | token、API 成本、时延分位数 | Agent 开销 |

### 7.3 用例矩阵

| 用例 | 执行位置 | 关键绑定对象 | 高价值证据 | 直接基线 | 首轮可行性 |
|-----|---------|------------|----------|---------|-----------|
| **波束预测** | UE 或网络侧 | Set A/B、码本、天线校准 | top-K 实测、扩展扫描 | P26/P27；传统扫描 | ✓ 主用例 |
| **双侧 CSI** | UE encoder / gNB decoder | latent、量化、配对 | proxy/shadow 重构 | P02–P06 | ✓ 对照用例 |
| **定位** | UE/网络/多点融合 | 坐标系、锚点、时钟 | 真值锚点、额外测量 | P32/P33/P37 | 扩展 |
| **神经接收机** | 接收端本地 | 波形、导频、MCS | 参考接收机、CRC | P34–P36 | 扩展 |
| **链路自适应** | UE/网络预测 | 反馈时延、MCS 集合 | 延迟标签、在线更新 | P40；OLLA | 扩展 |

## 8. 建议实施路线（尚未执行）

### 8.1 阶段 1：执行闭环（不使用 LLM）

**目标**：验证系统正确性

- [ ] 实现单侧功能（波束管理）的 manifest、epoch、验证、故障注入
- [ ] 实现双侧配对（CSI）的 PREPARE/READY/COMMIT/ACK 协议
- [ ] 提供传统扫描/非 AI fallback
- [ ] 区分兼容/不兼容、过期/有效、资源足/不足
- [ ] 真实恢复 vs "日志完成"

**数据**：时间有序真实轨迹（离线回放）

### 8.2 阶段 2：证据策略比较（冻结执行层）

**目标**：验证决策有效性

- [ ] 加入规则、变化检测、固定工作流、非 LLM 主动补测
- [ ] 出现非平凡权衡：不测有风险，全测太贵，错测延误恢复
- [ ] 比较相同证据预算下的风险—成本曲线

**评估**：Pareto 前沿、故障强度分层

### 8.3 阶段 3：LLM Agent（有理由才引入）

**目标**：验证 Agent 必要性

- [ ] 给相同工具/预算，考察新组合、异构能力、跨步骤约束
- [ ] 分离公共 validator 与规划收益
- [ ] 观察：验证器 vs 规划器的收益分解

**决策准则**：
- 若验证器获得绝大部分收益 → 安全发布/恢复系统，LLM 可选
- 若非 LLM 主动测量相当且更便宜 → 证据选择/统计 LCM
- 若同执行层上，新组合风险—成本显著改善 → 支持受限 Agent 决策贡献

## 9. 与现有工作的关系

### 9.1 已有先例（不再声称首次）

| 能力 | 先例 | 本项目定位 |
|-----|------|-----------|
| 双侧模型生命周期 | TR 38.843, P01 | 在此基础上研究证据与恢复 |
| 双端工具编排 | Dual-MCP (P12) | 扩展到模型 LCM 与故障恢复 |
| LLM 提议 + 确定性执行 | A1gent (P11), AgentSpec (P18) | 增加跨端证据/并发/故障语义 |
| 监测后切换/更新 | P03, P04, P26, P27, P36, P40 | 增加有成本证据选择 |
| 跨厂商互操作 | P02 | 作为输入条件 |
| 端网配对一致性 | P05 | 扩展为可执行协议与故障恢复 |

### 9.2 核心差异

1. **证据经济学**：证据获取有代价、会失效、可能冲突，需要主动选择
2. **配置绑定**：功能/无线配置语义化，不只是模型权重版本检查
3. **故障语义**：明确崩溃、消息丢失、TOCTOU、并发超卖的恢复
4. **用例通用性**：共享管理骨架，但不共享所有安全语义（波束 vs CSI vs 定位 vs 接收机）

## 10. 技术约束与假设

### 10.1 明确不做

- ❌ 跨厂商模型训练协议（假设兼容模型对已存在）
- ❌ 联邦学习/分割训练（假设模型已离线训练完成）
- ❌ 对抗性攻击防御（非恶意故障优先）
- ❌ 形式化隐私保证（工程隐私保护，不声称差分隐私）
- ❌ 毫秒级数据面 Agent（LLM 不直接控制物理层）

### 10.2 假设与限制

**假设**：
- 模型仓库已建立，候选模型已预训练和验证
- 通信信道可能丢包/延迟，但非拜占庭故障
- UE 和 gNB 有本地持久化存储
- 存在可用的 fallback 方案（传统方法或已验证旧模型）

**限制**：
- 首版不处理恶意 UE 或被攻陷 gNB
- 首版不处理网络分区超过恢复超时时间
- 首版不处理硬件故障导致的模型损坏

## 11. 参考文献

完整 40+ 篇论文、2 份标准文件及 BibTeX 见：
- [参考文献.md](../../相关工作/参考文献.md)
- [论文详解/](../../相关工作/论文详解/)
- [LCMAgent相关论文综述与研究定位.md](../分析/LCMAgent相关论文综述与研究定位.md)

## 12. 配套设计文档

- [代码框架与文件结构](代码框架与文件结构.md)：实现边界、模块职责、建议目录和阶段化依赖。
- [实验方案](实验方案.md)：研究假设、环境、基线、场景、指标和统计分析。
- [材料映射与决策门](材料映射与决策门.md)：本地文献/代码证据到设计选择的追踪，以及需要实验解决的决策。

**关键标准**：
- [S01] 3GPP TR 38.843 V19.0.0 (Release 19, 2025-09)
- [S02] 3GPP TS 28.105 V18.4.0 (2024-07)

**关键论文**：
- [P01] Huang et al., AI/ML Life-Cycle Management for Interoperable AI-Native RAN
- [P02] Korpi et al., Demonstrating Interoperable Channel State Feedback Compression
- [P05] Kumar, Toward a Layer-2 Trigger for AI/ML Lifecycle Management in 6G
- [P09] Lu et al., WirelessOpsAgent: A Benchmark and Agent Design
- [P11] Li et al., Agentic Open RAN: A Deterministic and Auditable Framework
- [P12] Baena et al., Demo: Dual-MCP and LLM Reasoning
- [P26] Sun et al., AI Model Selection and Monitoring for Beam Management
- [P27] Go et al., Model Adaptation for Lifecycle Management
- [P36] Soltani et al., VERITAS: Verifying AI-native Transceiver Actions
- [P40] Ali & Penna, LightTune: Lightweight Forward-Only Online Fine-Tuning

---

> **版本**：v1.0
> **作者**：LCM 研究组
> **最后更新**：2026-10-20
