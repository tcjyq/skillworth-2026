# 分析方法论

## 1. 方法论原则

- 所有指标以指定的市场切片计算：岗位 taxonomy、城市、经验、学历、数据来源和时间范围必须显示在结果中。
- 默认使用 Gold 去重岗位作为“岗位数”分母；跨来源信息通过 `job_source_map` 单独分析。
- 任何结果都必须携带 `methodology_version`、`data_version`、样本量和置信度。
- 统计相关性不得表述为因果性；学习推荐表示技能匹配度和市场信号的估计，不表示录用概率或薪资承诺。
- 低样本、过期或解析质量不足的切片应显示“数据不足”，而不是生成排名。

## 2. 标准化与质量规则

### 2.1 岗位标准化

岗位标题先保留原文，再按可版本化 taxonomy 映射到规范角色，例如“数据分析师”“后端开发工程师”。规则应包含同义词、层级、排除词与人工复核状态。不能匹配时标记 `unclassified`，不得强制归类。

城市、学历、经验、公司和发布时间同样保留原始值与标准化值。时间分析只使用可解析、落在声明观察窗口内的岗位。

Phase 2 的 Silver 标准化采用以下保守规则：

- 公司和岗位标题执行 Unicode NFKC、首尾空白清理、连续空白折叠和英文小写化；不删除公司法律实体后缀，也不进行未经验证的公司合并。
- 角色与城市 taxonomy 使用 `data/reference/*.json` 配置并携带版本。不能匹配的角色进入 `other`，不能匹配的城市保存空值和 `unparseable`。
- 学历标准化为 `no_requirement`、`high_school`、`associate`、`bachelor`、`master`、`doctorate`；无法可靠匹配时保存空值。
- 经验输出最小/最大年限和经验区间；“不限”不等于缺失，“应届/在校/实习”归为 entry。
- 日期支持 ISO 日期/时间及 `YYYY/MM/DD`、`YYYY.MM.DD`。相对日期（例如“昨天”）在没有可靠观察时间时不推断。

### 2.2 薪资标准化

Silver 目标字段为 `salary_min_monthly`、`salary_max_monthly`、`salary_mid_monthly`、`salary_annualized`、`salary_months` 和 `salary_parse_status`，同时永久保留 `salary_raw`。

规则：

1. 解析区间、单位（K/元）、周期（月/年/日）和可能的薪数（如 13 薪）。
2. 月薪没有明确薪数时，`salary_months=null`；`salary_annualized` 仅按 12 个月计算“标准年化等价值”，不表示实际年包或默认存在 12/13 薪。
3. 月薪明确写出 13/14 薪时，`salary_months` 保存原值，年化等价值按月薪中点乘以明确薪数。
4. 日薪按 21.75 个工作日/月换算，年薪按 12 个月折算为月薪；这两个换算常量属于方法版本，不能被描述为实际出勤或发薪承诺。
5. `面议` 使用 `negotiable`；缺失使用 `missing_at_source`；范围倒置、非正值或转换后非有限数值使用 `invalid_range`；未知格式使用 `unparseable`。这些状态的数值字段全部为空。当前尚未对正的有限薪资设置业务上限，极端但可解析的离群值需由来源质量规则和发布前分布审计处理。
6. 薪资分析使用可用记录的中位数、IQR 与样本量；不以均值单独代表市场薪资。

当前支持的首批格式：`15-25K`、`15-25k`、`20-30K·13薪`、`30-50K·14薪`、`200-300元/天`、`20-30万/年` 和 `面议`。

### 2.3 技能抽取与 Taxonomy

Phase 3 使用版本化的 `data/taxonomy/skills.yml`。每个技能包含稳定 `skill_id`、规范名、类别、别名、学习时间三点估计、成本来源和说明。1.1.0 起由同一 taxonomy 内的 `semantic_defaults` 与 `semantic_overrides` 配置解析 `skill_type`、`skillworth_eligibility` 和可审计原因；Analytics 不按技能名称写分支。学习时间表示“从零达到可用于初级岗位任务”的人工维护区间，是后续优化器的假设输入，不是课程时长、掌握承诺或就业承诺。默认使用 `learning_hours_expected`；任何结果都应允许展示最小/预期/最大情景和来源。

规则抽取版本 1.0.1 遵循 Rule First：

1. 将岗位原始标题与原始 JD 合并为抽取文本，不改写原始证据；只处理 `record_status=valid` 的 Silver 岗位。
2. 对规范名和 alias 使用 `re.IGNORECASE` 执行大小写不敏感匹配。ASCII 字母、数字和下划线被视为词内字符，因此 `jsonish` 不会命中 `JSON`；中文可紧邻英文技能词，例如“熟悉Python”。
3. `R`、`C`、`Go`、`AI` 不执行无上下文的规范名匹配，只在“R语言”“C/C++”“Go 开发”“AI 模型”等明确技术上下文中命中；`Golang`、`人工智能` 等低歧义 alias 仍按一般规则匹配。
4. 同一岗位同一技能只保存一条关系。优先级为规范名、alias、短词上下文，并在同等级下保留置信度更高、出现更早的证据。
5. `extraction_method` 当前为 `rule_canonical`、`rule_alias` 或 `rule_short_context`；相应 `confidence` 是版本化规则强度（0.98/0.95/0.90），不是统计概率。
6. LLM fallback 仅定义 `LLMSkillExtractor` interface；默认实现 `DisabledLLMSkillExtractor` 固定关闭、返回空列表，不读取凭证、不访问网络。未来即使启用，也只能返回 taxonomy 候选，不能参与统计计算或覆盖规则证据。

高歧义招聘缩写同样遵循 Precision 优先：v1.0.1 起不再把无上下文 `CV` 视为 Computer Vision，也不再把无上下文 `MD` 视为 Markdown。前者在真实 JD 中常表示简历或 Commercial Vehicle，后者可表示 Managing Director。完整名称 `Computer Vision`、`计算机视觉` 与 `Markdown` 仍可抽取；需要恢复缩写时，必须先增加上下文规则和人工标注正/负例。

人工标注 Benchmark 位于 `data/benchmark/jd_skill_extraction.yml`，覆盖中文、英文、中英混合、技术密集和非技术 JD。评测单位是 `(fixture_id, skill_id)`，使用 micro aggregate：

