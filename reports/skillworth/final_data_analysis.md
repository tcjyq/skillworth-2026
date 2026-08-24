# SkillWorth V1 Final Data Analysis

> 状态说明：本报告冻结 v6 数据分析与 Final 5。文末 publication gate 记录的是当时的分析交接节点；此后 Production Homepage Candidate 已在 `/lab/visual-v2` 实现，但尚未提升到正式 `/`。本说明不改变任何冻结分析结果。

> 分析日期：2026-08-21（Asia/Shanghai）  
> 固定快照：`freehire_china_tech_2026_08`，采集日期 2026-08-10  
> 默认口径：`180d`；辅助对照：`90d` / `365d` / `all_active`  
> 范围：Freehire 当前可观察的中国技术岗位补充样本，不代表完整中国招聘市场。

本报告只使用当前固定 snapshot、DuckDB warehouse、现有 API visual-ready 字段和全量快照技能图。本轮仅对已识别的 8 个 canonical merge groups 应用逐对审计决定并重建下游产物；没有修改 UI、taxonomy、SkillWorth 公式或通用模糊匹配算法，没有新增数据源，也没有使用 Salary 或 Trend。

## A. Data Integrity Summary

### A1. 固定数据范围

| 项目 | Exact number | 解释 |
| --- | ---: | --- |
| API raw rows | 1,236 | 15 个技术类别查询返回的原始行数 |
| API schema invalid | 1 | 采集阶段拒绝 |
| duplicate public slugs | 93 | 类别交叉带来的重复 slug |
| unique valid / Silver jobs | 1,142 | Pipeline 行数一致，invalid rate = 0 |
| Gold canonical jobs | 1,140 | 审计后保留 2 个合并组，6 个误合并组已拆分；相对 1,142 Silver rows 的 dedup rate = 0.1751% |
| Companies | 339 | all-active |
| Published date coverage | 100% | 有限时间窗可以定义分母 |
| City coverage | 900 / 1,140 = 78.95% | Gold `jobs.city_code` |
| Role=`other` | 594 / 1,140 = 52.11% | 角色口径仍然粗糙 |
| Jobs with ≥1 extracted skill | 818 / 1,140 = 71.75% | 138 个观测技能，4,053 个去重 job-skill 关系 |
| Salary usable | 0 / 1,140 | `salary_signal_status=unavailable` |
| Education usable | 0 / 1,140 | 不用于本轮故事 |
| Independent market sources | 1 | 38 个 upstream ATS label 不是 38 个独立数据源 |

180d 主切片含 998 个 canonical jobs、313 家公司、134 个观测技能；732 / 998 = 73.35% 岗位至少抽取到一项 taxonomy 技能，523 / 998 = 52.40% 岗位的 `role_id=other`。所有发现都是该切片的描述性结果。

### A2. 30-job Manual Sanity Audit

使用 `published_at >= 2026-02-11` 的 180d 切片，按 canonical ID 哈希确定性抽样，每组 5 条：AI/ML、Data、Backend、Frontend、Cloud/DevOps、Other，共 30 条。人工阅读标题、JD 片段、`role_id`、抽取技能和去重状态。这是 sanity check，不是 Gold，不计算 Precision / Recall / F1。

- Role normalization：29 / 30 未见明显错误；1 条明显可疑——`Principal, Data Analytics & Business Intelligence` 被归为 `other`。该比例不能外推，因为这是分层 sanity sample，不是随机评测集。
- Skill extraction：23 / 30 没有看到明显问题；5 / 30 存在宽泛词或公司介绍/职位背景中的 `AI` / `Optimization` 被计为岗位技能的风险；2 / 30 由于源 JD 只有招聘流程文本或现有 taxonomy 不覆盖硬件技能，没有抽取到技能。这只是明显错误筛查，不是质量分数。
- Obvious dedup：30 条样本中命中 1 个合并组（Amazon Data Engineer / Data Engineer II）；该组经逐条 provenance 审计确认是误合并并已拆分。sanity audit 本身不扩展为全库 dedup 评测。

### A3. 8-group canonical merge evidence audit

审计规则是：只有“明确不同 upstream requisition 且岗位层级或 variant 明显不同”才拆分；不同 requisition 本身不足以触发拆分。最终 6 组拆分、2 组保持合并。`canonical id` 同时列出修复前组 ID 与修复后记录归属；URL 是 Silver provenance，不是新增数据源。

