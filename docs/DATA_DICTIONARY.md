# 数据字典

## 1. 使用规则

本文件定义 SkillWorth 的领域字段、语义、空值含义与跨层映射。数据模型实现、Arrow/Pydantic schema、Parquet 字段、API response 和 Dashboard 标签必须以本文件为准。

- 字段名使用 `snake_case`；稳定主键使用语义前缀加 UUID/哈希，禁止依赖展示文本作为主键。
- 时间使用带时区的 ISO 8601；若原始时间未携带时区，保存原值、解析状态和假定时区。
- 金额统一为人民币月薪等价值，字段名显式包含 `cny` 与 `monthly`。
- 空值必须区分“来源未提供”“无法解析”“不适用”“被质量规则排除”，不能全部用 `null` 掩盖。
- 除 `data/demo` 的合成/受许可样例外，实际记录不进入版本控制。

## 2. 公共枚举与版本字段

| 字段/枚举 | 含义 | 允许值或格式 |
| --- | --- | --- |
| `data_layer` | 记录所在数据层 | `raw`、`bronze`、`silver`、`gold`。 |
| `authorization_status` | 来源使用状态 | `manual_confirmed`、`public_license_verified`、`authorized`、`disabled`、`revoked`。 |
| `record_status` | 岗位记录可用性 | `valid`、`invalid`、`duplicate_candidate`、`duplicate_merged`、`needs_review`。 |
| `parse_status` | 字段解析状态 | `parsed`、`missing_at_source`、`unparseable`、`not_applicable`、`excluded_by_quality_rule`。 |
| `methodology_version` | 指标公式、阈值、权重版本 | 语义化版本，例如 `1.0.0`。 |
| `taxonomy_version` | 角色/技能 taxonomy 版本 | 语义化版本，例如 `1.0.0`。 |
| `pipeline_version` | 数据转换规则版本 | Git SHA 或语义化版本。 |
| `confidence_band` | 结论的证据等级 | `high`、`medium`、`low`、`insufficient`。 |

薪资解析使用更细的 `salary_parse_status`：`parsed_monthly`、`parsed_monthly_with_months`、`parsed_daily`、`parsed_annual`、`negotiable`、`missing_at_source`、`invalid_range`、`unparseable`。

## 3. 来源与导入实体

### 3.1 `sources`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `source_id` | string | 是 | 稳定来源主键。 |
| `source_name` | string | 是 | 人可读来源名称。 |
| `source_type` | string | 是 | `manual_import`、`public_dataset`、`official_open_data`、`authorized_connector` 或 `demo_fixture`。 |
| `authorization_status` | enum | 是 | 当前接入权限状态。 |
| `license_or_terms_reference` | string | 否 | 许可、条款、授权或导入者声明的引用。 |
| `connector_id` | string | 是 | Connector 类型，如 `manual_import`。 |
| `connector_version` | string | 是 | 导入实现版本。 |
| `enabled_at` | datetime | 否 | 正式启用时间；disabled 来源为空。 |

### 3.2 `ingestion_runs`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `ingestion_run_id` | string | 是 | 单次导入批次主键。 |
| `source_id` | string | 是 | 关联来源。 |
| `imported_at` | datetime | 是 | 导入开始时间。 |
| `raw_artifact_path` | string | 是 | 受控本地原始文件路径或对象引用。 |
| `raw_artifact_sha256` | string | 是 | 原始文件完整性哈希。 |
| `schema_mapping_version` | string | 是 | 本次字段映射版本。 |
| `pipeline_version` | string | 是 | 执行的管道版本。 |
| `row_count_received` | integer | 是 | 接收原始行数。 |
| `row_count_accepted` | integer | 是 | 通过最低 schema 校验的行数。 |
| `coverage_notes` | string | 否 | 已知城市、角色、日期、字段缺失或使用限制。 |

### 3.3 `source_manifest_records`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `source_record_id` | string | 是 | Bronze 记录主键。 |
| `ingestion_run_id` | string | 是 | 关联导入批次。 |
| `native_record_id` | string | 否 | 原来源记录 ID；缺失时不以标题代替。 |
| `observed_at` | datetime | 否 | 系统获取到该记录的时间。 |
| `published_at_raw` | string | 否 | 来源提供的原始发布时间文本。 |
| `raw_record_pointer` | string | 是 | 原始内容中的可追溯位置。 |
| `raw_record_hash` | string | 是 | 单条原始记录完整性哈希。 |

## 4. 岗位数据分层

### 4.1 `bronze_job_records`

Bronze 仅封装来源字段，原则上不修改内容。除 provenance 公共字段外，保留 `raw_payload` 或受控的 `raw_record_pointer`。它不面向 API 或分析层。

