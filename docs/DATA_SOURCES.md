# 数据来源与合规接入说明

## 1. 基本政策

SkillWorth 的目标是分析合规获得的劳动力市场数据，不是绕过招聘平台访问控制。数据源能否接入由其明确许可、访问方式、数据处理范围、保留期限和用途限制共同决定。

默认策略：

- `manual_import`：启用。用户或项目维护者导入其有权使用的 CSV、Parquet 或等价文件。
- `authorized_connector`：默认禁用。只有在有可验证的授权、官方 API/导出机制或明确许可后才可启用。
- `public_dataset`：可使用，但要记录数据集许可证、发布日期、字段、覆盖范围和再分发限制。
- `demo_fixture`：可提交，必须标为合成、匿名化或明确可再分发的公开样例。

任何来源均不得通过绕过验证码、登录、限流、反爬、付费墙或其他访问控制的方式获取数据。

## 2. 来源类别与启用状态

| 类别 | 示例 | 默认状态 | 条件 |
| --- | --- | --- | --- |
| 手动导入 | 经授权的 CSV/Parquet | Enabled | 导入者确认有权使用；生成 manifest。 |
| 公开研究数据集 | 经许可的招聘研究数据 | Conditional | 核对许可证、字段敏感性、再分发限制。 |
| 官方开放数据/公开下载 | 政府或高校公开就业统计 | Conditional | 仅使用公开许可的下载/API，保存许可和访问日期。 |
| BOSS 直聘 Connector | 平台岗位数据 | Disabled | 获得明确的书面许可或官方授权接口后再启用。 |
| 智联招聘 Connector | 平台岗位数据 | Disabled | 同上。 |
| 前程无忧 51Job Connector | 平台岗位数据 | Disabled | 同上。 |
| 国聘网 Connector | 平台岗位数据 | Disabled | 同上。 |
| 企业招聘官网 Connector | 企业公开职位 | Disabled | 逐来源评估公开许可、robots/条款和使用范围。 |

“Disabled”表示可以保留适配器接口、配置 schema 和状态提示，但不得自动发起抓取、模拟访问或声称已经接入。

## 3. Source Manifest 最小字段

每个导入批次必须持久化以下 provenance：

| 字段 | 说明 |
| --- | --- |
| `source_id` | 稳定来源标识。 |
| `source_name` / `source_type` | 人可读来源与类别。 |
| `connector_id` / `connector_version` | 导入渠道及实现版本。 |
| `authorization_status` | `manual_confirmed`、`public_license_verified`、`authorized` 或 `disabled`。 |
| `license_or_terms_reference` | 许可、协议、书面授权或导入者声明的引用。 |
| `ingestion_run_id` / `imported_at` | 批次和导入时间。 |
| `raw_artifact_path` / `sha256` | 原始文件位置与完整性哈希。 |
| `native_record_id` | 来源内部记录标识；无则为空。 |
| `observed_at` / `published_at` | 数据被观测或岗位被发布的时间。 |
| `schema_mapping_version` | 该批次的字段映射版本。 |
| `coverage_notes` | 城市、角色、时间范围、已知缺失和使用限制。 |

## 4. 数据最小化与保留

- 只导入分析所需的招聘字段；不收集候选人简历、联系方式或登录凭据。
- 原始文本和文件属于受控本地数据，默认不进入 Git、公开 Demo 或浏览器响应。
- API 返回聚合值、必要的岗位层解释和来源 metadata；受限制来源的原始文本不外发。
- 数据删除、更正、授权撤回或保留期到期时，应删除对应 Raw/Bronze 记录，并通过再处理重建下游 Silver/Gold 结果。

## 5. Demo 数据要求

开发和公开展示必须可离线运行。`data/demo` 中的样例数据需要：

- 指定为合成、匿名化或带可再分发许可的公开数据；
- 包含最小的 source manifest、多个来源标签和可覆盖分析流程的字段；
- 经过相同的标准化、去重、技能抽取与指标管道；
- 在 UI 中清楚显示“Demo 数据”及其时间范围，不能伪装成最新真实市场。

## 6. 新来源启用检查清单

