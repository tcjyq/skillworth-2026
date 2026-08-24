# Gold Benchmark 人工标注工作流

Gold Benchmark 用于验证岗位分类、技能抽取与跨平台去重，不用于展示，也不允许由模型输出直接充当人工真值。

## 标注流程

1. 从真实 Silver 数据生成 `pending/` 待标注批次；该目录包含真实 JD 摘要，已被 `.gitignore` 排除。
2. 两名标注者独立标注；分歧由第三人仲裁。`predicted_*` 仅用于定位边界样本，不能复制为 Gold Label；正式 Gold 必须由人工确认。
3. 完成开发集后可调规则；`held_out_test` 一经封存，不得用于 taxonomy、阈值或规则调优。
4. 去除个人信息与无关联系人信息后，将仲裁结果写入对应 `gold.yml`。
5. 运行 `benchmark-all`。数据量不足时状态必须为 `INSUFFICIENT BENCHMARK DATA`。

开始标注前先运行：

```text
python -m app.cli benchmark-status
```

该命令不会写 Gold，只报告批次完整性与剩余人工标签数。当前仓库没有 Annotation UI；待标注 YAML/JSONL 具备 `annotator`、`annotation_notes` 和 `difficulty`，但不提供自动保存、断点续标、快捷键或显式 ambiguous/uncertain 状态。

`development` 固定占 30%，用于错误分析和规则迭代；`held_out_test` 固定占 70%，只用于最终、可重复的质量门禁评估。任何 taxonomy 修改都必须保留失败清单，不得根据测试集自动改写 taxonomy。若 held-out test 被用于开发，必须发布新的 benchmark version 并保留真正未触碰的 final holdout。

单批次 JSONL 生成命令：

```text
python -m app.cli prepare-annotation-batch --type skills --size 100 --seed 42 --output data/annotation_batches/skills_batch_001.jsonl
python -m app.cli prepare-annotation-batch --type roles --size 100 --seed 42 --output data/annotation_batches/roles_batch_001.jsonl
python -m app.cli prepare-annotation-batch --type dedup --size 100 --seed 42 --output data/annotation_batches/dedup_batch_001.jsonl
```

## 建议抽样

- Role：目标标题、疑似标题、明确非目标标题分层抽样，并覆盖不同公司和来源。
- Skill：按语言、技能密度、非技术文本分层，额外过采样短别名歧义。
- Dedup：同时抽取预测重复 pair 与近邻非重复 pair；Hard Case 必须覆盖城市、职级、实习/全职、事业部和相似 JD。