### 4.2 `silver_job_candidates`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `silver_job_id` | string | 是 | 标准化候选岗位主键。 |
| `source_record_id` | string | 是 | 对应 Bronze 来源记录。 |
| `source_id` | string | 是 | 提供该记录的平台或受许可数据源。 |
| `source_job_id` | string | 否 | 数据源内岗位 ID；与 `source_record_id` 不同，缺失时保持空值。 |
| `source_url` | string | 否 | 来源声明的岗位 URL；仅作 provenance，不用于抓取或绕过访问控制。 |
| `observed_at` | string | 否 | 来源/导入方记录该岗位时提供的原始观测时间；无法可靠解析时保留原文。 |
| `job_title_raw` / `job_title_normalized` | string | 是/否 | 原始标题与标准化标题。 |
| `role_id` / `role_match_status` | string/enum | 否/是 | taxonomy 映射角色及其状态。 |
| `company_name_raw` / `company_name_normalized` | string | 否/否 | 原始与标准化公司名。 |
| `city_raw` / `city_code` | string | 否/否 | 原始城市和规范城市编码。 |
| `experience_raw` / `experience_band` | string/enum | 否/否 | 原始经验和规范区间。 |
| `education_raw` / `education_band` | string/enum | 否/否 | 原始学历和规范分类。 |
| `job_description_raw` | string | 否 | 受控原始 JD，不默认对外返回。 |
| `published_at` | datetime | 否 | 经解析的岗位发布时间。 |
| `record_status` | enum | 是 | 当前候选记录状态。 |
| `quality_flags` | array[string] | 是 | 解析缺失、异常和人工复核标记。 |

Phase 2 Silver Parquet 还包含以下物理字段：

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `role_taxonomy_version` | string | 是 | 角色映射配置版本。 |
| `city_parse_status` / `city_taxonomy_version` | enum/string | 是 | 城市映射状态和配置版本。 |
| `education_parse_status` | enum | 是 | 学历标准化状态。 |
| `experience_min_years` / `experience_max_years` | number | 否 | 可可靠解析的经验上下界。 |
| `experience_parse_status` | enum | 是 | 经验标准化状态。 |
| `salary_raw` | string | 否 | 原始薪资文本，任何解析结果都不能覆盖它。 |
| `salary_min_monthly` / `salary_max_monthly` | number | 否 | 人民币月薪等价值上下限。 |
| `salary_mid_monthly` | number | 否 | 月薪等价值区间中点。 |
| `salary_annualized` | number | 否 | 按已知薪数或方法论换算的标准年化等价值。 |
| `salary_months` | integer | 否 | 明确薪数；普通月薪未知时为空，年薪/日薪换算基数为 12。 |
| `salary_parse_status` | enum | 是 | 薪资解析状态。 |
| `published_at_raw` / `published_at` | string/date | 否 | 原始日期文本和标准化日期。 |
| `date_parse_status` | enum | 是 | 日期解析状态。 |
| `pipeline_version` | string | 是 | 生成 Silver 记录的 Pipeline 版本。 |

### 4.3 `canonical_jobs`（Gold / `canonical_jobs.parquet`）

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `canonical_job_id` | string | 是 | 去重后的规范岗位主键。 |
| `canonical_silver_job_id` | string | 是 | 代表性 Silver 记录。 |
| `company_name_normalized` | string | 否 | 代表记录的规范公司名；不是跨企业实体解析结果。 |
| `job_title_normalized` | string | 否 | 代表记录的规范岗位标题。 |
| `role_id` | string | 否 | 规范岗位角色。 |
| `city_code` | string | 否 | 规范城市编码。 |
| `experience_band` | enum | 否 | 规范经验区间。 |
| `education_band` | enum | 否 | 代表 Silver 记录的规范学历要求；用于分析切片，无法可靠解析时为空。 |
| `published_at` | string | 否 | 代表 Silver 记录的已解析发布日期；Warehouse 转换为日期后用于月度聚合。 |
| `salary_mid_monthly` | number | 否 | 代表 Silver 记录的月薪等价值中点。 |
| `salary_parse_status` | enum | 否 | 代表 Silver 记录的薪资解析状态。 |
| `group_size` | integer | 是 | 归入该规范岗位的 Silver 记录数。 |
| `deduplication_status` | enum | 是 | `unique` 或 `merged`。 |
| `canonicalization_method` | enum | 是 | 代表记录与组内记录所采用的最高等级方法。 |
| `deduplication_rule_version` | string | 是 | 生成该实体的规则版本。 |

### 4.4 `job_source_map`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `canonical_job_id` | string | 是 | 关联 Gold 规范岗位。 |
| `silver_job_id` | string | 是 | 被保留的原始标准化岗位 ID。 |
| `source_record_id` | string | 是 | 原始来源记录。 |
| `source_id` | string | 是 | 原始平台或数据源。 |
| `source_job_id` | string | 否 | 原始平台岗位 ID。 |
| `source_url` | string | 否 | 原始平台岗位 URL。 |
| `observed_at` | string | 否 | 原始观测时间文本。 |
| `match_method` | enum | 是 | `unique`、`level_1_exact`、`level_2_fuzzy_title` 或 `level_3_simhash_description`。 |
| `match_score` | number | 否 | Level 2 为标题 ratio；Level 3 为描述 SimHash 相似度；`unique` 为空。 |
| `match_reason` | string | 是 | 可审计的合并依据。 |
| `deduplication_rule_version` | string | 是 | 执行版本。 |

### 4.5 DuckDB Warehouse 核心表与 Views

Warehouse 由 `python -m app.cli build-warehouse` 从 Parquet 幂等重建。`jobs` 对应 `canonical_jobs` 的分析快照；`companies` 从非空规范公司名派生稳定 `company_id`；`sources` 从 `job_source_map.source_id` 汇总，不对未提供的来源名称或授权状态作推断。