- [ ] 已记录数据权利、使用范围、保留期和再分发限制。
- [ ] 访问方式是官方 API、获授权导出、明确公开下载或手动导入。
- [ ] 没有验证码绕过、登录模拟、反爬规避或规避限流的实现。
- [ ] 已定义字段映射、唯一记录标识、增量策略和速率限制。
- [ ] 已定义 provenance 字段、质量校验和数据删除流程。
- [ ] 已更新本文件、`docs/ARCHITECTURE.md` 和受影响的测试。
- [ ] 已通过人工审批并将 Connector 状态从 `disabled` 变更为启用状态。

## 7. Phase 13 Connector Framework

### 7.1 实现范围

Connector Framework 位于 `packages/data-pipeline/src/app`，包含：

- `CsvConnector`：只读取本地 CSV；不接受 URL。
- `ParquetConnector`：只读取本地 Parquet；不接受 URL。
- `ManualExportConnector`：根据扩展名选择 CSV 或 Parquet Connector。
- `PublicDatasetConnector`：只读取已下载到本地、且完成许可证评审的数据集文件。
- `AuthorizedHttpConnector`：仅定义接口契约，仓库中没有任何网络实现、认证逻辑或平台私有接口代码。

平台与未来来源 Adapter 配置统一位于 `data/reference/sources.v1.yml`。BOSS 直聘、智联招聘、前程无忧 51Job 和国聘网均为：

```yaml
enabled: false
mode: manual_import
connector: manual_export
```

这里的 `enabled=false` 表示禁止自动同步或网络访问。`manual_import` 仍允许操作者导入其合法持有的本地导出文件；项目不据此判断或授予数据权利，导入者仍需确认授权、用途和保留范围。

官方就业平台、企业招聘官网、Public Dataset 和 Research Dataset 提供占位 Adapter。占位配置使用 `example.invalid` 条款链接，导入器会主动拒绝执行；只有替换为已审阅的真实条款或许可证引用后才可导入。

### 7.2 SourceMetadata

`list-sources` 和 `source-status` 输出统一的 `SourceMetadata`：

| 字段 | 说明 |
| --- | --- |
| `source_id` / `source_name` | 稳定来源标识和显示名称。 |
| `acquisition_method` | `manual_export`、`public_download`、`research_release` 或未来授权方式。 |
| `enabled` | 是否允许自动 Connector；四个招聘平台默认均为 `false`。 |
| `mode` | 当前接入模式。 |
| `terms_url` | 条款、许可或待评审引用。 |
| `data_usage_status` | `reviewed`、`permission_required` 或 `restricted`；非 `reviewed` 时导入器 fail closed。 |
| `last_sync` | 最近成功写入 Bronze 的导入时间；从 append-only manifest 推导。 |
| `record_count` | 该来源所有已接收 Bronze 记录总数。 |
| `freshness` | `fresh`、`stale` 或 `never`；阈值由来源配置管理。 |
| `notes` | 授权、限制和已知边界。 |

### 7.3 CLI

```bash
python -m app.cli list-sources
python -m app.cli source-status
python -m app.cli import-source boss jobs.csv
```

测试或隔离运行可使用：

```bash
python -m app.cli import-source boss jobs.csv --data-root /path/to/isolated-data
```

`import-source` 不会把文件直接写入 DuckDB 分析表。执行顺序固定为：

```text
本地合法文件
  → append-only Bronze Parquet + immutable manifest
  → Silver 标准化 + Data Quality Report
  → 跨来源 Dedup + job_source_map
  → Rule-first Skill Extraction
  → DuckDB Warehouse snapshot
```

每个导入批次生成唯一 `ingestion_run_id` 和独立 downstream snapshot。Silver 重建会读取 `data/bronze` 下全部历史 Bronze Parquet，因此不同平台分批导入后仍会在同一快照中执行跨平台去重。相同来源、相同 SHA-256 文件会被拒绝重复导入。

外部文件中的字段始终按不可信输入处理。Connector 生成自己的 `source_id`、`source_record_id`、`ingestion_run_id` 和 `observed_at`；如果导入文件包含同名字段，原值会以 `raw_input__*` 保存在 Bronze，不能覆盖系统 provenance。其他原始列保持原名和原值，字段映射只增加 Silver 所需的规范字段副本。

### 7.4 明确禁止的实现

当前 Connector 代码不包含，也不得扩展为：

