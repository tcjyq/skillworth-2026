# SkillWorth Live — 工程协作宪章

## Project

- 产品：技值 SkillWorth（开发代号 SkillWorth Live），面向中国技术岗位公开样本的劳动力市场分析与技能学习决策平台。
- 核心问题：给定目标岗位、已有技能和学习时间预算，下一项最值得学习的技术是什么。
- 当前阶段：V1 Data / Analysis / Story 已冻结；当前工作重点是发布治理与候选首页决策，不是继续扩展研究范围。
- 默认使用 UTF-8、简体中文和 Asia/Shanghai 时区。

## Current Facts

- 冻结 Real v6 snapshot：`freehire_china_tech_2026_08`，默认 `180d` 为 998 个岗位、313 家公司、134 项观测技能；`all-active` 为 1,140 个岗位、339 家公司、138 项观测技能。
- 当前只有 1 个中国补充市场来源 Freehire；它不是完整中国招聘市场的代表性样本。
- Salary 与 Trend 均为 `unavailable`；空值表示证据不可用，不是 0。
- Final 5、公式、技能 taxonomy、角色 taxonomy、去重、学习时长、来源集合和稳健性方法已冻结。
- Production Homepage Candidate 位于 `/lab/visual-v2`；正式 `/` 尚未替换。Public Surface 已统一，Methodology 已面向学生表达；是否提升候选页仍待人工产品决定。
- 默认 `npm run test:e2e` 使用确定性 Demo 数据；`npm run test:e2e:real` 使用本地、不进入 Git 的 Freehire v6 artifact。
- Git 历史从 2026-08-24 reconstructed baseline 开始；此前开发历史未能恢复。

## Source of Truth

发生冲突时按以下优先级判断当前事实：

1. 当前代码；
2. `data/reference/`、`data/taxonomy/` 等当前版本化配置；
3. `apps/api/src/skillworth_api/schemas.py` 等当前 API contract；
4. `pyproject.toml`、`apps/web/package.json`、测试命令及其实际运行结果；
5. `reports/skillworth/final_data_analysis.md` 等当前冻结分析报告；
6. `docs/`、`README.md` 和其他说明文档。

需求入口为 `docs/PRD.md`；架构边界见 `docs/ARCHITECTURE.md`；指标定义见 `docs/METHODOLOGY.md`；来源权利见 `docs/DATA_SOURCES.md`；字段语义见 `docs/DATA_DICTIONARY.md`。文档漂移时应按实现修正文档，不得用旧文档反向覆盖当前实现。

## Stack

- Data / Analytics：Python 3.11+、Polars、PyArrow/Parquet、DuckDB、Pydantic、NumPy、Statsmodels、NetworkX、RapidFuzz。
- API：FastAPI、Uvicorn、Pydantic。
- Web：Next.js 16、React 19、TypeScript、Tailwind CSS、ECharts。
- Verification：pytest、pip check、ESLint、TypeScript、Vitest、Playwright、Next.js production build。

## Architecture & Boundaries

主要数据流：

```text
Raw → Bronze → Silver → Gold Data Layer → DuckDB → Analytics → API → Web
```

- `packages/data-pipeline`：当前实际承载导入/Connector、Bronze → Silver → Gold、标准化、去重、技能抽取和质量校验。
- `packages/analytics`：承载可测试的指标、统计、图网络和优化；不得读取 HTTP 请求、页面状态或 Raw 数据。
- `apps/api`：只做 FastAPI 路由、Pydantic schema、参数验证和服务编排；不得复制 analytics formula。
- `apps/web`：只展示 API / analytics 输出；不得重新计算后端指标或硬编码排名、图表数字和推荐结果。
- `backend/app/sql`：DuckDB Warehouse 的核心表、视图和分析 SQL。
- `packages/connectors`、`packages/contracts`、`packages/ui`、`infra`、`scripts`：当前为空，属于 reserved / planned；不得把预留目录描述为已实现能力。
- `data/raw`、`data/bronze`、`data/silver`、`data/gold`、`data/modes`、`data/warehouse`：只保存本地或受控数据；真实数据和私有 artifact 不进入 Git。
- 每条原始岗位必须保留来源、导入时间、原始文件 hash、原始记录标识和处理版本；去重不得丢失跨来源映射。

## Product Freeze

以下 V1 决策除明确 bug 外不得重新打开：Final 5、指标公式、技能 taxonomy、角色 taxonomy、去重规则与已审计结果、学习时长、来源集合、稳健性方法。

