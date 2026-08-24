# China Tech Market Source Feasibility Audit

报告日期：2026-08-10（Asia/Shanghai）  
目标范围：**2026 年中国主要科技企业公开技术岗位样本**  
Freehire 结论：**`CHINA_SUPPLEMENTARY`**  
审计边界：本轮只访问 Freehire 的公开只读 API 与公开文档；未采集企业官网、未访问登录态接口、未创建任何新 Connector、未调整 Source Gate。

## 1. Freehire 上游、许可与访问边界

| 项目 | 审计结果 |
| --- | --- |
| 上游仓库 | `strelov1/freehire` — https://github.com/strelov1/freehire |
| 固定 revision | `d7ab8697635528b47cea719a590eac485e1dfa2c` |
| revision 时间 | 2026-08-10T04:10:00Z |
| API 文档 | https://freehire.me/docs/api |
| Facets 文档 | https://freehire.me/docs/api/jobs/facets-get |
| Search 文档 | https://freehire.me/docs/api/jobs/search-get |
| Companies 文档 | https://freehire.me/docs/api/companies/companies-get |
| API Base | `https://freehire.me/api/v1` |
| 代码许可 | MIT License，Copyright (c) 2026 freehire contributors |
| 访问日期 | 2026-08-10 |
| 认证要求 | 文档标注公开只读 API 无需认证；本轮未使用 Cookie、Token、Session 或登录态 |

MIT License 只适用于 Freehire 软件及其文档，不自动授予第三方招聘文本、商标、公司数据或原始 ATS 内容的版权和再分发权。本轮没有复制 Freehire 实质性代码。若以后复用代码，必须保留上游版权声明和 MIT License；若正式接入数据，SkillWorth 默认只公开聚合结果，不批量公开完整 JD。

## 2. Facet Discovery

2026-08-10 实时调用 `GET /jobs/facets` 后确认：

- China 的实际 country facet value 为小写 `cn`，不是预设值。
- `/jobs/facets` 当前响应不返回 company slug facet；尽管 `company_slug` 是文档支持的过滤参数，不能从未返回的 facet 猜测企业身份。
- ByteDance 通过公开 `/companies` 目录发现精确 slug `bytedance`；另有独立实体 `bytedance-pte-ltd`，两者未合并。
- 本阶段要求的 15 个 technical category 均为当前有效 category 值。

## 3. China Market Counts

快照时间：`2026-08-10T17:23:18+08:00`。计数只使用 metadata/facets，不下载全量数据。

| 范围 | 岗位数 |
| --- | ---: |
| China 全部岗位（`countries=cn`） | 8,294 |
| China 目标技术类别并集 | 1,234 |

技术并集通过一次逗号分隔 category 查询获得；不能把下表简单相加，因为一个岗位可同时属于多个类别。

| Category | Count | Category | Count |
| --- | ---: | --- | ---: |
| backend | 59 | frontend | 19 |
| fullstack | 36 | data_engineering | 47 |
| data_science | 47 | data_analytics | 267 |
| ml_ai | 99 | ai_engineering | 72 |
| devops | 41 | sre | 9 |
| security | 90 | embedded | 47 |
| hardware | 144 | product | 215 |
| business_analysis | 42 |  |  |

## 4. 中国科技公司覆盖

企业身份判断流程为：先用 `/companies` 做候选发现，再以明确的 company slug、公司名称和来源 provenance 核验；没有用模糊 `contains` 把相似名称认作同一公司。`technical_jobs` 使用本报告第 3 节的目标类别并集。

