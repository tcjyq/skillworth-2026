# NCSS Core Market Candidate 审计报告

审计日期：2026-08-10（Asia/Shanghai）  
上游仓库：`NIHILITY-cool/Spark-employment-platform`  
审计提交：`42a507b093e44b15a62fbd5e6b2891f558125106`  
SkillWorth 来源 ID：`ncss_public_jobs`

## 1. 结论

NCSS 与 SkillWorth 面向大学生的中国技术岗位目标高度相关，但目前只能登记为 `core_market_candidate`，不能导入真实岗位、运行真实 Preflight 或升级为 `core_market`。

阻断原因不是代码许可证，而是数据使用权限。上游仓库代码采用 MIT License；NCSS 官方用户协议同时规定招聘信息的用途边界、禁止商业用途，并声明站点文字和程序未经书面许可不得下载、复制或再使用。MIT License 不会把 NCSS 岗位内容转化为开放数据。当前未发现覆盖 SkillWorth 分析、保存和展示场景的独立开放数据许可证或书面授权。

当前结论：**Gate FAIL（fail closed）**。在许可状态变为 `reviewed` 前，不扩大采集。

## 2. 上游代码审计

### 2.1 已审计范围

- `LICENSE`
- `data_source/configs/field_mapping.json`
- `data_source/configs/ncss_jobs_config.json`
- `data_source/crawlers/base_crawler.py`
- `data_source/crawlers/ncss_job_crawler.py`
- `data_source/parsers/job_parser.py`
- `data_source/scripts/run_crawler.py`
- `data_source/scripts/validate_raw_data.py`
- `data_source/scripts/merge_raw_jobs.py`
- `data_source/scripts/recover_incomplete_run.py`
- `docs/data-source/ncss/`

### 2.2 可参考但未复制的内容

| 内容 | 审计结论 | SkillWorth 处理 |
| --- | --- | --- |
| 原始字段清单 | 与岗位 Data Contract 基本兼容 | 独立实现本地 CSV/JSONL 映射。 |
| `source_job_id` 去重 | 可作为单来源文件合并的最低规则 | 不复用；统一进入 SkillWorth Dedup 1.1.0。 |
| JD 职责/要求分段思路 | 有利于技能抽取 | 本地 Connector 保留三个字段，并组合为分析文本；未复制解析实现。 |
| 缺失率与唯一 ID 检查 | 可作为 Raw 层基础检查 | 由现有 Data Quality、Data Contract 和 Pipeline tests 覆盖。 |

本次没有复制上游实质性源代码，因此没有把其 MIT 代码嵌入仓库。仍在本报告和 `DATA_SOURCES.md` 记录参考来源与提交哈希。若未来复制代码，必须同时保留上游 copyright 和 MIT notice。

### 2.3 不复用的内容

| 内容 | 原因 |
| --- | --- |
| `requests.Session`、浏览器样式 Header 和 Referer | 本阶段明确禁止复制 Session；Connector 必须是本地文件输入。 |
| 列表 API、详情页 HTTP 获取 | NCSS 数据再利用权限未明确，且 SkillWorth 不应实现未授权采集。 |
| 通过地区、类别、学历、薪资和职位类型分片扩大公开结果 | 上游记录显示未筛选第 6 页已要求登录；继续通过组合筛选扩大可见集合可能越过站点表达的访问边界，SkillWorth 不采用该策略。 |
| 原始详情 HTML 批量持久化 | 体量大、内容权利与隐私边界未独立解决。 |
| 上游 merge script | 只按 `source_job_id` first-seen 去重，不含跨来源 Precision-first 规则、字段级融合和完整 provenance。 |
| 上游 validation | 主要检查缺失、重复和 Top 分布；未形成 SkillWorth 所需的角色、技能、薪资、市场范围和 Gate 证据。 |

### 2.4 项目特定耦合与风险

- Endpoint、查询参数、`pagenation` 响应结构和详情页 CSS selector 均与当时的 NCSS 页面实现强耦合。
- `publishDate` 假定为毫秒时间戳；`lowMonthPay/highMonthPay` 假定为 K/月，需要真实样本重新验证。
- JD 分段依赖中文标题词；无标题时把完整 JD 回退为 responsibility，会夸大 responsibility coverage。
- 手机号脱敏只覆盖中国大陆 11 位手机号，不覆盖邮箱、座机、微信号和联系人姓名。
- 重试逻辑未区分 403、429 和临时网络错误，也未处理 `Retry-After`；不适合作为合规采集基础。
- 上游仓库不包含其文档所述 10,834 条原始数据文件、固定 artifact hash 或独立数据许可证，因此该数字只能作为上游自报记录，不能作为 SkillWorth 实测结果。

## 3. License 与数据政策

