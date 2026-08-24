# SkillWorth Live 多来源验证报告

生成日期：2026-08-10（Asia/Shanghai）  
快照：`20260810T041733397746Z-68a0e4f0`  
结论：**NOT READY**

> 2026-08-10 Guardrail 2.0 修订：本文第 6 节旧等权结果和第 9 节旧 Confidence 结果仅保留为历史审计证据，不再作为当前指标输出。当前 `eligible_source_count=0`，`platform_balanced_coverage=unavailable`；Confidence 使用 Market Freshness、Effective Source Diversity 与配置化 cap。现行口径见 `docs/BENCHMARK_FOUNDATION_REPORT.md`。

本结论表示当前数据仍不足以支持 Portfolio Real Mode，更不代表 Production Labor Market Decision System。第二来源提高了新鲜度和来源数量，但没有补足目标技术岗位、跨来源重叠或可比人民币薪资。

## 1. Source Selection Reason

第二来源选择 `DATA.GOV.HK — Government Vacancies`。它是公务员事务局通过 DATA.GOV.HK 发布的官方 JSON，无需认证，许可、数据字典、发布日期、职位标题、招聘部门、JD、地点和薪资字段均可审计。固定 artifact 共 70 条，SHA-256 为 `c0ff0746c485f9133866a189e5d395f9c9e2458b5482f55257659e272925fbc5`。

其明显不足是香港公营部门构成和低技术岗位相关性。准入目的仅是检验多来源管道、来源构成差异和新鲜度，不把它作为中国内地技术招聘市场的替代样本。其他候选及拒绝理由见 `docs/DATA_SOURCES.md`。

## 2. License / Data Policy

- Dataset：`https://data.gov.hk/en-data/dataset/hk-csb-csb-gov-vacancies`
- Terms：`https://data.gov.hk/en/terms-and-conditions`
- Data dictionary：`https://www.csb.gov.hk/datagovhk/gov-vacancies/gov-job-vacancies-data-dictionary-en.pdf`
- Download：`https://www.csb.gov.hk/datagovhk/gov-vacancies/gov-job-vacancies-en.json`
- 数据条款允许在署名和权属声明条件下浏览、下载、复制、分发和商业/非商业使用；系统仍保留来源链接和 artifact hash。
- 没有绕过登录、验证码、反爬、限流或访问控制。
- 申请邮箱、电话和地址未拼入分析 JD。

## 3. Data Coverage

| 指标 | Source A：Techsalerator | Source B：DATA.GOV.HK | 合并快照 |
| --- | ---: | ---: | ---: |
| 原始行 | 9,919 | 70 | 9,989 |
| Bronze / Silver 有效行 | 451 | 70 | 521 |
| Canonical jobs | 427 | 70 | 497 |
| 发布日期 | 2024-03-05–2024-09-04 | 2025-07-01–2026-07-28 | 2024-03-05–2026-07-28 |
| 非空 JD | 451 | 70 | 521 |
| Canonical skill coverage | 149/427（34.89%） | 19/70（27.14%） | 168/497（33.80%） |
| 可比人民币薪资 | 0 | 0 | 0 |

合并后的时间范围更近，但两个来源窗口不连续，不能解释为持续时间序列。Source A 的 451 条输入在 Dedup 1.1.0 下形成 427 个 canonical jobs；这与旧规则的结果不同，原因见第 5 节。

## 4. Target Market Coverage

范围来自 `target_market.v1.yml` 的标题规则，仅用于市场 scope，不是人工 Gold Role Label。

| Scope | Source A | Source B | 合并 |
| --- | ---: | ---: | ---: |
| Target | 26 / 427（6.09%） | 2 / 70（2.86%） | 28 / 497（5.63%） |
| Possible | 221 / 427（51.76%） | 39 / 70（55.71%） | 260 / 497（52.31%） |
| Non-target | 180 / 427（42.15%） | 29 / 70（41.43%） | 209 / 497（42.05%） |

Source B 的 Target 仅有 `Statistician` 和 `Part-time Subject Matter Expert (IT System)`。28 个 Target 中 21 个仍被 Role Taxonomy 归为 `other`（75%）。这同时证明来源构成仍不适配、Role Taxonomy 也缺少真实 Gold 验证；不能通过扩写规则消除 `other`。