| 公司 | 状态与精确实体 | Open jobs | China jobs | China technical jobs |
| --- | --- | ---: | ---: | ---: |
| ByteDance | FOUND：`bytedance` | 26 | 0 | 0 |
| Baidu | NOT_FOUND；仅发现 `baidu-usa`，不冒充中国百度 | unavailable | unavailable | unavailable |
| Alibaba | NOT_FOUND；搜索命中为无关相似名称 | unavailable | unavailable | unavailable |
| Meituan | NOT_FOUND | unavailable | unavailable | unavailable |
| Tencent | FOUND：`tencent` | 197 | 38 | 0 |
| JD | FOUND：`jd-com` / JD.COM | 15 | 0 | 0 |
| Xiaomi | NOT_FOUND；只发现新加坡、印度实体 | unavailable | unavailable | unavailable |
| Huawei | FOUND：`huawei`，实时 facets 当前无开放岗 | 0 | 0 | 0 |
| Kuaishou | NOT_FOUND | unavailable | unavailable | unavailable |
| NetEase | FOUND（品牌实体）：`netease-games` | 11 | 1 | 0 |
| Xiaohongshu | FOUND：`xiaohongshu` | 2 | 0 | 0 |
| PDD | NOT_FOUND；只发现 `pdd-pte-ltd` | unavailable | unavailable | unavailable |
| Bilibili | NOT_FOUND；只发现新加坡实体 | unavailable | unavailable | unavailable |
| HoYoverse | FOUND：`hoyoverse` | 14 | 0 | 0 |
| DJI | NOT_FOUND；候选为无关相似名称 | unavailable | unavailable | unavailable |
| DeepSeek | NOT_FOUND | unavailable | unavailable | unavailable |
| MiniMax | NOT_FOUND；候选为无关同名公司 | unavailable | unavailable | unavailable |

补充：`bytedance-pte-ltd` 是独立的新加坡法人实体，Open jobs 45、China jobs 0，未与 `bytedance` 合并。ByteDance 精确实体在 Freehire 中的 **China technical jobs 为 0**。Freehire 能发现部分中国品牌，但实时中国技术岗位覆盖不足以代表“中国主要科技企业公开技术岗位”。

## 5. 500 条 Small Data Sample

由于 China technical 并集为 1,234，本轮按 `posted_at` 降序读取最多 500 条，存入独立、被 Git 忽略的本地 preflight staging；没有进入 Bronze、Gold 或生产 Warehouse，也没有提交 JD 原文。

| 质量项 | 结果 |
| --- | ---: |
| sample rows / unique public_slug | 500 / 500 |
| title coverage | 100.0% |
| description coverage | 99.6% |
| non-empty structured skills coverage | 77.6% |
| location coverage | 100.0% |
| posted_at coverage | 100.0% |
| usable salary min/max coverage | 1.6% |
| any salary metadata coverage | 7.8% |
| company diversity | 212 |
| source diversity | 30 |
| source URL coverage | 100.0% |
| external source ID coverage | 100.0% |

样本的主要 category 为 `data_analytics=111`、`product=88`、`hardware=50`、`ml_ai=41`、`backend=29`、`security=27`、`data_engineering=26`。主要来源为 `workday=158`、`echojobs=68`、`greenhouse=52`、`oracle=49`、`smartrecruiters=34`、`apple=23`。样本头部公司包括 Amazon、Apple、NVIDIA、Bosch、State Street 和 Coupang；未出现本报告核验过的精确中国大厂 slug。

每条记录保留 `url`、`source`、`external_id`、`company_slug` 与时间字段，provenance 基础较好。但部分 source 是聚合源而非第一方 ATS，`source_url` 可追溯不等于原始内容拥有可再分发许可。薪资覆盖明显不足。

## 6. Freehire → SkillWorth RawJob 字段兼容性

本表只评估映射，不创建旁路和 Connector。

| Freehire | SkillWorth RawJob / provenance | 处理约束 |
| --- | --- | --- |
| `public_slug` | `source_job_id` | 在 Freehire source namespace 内使用 |
| `url` | `source_url` | 保留原始 ATS/聚合来源 URL |
| `source` | `source`、`acquisition_metadata` | 保留上游 source 类型，不折叠 provenance |
| `external_id` | `source_external_id` | 与 public_slug 同时保留 |
| `title` | `job_title` | 后续进入现有 title/role normalization |
| `company` | `company_name` | 原文保留 |
| `company_slug` | `source_company_slug` | 只作来源实体标识，不替代 canonical company |
| `location` | `city` / `location_raw` | 后续走现有 city normalization |
| `cities`, `countries`, `regions` | structured location provenance | 标记为上游结构化字段 |
| `description` | `job_description` | 原文受数据使用边界约束，不批量再分发 |
| `skills` | `structured_skills_raw` | 不直接冒充 SkillWorth canonical taxonomy |
| `enrichment.category` | `source_category` | 不直接冒充 SkillWorth role |
| `enrichment.seniority` | `experience_raw` / source seniority | 进入现有 experience normalization |
| `enrichment.employment_type` | `employment_type_raw` | 保留来源值 |
| `enrichment.salary_*` | structured salary observation | 保留币种和周期，不静默换汇或猜测缺失值 |
| `posted_at` | `posted_at` | 保留原始时区/精度信息 |
| `created_at`, `updated_at` | upstream observation timestamps | SkillWorth `observed_at` 仍由导入事件记录 |
| `manually_added`, `enriched_at`, `enrichment_version`, `reality` | provenance / quality metadata | 不参与未经定义的业务指标 |

