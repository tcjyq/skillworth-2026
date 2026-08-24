# 技值 SkillWorth Live — Frontend Design Specification

## 1. 已确认视觉方向

实现目标是“技术技能市场终端”：以方案三的中文金融终端式信息架构为主体，市场主图采用方案一的技能气泡地图。整体面向大学生，但保持成熟、克制、专业的数据产品气质，不使用课程平台、后台模板、加密货币赌场或赛博朋克语言。

参考图为本地生成的视觉概念稿，不随仓库提交。

## 2. 设计原则

- Dark-first；开放画布、表格、轨道和图形优先，避免满屏圆角卡片。
- 单一琥珀色强调色；绿色和红色仅表达正负趋势。
- 分析数据全部来自 FastAPI。缺失、样本不足或后端未暴露的数据必须显示对应状态，不得补造。
- “技能匹配度”不得描述为录取概率；薪资指标统一使用“调整后薪资关联”。
- 所有页面固定显示：`分析用于学习决策参考，不代表录取概率。`

## 3. Design Tokens

### Color

| Token | Value | Use |
|---|---:|---|
| `--background` | `#090909` | 应用背景 |
| `--surface` | `#0D0E0E` | 主表面 |
| `--surface-elevated` | `#131515` | 浮层、检查器 |
| `--surface-hover` | `#181A19` | 行和控件 hover |
| `--border` | `#242626` | 常规边框 |
| `--border-subtle` | `#191B1A` | 图表网格、弱分割 |
| `--text-primary` | `#F0F0ED` | 主文字 |
| `--text-secondary` | `#888E8B` | 次级文字 |
| `--text-muted` | `#5F6461` | 注释和禁用文字 |
| `--accent` | `#D8A54A` | 选中、交互、主数据 |
| `--accent-muted` | `#6D542D` | 弱强调 |
| `--positive` | `#3EAD78` | 正向趋势 |
| `--negative` | `#D56565` | 负向趋势 |
| `--warning` | `#C98B45` | 低置信和告警 |

### Spacing and shape

- 基础间距：4px；常用层级：4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48。
- 桌面页面左右边距 20px，12 列网格，列间距 16px。
- 顶部导航 60px，市场筛选轨 52px，底部状态轨 30px。
- 圆角：控件 3px，表面 4px，图表画布 0–4px；禁止药丸形大卡片。
- 阴影仅用于 Command Palette、Tooltip、Drawer 和 Modal。

## 4. Typography

- Sans：`Geist Sans`, `Inter`, `PingFang SC`, `Microsoft YaHei`, sans-serif。
- Mono：`Geist Mono`, `JetBrains Mono`, `SFMono-Regular`, monospace。
- 页面标题 20px/28px，600；模块标题 15–16px/22px，600。
- 正文 13–14px/20px，400；说明 11–12px/18px。
- 所有指标、比例、时间和表格数值使用 Mono，采用 tabular numerals。
- 英文技能名称保持原名，解释、标签、状态和导航全部中文。

## 5. App Shell 与导航

- 左侧品牌：`技值 SkillWorth`，不加营销口号。
- 主导航：市场、技能、岗位、技能图谱、我的技能组合。
- 右侧：数据、搜索入口、`Ctrl K` 提示。
- 桌面单行导航；平板收敛次级文字；移动端使用底部导航与抽屉。
- 当前项使用琥珀色文字和 1px 底边，不使用填充胶囊。

## 6. Component System

- Button：高度 32/36px，3px radius；主按钮为琥珀底深色字，次按钮透明细边框。
- Input / Select：深色透明表面、1px 边框、琥珀 focus ring；标签始终可见。
- Table：30–38px 行高，右对齐数值，细分割线，sticky header；hover 只提高一个 surface 层级。
- Tooltip：深色 elevated surface，最多 280px，数值对齐，解释指标口径。
- Drawer / Modal：右侧检查器宽 360px；Command Palette 桌面宽 640px。
- Loading：骨架线和图表坐标框，不使用旋转大图标。
- Empty：保留页面骨架与上下文，明确下一步操作。
- Error：内联错误轨，显示重试；不暴露后端堆栈。
- Low confidence：琥珀边线、置信组件和原因；不得弱化或隐藏。

## 7. SkillWorth Chart Theme

