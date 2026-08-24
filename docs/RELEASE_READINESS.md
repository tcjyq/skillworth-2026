# SkillWorth 2026 Release Readiness

审计日期：2026-08-11（Asia/Shanghai）  
审计范围：Pre-Release Hardening，不含新数据源、算法、Taxonomy、Source Gate、Confidence 或产品功能变更。  
当前结论：**Release Candidate 技术回归通过；公开 V1 仍有 P1 人工与治理前置项。**

## 1. 当前公开口径

- 产品：SkillWorth 2026。
- Market scope：`china_open_tech_sample`。
- Source role：`china_supplementary`。
- Snapshot：`freehire_china_tech_2026_08`。
- 默认窗口：`180d`。
- 真实窗口规模：992 个 canonical jobs、313 家公司、134 项观测技能。
- 首页主榜：12 项 `main + robust + high_skillworth_candidate`。
- Salary：`unavailable`。
- Trend：`unavailable`。
- Disclaimer：当前公开技术岗位补充样本，不代表完整中国招聘市场。

## 2. 本轮已完成

### Visual / Rendered QA

- 公开 UI 保持 `VISUAL FREEZE V1`，没有新增页面、区块、指标或信息架构。
- 已验证首页、Role/Recency Filter、Bubble/键盘替代入口、Drawer、Market Board、Theme、Data Scope、Methodology、移动 Bottom Sheet、API failure 和 reduced motion。
- 新增浏览器断言：主路径无 console warning/error、无失败 API 请求；减少动态偏好关闭 Hero 位移和长时动画。
- Drawer 关闭时会取消尚未完成的角色证据请求；现有缓存、真实数据和显示语义不变。

### Gold Benchmark readiness

`python -m app.cli benchmark-status` 当前结果：

| Benchmark | Pending | Unlabeled | Gold | Development | Held-out test | Configured minimum Gold |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Skill | 100 | 100 | 0 | 27 | 73 | 300 |
| Role | 100 | 100 | 0 | 26 | 74 | 300 |
| Dedup Pair | 100 | 100 | 0 | 24 | 76 | 300 |

三类批次均通过 ID 唯一性、稳定 ID、确定性 split、Prediction/Gold 字段分离和 notes 字段检查。当前状态仍为 `INSUFFICIENT BENCHMARK DATA`，没有输出虚构指标，也没有写入 Gold Label。

仓库没有 Annotation UI，因此自动保存、断点续标、历史标签编辑、快捷键和显式 ambiguous/uncertain 状态不可用。当前人工标注准备度为 **NOT READY**。

### Repository / dependency safety

- 未发现 API key、Token、Cookie、Session、CSRF、凭据或私钥实值。
- `.gitignore` 已覆盖真实 Raw/Bronze/Silver/Gold、外部数据集、Freehire/Real snapshots、Benchmark pending/report、`data/annotation_batches`、Playwright、`.qa`、缓存、日志和构建产物。
- 已补充无密钥的 `.env.example`；文档中的本机用户名绝对路径已移除。
- 本地大型数据和完整 JD 只存在于忽略目录；没有删除本地正式数据。
- npm audit：0 vulnerabilities；Python `pip check`：无依赖冲突。
- `@playwright/test` 从 1.55.0 升至安全补丁 1.55.1；Vitest 从 3.2.4 升至 3.2.7。
- E2E 改用可复用的直接子进程启动器，健康检查后运行 Playwright，并在 `finally` 回收明确子进程；验证结束后 18011/13001 均无监听残留。

限制：当前工作区没有 `.git` 元数据，无法执行 `git status`、`git ls-files` 或历史机密扫描。文件系统扫描与忽略规则通过，但发布前必须在实际 Git 仓库中再次验证 tracked files。

### Documentation

- README 已改为发布候选稿，优先说明产品问题、真实范围、Frontier、稳健排名、Market Themes、Benchmark、架构和本地运行。
- PRD 的公开信息架构已更新为 SkillWorth 2026 + Methodology / Data Scope；旧八页能力明确归入 `/lab/*`。
- ARCHITECTURE 已移除“Next.js 尚未开始”的过期表述。
- BENCHMARKS 已从错误的 120/120/120 修正为真实 100/100/100，并记录 `benchmark-status` 与缺失的标注 UI 能力。
- 历史审计报告保留其日期与当时阶段，不改写历史结论。

## 3. Release blockers

### P0 — Block release（0）

无。没有发现会导致数据造假、敏感信息泄露、公开范围错误或主路径不可用的自动化阻断项。

### P1 — Should fix before V1（4）

1. **Human Gold Benchmark 未完成**：Skill/Role/Dedup Gold 均为 0；每类质量门禁要求至少 300，且必须保留未触碰 held-out test。
2. **Annotation workflow 不可直接使用**：没有 UI、自动保存、断点续标、历史编辑、快捷键及显式 ambiguous/uncertain 状态；本轮按约束没有新造 Annotation UI。
3. **仓库级 LICENSE 未选择**：项目代码不能在没有权利人决定的情况下被描述为开源。
4. **Git tracked/history 未验证**：当前目录没有 `.git`，无法确认真实数据、截图或旧密钥从未被跟踪；发布前必须在目标 Git 仓库中复核。

### P2 — Post-release / V1.1（2）

1. Skill Drawer 首次打开某技能/窗口时会并行查询 8 个角色切片。当前已有缓存、关闭取消和失败降级；若要消除 fan-out，需要新增聚合 API 契约，本轮未扩展 API。
2. pytest 有 1 条 Starlette `TestClient` / `httpx` 生态弃用警告；当前 223 项测试通过，待上游迁移路径稳定后升级。

### P3 — Optional（1）

1. README 尚未提交一张经过人工挑选的公开首页静态截图；不影响运行、数据语义或测试。

## 4. Regression evidence

| Check | Result |
| --- | --- |
| pytest | 223 passed，1 upstream deprecation warning |
| ESLint | passed |
| TypeScript | passed |
| Vitest | 11 passed |
| Playwright | 40 passed，2 desktop skips（移动专用测试） |
| Next.js production build | passed，20 routes |
| npm audit | 0 vulnerabilities |
| pip check | no broken requirements |

## 5. Release decision

工程回归、公开 UI、真实 API 路径、仓库忽略规则和依赖安全已达到 Release Candidate 状态，`VISUAL FREEZE V1` 保持有效。由于 Gold Benchmark、Annotation workflow、项目 LICENSE 和目标 Git tracked-files 审计仍未完成，当前不应标记为完成公开 V1，也不得称为生产级劳动力市场决策系统。