| 对象 | 主键/粒度 | 说明 |
| --- | --- | --- |
| `jobs` | `canonical_job_id` | 每行一个 Gold 规范岗位，包含公司、角色、城市、经验、发布日期与薪资分析字段。 |
| `companies` | `company_id` | 每行一个可规范化的公司名；不进行跨名称实体合并。 |
| `skills` | `skill_id` | `skills.parquet` 的版本化技能快照。 |
| `job_skills` | `(canonical_job_id, silver_job_id, skill_id)` | Silver 抽取关系通过 `job_source_map` 映射到 Gold；保留来源岗位粒度以支持来源分析。 |
| `sources` | `source_id` | 来源岗位数、贡献的规范岗位数和首次/最后观测时间。 |
| `job_source_map` | `silver_job_id` | Phase 4 映射快照及其去重审计字段。 |

Analysis Views：`role_summary`、`city_summary`、`source_summary`、`skill_demand`、`source_skill_demand`、`monthly_skill_demand`、`salary_distribution`、`skill_salary`、`skill_role` 和 `skill_city`。其中所有岗位分母均是明确标注的 `canonical_job_id` 或 `silver_job_id` 去重计数；`source_skill_demand` 使用来源岗位粒度，不能解释为全市场需求。Phase 6 的 `skillworth_analytics` 查询模块以这些事实表为输入，提供参数化市场指标，不写入派生数字。

## 5. 薪资实体

### `job_salary`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `canonical_job_id` | string | 是 | 关联 Gold 规范岗位。 |
| `salary_raw` | string | 否 | 原始薪资文本。 |
| `currency_code` | string | 否 | 原始或识别出的 ISO 币种。 |
| `salary_period_raw` | string | 否 | 月、年、日等来源周期。 |
| `salary_months` | number | 否 | 明确薪数或年薪/日薪换算基数；普通月薪未声明时为空。 |
| `salary_min_monthly` | decimal | 否 | 解析后的人民币月薪等价值下限。 |
| `salary_max_monthly` | decimal | 否 | 解析后的人民币月薪等价值上限。 |
| `salary_mid_monthly` | decimal | 否 | 分析使用的月薪等价值中点。 |
| `salary_annualized` | decimal | 否 | 标准年化等价值，不等于实际总包。 |
| `salary_parse_status` | enum | 是 | 解析/缺失/排除状态。 |
| `salary_quality_flags` | array[string] | 是 | 币种、周期、不确定性或异常标记。 |

## 6. Taxonomy 与技能抽取实体

### 6.1 `roles`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `role_id` | string | 是 | 稳定角色 ID。 |
| `role_name` | string | 是 | 规范角色名。 |
| `role_family` | string | 是 | 上层角色族。 |
| `taxonomy_version` | string | 是 | taxonomy 版本。 |
| `status` | enum | 是 | `active`、`deprecated`、`unclassified`。 |

### 6.2 `skills`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `skill_id` | string | 是 | 稳定技能 ID。 |
| `canonical_name` | string | 是 | 规范展示名。 |
| `category` | string | 是 | `programming`、`database`、`data_analysis`、`data_engineering`、`ai_ml`、`frontend`、`backend`、`devops`、`cloud`、`visualization`、`testing`、`product`、`office`、`statistics` 或 `other`。 |
| `aliases` | array[string] | 是 | 别名、缩写与中英文变体。 |
| `learning_hours_min` | integer | 是 | 学习成本最小情景，单位小时。 |
| `learning_hours_expected` | integer | 是 | 默认学习成本估计，单位小时。 |
| `learning_hours_max` | integer | 是 | 学习成本最大情景，单位小时。 |
| `learning_cost_source` | string | 是 | 学习成本估计方法或来源标识。 |
| `notes` | string | 是 | 口径、歧义和维护说明。 |
| `skill_type` | enum | 是 | 技能语义类型；允许值为 taxonomy 定义的 18 类，例如 `programming_language`、`database`、`broad_concept`。 |
| `skillworth_eligibility` | enum | 是 | `main`、`secondary` 或 `excluded`；仅 main 进入默认主榜。 |
| `skillworth_reason` | string | 是 | 当前语义资格的可审计原因。 |
| `taxonomy_version` | string | 是 | 词典版本。 |

约束：`learning_hours_min <= learning_hours_expected <= learning_hours_max`；`skill_id` 与忽略大小写后的 `canonical_name` 均唯一。Phase 3 的 source of truth 是 `data/taxonomy/skills.yml`，`skills.parquet` 是其可计算快照。

### 6.3 `job_skills`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `silver_job_id` | string | 是 | Phase 3 关联 Silver 岗位；Gold 去重完成后通过 `job_source_map` 映射为 `canonical_job_id`。 |
| `skill_id` | string | 是 | 关联技能。 |
| `canonical_skill` | string | 是 | 抽取时 taxonomy 中的规范技能名。 |
| `matched_text` | string | 是 | JD 或标题中实际命中的原文证据。 |
| `extraction_method` | enum | 是 | Phase 3 为 `rule_canonical`、`rule_alias` 或 `rule_short_context`；接口预留 `llm_fallback`。 |
| `confidence` | number | 是 | 版本化规则强度，范围 `[0,1]`，不是统计概率。 |
| `taxonomy_version` | string | 是 | 匹配使用的词典版本。 |

唯一性语义为 `(silver_job_id, skill_id)`；一次岗位文本中重复出现同一技能不会生成重复关系。Phase 4 后，Skill Demand 必须通过 `job_source_map.silver_job_id → job_skills.silver_job_id` 映射到 `canonical_job_id`，以 Gold 规范岗位作为分母；不得直接按 Silver 关系表计数。

## 7. 分析输出契约

### 7.1 `metric_metadata`

