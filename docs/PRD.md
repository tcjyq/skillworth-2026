# 产品需求文档（PRD）

## 1. 产品概述

**产品名称：** SkillWorth 2026（开发代号：SkillWorth Live）  
**公开版定位：** 2026 中国公开技术岗位样本的技能价值观察产品。

SkillWorth 不把招聘信息做成“技能出现次数排行榜”，而是将招聘数据转为可验证的市场信号，并结合用户现有技能和时间预算，提供可解释的学习决策。

核心问题：

> 对于某个目标岗位和用户当前技能，在有限学习时间下，下一项最值得学习的技术是什么？

## 2. 目标用户与需求

| 用户 | 典型问题 | 产品价值 |
| --- | --- | --- |
| 在校学生与应届生 | 想进入数据、开发、AI 或产品岗位，不知道该优先补齐什么技能。 | 基于目标岗位给出技能缺口、边际机会增益与学习顺序。 |
| 初入职场的技术从业者 | 想转向相邻岗位，但不清楚迁移成本。 | 对比角色技能簇、市场趋势和学习投入。 |
| 职业辅导或教学人员 | 需要理解不同岗位的真实技能需求。 | 提供可追溯的市场统计和方法说明。 |

## 3. 成功标准

- 用户可选择目标岗位、城市/时间等市场筛选，并输入已有技能与学习时间预算。
- 系统从实际导入的 Gold 数据计算技能需求、趋势、岗位覆盖和推荐结果；Demo 同样走真实计算链路。
- 每一项市场结论可展示来源、样本量、数据时间范围、处理版本和置信度。
- 用户可查看推荐技能的边际岗位覆盖增益、学习成本、市场价值和计算依据。
- 所有核心分析函数都有自动化测试，且不需要访问未授权招聘平台即可运行。

## 4. 业务范围

### 4.1 核心能力

1. 多源招聘数据接入（手动导入优先，授权 Connector 可扩展）。
2. Data Provenance：数据来源、授权状态与处理版本追踪。
3. 跨平台岗位去重与来源保留。
4. 岗位标题、城市、经验、学历、公司和发布时间标准化。
5. 薪资解析、币种/周期归一与可用性标记。
6. 技能词典、别名归一和可审计的技能抽取。
7. Skill Demand、Platform-balanced Demand、Adjusted Salary Association、Skill Trend。
8. Skill Co-occurrence Network 与技能簇。
9. Personal Skill Coverage、Marginal Skill Coverage Gain、Learning Cost、Market Value Score 与 Personal Skill ROI。
10. Learning Time Optimizer。
11. Cross-platform Bias Analysis 与 Data Confidence Score。
12. FastAPI 服务和 Next.js Dashboard。

### 4.2 非目标

- 不做招聘投递、简历代投、候选人筛选或企业 ATS。
- 不宣称技能造成薪资变化或保证求职成功；薪资仅进行控制变量后的关联分析。
- 不通过自动化手段绕过招聘网站的验证码、登录、反爬、限流或访问控制。
- 不把通用 LLM 对原始岗位文本的结论当作统计事实。
- 第一版不承诺覆盖全部中国城市、岗位类型或招聘平台，也不承诺实时全量市场。

## 5. 产品体验与页面边界

公开一级体验固定为：

1. `/`：SkillWorth 2026，按 Hero → Frontier → Skill Market Board → Market Themes → Methodology / Data Scope 叙事回答“2026，学什么技术最值？”；
2. `/methodology`：完整方法、证据边界和限制；
3. Data Scope：作为首页锚点展示 snapshot、窗口、样本量、来源角色与不可用信号。

历史 Market、Skills、Roles、Graph、Portfolio、Optimizer 与 Data Quality 能力保留在 `/lab/*`，不属于公开主导航。旧路径仅兼容重定向至对应 Lab 路由。