- 验证码识别或绕过；
- 登录绕过、账号模拟或凭据采集；
- 反爬、设备指纹或浏览器自动化规避；
- 私有接口发现、逆向或调用；
- rate limit、robots、付费墙或其他访问控制规避。

如未来获得合法授权 API，应单独实现经过安全和法务评审的 `AuthorizedHttpConnector`，并显式配置 `enabled=true`、授权范围、凭据注入方式、官方限流和删除流程。凭据不得写入来源 YAML、manifest、日志或 Git。

## 8. 当前数据状态

仓库仍未自动接入 BOSS、智联、51Job 或国聘等招聘平台，这些 Adapter 继续默认关闭。项目保留 `data/demo/bronze_jobs.csv` 合成样例，同时已建立独立的 Real Dataset Mode，接入许可证和文件版本均已核验的公开数据集；两种模式使用相同 Pipeline、taxonomy、Warehouse schema 和 Analytics methodology。

## 9. Real Dataset Mode：Techsalerator China Jobs v1

### 9.1 许可与版本审查

| 项目 | 已核验值 |
| --- | --- |
| 数据集 | `Techsalerator — Job Posting Data in China` |
| 发布渠道 | Kaggle 公开数据集页面与公开下载 API |
| 数据集版本 | `1` |
| Kaggle 更新时间 | `2024-09-13T09:05:48.55Z` |
| 许可元数据 | `Apache-2.0` |
| 下载文件 SHA-256 | `ff64ceab6ff1538fc21451bc836ad2f45239c503fd5316a7fd01aaa12a93e9ff` |
| 压缩文件大小 | 12,790,179 bytes |
| CSV | `Job Posting.csv`，9,919 行、21 个原始列 |

配置位于 `data/reference/sources.v1.yml`。Connector 只接受与审查哈希完全一致的 v1 ZIP/CSV；哈希不符时在写入 Bronze 前失败。Kaggle 页面同时包含商业联系文案，因此本项目只声明使用上述可公开下载、哈希固定的 v1 文件，不推断或获取任何未公开的商业数据。原始岗位描述来自企业招聘页面，Real Mode 不将原始文本再分发给浏览器或提交到 Git。

### 9.2 实际范围审查

数据集标题声称覆盖中国，但结构化 `Location Data.country` 显示 9,919 行中只有 451 行为 `China`。其余 9,468 行不进入中国市场分析，也不会通过岗位描述猜测国家。

纳入的 451 行具有以下已知偏差：

- 发布时间为 2024-03-05 至 2024-09-04，不代表当前招聘市场；
- 企业官网域名仅有 `zf.com` 406 行和 `bosch.com` 45 行，来源集中度极高；
- 中国子集薪资字段全部为空，所有薪资指标必须为 `unavailable`；
- 没有可靠学历和年限经验字段；`Seniority` 不等价于现有经验年限 taxonomy，因此不映射；
- 公开文件没有公司名称列，`Website Domain` 仅作为 `company_name` 的原始企业域名标识，不宣称为法定公司名；
- CSV 含少量非法 UTF-8 字节，Connector 使用 `utf8-lossy` 读取并在 manifest 中记录 warning；
- 主要为英文 JD，且岗位范围不限于本项目的技术角色 taxonomy，因此 `other` 占比很高。

该数据可用于验证真实文件接入、英文 JD 技能抽取、去重、城市分布和数据缺失处理；不适合独立支撑中国技术招聘市场结论、跨平台平衡需求或薪资关联模型。

### 9.3 Field Mapping v1

| 原始字段 | Data Contract 字段 | 规则 |
| --- | --- | --- |
| `Job Opening URL` | `source_job_id`, `source_url` | 原值映射；不调用该 URL。 |
| `Website Domain` | `company_name` | 作为企业域名标识；不扩展为法定公司名。 |
| `Job Opening Title` | `job_title` | 原值映射。 |
| `Location Data[0].country` | scope filter | 仅精确等于 `China` 时纳入。 |
| `Location Data[0].city` | `city` | 仅使用结构化值；空值保持 null。 |
| `First Seen At` | `published_at` | ISO 时间经现有日期标准化转为日期。 |
| `Salary` | `salary_raw` | 原值映射；中国子集无值，保持 null。 |
| `Description` | `job_description` | 原值映射，供 rule-first Skill Extraction。 |
| 无可靠字段 | `education`, `experience` | null；不从 JD 猜测。 |
| 其他 21 列 | Bronze 原始列 | 原名保留，不直接进入分析表。 |

