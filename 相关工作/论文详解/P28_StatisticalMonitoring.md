# [P28] Statistical AI/ML Model Monitoring for 5G/6G: Interference Prediction Case Study

> 核验/解读日期：2026-10-20。对应综述编号 `P28`，BibTeX key：`kaswan2024statisticalmonitoring`。

## 1. 文献信息与阅读边界

- 作者/机构：Kaswan, Priyanka and Marzban, Mohamed F. and Nam, Wooseok and Akkarakaran, Sony and Luo, Tao。
- 载体与年份：2024 IEEE International Conference on Communications Workshops (ICC Workshops)；2024。
- 类型：pure method / monitoring。
- 阅读深度：A：正式书目与作者上传原文的三类方案、统计检验及实验表；未运行代码。
- 原始来源：[正式 DOI](https://doi.org/10.1109/ICCWorkshops59551.2024.10615307)；[原始材料/作者入口](https://www.researchgate.net/publication/379653127_Statistical_AIML_Model_Monitoring_for_5G6G_Interference_Prediction_Case_Study)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

Kaswan 等研究 5G/6G 的统计 AI/ML 模型监测，以干扰预测为案例。干扰预测模型上线后，环境与干扰流量变化会影响其适用性；仅知道网络 KPI 变差，未必能判断是预测器失效还是干扰本身变强。

## 3. 方法与工作流程

方案一只看模型输入/输出统计，将部署与训练时的分布用 Kolmogorov–Smirnov 检验比较；方案二在部署前训练反向映射，用预测输出重建输入，再比较重建值与真实输入；方案三等延迟干扰真值可得，用预测残差检验性能。三类方案按能获得多少模型信息及真值分层，不能只拿需要真值的最好检测率去与无标签方案比较。

## 4. 实验证据、结果与局限

仿真任务为预测未来一个 slot 的干扰统计；原文表格测试均值、方差、skewness、kurtosis 以及联合使用。方案一在 100 个监测样本和全部统计量时，既有基准误报约 6.5%，改变干扰业务/数量/场景后的检出约 99%、82%、90%，而单用均值对部分变化敏感性较弱。该表是特定单次检验设定，不是长期连续检验的全局误报保证。正式载体是 ICC Workshops 2024，638–643。

## 5. 对 LCMAgent 的具体影响

它使 LCMAgent 的相关工作从 CSI/波束扩展到干扰与通用监测。应把统计监测器作为可调用证据工具或非 LLM 基线，比较同误报约束下检测、补测及错误干预代价。论文若已覆盖某种触发与恢复，须据全文实质比较，而非凭摘要宣称空白。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 分别复现无模型、反向模型和延迟真值三种信息条件，记录不同部署代价。
- 分别扰动干扰强度、负载周期和预测模型参数，避免把物理变化等同模型错误。
- 检查 KS/t 检验的样本依赖及重复监测问题，再绘制误报—时延—成本曲线。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `kaswan2024statisticalmonitoring`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
