# SkillWorth Live Web

SkillWorth Live 的 Next.js 前端。业务数据统一通过 `/backend-api/*` 转发到 FastAPI；前端不包含分析结果 fixture 或静态市场数字。

完整环境、数据链和启动说明见仓库根目录 [README](../../README.md)。

常用命令：

```powershell
npm ci
npm run dev
npm run lint
npm run typecheck
npm run test
npm run build
npm run test:e2e
```

默认后端地址为 `http://127.0.0.1:8011`。需要覆盖时，在构建或启动前设置 `SKILLWORTH_API_URL`。