```text
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 × Precision × Recall / (Precision + Recall)
```

没有预测且没有真值时，该 fixture 不单独制造 TN 分数；整体 TP、FP、FN 汇总后计算。任何 taxonomy 或规则变更都必须重新运行 Benchmark，并报告典型 false positive / false negative。小规模 fixture 的高分只证明回归样例表现，不代表真实招聘市场的泛化性能。

### 2.4 跨平台岗位去重

Phase 4 的目标是构造 Gold 层的 `canonical_jobs.parquet`，并把每一条 Silver 候选记录无损映射到 `job_source_map.parquet`。去重仅处理 `record_status=valid`、且具有非空 `silver_job_id` 的记录；无效 Silver 不进入市场指标分母，也不会被静默删除。

规则版本 `deduplication_rule_version=1.0.0` 的总体原则是 Precision 优先于 Recall。候选对必须先满足公司和城市相同，且不得出现以下任一冲突：

- 双方可解析的 `role_id` 不同；
- 岗位标题或经验字段明确显示不同 seniority；
- 一方为实习、另一方明确为全职；
- 两个岗位标题中均有可识别业务单元标记（括号或方括号内容），且标记不同。

匹配按强度依次尝试，首次命中的等级写入审计映射：

1. **Level 1 — `level_1_exact`**：`company_name_normalized`、城市键（优先 `city_code`）与 `job_title_normalized` 全部精确相同。
2. **Level 2 — `level_2_fuzzy_title`**：公司和城市相同、双方具有相同且已分类（非 `other`）的 `role_id`，且 RapidFuzz `fuzz.ratio` 的规范标题相似度不低于 96/100。只使用完整字符串 ratio，不使用会对标题子集返回 100 的 token-set 指标。
3. **Level 3 — `level_3_simhash_description`**：公司和城市相同、双方具有相同且已分类的 `role_id`、标题 ratio 不低于 90/100，且非空 JD 的 64-bit character 3-gram SimHash Hamming distance 不大于 3。该规则无需 Embedding 或任何付费 API。

分组使用确定性的 complete-link 贪心合并：新记录只有在能与某一既有组的每个成员都满足同一保守匹配门槛时才加入；若多个组均可加入，选择最低匹配等级更强、最低分更高、再按代表记录 ID 排序后的组。这避免“链式相似”把两个原本不相同的岗位经由中间记录错误合并。

每个组的代表记录按 `observed_at`、`source_id`、`silver_job_id` 的稳定顺序选取；`canonical_job_id` 由代表 `silver_job_id` 的 SHA-256 派生。映射表保留原始标准化岗位 ID、来源、来源岗位 ID、来源 URL、观测时间、匹配等级、分数、原因和规则版本。去重不修改 Bronze/Silver，也不将“相似”描述为确定事实。

固定快照可应用版本化的 exact-pair 人工审计决定，但它不是新的模糊匹配层，也不改变通用候选生成和打分。审计键必须精确到两条 `(source_id, source_job_id)`，且只能作用于通用规则已经形成的同一二元组：`different` 将该组拆成两个 singleton，`same` 保持原组并记录审计理由。不得仅因 upstream requisition 不同而拆分；需要同时存在明确的岗位层级或 variant 证据。`freehire_china_tech_2026_08` 的审计范围固定为 `data/reference/freehire_dedup_audit_2026_08.v1.yml` 中原有 8 组，不扩展为全库 Dedup Benchmark。

当前 v1 的岗位维度字段（包括薪资、岗位、城市、经验和学历）取自该稳定代表记录，不会跨成员择优补值；因此代表记录缺失、其他重复成员存在该字段时，Gold 仍可能为 null。技能关系则通过 `job_source_map` 汇总同一 `canonical_job_id` 下各 Silver 成员的去重技能并集。该不对称行为是已知限制，分析时必须结合字段覆盖率，不能把缺失解释为该重复组所有来源都没有该信息。

去重报告定义：

- `raw_job_count`：输入 Silver 总行数；`eligible_job_count`：参与去重的有效行数。
- `canonical_job_count`：Gold 规范岗位组数；`duplicate_group_count`：成员数大于 1 的组数。
- `dedup_rate=(eligible_job_count-canonical_job_count)/eligible_job_count`；无 eligible 记录时为 0。
- `cross_platform_overlap_group_count`：拥有至少两个不同 `source_id` 的规范岗位组数；`cross_platform_overlap_rate=cross_platform_overlap_group_count/canonical_job_count`。它反映本次样本中的可识别重叠，不代表平台整体覆盖率或市场份额。

阈值为初始保守配置，必须通过人工标注岗位对复核 Precision/Recall 后才可调整。短 JD、缺失公司/城市、未被标题标记出的业务单元以及跨天重发均是已知漏检来源；结果不得宣称“没有重复岗位”。

### 2.5 Bronze → Silver 与 Data Quality Report

Bronze 输入是 append-only：Pipeline 仅以只读方式打开 CSV/Parquet，并在转换前后比较每个输入文件的 SHA-256。Silver 输出不得与任一 Bronze 输入路径相同；任何输入哈希变化都会使构建失败。Silver 不因字段解析失败而丢行，结构性无效记录保留并标记 `record_status=invalid`。

质量报告定义：

- `raw_row_count`：读取到的 Bronze 行数。
- `silver_row_count`：写入 Silver 的行数。
- `missing_rate`：公司、标题、城市、学历、经验、薪资中点和发布日期七个关键 Silver 字段缺失率的等权平均。
- `missing_rate_by_field`：上述字段各自的缺失率。
- `salary_parse_rate`：薪资状态属于任一 `parsed_*` 状态的行数占比；`面议`不计为成功解析。
- `role_parse_rate`：角色明确命中 taxonomy（不含 `other` fallback）的行数占比。
- `city_parse_rate`：城市明确命中 taxonomy 的行数占比。
- `invalid_record_rate`：缺少核心 provenance 或岗位标题的结构性无效记录占比；单个分析字段无法解析不会使整条岗位无效。

## 3. 市场指标

### 3.1 Skill Demand

在市场切片 `S` 中，技能 `k` 的岗位覆盖率为：

```text
Demand(k, S) = 含技能 k 的去重有效岗位数 / S 中去重有效岗位总数
```

