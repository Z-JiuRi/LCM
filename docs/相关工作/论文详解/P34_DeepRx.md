# [P34] DeepRx: Fully Convolutional Deep Learning Receiver

> 核验/解读日期：2026-10-20。对应综述编号 `P34`，BibTeX key：`honkala2021deeprx`。

## 1. 文献信息与阅读边界

- 作者/机构：Honkala, Mikko and Korpi, Dani and Huttunen, Janne M. J.。
- 载体与年份：IEEE Transactions on Wireless Communications；2021。
- 类型：pure method / neural receiver。
- 阅读深度：B：原始摘要、正式记录及与后续 VERITAS 的关系；未全面复审全文。
- 原始来源：[正式 DOI](https://doi.org/10.1109/TWC.2021.3054520)；[公开论文](https://arxiv.org/abs/2005.01494)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

DeepRx 研究全卷积学习式接收机，目标是将传统分块接收链中的部分处理整合学习，改善复杂信道条件下的检测。它是 LCMAgent 可以管理的实时无线执行功能，而不是管理 Agent 本身。

## 3. 方法与工作流程

网络使用接收频域信号及导频信息产生发送比特的软信息。输入组织、导频、调制和天线配置决定其语义；“输出维度相同”不足以保证接收机可直接替换。软输出的定义还会影响后续译码，必须与实际链路配置共同验证。

## 4. 实验证据、结果与局限

正式 IEEE TWC 2021，20(6):3925–3940，DOI 10.1109/TWC.2021.3054520；2020 为公开稿首发。本轮不列未经逐图复核的 BER 增益。静态训练/测试优势不能证明真实部署后跨时延扩展、移动速度或硬件变化的可靠性。

## 5. 对 LCMAgent 的具体影响

与波束模型相比，神经接收机的实时性、计算预算和错误传播约束更强。LCMAgent 可决定监测/参考解码预算、模型验收与更新窗口，但不能令逐符号解调等待远端 LLM。部署后恢复应比较 P36，而不能只与永久不更新的 DeepRx 比较。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 核对导频、MCS、天线、输入归一化和软输出语义。
- 同时报告 BER/BLER、译码延迟和并行参考处理算力。
- 用真实配置变更和信道漂移区分结构不兼容与性能退化。

## 7. 引用与导航

### 公开实现

[DeepRx-OFDM-PyTorch](https://github.com/G-ALI007/DeepRx-OFDM-PyTorch) 是公开的第三方复现，README 报告与传统 LMMSE 接收机对比；论文作者未将其列为官方 artifact，GitHub 未检测到 SPDX 许可证。它可作为代码候选，不可作为论文结果已被复现的证据。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `honkala2021deeprx`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
