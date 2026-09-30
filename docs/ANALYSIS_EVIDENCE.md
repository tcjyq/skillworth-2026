# 三个分析问题与 SQL 复核

版本：2026-09-29。数字均指 `freehire_china_tech_2026_08` 的 180d、Freehire 单一补充样本；来源访问日 2026-08-10，`PUBLIC_SAFE` 产物生成日 2026-08-29。页面以聚合响应取数，本页记录该固定版本的复核值。它不是实时中国市场结论。

## 1. 热门是否应该优先学习？

- **业务问题**：仅按岗位提及量安排学习，是否与当前模型排序一致？
- **样本／方法**：998 个 canonical 岗位、313 家公司、134 个观测技能；比较同一响应中 C++ 的 `demand_rank` 与 `skillworth_rank`，后者包含版本化的学习投入折减。
- **发现**：C++ 见于 92 个岗位，需求第 3；以约 260 小时的从零学习假设计算，SkillWorth 第 35。数字来自 `data/production-safe/current/skill_aggregates.json` 的 `180d:__global__`，对应 [冻结报告](../reports/skillworth/final_data_analysis.md) Finding 2。
- **限制／行动**：学习小时是模型假设，不是个人学习时长；应结合目标岗位、已有基础与具体职责再判断，不能推出“不值得学 C++”。

## 2. 某岗位方向的技能组合是什么？

- **业务问题**：DevOps 方向中，Kubernetes 与什么技能共同出现？
- **样本／方法**：DevOps 切片 21 个 canonical 岗位；`devops_kubernetes` 出现于 17 个岗位，与 Terraform 在 11 个岗位共同出现。使用同一 180d、`role_id=devops_engineer` 的只读聚合关系；来源为 `skill_aggregates.json` 与 `relation_aggregates.json`。
- **限制／行动**：21 个岗位不足以代表整个职业市场；共现不是因果或每个岗位的必备条件。将其作为岗位阅读线索，而不是自动生成学习顺序。

## 3. 什么时候不应该给排名？

- **业务问题**：稀疏角色切片还能给出精确优先级吗？
- **样本／方法**：技术产品经理方向在同一窗口只有 3 个岗位，主排名层为 0 项；已观察技能仍由接口保留。页面直接使用 `180d:technical_product_manager` 聚合。
- **限制／行动**：没有可计算排名不等于没有技能需求。先取得更多合法、独立的样本，再做角色级比较；不补造精确名次。

## SQL 与处理链

本地真实链路是导入原始行 → Silver 有效唯一记录 → Gold canonical 岗位 → `job_skills` → DuckDB Warehouse／Analytics → 安全聚合 → 页面。冻结报告记录 1,236 条 API 原始返回、1 条 schema invalid、93 条重复公开 slug、1,142 条 Silver、1,140 个 all-active Gold；质量安全快照的 `raw_row_count=1142` 是进入质量报告的管线行数，不能冒充 API 原始返回 1,236。180d 再过滤到 998 个 Gold 岗位。未在本轮重跑真实 ETL。

`packages/data-pipeline/src/app/warehouse.py` 在本地建仓时执行 `backend/app/sql/02_analysis_views.sql`，其中 `skill_demand` 使用 `COUNT(DISTINCT canonical_job_id)`。当前 China SkillWorth 排名则由 `packages/analytics/src/skillworth_analytics/china_skillworth.py` 读取 `jobs`、`SELECT DISTINCT canonical_job_id, skill_id FROM job_skills` 等输入，再按版本化配置计算；不能将历史 `skill_demand` SQL 视作线上 Worker 每次请求运行的查询。Worker 仅返回预计算 JSON。

主键和基数：`jobs.canonical_job_id` 唯一；一个 canonical 岗位可对应多条 Silver 来源映射，也可对应多项 `job_skills`。把 `job_source_map` 与 `job_skills` 直接连接再 `COUNT(*)` 会因来源映射重复而放大技能需求。过滤条件是当前 snapshot、`published_at` 对应 180d 和所选角色；岗位覆盖分母是同一窗口／角色内不同 canonical 岗位数。各窗口的 Python–SQL 共现可不同，不能把 180d 的 128 与其他窗口的 141 强行统一。

只用合成数据复核这个连接风险：

```powershell
.\.venv\Scripts\python.exe -m pytest tests/unit/test_sql_evidence.py -q
```

测试中 2 个合成 canonical 岗位都提及 Python，其中一个有 2 条 Silver 来源映射；连接后 `COUNT(*)=3`，`COUNT(DISTINCT canonical_job_id)=2`，岗位分母为 2。这证明 SQL 基数原理，不验证真实市场的 998 或排名；真实数值需用冻结 Real v6 artifact 与对应断言复核。

## 假设敏感性

安全聚合当前提供基准排名及 `sensitivity_rank_min/max`，没有公开逐情景排名表，因此方法页只显示范围。该固定 180d 样本中 Python 基准第 1、范围 1–2；SQL 第 2、范围 1–2；C++ 第 35、范围 18–50。情景按 `data/reference/china_skillworth.v1.yml` 改变需求／广度／协同权重与 `half_value_hours`（100、240），岗位样本不变；`half_value_hours` 改变不是对个人真实学习时间的测量，也不构成趋势预测。
