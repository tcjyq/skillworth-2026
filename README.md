# SkillWorth 2026

## 2026，学什么技术最值？

SkillWorth 不只看招聘需求。它把 **Market Signal（市场信号）** 与透明的学习投入假设放在一起，帮助观察：下一项技术，值得投入多少时间？

本项目基于当前可观察的中国公开技术岗位补充样本，从市场价值与学习投入重新看技术技能的性价比。它是一件可复现的数据分析与交互可视化作品，不是完整中国招聘市场、就业承诺或权威排名。

## 为什么做这个项目

普通的热门技能排行榜回答：

> 市场上什么出现得多？

但学习者真正关心的是：

> 考虑需求、覆盖范围、技术协同和学习投入后，下一项技术最值得学什么？

**Demand ≠ Learning Priority（需求不等于学习优先级）。**

这正是 SkillWorth 与普通招聘市场 Dashboard 的区别：它不仅统计技能出现了多少次，还考察技能覆盖多少公司和岗位类型、与其他技能如何共同出现、证据是否稳定，以及从零学习所需投入的模型假设。

## 数据概览

当前公开分析使用冻结的 v6 数据：

| 口径 | 规范岗位 | 公司 | 观测技能 |
| --- | ---: | ---: | ---: |
| 默认 `180d` 窗口 | 998 | 313 | 134 |
| `all-active` 全部活跃记录 | 1,140 | 339 | 138 |

| 项目 | 当前口径 |
| --- | --- |
| Snapshot | `freehire_china_tech_2026_08` |
| Market scope | China Open Tech Sample（`china_open_tech_sample`） |
| Source role | `china_supplementary` |
| 独立市场来源 | 1（Freehire） |
| Salary | `unavailable` |
| Trend | `unavailable` |

这些数据是 **Freehire 当前可观察的中国技术岗位补充样本**，不代表完整中国技术招聘市场。数据中记录的 38 个 upstream ATS/catalogue labels 用于来源追踪，不是 38 个独立市场来源。

数据来源、访问方式与授权边界见 [DATA_SOURCES.md](docs/DATA_SOURCES.md) 和 [FREEHIRE_USAGE_AUDIT.md](docs/FREEHIRE_USAGE_AUDIT.md)。

## 五个主要发现

### 1. 效率前沿：Python → SQL → Git

在当前候选门槛和学习投入假设下，Python、SQL、Git 构成可发布的效率前沿：在不同投入水平上，它们提供了更高的市场信号。

| 技能 | Market Signal | 预期学习投入 | SkillWorth | 排名 |
| --- | ---: | ---: | ---: | ---: |
| Python | 48.05 | 160h | 24.03 | #1 |
| SQL | 36.32 | 100h | 22.35 | #2 |
| Git | 21.68 | 55h | 16.13 | #3 |

这里的小时数是“从零达到可用于初级岗位任务”的透明模型假设，不是精确课程时长，也不是对个人学习结果的承诺。

### 2. 高需求不自动等于高 SkillWorth

C++ 是最清楚的反例：

| 指标 | C++ |
| --- | ---: |
| 岗位数 | 92 |
| 需求排名 | #3 |
| 公司数 | 48 |
| Market Signal | 24.76 |
| 预期学习投入 | 260h |
| SkillWorth | 9.43 |
| SkillWorth 排名 | #35 |

这并不表示“C++ 不值得学”。更准确的结论是：**在当前从零学习投入假设下，C++ 的高市场需求没有转化成同样高的 SkillWorth 排名。**

### 3. 目标岗位改变，答案也会改变

不存在一个适用于所有技术岗位的最佳学习顺序。

| 角色切片 | 技能 | 角色内覆盖 | 全局排名 → 角色排名 |
| --- | --- | ---: | ---: |
| DevOps，n=21 | Kubernetes | 17/21 = 80.95% | #18 → #1 |
| DevOps，n=21 | Terraform | 11/21 = 52.38% | #33 → #3 |
| Data Engineer，n=38 | Apache Spark | 22/38 = 57.89% | #19 → #3 |
| Data Engineer，n=38 | Kafka | 12/38 = 31.58% | #23 → #5 |

这些结果说明职业目标会改变技能优先级，但 `DevOps n=21` 和 `Data Engineer n=38` 都是有限样本，不能包装成完整市场定论。

### 4. 技能往往以技术栈出现

在 `all-active` 的 1,140 个 canonical jobs 技能图中：

