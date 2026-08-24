# Freehire China Technical Snapshot 2026-08

## 1. 结论

固定快照已通过现有 Data Contract 完成 Raw → Bronze → Silver → Role/Skill Normalization → Dedup → Gold → DuckDB → Analytics。它适合用于 **中国公开技术岗位补充样本** 和 Portfolio Real Mode 验证，但仍不是完整中国招聘市场，也不升级为 China Core Market。

产品范围固定为：

- `market_scope=china_open_tech_sample`
- `source_role=china_supplementary`
- `snapshot=2026-08`
- 免责声明：该样本来源于 Freehire 当前可观察的中国技术岗位，不代表完整中国招聘市场。

## 2. 使用与访问边界

- 审计日期：2026-08-10（UTC+8）。
- 上游：`strelov1/freehire`，revision `d7ab8697635528b47cea719a590eac485e1dfa2c`。
- 使用状态：`no_explicit_block_found`，不是完整招聘文本再分发授权。
- 仅使用文档化、无需认证的公开 read API；没有登录、Cookie、Session、Token、验证码、代理规避、私有接口或限流绕过。
- API 页面串行请求，默认间隔 0.5 秒；429 遵守 `Retry-After`，5xx/网络错误指数退避；响应逐页缓存并记录访问时间与 hash。
- 完整 JD 仅保存在本地忽略目录，不随代码仓库发布。

## 3. Snapshot 元数据

| 项目 | 结果 |
| --- | ---: |
| API raw rows | 1,236 |
| API schema invalid rows | 1 |
| duplicate public slugs | 93 |
| unique valid rows | 1,142 |
| Pipeline valid rows | 1,142 |
| Canonical jobs | 1,134 |
| Dedup 合并减少 | 8（0.70%） |
| Companies | 339 |
| Skill taxonomy hits | 138 skills |
| Upstream ATS/catalogue labels | 38 |
| Data source count | 1（Freehire） |
| Artifact SHA-256 | `edae6443a3cc41660958dbb7bbe7f682c351ffc7cc582415fb392bdde9c60ea5` |
| 发布日期范围 | 2018-11-26 至 2026-08-10 |
| 发布日期覆盖 | 100% |

38 个 upstream labels 是 provenance，不被当成 38 个独立、合格的市场来源。

## 4. 数据覆盖与 Source Gate

| 指标 | 结果 |
| --- | ---: |
| Description coverage | 99.47% |
| Freehire structured skills coverage | 77.58% |
| SkillWorth extracted-skill job coverage（全量） | 71.52% |
| SkillWorth extracted-skill coverage（target） | 81.90% |
| Location coverage | 99.65% |
| Salary structured evidence（任一字段） | 4.29% |
| Salary min+max 同时存在 | 0.96% |
| 可比较人民币月薪 coverage | 0% / unavailable |

Target Market Scope 分布：`target=580`（51.15%）、`possible=532`（46.91%）、`non_target=22`（1.94%）。按未调整的现有数值 Gate，样本量、target ratio、skill coverage 与最新发布日期条件通过；但 Source Role 仍依据来源代表性审计保持 `supplementary_market`，不会因数值 Gate 通过自动升级为 core market。

Role normalization 中 `other=593`，其余主要为 product manager 179、backend 50、data engineer 44、AI engineer 37、ML engineer 37、data scientist 28、fullstack 27、data analyst 24、software engineer 24、DevOps 23。这个结构提示 Freehire 技术类别与 SkillWorth Role Taxonomy 仍有明显口径差异，不能把类别筛选等同于精确角色标注。

## 5. Market Signal 与 SkillWorth Top 20

