# Gold Benchmark 人工标注工作台

## 启动

在仓库根目录、已激活项目虚拟环境的终端运行：

```text
python -m app.cli benchmark-annotate
```

默认在 `http://localhost:8501` 打开本地 Streamlit 界面。可用 `--port` 更换端口，或用 `--silver` 明确指定 Dedup 对照所需的 Silver Parquet。

## 人工确认协议

- Prediction 始终标记为“系统预测 · 仅供参考，不是 Gold”，只提供上下文，不会预填 Gold。
- Skill Gold 只能选择 `data/taxonomy/skills.yml` 中的稳定 `skill_id`；指南允许无技能时可明确保存空列表。
- Role Gold 只能选择当前 Role Taxonomy 的合法 ID。
- Dedup 保持现有布尔契约：`Same posting=true`、`Different posting=false`；不确定性单独记录为 `ambiguous`，不改变 Gold 类型。
- 每次保存都要求 annotator 和明确点击人工确认；skip 不写 Gold。
- 页面不显示 development / held-out test 身份，后台原固定 split 原样写回，绝不重新划分。

## 快捷键

| 操作 | 快捷键 |
| --- | --- |
| 保存并进入下一条 | `Ctrl/Cmd + Enter` |
| 上一条 | `Alt + ←` |
| 跳过 | `Alt + →` |
| 切换 ambiguous | `Alt + A` |
| Dedup：同一岗位 | `1` |
| Dedup：不同岗位 | `2` |

Skill taxonomy 多选和 Role selector 均支持键盘搜索、方向键与 Enter。侧栏支持跳转到任意样本，并以 `✓` 标识已完成记录。

## 持久化与恢复

人工确认后立即以临时文件加 `os.replace` 原子更新：

- `data/benchmarks/skills/gold.yml`
- `data/benchmarks/roles/gold.yml`
- `data/benchmarks/dedup/gold.yml`

当前浏览位置写入本地忽略文件 `data/benchmarks/.annotation_state.yml`。重新启动后，Continue 会恢复上次位置；没有位置时跳到第一条未完成样本。编辑已有 Gold 会替换同 ID 记录、递增 `annotation_version`，不会重复计数。

每条人工 Gold 记录包含 `annotated_at`、`updated_at`、`annotator`、`annotation_version`、`ambiguous`、`annotation_notes` 和 `human_confirmed=true`。正式 evaluator 忽略这些附加审计字段，不改变指标计算协议。

## 中文辅助阅读

- 界面默认展示已缓存的中文辅助标题和 JD，并明确标记“辅助翻译，仅用于阅读；Gold 判断仍基于原始岗位内容”。
- 每条辅助内容与 `sample_id` 及原文 SHA-256 绑定；原文变化或 ID 不匹配时拒绝读取，不会静默套用旧翻译。
- 辅助内容仅保存在 `data/benchmarks/annotation_helpers/`，不写入 benchmark sample、Prediction、Gold 或生产数据层。
- 原始英文标题和 JD 始终可通过“查看英文原文”展开；没有通过 hash 校验的辅助内容时，原文默认展开。
- Role 选择器显示中文名称和 canonical ID，保存值仍是当前 Role Taxonomy 的 canonical ID。Skill 保留 canonical 英文名，只附加中文类别说明。

## 状态与边界

```text
python -m app.cli benchmark-status
```

该命令读取当前 partial Gold，报告三类已完成数。只有当前三份固定批次全部获得人工确认后才显示 `READY FOR EVALUATION`；否则显示 `NOT READY`。这不等于生产质量门槛已经通过，也不会执行正式 Benchmark。

保存前会拒绝未知 taxonomy、非法 Role、非布尔 Dedup、缺失 annotator、孤立 Gold、重复 ID、sample/pair mismatch 和 split mismatch。