未来若获准正式接入，仍必须完整经过：Raw → append-only Bronze → Silver → Skill Normalization → Role Normalization → Dedup → Gold → DuckDB。Freehire 的 category、skills 或 enrichment 不能绕过现有 Data Contract 和 normalization。

## 7. Source Role Decision

Freehire 定位为 **`CHINA_SUPPLEMENTARY`**，不标记为 `CHINA_CORE_CANDIDATE`。依据：

1. China 技术类别并集 1,234，字段与 provenance 足以支持进一步工程评估；因此不是 REJECT 或纯 ENGINEERING_VALIDATION。
2. 最新 500 条样本以在华跨国企业和多 ATS/聚合源为主，未覆盖核验清单中的精确中国大厂 slug。
3. 已发现的目标品牌实体，其 China technical jobs 合计仍为 0；不能支持新的市场范围。
4. 可用薪资 min/max 覆盖仅 1.6%，且第三方职位文本的再利用/再分发权不能由 Freehire 代码 MIT License 推导。
5. 本轮不降低任何现有 Source Gate，也不因 metadata 分类标签而绕过 SkillWorth 的目标市场识别。

## 8. 中国大厂 Source Registry 决策

配置化登记见 `data/reference/china_tech_company_sources.yml`。

| 公司 | Status | 下一步 |
| --- | --- | --- |
| Tencent | `manual_reference_only` | 正式停止自动采集路线；只有明确书面许可才可重开 |
| Baidu | `permission_required` | 值得进行许可与数据使用范围调查，不开发 Connector |
| Alibaba | `permission_required` | 值得核实官方 API 授权模型与再利用条款，不开发 Connector |
| Meituan | `permission_required` | 值得进行许可调查，不开发 Connector |
| ByteDance | `permission_required` | 值得分别审计公开页面与公开接口；禁止 Cookie/CSRF/Session 路线 |

腾讯依据官方招聘平台条款保持 manual reference only：https://careers.tencent.com/m/zh-cn/termsservice.html 。其他企业的公开可见页面不构成自动化采集、分析或再分发许可。

## 9. 最终回答

1. Freehire 当前 China jobs：**8,294**。
2. 目标技术类别并集：**1,234**。
3. 是否覆盖中国大厂：**只覆盖少数品牌实体，覆盖稀疏且不具代表性**。
4. ByteDance China technical jobs：精确 `bytedance` slug 为 **0**。
5. Freehire Source Role：**`CHINA_SUPPLEMENTARY`**。
6. 百度：**值得进入许可调查，不允许开发 Connector**。
7. 阿里：**值得进入许可/API 授权调查，不允许开发 Connector**。
8. 美团：**值得进入许可调查，不允许开发 Connector**。
9. 字节：**值得做公开访问与许可分离审计；禁止任何登录态依赖路线**。
10. 腾讯：**正式停止自动采集路线，保持 `manual_reference_only`**。
11. 是否已有 China Core Market：**没有**。Freehire、NextGig、NCSS、现有 Real Dataset 与企业官网证据均未同时满足范围、许可和质量要求。
12. 下一步最多允许开发的 Connector：**只优先考虑 1 个 Freehire 公开只读 Connector，且必须先确认 API 服务条款、速率限制和第三方数据使用边界；当前不允许开发任何企业官网 Connector。** 若未来取得明确书面授权，第二个名额才可从百度或阿里中择一，不得并行铺开。

## 10. 局限与复现说明

- Freehire 是 live API，计数会变化；本报告只对快照时间负责。
- 500 条样本按最新发布时间截取，不是对 1,234 条的随机代表性抽样。
- `technical_jobs` 使用 Freehire category metadata，仅用于来源可行性预检，不替代 SkillWorth Role/Skill Gold Benchmark。
- 本轮未向企业官网发送批量请求，未验证 cookie/CSRF/captcha 的所有动态状态；registry 中未知项保留为 null。
- 本轮未创建生产数据快照或发布 JD；只保存被 Git 忽略的本地 preflight 响应，用于审计复核。