当前公开默认口径为 `market_scope=china_open_tech_sample`、`source_role=china_supplementary`、`recency_window=180d`。界面采用 Cinematic Data Intelligence 视觉语言，但视觉不得替代解释；任意数字、图表点位或推荐文本必须能追溯到 API 与方法论。

## 6. 约束与工程原则

- 核心技术栈：Python、FastAPI、Pydantic、Polars、DuckDB、Parquet、PyArrow、NumPy、Statsmodels、Scikit-learn、NetworkX、RapidFuzz；Next.js、TypeScript、Tailwind CSS、shadcn/ui、ECharts；pytest、Vitest、Playwright。
- 默认运行方式必须仅依赖本地公开/合成样例数据；任何真实 Connector 默认关闭。
- Connector 与分析层解耦；API 与前端不直接读取原始文件。
- 指标方法、权重、阈值和已知局限必须版本化并记录于 `docs/METHODOLOGY.md`。
- 真实数据默认不提交到版本库；只提交受许可的公开、小型、匿名化或合成 Demo 数据。

## 7. 当前阶段验收条件

- [x] 仓库目录按 monorepo 边界建立。
- [x] 产品、架构、方法论和数据来源文档已建立。
- [x] 数据合规和 provenance 规则已书面化。
- [x] 已创建 Bronze → Silver Python ETL、配置化角色/城市 taxonomy、质量报告和测试。
- [x] 已创建保守的 Silver → Gold 跨平台去重、`canonical_jobs`、`job_source_map`、报告和测试。
- [x] 已创建可重建 DuckDB Analytics Warehouse、核心表、Analysis Views、数据测试和 Query Benchmark。
- [x] 已创建正式 Analytics、FastAPI、Next.js、合规 Connector Framework 与独立 Real Dataset Mode；招聘平台授权 Connector 仍按设计默认关闭。

## 8. 未来 12 个开发阶段

- [x] **Phase 1 — 产品、架构与 Data Contract**：建立 monorepo、工程原则、PRD、架构、方法论、数据源和数据字典，并初始化可测试 Python 包。
- [x] **Phase 2 — Bronze → Silver ETL**：实现 append-only 读取、岗位/公司/地点/经验/学历/日期/薪资标准化、Parquet 输出、质量报告和 CLI。
- [x] **Phase 3 — Skill Taxonomy & Extraction**：实现 120+ 版本化技能、学习成本字段、规则优先抽取、短词消歧、人工标注 Benchmark、Parquet 输出和 CLI；LLM 默认关闭。
- [x] **Phase 4 — 跨平台去重与 Gold 数据集**：实现三级保守匹配、complete-link 分组、`canonical_jobs`、`job_source_map`、质量报告和 CLI。
- [x] **Phase 5 — DuckDB Analytics Warehouse**：实现核心事实/维度表、Analysis Views、数据测试、Query Benchmark 和可重建 CLI。
- [x] **Phase 6 — 基础劳动力市场指标**：发布 Skill Demand、Platform-balanced Demand、技能薪资分布、角色/城市/经验切片和来源构成分析；Skill Trend 与 Data Confidence 仍在后续阶段实现。
- [x] **Phase 7 — Advanced Analytics**：实现覆盖率趋势与透明分类、Adjusted Salary Association、样本门槛、HC3 模型诊断、PMI/Jaccard 技能网络和社区划分。
- [x] **Phase 8 — Data Confidence Engine**：实现样本量、来源多样性、数据时效性、薪资覆盖率和跨来源一致性的透明评分、等级、分量与 warning。
- [x] **Phase 10A — 市场价值与敏感性分析**：实现配置化 Market Value、Personal ROI、学习时长估算/覆盖、排名稳定性和敏感排名警告。
- [x] **Phase 9 — Personal Skill Opportunity Engine**：实现用户技能输入、岗位 Skill Fit、阈值覆盖、候选技能边际增益、crossing jobs、筛选、置信度与集合化计算。
- [x] **Phase 10 — 学习时间优化器**：实现 Learning Cost 情景、Iterative Greedy、预算约束、每步重算边际收益与测试基准；Beam Search 保持 optional、当前未启用。
- [x] **Phase 11 — FastAPI 与 Next.js 产品层**：实现稳定 API、Dashboard、数据质量页、Portfolio/Optimizer 流程、Vitest、Playwright 和可访问状态设计。
- [ ] **Phase 12 — 端到端验证与发布材料**：执行浏览器测试、性能和方法论审计，完善 README、架构图、Demo 数据说明与项目展示材料。