所有分析结果共用以下 metadata：

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `metric_name` | string | 是 | 稳定指标名，如 `skill_demand`。 |
| `methodology_version` | string | 是 | 公式/配置版本。 |
| `data_version` | string | 是 | Gold 数据版本或快照 ID。 |
| `slice` | object | 是 | 角色、城市、时间、来源等筛选条件。 |
| `sample_size` | integer | 是 | 该结果实际分母。 |
| `source_count` | integer | 是 | 贡献有效记录的来源数。 |
| `observed_date_range` | object | 是 | 最早和最晚观测/发布时间。 |
| `confidence_score` | number | 是 | 范围 `[0,100]`。 |
| `confidence_level` | enum | 是 | `High`、`Medium` 或 `Low`。 |
| `limitations` | array[string] | 是 | 当前切片的已知限制。 |

### 7.2 核心指标字段

| 指标 | 主字段 | 语义 |
| --- | --- | --- |
| Skill Demand | `job_coverage_rate`、`job_count` | 含技能的 Gold 有效岗位占比与数量。 |
| Platform-balanced Demand | `balanced_coverage_rate`、`contributing_source_count` | 各合格来源覆盖率的等权平均。 |
| Adjusted Salary Association | `association_percent`、`confidence_interval`、`model_diagnostics` | 控制变量后与技能共现的薪资关联，非因果。 |
| Skill Trend | `monthly_coverage_rate`、`change_3m`、`change_6m`、`trend_slope` | 按月岗位覆盖变化。 |
| Co-occurrence Edge | `skill_a_id`、`skill_b_id`、`co_occurrence_count`、`jaccard`、`pmi` | 技能对共同出现与关联强度。 |
| Personal Coverage | `average_coverage`、`threshold_qualified_rate` | 用户技能对目标岗位集合的加权覆盖，不是就业概率。 |
| Marginal Gain | `coverage_gain`、`threshold_gain` | 新增一个候选技能后的覆盖提升。 |
| Market Value | `market_value_score`、`component_scores` | 市场信号综合分，与用户无关。 |
| Personal ROI | `personal_roi_score`、`component_scores` | 用户/角色/预算上下文中的学习优先级，非财务回报。 |
| Optimizer Step | `step`、`skill_id`、`expected_hours`、`cumulative_hours`、`marginal_gain` | 启发式学习路径的一步。 |

### 7.3 Phase 6 Analytics Module 输出

`packages/analytics/src/skillworth_analytics` 是 Warehouse 的只读查询边界。全部结果均包含 `AnalyticsMetadata`（方法版本、筛选条件、去重岗位样本量、来源数和实际发布日期范围）。

| 方法 | 记录字段 | 粒度 |
| --- | --- | --- |
| `skill_demand` | `skill_id`、`job_count`、`job_coverage`、`source_count`、`sample_size` | 技能 × 过滤后的 Gold 岗位集。 |
| `platform_balanced_demand` | `pooled_coverage`、`platform_balanced_coverage`、`platform_breakdown` | 技能；breakdown 为来源岗位粒度。 |
| `salary_by_skill` | `median`、`p25`、`p75`、`sample_size`、`salary_coverage`、`status` | 技能 × 有可用薪资的 Gold 岗位；无薪资样本时 `status=unavailable` 且 coverage 为 null。 |
| `skill_by_role` / `skill_by_city` / `skill_by_experience` | `dimension_value`、`job_count`、`job_coverage`、`sample_size` | 技能 × 指定维度值。 |
| `source_bias_analysis` | `dimension`、`source_id`、`value`、`job_count`、`job_coverage`、`sample_size` | 来源岗位 × role/skill/city/experience 构成。 |

### 7.4 Phase 7 Advanced Analytics 输出

| 对象/方法 | 主字段 | 语义 |
| --- | --- | --- |
| `skill_trend` 月度点 | `month`、`job_count`、`sample_size`、`skill_job_coverage`、`rolling_mean` | 技能 × 月；覆盖率分母为当月 Gold 岗位数。 |
| `SkillTrendRecord` | `change_3m`、`change_6m`、`trend_slope`、`volatility`、`classification`、`conclusion_strength` | 技能趋势摘要；低样本或规则不匹配时分类为空。 |
| `AdjustedSalaryAssociationRecord` | `coefficient`、`percentage_approximation`、两类置信区间、`p_value`、`sample_size`、`status`、`diagnostics` | 控制变量后的薪资条件关联；不可解释为因果效应。 |
| `skill_graph_nodes.parquet` | `skill_id`、`job_count`、`job_coverage`、`degree`、`weighted_degree`、`community_id` | 一个技能节点。 |
| `skill_graph_edges.parquet` | `skill_a_id`、`skill_b_id`、`cooccurrence_count`、`jaccard`、`pmi`、`weight` | 一条达到配置支持门槛的无向技能边。 |

节点和边均包含 `methodology_version`、`config_version`；网络输出可由同一 Warehouse 快照与配置幂等重建。

### 7.5 Phase 8 Data Confidence 输出

`DataConfidenceResult` 是任一市场指标可复用的证据质量外层，不改变被评估指标本身。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `confidence_score` | number | 配置化分量的适用权重归一化总分，范围 `[0,100]`。 |
| `confidence_level` | enum | `High`、`Medium` 或 `Low`。 |
| `confidence_components` | object | 固定包含 `sample_size`、`source_diversity`、`data_freshness`、`salary_coverage`、`cross_source_agreement`。 |
| `warnings` | array[object] | 稳定 `code`、所属 `component` 和可显示 `message`。 |
| `methodology_version` | string | Data Confidence 方法标识与版本。 |
| `config_version` | string | `data_confidence.v1.yml` 的规则版本。 |

