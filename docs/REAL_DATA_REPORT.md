# SkillWorth Live Real Dataset Report

生成时间：2026-08-09（Asia/Shanghai）  
数据模式：Real  
数据集：Techsalerator — Job Posting Data in China v1  
Pipeline run：`20260809T133317784007Z-050d9a7f`

## 结果摘要

| 指标 | 真实计算结果 | 口径 |
| --- | ---: | --- |
| Raw rows | 9,919 | 下载 CSV 全部行。 |
| In-scope China rows | 451 | `Location Data[0].country == China`。 |
| Valid Silver rows | 451 | `record_status=valid`。 |
| Canonical jobs | 388 | Gold 去重后岗位。 |
| Excluded out-of-scope rows | 9,468 | 非结构化 China 范围，不进入市场分析。 |
| Date range | 2024-03-05 ～ 2024-09-04 | 可解析 `First Seen At`。 |
| Salary coverage | unavailable | 中国子集没有薪资值；0/388，不填假值。 |
| Skill coverage | 37.37% | 145/388 个规范岗位至少抽取到一个 taxonomy skill。 |
| Source count | 1 | `techsalerator_china_jobs_v1`。 |

## Role Distribution

| Role | Canonical jobs | Share |
| --- | ---: | ---: |
| `other` | 385 | 99.23% |
| `product_manager` | 2 | 0.52% |
| `data_analyst` | 1 | 0.26% |

该分布反映当前窄 Role Taxonomy 与该公开数据集的宽岗位范围，不应解释为中国技术岗位真实构成。

## City Distribution

已解析城市 233/388（60.05%）：

| City code | Canonical jobs |
| --- | ---: |
| `CN-SH` | 123 |
| `CN-GZ` | 47 |
| `CN-WH` | 25 |
| `CN-HZ` | 12 |
| `CN-CD` | 11 |
| `CN-BJ` | 9 |
| `CN-SZ-SU` | 6 |

其余 155 个规范岗位保持城市不可用；未配置城市不会被猜测。

## Source Distribution

| Source | Canonical jobs |
| --- | ---: |
| `techsalerator_china_jobs_v1` | 388 |

底层中国范围记录高度集中于两个企业官网域名：`zf.com` 406 行、`bosch.com` 45 行。只有一个数据集来源，因此 Platform-balanced Demand、Cross-platform Bias 与 Cross-source Agreement 不具备多来源证据，应显示不可用或低置信度。

## Pipeline 与质量结果

- Silver：451 行；invalid record rate 0%；salary parse rate 0%；role parse rate 0.67%；city parse rate 61.42%。
- Dedup：451 → 388；44 个 duplicate groups；去除 63 行；dedup rate 13.97%；全部为 Level 1 exact。
- Skill Extraction：Rule-first；LLM 未启用。
- Warehouse：正式 core tables 与 10 个 Analysis Views 已构建；14 项 Data Tests 通过；2 个 query benchmark 完成。
- Analytics：`phase6_market_basics_v1` 已实际执行，sample size 388；Skill Network 已生成。
- Demo/Real：Pipeline 0.2.0、Role Taxonomy 1.0.0、City Taxonomy 1.1.0、Skill Taxonomy 1.0.1、Warehouse objects 和 Analytics methodology 六项一致性检查全部通过。

Skill Taxonomy 1.0.1 移除了高歧义短别名 `CV` 与 `MD`。审计发现它们会把普通招聘文本中的简历缩写和其他缩写误识别为 Computer Vision、Markdown；修复后 Real 数据中至少有一个技能的规范岗位由 152 个降至 145 个。该变化是 false positive 修正，不是数据缺失填补或指标硬编码。

机器可读结果位于本地 `data/modes/real/reports/real_dataset_report.json` 和 `data/modes/real/reports/demo_vs_real.json`；原始数据与派生快照已被 `.gitignore` 排除。

## 使用限制

- 数据截至 2024-09-04，已明显陈旧，不能称为实时或当前市场。
- 仅两个企业官网域名，无法代表中国招聘平台或整体技术劳动力市场。
- 无薪资、学历和可靠经验年限，不支持薪资关联及相关筛选。
- 绝大部分岗位落入 `other`，不适合直接驱动面向大学生的技术学习建议。
- 该数据集目前主要用于证明 Real Dataset Pipeline、缺失值语义和 provenance 机制真实可运行；正式市场结论仍需增加许可明确、覆盖更广的新来源。