| 技能组合 | 共同出现的岗位 | Jaccard | PMI | 主要含义 |
| --- | ---: | ---: | ---: | --- |
| Python–SQL | 141 | 0.3431 | 0.8565 | 规模强，搭配广泛 |
| NumPy–Pandas | 12 | 0.6667 | 4.1255 | 亲和度强，更专业化 |
| Grafana–Prometheus | 11 | 0.5789 | 4.0385 | 亲和度强，更专业化 |

`co-occurrence count` 回答“共同出现了多少次”；Jaccard 和 PMI 更关注“两项技能彼此关联得有多紧”。因此 Python–SQL 可以在规模上更强，而 NumPy–Pandas、Grafana–Prometheus 在专业亲和度上更突出。

共现只表示当前样本中的关联，不代表因果关系，也不表示这些技能必须一起学。

### 5. 相信稳健核心，不迷信每一个名次

SkillWorth 用多个权重和学习投入情景检查排名对模型假设是否敏感：

| 相对稳定的头部 | 排名区间 | 对假设敏感的技能 | 排名区间 |
| --- | ---: | --- | ---: |
| Python | 1–2 | Tableau | 7–25 |
| SQL | 1–2 | RAG | 6–29 |
| Git | 3–4 | Azure | 8–27 |
| Docker | 3–4 |  |  |

头部存在一个 **Robust Core（稳健核心）**，但长尾的精确名次不应被当成确定事实。

作为辅助证据，180d 排名与 90d、365d、all-active 窗口的 Spearman 秩相关为 0.989–0.998。它不能被解释为 Trend：这些发布时间窗口高度重叠，而且协同信号共用 all-active 技能图。

## SkillWorth Frontier

Frontier 是本项目的标志性可视化：

- X 轴：Expected Learning Effort，越向左表示预期学习投入越低。
- Y 轴：Market Signal，越向上表示当前样本中的市场信号越强。
- 效率前沿：在不同投入水平下，没有被“学习投入更低且市场信号更高”的候选完全压过的技能。

Python 提供最高的市场信号，SQL 用更低投入取得较强信号，Git 则以更低投入保留有意义的市场支持，所以三者进入当前前沿。

Frontier 不是“科学证明最应该学什么”。它是在当前样本、候选门槛和显式学习投入假设下形成的决策辅助分析。

## SkillWorth 如何工作

第一步，把招聘市场中的多类证据合成为 Market Signal：

```text
Demand Strength（需求强度）
+ Company Breadth（公司覆盖广度）
+ Role Breadth（岗位类型广度）
+ Skill Synergy（技能协同）
+ Confidence（证据置信度）
                    ↓
              Market Signal
```

第二步，把市场信号和学习投入放在同一决策框架中：

```text
Market Signal + Expected Learning Effort
                    ↓
                SkillWorth
```

这些名称表达的是计算概念，不是另写的一套简化公式。真实公式、权重、门槛、分母、过滤条件与已知局限以 [METHODOLOGY.md](docs/METHODOLOGY.md) 为准；字段和空值语义见 [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)。

## 范围与限制

### 单一补充来源

当前中国样本主要来自 Freehire，独立市场来源仍然是 1。因此结果只能描述当前可观察样本，不能代表完整中国技术招聘市场。

### Salary：不可用

当前没有足够的可比较人民币薪资证据。`unavailable` 表示证据不足，不是数值 0；项目不会用职位标题猜测薪资或静默换汇。

### Trend：不可用

当前只有一个固定 snapshot。90d、180d、365d 是同一快照中的 posting recency windows，不是多期独立市场快照，因此不能产生增长、动量或趋势结论。

### Learning Effort：模型假设

学习时长是版本化、可查看的估算，用于比较投入情景。它不是客观学习周期，也不是个人完成课程所需时间。

### Role Coverage：细分样本有限

180d 窗口中有 523/998（52.40%）岗位被归为 `role=other`。角色细分发现应视为有限样本观察，尤其不能忽略 `DevOps n=21` 与 `Data Engineer n=38` 的分母。

### Skill Extraction：存在文本污染风险

当前采用版本化 taxonomy 和规则优先抽取。宽泛的 AI、Optimization 等词可能来自公司介绍或职位背景，而非明确技能要求；项目不宣称技能抽取达到研究级准确率。

### Dedup：经过审计，但不是“完全去重”

项目对已知 8 个 canonical merge groups 做了 provenance 审计：6 个误合并已纠正，2 个保守保留。这不等于所有重复岗位已经完全消除。

## 数据管道

