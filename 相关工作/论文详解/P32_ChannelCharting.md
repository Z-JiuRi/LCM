# [P32] Channel Charting: Locating Users Within the Radio Environment Using Channel State Information

> 核验/解读日期：2026-10-20。对应综述编号 `P32`，BibTeX key：`studer2018channelcharting`。

## 1. 文献信息与阅读边界

- 作者/机构：Studer, Christoph and Medjkouh, Saïd and Gönültaş, Emre and Goldstein, Tom and Tirkkonen, Olav。
- 载体与年份：IEEE Access；2018。
- 类型：pure method。
- 阅读深度：B：原始记录、摘要与正式 DOI，未复审所有实验。
- 原始来源：[正式 DOI](https://doi.org/10.1109/ACCESS.2018.2866979)；[公开论文](https://arxiv.org/abs/1807.05247)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

Channel Charting 利用 CSI 中反映传播几何的结构，在缺少绝对位置标签时形成低维信道图。目标是保留相近用户在表示空间中的局部关系；不能直接将其写成已有绝对坐标精度保证的定位方案。

## 3. 方法与工作流程

方法从信道特征学习或构建保持局部几何的低维表示，把 CSI 相似性与空间邻域联系起来。相对图、绝对坐标定位与后续坐标对齐是不同步骤。具体降维变体、预处理和质量指标需要按原文实验逐项选择，不能把后续领域中的所有算法都归给这篇奠基工作。

## 4. 实验证据、结果与局限

IEEE Access 2018 的正式记录和公开稿可核对。当前不列未经复审的米级误差；尤其不能从“locating users”题名推断其直接输出 WGS84 坐标。图的可靠性受数据覆盖、环境变化和测量配置影响，不存在只凭可视化就证明定位泛化的结论。

## 5. 对 LCMAgent 的具体影响

LCMAgent 若管理信道图功能，应版本化 CSI 特征、参考图、邻域、坐标对齐和锚点，而不只保存 NN 权重。图变化可能改变位置/波束决策下游语义。适配验收需检查局部结构和下游功能，不应照搬 CSI NMSE 或只看图像形状。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 明确输出是相对图还是绝对坐标，标识坐标映射来源。
- 留出区域和新采集日期，测试图更新后邻域是否稳定。
- 将图更新与下游波束/定位模型的依赖写入 manifest，测联合失配。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `studer2018channelcharting`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