主要 Analytics 已默认 `market_scope=target`；API 可显式传 `market_scope=all` 查看全量。

## 5. Cross-source Dedup

| 指标 | 结果 |
| --- | ---: |
| Source A postings | 451 |
| Source B postings | 70 |
| Canonical jobs | 497 |
| Cross-source overlap count | 0 |
| Cross-source duplicate groups | 0 |
| Cross-source exact matches | 0 |
| Cross-source fuzzy-title matches | 0 |
| Cross-source description matches | 0 |
| 全部来源内 Level 1 merged members | 24 |

没有 cross-source merge example 可供输出；伪造样例会误导。最相似的跨来源非合并标题包括 `Launch Manager` vs `Research Manager`（73.33）和 `Product Engineer` vs `Contract Engineer`（72.73），公司和城市均不同，正确保持分离。

实际运行发现 Source B 的两个同名 `Part-time Instructor / Leader / Camp Counsellor` 岗位 JD 和职责不同，旧 Level 1 会误合并。Dedup 1.1.0 已增加同来源不同 native ID 的 JD 95% 相似保护；重跑后 Source B 保留 70 个 canonical jobs。代价是 Source A 的 dedup recall 下降。Gold Dedup Pair 仍为 0，当前 evaluator 返回 `INSUFFICIENT BENCHMARK DATA`，因此不能给出可靠 false merge rate。

## 6. Platform-balanced Demand

Target Scope：28 canonical jobs；Source A 平台分母 27 个 source postings，Source B 分母 2。Source A 存在一个 Target canonical group 含两个 postings，因此平台分母与 canonical 分母不同。

| Skill | Source A Coverage | Source B Coverage | Pooled Coverage | Platform-balanced | Variance | Agreement |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| C++ | 11.11% | 0% | 10.71% | 5.56% | 0.003086 | Medium |
| Python | 11.11% | 0% | 10.71% | 5.56% | 0.003086 | Medium |
| C | 7.41% | 0% | 7.14% | 3.70% | 0.001372 | High |
| Excel | 7.41% | 0% | 7.14% | 3.70% | 0.001372 | High |
| MATLAB | 7.41% | 0% | 7.14% | 3.70% | 0.001372 | High |
| PowerPoint | 7.41% | 0% | 7.14% | 3.70% | 0.001372 | High |

Source B 的两个 Target JD 没有命中当前 taxonomy 技能，因此所有非零技能仍来自 Source A。Platform balancing 将覆盖率约减半，但非零技能的排名变化均为 0。这里的“High/Medium Agreement”只描述覆盖率方差；Source B 样本量 2 极小，不能据此声称跨平台验证成功。

## 7. Observed Source Composition Difference

Target Scope 下使用 base-2 Jensen-Shannon divergence：

| Dimension | JSD | 观察 |
| --- | ---: | --- |
| Role | 0.1498 | Source B 两条均为 `other`；Source A 含少量 BA、DA、PM、Security。 |
| City | 1.0000 | Source B 全部为 `CN-HK`，Source A Target 主要为广州、上海及缺失城市。 |
| Experience | 1.0000 | Source A 全部缺结构化年限；Source B Target 为 no_requirement / expert。 |
| Skill | 1.0000 | Source B Target 没有 taxonomy skill 命中。 |

公司构成同样明显分离：Source A 主要为 ZF/Bosch 汽车工业企业，Source B 为香港政府部门。以上只能称为 **Observed Source Composition Difference**，不是平台导致岗位结构差异的因果证据。

## 8. Salary Coverage

| 口径 | Source A | Source B | 合并 |
| --- | ---: | ---: | ---: |
| salary_raw 非空 | 0/451 | 70/70（100%） | 70/521（13.44%） |
| 原生结构化月薪下限 | 0/451 | 60/70（85.71%） | 60/521（11.52%） |
| 可比 CNY monthly | 0 | 0 | 0 |
| Salary parser / model coverage | 0% | 0% | 0% |

Source B 原始薪资为 HKD。Pipeline 保留 `salary_raw`、`salary_currency=HKD` 与 `salary_native_min_monthly/hourly/daily`，但不做隐式换汇，因此 Role、City、Source 层级的可比人民币薪资覆盖均为 0，Adjusted Salary Association 为 `unavailable`。没有 cross-source duplicate group，因此也没有跨来源 canonical salary conflict；原始 observation 未被覆盖。