```text
Raw
  ↓
Bronze（原始事实，只追加）
  ↓
Silver（标准化记录）
  ↓
Skill Extraction
  ↓
Dedup / Canonical Jobs
  ↓
Gold（分析实体）
  ↓
DuckDB Warehouse
  ↓
Analysis Views
  ↓
FastAPI
  ↓
Next.js
```

管道保留每条岗位记录的 provenance，使用固定快照和 source gating 控制可复现范围；去重后的 canonical job 仍能追溯原始来源。技能 taxonomy、质量报告和分析配置均版本化。未获得明确合法授权的数据源默认关闭，只允许手动导入或授权 Connector。

## 工程实现

项目后半部分支撑前面的分析结论，而不是在前端重复计算指标：

- **数据与分析**：Python、Parquet、DuckDB；Bronze / Silver / Gold 分层、数据质量检查、技能图与敏感性分析。
- **服务契约**：FastAPI、Pydantic；负责参数验证和查询编排，指标公式留在可测试的 analytics 模块。
- **交互可视化**：Next.js、React、TypeScript；展示 API 返回的真实分析结果，并处理筛选、空状态和响应式布局。
- **可追溯性**：固定 snapshot、source provenance、canonical job 映射和版本化配置。
- **测试**：pytest、Vitest、Playwright，覆盖数据管道、分析、API、组件和主要用户路径。

仓库目录职责与关键架构决策见 [ARCHITECTURE.md](docs/ARCHITECTURE.md)。项目还预留了人工 Gold Evaluation infrastructure，包括固定样本、评估器和标注工作区；V1 没有正式 Gold 结果，因此不发布 Precision、Recall 或 F1。

## 测试状态

2026-08-21 重新核验的当前结果：

| 检查 | 结果 |
| --- | --- |
| Python test suite | 238 passed |
| ESLint | passed |
| TypeScript | passed |
| Vitest | 12 passed |
| Playwright | 44 passed，2 expected skipped |
| Next.js production build | passed，生成 20 个页面/路由 |

运行相同检查：

```powershell
.\.venv\Scripts\python.exe -m pytest
Set-Location apps\web
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

`npm run test:e2e` 会从已提交的 `data/demo` 合成 fixture 重建隔离的 Demo 数据，不依赖本机 Real 数据。冻结 Freehire v6 数据故事验证使用 `npm run test:e2e:real`；该命令要求本地存在 `data/modes/freehire/current.json`，或通过 `SKILLWORTH_REAL_MODE_MANIFEST` 指向等价的本地 manifest。

## 本地运行

Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
Set-Location apps\web
npm ci
```

复制 `.env.example` 后启动 Demo API：

```powershell
Set-Location ..\..
$env:PYTHONPATH='packages/data-pipeline/src;packages/analytics/src;apps/api/src'
$env:SKILLWORTH_DATA_MODE='demo'
.\.venv\Scripts\python.exe -m uvicorn skillworth_api.main:app --host 127.0.0.1 --port 8011
```

另开终端启动 Web：

```powershell
Set-Location apps\web
$env:SKILLWORTH_API_URL='http://127.0.0.1:8011'
npm run dev
```

浏览器打开 `http://127.0.0.1:3000`。Real Mode 需要本地已构建且不进入版本控制的 manifest；不要提交真实 Raw / Bronze / Silver / Gold 数据。

## 后续研究

- 按月保存相互独立的 snapshot，才能分析真实 Trend。
- 增加第二个许可清晰的中国来源，增强跨来源证据。
- 补充更丰富、可比较的人民币薪资证据。
- 可选地完成正式人工 Gold evaluation。

## 数据归属与代码许可

Freehire 的数据来源说明和访问边界见 [DATA_SOURCES.md](docs/DATA_SOURCES.md)、[FREEHIRE_USAGE_AUDIT.md](docs/FREEHIRE_USAGE_AUDIT.md) 与 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。第三方招聘文本的权利与项目代码许可相互独立；未来采用某种代码许可证，也不会自动获得第三方 JD 的再分发授权。

SkillWorth 自主创作的源代码与项目文档采用 [MIT License](LICENSE)。该许可不覆盖第三方软件、招聘文本、外部数据集、商标或其他第三方内容；这些内容仍受各自许可、条款和权利边界约束，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## Git 基线 provenance

本仓库 Git 历史自 2026-08-24 重建基线开始；此前开发历史未能恢复，因此无法对基线之前的 Git 历史进行完整审计。

Git history begins from the reconstructed baseline established on 2026-08-24. Earlier development history was not recoverable.
