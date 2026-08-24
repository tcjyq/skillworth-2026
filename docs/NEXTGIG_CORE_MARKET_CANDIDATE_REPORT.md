# NextGig June 2026 Core Market Candidate Report

报告日期：2026-08-10（Asia/Shanghai）  
结论：**Gate FAIL — 保持 `core_market_candidate`，不运行全量导入，不替换 Demo 主数据。**

## 1. 来源与许可

NextGig 数据集采用 CC BY 4.0；固定 revision 为 `fc9787e07b2a9b5f11a470c503c36e854abd6378`。完整 Parquet 112,816 行，SHA-256 为 `b80c4d541eec3649c5b8d0143a11ddbc9a60691e1c27f6d574b501d4c9ff3f14`。Preflight 样本固定为 seed `202606`、无放回 5,000 行并按原始 row index 排序，样本 SHA-256 为 `20d40c5e721e8459d156c7f9ae1b5b53829dbff154e5e6d89b53e13f8d3226d5`。

## 2. Pipeline 运行

Run ID：`20260810T074444699227Z-1d934602`。5,000 行全部经过 Raw → append-only Bronze → Silver → Role/Salary normalization → Skill Extraction → Dedup → Gold → DuckDB；valid 5,000，canonical 5,000，当前样本未形成重复组。该结果只说明 Pipeline 可运行，不说明 dedup recall 或市场代表性。

## 3. 小样本质量

| 指标 | 结果 |
| --- | ---: |
| raw / valid / canonical jobs | 5,000 / 5,000 / 5,000 |
| target market jobs | 193 |
| target market ratio | 3.86% |
| China-derived geography jobs | 17（0.34%） |
| LLM summary coverage | 100.00%（不是原始 JD） |
| qualification requirement coverage | 79.16% |
| 可用于规则抽取的 qualification/responsibility 文本 | 83.16% |
| structured skills coverage | 71.32% |
| all-job extracted skill coverage | 15.02% |
| target-job extracted skill coverage | 83.42% |
| salary raw coverage | 47.14% |
| 原币种月频可转换覆盖 | 46.36% |
| posted_at coverage | 18.92% |
| 已解析日期中 2026 占比 | 93.87% |
| latest reliable posted_at | 2026-06-06 |

摘要覆盖率不能替代 JD coverage；上游摘要不用于原始 JD Rule Extraction。薪资可转换率也不等于人民币薪资覆盖率，后者仍为 unavailable。

## 4. 技术岗位与 Role

配置化 target scope 识别 193 条。Role normalization 明确识别 131 条，其中 software engineer 52、product manager 13、full-stack 13、data engineer 8、business analyst 7、data analyst 6、backend engineer 5、data scientist 5；其余已识别技术角色各 1–4 条。`other=4,869` 主要由全球全行业岗位构成，不能靠扩 taxonomy 将其改成技术岗。

## 5. Market Freshness 与 Trend

发布日期覆盖仅 18.92%，低于 Trend 配置门槛 70%。P75 岗位年龄 67 天，但低覆盖使该年龄统计不能代表完整样本；Trend 必须为 insufficient/unavailable。晚于固定上游 snapshot cutoff 的日期已置 null，防止虚高 freshness。

## 6. Source Gate

| Gate component | Evidence | Result |
| --- | ---: | --- |
| Target Sample Size ≥ 50 | 193 | PASS |
| Target Market Ratio ≥ 20% | 3.86% | **FAIL** |
| Skill Coverage ≥ 50%（target scope） | 83.42% | PASS |
| Market Age ≤ 180 days | 65 days | PASS，但日期覆盖低 |
| Source Role eligible | `core_market_candidate` | **FAIL** |

机器原因：`SOURCE_ROLE_NOT_CORE_MARKET_ELIGIBLE`、`TARGET_MARKET_RATIO_BELOW_MINIMUM`。此外，China-derived geography 仅 0.34%，构成比现有通用 Gate 更严格的产品适用性限制。不得降低 Gate 或只抽技术岗位后重算全源 target ratio 来规避失败。

## 7. Confidence

Target-scope evidence 的 Confidence 为 **40.79 / 100（Low）**。主要限制：eligible source 为 0、posted date coverage 18.92%、跨来源 agreement unavailable、Gold Benchmark 未达 Gate。单一全球来源增加样本量，不等于增加中国市场 source diversity。

## 8. Qarera 外部基准

Qarera overall 250 个技能中，61 个可映射到 SkillWorth taxonomy，与 NextGig target scope 内部技能交集 58 个。发布排名与内部排名 Pearson rank correlation 为 `0.523`，状态 `MEDIUM_AGREEMENT`。Python、SQL、Java、AWS 相对接近；Azure、Google Cloud、React、AI 等存在显著 rank divergence。差异只表示 collection frame/denominator 不同，不作为调整内部排名的依据。

## 9. 是否值得扩大采集

当前**不值得为 SkillWorth 中国核心市场运行 NextGig 全量导入**。原因不是工程性能，而是目标市场比例与中国覆盖明显不匹配，且日期稀疏、摘要/地理为派生字段、缺少原始职位 URL 与 source job id。它可以保留为全球工程验证或补充候选，但升级角色需新的中国市场证据和显式评审。

## 10. Demo 替换判断

不能将 Demo 主数据替换为 NextGig。Demo Mode 必须继续独立运行。当前来源最适合保留为受限的 `core_market_candidate`/engineering validation snapshot；中国市场 Real Mode 仍需许可明确、近期、JD/发布日期完整、目标技术岗比例足够的来源。
