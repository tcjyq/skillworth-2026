# SkillWorth 2026 本地审阅状态

更新：2026-09-29（Asia/Shanghai）。[2026-08-24 的历史就绪记录](archive/RELEASE_READINESS_2026-08-24.md)保留原文供追溯；其中“无 remote／无 CI／候选页尚未提升”的表述不再代表当前仓库。

## 当前已核对的事实

- 基线 HEAD：`c484c93456c32aaade5aca6145ee9e167869ef96`；本轮在 `codex/skillworth-optimization-2026` 分支。提交、Draft PR 与远端 CI 状态以 GitHub 记录为准；本轮不 merge 或 deploy。
- 正式 `/` 和 `/lab/visual-v2` 当前均使用 Visual V2；`/skill-field` 是独立动态加载的探索页。首页已提升的历史审批过程不能仅凭本轮代码还原。
- `origin` 指向 `https://github.com/tcjyq/skillworth-2026.git`；版本化 CI 位于 `.github/workflows/ci.yml`。本文件只记录本地验证，远端运行结果以对应 Draft PR 的 CI 为准。
- 冻结快照 `freehire_china_tech_2026_08`：180d 为 998 canonical 岗位／313 公司／134 观测技能；all-active 为 1,140／339／138。唯一中国补充来源为 Freehire，不代表完整市场。
- 本地 Python 管线、DuckDB、FastAPI 支持完整数据处理与分析；公开 Worker 只读取 `PUBLIC_SAFE` 预计算聚合。公开站点不提供岗位级优化、写入或完整原始招聘文本分发。Salary、Trend 和正式人工 Gold 评测仍不可用。
- 实际发布构建为 `npm run build:vinext`；`npm run build` 验证 Next 路径，不能代替 Worker 构建。本轮 CI 增加本地 vinext Worker 上的 production-safe E2E。
- 旧 V1 首页 E2E 已保存在 `apps/web/e2e/archive/skillworth-2026.legacy.ts`，其断言针对当前已不存在的首页 DOM；当前首页由 Visual V2 测试与 production-safe 门禁验证。历史测试未删除，也不计入当前通过数。

## 本轮验证记录

以下为本地分支的 2026-09-29 结果；远端 CI 结果须另行查看对应 Draft PR。历史 [2026-08-24 记录](archive/RELEASE_READINESS_2026-08-24.md)中的测试数量不能沿用。

| 检查 | 本地结果 |
| --- | --- |
| pytest | 245 passed、0 skipped、1 条 Starlette/httpx 弃用警告；Windows 使用短 D 盘 `--basetemp` 避开系统临时目录权限与长路径问题 |
| pip check | passed |
| ESLint / TypeScript | passed / passed |
| Vitest | 14 文件、85 passed |
| Next production build | passed |
| vinext build + 本地 Worker production-safe E2E | build passed；7 passed、1 skipped（岗位竞态用例仅桌面执行） |
| Demo E2E | 55 passed、7 skipped；仅 Real v6 才有意义的用例按模式跳过 |
| Real v6 E2E | 72 passed、6 skipped；冻结样本与关键排名断言通过 |
| `project-constitution` validator | PASS，157 行 |

当前检查命令：

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pip check
Set-Location apps\web
npm run lint
npm run typecheck
npm run test -- --run
npm run build
npm run build:vinext
npm run test:e2e
npm run test:e2e:production-safe
```

`test:e2e` 重建确定性 Demo；`test:e2e:production-safe` 使用已版本化安全产物、本地 vinext 构建和 Wrangler runtime，不调用生产密钥或部署。`test:e2e:real` 仅在未入 Git 的 Real v6 manifest 完整可用时执行；任何冻结断言失败都应停止发布治理。此门禁验证选定公开路径与只读边界，不等于全面安全审计、线上可用性或真实 GPU 设备测试。

本地 vinext 与 Next 会写入同一 `.next/types` 目录；若紧接 vinext 构建单独运行 `npm run typecheck`，可能读到混合生成的路由声明。本轮按 CI 顺序完成 Next build 后重跑 TypeScript 检查，结果通过；不把第一次由构建缓存导致的报错记作源码通过。

本地 Windows 上如默认 pytest 临时目录无权限或因项目路径较长触发 `FileNotFoundError`，可使用未占用的短 D 盘目录运行 `-p no:cacheprovider --basetemp D:\<short-unique-dir>`；这不改变测试断言。旧 V1 首页测试归档的原因是路由 DOM 已由 Visual V2 取代，并非将当前失败测试改为 skip。现有 6 个 Real E2E skip 仍按设备／场景条件保留。

## 待审阅事项

1. 本轮代码以 Draft PR 供审阅；提交与推送已获授权，merge 与 deploy 未获授权。
2. 正式人工 Gold Benchmark 未完成，不发布 Precision、Recall 或 F1。
3. 新来源、Salary、Trend 和真实目标用户任务观察属于独立后续研究，不能填入当前成果。