- 背景透明，文字 `#888E8B`，标题 `#F0F0ED`。
- 坐标轴和 splitLine 分别使用 `#242626` / `#191B1A`，线宽 1。
- 主序列 `#D8A54A`；辅助序列依次为灰绿、砂岩、冷灰，避免默认 ECharts 调色板。
- 正负变化仅使用 `#3EAD78` / `#D56565`。
- Tooltip 使用 `#131515`、1px `#2B2E2C`、4px radius，无玻璃效果。
- 动画 180ms cubic-out；筛选变化只做位置、尺寸、透明度过渡。
- `prefers-reduced-motion` 下关闭图表和数字动画。

## 8. 页面布局

### Market Pulse / 市场脉搏

- 顶部筛选轨：目标岗位、城市、日期范围、技能类别。
- 主区域 8.5/12 列：方案一技能市场气泡地图；X=岗位覆盖率，Y=6 个月变化，Bubble=岗位数。
- 无可靠趋势时保留坐标画布并显示低置信说明，不对缺失趋势制造位置。
- 右侧 3.5/12 列：市场状态、上升技能、下降技能、数据源账本。
- 底部状态轨：样本量、数据时间范围、来源数、数据说明。

### Skill Explorer / 技能探索

- 左侧技能检索和资产列表；右侧资产详情。
- 首屏：市场价值、需求、6M 趋势、调整后薪资关联、置信度。
- 下方：历史趋势、来源拆分、岗位、城市、相关技能、学习成本。

### Role Intelligence / 岗位洞察

- 左侧岗位列表，主画布展示薪资概况、核心技能、新兴技能、技能组合、经验、城市、来源。
- API 当前无法支持的分布或维度显示“后端暂未提供”，不得用代理值冒充。

### Skill Graph / 技能图谱

- 大型 ECharts Graph 画布，支持 zoom、pan、hover、focus 和节点点击。
- 顶部过滤轨，右侧 360px Inspector；移动端检查器变为底部 Drawer。
- 节点大小来自真实支持度，边来自 `/skills/{skill}/related`。

### My Skill Portfolio / 我的技能组合

- 输入现有技能、目标岗位、可选城市/经验和阈值。
- 输出最高杠杆下一技能、平均技能匹配度增益、跨越阈值岗位占比、学习时长估算和置信度。
- 未分析前显示任务引导，不展示预置结果。

### Learning Optimizer / 学习优化器

- 预算输入与 100h / 200h / 300h 快捷项。
- 核心为技能投资时间线：步骤、技能、估算时长、边际增益、累计匹配度和阈值覆盖。
- 每次结果由 `/portfolio/optimize` 返回。

### Data Quality / 数据质量

- 专业数据工程视图：来源状态、新鲜度、薪资覆盖、技能抽取 F1、去重率、缺失率和置信状态。
- 后端缺失字段明确标记“API 暂未提供”。

### Methodology / 方法说明

- 非营销文档页。左侧目录、右侧正文，解释 Demand、Salary Association、Trend、Opportunity Gain、Market Value、Personal ROI、Confidence。
- 公式旁展示口径限制和误用警告。

## 9. Motion

- 通用 150–250ms；hover 150ms，Drawer 220ms，图表 180ms。
- 数字仅在真实请求完成后进行一次轻量过渡。
- 不使用粒子、循环漂浮、霓虹辉光或无意义图标动画。
- `prefers-reduced-motion: reduce` 时动画时长设为 1ms，保留状态变化。

## 10. Responsive Rules

- 1440×900：完整 12 列，地图与右轨并排，信息密度最高。
- 1366×768：保持并排，压缩垂直留白和右轨行高，不缩小正文低于 12px。
- 768–1023：6 列，右轨移到主图下，Inspector 变 Drawer。
- <768：单列；顶部导航简化，主导航移到底部；表格水平滚动；图表高度 360–440px；筛选器变可折叠区域。

## 11. API 与状态契约

- 浏览器只访问 `/backend-api/*`，由 Next.js rewrite 转发至 FastAPI。
- Demo 模式同样访问 FastAPI Demo Dataset，不存在前端 mock 数字。
- 每个查询具有 `loading / error / empty / low-confidence / ready` 五态。
- GET 使用共享缓存和去重；POST 仅由用户提交触发。
- Filter 变化通过 URL/query key 触发新请求，并保留旧画布直到新响应到达。

## 12. Accessibility

- 所有图表提供文本摘要；颜色不是唯一编码方式。
- 键盘可访问导航、筛选、命令面板和表格行。
- 可见 focus ring；Tooltip 信息可由 focus 触发。
- 对比度、字号和命中区域满足成熟数据工具使用要求。