## 9. Confidence Before / After

对 Target Skill Demand 使用现有透明 Confidence Engine。以 C++ / Python 为例：

| 状态 | Sample size | Effective sources | Cross-source agreement | Score | Level |
| --- | ---: | ---: | --- | ---: | --- |
| Before Source 2 | 26 | 1.000 | unavailable | 48.12 | Low |
| After Source 2 | 28 | 1.147 | 77.78 component score | 63.12 | Medium |

分数上涨来自来源数从 1 到 2、样本量增加 2 和一致性分量变为可计算。它不等于证据已经充分：Source B 的 Target n=2 且没有 skill 命中，质量门禁仍应覆盖 `sample_size_below_threshold`。若使用发布日期而非导入观测时间衡量市场新鲜度，Source B 明显更新；当前 Confidence Engine 的 freshness 定义仍是 `latest_observation_date`，本报告不擅自替换公式。

## 10. Market Metrics Rebuild

| 模块 | 结果 |
| --- | --- |
| Skill Demand | 已重建；默认 Target n=28。 |
| Platform-balanced Demand | 已重建；见第 6 节。 |
| Role Intelligence | 已重建，但 28 个 Target 中 21 个 role=`other`。 |
| Trend | `unavailable`：2024-03–09 与 2026-07 之间存在 21 个月空档，且来源构成切换。 |
| Adjusted Salary Association | `unavailable`：可比 CNY salary n=0。 |
| Market Value | `unavailable`：Salary Association 与可比较 Trend 缺失，不制造分数。 |
| Skill Network | 已重建：10 nodes、0 retained edges；低支持过滤后不展示伪网络。 |

## 11. Regression / Quality Gates

- 完整 Pipeline 已实际执行：Raw artifact snapshot → Bronze → Silver → Skill Extraction → Dedup → Gold → DuckDB Warehouse → Analytics → Skill Network。
- Demo 重新通过同一 Pipeline 0.3.0 构建到 `data/modes/demo/current`；旧 Demo 文件未删除。
- 最新 `demo_vs_real.json` 的全部方法指纹一致，`business_logic_consistent=true`。
- Real API smoke test：默认 Target Scope 返回 HTTP 200、sample size 28；显式 `market_scope=all` 返回 HTTP 200、sample size 497。
- Backend：`pytest` 185 passed；仅有 1 条 Starlette TestClient 弃用警告。
- Frontend：ESLint、TypeScript typecheck、Vitest（6 tests）、production build 全部通过。
- Playwright：复用已运行的本地 Next.js 服务执行，22 tests passed；未修改前端视觉。
- Role Gold labels：0；Skill Gold labels：0；Dedup Gold pairs：0。
- 三个 Benchmark 均为 `INSUFFICIENT BENCHMARK DATA`，不得声称 production-ready。
- 多来源 fixture 覆盖 connector mapping、Target Scope 默认值、platform-balanced denominator、source disagreement/JSD、same-source false-merge protection、salary currency preservation 和 canonical provenance。

## 12. Remaining Limitations

1. 只有 28 个明确 Target jobs，Source B 仅贡献 2 个。
2. 无 cross-source overlap，无法用真实重叠岗位验证 Dedup 或 canonical salary merge。
3. 可比人民币薪资为 0，薪资相关指标全部不可用。
4. Role、Skill、Dedup held-out Gold 数据均为 0。
5. Source A 高度集中于两个汽车企业域名；Source B 高度集中于香港公营部门。
6. 时间窗口不连续，趋势不可解释。
7. 当前 Confidence 的观测新鲜度不等于职位发布日期新鲜度；分数上涨不能掩盖 source-level n=2。

## 13. Final Decision

**NOT READY**

当前快照适合继续做工程验证和人工标注，不足以支持 SkillWorth Portfolio Real Mode。下一步不是增加第三个低相关来源，而是先完成真实 Gold 标注，并寻找许可明确、近期、以中国数字化/技术岗位为主、含人民币薪资且能与现有来源产生合理重叠的公开或授权来源。
