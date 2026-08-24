# Gold Benchmark 与生产质量门禁

本文的 Gold 指人工评测 ground truth，不是 Bronze / Silver / Gold 管道中的 Gold Data Layer。Gold Benchmark 未完成不否定分析就绪数据层已经构建，也不作为当前 V1 blocker；在评测完成前不得发布 Precision、Recall 或 F1。

## 当前状态

正式 Gold 数据当前为 0；历史技能 fixture 有 9 条，但规模过小、无 held-out split，保留为规则回归样例，不计入生产质量门禁。已从 Real Silver 生成三份本地待标注批次：Role 100、Skill 100、Dedup Pair 100。待标注文件包含真实 JD，因此不进入版本控制。

所有评估器分别计算 `development` 与 `held_out_test`。只有开发集允许参与规则迭代；held-out test 不得用于 taxonomy、阈值或规则调优。样本不足时，指标保持 `null`，状态输出 `INSUFFICIENT BENCHMARK DATA`。

## Role Classification

Schema：`record_id`、`title`、`description_excerpt`、`source`、`gold_role`、`annotator_notes`、`split`。

输出 accuracy、macro precision/recall/F1、逐 role precision/recall/F1/support 和以 Gold Role 为行、预测 Role 为列的 confusion matrix。当前 role taxonomy v1.2.0 覆盖 20 个显式 role 与 `other` fallback。

## Skill Extraction

Schema：`record_id`、`title`、`description`、`source`、`language`、`gold_skills`、`negative_terms`、`notes`、`split`。`gold_skills` 使用稳定 `skill_id`。

输出 micro/macro precision、recall、F1、exact match、false positives、false negatives，并单独计算 ambiguity suite（R、C、C++、Go、AI、ML、BI、CV、MD、SQL、JS、TS）的 short-alias precision。失败分析不得自动修改 taxonomy。

## Dedup Pair

Schema：`left_job_id`、`right_job_id`、`gold_duplicate`、`difficulty`、`reason`、`source_pair`、`notes`、`split`。Difficulty 为 easy、medium、hard。

输出 precision、recall、F1、False Merge Rate 与 Miss Rate。由于系统采用 precision-first，质量门禁优先检查 False Merge Rate。当前 100 对待标注样本覆盖 easy/medium/hard，但全部来自同一来源，不能替代未来跨平台 pair 标注。

## 配置化质量门禁

门禁位于 `data/reference/benchmark_quality.v1.yml`：

- Skill：Gold ≥300、held-out ≥100、micro precision ≥0.95、micro recall ≥0.90、short-alias precision ≥0.98。
- Role：Gold ≥300、held-out ≥100、每个目标 role held-out support ≥20、macro F1 ≥0.85。
- Dedup：Gold pair ≥300、held-out ≥100、precision ≥0.98、recall ≥0.75、False Merge Rate ≤0.02。

这些是建议门槛，不是当前已达成状态。只有真实 held-out 数据全部达标，才允许声明 production-ready。

## CLI

```text
python -m app.cli prepare-benchmark-batches
python -m app.cli benchmark-roles
python -m app.cli benchmark-skills
python -m app.cli benchmark-dedup
python -m app.cli benchmark-all
python -m app.cli benchmark-status
python -m app.cli benchmark-annotate
```

`benchmark-status` 只检查批次数量、未标注数、ID 唯一性/稳定性、固定 split、Prediction/Gold 分离和质量门禁缺口，不生成或修改任何 Gold Label。`benchmark-annotate` 启动本地 Annotation Workspace，支持人工确认、保存、断点续标、已有标签编辑、快捷键和显式 `ambiguous` 状态。Workspace framework 已实现不等于正式 Gold Evaluation 已完成；当前仍不得输出未经真实 held-out 数据支持的质量指标。