同时返回绝对岗位数。分母是 Gold `jobs` 中满足显式 role/city/experience/education/source/date 筛选的全部规范岗位；它们已经排除结构性无效 Silver，但不要求 `role_id` 非 `other`，也不要求岗位抽取到至少一项技能。后者必须留在分母，否则会系统性夸大技能覆盖率。分子按 `canonical_job_id` 去重，技能关系使用该规范岗位所有来源成员的技能并集。结果必须展示分母和时间范围。

### 3.2 Skill Trend

每月先计算该技能在当月切片内的岗位覆盖率 `d_t`。默认报告：

- 3 个月与 6 个月覆盖率百分点差值；
- 线性趋势斜率；
- 月度样本量和可选的 3 期移动平均；
- `emerging`、`growing`、`stable`、`declining`、`niche` 标签。

标签仅在月度样本门槛、最小观察月数和波动门槛全部满足时发布；具体阈值由版本化配置提供。季节性、平台构成变化和发布时间缺失会被标为局限。

Phase 7 的可执行规则来自 `data/reference/advanced_analytics.v1.yml`。月度分母是该切片当月所有 Gold 规范岗位数，分子是当月含该技能的不同 `canonical_job_id` 数；没有该技能但存在岗位的月份覆盖率为 `0`，没有任何岗位的月份不被填成 `0`。因此趋势基于 `skill_job_coverage`，绝不以绝对岗位数代替。

对最新有岗位月份 `T`：

```text
change_3m = d_T - d_(T-3)
change_6m = d_T - d_(T-6)
rolling_mean_t = mean(d_(t-w+1), ..., d_t), 默认 w=3
trend_slope = OLS(d_t ~ 1 + elapsed_month_index) 的月度斜率
volatility = sample_std(d_t - d_(t-1))
```

变化值和斜率使用覆盖率单位，例如 `0.02` 表示 2 个百分点，不表示 2%。Rolling mean 只有在窗口完整时才返回。斜率和波动只使用达到 `minimum_monthly_sample_size` 的月份；月份数、累计岗位样本或最新月份样本不达门槛时，`classification=null`、`conclusion_strength=insufficient`，不输出 Emerging/Growing 等强结论。

达到样本门槛后按以下顺序匹配，所有阈值均来自配置：

1. `Declining`：斜率和 3-month change 同时低于下降阈值；
2. `Emerging`：3 个月前覆盖率低于基线且 3-month change 达到新兴阈值；
3. `Growing`：斜率和 3-month change 同时达到增长阈值；
4. `Mature`：最新覆盖率达到成熟门槛，且斜率和波动处于成熟范围；
5. `Niche`：最新覆盖率低于小众门槛，且斜率接近零；
6. `Stable`：斜率和波动都处于稳定范围。

即使样本充分，若没有规则匹配，也返回 `classification=null`、`conclusion_strength=inconclusive`，而不是强行归类。

### 3.3 Adjusted Salary Association

薪资溢价回答“在可观察控制变量相近的岗位中，含某技能的岗位薪资是否存在关联差异”，不回答因果问题。

对通过解析和异常值质量门槛的岗位拟合：

```text
log(monthly_salary_midpoint)
~ has_skill(k) + role + city + experience + education + month
```

报告 `has_skill(k)` 系数转换后的百分比关联、置信区间、样本数、控制变量可用性、模型版本和诊断摘要。只有样本量、技能正例数量和模型诊断达到门槛时才显示结果；否则显示不可估计。岗位描述中技能遗漏、未观测公司等级和选择偏差属于已知混杂因素。

Phase 7 使用自然对数月薪中点作为因变量，对 role、city、experience、education 和发布日期月份做 one-hot 控制（每组丢弃一个参考类别）；缺失控制值作为显式 `__missing__` 类别保留。只纳入薪资为正且落在配置范围内的 Gold 岗位。每个技能分别拟合：

```text
log(salary_mid_monthly)
= intercept + has_skill + role FE + city FE
  + experience FE + education FE + month FE + error
```

模型使用 Statsmodels OLS 和 HC3 heteroskedasticity-robust covariance。结果返回：

```text
coefficient = beta_skill
percentage_approximation = 100 * (exp(beta_skill) - 1)
confidence_interval = beta_skill 的双侧置信区间
percentage_confidence_interval = 对区间端点做相同指数变换
```

同时返回 p-value、样本量、技能正/负样本数、R²、调整 R²、AIC、BIC、残差标准差、设计矩阵秩、参数数、condition number 和 covariance type。总样本、技能正例或负例不足时状态为 `insufficient_sample`；设计矩阵秩不足时为 `rank_deficient`；condition number 超过配置时为 `estimated_with_warning`。p-value 不作为发布/隐藏结果的开关。

Adjusted Salary Association / Salary-associated Premium 是条件关联，不是因果效应。控制变量不包含公司规模、职级细粒度、候选人能力、奖金股权或工作强度，任何结果都不得表述为技能带来的确定工资增幅。

### 3.4 Skill Co-occurrence Network

对同一市场切片中的去重岗位，统计技能对 `(a, b)` 的共同出现次数。边强度同时计算：

```text
Jaccard(a, b) = 共现岗位数 / 至少包含其中一个技能的岗位数
PMI(a, b) = log(P(a,b) / (P(a) × P(b)))
```

网络只保留超过最小共现次数且通过强度阈值的边，以避免稀有偶然共现。NetworkX 社区发现用于识别技能簇；可视化中必须显示阈值和所选指标。

Phase 7 在过滤后的 Gold 岗位技能集合上定义：

```text
cooccurrence(a,b) = 同时包含 a、b 的规范岗位数
Jaccard(a,b) = cooccurrence / (support(a) + support(b) - cooccurrence)
PMI(a,b) = log(cooccurrence * N / (support(a) * support(b)))
```

其中 `N` 是切片内规范岗位数。仅保留 `cooccurrence >= minimum_cooccurrence_count` 且 `Jaccard >= minimum_jaccard` 的边。NetworkX 无向图以配置的 `edge_weight`（v1 为 Jaccard）执行 greedy modularity community detection；无边节点作为单独社区保留。输出节点和边 Parquet 均携带 `methodology_version` 与配置版本。PMI 可为负数，表示共同出现弱于独立性基线，不能被截断为零。

### 3.5 Cross-platform Bias Analysis

