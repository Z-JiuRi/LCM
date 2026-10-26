# [P03] Performance Monitoring-Enabled Reliable AI-Based CSI Feedback

> 核验/解读日期：2026-10-20。对应综述编号 `P03`，BibTeX key：`guo2025csimonitoring`。

## 1. 文献信息与阅读边界

- 作者/机构：Guo, Jiajia and Ma, Shaodan and Wen, Chao-Kai and Jin, Shi。
- 载体与年份：IEEE Transactions on Wireless Communications；2025。
- 类型：pure method。
- 阅读深度：B：作者机构原始摘要与正式书目；全文实验条件尚未补齐。
- 原始来源：[正式 DOI](https://doi.org/10.1109/TWC.2024.3490600)；[原始材料/作者入口](https://researchportal.hkust.edu.hk/en/publications/performance-monitoring-enabled-reliable-ai-based-csi-feedback/)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

CSI 反馈质量在传输前不易获知：BS 才能用完整 decoder 重建，而 UE 要决定本次压缩反馈是否可靠。仅靠 BS 长窗口 KPI 检测过于间接，也可能来不及拦截低质量样本。该工作直接研究低开销、样本级性能监测，而非仅优化平均重构精度。

## 3. 方法与工作流程

已核验的机制是在 UE 放置经知识蒸馏训练的轻量 proxy decoder，近似 BS 端重建行为，让 UE 在发送 codeword 之前估计质量。proxy 是对当前实际 decoder 的近似，因此其训练对象、版本一致性和近似误差都影响监测是否可信；不能把它等同于真实重构标签。

## 4. 实验证据、结果与局限

摘要报告接近 95% 的低质量样本检测能力，但本轮未获得足以核对全部阈值、误报、样本定义和开销的全文材料，不外推为部署安全率。检测率若不同时说明低质量比例、漏报和误报，就不足以比较实际业务代价。

## 5. 对 LCMAgent 的具体影响

“UE 本地先验证”“只发紧凑质量证据”已有直接先例。LCMAgent 可以把 proxy 结果作为一种证据动作，研究何时调用、何时过期及何时需要更昂贵的 BS 复核。若 decoder 更新而 proxy 未更新，证据可能失效；这一管理问题是项目分析，不是声称原论文已经给出的结论。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 补读全文并记录质量阈值、误报率及 proxy 的参数/FLOPs/能耗开销。
- 用完全相同 decoder 版本比较 proxy、完整 shadow 重构及固定规则。
- 注入 proxy 与 decoder 版本不一致，检查监测证据能否被撤销。

## 7. 引用与导航

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `guo2025csimonitoring`。
- [LCMAgent 深度综述](../../分析文档/LCMAgent/README.md) · [详解目录](README.md)。
