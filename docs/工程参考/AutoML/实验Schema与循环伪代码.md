# AutoML 实验 Schema 与循环伪代码

> 整理日期：2026-10-25。候选设计/示例；尚未实现或验证。原章节编号保留，便于核对旧稿。
> 本页为通用 AutoML 工程参考，代码与参数是设计示例，不代表 LCMAgent 已采用的接口或依赖。

[文档导航](../../README.md) · [原稿章节对照](../../整理说明.md)

---

> 来源：`AutoML_Agentic_AutoML_Research_Report_2026-10-22_v3_AutoResearch_Ecosystem.md`；2026-10-22 V3。

<a id="s13"></a>

## 13. 执行级伪代码、Schema 与实现示例

> 以下是**本报告原创的系统设计示例**，不是任何论文的官方伪代码。目标是表达模块边界、接口与可验证流程。代码可用作原型起点，但仍需依赖管理、数据检查、权限控制和安全测试后才能部署。

<a id="s13-1"></a>

### 13.1 类型化 ExperimentSpec（可作为 REST/gRPC schema 基础）

```json
{
  "task_id": "credit-risk-v1",
  "dataset_snapshot_id": "ds_20261001_abc123",
  "split_contract_id": "split_temporal_v2",
  "target_column": "default_next_90d",
  "objective": {"metric": "roc_auc", "direction": "maximize"},
  "proposal": {
    "hypothesis": "Improve a stable baseline using a limited gradient-boosted tree search",
    "method": "flaml",
    "config": {"time_budget": 900, "task": "classification"},
    "expected_failure_modes": ["high_cardinality", "class_imbalance"]
  },
  "limits": {"wallclock_seconds": 1200, "gpu_count": 0, "memory_gb": 16},
  "security": {"network": false, "read_only_dataset": true, "write_roots": ["/artifacts"]},
  "seed": 2026
}
```

验证器必须拒绝未知字段、越权路径、负预算、不允许的模型类型与不一致的 `split_contract_id`。理想情况下，LLM 只被允许输出这些限定字段，而真实任务执行由服务端拼装。

<a id="s13-2"></a>

### 13.2 基于反馈的安全实验循环伪代码

```python
from dataclasses import dataclass

@dataclass
class TrialResult:
    trial_id: str
    status: str           # completed / failed / cancelled
    score: float | None
    cost_seconds: float
    artifacts: dict
    diagnostics: dict


def agentic_automl(task, tools, policy, budget):
    task = policy.validate_task(task)
    profile = tools.profile_dataset(task.dataset_snapshot_id)
    evaluation = tools.create_locked_evaluation_contract(task, profile)

    baseline = tools.fit_baseline(task, evaluation, budget=budget.baseline)
    best = tools.verify_trial(baseline, evaluation)
    history = [best]

    while budget.can_schedule_trial():
        # Language model proposes a hypothesis; it does not alter evaluator/test data.
        hypothesis = tools.plan_next_experiment(
            task=task,
            profile=profile,
            history=tools.summarize(history),
            remaining_budget=budget.snapshot(),
        )
        proposal = policy.validate_proposal(hypothesis, evaluation)
        if proposal is None:
            continue

        # External scheduler has full authority over resources and execution.
        job = tools.submit_trial(proposal, evaluation, budget)
        result: TrialResult = tools.wait_for_result(job)
        result = tools.verify_trial(result, evaluation)
        history.append(result)
        budget.debit(result)

        if result.status == "completed" and policy.is_better(result, best):
            best = result
        if policy.stop_condition(history, budget):
            break

    # Locked test set is evaluated once as part of release gating.
    selected = tools.finalize_model(best, evaluation)
    report = tools.generate_audit_report(task, history, selected)
    return tools.request_human_approval(selected, report)
```

**注意**：生产实现不能无限 `continue` 避免非法提案不消耗配额；应引入 `max_invalid_proposals` 与决策 token 限额，并让 scheduler 以真实 wall-clock 扣费。`wait_for_result` 应由异步队列/事件服务实现，此伪代码只表达逻辑。

