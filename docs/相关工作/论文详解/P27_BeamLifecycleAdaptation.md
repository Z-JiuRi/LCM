# [P27] Model Adaptation for Lifecycle Management in AI-native 5G/6G Networks

> 核验/解读日期：2026-10-20。对应综述编号 `P27`，BibTeX key：`go2025beamlifecycleadaptation`。

## 1. 文献信息与阅读边界

- 作者/机构：Go, Jewoo and Park, Taeje and Sung, Wonjin。
- 载体与年份：2025 16th International Conference on Information and Communication Technology Convergence (ICTC)；2025。
- 类型：pure method / LCM procedure。
- 阅读深度：A：ICTC 原始六页 PDF 的流程、仿真配置和结论。
- 原始来源：[正式 DOI](https://doi.org/10.1109/ICTC66702.2025.11388480)；[原始材料/作者入口](https://d2j16w31g89z0j.cloudfront.net/site/ictc2025/abs/C08-2.pdf)。
- 书目状态：Public conference PDF and Crossref pagination differ; page range omitted pending final-version verification

## 2. 问题、对象与前提

Jewoo Go、Taeje Park、Wonjin Sung 将 model adaptation 作为 AI-native 5G/6G 的生命周期机制，针对动态传播环境中波束模型适用性下降。这里的 adaptation 包括基于支持信息推荐、测试并激活更适合的模型，不应直接等同于在线梯度微调。

## 3. 方法与工作流程

流程包含网络发现退化并请求信息、UE 报告能力和当前状态、网络下发适配信息、UE 在给定数据上评估推荐模型并申请激活、网络最终发送激活指示。论文使用模型/数据/场景等支持信息指导选择。它是单侧推理仍需端网协作的直接例子，既不是双侧 latent 配对，也不要求两端各有 LLM。

## 4. 实验证据、结果与局限

仿真训练 54 个模型，推理序列 5,000 步；周期评估，示例 $T_{\mathrm{LCM}} = 1\,\mathrm{s}$、$\gamma_{\mathrm{RSRP}} = 5\,\mathrm{dB}$。比较无 LCM、仅 dataset ID 与所提适配。适配测试使用当前扇区随机采样的 5,000 个位置，这种信息条件非常强，需与线上可采集标签区分。论文文字对 eRSRP、退化方向和参考值的描述需结合图核对，不能把误差阈值抄成通用标准。

## 5. 对 LCMAgent 的具体影响

该文覆盖网络推荐—UE 测试—网络确认激活的主链。因此 LCMAgent 不应声称首次提出这套协作。值得检验的是只有少量实测、标签延迟、模型测试耗能且证据会过期时，如何选择补测和验收；公平基线要给各策略同一候选与评估预算，不能让 Agent 获得更便宜的环境真值。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 复现 54 模型候选库与 dataset-only/non-LCM 基线，再限制适配测试数据量。
- 记录监测间隔、阈值、候选数与评估成本的联合权衡。
- Crossref 页码与公开会议 PDF 页脚存在差异，引用时不混用，优先补核正式版。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `go2025beamlifecycleadaptation`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
