# 3D Skill Field Prototype

## Scope

`/lab/3d-skill-field` 是独立于 `/lab/visual-v2` 和正式 `/` 的人工评审探索路由。它不复制分析故事，也不替换候选首页；用户从 `/lab/visual-v2#analysis-results` 主动进入，并可通过统一页面导航返回同一结果锚点。3D runtime 与 bundle 仍只在该路由加载，且不改动 Final 5、SkillWorth 公式、来源、taxonomy、去重、学习时长或冻结 Finding。

## Compatibility and adopted dependencies

- React 19.2.8 / React DOM 19.2.8。
- `@react-three/fiber` 9.7.0：同 React 19 主版本匹配。
- `@react-three/drei` 10.7.8：使用 `CameraControls`。
- `three` 0.180.0：与 R3F / Drei peer range 匹配，并避免更高版本中已观察到的 `THREE.Clock` 弃用警告。
- `camera-controls` 3.1.2：Drei 的传递依赖。

上述库均为 MIT。`3d-force-graph`、`react-force-graph` 和 Obsidian 交互只用于研究，没有复制代码，也没有加入 runtime dependency。详见 `THIRD_PARTY_NOTICES.md`。

## Scene architecture

```text
DOM Search / Controls / Detail
              |
        Scene Director
              |
  GLOBAL_VALUE / GLOBAL_DEMAND
  ROLE_VALUE
  RELATION_GLOBAL / RELATION_ROLE
              |
 deterministic layout adapters
              |
 Instanced nodes + relation/shift lines + bounded CameraControls
```

- `state/`：单一 reducer 管理 mode、role、skill、relation、最近 5 步路径、transition token 和 Reduced Motion。
- `layout/`：价值、需求和职业场只让 rank 影响半径；方向来自 stable hash。价值核心保留 `2.75` 的安全半径，第一价值轨道从 `3.7` 开始；节点大小是 capped square-root job coverage，不改变覆盖度相对顺序。
- `data/`：只把 API 输出转换为 scene model，不重算 SkillWorth、Market Signal、Confidence、Robustness、Jaccard 或 PMI。
- `scene/`：一个可见 `InstancedMesh`、一个透明放大命中 `InstancedMesh`、单批关系线、最多 3 条职业排名上升轨迹、五种稳定默认视角、有界 Camera Director 和 demand render loop。
- `ui/`：搜索、控件、证据面板、关系轨道与 WebGL 2D fallback 全部为 DOM。

## Data contracts

- 价值、需求和职业切片：`GET /market/china-skillworth`。
- `demand_rank`：analytics 按 main 技能的 `job_count DESC, skill_id ASC` 稳定排序；Real v6 C++ 保持 Demand #3 / SkillWorth #35。
- 关系：`GET /market/china-skill-relations`，使用 canonical job 分母返回 co-occurrence、core conditional coverage、Jaccard 与 PMI。
- 探索关系门槛：`data/reference/exploratory_relations.v1.yml`，默认最少 3 个共同岗位且 Jaccard 不低于 0.01。
- 职业样本：`n >= 10` 正常，`4..9` 永久显示小样本警示，`n <= 3` 不形成排名星域并提供全局替代入口。

## Interaction and accessibility

- 搜索技能会保留职业上下文；搜索职业进入 `ROLE_VALUE`。支持模糊匹配、上下键、Enter 与 Escape。
- 关系星座为 1 个中心、最多 7 个 Primary 和 12 个 Secondary；距离保留 Jaccard 排序，线亮度使用共同岗位数的平方根变换。
- Camera 限制在水平约 ±45°、垂直约 ±20°、15–34 距离；无自动旋转、自由平移、节点拖动或 scroll hijack。
- 标签按选中技能、故事技能、职业变化、Top 技能、hover 的优先级做确定性屏幕空间避让；Desktop 默认 5 个技能标签、关系场 6 个，Mobile 为 3–4 个。Canvas 节点不进入 134 次 Tab 顺序。
- C++ 在需求模式直接显示 `招聘需求 #3`，回到学习性价比时保留 `需求 #3` 起点并落到真实 `学习性价比 #35`；DevOps 直接标注 Kubernetes `#18 → #1`、Terraform `#33 → #3`。
- Reduced Motion 直接定位并取消迁移轨迹和证据粒子，保留排名变化信息。WebGL 不可用时保留搜索、职业、详情、C++ `#3 → #35` 和关系列表。

## Measured performance

Real v6，Edge production build，2026-08-25 采样。桌面为 1440×900、device DPR 2、renderer DPR 1.45、BALANCED；移动为 390×844、device DPR 3、触摸模拟、renderer DPR 1.1、LOW。这里的 FPS 是测试机 Edge 中按最近 30 个有效渲染帧间隔计算的实际画布帧率，不是物理手机实测，也不应外推到所有移动设备。

- 3D dynamic chunk：926,066 bytes raw，243,964 bytes gzip，199,422 bytes Brotli；依赖仍只进入本 Lab route，不进入正式首页 LCP critical path。
- 134 个真实节点；全局 7 draw calls，普通关系场 5，选中关系 6，均满足 `<= 7 / <= 10` 红线；0 textures、0 post-processing passes。
- Desktop：静止新增渲染帧 0；需求切换约 240.2 fps；关系迁移约 119.8 fps；选中 Python–SQL 约 120.0 fps。
- Desktop 标签 5 个，关系场 6 个；环境粒子 96，选中关系证据粒子 4，未选中为 0。
- Mobile LOW：静止新增渲染帧 0；需求切换持续最低 223.4 fps，搜索 Python 116.1 fps，触摸旋转 120.0 fps，选择 Python–SQL 117.8 fps，回到全局 232.2 fps，全部高于 40–45 fps 目标。
- Mobile 标签 3–4 个，环境粒子 48，LOW 关系证据粒子 0；使用约 12.7 MiB JS heap / 21.8 MiB total。
- Desktop 使用约 14.5 MiB JS heap / 29.8 MiB total；产品级 console warning 0，GPU warning 0。Edge 的 Next.js CSS preload 提示单独记录为浏览器 preload warning，不属于 WebGL/GPU warning。
- 未采用 Line2：批量渐变、非选中关系降至背景、端点完整亮度和按需证据粒子已足够清楚；因此 Line2 增加 0 draw calls，避免引入额外跨平台线宽路径。
- 截图、A–F 录屏与原始 JSON 位于 Git 忽略的 `output/3d-skill-field-review/`；共 50 张 PNG、8 段 WebM。真人理解测试仍须按 `docs/3D_SKILL_FIELD_HUMAN_TEST.md` 由未参与项目的人执行，当前没有伪造用户结果。

原始采样与人工评审产物由 `npm run capture:3d-review` 生成至 Git 忽略的 `output/3d-skill-field-review/`。
