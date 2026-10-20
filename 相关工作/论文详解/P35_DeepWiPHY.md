# [P35] DeepWiPHY: Deep Learning-Based Receiver Design and Dataset for IEEE 802.11ax Systems

> 核验/解读日期：2026-10-20。对应综述编号 `P35`，BibTeX key：`zhang2021deepwiphy`。

## 1. 文献信息与阅读边界

- 作者/机构：Zhang, Yi and Doshi, Akash and Liston, Rob and Tan, Wai-tian and Zhu, Xiaoqing and Andrews, Jeffrey G. and Heath, Robert W.。
- 载体与年份：IEEE Transactions on Wireless Communications；2021。
- 类型：method + dataset。
- 阅读深度：B：原始摘要、正式记录和作者机构公开 PDF 入口。
- 原始来源：[正式 DOI](https://doi.org/10.1109/TWC.2020.3034610)；[公开论文](https://arxiv.org/abs/2010.09268)；[原始材料/作者入口](https://www.merl.com/publications/docs/TR2021-043.pdf)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

DeepWiPHY 面向 IEEE 802.11ax 接收处理，结合学习式接收机设计与数据集。它提醒无线神经功能研究应考虑真实射频和接收链失真，而不只是理想化仿真信道。其协议场景是 Wi-Fi，不能直接写成 5G NR 接收器实验。

## 3. 方法与工作流程

工作联合考虑均衡、公共相位误差及相关采样偏差补偿等接收任务，并使用仿真与实测数据。具体模块接口和训练配置应以原文为准，不能把它扩展成通用端到端全协议替换。实测的硬件和采集状态也可能成为输入分布的一部分。

## 4. 实验证据、结果与局限

正式 IEEE TWC 2021，20(3):1596–1611，DOI 含 2020 对应早期发表。数据集和作者公开文本提供较好的复核入口，但本轮没有运行代码。跨设备和跨时间的稳定性需实际划分验证，不能因为数据“真实”就默认分布覆盖充分。

## 5. 对 LCMAgent 的具体影响

LCMAgent 可把硬件校准、同步处理、输入/输出语义纳入接收功能契约。与 DeepRx 的共同点是本地快速执行；不同点在协议与前处理，不能共用一个未经适配的安全检查器。管理层可以共享证据格式，却必须保留协议专用验证和 fallback。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 先确认数据许可、接收硬件和训练测试采集条件。
- 分别测仿真到实测、跨硬件及跨日期差异，而非只随机划分。
- 把校准修复与 NN 权重更新分开比较，防止误诊硬件问题。

## 7. 引用与导航

### 代码核对

本次未找到可确认对应 DeepWiPHY 的公开仓库。曾被误关联的 [`zhongyuanzhao/dl_ofdm`](https://github.com/zhongyuanzhao/dl_ofdm) 实际对应另一篇 *Deep-Waveform* 论文，已排除，不应作为 DeepWiPHY 代码克隆。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `zhang2021deepwiphy`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
