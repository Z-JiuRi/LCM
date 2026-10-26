# AutoML 与 HPO 代码示例

> 整理日期：2026-10-25。候选设计/示例；尚未实现或验证。原章节编号保留，便于核对旧稿。
> 本页为通用 AutoML 工程参考，代码与参数是设计示例，不代表 LCMAgent 已采用的接口或依赖。

[文档导航](../../README.md) · [原稿章节对照](../../整理说明.md)

---

> 来源：`AutoML_Agentic_AutoML_Research_Report_2026-10-22_v3_AutoResearch_Ecosystem.md`；2026-10-22 V3。

<a id="s13-3"></a>

### 13.3 传统 AutoML baseline：AutoGluon（表格任务示意）

```python
# pip install autogluon.tabular
# 数据已完成许可检查，并按正确时间/组策略分离。
from autogluon.tabular import TabularPredictor

label = "target"
train_df = ...   # 仅含训练数据
valid_df = ...   # 锁定验证数据；不要放最终测试集

predictor = TabularPredictor(
    label=label,
    eval_metric="roc_auc",
    path="./artifacts/autogluon_baseline",
)

predictor.fit(
    train_data=train_df,
    tuning_data=valid_df,
    time_limit=1800,
    presets="medium_quality",
)

# 如果需要额外评分，请在与训练未重叠的指定数据集上执行。
# 某些更高质量 preset 会自动 bagging/stacking，tuning_data 解释随配置变化，
# 不要假定所有参数组合会保持该验证集完全独立。
print(predictor.leaderboard(silent=True).head())
```

**为何选择这个代码**：其参数风格与官方现行 `TabularPredictor.fit` 文档一致，较易形成 Agent 可以调用的强 baseline。对任何涉及 stacking/bagging 的配置，都要复核 `tuning_data` 与验证泄漏行为，不能在模型训练后用参与建模的同一数据评价泛化。见官方 API。[R38]

<a id="s13-4"></a>

### 13.4 传统 AutoML baseline：FLAML（受限计算环境）

```python
# pip install "flaml[automl]"
from flaml import AutoML

automl = AutoML()
automl.fit(
    X_train=X_train,
    y_train=y_train,
    task="classification",
    metric="roc_auc",
    time_budget=300,
    seed=2026,
    log_file_name="flaml_baseline.log",
)

# 不要把内部 holdout 的最佳分数误当成独立最终测试分数。
y_score = automl.predict_proba(X_valid)[:, 1]
```

`X_train` / `X_valid` 应由第 12.5 节规则生成，不可因分数不好而临时更换切分。对正例极少的数据，还应考虑 AUCPR 与业务误报/漏报代价。[R39]

<a id="s13-5"></a>

### 13.5 Optuna 结构化 HPO（以及如何补充剪枝）：例子

```python
# 仅示意结构：需要数据预处理和 XGBoost 安装依赖
import optuna
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score


def objective(trial):
    params = {
        "max_depth": trial.suggest_int("max_depth", 2, 8),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "n_estimators": trial.suggest_int("n_estimators", 100, 600),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "random_state": 2026,
        "n_jobs": 4,
        "tree_method": "hist",
    }
    model = XGBClassifier(**params)
    model.fit(X_train, y_train)
    pred = model.predict_proba(X_valid)[:, 1]
    return roc_auc_score(y_valid, pred)


study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=30, timeout=1200)
print(study.best_value, study.best_params)
```

示例虽称“带剪枝”，但上述函数未实现逐步中间汇报与 `trial.should_prune()`，因此**它实际是有边界的普通 Optuna HPO，并未启用有效 pruning**。要实现真正的剪枝，需使用框架兼容的回调或分阶段训练，在每个阶段通过 `trial.report(value, step)` 更新中间指标，再检查 `trial.should_prune()`；不要假装只创建一个 pruner 就等于完成多保真优化。此处保留这个区别，是为了强调工程报告必须区分“API 已声明”和“功能已经生效”。

<!-- 本页使用的引用定义；书目详情由对应资料索引维护。 -->
[R38]: https://auto.gluon.ai/stable/api/autogluon.tabular.TabularPredictor.fit.html "AutoGluon — TabularPredictor.fit docs"
[R39]: https://microsoft.github.io/FLAML/docs/reference/automl/automl/ "FLAML — AutoML docs"
