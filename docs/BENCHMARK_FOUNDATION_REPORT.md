# SkillWorth Live Metric Guardrails & Gold Benchmark Foundation

生成日期：2026-08-10（Asia/Shanghai）  
最终状态：**BENCHMARK NOT LABELED**

框架、门禁和首批待标注数据已经建立，但 Skill、Role、Dedup 人工 Gold Label 均为 0。不能把工程完成描述为 Benchmark Ready。

## 1. 旧 Platform-balanced Demand 为什么失真

旧实现直接等权平均所有有岗位来源。DATA.GOV.HK Target n=2、技能命中为 0，导致 Source A Python 约 11.11% 与 Source B 0% 被平均为约 5.56%。算术没有错误，但 Source B 不具备可比较样本量，也不是 SkillWorth 核心目标市场来源，因此结果缺少市场解释资格。

Guardrail 2.0 下，当前来源的 `eligible_source_count=0`，`platform_balanced_coverage=null`。Pooled Coverage 仍可作为描述性结果返回，但不能冒充跨平台均衡验证。

## 2. Source Eligibility Gate

配置：`data/reference/metric_guardrails.v1.yml`。

| 门禁 | 默认值 |
| --- | ---: |
| minimum_target_sample_size | 50 |
| minimum_target_market_ratio | 20% |
| minimum_skill_extraction_coverage | 50% |
| maximum_market_age_days | 180 |
| minimum_agreement_sample_size | 30 |
| required_eligible_sources | 2 |

当前 Real 结果：

- Techsalerator：`core_market`，Target posting 27；因目标样本量、目标比例、技能覆盖和市场年龄未过门禁而 ineligible。
- DATA.GOV.HK：`engineering_validation`，Target posting 2；因 Source Role、样本量、目标比例和技能覆盖未过门禁而 ineligible。

DATA.GOV.HK 被保留用于 Data Quality、Connector、币种保留和来源构成验证，不进入默认核心 Market Metric。

## 3. Effective Source Diversity

系统同时返回 `raw_source_count`、`eligible_source_count` 和 `effective_source_count`。有效来源数只对 eligible 来源按样本权重计算 `1 / Σ(wᵢ²)`；不合格来源贡献为 0。Target n=2 不再被当作完整第二来源。

## 4. Market Freshness vs Pipeline Freshness

当前 Real 快照：

| 口径 | 结果 |
| --- | --- |
| latest_observed_at | 2026-08-10 |
| pipeline_age_days | 0 |
| latest_posted_at | 2026-07-28 |
| median_posting_age_days | 795 |
| p75_posting_age_days | 836 |
| posting_date_coverage | 100% |

数据是当天导入，但大多数岗位很旧。Confidence 2.0 使用 Market Freshness，不再把 pipeline freshness 当作市场新鲜度。

## 5. Confidence Engine 2.0

新分量为 sample strength、effective source diversity、market freshness、cross-source agreement 和 metric-specific coverage。Agreement 只有在至少两个 eligible 来源且每个达到最小样本时可用，否则返回 `INSUFFICIENT_COMPARABLE_SOURCES`。

Confidence 增加配置化 cap：缺少达标 Gold Benchmark、eligible source 不足或样本量极低时，分数不能突破对应上限。Confidence 只表示数据对分析结论的证据强度，不表示代码质量或技能本身可信度。

## 6. Benchmark Schema

- Skill：包含语言、Gold skills、negative terms、difficulty、split、annotator 和 ambiguity suite。
- Role：包含标题、JD 摘要、Gold role、difficulty、split 和标注说明。
- Dedup：包含稳定 pair ID、左右岗位、Gold duplicate、difficulty、source pair、reason 和 split。
- Metadata：benchmark/taxonomy/dedup/role taxonomy 版本、创建时间、标签数和 split seed。

Development 占 30%，held-out test 占 70%。Test failure 不得直接用于调参后继续声称 untouched test。

## 7. Annotation Sampling

CLI：

```text
python -m app.cli prepare-annotation-batch --type skills --size 100 --seed 42 --output data/annotation_batches/skills_batch_001.jsonl
python -m app.cli prepare-annotation-batch --type roles --size 100 --seed 42 --output data/annotation_batches/roles_batch_001.jsonl
python -m app.cli prepare-annotation-batch --type dedup --size 100 --seed 42 --output data/annotation_batches/dedup_batch_001.jsonl
```

首批结果：

| 批次 | 数量 | 重点覆盖 |
| --- | ---: | --- |
| Skill | 100 | 两来源；短别名歧义、技术密集/稀疏文本；36 HK、64 Techsalerator。 |
| Role | 100 | Target/Possible/Non-target；8 HK、92 Techsalerator；93 条预测为困难边界。 |
| Dedup | 100 pairs | easy/medium/hard；33 个跨来源 hard-negative candidate。 |

所有 `gold_*` 均为 null，邮箱已脱敏；prediction 只供人工参考。

## 8. 当前人工 Gold Label 数量

| Benchmark | Gold labels |
| --- | ---: |
| Skill | 0 |
| Role | 0 |
| Dedup pairs | 0 |

四个 Benchmark CLI 均返回 `INSUFFICIENT BENCHMARK DATA`，precision/recall/F1 保持 null。

## 9. Portfolio Quality Gate 状态

Skill Gate 要求总样本、hard 样本、negative 样本、held-out 样本、precision、recall 和 short-alias precision；Role Gate 要求总量、重要角色支持度与 macro F1；Dedup Gate 要求总 pair、hard pair、precision、recall 与最大 false merge rate。当前三套均未通过最低样本门槛，`portfolio_ready=false`。

## 10. 下一阶段人工工作

1. 两名标注者独立完成三份 JSONL；Gold 字段不能复制 prediction。
2. 仲裁分歧并记录 annotator / annotation notes。
3. 优先检查短别名、Role=`other` 的目标岗位和跨来源 hard negatives。
4. 将确认标签写入 Gold v2，不改变固定 split。
5. 运行 `benchmark-all`；只在 held-out gate 达标后讨论 Portfolio readiness。

## 11. 是否允许寻找第三真实来源

**当前不允许。** 先完成首批人工标注并得到真实 failure analysis。没有 Gold 证据时继续增加来源只会扩大未知误差，无法证明指标更可靠。

## 12. Regression Verification

- `pytest`：190 passed；1 条既有 Starlette TestClient 弃用警告。
- ESLint：通过。
- TypeScript typecheck：通过。
- Vitest：6 passed。
- Playwright：22 passed（desktop + mobile，复用本地服务）。
- Next.js production build：通过，12 个静态页面生成成功。
- Real API：Core Target sample=26；eligible sources=0；两来源均明确列为 ineligible；全部 Platform-balanced coverage 为 null。
- Real `source-status` 可读取 multi-source current pointer，并显示 DATA.GOV.HK 为 `engineering_validation`。
- Demo/Real methodology fingerprint：`phase6_market_basics_v2`，`business_logic_consistent=true`。
- 未接入第三来源，未修改前端视觉。

## 13. Final Status

**BENCHMARK NOT LABELED**
