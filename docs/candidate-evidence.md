# SkillWorth 招聘证据与贡献边界

更新：2026-09-29。定位为“公开招聘样本分析与技术学习决策数据产品”，当前证据来自 Freehire 单源固定快照。以下是**项目中可展示的能力证据**，不自动等于某个人独立完成的贡献；本人具体决策、手写代码与审阅记录待本人确认。Codex 参与的本轮实现不得表述为本人独立手写。

| 可讲能力 | 代码／测试／产物证据 | 面试可讲的问题 | 目前限制 |
| --- | --- | --- | --- |
| 需求定义 | `docs/PRD.md`、正式 `/` 与 `/methodology` | 为何从“热门”转为“目标岗位下优先学什么”？ | 页面是决策辅助，无职业收益验证 |
| 口径与来源 | `docs/DATA_SOURCES.md`、`data/production-safe/current/artifact_metadata.json` | 访问日、产物生成日、180d、all-active 分别表示什么？ | Freehire 单源，不具市场代表性 |
| 清洗与去重 | `packages/data-pipeline/src/app/`、`tests/integration/test_warehouse.py`、冻结报告 A 节 | 原始、Silver、Gold 各有多少，为什么不能混用分母？ | 本轮未全量重跑私有 ETL |
| SQL 与连接基数 | `backend/app/sql/02_analysis_views.sql`、`tests/unit/test_sql_evidence.py` | 一对多来源映射为何使 `COUNT(*)` 放大？ | 合成测试验证原理，不证明真实市场计数 |
| 指标假设与敏感性 | `data/reference/china_skillworth.v1.yml`、`packages/analytics/src/skillworth_analytics/china_skillworth.py`、`docs/ANALYSIS_EVIDENCE.md` | C++ 第 3→第 35 和学习小时假设应怎样解释？ | 非个人学习实测，无逐情景公开聚合 |
| 数据质量 | `quality_snapshot.json`、`/methodology` | 角色／城市匹配率的 Silver 分母与 other 有何不同？ | Gold Benchmark 未完成，不能说 Precision／Recall／F1 |
| 只读发布 | `apps/web/src/worker.ts`、`apps/web/e2e/production-safe.spec.ts` | 为什么只给安全聚合，不公开岗位文本或在线优化？ | 本地门禁不是全面安全审计 |
| 可复现验证 | `.github/workflows/ci.yml`、Demo／production-safe E2E、pytest、Vitest | Demo、Real、Worker 分别验证什么？ | Real 需要未入 Git 的固定 artifact；远端结果以本轮 Draft PR CI 为准 |

## 成果与个人贡献边界

- **项目已有成果**：冻结 v6 分析、Final 5、管线、既有方法与公开安全聚合可由上表的代码和产物核验；这些证据本身不证明某个人独立完成。
- **本轮 Codex 实施**：S01–S09 的修复、展示、测试及文档整理由 Codex 在用户给定范围内执行，不能表述为本人全部独立手写或独立计算。
- **本人可如实认领的本轮行为**：提出本轮目标、限制和验收要求，并决定是否接受审查结果；如实际进行了代码复核或测试验收，可据可追溯记录描述具体审阅工作，不能预先把尚未发生的审阅写成已完成。
- **待本人确认的历史贡献**：需求与口径的原创决策、清洗和人工去重审阅、历史代码作者、AI 生成代码的实际审查范围，均需本人核对并补充原始记录；不推断贡献比例。
- 30 条岗位的历史人工 sanity check 是有限抽查，不是正式 Gold Benchmark；AI 整理案例不能签署人工评测。

## 可用于简历的待审阅文案

1. 围绕公开招聘补充样本，搭建可追溯的数据处理与分析展示链路，区分 1,142 条 Silver、1,140 个 all-active canonical 岗位和 998 个 180d 岗位的统计口径。**先核对本人实际参与范围。**
2. 设计并解释需求覆盖、学习投入假设与排名敏感性的证据边界；用 C++ 需求第 3、SkillWorth 第 35 的同窗口案例说明“热门”与“优先学习”不同。**先核对本人在方法设计中的实际贡献。**
3. 为只读聚合页面建立 Demo 与本地 Worker 的确定性验证，覆盖岗位切换、WebGL 降级、原始资产阻断和写入拒绝。**本轮代码由 Codex 辅助实现，表述时应说明本人审阅与验收的具体工作。**

作品集短文案建议：**“用单一公开补充招聘快照研究技术技能的需求与学习投入，在 180 天、998 个 canonical 岗位的固定窗口里展示有条件的排序和限制；公开版只提供预计算聚合。”** 不加入用户量、准确率、收益、企业落地或线上优化能力。