每个 component 包含 `component_score`、`raw_value`、`weight`、`effective_weight`、`applicable`、`available` 和 `explanation`。非薪资指标的薪资分量为 `applicable=false`、`component_score=null` 并排除加权；适用但缺少跨平台证据时为 `available=false`、保守 0 分，并必须结合 warning 解读。

`ConfidenceEvidence` 输入使用去重样本量、各来源样本量、最新观测日期、显式评估日期、薪资可用样本数和各平台同口径指标值。`platform_metric_values` 必须落在 `[0,1]`；薪资可用样本数不得超过总样本数。

### 7.6 Phase 9 Personal Skill Opportunity 输出

`PersonalSkillOpportunityResult` 表示指定用户技能和目标岗位切片下的技能覆盖机会，不表示录取、就业或 Offer 概率。

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `status` | enum | `ok`、`no_target_jobs` 或 `no_skill_evidence`。 |
| `current_average_fit` | number/null | 可计算目标岗位的平均 Skill Fit。 |
| `current_threshold_coverage` | number/null | 当前 Fit 大于等于请求阈值的岗位占比。 |
| `target_job_count` | integer | 筛选命中的全部 Gold 目标岗位数。 |
| `sample_size` | integer | 至少有一个抽取技能、实际进入 Fit 计算的岗位数。 |
| `jobs_without_extracted_skills` | integer | 因技能集合为空而不进入 Fit 分母的目标岗位数。 |
| `candidates` | array[object] | 用户尚未掌握的候选技能边际机会记录。 |
| `confidence` | object | 当前 cohort 的 Phase 8 Data Confidence。 |

每个候选记录包含 `skill_id`、`canonical_name`、`category`、`new_average_fit`、`new_threshold_coverage`、`average_fit_gain`、`threshold_coverage_gain`、`jobs_crossing_threshold`、`sample_size` 和候选专属 `confidence`。所有 Fit 和 gain 范围均为 `[0,1]`；UI 可格式化为 percentage points，但不得改写底层值。

### 7.7 Phase 10 Decision 与 Optimizer 输出

| 对象 | 关键字段 | 含义 |
| --- | --- | --- |
| `MarketValueResult` | `market_value_score`、`components`、`warnings` | 整体市场价值信号；每个 component 展示原始值、归一化分、权重和贡献。 |
| `PersonalROIResult` | `personal_roi_score`、`components`、`learning_hours` | 对具体用户的学习优先级，非财务回报率。 |
| `LearningHoursReport` | min/expected/max、`effective_expected_hours`、来源、覆盖状态、免责声明 | 学习时间估算；用户覆盖不修改 taxonomy 原值。 |
| `SensitivityResult` | `scenario_names`、`overall_rank_stability`、`records` | 配置化权重场景下的排名稳定性。 |
| `SensitivitySkillRecord` | `baseline_rank`、`rank_min`、`rank_max`、`rank_range`、`rank_stability`、`warning` | 单项技能排名波动；高敏感时显示固定 warning。 |
| `LearningOptimizerStep` | `step`、技能、`estimated_hours`、`cumulative_hours`、`marginal_fit_gain`、`cumulative_fit`、`threshold_coverage`、`reason` | 每次重算边际收益后选中的一步。 |

`ScoreComponent` 包含 `raw_value`、`normalized_score`、`configured_weight`、`effective_weight`、`contribution`、`available` 和 `explanation`。所有权重来源于 `decision_scores.v1.yml`。

## 8. 用户输入实体

### `opportunity_request`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `current_skills` | array[string] | 是 | 用户已有技能 ID；允许空数组，不允许空值或重复值。 |
| `target_role` | string | 是 | 目标 `role_id`。 |
| `city` | string | 否 | 可选 `city_code` 精确筛选。 |
| `experience` | string | 否 | 可选 `experience_band` 精确筛选。 |
| `match_threshold` | number | 是 | Skill Fit 阈值，范围 `[0,1]`。 |

### `learning_optimizer_request`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `current_skills` | array[string] | 是 | 用户当前技能，允许空数组。 |
| `target_role` | string | 是 | 目标角色。 |
| `hour_budget` | number | 是 | 严格大于 0 的学习小时预算。 |
| `city` / `experience` | string | 否 | 可选市场切片。 |
| `match_threshold` | number | 否 | 为空时使用配置默认值。 |
| `learning_hours_overrides` | object | 否 | skill ID 到用户 expected hours 的正数覆盖。 |

### `portfolio_request`

| 字段 | 类型 | 必填 | 含义 |
| --- | --- | ---: | --- |
| `target_role_id` | string | 是 | 用户目标角色。 |
| `current_skill_ids` | array[string] | 是 | 用户确认拥有的技能集合。 |
| `city_codes` | array[string] | 否 | 市场筛选城市；为空表示文档声明的默认范围。 |
| `hour_budget` | number | 是 | 总学习时间预算，必须大于 0。 |
| `learning_cost_overrides` | object | 否 | 用户覆盖的技能预期小时数；不改写全局基准。 |
| `data_slice` | object | 否 | 时间和来源筛选；必须写入结果 metadata。 |

## 9. API 契约

