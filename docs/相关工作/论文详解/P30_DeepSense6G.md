# [P30] DeepSense 6G: A Large-Scale Real-World Multi-Modal Sensing and Communication Dataset

> 核验/解读日期：2026-10-20。对应综述编号 `P30`，BibTeX key：`alkhateeb2022deepsense6g`。

## 1. 文献信息与阅读边界

- 作者/机构：Alkhateeb, Ahmed and Charan, Gouranga and Osman, Tawfik and Hredzak, Andrew and Morais, João and Demirhan, Umut and Srinivas, Nikhil。
- 载体与年份：公开稿 / arXiv；2022。
- 类型：pure benchmark / dataset。
- 阅读深度：B：数据集论文摘要和官方项目入口；未下载全量数据或运行代码。
- 原始来源：[公开论文](https://arxiv.org/abs/2211.09769)；[原始材料/作者入口](https://deepsense6g.net/)。
- 书目状态：First posted 2022; public revision v2 dated 2023-03-20; dataset paper

## 2. 问题、对象与前提

DeepSense 6G 面向真实多模态感知与通信联合研究，提供比纯仿真信道更接近实际环境的研究资源。其相关性不限于某个预测器，而是支持位置/视觉等信息辅助波束决策、以及研究跨场景变化。

## 3. 方法与工作流程

数据集将通信测量与多类感知信息相联系，具体可用模态和标注应逐个 scenario 核对。不能假定每个场景都有 GPS、相机、雷达和 LiDAR 的完整同步观测，也不能把离线最佳波束标签视为在线零成本可获得。数据采集同步和传感器坐标是模型输入语义的一部分。

## 4. 实验证据、结果与局限

这是资源型工作，不按“方法提高多少百分比”评价。可复用性取决于轨迹连续性、时间戳、可用模态、许可证、划分和标签定义。官方列出数据或基准，不代表本地已下载、校验或复现；本轮没有产生任何该数据集上的新性能结果。

## 5. 对 LCMAgent 的具体影响

它适合成为 LCMAgent 单侧波束主用例的数据起点，但无法单独提供网络动作对后续状态的反馈、模型下载延迟、UE 温度或丢包协议。可以先做时间有序轨迹回放的证据策略研究，再连接仿真/真实闭环；不得将离线回放包装为 OTA 系统实验。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 按场景建立模态、时间连续性、标签和许可清单。
- 用轨迹/日期/场景留出而非随机快照划分，参考 P31 的漂移分析。
- 给扫描、传感器读取和模型切换显式加成本，并声明哪些成本为模拟。

## 7. 引用与导航

### 相关代码

DeepSense6G 的 V2V beam prediction challenge 有 [官方 baseline](https://github.com/DeepSense6G/Multi-Modal-V2V-Beam-Prediction-Challenge-2023-Baseline)；另有 [ITU AI/ML in 5G challenge 团队方案](https://github.com/ITU-AI-ML-in-5G-Challenge/DeepSense6G_TII)，MIT 许可。二者是数据集/挑战方案代码，不是原始 DeepSense6G 数据集论文的完整源码或数据下载包；前者 GitHub 未检测到 SPDX 许可证。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `alkhateeb2022deepsense6g`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