| # | Skill | Jobs | Coverage | Market Signal | 学习时长估算 | SkillWorth | Confidence | 敏感排名范围 |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Python | 363 | 32.01% | 47.62 | 160h | 23.81 | 56.06 | 1–2 |
| 2 | SQL | 186 | 16.40% | 36.18 | 100h | 22.27 | 55.31 | 1–2 |
| 3 | AI | 404 | 35.63% | 47.02 | 240h | 18.81 | 57.61 | 3–6 |
| 4 | Git | 47 | 4.14% | 23.75 | 55h | 17.67 | 47.81 | 3–8 |
| 5 | Agile | 107 | 9.44% | 25.39 | 70h | 17.66 | 49.86 | 4–5 |
| 6 | Optimization | 234 | 20.63% | 34.87 | 180h | 16.41 | 53.65 | 4–13 |
| 7 | Docker | 59 | 5.20% | 25.72 | 100h | 15.82 | 49.69 | 4–9 |
| 8 | Excel | 113 | 9.96% | 24.95 | 100h | 15.35 | 51.72 | 6–12 |
| 9 | Power BI | 70 | 6.17% | 24.77 | 100h | 15.24 | 50.27 | 7–11 |
| 10 | Machine Learning | 250 | 22.05% | 37.83 | 260h | 14.41 | 53.86 | 7–17 |
| 11 | PowerPoint | 67 | 5.91% | 18.53 | 60h | 13.48 | 47.70 | 10–14 |
| 12 | AWS | 93 | 8.20% | 30.81 | 220h | 12.97 | 50.12 | 10–18 |
| 13 | Word | 37 | 3.26% | 14.68 | 35h | 12.05 | 41.22 | 11–24 |
| 14 | Tableau | 45 | 3.97% | 19.56 | 100h | 12.04 | 50.01 | 14–33 |
| 15 | Azure | 68 | 6.00% | 28.45 | 220h | 11.98 | 50.27 | 12–31 |
| 16 | Bash | 45 | 3.97% | 18.43 | 90h | 11.79 | 47.61 | 9–25 |
| 17 | Java | 96 | 8.47% | 27.95 | 220h | 11.77 | 46.11 | 14–26 |
| 18 | RAG | 52 | 4.59% | 21.70 | 140h | 11.58 | 47.16 | 15–40 |
| 19 | Linux | 74 | 6.53% | 24.17 | 180h | 11.37 | 47.80 | 17–39 |
| 20 | HTML | 19 | 1.68% | 14.57 | 45h | 11.37 | 37.39 | 7–29 |

Market Signal 排名前列是 Python、AI、Machine Learning、SQL、Optimization；加入学习成本后 SQL、Git、Agile、Docker 等较低时长技能上升。138 项技能中 94 项触发 Sensitive Ranking Warning，说明长尾排名高度依赖权重与学习时长假设，不适合展示成确定性榜单。

## 6. Skill Network 与外部对照

技能网络包含 138 个节点、1,204 条通过支持阈值的边。网络信号复用共现、Jaccard、PMI 与 centrality，没有使用 Embedding 或付费 LLM。

Qarera 固定 revision 的 250 行外部聚合中，61 项可映射技能与本快照重叠；描述性 rank correlation 为 `0.6095`，状态 `MEDIUM_AGREEMENT`。Google Cloud、Azure、Bash、Redis、Apache Spark、RAG 等差异较大。由于 Qarera 的收集范围、时间窗与分母不同，这只是外部一致性诊断，不证明 Freehire 或 Qarera 代表中国市场，也不改变内部排名。

## 7. 不可用指标与限制

- Salary：`salary_signal=null/status=unavailable`。不做汇率转换、标题估薪、全球薪资代入、LLM 猜测或缺失值填补。
- Trend：`trend_signal=null/status=unavailable`。单一 snapshot 不能产生增长、动量或趋势分类。
- Confidence：单一 supplementary source 且没有达标 Gold Benchmark，source diversity 与 cross-source agreement 受限；分数按现有 cap 保守处理。
- 日期：最新岗位为 2026-08-10，但尾部包含 2018 年旧记录；新鲜度必须按技能自身 posting-age 分布计算，不能只看最大日期。
- Role：大量 `other` 与 product 类岗位说明上游技术类别不等同于 SkillWorth 精确目标角色。

## 8. 最终判断

值得保留并继续按月构建受控快照，用于补充样本、技能共现和 Portfolio Real Mode；不应升级为 China Core Market。下一步应优先积累第二个许可清晰、结构独立的中国技术岗位来源，以及补足 Role/Skill/Dedup held-out Gold Benchmark，而不是扩大未经审计的数据采集范围。