城市 taxonomy 1.1.0 仅为已有城市增加英文别名。未配置的真实城市仍为 null + `unparseable`，不会临时硬编码或猜测。

### 9.4 模式隔离与运行

```bash
python -m app.cli build-real-dataset data/external/techsalerator_china_jobs_v1/dataset.zip
```

Real 数据默认写入 `data/modes/real`，Demo 派生数据仍位于原路径。成功顺序为：原始 artifact 哈希快照 → append-only Bronze → Silver → Dedup → Skill Extraction → Warehouse → Analytics → Skill Network → mode reports。只有全部成功后才原子更新 `data/modes/real/current.json`。

启动 API 时默认仍使用 Demo。切换到 Real：

```powershell
$env:SKILLWORTH_DATA_MODE = "real"
python -m uvicorn skillworth_api.main:app --app-dir apps/api/src
```

如 `current.json` 不存在，Real 模式启动会明确失败，不回退或伪装为 Demo。

## 10. 第一来源代表性审计（历史基线）

接入第二来源前，Real Dataset 仅包含 `techsalerator_china_jobs_v1`；其岗位集中于两个汽车工业企业域名，明确目标岗位占比很低。该历史基线只能用于真实 Pipeline 验证，不能代表中国整体技术招聘市场。当前双来源结果、口径变化与限制以 `docs/MULTI_SOURCE_VALIDATION_REPORT.md` 为准。

Role、Skill 和 Dedup held-out Gold Benchmark 仍未达到最低样本量，因此第二来源只进入受限验证，不构成正式生产市场比较。后续来源仍应优先补足目标数字化岗位、公司多样性和跨来源重复 pair，而不是简单增加非目标岗位数量。

## 11. 第二真实来源：DATA.GOV.HK Government Vacancies

### 11.1 Source Candidate Evaluation

| source_name | license | date_range | record_count | China coverage | salary coverage | description coverage | city coverage | role relevance | update recency | integration difficulty | recommended |
| --- | --- | --- | ---: | --- | ---: | ---: | ---: | --- | --- | --- | --- |
| DATA.GOV.HK Government Vacancies | DATA.GOV.HK 使用条款明确允许在署名条件下复制、分发和商业/非商业使用 | 2025-07-01–2026-07-28 | 70 | 香港特别行政区 | 原文 100%；结构化月薪下限 85.71% | 100% | 100% | Target 2/70（2.86%），很低 | 官方页面标明按小时更新；固定快照时间 2026-07-29 10:10 +08:00 | 低；官方 JSON、无认证 | **是，仅作为受限验证来源** |
| Kaggle `China Jobs Data` | 页面未给出可审计许可证 | 未作为准入依据 | 未作为准入依据 | 声称中国 | 未核验 | 未核验 | 未核验 | 未核验 | 未核验 | 中 | `REJECTED_SOURCE_CANDIDATE`：许可不明确 |
| Kaggle 中国薪资合成数据 | CC0 或页面许可可见，但数据为 synthetic | 合成 | 不适用 | 合成 | 合成 | 不适用 | 合成 | 低 | 不适用 | 低 | `REJECTED_SOURCE_CANDIDATE`：不是真实招聘岗位 |
| Chinese-SkillSpan 研究数据 | 研究发布；本阶段未确认满足市场再利用条件 | 2014–2025（论文描述） | 约 20,000 标注实例 | 中文文本 | 无 | 有 | 无 | 技能抽取相关 | 研究数据 | 中 | `REJECTED_SOURCE_CANDIDATE`：缺公司、地点、发布日期和薪资等 Data Contract 字段，可另作 Benchmark 候选 |
| 未授权商业招聘平台抓取 | 无合法授权或公开再利用许可 | 不适用 | 不适用 | 可能较高 | 可能有 | 可能有 | 可能有 | 可能较高 | 可能较新 | 高 | `REJECTED_SOURCE_CANDIDATE`：禁止绕过登录、验证码、反爬和访问控制 |