对每个来源 `p`，先独立计算技能覆盖率 `d_{k,p}`，再计算：

```text
Pooled Demand(k) = 所有有效岗位合并后的覆盖率
Platform-balanced Demand(k) = 可用来源覆盖率的等权平均
Platform Delta(k,p) = d_{k,p} - Platform-balanced Demand(k)
```

该分析描述样本构成差异，不能证明平台本身存在偏见或代表真实全市场。样本量不足的来源不纳入均衡平均，并应公开缺失情况。

### 3.6 Phase 6 基础市场分析

Phase 6 的全部指标由独立的 `skillworth_analytics` 模块从 DuckDB Warehouse 查询。模块接受相同的可选切片：`role_id`、`city_code`、`experience_band`、`education_band`、一个或多个 `source_id` 以及闭区间 `published_from` / `published_to`。字段值全部作为 SQL 参数绑定；来源筛选先要求规范岗位至少有一条映射记录来自所选来源，再只使用这些来源岗位上的技能证据，避免同一 canonical job 的其他平台 JD 混入。其他维度来自代表性 Gold 岗位。空切片保留空结果及分母 `0`，不伪造结论。

**Skill Demand** 对每个技能在过滤后的 Gold 规范岗位集合 `J` 计算：

```text
job_count(k) = |{j ∈ J : j 包含 k}|
job_coverage(k) = job_count(k) / |J|
```

`sample_size=|J|`；`source_count` 是含该技能的规范岗位可追溯到的不同来源数。因岗位分母去重，该指标不会把跨平台重复发布直接累加。

**Platform-balanced Demand** 将每个来源 `p` 的岗位集合保持在 `silver_job_id` 粒度：

```text
coverage(k,p) = 来源 p 中含技能 k 的岗位数 / 来源 p 的岗位数
pooled_coverage(k) = job_coverage(k)
platform_balanced_coverage(k) = mean_p(coverage(k,p))
```

输出必须同时包含每个平台的 `coverage`、`sample_size` 和来源标识。均衡值只对实际有岗位的来源等权平均；它用于降低单一来源样本量对合并结果的支配，不代表任一平台或全市场的真实份额。

**Salary By Skill** 仅使用可解析的 `salary_mid_monthly`，对每个技能返回中位数、P25、P75、`sample_size` 与：

```text
salary_coverage(k) = 有可用薪资的含技能规范岗位数 / 含技能规范岗位数
```

这是描述性分布，不能解释为技能导致的薪资差异。`Skill By Role`、`Skill By City`、`Skill By Experience` 使用相同的 Gold 去重岗位分母，在每个分组内返回技能岗位数、覆盖率和样本量。

**Source Bias Analysis** 在来源岗位（`silver_job_id`）粒度比较 role、skill、city、experience 的构成：某构成值的 coverage 是该来源含该值的岗位数除以该来源过滤后的岗位数。结果只描述当前导入样本的构成差异，名称中的 “bias” 不构成对招聘平台行为或人群代表性的因果判断。

## 4. 决策指标

### 4.1 岗位技能覆盖与 Marginal Opportunity Gain

每个岗位的技能集合设为 `R_j`，用户已掌握技能集合为 `U`。对于岗位 `j`：

```text
SkillFit(j, U) = |U ∩ R_j| / |R_j|
```

Phase 9 v1 对技能等权，不把 Skill Fit 描述为录取概率、就业概率或 Offer Probability。目标岗位由必填 `target_role` 与可选 `city`、`experience` 筛选；`R_j` 来自 Gold `job_skills` 的去重技能集合。没有抽取到任何技能的目标岗位因分母为 0，不进入 Fit 样本，并通过 `jobs_without_extracted_skills` 单独报告。

对可计算岗位集合 `J` 和阈值 `τ`：

```text
CurrentAverageFit = avg(SkillFit(j, U)), j in J
CurrentThresholdCoverage = count(SkillFit(j, U) >= τ) / |J|

NewAverageFit(c) = avg(SkillFit(j, U ∪ {c})), j in J
NewThresholdCoverage(c) = count(SkillFit(j, U ∪ {c}) >= τ) / |J|

AverageFitGain(c) = NewAverageFit(c) - CurrentAverageFit
ThresholdCoverageGain(c) = NewThresholdCoverage(c) - CurrentThresholdCoverage
JobsCrossingThreshold(c) = count(
    SkillFit(j, U) < τ and SkillFit(j, U ∪ {c}) >= τ
)
```

候选集合是目标岗位中出现、但不属于 `U` 的全部技能。因为候选技能尚未掌握且单个岗位技能集合已去重，若岗位要求候选 `c`，该岗位 Fit 增量恰为 `1 / |R_j|`；否则为 0。实现利用这一恒等式在 DuckDB 中只聚合实际要求候选技能的岗位，不构造候选技能与全部岗位的 Python row-loop 或完整笛卡尔积。

`match_threshold` 范围为 `[0,1]` 且包含边界。只有当前 Fit 严格低于阈值、增加候选技能后大于等于阈值的岗位才计入 crossing；已经位于阈值上的岗位不会重复计数。结果按 `threshold_coverage_gain` 降序、`average_fit_gain` 降序、`skill_id` 升序稳定排列。

无目标岗位时状态为 `no_target_jobs`；存在目标岗位但全部缺少技能证据时为 `no_skill_evidence`。这两种情况的 Fit 均为 `null`，不以 0 冒充测量结果。

每个候选技能的 Data Confidence 使用同一目标岗位样本、来源构成和最新发布日期，并以“该候选在各来源内的 Average Fit Gain”评估跨来源一致性；顶层 cohort confidence 使用各来源 Current Average Fit。来源不足时沿用 Phase 8 的保守 warning 和评分规则。

其中 `τ` 是用户可见且版本化的匹配阈值。两个值均表示岗位技能匹配改善，不表示职位可获得性。

### 4.2 Learning Cost

每个技能从版本化 Skill Taxonomy 读取 `learning_hours_min`、`learning_hours_expected`、`learning_hours_max` 和 `learning_cost_source`。Learning Hours 是“从零达到可用于初级岗位任务”的人工维护估算，不是课程时长、掌握承诺或就业承诺。输出必须始终携带 `is_estimate=true` 和免责声明。

