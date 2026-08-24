# Visual V2.1 QA

日期：2026-08-23（UTC+8）  
地址：`http://127.0.0.1:3000/lab/visual-v2`  
模式：Real Mode，Freehire 当前固定快照。

## 验证路径

`/lab/visual-v2` → 阅读 Hero 与 Final 5 → 搜索 React → 展开进阶指标 → 切换 19 个岗位方向 → 验证主排名层、已观察技能与低样本状态。

浏览器插件当前不可用，因此使用仓库现有 Playwright 配置和 Chromium/Edge 运行生产构建验收。

## 结果

| 检查 | 结果 |
| --- | --- |
| 页面身份与非空内容 | 通过 |
| Next.js 错误覆盖层 | 无 |
| Console error / warning | 0 / 0 |
| 失败请求 | 0 |
| 1440×900 桌面视觉 | 通过 |
| 390×844 移动视觉 | 通过 |
| 移动端横向溢出 | 0 px |
| Reduced Motion | 通过 |
| 全局技能集合 | 134 项；110 项进入主排名层、24 项仅观察 |
| 技能搜索与详情 | React 搜索、选择、进阶指标展开通过 |
| 角色筛选 | 19/19 均显示主排名层与已观察技能，没有空白画布 |
| 低样本状态 | 技术产品经理正确显示 0 项可排名、6 项仅观察、3 岗位及极低样本提示 |
| 方法与局限导航 | 页内锚点跳转通过；返回正式首页链接保持为 `/` |
| E2E | 11 项通过，1 项桌面专用检查在移动项目中按条件跳过，0 失败 |
| 单元测试 | 6 文件、12/12 通过 |
| TypeScript / ESLint / Build | 全部通过 |

## 视觉证据

文件位于 `apps/web/output/playwright/visual-v2-1/`：

- `hero-desktop.png`
- `story-desktop.png`
- `cpp-desktop.png`
- `role-desktop.png`
- `explore-desktop.png`
- `explore-search-react.png`
- `role-low-evidence.png`
- `hero-mobile.png`
- `explore-mobile.png`
- `motion-v2-1.webm`

## 仍需人工判断

自动化只能确认信息、数据状态、交互和布局正常；“是否形成足够强的视觉冲击”和“权威感是否达到目标”仍由下一轮人工体验决定。
