# AutoML 工具 API、提示约束与搜索树

> 整理日期：2026-10-25。候选设计/示例；尚未实现或验证。原章节编号保留，便于核对旧稿。
> 本页为通用 AutoML 工程参考，代码与参数是设计示例，不代表 LCMAgent 已采用的接口或依赖。

[文档导航](../../README.md) · [原稿章节对照](../../整理说明.md)

---

> 来源：`AutoML_Agentic_AutoML_Research_Report_2026-10-22_v3_AutoResearch_Ecosystem.md`；2026-10-22 V3。

<a id="s13-6"></a>

### 13.6 设计可执行的 Agent 工具 API

推荐工具签名：

```text
profile_dataset(dataset_id) -> DataProfile
create_eval_contract(task_spec, profile) -> EvalContract
list_allowed_search_spaces(task_type, budget) -> SearchSpace[]
retrieve_prior_experiments(meta_features, constraints, top_k) -> PriorRun[]
submit_search(engine, search_space, eval_contract, budget) -> JobID
get_job_status(job_id) -> JobStatus
read_structured_results(job_id) -> TrialResult[]
compare_candidates(candidate_ids, eval_contract) -> Scorecard
request_model_registration(candidate_id, approval_token) -> RegistryRequest
```

工具输出建议做**去噪和结构化**：只返回最相关的日志、错误类型、资源耗费与指标变化。例如让 Agent 看到 `failure_type=OOM; expected_memory=24GB; limit=16GB`，而不是 100,000 行原始 traceback。

<a id="s13-7"></a>

### 13.7 Prompt 的最小必要约束（设计示例）

> 你是 AutoML 规划器。你只能提出符合 TaskSpec、EvaluationContract 和 Budget 的实验建议。不得改变测试集、标签定义、数据切分、评估程序或权限。每条建议必须说明假设、预期收益、可能失败原因、预计资源和中止条件。若数据泄漏风险未排除，应先调用验证工具；不得通过提高验证分数来证明未知信息真实可用。输出必须符合 `ExperimentProposal` JSON Schema。

该模板的价值不在文采，而在**可被程序化检查**。Prompt 限制是辅助护栏，不是足以替代运行时权限隔离的安全机制。

<a id="s13-8"></a>

### 13.8 长程搜索的树节点结构

```text
Node(
    node_id, parent_id,
    code_hash, dataset_hash,
    change_type, hypothesis,
    metric_vector, cost_vector,
    reproducibility_status,
    error_category, audit_state,
)
```

每次修改只改变有限维度（例如同一轮只改特征工程，不同时更换分层切分、模型和调参方案），有利于归因。探索树定期做分支压缩和回放测试；验证集异常大幅提升时，应优先审查泄漏，而不是自动设为最佳。

---