| 对象 | 状态 | 影响 |
| --- | --- | --- |
| 上游源代码 | MIT License | 可在保留 notice 的条件下复用代码；本次未复制实质性代码。 |
| NCSS 岗位数据 | 未发现开放数据许可证；官方用户协议包含用途和复制限制 | `data_usage_status=permission_required`，禁止导入。 |
| 公开页面可浏览性 | 不等于批量保存、分析或再分发授权 | 不启动小样本或全量采集。 |

官方引用：

- NCSS 用户协议：<https://job.ncss.cn/student/connectUser.html>
- NCSS 职位页：<https://www.ncss.cn/student/jobs/index.html>
- 上游仓库：<https://github.com/NIHILITY-cool/Spark-employment-platform>

## 4. Connector 与字段映射

实现：`NcssPublicExportConnector`。它只接受本地 `.csv` 或 `.jsonl`，不包含 HTTP、Session、Cookie、Token、CAPTCHA、代理或登录逻辑。来源配置默认 `enabled=false`、`mode=manual_import`、`data_usage_status=permission_required`。

| NCSS 导出字段 | SkillWorth 字段 | 处理 |
| --- | --- | --- |
| `source_job_id` | `source_job_id` | 必填；空值记录拒绝。 |
| `job_name` | `job_title` | 必填；原字段仍留在 Bronze。 |
| `company_name` | `company_name` | 必填。 |
| `city` | `city` | 不猜测区县。 |
| `salary_text` | `salary` / Silver `salary_raw` | 交给现有薪资 Parser。 |
| `education_text` | `education` | 交给现有标准化。 |
| `experience_text` | `experience` | 交给现有标准化；上游历史数据可能整体缺失。 |
| `job_description` | `description` | Bronze 保留。 |
| `job_responsibility` | `responsibility` | Bronze 保留。 |
| `job_requirement` | `requirements` | Bronze 保留。 |
| 三个 JD 字段 | `job_description` | 去重后按 description → responsibility → requirements 顺序合并，供现有 Skill Extraction 使用。 |
| `publish_time` | `published_at` | 交给现有日期 Parser。 |
| `source_url` | `source_url` | 仅作 provenance，不用于抓取。 |
| `district`、`industry`、`company_size`、`company_type` | Bronze 原始列 | 原名保留，当前不新增分析旁路。 |

取得书面许可并把配置改为 `data_usage_status=reviewed` 后，导入仍只能走：

```text
Raw artifact → append-only Bronze → Silver → Role Normalization
→ Salary Parsing → Skill Extraction → Dedup/Gold → DuckDB → Analytics
```

## 5. 小样本 Preflight

本阶段没有合法取得可用于 SkillWorth 的 NCSS 样本，也没有从上游仓库复制岗位数据。以下指标不能计算：

| 指标 | 结果 | 原因 |
| --- | --- | --- |
| `raw_jobs` | unavailable | Permission required；未采集。 |
| `valid_jobs` | unavailable | 无合法样本。 |
| `target_market_jobs` | unavailable | 无合法样本。 |
| `target_market_ratio` | unavailable | 无合法样本。 |
| `description_coverage` | unavailable | 无合法样本。 |
| `requirement_coverage` | unavailable | 无合法样本。 |
| `salary_raw_coverage` | unavailable | 无合法样本。 |
| `salary_parseable_coverage` | unavailable | 无合法样本。 |
| `posted_at_coverage` | unavailable | 无合法样本。 |
| `2026_job_ratio` | unavailable | 无合法样本。 |
| `role_distribution` | unavailable | 无合法样本。 |
| `city_distribution` | unavailable | 无合法样本。 |
| `company_distribution` | unavailable | 无合法样本。 |
| `skill_extraction_coverage` | unavailable | 无合法样本。 |
| 目标技术岗数量 | unavailable | 不采用上游自报总量替代本项目计算。 |
| Market Freshness | unavailable | 无可审计的本地 artifact 与 Pipeline 结果。 |

测试中的岗位是明确的合成 fixture，只验证映射和流水线兼容性，不参与上述指标或 Source Gate。

## 6. Source Gate

现有阈值未降低：Target 样本至少 50、Target 比例至少 20%、技能抽取覆盖至少 50%、市场年龄不超过 180 天，并要求允许的 Source Role。

当前 Gate：**FAIL**。

- `SOURCE_ROLE_NOT_CORE_MARKET_ELIGIBLE`：`core_market_candidate` 永远不能直接通过 Gate。
- `DATA_USAGE_PERMISSION_REQUIRED`：导入层在写 Raw/Bronze 前 fail closed。
- Target Sample Size、Target Market Ratio、Skill Coverage 与 Market Freshness 均无真实证据，不能视为通过。

## 7. 是否值得扩大采集

当前：**不值得、也不允许扩大采集**。

下一决策点是取得 NCSS 或数据权利方对“本地保存、聚合分析、技能抽取、结果展示、商业/非商业使用及保留期限”的书面许可，或取得许可明确的官方导出。许可通过后，先运行不超过约定规模的小样本 Preflight；只有真实 Pipeline 结果通过未修改的 Gate，才另行设计完整公开范围内的采集方案。
