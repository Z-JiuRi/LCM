# NAS、元学习与基础模型路线

> 整理日期：2026-10-25。原文整理；未新增文献核验或实验结果。原章节编号保留，便于核对旧稿。

[文档导航](../../README.md) · [原稿章节对照](../../整理说明.md)

---

> 来源：`AutoML_Agentic_AutoML_Research_Report_2026-10-22_v3_AutoResearch_Ecosystem.md`；2026-10-22 V3。

<a id="s6"></a>

## 6. 神经架构搜索、元学习与基础模型路线

<a id="s6-1"></a>

### 6.1 NAS 的三个设计空间

典型 NAS 至少包含三个问题：

1. **Search Space**：选择哪些层、算子、连接拓扑、宽度、深度或输入尺度；
2. **Search Strategy**：RL、进化算法、随机/BO、梯度法、one-shot weight sharing；
3. **Performance Estimation**：完整训练、early stopping、proxy task、weight sharing、zero-cost proxy。

若不在相同的训练 epoch、算力、数据处理和再训练协议下比较，NAS 性能结果容易严重偏差。[R01], [R09], [R17]

<a id="s6-2"></a>

### 6.2 DARTS：连续松弛使离散架构可微

**论文**：Liu et al., *DARTS: Differentiable Architecture Search*，ICLR 2019。[R09]

将原本离散的操作选择，通过 softmax 权重组合成连续化的混合操作，在验证损失和训练损失之间执行近似双层优化：

$$
\min_\alpha \mathcal L_{val}(w^*(\alpha),\alpha),
\quad\mathrm{s.t.}\quad w^*(\alpha)=\arg\min_w\mathcal L_{train}(w,\alpha)
$$

这里 $\alpha$ 代表架构选择参数，$w$ 代表网络权重。DARTS 减轻离散架构搜索的计算开销，但梯度松弛与离散架构最终表现之间可能有偏差，并受架构塌缩、训练稳定性影响。**Agent 不能简单把 DARTS 与代码改写搜索视为同一类算法。**

<a id="s6-3"></a>

### 6.3 NAS-Bench-101：可重复实验的基础设施

**论文**：Ying et al., *NAS-Bench-101: Towards Reproducible Neural Architecture Search*，ICML 2019。[R17]

公开预计算架构性能数据库（423k 余个独特卷积架构，多次评估），让 NAS 搜索策略可以低成本模拟和重复比较。关键贡献不只是某个架构表现更好，而是把“搜索器质量”与“重新训练成本”在一定程度上解耦。

**对 Agentic AutoML 的迁移**：构造离线可查询的历史实验仓库，以低成本评估 Agent 选择下一实验的策略；随后再在真实代码执行环境里验证。离线模拟有利于策略迭代，但也会失去开放式代码修改和异常调试的重要挑战。

<a id="s6-4"></a>

### 6.4 TabRepo：可复用的表格模型经验数据库

**论文**：Salinas & Erickson, *TabRepo: A Large Scale Repository of Tabular Model Evaluations and its AutoML Applications*，AutoML 2024。[R12]

论文摘要报告：在 200 个分类与回归数据集上评估 1,206 个模型并记录预测与指标，可用于模拟 ensemble、模型选择与迁移学习。注意项目后续仓库可能维护了更大版本，**论文统计与当前仓库统计不应混用**。[R12]

这个方向非常适合 Agent：把经验存成 `(data meta-features, pipeline/config, score distribution, latency, failure)`，在推理时依据历史相似性做有证据的搜索空间缩减，而不只检索自然语言文章。

<a id="s6-5"></a>

### 6.5 TabPFN 和 TabArena 改变什么

**TabPFN**，Hollmann et al., *Accurate predictions on small data with a tabular foundation model*，Nature，2025 年 1 月发表。[R18] 该论文讨论通过预训练的表格基础模型在小数据任务上的快速推断与竞争力，并在其指定实验条件下报告非常显著的效率提升。**不可泛化为“任何表格任务都优于 GBDT”，也不能忽视内存、数据规模、类别/特征限制及许可证。**

**TabArena**，Erickson et al., 2025 年 arXiv 预印本，提出持续维护的表格学习评估平台，强调验证协议、不同时间预算、模型集成，以及表格基础模型在较小数据集上的优势。[R19]

**对 Agent 架构的重大影响**：部分过去需要长时间搜索的场景，可能只需选择强表格基础模型或预训练 portfolio；Agent 的价值转向**任务识别、是否需要搜索、何时调用基础模型、是否需要 ensemble、是否满足许可/延时约束**。

<a id="s6-6"></a>

### 6.6 AutoML 的三条长期路线

| 路线 | 主要优化方式 | 研究难点 | 预计更适合的情形 |
|---|---|---|---|
| 搜索型 AutoML | 在已知空间采样、训练、评价 | 算力、维度、条件性、低保真偏差 | 模型可训练、指标清晰、部署约束复杂 |
| Meta/Portfolio 型 | 从历史数据迁移配置或模型族排序 | 任务相似度、OOD 泛化、经验污染 | 频繁重复的类似业务问题 |
| Foundation Model 型 | 预训练模型迁移/近零搜索预测 | 通用性、数据规模、许可证、可解释性 | 小中等数据、快速开发、数据分布适配良好 |

合理系统不必二选一：可按资源和任务估计先选择基础模型/portfolio，再投入残余预算做 HPO 与集成。

---

<!-- 本页使用的引用定义；书目详情由对应资料索引维护。 -->
[R09]: https://mlanthology.org/iclr/2019/liu2019iclr-darts/ "Liu et al. — DARTS"
[R12]: https://proceedings.mlr.press/v256/salinas24a.html "Salinas and Erickson — TabRepo"
[R17]: https://proceedings.mlr.press/v97/ying19a.html "Ying et al. — NAS-Bench-101"
[R18]: https://www.nature.com/articles/s41586-024-08328-6 "Hollmann et al. — TabPFN (Nature 2025)"
[R19]: https://arxiv.org/abs/2506.16791 "Erickson et al. — TabArena"
[R01]: https://www.automl.org/book/ "Hutter, Kotthoff, Vanschoren (eds.) — AutoML: Methods, Systems, Challenges"
