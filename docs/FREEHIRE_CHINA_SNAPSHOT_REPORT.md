# Freehire China Technical Snapshot 2026-08

## 1. Current Snapshot Identity

| 字段 | 当前值 |
| --- | --- |
| Snapshot ID | `freehire_china_tech_2026_08` |
| Processing version | `v6` |
| Access date | 2026-08-10（Asia/Shanghai） |
| Market scope | `china_open_tech_sample` |
| Source role | `china_supplementary` |
| Independent China market sources | 1（Freehire） |
| Default recency window | `180d` |
| Salary signal | `unavailable` |
| Trend signal | `unavailable` |

该固定快照已通过当前 Data Contract 完成 Raw → Bronze → Silver → Role/Skill Normalization → Dedup → Gold Data Layer → DuckDB → Analytics。它适合描述 **Freehire 当前可观察的中国技术岗位补充样本** 和验证 Portfolio Real Mode，但不代表完整中国招聘市场，也不升级为 China Core Market。

## 2. Current v6 Counts

| 口径 | Canonical jobs | Companies | Observed skills |
| --- | ---: | ---: | ---: |
| 默认 `180d` | 998 | 313 | 134 |
| `all-active` | 1,140 | 339 | 138 |

上游与 Pipeline 基础计数：

| 项目 | 当前值 |
| --- | ---: |
| API raw rows | 1,236 |
| API schema invalid rows | 1 |
| Duplicate public slugs | 93 |
| Unique valid / Silver rows | 1,142 |
| v6 Gold canonical jobs | 1,140 |
| v6 dedup merge reduction | 2 |
| Upstream ATS/catalogue labels | 38 |
| Data source count | 1（Freehire） |
| Artifact SHA-256 | `edae6443a3cc41660958dbb7bbe7f682c351ffc7cc582415fb392bdde9c60ea5` |
| 发布日期范围 | 2018-11-26 至 2026-08-10 |
| 发布日期覆盖 | 100% |

38 个 upstream ATS/catalogue labels 只用于 provenance，不是 38 个独立市场来源。

## 3. Dedup Audit and v6 Correction

v6 对同一固定 Silver / skills 输入中的 8 个既有 canonical merge groups 做了逐组 provenance 审计：

- 6 组确认是不同岗位并拆分；
- 2 组在当前证据下保守保留合并；
- all-active canonical jobs 从 v4 的 1,134 修正为 v6 的 1,140；
- 180d canonical jobs 从 v4 的 992 修正为 v6 的 998；
- 公司数与观测技能数保持为 all-active 339 / 138、180d 313 / 134。

审计决定的版本化真源为 `data/reference/freehire_dedup_audit_2026_08.v1.yml`。修正后的 Gold Data Layer、Warehouse、技能图、summary 和 visual-ready analysis 均从固定输入重建；Final 5 没有 substantive change。

## 4. Previous Processing Version

旧版 snapshot 文档中的 1,134 all-active、992 180d、8 个合并减少以及对应 Top 20 / coverage 表属于 **Previous processing version v4**，不再是当前结论。历史前后对比保留在 `reports/skillworth/final_data_analysis.md`，其中明确标注 v4 与 v6。

当前发布口径只使用本报告第 1–3 节的 v6 数字。不得把历史 v4 数字标记为 Current、Latest、Now 或 Present。

## 5. Use and Access Boundary

- 上游：`strelov1/freehire`，审计 revision `d7ab8697635528b47cea719a590eac485e1dfa2c`。
- 使用状态：`no_explicit_block_found`；这不是完整招聘文本的再分发授权。
- Connector 仅使用文档化、无需认证的公开 read API；没有登录、Cookie、Session、Token、验证码、代理规避、私有接口或限流绕过。
- API 页面串行请求，429 遵守 `Retry-After`，5xx/网络错误退避；响应缓存并记录访问时间与 hash。
- 完整 JD 和 Real artifact 只保存在本地忽略目录，不进入代码仓库。
- Freehire 软件采用 MIT，不代表其聚合的第三方岗位内容采用 MIT；第三方内容权利与 SkillWorth 代码许可相互独立。

## 6. Unavailable Signals and Limitations

- Salary：`salary_signal=null/status=unavailable`。不做静默换汇、标题估薪、全球薪资代入、LLM 猜测或缺失值填补。
- Trend：`trend_signal=null/status=unavailable`。单一 snapshot 的 90d / 180d / 365d / all-active recency windows 不是独立时间序列。
- Representativeness：只有一个 supplementary source，不能外推完整中国技术招聘市场。
- Role / Skill：规则归一和抽取存在文本污染与长尾误差；正式 Gold Benchmark 未完成前不得声称 Precision、Recall 或 F1。
- Dedup：8 个已知 merge groups 的审计不等于全库重复岗位已经被完全消除。

## 7. Release Interpretation

v6 可用于当前冻结 V1 的聚合故事与 Real E2E。Final 5、公式、taxonomy、role taxonomy、learning hours、source set 和 robustness method 保持冻结。第二来源、独立时间快照、可比较人民币薪资与 Gold Evaluation 属于 Future / Independent research，不在本次治理同步中重新打开。
