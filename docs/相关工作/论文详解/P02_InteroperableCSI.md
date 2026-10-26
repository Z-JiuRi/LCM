# [P02] Demonstrating Interoperable Channel State Feedback Compression With Machine Learning

> 核验/解读日期：2026-10-20。对应综述编号 `P02`，BibTeX key：`korpi2026interoperablecsi`。

## 1. 文献信息与阅读边界

- 作者/机构：Korpi, Dani and Wang, Rachel and Wang, Jerry and Ibrahim, Abdelrahman and Nuzman, Carl and Wang, Runxin and Mestav, Kursat Rasim and Zhang, Dustin and Saniee, Iraj and Winston, Shawn and Pavlovic, Gordana and Ding, Wei and Hillery, William J. and Hao, Chenxi and Thirunagari, Ram and Chang, Jung and Kim, Jeehyun and Kozicki, Bartek and Samardzija, Dragan and Yoo, Taesang and Maeder, Andreas and Ji, Tingfang and Viswanathan, Harish。
- 载体与年份：IEEE Wireless Communications；2026。
- 类型：method + system。
- 阅读深度：A：公开全文、OTA 实验和比较条件。
- 原始来源：[正式 DOI](https://doi.org/10.1109/MWC.2025.3630622)；[公开论文](https://arxiv.org/abs/2506.21796)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

跨厂商 CSI 压缩面临双方不愿公开私有模型、却必须共同完成编码/解码的问题。论文研究如何在保密约束下形成互操作模型，并将性能从离线重构指标延伸到真实无线链路收益。它比“两个工具分别运行 encoder 和 decoder”更直接触及跨厂商可用性。

## 3. 方法与工作流程

方法采用顺序协作训练，使不同参与方在不完整公开彼此模型的条件下生成可互操作的 CSI 反馈组件，再在原型中进行 OTA 评估。需要区分“训练出来的组合可用”与“运行中的多版本安全切换”：前者提供合法候选配对，后者仍依赖配置、版本及激活流程。

## 4. 实验证据、结果与局限

论文报告相对 Type I 反馈约 30%–100%、平均约 60% 的下行吞吐量提升。但比较中的传统方案使用宽带预编码，ML 方案使用子带预编码，不能把全部提升归因于压缩网络。OTA 原型是较强实证，也不自动覆盖大规模设备、失联、并发更新或资源不足。

## 5. 对 LCMAgent 的具体影响

LCMAgent 不应再声称首次实现双侧模型互操作；可以把该类训练结果作为候选模型库，研究何时选择/激活以及失败恢复。波束用例不必复刻相同训练保密流程，但同样要明确输入码本、配置和校准依赖。跨用例共享的是管理契约，不是强行统一模型结构。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 重建传统与 ML 方案的预编码粒度、反馈预算和资源占用对照表。
- 把配对已合法作为基线前提，再注入版本或量化失配。
- 同时报告重构、实际吞吐和切换损失，不用单一 NMSE 代替部署收益。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `korpi2026interoperablecsi`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
