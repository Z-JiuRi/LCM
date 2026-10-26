# 相关工作逐篇详解

> 更新：2026-10-20。共 **43 份解读：40 篇论文 + 2 份标准文件 + 1 份讨论材料**。每份包含问题、方法、证据与限制、LCMAgent 关系以及后续精读/复现检查项。不是 43 篇均已完成全文精读；受限来源在各篇首页明确标记。

## 建议阅读路径

1. **先看直接近邻**：P01/P26/P27/P36/P40，分别理解一般 LCM、波束选择监测/适配、接收机恢复和轻量在线更新。
2. **再看执行与数据**：P29–P35，对照波束、定位和接收机的输入、标签、配置依赖及真实数据条件。
3. **再看证据决策**：P03/P04/P19/P28/P37，区分性能监测、受控观测和统计校准。
4. **最后比较 Agent 与可靠执行**：P07–P18/P20/P21，避免把工具接口、安全门和事务术语误写为首创。
5. 标准先读 S01 的共性框架及波束/定位章节，再映射 S02；D01 只作讨论背景。

## 全部条目

- [S01 · Study on Artificial Intelligence (AI)/Machine Learning (ML) for NR air interface](S01_TR38843.md) — 标准研究报告；A。
- [S02 · Artificial Intelligence/Machine Learning (AI/ML) management](S02_TS28105.md) — 管理规范；A。
- [D01 · AI/ML for 6GR: Moderator's Summary, revision 4](D01_R12508811.md) — 会议讨论材料；C。
- [P01 · AI/ML Life-Cycle Management for Interoperable AI-Native RAN](P01_InteroperableLCM.md) — survey / framework；A。
- [P02 · Demonstrating Interoperable Channel State Feedback Compression With Machine Learning](P02_InteroperableCSI.md) — method + system；A。
- [P03 · Performance Monitoring-Enabled Reliable AI-Based CSI Feedback](P03_CSIPerformanceMonitoring.md) — pure method；B。
- [P04 · Scenario-Aware Framework for DL-Based CSI Feedback With Unified Training, Monitoring, and Updating](P04_ScenarioAwareCSI.md) — pure method；B。
- [P05 · Toward a Layer-2 Trigger for AI/ML Lifecycle Management in 6G](P05_L2Trigger.md) — method / control case study；A。
- [P06 · Deep Learning for CSI Feedback: One-Sided Model and Joint Multi-Module Learning Perspectives](P06_OneSidedCSI.md) — survey / perspectives；B。
- [P07 · WirelessAgent: Large language model agents for intelligent wireless networks](P07_WirelessAgent.md) — system / agent framework；B。
- [P08 · WirelessAgent++: Automated Agentic Workflow Design and Benchmarking for Wireless Networks](P08_WirelessAgentPlusPlus.md) — method + benchmark；A。
- [P09 · WirelessOpsAgent: A Benchmark and Agent Design for Action Assurance in Wireless Networks](P09_WirelessOpsAgent.md) — method + benchmark；A。
- [P10 · AgentRAN: An Agentic AI Architecture for Autonomous Control of Open 6G Networks](P10_AgentRAN.md) — system / architecture；B。
- [P11 · Agentic Open RAN: A Deterministic and Auditable Framework for Intent-Driven Radio Control](P11_AgenticOpenRAN.md) — system / framework；A。
- [P12 · Demo: Human-in-the-Loop Agentic Reconfiguration of Edge 5G Networks via Dual-MCP and LLM Reasoning](P12_DualMCP.md) — demo / system；A。
- [P13 · OnlineCritic-xApp: Online Learning for LLM-Assisted RAN Slice Resource Management](P13_OnlineCritic.md) — pure method / xApp；C。
- [P14 · Open RAN Conflict Agents: Detecting and Mitigating xApp Conflicts with Generative Agents](P14_OpenRANConflictAgents.md) — system / generative agents；C。
- [P15 · PACIFISTA: Conflict Evaluation and Management in Open RAN](P15_PACIFISTA.md) — system / conflict management；B。
- [P16 · LLM-Based Net Analyzer rApp for Explainable and Safe Automation in O-RAN Non-RT RIC](P16_NetAnalyzer.md) — system / rApp；A。
- [P17 · LLM-Driven Agentic AI Approach to Enhanced O-RAN Resilience in Next-Generation Networks](P17_ORANResilience.md) — agent framework / workshop；C。
- [P18 · AgentSpec: Customizable Runtime Enforcement for Safe and Reliable LLM Agents](P18_AgentSpec.md) — system / runtime enforcement；B。
- [P19 · Quickest Change Detection with Controlled Sensing](P19_ControlledSensing.md) — theory / proof；B。
- [P20 · Consensus on transaction commit](P20_TransactionCommit.md) — theory / protocol；B。
- [P21 · Invariant-Guided Logical Testing of Open RAN Controllers](P21_InvaRAN.md) — system / testing；B。
- [P22 · Deep Learning for Massive MIMO CSI Feedback](P22_CsiNet.md) — pure method；B。
- [P23 · Exploring the Potential of Large Language Models for Massive MIMO CSI Feedback](P23_LLMCSI.md) — pure method；B。
- [P24 · Agentic AI for ISAC: Analysis, Framework, and Case Study](P24_AgenticISAC.md) — survey / framework / case study；B。
- [P25 · Adaptive Root Cause Analysis for Self-Healing in 5G Networks](P25_AdaptiveRCA.md) — pure method / self-healing；C。
- [P26 · AI Model Selection and Monitoring for Beam Management in 5G-Advanced](P26_BeamModelSelection.md) — method / beam management；A。
- [P27 · Model Adaptation for Lifecycle Management in AI-native 5G/6G Networks](P27_BeamLifecycleAdaptation.md) — pure method / LCM procedure；A。
- [P28 · Statistical AI/ML Model Monitoring for 5G/6G: Interference Prediction Case Study](P28_StatisticalMonitoring.md) — pure method / monitoring；A。
- [P29 · DeepBeam: Deep Waveform Learning for Coordination-Free Beam Management in mmWave Networks](P29_DeepBeam.md) — method + experimental dataset；B。
- [P30 · DeepSense 6G: A Large-Scale Real-World Multi-Modal Sensing and Communication Dataset](P30_DeepSense6G.md) — pure benchmark / dataset；B。
- [P31 · Challenges of Predictive Beamforming Using Geographical Positioning: Insights from the DeepSense Dataset](P31_PredictiveBeamformingDrift.md) — empirical analysis / benchmark study；A。
- [P32 · Channel Charting: Locating Users Within the Radio Environment Using Channel State Information](P32_ChannelCharting.md) — pure method；B。
- [P33 · Spatial and Temporal Generalization of CSI-based Neural Positioning](P33_NeuralPositioningGeneralization.md) — method + real-world evaluation；A。
- [P34 · DeepRx: Fully Convolutional Deep Learning Receiver](P34_DeepRx.md) — pure method / neural receiver；B。
- [P35 · DeepWiPHY: Deep Learning-Based Receiver Design and Dataset for IEEE 802.11ax Systems](P35_DeepWiPHY.md) — method + dataset；B。
- [P36 · VERITAS: Verifying the Performance of AI-native Transceiver Actions in Base-Stations](P36_VERITAS.md) — method / post-deployment recovery；A。
- [P37 · Post-Hoc Conformal Prediction for Reliable Wireless Communications](P37_PostHocConformal.md) — theory + wireless applications；A。
- [P38 · Position Paper: Rethinking AI/ML for Air Interface in Wireless Networks](P38_RethinkingAirInterface.md) — position paper / workshop；A。
- [P39 · AI/ML for Mobile Networks: Release 19 Status and Future Challenges](P39_Release19Deployment.md) — survey + empirical case study；A。
- [P40 · LightTune: Lightweight Forward-Only Online Fine-Tuning with Applications to Link Adaptation](P40_LightTune.md) — pure method / online adaptation；A。

## 使用边界

解读中的“可研究”“建议测试”是本项目的推导，不是原论文的实验结论；不能据此宣称新颖性已经成立。未取得全文的直接竞争者，优先补读而不是直接认定不重合。

[统一 BibTeX](../参考文献.md) · [LCMAgent 综述](../../分析文档/LCMAgent/README.md)