最终只接入一个候选：香港特别行政区政府公务员事务局在 DATA.GOV.HK 发布的官方职位 JSON。选择依据是许可、字段、发布日期和更新机制均可审计；其市场代表性弱，因此不能用“官方来源”替代代表性验证。

### 11.2 许可、版本与 Field Mapping

| 项目 | 固定值 |
| --- | --- |
| Dataset page | `https://data.gov.hk/en-data/dataset/hk-csb-csb-gov-vacancies` |
| Download URL | `https://www.csb.gov.hk/datagovhk/gov-vacancies/gov-job-vacancies-en.json` |
| Terms | `https://data.gov.hk/en/terms-and-conditions` |
| Data dictionary | `https://www.csb.gov.hk/datagovhk/gov-vacancies/gov-job-vacancies-data-dictionary-en.pdf` |
| Snapshot timestamp | `2026-07-29 10:10:00 +08:00` |
| SHA-256 | `c0ff0746c485f9133866a189e5d395f9c9e2458b5482f55257659e272925fbc5` |

| 原始字段 | Data Contract 字段 | 规则 |
| --- | --- | --- |
| `jobid` | `source_job_id` | 字符串化；稳定来源记录标识。 |
| 官方 JSON URL | `source_url` | 指向官方快照资源；不合成未经文档确认的职位详情 URL。 |
| `deptnamejve` | `company_name` | 作为招聘部门名称。 |
| `jobname` | `job_title` | 原值。 |
| 固定来源辖区 | `city` | `Hong Kong`，经 City Taxonomy 映射为 `CN-HK`。 |
| `academic[]` | `education` | 只做透明层级映射；无法映射则 null。 |
| `expfrom`, `expto` | `experience` | 结构化年数转为现有 parser 支持的范围；0 解释为来源未设最低年限。 |
| `entrypay` | `salary_raw` | 原文保留。 |
| `ccym/ccyh/ccyd` | `salary_currency` | 当前识别为 `HKD`。 |
| `minpaym/minpayh/minpayd` | `salary_native_min_*` | 保留原生结构化下限，不自动换汇。 |
| `pubdate` | `published_at` | ISO 日期。 |
| `duties`, `entreq`, `ernotes` | `job_description` | 带章节标签拼接；不纳入申请邮箱、电话或地址。 |

港币记录不会进入人民币 `salary_mid_monthly`、Adjusted Salary Association 或 Market Value。若未来增加换汇，必须固定汇率来源、汇率日期和货币口径，并重新版本化方法论。

### 11.3 Source Positioning

`hk_csb_gov_vacancies` 的 `analysis_role=engineering_validation`。它用于 multi-source pipeline、币种保留、来源构成差异和 Connector 测试；由于 Target n=2，默认不参与 Core Skill Demand、Platform-balanced Demand 或 Skill Market Value。此定位不评价数据集本身质量，只说明它与“中国数字化/技术岗位市场”目标的匹配程度。

## 12. NCSS Core Market Candidate

`ncss_public_jobs` 已登记为 `analysis_role=core_market_candidate`，默认 `enabled=false`、`mode=manual_import`、`data_usage_status=permission_required`。Connector 只读取本地 CSV/JSONL，不实现网络采集、Session、Cookie、Token、验证码、代理或登录逻辑。

参考的上游仓库 `NIHILITY-cool/Spark-employment-platform` 在提交 `42a507b093e44b15a62fbd5e6b2891f558125106` 下采用 MIT License；本次只参考字段和审计记录，没有复制实质性代码。MIT 仅覆盖上游代码，不覆盖 NCSS 岗位内容。NCSS 官方用户协议包含用途和复制限制，当前没有适用于 SkillWorth 的开放数据许可或书面授权，因此未运行真实 Preflight，所有样本质量指标为 unavailable，Source Gate 为 FAIL。

完整审计、字段映射和 Gate 结果见 `docs/NCSS_SOURCE_AUDIT.md`。

## 13. NextGig June 2026 与 Qarera 外部基准

`nextgig_global_jobs_2026_06` 固定于 Hugging Face revision `fc9787e07b2a9b5f11a470c503c36e854abd6378`，上游文件 SHA-256 为 `b80c4d541eec3649c5b8d0143a11ddbc9a60691e1c27f6d574b501d4c9ff3f14`。数据集采用 CC BY 4.0，署名为 `NextGig-Rocks/global-job-postings-multi-ats by NextGig`。Preflight 只使用 seed `202606` 的固定 5,000 行样本；派生 hash 与过程记录在 `data/reference/nextgig_source_metadata.v1.json`。

