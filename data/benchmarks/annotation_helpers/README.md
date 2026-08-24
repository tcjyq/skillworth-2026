# Annotation Helpers

该目录只存放 Gold Benchmark 人工标注的阅读辅助内容。`skills.jsonl`、`roles.jsonl` 和 `dedup.jsonl` 不是 Benchmark sample，也不是 Gold。

每条翻译通过 `sample_id` 对应固定样本，并保存原始标题与 JD 的 SHA-256。UI 只在 hash 一致时显示翻译；若原文改变，会拒绝使用旧 helper。

翻译的固定声明为：“辅助翻译，仅用于阅读；Gold 判断仍基于原始岗位内容。”

实际 JSONL 包含派生的完整 JD 翻译，默认不进入版本控制。