默认计算使用 `learning_hours_expected`。用户可用正数覆盖某个技能的 expected hours；覆盖只改变本次请求的 `effective_expected_hours`，不修改 taxonomy 中的 min/expected/max 或来源，并标记 `is_user_override=true`。

### 4.3 Market Value Score

Market Value Score 回答“该技术从整体招聘市场看价值如何”，不描述某个用户是否应学习。Phase 10 配置位于 `data/reference/decision_scores.v1.yml`，所有分量先映射到 `[0,100]`：

```text
DemandScore = 100 × Demand
SalaryScore = 100 × clip((association_pct - salary_min) / (salary_max - salary_min), 0, 1)
TrendScore = 100 × clip((trend_slope - trend_min) / (trend_max - trend_min), 0, 1)
SynergyScore = 100 × SkillSynergy
ConfidenceScore = DataConfidence

MarketValue = sum(component_score_i × effective_weight_i)
```

默认权重为 Demand `0.25`、Adjusted Salary Association `0.20`、Trend `0.20`、Skill Synergy `0.15`、Confidence `0.20`。薪资分量仍只表示条件关联，不表示因果。统计模型无法估计薪资或趋势时，该分量显示 `available=false` 和 warning，并按配置 `exclude_and_reweight` 只在其余可用分量上重算 effective weights。每个 component 返回原始值、归一化分、配置权重、实际权重、贡献值和解释；UI 不得持有另一套权重。

### 4.4 Personal ROI Score

Personal Skill ROI 回答“对这个具体用户来说，现在学它是否划算”，是学习优先级，不是财务回报率。输入为 Phase 9 Marginal Skill Coverage Gain、Market Value、Learning Hours 和候选技能 Data Confidence：

```text
MarginalGainScore = 100 × MarginalSkillCoverageGain
LearningCostEfficiency = 100 × half_value_hours / (half_value_hours + effective_expected_hours)

PersonalROI = 0.45 × MarginalGainScore
            + 0.25 × MarketValue
            + 0.15 × LearningCostEfficiency
            + 0.15 × DataConfidence
```

默认 `half_value_hours=160`，全部权重配置化。结果必须同时展示四个 component 和完整 Learning Hours 区间。用户覆盖时长后必须重新计算，不得覆盖原始估算。

### 4.5 Sensitivity Analysis

Sensitivity Analysis 使用配置中的多组 Market Value / Personal ROI 权重重新计算全部候选技能排名。每个场景使用分数降序、`skill_id` 升序的确定性 ordinal rank。对技能 `k`：

```text
RankRange(k) = max_s(rank_s(k)) - min_s(rank_s(k))
RankStability(k) = 1 - RankRange(k) / (skill_count - 1)
```

只有一个技能时稳定度定义为 1；整体 `overall_rank_stability` 是技能稳定度的算术平均。配置 v1 当 `rank_range >= 2` 时输出 `Sensitive Ranking Warning`。该 warning 表示排序依赖权重选择，不表示技能数据本身错误。Notebook `05_sensitivity_analysis.ipynb` 只调用公开评分模块。

### 4.6 Learning Time Optimizer

输入为当前技能、目标角色和正数小时预算；可选城市、经验、Skill Fit 阈值与用户学习时长覆盖。Phase 10 v1 使用 Iterative Greedy Marginal Gain，不执行一次静态 ROI 排名后顺序截取。

在当前技能集合 `U_t` 下调用 Phase 9 重新计算所有剩余候选。对预算内候选 `c`：

```text
MarginalGain(c | U_t) = 0.60 × AverageFitGain(c | U_t)
                      + 0.40 × ThresholdCoverageGain(c | U_t)
SelectionScore(c | U_t) = MarginalGain(c | U_t) / effective_expected_hours(c)
```

选择 Selection Score 最大的技能，加入 `U_t`，更新剩余预算，然后重新查询全部剩余技能。若没有预算内且达到最小边际增益的技能则停止。输出 `step`、技能、估算小时、累计小时、`marginal_fit_gain`、累计 Fit、阈值覆盖和选择原因。

这是可解释启发式，不保证全局最优。当前版本没有启用 Beam Search，结果显式返回 `beam_search_used=false`；不得把 Greedy 结果描述为 Beam 或全局最优。

## 5. Data Confidence Score

Data Confidence 衡量一个指标结果的证据充分程度，不衡量技能好坏，也不是统计置信区间。Phase 8 使用 `data/reference/data_confidence.v1.yml` 中的透明规则；固定评估日期 `as_of_date` 后，同一证据和配置必然得到同一结果，不调用 LLM 或其他黑盒模型。

### 5.1 分量

所有分量先转换到 `[0,100]`：

```text
SampleSize = 100 × min(1, log1p(n) / log1p(target_n))

p_s = source_s_count / sum(source_count)
EffectiveSources = 1 / sum(p_s²)
SourceDiversity = 100 × min(1, EffectiveSources / target_effective_sources)

Freshness = 100                                      if age_days <= full_score_days
Freshness = 100 × (zero_score_days - age_days)
                  / (zero_score_days - full_score_days)
                                                       otherwise
Freshness = 0                                        if age_days >= zero_score_days

SalaryCoverage = 100 × salary_eligible_count / sample_size

Disagreement = population_std(platform_metric_values)
CrossSourceAgreement = 100 × max(0, 1 - Disagreement / zero_score_std)
```

- `sample_size` 使用该指标切片中的 Gold 去重有效岗位数；达到目标样本量后封顶，避免超大平台样本无限放大分数。
- `source_diversity` 同时考虑来源数量和集中度。四个平台不等于四个同等证据来源；一个来源占绝大多数时，有效来源数接近 1。
- `data_freshness` 使用 `as_of_date - latest_observation_date` 的天数。缺失日期按 0 分；未来日期按 0 天计算并产生数据质量警告。
- `salary_coverage` 只适用于薪资类指标。非薪资指标标记为 `applicable=false`，不参与总分；样本量为 0 时覆盖率为 0。
- `cross_source_agreement` 使用各平台同一指标、同一切片下 `[0,1]` 值的总体标准差。平台数不足时一致性是“未知”，不是“完全一致”：该分量标记 `available=false`，按保守 0 分参与总分并输出 warning；0 分表示证据缺失，不能表述为已证实平台不一致。

