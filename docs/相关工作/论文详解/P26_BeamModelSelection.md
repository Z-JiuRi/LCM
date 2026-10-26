# [P26] AI Model Selection and Monitoring for Beam Management in 5G-Advanced

> 核验/解读日期：2026-10-20。对应综述编号 `P26`，BibTeX key：`sun2024beammodelmonitoring`。

## 1. 文献信息与阅读边界

- 作者/机构：Sun, Chen and Zhao, Le and Cui, Tao and Li, Haojin and Bai, Yingshuang and Wu, Songtao and Tong, Qiang。
- 载体与年份：IEEE Open Journal of the Communications Society；2024。
- 类型：method / beam management。
- 阅读深度：A：补读 13 页作者接受稿的波束选择、监测算法和仿真；正式版书目另核。
- 原始来源：[正式 DOI](https://doi.org/10.1109/OJCOMS.2023.3337850)；[原始材料/作者入口](https://artefacts-discovery.researcher.life/full_text/DA-2/68/686bdce43f2a3f6b9723dc4ba34adb33/full_text/3639d145330dd9fe30a87f1b1284dea0.pdf)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

波束预测器可减少扫描，但一个离线模型不一定适用于所有 UE、码本与传播条件。这篇工作直接研究 5G-Advanced 波束管理中的 AI 模型选择和监测，因此“波束场景此前没有 LCM”是错误定位。作者是 Chen Sun、Le Zhao、Tao Cui、Haojin Li、Yingshuang Bai、Songtao Wu、Qiang Tong。

## 3. 方法与工作流程

工作先比较环境分区专用波束模型与覆盖所有区域的统一模型，研究 beam ID 和物理方向两种输出。监测阶段不是只看 AI 波束 RSRP 下降，而用 LSTM 分别预测 AI 与传统波束管理的 RSRP：两者都恶化时，原因可能是进入困难传播环境，回退未必有益；仅 AI 相对变差才更支持切换。算法以预测 3 dB drop 位置的重合来计算可避免的回退，已经实质研究“退化归因与干预价值”。

## 4. 实验证据、结果与局限

正式记录为 IEEE Open Journal of the Communications Society，5:38–50，2024；2023 是早期记录。接受稿中某条轨迹上的回退从 294 次减到 264 次，约减少 10%；这是相对特定 3 dB 触发基线的轨迹统计，不是全场景安全率。统一深层模型没有在其分区实验中胜过专用模型，也不证明大模型普遍无效。监测预测器自身有误差，代价与校准仍需检查。

## 5. 对 LCMAgent 的具体影响

LCMAgent 的波束扩展必须前置比较该文，而不是仅引用 DeepBeam 这类执行模型。潜在差异应具体为：预算不足时主动选择额外扫描、配置变化后撤销旧证据、候选模型评估成本和跨端激活恢复。不能把“由 Agent 选择模型”本身作为新问题；也不能用一个弱阈值策略冒充该文完整复现。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 优先复现 AI/传统双性能预测，而非以只看 AI 下降的弱阈值冒充该方法。
- 核对 top-K、RSRP/速率损失和测量开销，避免只比较分类准确率。
- 记录 294→264 的轨迹和预测误差条件；没有代码复现前不写优于原文。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `sun2024beammodelmonitoring`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
