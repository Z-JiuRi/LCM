# [P21] Invariant-Guided Logical Testing of Open RAN Controllers

> 核验/解读日期：2026-10-20。对应综述编号 `P21`，BibTeX key：`yang2026invaran`。

## 1. 文献信息与阅读边界

- 作者/机构：Yang, Tianchang and Ranjbar, Ali and Tan, Gang and Hussain, Syed Rafiul。
- 载体与年份：35th USENIX Security Symposium (USENIX Security 26)；2026。
- 类型：system / testing。
- 阅读深度：B：USENIX 官方摘要、书目和 artifact 入口。
- 原始来源：[原始材料/作者入口](https://www.usenix.org/conference/usenixsecurity26/presentation/yang-tianchang)。
- 书目状态：已核对题名、作者及上述原始入口；不声称已经运行论文代码。

## 2. 问题、对象与前提

InvaRAN 针对 Open RAN 控制器的逻辑错误进行不变量引导测试。安全执行器和 validator 并非天然正确；规则遗漏、状态组合和异常顺序会使“确定性”程序仍然违反实际控制约束。

## 3. 方法与工作流程

工作以动态推断的不变量引导逻辑测试，检查控制器行为。动态不变量来自已观察运行，不是覆盖所有状态的数学真理，因此需结合测试生成与反例分析。其研究对象是控制器逻辑，不能误写成训练 LLM 让其自我批评。

## 4. 实验证据、结果与局限

USENIX Security 2026 官方记录页码 711–730，摘要报告发现 9 个此前未知问题，其中 7 个逻辑问题、2 个内存问题。本次未运行 artifact，也未核对每个问题的触发细节；不猜测 arXiv ID，不根据别人文件名填写标识。

## 5. 对 LCMAgent 的具体影响

LCMAgent 应测试守卫自身：比如忘记码本版本、同一资源重复预留、超时后仍接受旧授权、回退资源已释放等。只测 Agent 输出是否为合法 JSON 会错过根本风险。测试提供反例证据，不自动成为协议形式验证。

## 6. 精读/复现与实验检查项

以下是后续工作建议，不是本次已经完成的复现，也不是原论文额外报告的结论。

- 为功能配置、资源和证据时效建立候选不变量并寻找反例。
- 对 validator 做状态机和并发故障注入，而非仅做输入格式测试。
- 保留 artifact 版本和复现条件，运行前不声称确认原文缺陷。

## 7. 引用与导航

### 公开代码

[INVARAN artifact](https://github.com/SyNSec-den/INVARAN) README 描述轨迹插桩、关键不变量分类、关联分析、断言插桩及 fuzzing。仓库注明部分 trace 为便于普通内存设备运行而缩减，结果可能与论文略有不同；GitHub 未检测到 SPDX 许可证。本次未运行 artifact。

- 本文只解读已说明阅读层级的材料；未核验处不作“原文没有”的否定判断。
- [统一 BibTeX 与条目索引](../参考文献.md)：检索 `yang2026invaran`。
- [LCMAgent 深度综述](../../docs/LCMAgent相关论文综述与研究定位.md) · [详解目录](README.md)。
