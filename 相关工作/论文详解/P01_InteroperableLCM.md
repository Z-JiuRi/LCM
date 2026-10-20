# [P01] AI/ML Life-Cycle Management for Interoperable AI-Native RAN

> 核验/解读日期：2026-10-20。对应综述编号 `P01`，BibTeX key：`huang2026interoperablelcm`。

## 1. 文献信息与阅读边界

- 作者/机构：Huang, Chu-Hsiang and Chiang, Yuan-Chih Fan and Wen, Chao-Kai and Li, Geoffrey Ye。
- 载体与年份：IEEE Communications Standards Magazine；2026。
- 类型：survey / framework。
- 阅读深度：A：公开 v3 的框架、监测讨论及 CSI 环境变化案例。
- 原始来源：[正式 DOI](https://doi.org/10.1109/MCOMSTD.2026.3728497)；[公开论文](https://arxiv.org/abs/2507.18538)。
- 书目状态：Journal DOI verified; final volume, issue, and pagination not independently verified

## 2. 问题、对象与前提

该工作讨论互操作 AI-native RAN 中模型从训练、存储、推理到监测和适配的生命周期。关键难点不是模型文件如何下载，而是无线环境、部署配置与多厂商模型之间的依赖如何持续保持有效。公开稿将管理层与 RAN 本地的不同时间尺度分开，不支持统一用远端慢速推理控制所有无线动作。

## 3. 方法与工作流程

框架联结数据、训练/适配、模型存储和推理监测，并讨论双侧 CSI 模型的跨厂商协作。慢速 OAM 与更快的 RAN-local LCM 分工，意味着规划、部署与紧急纠正不必由同一控制环完成。监测不仅看业务 KPI 绝对下降，也要识别模型是否仍适用于当前分布。

## 4. 实验证据、结果与局限

CSI 环境切换案例说明，环境变化后即使模型相对失配，绝对 SGCS 仍可能提升。因此“比过去差才换模型”的阈值逻辑会漏掉适用性变化。该案例不等于对多 UE 资源竞争、模型下载失败、跨端提交和长期恢复的完整评估；不能由框架覆盖推断这些性质已证明。

## 5. 对 LCMAgent 的具体影响

这是必须前置引用的直接近邻：LCM 闭环、互操作和分层控制均非空白。可进一步研究监测不足时采集什么证据、信息过期如何重验，以及决定与可靠执行如何衔接。其一般生命周期视角也支持把 LCMAgent 扩展到单侧波束/定位功能，而不是限定为配对 CSI。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 复现“绝对 KPI 改善但相对模型失配”的案例，排除只测显著退化的简单设定。
- 分别量化 OAM 规划延迟与本地 fallback 延迟。
- 在同样候选模型和监测接口上比较规则、统计策略与 Agent，隔离架构收益。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `huang2026interoperablelcm`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
