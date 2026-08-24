# Visual V2 验收记录

日期：2026-08-22（UTC+8）  
路由：`/lab/visual-v2`  
数据模式：`real`，使用 `data/modes/freehire/current.json`，样本为 998 个岗位。

## 概念稿对照

| 对照项 | 概念稿 | 实现 | 结论 |
| --- | --- | --- | --- |
| 首屏文案 | “2026，学什么技术最值？”及三项样本信息 | 文案、顺序和数字一致 | 通过 |
| 导航 | 数据范围、方法、退出实验 | 名称与目标一致 | 通过 |
| 画布 | 左侧叙事、右侧持续数据舞台 | 桌面端同一 SVG 舞台贯穿 Final 5 | 通过 |
| 视觉语言 | 墨黑、米白、酸性黄绿，青/紫分组 | 使用同一色彩和编辑式排版 | 通过 |
| 数据节点 | 技能点、排名变化、协同关系、稳健区间 | 13 个节点在场景间连续变形 | 通过 |
| 移动端 | 取消固定舞台，改为短场景和显式控制 | 390/412 px 下采用角色切换与可展开表格 | 通过 |
| 动效 | 滚动驱动，不自动播放 | GSAP ScrollTrigger 仅在场景边界更新状态 | 通过 |

有意差异：移动端不复刻桌面 SVG，而使用可触控、可读的短场景；这是为避免 390 px 画布产生标签碰撞。概念图仅作为方向基准，不作为页面图片资产。

## 浏览器与交互 QA

- Chromium：1440×900、1920×1080、390×844、412×915 均已截图检查。
- 滚动：Final 5 顺序、固定舞台和场景切换正常。
- 点击/触控：移动角色切换、数据表展开正常。
- 悬停：桌面导航链接正常，无布局跳动。
- Reduced Motion：禁用滚动进度动画，内容保持完整可用。
- 控制台：0 error，0 warning；失败请求 0。
- 横向溢出：`scrollWidth = clientWidth = 1440`；移动端自动化断言同样通过。

## 轻量性能抽样

本地 Next.js 开发服务器、Chromium 1440×900、API 为本机进程；以下数值仅用于发现明显回归，不代表生产环境 SLA。

| 指标 | 结果 |
| --- | ---: |
| TTFB | 509 ms |
| DOMContentLoaded | 661 ms |
| Load | 756 ms |
| FCP | 676 ms |
| LCP | 676 ms |
| HTML 导航传输量 | 7 KB |

## 自动化结果

- `npm run typecheck`：通过。
- `npm run lint`：通过。
- `npm run test -- --run`：6 个文件、12 个测试通过。
- `npm run build`：通过，`/lab/visual-v2` 成功生成。
- `npm run test:e2e -- visual-v2.spec.ts`：5 通过、1 个按桌面条件跳过、0 失败。

## 证据文件

截图和动效位于 `apps/web/output/playwright/visual-v2/`：

- `desktop-1440x900.png`
- `desktop-1920x1080.png`
- `desktop-role.png`
- `desktop-synergy.png`
- `desktop-robustness.png`
- `mobile-390x844.png`
- `mobile-412.png`
- `motion-desktop.webm`