## 9. 待确认项

- 初始公开/合成 Demo 数据集的许可、字段和时间范围。
- 首批支持的目标岗位 taxonomy 与城市范围。
- Learning Cost 初始估计的来源、维护者和用户编辑方式。
- Market Value 与 Personal ROI 权重的校准样本及版本治理方式。

## 10. 交付版本划分

### MVP — 可信的离线决策闭环

MVP 的目标不是“接入所有招聘平台”，而是让一份合规的 Demo/手动导入数据完整通过同一条可复现链路，并回答核心问题。

- 仅启用 `manual_import` 与带 manifest 的本地 Demo 数据；第三方平台 Connector 保持 disabled。
- 实现 source provenance、Bronze/Silver/Gold、岗位/薪资标准化、技能 taxonomy 与规则优先的技能抽取。
- 实现确定性去重和保守的模糊匹配候选输出；保留 `job_source_map`。
- 实现 Skill Demand、Platform-balanced Demand、Skill Trend、Data Confidence、个人 Skill Coverage 与 Marginal Skill Coverage Gain。
- 实现带 Learning Cost 的可解释贪心 Learning Time Optimizer，输出每一步重新计算后的增益。
- 提供最小 FastAPI API 和功能优先的 Next.js 页面，用于展示真实计算结果与方法版本。
- 覆盖核心管道/指标的 pytest，以及最小 API 和关键用户路径测试。

**MVP 完成条件：** 从本地示例导入开始，用户可以选择目标岗位、输入现有技能和小时预算，得到带样本量、数据范围、来源与置信度的推荐结果；任一界面数字可追溯到 Gold 数据和方法版本。

### V2 — 多源可比分析与市场解释

- 在获得授权后启用独立 Connector，并记录来源权利、覆盖范围和增量策略。
- 完善跨平台模糊去重、人工复核工作流与质量评估集。
- 实现 Adjusted Salary Association、模型诊断、Skill Co-occurrence Network、Platform Sampling Bias Analysis 与 Market Value Score。
- 扩展角色、城市、经验和学历切片；加入数据质量、来源健康度与方法论页面。
- 增加 Vitest 图表/筛选器测试、Playwright 端到端测试与性能基线。

### V3 — 产品化与高级决策能力

- 实现 Personal Skill ROI、权重敏感性分析、学习成本情景与 beam search 优化对照。
- 支持用户保存 Portfolio、可编辑学习成本和推荐方案比较；前提是完成隐私与认证设计审查。
- 增加 LLM 解释层：只能引用已计算的结构化证据和 methodology version，不得计算指标。
- 完善响应式、高可访问性的数据产品界面、观察性、数据版本比较和发布自动化。

## 11. 跨阶段完成定义

每个开发 checklist 项完成前均需满足：

- [ ] 新增或变更的字段已写入 `docs/DATA_DICTIONARY.md`。
- [ ] 新增或变更的复杂指标已写入 `docs/METHODOLOGY.md`。
- [ ] 每个真实数据输入都具有 source manifest 和处理版本。
- [ ] 增加与变更风险相称的 pytest、Vitest 或 Playwright 测试。
- [ ] 不包含未授权网络访问、硬编码分析结果、密钥或真实受限数据。
- [ ] API、Dashboard 与文档对同一指标使用相同名称和版本。