Phase 11 API 的市场筛选字段为 `role_id`、`city_code`、`experience_band`、`education_band`、重复的 `source_id` 和 `published_from`/`published_to`。它们映射到统一的 `AnalyticsFilters`，每个分析响应保留 `metadata.filters`、`sample_size`、`source_count` 和 `methodology_version`。

错误响应统一为 `{"error": {"code", "message", "details"}}`。无效请求返回 `422`，不存在的技能或岗位返回 `404`，缺失 DuckDB、技能图谱或质量报告返回 `503`。Portfolio API 复用 `OpportunityRequest` 和 `LearningOptimizerRequest`，其中 Skill Fit 仍只表示 Skill Coverage，不表示录取或就业概率。

## 10. 变更流程

新增、删除或改变字段语义时必须：

1. 更新本数据字典和对应 taxonomy/methodology 版本；
2. 更新 Pydantic/Arrow/API 契约与迁移策略；
3. 更新 fixture、测试和 Dashboard 文案；
4. 记录向后兼容性与重新处理范围。

## 11. Public Dataset Connector 与 provenance 扩展

### 11.1 Source 配置字段

启用的 `public_dataset` 除通用 `SourceAdapterConfig` 字段外，必须提供：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `dataset_url` | HTTPS URL | 数据集说明页。 |
| `dataset_version` | string | 被审查和固定的发布版本。 |
| `download_url` | HTTPS URL | 公开下载地址，不包含凭据。 |
| `license_name` | string | 明确许可证标识。 |
| `license_url` | HTTPS URL | 许可证原文。 |
| `expected_sha256` | 64 位 hex | 允许导入的原始 artifact 内容哈希。 |

缺少任一字段时，`enabled=true` 的 Public Dataset 配置无法通过 Pydantic 边界校验。

### 11.2 Source Import Manifest 扩展

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `raw_record_count` | integer | Connector 读取的原始文件总行数。 |
| `record_count` | integer | 通过数据集 scope 规则并写入 Bronze 的行数。 |
| `rejected_record_count` | integer | 未进入该市场范围的行数；不等价于数据错误。 |
| `connector_warnings` | array[string] | 编码、字段替代、范围过滤等可审计 warning。 |
| `stored_raw_artifact_path` | path/null | 按 SHA-256 命名的 append-only 原始文件快照。旧 manifest 可为空。 |

`raw_artifact_path` 保留操作者提供的原路径；`stored_raw_artifact_path` 是 Pipeline 控制的数据根目录内快照。两者均不得用作业务字段来源，分析只能从 Bronze 继续向下处理。

## 12. Dataset Mode Report

`DatasetModeReport` 是一次完整模式构建的机器可读数据报告。行数口径如下：

| 字段 | 粒度 | 含义 |
| --- | --- | --- |
| `raw_rows` | 原始 artifact | 读取到的全部源行。 |
| `in_scope_rows` | Bronze | 满足数据集 scope 并写入 Bronze 的行。 |
| `excluded_out_of_scope_rows` | 原始 artifact | 未满足 scope 的行。 |
| `valid_rows` | Silver | `record_status=valid` 的行。 |
| `canonical_rows` | Gold/Warehouse | 去重后的规范岗位数。 |

`date_range`、`salary_coverage`、`skill_coverage`、`role_distribution`、`city_distribution`、`source_distribution` 和 `analytics_check` 均使用统一结构：

| 字段 | 类型 | 含义 |
| --- | --- | --- |
| `status` | `available` / `unavailable` | 指标是否被该数据支持。 |
| `value` | any/null | 真实计算值；不可用时必须为 null。 |
| `reason` | string/null | 不可用原因。 |
| `available_rows` | integer/null | 对该指标有值的行数。 |
| `sample_size` | integer/null | 指标分母。 |

真实的 0 与 `unavailable` 不可互换。当前 Real 数据薪资行数为 0，因此 `salary_coverage.status=unavailable`、`value=null`，不能填 0%、估算值或 Demo 值。

`logic_fingerprint` 包含 Pipeline、Role/City/Skill taxonomy、Warehouse objects 和 Analytics methodology 版本。`ModeComparisonReport.business_logic_consistent` 只比较这些逻辑契约，不要求 Demo 与 Real 的市场数值相同。

## 11. Gold Benchmark 数据契约

### 11.1 Role Gold Record

| 字段 | 类型 | 空值 | 说明 |
| --- | --- | --- | --- |
| record_id | string | 否 | 对应 Silver 记录的稳定 ID。 |
| title | string | 否 | 标注时可见的原始岗位标题。 |
| description_excerpt | string | 否 | 去除无关个人信息后的 JD 摘要。 |
| source | string | 否 | 来源 ID。 |
| gold_role | enum | 否（Gold） | 人工仲裁后的 Role；pending batch 中为 null。 |
| annotator_notes | string | 否 | 判断依据与边界说明。 |
| split | enum | 否 | `development` 或 `held_out_test`。 |

### 11.2 Skill Gold Record

`gold_skills` 为人工确认的稳定 `skill_id` 集合；`negative_terms` 记录文本中出现但不应提取为技能的歧义词；`language` 为 zh、en、mixed 或 other。其余字段见 `data/benchmarks/skills/schema.json`。

### 11.3 Dedup Gold Pair

`gold_duplicate` 是人工确认的 pair 真值；`difficulty` 为 easy、medium、hard；`source_pair` 保留左右来源组合；`split` 与其他 Benchmark 相同。pending batch 的 `gold_duplicate` 为 null，不能送入 evaluator。

