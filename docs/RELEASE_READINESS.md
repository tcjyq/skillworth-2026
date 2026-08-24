# SkillWorth 2026 Release Readiness

审计日期：2026-08-24（Asia/Shanghai）

审计范围：Project Governance & Documentation Sync；不含新数据源、Gold annotation、算法、分析结果或产品 UI 变更。

当前结论：**数据、分析、复现链路、本地 Git 基线与权利边界通过；正式首页仍等待人工视觉批准与 V2 提升决定。**

## 1. Current Release State

| 项目 | 当前事实 |
| --- | --- |
| Product | V1 Data / Analysis / Story frozen |
| Homepage | Production candidate 位于 `/lab/visual-v2`；正式 `/` 尚未替换 |
| Snapshot | `freehire_china_tech_2026_08`，Real v6 |
| Market scope | `china_open_tech_sample` |
| Source role | `china_supplementary` |
| Default window | `180d` |
| 180d | 998 canonical jobs / 313 companies / 134 observed skills |
| all-active | 1,140 canonical jobs / 339 companies / 138 observed skills |
| China supplementary market sources | 1（Freehire） |
| Salary | `unavailable` |
| Trend | `unavailable` |
| Representativeness | 不代表完整中国技术招聘市场 |

Final 5、公式、taxonomy、role taxonomy、dedup、learning hours、source set 与 robustness method 均保持冻结。本轮没有修改任何分析结果。

## 2. Release Gates

### Data / Analysis — PASS

- Real v6 已冻结，默认 180d 与 all-active 口径已写入当前文档。
- Final 5 保持不变，来源范围、分母、Salary/Trend 不可用和代表性限制已披露。
- 8 个既有 dedup merge groups 已审计：6 个拆分，2 个保守保留合并。

### Product — PENDING

- 等待最终人工视觉批准。
- 等待决定是否将 `/lab/visual-v2` 提升到正式 `/`。
- Candidate 不是 final homepage；本轮禁止自动提升。

### Reproducibility — PASS

- `npm run test:e2e`：从版本化 `data/demo` 重建隔离、确定性的 Demo fixture，不要求本地 Real 数据。
- `npm run test:e2e:real`：验证本地私有 Freehire v6 manifest 与冻结 Real assertions；Real artifact 不进入 Git。
- Demo 与 Real 命令、数据依赖和测试选择已明确分离。

### Git — PASS

- `main` 已通过 `--ff-only` 集成已验证 hardening commit `327453944823b993399dc9a9f99f63a2d7d2ca1d`。
- 本地历史从 2026-08-24 reconstructed baseline `265f40c9044a57c2c0a02c3847fa2de9ef037546` 开始。
- 更早开发 Git 历史未能恢复；不得 amend、rebase 或重写 reconstructed baseline。

### Remote — PENDING

- 当前没有 GitHub remote。
- 本轮不创建 remote、不 push。

### License / Data Rights — PASS

- 根目录 MIT 仅覆盖 SkillWorth 自主创作的代码与项目文档。
- Freehire 软件的 MIT 许可不等于招聘内容采用 MIT。
- 第三方招聘文本、外部数据集、商标和其他第三方内容保留各自权利与使用边界。

### CI — PENDING

- 当前没有版本化 CI workflow。
- 本地完整验证可作为当前 release evidence，但不应描述为已建立持续集成。

### README Asset — PENDING

- 最终产品截图等待正式首页决定。
- 本轮不添加截图、部署 badge、release version badge 或 remote link。

### Gold Evaluation — NOT V1 BLOCKER

- Gold Data Layer 是 Bronze / Silver / Gold 管道中的分析就绪数据层。
- Gold Benchmark / Gold Labels 是人工评测 ground truth；当前正式评测尚未完成。
- 标注批次、evaluator 与 annotation workspace framework 已存在，但 framework 存在不等于正式评测完成。
- Gold Evaluation 属于 Future / Independent research，不阻止当前 V1 发布决策。
- 在人工评测达到既定协议前，禁止声称技能抽取、角色归一或去重的 Precision、Recall、F1。

## 3. Verification Evidence

本轮文档同步后的完整验证以本节为唯一 release gate 统计来源：

| Check | Result |
| --- | --- |
| pytest | 239 passed，1 条既有 Starlette/httpx deprecation warning |
| pip check | passed |
| ESLint | passed |
| TypeScript | passed |
| Vitest | 17 passed |
| Next.js production build | passed |
| Demo E2E | 30 passed |
| Real E2E | 61 passed，3 项设备条件 skip，0 failed |

标准命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
Set-Location apps\web
npm run lint
npm run typecheck
npm run test -- --run
npm run build
npm run test:e2e
npm run test:e2e:real
```

`test:e2e:real` 仅在本地 Freehire v6 manifest 与依赖 artifact 可用时运行。任何 frozen Real Finding assertion 回归都必须停止发布流程。

## 4. Remaining Release Blockers / Decisions

### 发布前人工决定

1. 最终人工视觉批准。
2. 决定是否将 V2 candidate 从 `/lab/visual-v2` 提升到 `/`。
3. 首页决定后选择 README 最终产品截图。

### 仓库运营待办

1. 建立 GitHub remote。
2. 建立 CI workflow。

这些待办不会授权本轮自动 promote、截图、创建 remote、push 或 deploy。Gold Evaluation 明确不是 V1 blocker；Salary、Trend 和完整市场代表性仍为产品限制，必须持续披露。