该来源是全球、多 ATS 的聚合/enriched 数据，不是中国专属招聘市场。`job_description` 是上游 LLM 摘要，Connector 以 `description_type=llm_summary` 保留其身份，但不把摘要作为原始 JD 规则提取文本；技能证据优先来自结构化 `skills_required` 与 qualification/responsibility 字段。`city/country` 标记 `geography_source=derived`。来源未发布 application URL 与原始 source job id，因此 URL 为 null，ID 为固定 revision 内的确定性技术标识。

结构化薪资只在原币种内按 year/month/week/day/hour 统一为月频，保留原币种和 rate unit；FX 字段保持 null，且不进入人民币 `salary_mid_monthly`。发布日期晚于固定 snapshot cutoff `2026-06-06` 的值按不可靠日期置 null。Source Gate 结果见 `docs/NEXTGIG_CORE_MARKET_CANDIDATE_REPORT.md`。

`qarera_skills_2026` 固定于 revision `e12a94a46a334188082d329a175e11bc580f6ba2`，采用 CC BY 4.0，DOI `10.5281/zenodo.21204423`。其角色固定为 `external_market_benchmark`：只比较技能排名，不进入 jobs、来源多样性、Pooled Demand、Platform-balanced Demand、薪资模型或 Confidence 的来源数。

## 14. Freehire China Tech Feasibility Audit

2026-08-10 对 `strelov1/freehire` 的公开只读 API 完成来源可行性审计。实时 facets 显示 China 全部岗位 8,294 条，指定技术类别并集 1,234 条；最新 500 条预检样本的 description coverage 为 99.6%、structured skills coverage 为 77.6%，但可用 salary min/max coverage 仅 1.6%，且样本主要由在华跨国企业和多 ATS/聚合来源组成。核验清单中的中国大厂覆盖稀疏，ByteDance 精确 slug 的 China technical jobs 为 0。

因此 Freehire 当前 Source Role 为 `CHINA_SUPPLEMENTARY`，不是 `CHINA_CORE_CANDIDATE`。Freehire 代码采用 MIT License，但该许可不自动覆盖第三方招聘文本；SkillWorth 不批量再分发完整 JD。本轮未创建 Connector、未进入生产 Pipeline、未调整 Source Gate。完整证据、字段映射和企业来源治理状态见 `docs/CHINA_TECH_SOURCE_FEASIBILITY.md` 与 `data/reference/china_tech_company_sources.yml`。

## 15. Freehire China Technical Snapshot 2026-08

在最终使用边界复核未发现明确禁止公开只读 API 聚合分析的条款后，项目以 `data_usage_status=no_explicit_block_found` 接入 `FreehirePublicApiConnector`。该状态不等于获得完整第三方 JD 的开放再分发许可。Connector 仅访问文档化 `/api/v1/agent/jobs/search`，不使用登录、Cookie、Session、Token、验证码、代理规避或私有接口。

- Snapshot：`freehire_china_tech_2026_08`
- 查询：country facet `cn`；15 个审计技术类别；按 `posted_at desc` 分页。
- Source Role：`supplementary_market` / 产品显示 `china_supplementary`。
- 软件上游 revision：`d7ab8697635528b47cea719a590eac485e1dfa2c`，MIT 仅覆盖 Freehire 软件。
- 原始招聘文本：仅本地受控保存用于管道与聚合，不随仓库提交或批量再分发。
- 采集：串行分页、0.5 秒页间延迟、429 `Retry-After`、5xx/网络错误指数退避、页面缓存和断点复用。
- 快照 SHA-256：`edae6443a3cc41660958dbb7bbe7f682c351ffc7cc582415fb392bdde9c60ea5`。

实际结果与限制见 `docs/FREEHIRE_CHINA_SNAPSHOT_REPORT.md`，使用审计见 `docs/FREEHIRE_USAGE_AUDIT.md`。早期可行性文档中“未创建 Connector/未进入 Pipeline”的描述仅代表当时阶段，已由本节和固定快照报告取代。