### 5.2 合成与等级

默认原始权重分别为 `0.30 / 0.20 / 0.20 / 0.15 / 0.15`。只在适用分量集合 `A` 上重新归一化：

```text
effective_weight_i = configured_weight_i / sum(configured_weight_j for j in A)
Confidence = sum(component_score_i × effective_weight_i for i in A)
```

总分在 `[0,100]` 内保留两位小数。配置 v1.0.0 的等级为：`High >= 75`、`Medium >= 50 且 < 75`、`Low < 50`。边界使用包含下界的规则。

### 5.3 警告规则

warning 使用稳定代码并携带所属 component 和解释文本。比较边界保持透明：样本量、来源数和薪资覆盖率使用“低于”触发；数据年龄和平台总体标准差使用“高于”触发。

| warning code | 触发条件 |
| --- | --- |
| `sample_size_below_threshold` | `sample_size < warning_below` |
| `source_count_below_threshold` | 非零记录来源数低于配置门槛 |
| `data_freshness_missing` | 最新观测日期为空 |
| `data_older_than_threshold` | 数据年龄超过配置天数 |
| `latest_observation_in_future` | 最新观测日期晚于评估日期 |
| `salary_coverage_below_threshold` | 薪资类指标覆盖率低于配置门槛 |
| `cross_source_agreement_unavailable` | 平台指标值少于最低来源数 |
| `platform_disagreement_above_threshold` | 平台指标总体标准差超过配置门槛 |

结果必须单独显示 `confidence_score`、`confidence_level`、每个 `confidence_components` 和全部 `warnings`。总分不能掩盖低分分量或 warning；任何低置信结论禁止在不显示警示的情况下进入推荐榜首。

## 6. 验证与版本治理

- 每个公式都有边界条件测试、已知 fixture 结果和输入数据版本。
- 薪资模型记录回归诊断；技能抽取使用人工标注集评估；去重使用标注对评估 precision/recall。
- 每次 taxonomy、阈值、权重或模型改变时递增 `methodology_version`，并重新生成受影响的结果。
- Dashboard 应提供此文档的入口，展示与当前响应一致的方法版本。

## 7. Gold Benchmark 与目标市场验证

目标市场覆盖先于 taxonomy 扩充。系统使用配置化标题规则把岗位审计为 `target`、`possible`、`non_target`，同时统计公司集中度、行业线索、JD 技术关键词、模板文本和来源构成。该分类仅用于抽样与数据源诊断，不是人工 Gold Label，也不用于报告正式分类准确率。

Role、Skill 与 Dedup Benchmark 均固定分为 `development` 和 `held_out_test`。开发集可用于失败分析和规则迭代；held-out test 禁止用于调参。样本不足时不以空集合计算 100% 指标，而是输出 null 和 `INSUFFICIENT BENCHMARK DATA`。指标定义及门禁详见 `docs/BENCHMARKS.md`。

### 7.1 Canonical Job 字段级融合

Dedup group 与 `canonical_job_id` 的身份规则保持不变，Canonical 字段不再全部来自 representative row：

- Title：优先显式 `title_normalization_confidence`，其次选择 Role 已解析、原始标题信息更完整的记录；稳定 ID 用于最终 tie-break。记录 `title_source_silver_job_id`。
- Company、City、Experience、Education：选择非空标准化值的稳定众数；并列时按信息长度和字典序稳定选择。
- Description：按不同 token 数、去空白字符长度选择信息量最高的非空 JD，记录 `description_source_silver_job_id`。这只是透明信息量规则，不判断文案真实性。
- Salary：保留组内每条 `salary_observations`，字段为 source、raw_salary、normalized_salary（月薪中点）和 observed_at。只使用 parser 明确成功、有限且为正的月薪；先计算每个来源的中位数，再计算跨来源中位数，避免单一来源多次观测获得额外权重。
- Salary conflict：跨来源有效月薪的 `(max - min) / median` 大于配置阈值 0.35 时，`salary_conflict_flag=true`，`canonical_salary=null`，不强制融合。无冲突时 canonical salary 为来源中位数的中位数。
- Dates：`first_posted_at` 为最早可靠发布日期；`first_seen_at`/`last_seen_at` 为最早/最晚观测时间。无法可靠解析的日期不参与边界计算。
- Provenance：`job_source_map` 保留全部 Silver 记录及 source、source_job_id、source_url、observed_at，不因字段融合而删除来源。

`salary_observations` 另保留 `currency` 与 `native_min_monthly`。只有与分析基准币种兼容且 parser 成功的 `normalized_salary` 才参与 canonical salary；港币原生数值不会与人民币月薪直接求中位数。

## 8. Target Market Scope 与多来源验证

`data/reference/target_market.v1.yml` 对标题给出可审计的 `target`、`possible`、`non_target` 规则。它是市场范围过滤器，不是 Role Gold Label；不能用它报告分类 accuracy。主要市场指标的 `AnalyticsFilters.market_scope` 默认值为 `target`，调用方必须显式传 `all` 才查看全量。

Platform-balanced Demand 先在每个来源内计算 `skill posting count / source posting count`，再对来源覆盖率等权平均。Pooled Coverage 的分母仍为 Target Scope 的 canonical jobs。来源样本很小或没有技能命中时，0 是实际覆盖值，但必须同时展示 source sample size，不能把等权结果解释为总体市场真值。

跨来源覆盖率离散度报告总体方差：

```text
cross_source_variance = population_variance(source_coverage)
High Agreement   : variance <= 0.0025   (std <= 5pp)
Medium Agreement : variance <= 0.0225   (std <= 15pp)
Low Agreement    : variance > 0.0225
```

来源构成差异使用 base-2 Jensen-Shannon divergence，范围 `[0,1]`。0 表示观测分布相同，1 表示当前类别支持完全分离。该指标统一称为 **Observed Source Composition Difference**，不主张平台造成了差异。

当前多来源快照中 Target 岗位按月仅覆盖 2024-03 至 2024-09，以及 2026-07，中间存在 21 个月空档且来源构成改变。因此 Trend 标记为 `unavailable`；不能把两个不连续来源窗口连接成增长率。Salary Association 因可比人民币薪资为 0 同样不可用。Market Value 的必需输入不完整，不发布正式分数。