- 影响指标的 bug 修复必须同步更新 `docs/METHODOLOGY.md`、测试样例和版本说明。
- 字段、枚举或空值语义变化必须同步更新 `docs/DATA_DICTIONARY.md`。
- 新来源、Connector 启用或公共契约变化必须先更新 `docs/DATA_SOURCES.md` 或 `docs/ARCHITECTURE.md`。
- Gold Data Layer 指分析就绪数据；Gold Benchmark / Gold Labels 指人工评测真值，两者不得混称。

## Development Rules

- 优先保证数据质量、分析正确性和测试，再处理展示。
- LLM 不得执行统计计算、评分或优化；只能解释已计算证据，或在规则抽取失败后提出可审计候选。
- 未获明确合法授权的来源保持 disabled；严禁绕过验证码、登录、反爬、限流、付费墙或其他访问控制。
- Demo 数据必须明确为公开、合成或匿名化，并通过与 Real 相同的计算链路。
- 不创建无实际复用需求的抽象，不修改当前任务无关文件。

## Task Routing

- Data bug：定位 Raw / Bronze / Silver / Gold、provenance、schema 或质量规则；不要顺带改 UI。
- Analysis bug：定位 `packages/analytics`、`backend/app/sql` 和版本化配置；验证冻结 Finding 是否变化。
- UI bug：只处理 API 消费、展示、交互和可访问性；不要重新打开数据研究或复制分析公式。
- Docs task：先按 Source of Truth 顺序核实现状，只同步事实和术语。
- Release task：检查 `docs/RELEASE_READINESS.md`、完整验证、Git diff、数据权利和未决人工 Gate。
- Future research：第二来源、Salary、Trend、Gold Benchmark 等独立排期，不作为普通 V1 修复附带实现。
- 架构/治理审计使用 `project-constitution`；Bug 使用 `debugging-and-error-recovery`；代码评审使用 `code-review-and-quality`；浏览器验收使用 `browser-testing-with-devtools` 或前端测试技能。

## Verification

从仓库根目录运行 Python 检查：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
```

从 `apps/web` 运行 Web 检查：

```powershell
npm run lint
npm run typecheck
npm run test -- --run
npm run build
npm run test:e2e
```

`npm run test:e2e` 会从已提交的 `data/demo` 重建隔离、确定性的 Demo fixture，不要求 Real 私有数据。若本地 Freehire v6 manifest 和依赖 artifact 可用，再运行：

```powershell
npm run test:e2e:real
```

Real E2E 的 frozen assertion 回归必须停止发布治理工作并报告，不得通过修改冻结 Finding 掩盖失败。

## Git & Change Safety

- `main` 保持稳定；一个任务使用一个短期 branch，开始修改前必须确认 clean checkpoint。
- 保护 reconstructed baseline；禁止 amend、rebase 或重写该基线，禁止擅自 force push/reset。
- 禁止提交 Real/raw/private 数据、DuckDB、完整 JD、个人信息、密钥、Token、截图、视频或本地缓存。
- commit 前运行 `git status`、`git diff --stat`、`git diff`、`git diff --check`，审计范围、机密和生成物。
- 不覆盖用户未提交修改；不执行不可逆操作，除非用户明确授权。

## Data / Source Rights

- 根目录 MIT 仅覆盖 SkillWorth 自主创作的代码与项目文档。
- Freehire 软件的 MIT 许可不等于招聘内容采用 MIT；外部岗位文本、数据集、商标和其他第三方内容保留各自权利。
- 默认只发布聚合结果；第三方数据不会因进入分析管道而自动继承仓库许可证。

## Do Not

- 不为演示效果硬编码指标、排名、推荐或图表数字。
- 不把单一 Freehire 补充样本描述为完整中国市场。
- 不把 recency window 描述为 Trend，不把 Salary `unavailable` 写成 0。
- 不宣称未完成的 Gold Benchmark 具有 Precision、Recall 或 F1。
- 不把 reserved / planned 包描述为已实现。
- 不因 UI 问题重新打开冻结的数据、公式或研究范围。

## Unknowns / Limitations

- Salary evidence unavailable。
- Trend evidence unavailable；当前只有单一 snapshot。
- 完整中国技术招聘市场代表性 unavailable；当前只有一个补充来源。
- Gold Benchmark / Gold Labels 不完整，尚不能发布 Precision、Recall 或 F1。
- Visual V2 是否提升到 `/`、最终产品截图、GitHub remote 和 CI workflow 尚未决定或建立。

## Stale When

发生以下任一变化时必须更新本文件并重新运行 project-constitution validator：

- snapshot、默认窗口或冻结样本数字变化；
- 测试命令、Demo / Real E2E 机制或发布验证门槛变化；
- `/lab/visual-v2` 被提升为正式首页；
- 新来源加入或来源角色/权利边界变化；
- 公式、taxonomy、去重、学习时长或稳健性方法变化；
- 架构、目录职责、API contract、release workflow、remote 或 CI 状态变化。