## 12. Canonical Job 新增字段

| 字段 | 类型 | 空值 | 说明 |
| --- | --- | --- | --- |
| title_source_silver_job_id | string | 否 | Canonical title 的来源 Silver ID。 |
| description_source_silver_job_id | string | 否 | Canonical description 的来源 Silver ID。 |
| job_title_raw | string | 是 | 按标题融合规则选出的原始标题。 |
| job_description_raw | string | 是 | 信息量最高的组内 JD。 |
| salary_observations | list&lt;struct&gt; | 否 | 每个组成员的 source、raw_salary、normalized_salary、observed_at。 |
| canonical_salary | float | 是 | 无冲突时的跨来源兼容月薪中点；冲突或无有效薪资时为 null。 |
| salary_source_count | integer | 否 | 提供有效标准化薪资的不同来源数。 |
| salary_conflict_flag | boolean | 否 | 跨来源相对跨度是否超过配置阈值。 |
| first_posted_at | date string | 是 | 最早可靠发布日期。 |
| first_seen_at | timestamp string | 是 | 最早观测时间。 |
| last_seen_at | timestamp string | 是 | 最晚观测时间。 |
| canonical_merge_version | string | 否 | 字段级融合规则版本。 |

### 12.1 Silver 市场范围与原生薪资字段

| 字段 | 类型 | 空值 | 说明 |
| --- | --- | --- | --- |
| salary_currency | string | 是 | 来源声明币种，如 `HKD`；不等于分析基准币种。 |
| salary_native_min_monthly | float | 是 | 来源结构化月薪下限，保持原生币种。 |
| salary_native_min_hourly | float | 是 | 来源结构化时薪下限，保持原生币种。 |
| salary_native_min_daily | float | 是 | 来源结构化日薪下限，保持原生币种。 |
| market_scope | enum | 否 | `target`、`possible`、`non_target`；规则审计范围，不是 Role Gold Label。 |
| market_scope_method | string | 否 | 当前为 `configured_title_rules`。 |
| market_scope_version | string | 否 | `target_market.v1.yml` 的版本。 |

`salary_observations` struct 扩展为 `source`、`raw_salary`、`normalized_salary`、`currency`、`native_min_monthly`、`observed_at`。外币原生数值仅用于覆盖率与冲突审计，不进入 `canonical_salary`。

兼容字段 `published_at` 等于 `first_posted_at`，`salary_mid_monthly` 等于无冲突的 `canonical_salary`；发生冲突时二者均为空，防止下游薪资分析误用强制融合值。

## 13. Metric Guardrail 与 Freshness 字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| analysis_role | enum | `core_market`、`core_market_candidate`、`supplementary_market`、`engineering_validation`、`historical_reference`、`external_market_benchmark`。candidate 不参与核心指标，外部基准永不进入岗位市场分母。 |
| data_usage_status | enum | `reviewed`、`permission_required`、`restricted`。非 `reviewed` 来源在 Raw/Bronze 写入前被拒绝。 |
| core_market_eligible | boolean | 当前切片下是否满足 Source Eligibility Gate。 |
| ineligibility_reasons | list[string] | 未通过的配置化门禁原因。 |
| raw_source_count | integer | 当前证据中有记录的原始来源数。 |
| eligible_source_count | integer | 满足当前指标可比门禁的来源数。 |
| effective_source_count | float | eligible 来源权重的 `1 / Σ(w²)`。 |
| latest_observed_at | date | 最新导入/观测日期。 |
| pipeline_age_days | integer | Pipeline Freshness 天数。 |
| latest_posted_at | date | 最新岗位实际发布日期。 |
| median_posting_age_days | float | 岗位年龄中位数。 |
| p75_posting_age_days | float | 岗位年龄 P75。 |
| posting_date_coverage | float | 有发布日期岗位数 / 分析岗位数。 |
| confidence_cap | float | 配置化证据上限，不是原始加权分。 |

Benchmark pending batch 中 `predicted_role`、`predicted_skills`、`predicted_duplicate` 仅为标注建议；`gold_role`、`gold_skills`、`gold_duplicate` 为 null，直到人工确认。字段 `annotator`、`annotation_notes`、`difficulty`、`split` 均为正式契约。

## 14. NextGig Silver 语义字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| description_type | string | NextGig 固定为 `llm_summary`，说明来源描述不是原始 JD。 |
| source_job_description | string | 上游 LLM 摘要的原值，仅供 provenance/审计。 |
| skill_evidence_source | string | 技能抽取证据来源说明。 |
| structured_skills_raw | JSON string | 上游 `skills_required` 原值；未映射条目不猜测。 |
| raw_skill | string | 结构化技能的原始词面。 |
| mapping_method | string | 当前结构化映射为 `taxonomy_alias_exact`。 |
| mapping_confidence | float | 来源结构化技能映射置信度；不等于人工 Gold 正确率。 |
| evidence_type | string | `source_structured_skill` 或 `qualification_or_title_text`。 |
| country_raw | string | 上游派生国家原值。 |
| geography_source | string | NextGig 固定为 `derived`。 |
| salary_raw_structured | JSON string | min/max/currency/rate unit 的原始结构。 |
| salary_currency_original | string | 原始币种。 |
| salary_rate_unit_original | string | 原始计薪周期。 |
| salary_min/max/mid_normalized | float | 原币种内的月频值；不是人民币。 |
| salary_normalization_method | string | 月频转换规则或失败状态。 |
| fx_rate / fx_rate_date / fx_source | nullable | 当前固定 null；禁止静默换汇。 |