Dedup 1.1.0 对“同一来源、不同 source_job_id、相同公司/城市/标题”的 Level 1 pair 增加 JD 相似保护：只有非空 JD 的 RapidFuzz ratio 至少 95 才合并。跨来源的精确键规则不变。该调整优先降低同平台同名但不同招聘批次的 false merge；真实 Gold Pair 仍不足，因此不声明已达到生产 precision。

融合参数位于 `data/reference/canonical_merge.v1.yml`，输出记录 `canonical_merge_version`。薪资 association 分析仍只使用非冲突且有效的 `salary_mid_monthly`。

## 8. Metric Guardrails 2.0（覆盖旧 Platform-balanced / Confidence 口径）

本节自 `phase6_market_basics_v2`、`platform-balanced-demand-2.0.0` 和 `data-confidence-2.0.0` 起生效；与上文旧口径冲突时以本节为准。阈值集中在 `data/reference/metric_guardrails.v1.yml` 和 `data/reference/data_confidence.v1.yml`。

### 8.1 Source Role 与核心市场范围

每个来源明确标记为 `core_market`、`core_market_candidate`、`supplementary_market`、`engineering_validation` 或 `historical_reference`。`core_market_candidate` 是待验证状态，本身不具备核心市场资格；即使样本指标达标，也必须先完成数据许可审查并显式升级角色。核心 Market Metric 默认只读取 core 和满足门禁的 supplementary source；调用方必须显式设置 `source_scope=all` 才能查看工程验证来源。`engineering_validation` 仍可进入 Data Quality、Source Composition Difference、Connector 与 Pipeline 验证。

当前 `hk_csb_gov_vacancies` 为 `engineering_validation`，不能默认参与 Skill Market Value。未知来源不会被自动宣称为正式核心市场来源；Demo fixture 仅为兼容测试保留独立运行。

`ncss_public_jobs` 当前为 `core_market_candidate` 且 `data_usage_status=permission_required`。导入器在写入 Raw/Bronze 前拒绝该来源；Source Gate 也返回 `SOURCE_ROLE_NOT_CORE_MARKET_ELIGIBLE`。上游代码许可证不作为数据许可证据。

### 8.2 Source Eligibility Gate 与 Platform-balanced Demand

来源必须同时满足：目标市场样本量、目标市场比例、技能抽取覆盖率、最大市场年龄和允许的 Source Role。每个失败条件都返回机器可读 reason。只有 `eligible_source_count >= required_eligible_sources` 时才计算：

```text
coverage(k,p) = source p 中含技能 k 的 posting 数 / source p 的 target posting 数
platform_balanced_coverage(k) = mean(coverage(k,p) for eligible source p)
```

来源不足时 `platform_balanced_coverage=null`，并返回 `pooled_coverage`、`eligible_source_count`、`ineligible_sources` 和原因。实验性 `reliability_weighted_coverage` 目前只保留接口，状态为 `not_implemented`：现有证据不足以定义不会让大平台重新主导的稳定 shrinkage 公式。

Cross-source Agreement 只使用 eligible 且每个来源达到 `minimum_sample_per_source` 的值；否则为 unavailable，warning 为 `INSUFFICIENT_COMPARABLE_SOURCES`。Jensen-Shannon divergence 必须同时携带两侧样本量、eligibility 和 warning；它仍只表示 Observed Source Composition Difference。

### 8.3 Effective Source Diversity

保留 `raw_source_count`，但 Confidence 使用 eligible 来源样本权重：

```text
w_i = eligible source i 的样本量 / eligible source 总样本量
effective_source_count = 1 / Σ(w_i²)
```

不 eligible 的来源权重为 0，因此 Target n=2 的工程验证来源不会被视为完整第二市场来源。

### 8.4 Pipeline Freshness 与 Market Freshness

- Pipeline Freshness：`latest_observed_at` 与 `pipeline_age_days`，表示数据何时进入管道。
- Market Freshness：`latest_posted_at`、`median_posting_age_days`、`p75_posting_age_days` 与 `posting_date_coverage`，表示岗位实际发布时间。

核心 Confidence 使用 P75 posting age，并乘以 posting-date coverage。当天导入的旧岗位只能获得新鲜 Pipeline 状态，不能获得新鲜 Market 状态。

### 8.5 Confidence 2.0

分量为 `sample_strength`、`effective_source_diversity`、`market_freshness`、`cross_source_agreement` 和 `metric_specific_coverage`。适用分量按配置权重重新归一化。Confidence 表示“当前数据支持该分析结论的证据强度”，不表示代码质量或技能本身可信度。

配置化 cap 包括：无达标 Gold Benchmark、eligible source 不足和样本量极低。先计算透明加权分，再取 `min(weighted_score, confidence_cap)`；响应必须同时返回 cap 与触发 warning。

## 9. Gold Benchmark 2.0

Skill、Role、Dedup Gold Set 均含版本 metadata：`benchmark_version`、`created_at`、`label_count`、`split_seed`、`taxonomy_version`、`dedup_version`、`role_taxonomy_version`。固定拆分为 30% development / 70% held-out test；test 不用于调参，规则迭代后若污染测试集必须发布新 benchmark version。

`prepare-annotation-batch` 使用目标范围、歧义短词、预测低置信、不同来源与 hard negative 分层抽样。`predicted_*` 只是建议；`gold_*` 必须由人工填写。Portfolio Quality Gate 额外检查 hard/negative 样本数，不把框架完成等同于 Benchmark Ready。

## 10. NextGig enriched 字段边界

- `job_description` 是上游 LLM 摘要，保留为 `source_job_description` 并标记 `description_type=llm_summary`；规则技能提取不把它当原始 JD。可用文本只拼接 responsibilities、minimum qualifications、preferred qualifications 与标题。
- `skills_required` 按 JSON list 读取，以 taxonomy canonical name/alias 做 case-insensitive exact mapping。命中保存 `raw_skill`、`mapping_method=taxonomy_alias_exact`、`mapping_confidence=0.85`；未知技能保持未映射，不模糊猜测。与文本规则重复时优先保留结构化证据。
- 结构化薪资仅在原币种内统一月频：year `/12`、month `×1`、week `×52/12`、day `×260/12`、hour `×2080/12`。后两项是透明工时假设，不是汇率。币种不同的数据不合并；没有经审计 FX 来源时 `fx_*` 为 null，标准人民币薪资字段也为 null。
- `date_posted` 先按 `MM/DD/YYYY`/ISO 解析，再检查不得晚于固定 snapshot cutoff。低于 `minimum_posting_date_coverage=0.70` 时 Trend 不输出强结论，返回 `posting_date_coverage_below_threshold`。
- Qarera 只进行 canonical skill 交集上的描述性排名比较。Rank Difference 使用 SkillWorth 内部 target-scope rank 减 Qarera 发布 rank；绝对差至少 20 标记 divergence warning。该比较不改变内部 Demand，也不证明任一数据集代表中国市场。