| canonical id（before → after） | source / upstream requisition | title | company | location | published_at | source URL / provenance | same / different 证据与决定 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `job_0a26179bbbb0530d07b09aa0` → `job_0a26179bbbb0530d07b09aa0` | freehire / Workday `WD220973` | Operative Product Manager-2 | Flextronics International | Shenzhen / CN-SZ | 2026-05-14 | [Workday WD220973](https://flextronics.wd1.myworkdayjobs.com/Careers/job/China-Shenzhen/Operative-Product-Manager-2_WD220973?utm_source=freehire.me) | **different**：独立 requisition，且标题明确为 variant 2。 |
| `job_0a26179bbbb0530d07b09aa0` → `job_80f1607a1a521f4ec6bcd8cc` | freehire / Workday `WD220974` | Operative Product Manager-1 | Flextronics International | Shenzhen / CN-SZ | 2026-05-14 | [Workday WD220974](https://flextronics.wd1.myworkdayjobs.com/Careers/job/China-Shenzhen/Operative-Product-Manager-1_WD220974?utm_source=freehire.me) | **different**：独立 requisition，且标题明确为 variant 1；拆分。 |
| `job_11cbf40ef4b6c1650d6966f5` → `job_11cbf40ef4b6c1650d6966f5` | freehire / Echojobs→Amazon `10491143` | Technical Program Manager, Hardware Development | Amazon | Shanghai / CN-SH | 2026-08-09 | [Amazon 10491143](https://amazon.jobs/en/jobs/10491143/technical-program-manager-hardware-development/) | **same**：标题完全相同、职责近乎相同，未观察到层级或岗位 variant。 |
| `job_11cbf40ef4b6c1650d6966f5` → `job_11cbf40ef4b6c1650d6966f5` | freehire / Echojobs→Amazon `10491940` | Technical Program Manager, Hardware Development | Amazon | Shanghai / CN-SH | 2026-08-09 | [Amazon 10491940](https://amazon.jobs/en/jobs/10491940/technical-program-manager-hardware-development/) | **same**：虽 requisition 不同，但证据不足以仅凭 ID 拆分；保守保持合并。 |
| `job_12a438065e8b95c48247af13` → `job_12a438065e8b95c48247af13` | freehire / Workday `JOBREQ-2616113` | Staff/Senior ML Engineer, ML Infrastructure – Online | Unity | Shanghai / CN-SH | 2026-07-09 | [Workday JOBREQ-2616113](https://unitytech.wd1.myworkdayjobs.com/Unity/job/Shanghai-China/Staff-Machine-Learning-Engineer_JOBREQ-2616113?utm_source=freehire.me) | **different**：独立 requisition，明确 Online variant。 |
| `job_12a438065e8b95c48247af13` → `job_8c1e8b6120441a8c6348d7d0` | freehire / Workday `JOBREQ-2616270` | Staff/Senior ML Engineer, ML Infrastructure – Offline | Unity | Shanghai / CN-SH | 2026-07-22 | [Workday JOBREQ-2616270](https://unitytech.wd1.myworkdayjobs.com/Unity/job/Shanghai-China/Staff--Senior-Machine-Learning-Engineer--ML-Infrastructure--Offline_JOBREQ-2616270?utm_source=freehire.me) | **different**：独立 requisition，明确 Offline variant；拆分。 |
| `job_531f66a95849549c624d1d41` → `job_531f66a95849549c624d1d41` | freehire / Echojobs→Workday `26WD100098-1` | Product Manager, Revit Architecture | Autodesk | Shanghai / CN-SH | 2026-08-09 | [Autodesk Echojobs provenance](https://autodesk.wd1.myworkdayjobs.com/en-US/Ext/job/Product-Manager--Revit-Architecture_26WD100098-1?utm_source=freehire.me) | **same**：两条 provenance 指向相同 Autodesk requisition `26WD100098-1`。 |
| `job_531f66a95849549c624d1d41` → `job_531f66a95849549c624d1d41` | freehire / Workday `26WD100098-1` | Product Manager, Revit Architecture | Autodesk | Shanghai / CN-SH | 2026-08-05 | [Autodesk Workday provenance](https://autodesk.wd1.myworkdayjobs.com/Ext/job/Shanghai-CHN/Product-Manager--Revit-Architecture_26WD100098-1?utm_source=freehire.me) | **same**：强真重复；保持合并。 |
| `job_5d9004e7a4447ff688c24fd9` → `job_5d9004e7a4447ff688c24fd9` | freehire / Amazon `10490462` | Data Engineer, AOP – RoW Central Data Engineer Team | Amazon | Beijing / CN-BJ | 2026-08-03 | [Amazon 10490462](https://www.amazon.jobs/en/jobs/10490462/data-engineer-aop-row-central-data-engineer-team) | **different**：独立 requisition，标题为 Data Engineer。 |
| `job_5d9004e7a4447ff688c24fd9` → `job_3759c2dcf9f0c9f683d50bfb` | freehire / Amazon `10489942` | Data Engineer II, AOP – RoW Central Data Engineer Team | Amazon | Beijing / CN-BJ | 2026-08-03 | [Amazon 10489942](https://www.amazon.jobs/en/jobs/10489942/data-engineer-ii-aop-row-central-data-engineer-team) | **different**：独立 requisition，明确 II 级；拆分。 |
| `job_8f08a78e28c8845b81a5ff17` → `job_8f08a78e28c8845b81a5ff17` | freehire / Workday `R0072308` | Business Analyst | TSYS | Xi’an / city_code unavailable | 2026-08-06 | [Workday R0072308](https://tsys.wd1.myworkdayjobs.com/TSYS/job/XIAN-SHAANXI-CHINA/Business-Analyst_R0072308?utm_source=freehire.me) | **different**：独立 requisition，无 II 层级标记。 |
| `job_8f08a78e28c8845b81a5ff17` → `job_f7ea87c12c834726eb1e6a49` | freehire / Workday `R0070999` | Business Analyst II | TSYS | Xi’an / city_code unavailable | 2026-06-24 | [Workday R0070999](https://tsys.wd1.myworkdayjobs.com/TSYS/job/XIAN-SHAANXI-CHINA/Business-Analyst-II_R0070999?utm_source=freehire.me) | **different**：独立 requisition，明确 II 级；拆分。 |
| `job_b2f5412220bea3c3bda9afe9` → `job_b2f5412220bea3c3bda9afe9` | freehire / Workday `JR116004` | Sr. Embedded Software Engineer-2 | Copeland | Xi’an / city_code unavailable | 2026-06-29 | [Workday JR116004](https://copeland.wd5.myworkdayjobs.com/Copeland_External_Careers_Page/job/Xian-China/Sr-Embedded-Software-Engineer-2_JR116004?utm_source=freehire.me) | **different**：独立 requisition，明确 variant 2。 |
| `job_b2f5412220bea3c3bda9afe9` → `job_6730418b072ccf165d7cae09` | freehire / Workday `JR116005` | Sr. Embedded Software Engineer-1 | Copeland | Xi’an / city_code unavailable | 2026-06-29 | [Workday JR116005](https://copeland.wd5.myworkdayjobs.com/Copeland_External_Careers_Page/job/Xian-China/Sr-Embedded-Software-Engineer-1_JR116005?utm_source=freehire.me) | **different**：独立 requisition，明确 variant 1；拆分。 |
| `job_dc7a2ddffd65a96f2ba485df` → `job_dc7a2ddffd65a96f2ba485df` | freehire / Workday `R101037` | Senior Data Scientist I | RELX | Shanghai / CN-SH | 2025-09-12 | [Workday R101037](https://relx.wd3.myworkdayjobs.com/LexisNexisLegal/job/Shanghai/Senior-Data-Scientist-I_R101037?utm_source=freehire.me) | **different**：独立 requisition，明确 I 级。 |
| `job_dc7a2ddffd65a96f2ba485df` → `job_8171364505b24f525be5335b` | freehire / Workday `R112695-1` | Senior Data Scientist II | RELX | Shanghai / CN-SH | 2026-06-23 | [Workday R112695-1](https://relx.wd3.myworkdayjobs.com/LexisNexisLegal/job/Shanghai/Senior-Data-Scientist-II_R112695-1?utm_source=freehire.me) | **different**：独立 requisition，明确 II 级；拆分。 |

### A4. 修复前后重建对比

| 指标 | 修复前 v4 | 修复后 v6 | 变化 |
| --- | ---: | ---: | ---: |
| Gold canonical jobs | 1,134 | 1,140 | +6 |
| 180d canonical jobs | 992 | 998 | +6 |
| all-active / 180d observed skills | 138 / 134 | 138 / 134 | 不变 |
| 去重 canonical job-skill pairs | 4,023 | 4,053 | +30 |
| Jobs with ≥1 skill（all / 180d） | 812 / 726 | 818 / 732 | +6 / +6 |
| 180d main skills with rank change | — | 26 / 110 | 最大绝对变动 4 位 |
| 180d Market Signal 最大绝对变化 | — | 0.75 | scikit-learn |
| 180d SkillWorth 最大绝对变化 | — | 0.44 | scikit-learn |

分组 partition 核验：v4 的 8 个二元合并组中，仅上述 6 组消失；Amazon TPM 与 Autodesk 两组保持原 canonical membership，未产生新的合并组。受影响 Gold、warehouse、全量技能图、summary 与 visual-ready analysis 均已从固定 v4 Silver/skills 输入重建。

| Final-5 相关全局技能（180d） | 修复前：jobs / Signal / SkillWorth / rank | 修复后：jobs / Signal / SkillWorth / rank |
| --- | ---: | ---: |
| Python | 319 / 48.07 / 24.03 / 1 | 321 / 48.05 / 24.03 / 1 |
| SQL | 168 / 36.41 / 22.40 / 2 | 169 / 36.32 / 22.35 / 2 |
| Git | 39 / 21.52 / 16.02 / 3 | 40 / 21.68 / 16.13 / 3 |
| Docker | 53 / 25.38 / 15.62 / 4 | 53 / 25.36 / 15.61 / 4 |
| C++ | 92 / 24.79 / 9.44 / 34 | 92 / 24.76 / 9.43 / 35 |
| Kubernetes | 70 / 26.16 / 11.01 / 17 | 70 / 26.13 / 11.00 / 18 |
| Terraform | 25 / 17.59 / 9.70 / 32 | 25 / 17.58 / 9.70 / 33 |
| Apache Spark | 63 / 23.73 / 10.85 / 18 | 63 / 23.69 / 10.83 / 19 |
| Apache Kafka | 27 / 20.03 / 10.34 / 22 | 27 / 20.02 / 10.33 / 23 |
| Tableau | 43 / 19.70 / 12.12 / 7 | 44 / 19.81 / 12.19 / 7 |
| RAG | 49 / 22.61 / 12.06 / 8 | 50 / 22.76 / 12.14 / 8 |

**Substantive-change verdict**：Final 5 的选择、方向和核心故事均未发生 substantive change；需要实质更新的是所有公开 exact numbers。C++ 由第 34 调整为第 35，Data Engineer 中 Kafka 因 AWS 上升而由角色第 4 调整为第 5，但“需求与技值背离”和“角色特定排名反转”仍成立。

### A5. Integrity verdict

数据足以支持一个带明确边界的可复现交互分析作品，但不足以支持“完整中国市场”、Trend、Salary 或高精度细分角色结论。最稳妥的故事应依赖大样本、稳健主榜、相对比较和全量技能图；避免把宽泛主题、小角色切片和长尾敏感排名当成强结论。

## B. 13 Candidate Findings

### F1. 可发布的效率前沿只有 Python、SQL 和 Git

1. **一句话结论**：在通过 candidate gate 且 Ranking Robustness=`robust` 的技能中，Python、SQL、Git 构成“Market Signal 更高、学习时长更低”的 Pareto frontier。
2. **Exact numbers**：Python = 48.05 signal / 160h / SkillWorth 24.03 / rank 1；SQL = 36.32 / 100h / 22.35 / rank 2；Git = 21.68 / 55h / 16.13 / rank 3。
3. **Comparison baseline**：180d 内所有 `main + high_skillworth_candidate + robust` 技能；其他技能均被这三者之一在 signal/hours 上严格支配。
4. **Source fields**：`china_skillworth_visual_ready.market_signal`, `learning_hours_expected`, `skillworth_score`, `skillworth_rank`, `high_skillworth_candidate`, `robustness_level`。
5. **Sample/window**：998 jobs，313 companies，180d，全角色。
6. **Confidence / robustness**：三者 robustness 85.29 / 83.47 / 83.97，敏感性排名范围 1–2 / 1–2 / 3–4；Confidence 58.60 / 56.45 / 51.32，均为 Medium。
7. **Caveat**：学习时长是 taxonomy 假设，前沿会随候选 gate 改变；如果不做质量 gate，JSON 和 HTML 也会因低时长进入数学前沿，但两者样本少且 sensitive。
8. **Homepage**：是，适合做效率前沿主视觉。
9. **README**：是，适合解释 SkillWorth 不是需求排行榜。
10. **Interesting?**：真正有趣，是方法论与数据共同产生的结论。

### F2. C++ 是最强的 Demand vs SkillWorth 背离案例

1. **一句话结论**：C++ 的需求排名第 3，但 SkillWorth 只排第 35，高需求没有自动转化成高学习投资优先级。
2. **Exact numbers**：92 jobs（9.2184%）、48 companies、5 supported roles、Market Signal 24.76、expected learning 260h、SkillWorth 9.43；demand rank 3 vs SkillWorth rank 35，差 32 位。
3. **Comparison baseline**：180d 全部 main 技能的 job coverage rank vs SkillWorth rank。
4. **Source fields**：`job_count`, `job_coverage`, `company_count`, `role_count`, `market_signal`, `learning_hours_expected`, `skillworth_score`, `skillworth_rank`。
5. **Sample/window**：998 jobs，180d，全角色。
6. **Confidence / robustness**：Confidence 51.67 Medium；robustness 55.06 Moderate；敏感性排名 18–50。
7. **Caveat**：这不是“C++ 不值得学”，而是在从零学习的 260h 假设下，其市场信号被学习投入折损；排名本身为 Moderate。
8. **Homepage**：是，是最清晰的“需求 ≠ 投资优先级”故事。
9. **README**：是。
10. **Interesting?**：真正有趣，且有反直觉性。

### F3. Git 是“低需求、高技值”的对称背离

1. **一句话结论**：Git 只覆盖 4.01% 岗位，需求排名第 18，却因 55h 预期学习投入与跨角色信号升至 SkillWorth 第 3。
2. **Exact numbers**：40 jobs，27 companies，5 supported roles，role breadth 0.1959，Market Signal 21.68，55h，SkillWorth 16.13；demand rank 18 vs SkillWorth rank 3。
3. **Comparison baseline**：180d main 技能 demand rank；对照 AWS（79 jobs，220h，SkillWorth 12.45，rank 6）。
4. **Source fields**：同 F2，另加 `role_breadth`。
5. **Sample/window**：998 jobs，180d。
6. **Confidence / robustness**：Confidence 51.32 Medium；robustness 83.97 Robust；敏感排名 3–4。
7. **Caveat**：55h 是“从零到可用于初级岗位任务”的 taxonomy 估算，不是个人课程承诺。
8. **Homepage**：是，可作为高价值低投入卡片。
9. **README**：是。
10. **Interesting?**：真正有趣，但与 F1 有部分重叠。

### F4. Power BI 的公司广度比 C++ 更分散

1. **一句话结论**：C++ 岗位更多，但 Power BI 出现在更多公司中，显示绝对岗位数和雇主广度并不等价。
2. **Exact numbers**：Power BI = 63 jobs / 49 companies，company/job=77.78%，company coverage=15.655%；C++ = 92 jobs / 48 companies，company/job=52.17%，company coverage=15.335%。
3. **Comparison baseline**：同一 180d 公司分母 313；比较岗位需求与公司广度。
4. **Source fields**：`job_count`, `company_count`, `company_coverage`, `company_sample_size`。
5. **Sample/window**：998 jobs / 313 companies，180d。
6. **Confidence / robustness**：Power BI robustness 77.88 Robust，Confidence 50.87 Medium；C++ 55.06 Moderate / 51.67 Medium。
7. **Caveat**：company/job 不是独立统计指标，只是直观对照；公司名标准化并未做激进实体合并。
8. **Homepage**：候选，适合作为公司广度解释，不适合单独当 Hero。
9. **README**：是。
10. **Interesting?**：有趣，不只是排行榜复述。

### F5. Python 和 SQL 是真正的 Generalist，Transformers 是当前口径下的 Specialist

1. **一句话结论**：Python/SQL 的优势不只来自岗位数，还来自稳定跨角色覆盖；Transformers 有 29 个岗位，但没有任一角色达到 3 条支持后进入 breadth 计算。
2. **Exact numbers**：Python = 12 supported roles / breadth 0.5111 / 321 jobs；SQL = 10 / 0.3415 / 169；Transformers = 0 / 0 / 29，SkillWorth rank 67。
3. **Comparison baseline**：180d 主榜技能的 `role_count` 与 inverse-HHI `role_breadth`。
4. **Source fields**：`role_count`, `role_breadth`, `job_count`, `skillworth_rank`。
5. **Sample/window**：998 jobs，180d；role breadth 排除 `other` 且要求每角色至少 3 jobs。
6. **Confidence / robustness**：Python/SQL 均 Robust + Medium Confidence；Transformers Moderate，Confidence 43.81 Low。
7. **Caveat**：52.40% 的 180d 岗位被归为 `other`，所以 breadth 是已识别角色内的保守信号；“0 supported roles”不等于没有角色。
8. **Homepage**：是，但应把 role threshold 写进 tooltip。
9. **README**：是。
10. **Interesting?**：有趣，可把“通用技能”从印象变成可审计数字。

### F6. DevOps 角色发生强排名反转：Kubernetes 和 Terraform 取代全局前排

1. **一句话结论**：全局排名第 18/33 的 Kubernetes/Terraform，在 DevOps 岗位中变成第 1/3。
2. **Exact numbers**：DevOps n=21；Kubernetes 17/21=80.95%，role rank 1 vs global 18；Terraform 11/21=52.38%，role rank 3 vs global 33；Python 12/21=57.14%，role rank 2。
3. **Comparison baseline**：同一 180d 的全角色 main rank vs `role_id=devops_engineer` rank。
4. **Source fields**：`role_id`, `sample_size`, `job_count`, `job_coverage`, `skillworth_rank`。
5. **Sample/window**：21 DevOps jobs，180d。
6. **Confidence / robustness**：Kubernetes/Terraform 的角色内 robustness 均 Moderate；小切片结论强度低于全局。
7. **Caveat**：n=21，不应表述为整个中国 DevOps 市场；role normalization 未有 Gold 评测。
8. **Homepage**：是，适合用来解释“目标角色改变学习答案”。
9. **README**：是。
10. **Interesting?**：真正有趣，是产品核心问题的直接证据。

### F7. Data Engineer 的实际技术栈比全局排名更“分布式”

1. **一句话结论**：Apache Spark 和 Kafka 在全局只排第 19/23，但在 Data Engineer 中排第 3/5。
2. **Exact numbers**：Data Engineer n=38；Spark 22/38=57.89%，role rank 3 vs global 19；Kafka 12/38=31.58%，role rank 5 vs global 23；SQL 32/38=84.21% 排第 1。
3. **Comparison baseline**：180d 全角色 main rank vs Data Engineer role rank。
4. **Source fields**：同 F6。
5. **Sample/window**：38 Data Engineer jobs，180d。
6. **Confidence / robustness**：Spark/Kafka 角色内均 Moderate；SQL/Python 为 Robust。
7. **Caveat**：切片小，且部分 Data 标题被归到 `other`；不是技能因果组合。
8. **Homepage**：是，可与 F6 合并成 Role Reversal 故事。
9. **README**：是。
10. **Interesting?**：真正有趣。

### F8. Backend 的 Redis 信号远高于它的全局位置

1. **一句话结论**：Redis 全局第 14，但在 Backend 中排第 2，仅次于 SQL。
2. **Exact numbers**：Backend n=41；Redis 10/41=24.39%，9 companies，role rank 2；SQL 19/41=46.34% 排第 1；Java 17/41=41.46% 排第 3。
3. **Comparison baseline**：180d global main rank 14 vs Backend rank 2。
4. **Source fields**：同 F6。
5. **Sample/window**：41 Backend jobs，180d。
6. **Confidence / robustness**：Redis 角色内 Moderate；样本支持好于多数角色长尾技能。
7. **Caveat**：仍然只有 41 条；不能把共现解释成必备技能。
8. **Homepage**：候选，优先级低于 F6/F7 的合并故事。
9. **README**：可用作 role-filter 示例。
10. **Interesting?**：有趣，但与 Role Reversal 主故事重叠。

### F9. 技能共现有两种不同的“强”：规模强与亲和度强

1. **一句话结论**：Python–SQL 是规模最大的具体技能组合，而 NumPy–Pandas 和 Grafana–Prometheus 虽样本小，相对亲和度更强。
2. **Exact numbers**：Python–SQL = 141 co-jobs / Jaccard 0.3431 / PMI 0.8565；NumPy–Pandas = 12 / 0.6667 / 4.1255；Grafana–Prometheus = 11 / 0.5789 / 4.0385。
3. **Comparison baseline**：同一 all-active 技能图中的 absolute cooccurrence vs Jaccard/PMI。
4. **Source fields**：`skill_graph_edges.parquet.cooccurrence_count`, `jaccard`, `pmi`, `weight`, `skill_a_id`, `skill_b_id`。
5. **Sample/window**：1,140 all-active canonical jobs；现有 synergy 设计在 90/180/365d 榜单中也复用这个全量图。
6. **Confidence / robustness**：Python–SQL 支持强；后两对为中等探索性证据，胜在高 Jaccard/PMI，不是大样本。
7. **Caveat**：共现不是协同的因果证明，PMI 对小样本敏感；图为 all-active，不是 180d 独立网络。
8. **Homepage**：是，适合做“广泛搭配 vs 专业套件”交互故事。
9. **README**：是。
10. **Interesting?**：真正有趣，且不是排行榜复述。

### F10. Market Theme 不能直接当成可学习的 Concrete Skill

1. **一句话结论**：AI 主题覆盖 41.48% 岗位，但这是重叠技能的并集，其中宽泛 `AI` 词本身就覆盖 37.47%，不应与 Python 这类具体学习对象混排。
2. **Exact numbers**：AI Theme = 414/998=41.4830%，167 companies；canonical `AI` = 374/998=37.4749%；Machine Learning Theme = 228/998=22.8457%；Python = 321/998=32.1643%。
3. **Comparison baseline**：180d theme union coverage vs concrete-skill job coverage。
4. **Source fields**：`china_skillworth_market_themes.job_count/job_coverage/company_count`；`china_skillworth_visual_ready.skill`, `skillworth_eligibility`, `job_count/job_coverage`。
5. **Sample/window**：998 jobs，180d。
6. **Confidence / robustness**：Theme 是确定性并集，但语义结论可信度 Low–Moderate；374 个 `AI` 岗位中只有 116 个标题显式含独立词 AI，258 个来自非标题文本。
7. **Caveat**：人工 sanity audit 已观察到公司介绍和职位背景中的 AI 被抽取；不能把 41.43% 说成“41% 岗位要求会 AI”。
8. **Homepage**：有条件适合，只能用 Theme vs Concrete Skill 的对照表述。
9. **README**：是，适合说明语义边界。
10. **Interesting?**：有趣，但证据比其他候选弱，不建议进 Final 5。

### F11. 头部有稳健核心，但第 7 名以后很快进入模型敏感区

1. **一句话结论**：Python、SQL、Git、Docker 对权重与学习 half-value 非常稳定，而 Tableau、RAG 的当前前十位置不稳定。
2. **Exact numbers**：Python 1–2，SQL 1–2，Git 3–4，Docker 3–4；Tableau 7–25，RAG 6–29，Azure 8–27。180d main 中 Robust 12、Moderate 31、Sensitive 67。
3. **Comparison baseline**：配置的 demand-heavy / breadth-heavy / synergy-heavy 权重与 100/240h half-value 情景。
4. **Source fields**：`sensitivity_rank_min`, `sensitivity_rank_max`, `ranking_robustness`, `robustness_level`, `skillworth_rank`。
5. **Sample/window**：998 jobs，180d，110 个 main 可观测技能。
6. **Confidence / robustness**：这项发现直接来自稳健性分析，对“当前模型内是否稳定”的信心高；对外部市场真实性仍为单源 Low/Medium Confidence。
7. **Caveat**：情景集是现有配置定义的有限压力测试，不是所有可能模型的穷举。
8. **Homepage**：是，应把稳健区间而不是单一名次作为重点。
9. **README**：是。
10. **Interesting?**：真正有趣，也是防止过度叙事的关键发现。

### F12. Posting-recency 窗口下的整体排名高度稳定

1. **一句话结论**：180d 排名与 90d、365d、all-active 的 Spearman 秩相关均高于 0.989，前 6 名在四个窗口完全一致。
2. **Exact numbers**：ρ(180,90)=0.9984，ρ(180,365)=0.9972，ρ(180,all)=0.9894；四窗口 Top 6 均为 Python、SQL、Git、Docker、Power BI、AWS。样本为 864 / 998 / 1,042 / 1,140 jobs。
3. **Comparison baseline**：四个 recency window 中共同 main skill 的 SkillWorth rank。
4. **Source fields**：`recency_window`, `sample_size`, `skill_id`, `skillworth_rank`, `window_status`。
5. **Sample/window**：90d / 180d / 365d / all-active，全部 `available`。
6. **Confidence / robustness**：对当前 snapshot 内的排名窗口稳定性信心高；不是时间趋势证据。
7. **Caveat**：窗口高度重叠，且 synergy 共用 all-active 技能图，会机械地提高相似度；绝不能叙述成 trend。
8. **Homepage**：是，可作为默认 180d 的可信解释。
9. **README**：是。
10. **Interesting?**：有趣，更偏稳健性证据而非主故事。

### F13. 总体稳定不等于每项技能都稳定

1. **一句话结论**：Google Cloud 和 Linux 对窗口选择明显敏感，提示 all-active 的较旧库存会改变个别位次。
2. **Exact numbers**：Google Cloud rank = 28(90d) / 21(180d) / 22(365d) / 15(all)，span 13；Linux = 23 / 22 / 14 / 12，span 11；180d jobs 分别为 47 / 66。
3. **Comparison baseline**：四窗口 SkillWorth rank span。
4. **Source fields**：同 F12，另加 `job_count`。
5. **Sample/window**：四个 available window。
6. **Confidence / robustness**：Google Cloud / Linux 在 180d 均为 Moderate，Confidence 53.68 / 50.19。
7. **Caveat**：不能说“近期下降”或“过去更热”；这只是不同发布日期库存切片的差异，不是多期快照。
8. **Homepage**：否，容易被误读为 Trend。
9. **README**：是，适合用于说明 recency-window caveat。
10. **Interesting?**：有趣，但主要是方法论边界。

## C. Evidence Table

| Evidence ID | 数据对象 / 字段 | 分母或窗口 | 支持 Findings | 可复现说明 |
| --- | --- | --- | --- | --- |
| E1 | `china_skillworth_visual_ready`: `job_count`, `job_coverage`, `sample_size` | 90/180/365/all-active | F1–F8, F10–F13 | API 只读表，粒度 `skill × window × role` |
| E2 | 同表：`company_count`, `company_coverage`, `company_sample_size` | 180d jobs=998，companies=313 | F1, F2, F4, F10 | 公司去重计数 |
| E3 | 同表：`role_count`, `role_breadth` | 排除 `other`，每角色最小支持 3 | F5 | inverse-HHI effective-role 信号 |
| E4 | 同表：`market_signal`, `learning_hours_expected`, `skillworth_score` | 180d | F1–F4 | 现有方法论，未调整权重 |
| E5 | 同表：`sensitivity_rank_min/max`, `ranking_robustness`, `confidence` | 180d | F1–F3, F11 | 模型内敏感性与数据信心分开 |
| E6 | 同表：`role_id`, `sample_size`, `skillworth_rank` | role-specific 180d | F6–F8 | 与全局同算法的角色切片 |
| E7 | `china_skillworth_market_themes` | 180d theme union | F10 | theme mapping 允许重叠，不进入主榜 |
| E8 | `skill_graph_edges.parquet`: `cooccurrence_count`, `jaccard`, `pmi` | 1,140 all-active jobs | F9 | 全量图，不是 180d 独立图 |
| E9 | `jobs`, `job_skills`, `job_source_map`、Silver provenance | 30-job sanity + 8 个既有合并组 | A2–A4, F10 caveat | 人工 sanity 与逐组审计，不产生 Gold Benchmark |
| E10 | `silver_jobs.quality.json`, `dedup_report.json`, `current.json` | snapshot 全量 | A1–A5 | v6 重建产物与 provenance |
| E11 | `integration_manifest.v4.json` vs `integration_manifest.v6.json` | 修复前后同一固定 Silver 输入 | A4、Final 5 | 对比分母、技能计数、Signal、Score 与 rank |

核心可复现 SQL 形式：

```sql
SELECT *
FROM china_skillworth_visual_ready
WHERE recency_window = '180d' AND role_id IS NULL;

SELECT *
FROM china_skillworth_visual_ready
WHERE recency_window = '180d' AND role_id = 'devops_engineer';

SELECT *
FROM china_skillworth_market_themes
WHERE recency_window = '180d';
```

## D. Weak / Unsupported Findings

| 不应发布的说法 | 状态 | 原因 |
| --- | --- | --- |
| “RAG / AI / Linux 正在增长或下降” | Unsupported | 只有一个 snapshot；recency window 不是 trend |
| “某技能带来薪资溢价” | Unavailable | 0 条可比较人民币月薪 |
| “AI 是 41% 岗位的硬性技能要求” | Weak / misleading | Theme 是重叠并集；宽泛 AI 抽取存在背景文本污染 |
| “Frontend 市场首选 React” | Weak | frontend 180d 只有 8 条，排名全部 Sensitive |
| “Security 市场首选 Python” | Weak | security 180d 只有 11 条，排名 Sensitive |
| “Transformers 没有角色覆盖” | Misleading literalism | `role_count=0` 表示没有角色达 3 条支持，不是真的零角色 |
| “四窗口排名稳定证明市场长期稳定” | Unsupported | 窗口重叠且共用 all-active synergy |
| “该结果代表中国技术招聘市场” | Prohibited | 单一 supplementary source，非完整市场抽样 |
| “公司广度高证明技能更安全” | Unsupported causal leap | company breadth 只是当前样本的分散度 |
| “共现技能必须一起学” | Unsupported causal leap | Jaccard/PMI 是关联，不是学习前置关系 |
| “现有去重已消除所有重复或误合并” | Unsupported | 本轮只审计 8 个既有合并组；6 组已纠正、2 组保留，但未扩大为全库 dedup 评测 |

## E. Recommended Final 5 Findings

1. **Efficiency Frontier：Python → SQL → Git**（F1）  
   最能体现 SkillWorth 的作品定位：展示需求、市场广度与学习投入如何组成可审计前沿。

2. **Demand ≠ SkillWorth：C++ 从需求第 3 到技值第 35**（F2）  
   最强反直觉案例，而且数字足够大，不依赖长尾小样本。

3. **Role-specific Reversal：DevOps 的 Kubernetes/Terraform，Data Engineer 的 Spark/Kafka**（合并 F6 + F7）  
   直接回答“目标岗位改变时，下一项值得学的技术也会改变”。公开时必须同时显示 n=21 / n=38。

4. **Synergy 的两种强度：Python–SQL 的规模，NumPy–Pandas / Grafana–Prometheus 的亲和度**（F9）  
   适合交互可视化，也能展示为什么只看共现次数会丢掉专业技术栈。

5. **Robust Core：头部四项在权重和 recency 窗口下稳定，但长尾不稳定**（合并 F11 + F12）  
   同时展示可信结论和不确定性：Python/SQL 为 1–2，Git/Docker 为 3–4；180d 与其他窗口秩相关 0.989–0.998，但 RAG/Tableau 的模型排名范围分别扩到 6–29 / 7–25。

### Final-5 publication gate

修复后的 Final 5 与修复前相比没有 substantive change，但全部公开数字必须采用本报告的 v6 数字。当前 publication gate 停在这里：在获得确认前，不进入 Data Story Integration，不修改首页。
