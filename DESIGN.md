# SkillWorth 2026 Design System

## Release Status

**VISUAL FREEZE V1** — 公开版信息架构、视觉语言、响应式结构和核心交互已冻结。后续改动必须以缺陷修复、可访问性或真实数据契约变化为依据，不再扩展视觉功能。

## Direction

视觉方向为 **Cinematic Data Intelligence**：深色编辑式技术研究产品，以炭黑空间、数据坐标、层次光场和克制的节点材质建立沉浸感。文字为偏暖浅灰，Signal Lime 只用于当前选择、效率前沿和关键数值；Ice Cyan 与 Muted Violet 仅承担次级数据语义。界面继续依靠排版、开放画布、细分割线和数据密度建立专业感，不使用卡片堆叠、霓虹或赛博朋克装饰。

## Typography

- UI：Geist Sans，中文回退 `PingFang SC`、`Microsoft YaHei`。
- 数据：Geist Mono，启用 tabular numerals。
- 页面问题标题最大 88px，最紧字距不超过 `-0.04em`。
- 正文控制在 65–75ch；小标签只在元数据和坐标语义中使用。

## Color Tokens

- Canvas `#0d110e`
- Deep `#090d0b`
- Surface `#121713`
- Elevated `#171c18`
- Hover `#1a201a`
- Border `#252d27`
- Text `#f1f0e9`
- Secondary `#a3aaa1`
- Muted `#747c73`
- Accent `#c8dc62`
- Ice Cyan `#83bcc1`
- Muted Violet `#9e8eb7`
- Warning `#d2a36f`
- Negative `#d57972`

## Layout

- 公共页面最大宽度 1560px，桌面左右边距 48px，移动端 20px。
- 首屏在 1440×900 内必须同时出现问题、真实样本条和 Frontier 的主要区域。
- Frontier 是最大视觉元素；Robust Picks 使用密集编辑表，不使用排名卡片。
- 研究能力统一位于 `/lab/*`。

## Components

- Header：56px 顶部栏，仅含品牌、Methodology、Data Scope。
- Metadata Strip：连续表格式元数据，不拆成 KPI 卡。
- Editorial Filter：无容器的文字控制，选中项使用 Signal Lime 下划线。
- Frontier：自定义 ECharts 主题、严格的学习投入/市场信号四象限、平方根气泡缩放、径向节点材质和发光但克制的 Pareto 前沿。
- Market Board：连续数据行、双向 hover 联动与微型敏感性区间，不使用排名卡片。
- Market Themes：非对称大字排版，只展示真实岗位、公司和覆盖率，不进入技能主榜。
- Detail：桌面 430px 半透明深色 Drawer，移动端 Bottom Sheet；仅使用真实微型证据轨。
- States：与图表结构匹配的 Skeleton、内联 Error、说明型 Empty State。

## Motion

交互状态使用 120–180ms，标准状态使用 220–320ms，图表数据重排使用 300–450ms，区块显现使用 450–700ms；统一采用无弹跳的 cubic-bezier。Hero 指针光场只更新 CSS 变量，不触发 React render。减少动态偏好下关闭视差、区块位移和高强调图表动效。