## 11. Freehire 中国技术岗位快照与 China SkillWorth

固定快照 `freehire_china_tech_2026_08` 使用 Freehire 文档化、无需认证的公开只读 API，查询实际 country facet `cn` 与审计确认的 15 个技术类别。API 分页响应原样缓存；JSONL artifact、响应 hash、访问时间、查询条件与内容 SHA-256 构成不可变采集证据。后续处理必须走标准 Raw → Bronze → Silver → Role/Skill Normalization → Dedup → Gold → DuckDB 流程。

该快照的分析范围固定为 `china_open_tech_sample`，Source Role 固定为 `china_supplementary`。查询已在来源端限制为技术类别，因此构建该专用快照的网络和 SkillWorth 表时显式使用 `market_scope=all`、`source_scope=all`；这不会改变全局 API 的默认 target/core guardrail。

### 11.1 Market Signal

Market Signal 范围为 0–100，配置位于 `data/reference/china_skillworth.v1.yml`：

```text
Market Signal = 100 × (
  0.30 × Demand Strength
  + 0.20 × Company Breadth
  + 0.20 × Role Breadth
  + 0.15 × Skill Synergy
  + 0.15 × Confidence / 100
)
```

- `Demand Strength = skill canonical job count / snapshot canonical job count`。
- `Company Breadth = companies requiring skill / snapshot companies`。
- Role Breadth 先排除 `other`，只保留每个角色至少 3 条支持；以 inverse-HHI effective roles 除以快照有效角色数，再乘以最多 30 条技能岗位的支持因子。
- Skill Synergy 复用现有技能网络，以归一化 weighted-degree centrality、log edge support、按共现次数加权的 Jaccard、截断到参考值 2.0 的正 PMI 组成；内部权重为 0.40/0.20/0.20/0.20。
- Confidence 直接复用 Data Confidence Engine。Freehire 是单一 supplementary source，不能把 38 个上游 ATS 标签误计为 38 个独立合格市场来源；因此 source-diversity 与 cross-source agreement 保守受限。

Salary 不进入该 Market Signal：快照没有可比较、可审计的人民币月薪覆盖，`salary_signal=null/status=unavailable`。Trend 也不进入：单月截面无法支持时间趋势，`trend_signal=null/status=unavailable`。

### 11.2 China SkillWorth 与敏感性

```text
Learning Efficiency = half_value_hours / (half_value_hours + learning_hours_expected)
China SkillWorth = Market Signal × Learning Efficiency
```

默认 `half_value_hours=160`。学习时长来自版本化技能 taxonomy，是估算值，不是课程承诺。敏感性分析同时改变 Market Signal 权重组合及 half-value（100/240 小时），输出 `rank_min`、`rank_max`、`rank_stability`；排名跨度至少 5 时显示 `Sensitive Ranking Warning`。该分数是当前样本下的市场信号与学习成本折中，不是录用概率、薪资因果效应或完整中国市场排名。

Qarera 仅用于外部排名对照。其岗位、coverage 与 source 不进入任何 SkillWorth 分母、Confidence 或 Source Diversity。

### 11.3 主榜语义、Ranking Robustness 与候选 Gate

`skillworth_eligibility=main` 只授予可形成具体、可验证学习目标的技术；`secondary` 保留岗位相关但方向依赖的基础方法或生产力工具；`excluded` 仍可进入 Requirement Statistics、Skill Network 与 Market Theme，但不进入“下一项具体技术学什么”的主榜。当前明确将 AI、Optimization 等宽泛概念，Word、PowerPoint 等一般办公工具，以及 Agile、Scrum 等一般方法排除出主榜；规则全部来自 taxonomy 配置。

Ranking Robustness 范围 0–100，独立于 Data Confidence。敏感性名次只在相同 eligibility 集合内比较，因此 excluded/secondary 不会改变 main 主榜的 rank width。它按配置权重综合：敏感性排名跨度 30%、岗位支持 20%、公司支持 15%、角色广度 10%、Confidence 15%、学习时长区间不确定性 10%。各分量先相对配置 reference 截断到 0–1；`>=70` 为 robust，`>=50` 为 moderate，其余为 sensitive。它描述排名在模型与输入不确定性下的稳定程度，不是统计显著性或数据真实性概率。

`high_skillworth_candidate` 的当前建议门槛来自本快照分布，而非按期望候选数量反推：main、岗位数至少 10（观测中位数 10.5）、公司数至少 8（观测中位数 8.5）、Confidence 至少 30（观测 P10 约 30.76），并且 Robustness 为 robust 或 moderate。这些是 visual-ready 候选筛选规则，不是生产质量 Gate。

### 11.4 Market Theme 与 Posting Recency

Market Theme 只允许使用 taxonomy 中已存在的 canonical skill 作为主题名，并以配置化 theme → skill IDs 映射计算岗位、公司和角色并集；映射允许重叠，主题不参与主榜排名。当前没有凭空建立 `Cloud`、`Data` 或 `Security` taxonomy 项。

`90d`、`180d`、`365d` 只纳入 `published_at >= snapshot_date - days` 的岗位；`all_active` 纳入快照全部开放岗位。有限窗口缺少发布日期的岗位不进入分母。每个窗口按 `minimum_jobs` 标记 available/insufficient，并重新计算 Demand、Company Breadth、Role Breadth、Confidence、SkillWorth 与敏感性；Skill Synergy 暂沿用同一快照的全局共现网络信号，避免把稀疏窗口网络噪声误当趋势。Posting Recency 不是 Trend，所有窗口的 `trend_signal` 仍为 unavailable。首页窗口按“最短 available 且覆盖至少 80% all-active 岗位”选择，当前结果为 180d。
