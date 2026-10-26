# [P17] LLM-Driven Agentic AI Approach to Enhanced O-RAN Resilience in Next-Generation Networks

> 核验/解读日期：2026-10-20。对应综述编号 `P17`，BibTeX key：`wu2025oranresilience`。

## 1. 文献信息与阅读边界

- 作者/机构：Wu, Xingqi and Wang, Yuhui and Farooq, Junaid and Chen, Juntao。
- 载体与年份：IEEE INFOCOM 2025 - IEEE Conference on Computer Communications Workshops (INFOCOM WKSHPS)；2025。
- 类型：agent framework / workshop。
- 阅读深度：C：正式书目及原有材料；未重新完整审计实验。
- 原始来源：[正式 DOI](https://doi.org/10.1109/INFOCOMWKSHPS65812.2025.11152722)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

该工作研究 LLM-driven Agentic AI 对 O-RAN 韧性的支持，属于网络侧故障应对与智能控制背景。其正式载体是 INFOCOM Workshops 2025，而不是 INFOCOM 主会；两者必须准确区分。

## 3. 方法与工作流程

从题名与已核验记录能确认的中心是 Agentic 推理与 O-RAN resilience 的结合。本轮没有足够重读证据逐项说明其故障预测器、恢复动作和工具协议，故不补造细节。后续精读应追踪“检测—诊断—建议—执行—验证”每一步的实证支撑。

## 4. 实验证据、结果与局限

正式 DOI 与会议记录可信，但不自动意味着所有韧性能力均在真实硬件上验证。不能用网络恢复案例替代跨端模型一致性，也不能把工作坊案例推广成任意网络异常下的可恢复性保证。当前不列未经重新核对的性能数字。

## 5. 对 LCMAgent 的具体影响

它帮助 LCMAgent 定义恢复视角：不仅看更新成功，还看业务在失败时能否恢复。相比一般韧性 Agent，本项目应明确被管理的模型功能、回退依赖和证据时效。若仅做告警解释和工具调用，差异会很弱。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 补齐故障类型、恢复动作和真实/仿真环境的原文证据。
- 将恢复延迟从故障发生时刻和可检测时刻分别计量。
- 测试 fallback 不可用，而不是默认任何失败都可瞬时回退。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `wu2025oranresilience`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
