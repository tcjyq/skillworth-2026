# Target Market Coverage Report

生成依据：当前 Real Dataset Mode 最新快照；Silver 451 条，Canonical Job 388 条。报告中的目标市场分类是透明标题规则审计，不是人工 Gold Label，也不用于直接修正 Role Taxonomy。

## 结论

当前 99.23% `other` 的主要原因是 **C：数据源市场构成与 Role Taxonomy recall 共同造成**。

- 数据源不完全属于目标市场：388 个 Canonical Job 中，明确目标岗位 26（6.70%），可能属于目标市场 192（49.48%），明确非目标岗位 170（43.81%）。明确非目标占比已超过配置的 25% 证据阈值。
- Taxonomy recall 明显不足：26 个明确目标标题中有 23 个仍被当前规则归为 `other`，代理漏识别率为 88.46%。这不是正式 Recall；正式 Recall 必须由人工 Role Gold Set 计算。
- 当前 Role 输出为 `other=385`、`product_manager=2`、`data_analyst=1`，即 `other=99.23%`。

因此，不能仅扩充 taxonomy 来“降低 other”，也不能把全部 `other` 解释为数据源错误。下一步必须先完成人工分层标注。

## 数据依据

### 标题与公司

Top title 包括：Customer Quality Engineer 6、Process Quality Engineer 6、ME Engineer 5、Application Engineer 4、Customer Planner 4、Supplier Quality Engineer 4。标题共 336 个不同值，制造、质量、供应链与工厂运营岗位占据显著份额。

Canonical company 仅有两家：`zf.com` 350（90.21%），`bosch.com` 38（9.79%）。这说明当前数据高度集中于汽车工业企业，不能代表中国整体数字化招聘市场。

### 行业与 JD 特征

- 汽车/工业线索：324 / 388（83.51%）。
- 质量/运营线索：177 / 388（45.62%）。
- JD 技术关键词覆盖：342 / 388（88.14%）。该值不能解释为目标技术岗位覆盖，因为公司介绍和工业技术语境会引入大量技术词。
- 非空 JD：385 / 388；标准化字符中位数 2,278；英文主导 377 / 388。
- 高频模板包括 `Req ID`、`Your tasks`、`Your profile`、`ZF is a global technology company` 和 `Become our next FutureStarter`。模板文本会污染仅基于 JD 关键词的市场归属判断。
- 至少抽取到一个技能的 Canonical Job：145 / 388（37.37%）。技能命中不等同于岗位属于 SkillWorth 目标市场。

### 来源构成

唯一来源为 `techsalerator_china_jobs_v1`：Silver 451、Canonical 388。当前没有跨来源代表性，也无法用该快照验证跨平台采样偏差或跨平台 Dedup。

## 限制

本报告是待标注样本分层工具，不是市场份额估计。`possible` 类占 49.48%，其不确定性很高；在人工 Gold Set 完成前，不应据此对中国技术招聘市场作外推。
