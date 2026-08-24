# Production Homepage Candidate

日期：2026-08-23（UTC+8）  
验收路由：`/lab/visual-v2`  
正式首页：`/` 保持不变。

## 首层用户路径

1. Hero：直接回答“2026，学什么技术最值？”，同屏公开样本和市场边界。
2. C++：使用直接标注呈现需求 `#3` 到技值 `#35` 的反直觉变化。
3. Role First：先选岗位方向，再显示样本、证据状态、主要技能和全局到岗位排名变化。
4. Full Explore：按技能或岗位查找 134 项技能，并可筛选技能层和时间窗口。

## 信息分层

### 首层

- 岗位覆盖
- 公司覆盖
- 约学习时间
- 排名稳定性
- 样本量与证据状态
- 主排名层 / 已观察技能

### 进阶层

- 市场信号 Market Signal
- 技值 SkillWorth
- 岗位广度 Role Breadth
- 技能协同 Synergy
- 置信度 Confidence

## 字号层级

| 用途 | 桌面 | 移动 |
| --- | --- | --- |
| Hero 主标题 | 68–112 px | 52–66 px |
| 数据故事主标题 | 52–88 px | 45 px |
| 主数据排名 | 86–150 px | 68 px |
| Role / Explore 标题 | 50–82 px | 48–50 px |
| 技能详情标题 | 42 px | 34 px |
| 首层正文 | 16–18 px | 15–16 px |
| 次级说明 | 13–15 px | 12–14 px |
| 来源与图注 | 12–13 px | 11–12 px |

## 边界

- 不修改排名、taxonomy、dedup、API 或任何指标公式。
- 不新增数据源、Finding、benchmark 或可视化库。
- Salary 与 Trend 保持不可用；Learning Effort 明确标记为模型假设。
- Freehire 是单一中国公开技术岗位补充样本，不代表完整中国市场。

## 信息密度对比

- 进入 Explore 前的数据故事章节由 5 个收敛为 1 个 C++ 反直觉发现，Role 改为用户选择后才展开。
- 桌面端完整页高度由 8218 px 降为 5541 px，减少 32.6%。
- Market Signal、SkillWorth、Role Breadth、Synergy 和 Confidence 不再占用首层故事，统一放入技能详情的进阶折叠层。

## QA

| 检查 | 结果 |
| --- | --- |
| TypeScript | 通过 |
| ESLint | 通过 |
| 单元测试 | 6 文件，12/12 通过 |
| Production Build | 通过，`/lab/visual-v2` 静态页生成 |
| Playwright E2E | 15 通过，1 个桌面专用的 19 角色循环在移动项目中按条件跳过，0 失败 |
| 19 个角色筛选 | 19/19 请求成功，主排名层与已观察技能均可见 |
| Console error / warning | 0 / 0 |
| 失败请求 | 0 |
| 390×844 移动横向溢出 | 0 px |
| Reduced Motion | 通过 |