## 15. Freehire snapshot 与 China SkillWorth 字段

### 15.1 Snapshot provenance

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `snapshot_id` | string | 固定快照标识；当前为 `freehire_china_tech_2026_08`。 |
| `api_query` / `query_scope` | string/object | 文档化 API 查询与 country/category 范围。 |
| `api_accessed_at` | datetime | 单页响应实际访问时间。 |
| `source_payload_sha256` | string | 单条上游 JSON payload 的 SHA-256。 |
| `upstream_source` | string | Freehire 保留的原 ATS/catalogue provenance；不是独立合格市场平台。 |
| `upstream_external_id` | nullable string | 上游外部岗位标识。 |
| `source_company_slug` | nullable string | Freehire 精确 company slug。 |
| `content_sha256` | string | 固定 JSONL artifact 的 SHA-256。 |
| `raw_job_count` | integer | API 页面中观察到的原始行数，含重复与无效行。 |
| `valid_job_count` | integer | 通过 API schema 后按 `public_slug` 唯一化的行数。 |
| `pipeline_job_count` | integer | 进入 Bronze/Silver Data Contract 的行数。 |
| `rejected_job_count` | integer | API schema 无效行数；不包含重复 slug。 |

### 15.2 `china_skillworth_summary`

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `job_count` / `job_coverage` | integer/float | 要求技能的 canonical jobs 及其占快照岗位比例。 |
| `company_count` / `company_coverage` | integer/float | 要求技能的公司数及其占快照公司比例。 |
| `role_count` / `role_breadth_score` | integer/float | 达到支持阈值的角色数及透明 breadth 分数。 |
| `network_centrality` / `synergy_score` | float | 现有共现网络派生信号，范围 0–1。 |
| `market_signal` | float | 配置化 Market Signal，范围 0–100。 |
| `market_signal_components` | JSON | 每个分量的原始值、归一化值、权重、贡献和解释。 |
| `learning_hours_min/expected/max` | float | taxonomy 学习时长区间估算，不是客观课程承诺。 |
| `learning_efficiency` | float | 学习时长折减因子，范围 (0,1]。 |
| `skillworth_score` | float | Market Signal × Learning Efficiency，范围 0–100。 |
| `confidence` / `confidence_components` | float/JSON | 现有 Confidence Engine 总分与分量。 |
| `salary_signal` / `salary_signal_status` | nullable/status | 本快照固定为 null / `unavailable`。 |
| `trend_signal` / `trend_signal_status` | nullable/status | 单快照固定为 null / `unavailable`。 |
| `rank_min` / `rank_max` / `rank_stability` | integer/integer/float | 配置化敏感性场景中的排名范围与稳定度。 |
| `sensitive_ranking_warning` | nullable string | 排名跨度达到阈值时为 `Sensitive Ranking Warning`。 |
| `market_scope` / `source_role` | string | `china_open_tech_sample` / `china_supplementary`。 |

`GET /market/china-skillworth` 的响应元数据另含 `access_date`（nullable date）：Real Mode 取冻结 manifest 的 `acquired_at` / `access_date`，Demo Mode 取版本化合成 fixture manifest 的 `imported_at`。该字段只描述数据访问/导入日期，不参与指标或排名计算。

### 15.3 `china_skillworth_visual_ready`

粒度为 `skill_id × recency_window × role_id`；`role_id=null` 表示全角色。该表是 API 的只读 visual-ready 来源，不替代 `china_skillworth_summary` 的基础审计记录。

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `skill_type` / `skill_category` | enum/string | taxonomy 语义类型与原始类别。 |
| `skillworth_eligibility` / `eligibility_reason` | enum/string | 主榜资格与配置原因。 |
| `job_count` / `job_coverage` | integer/float | 当前时间窗及角色切片的岗位支持与分母占比。 |
| `sample_size` | integer | 当前时间窗及角色切片的岗位分母。 |
| `company_count` / `company_coverage` | integer/float | 当前切片公司支持与分母占比。 |
| `company_sample_size` | integer | 当前时间窗及角色切片的公司分母。 |
| `role_count` / `role_breadth` | integer/float | 达到支持阈值的角色数与 breadth 分数。 |
| `skillworth_rank` | nullable integer | 仅 main 技能按当前切片 SkillWorth score 排名；secondary/excluded 为 null。 |
| `sensitivity_rank_min/max` | integer | 当前切片全部观测技能在配置场景中的名次范围。 |
| `ranking_robustness` / `robustness_level` | float/enum | 排名稳健性分数与 `robust`、`moderate`、`sensitive`。不得解释为 Confidence。 |
| `high_skillworth_candidate` | boolean | 是否通过配置化主榜候选门槛。 |
| `market_theme` | nullable string | 该技能所属的一个或多个配置化主题，以 `; ` 分隔。 |
| `recency_window` | enum | `90d`、`180d`、`365d` 或 `all_active`。 |
| `window_status` | enum | `available` 或 `insufficient`。 |
| `salary_signal_status` / `trend_signal_status` | status | 当前固定 `unavailable`，不得填充占位分数。 |

### 15.4 `china_skillworth_market_themes`

每行是 `market_theme × recency_window`，提供主题成员技能岗位并集的 `job_count/coverage`、公司并集和角色数。主题名必须已存在于 taxonomy，不参与具体技术主榜。
