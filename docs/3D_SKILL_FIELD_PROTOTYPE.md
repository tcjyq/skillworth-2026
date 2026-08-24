# 3D Skill Field Prototype

## Scope

`/lab/3d-skill-field` 是与 `/lab/visual-v2` 和正式 `/` 隔离的人工评审原型。它不改动 Final 5、SkillWorth 公式、来源、taxonomy、去重、学习时长或冻结 Finding。

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
- `layout/`：价值、需求和职业场只让 rank 影响半径；方向来自 stable hash。节点大小是 capped square-root job coverage。
- `data/`：只把 API 输出转换为 scene model，不重算 SkillWorth、Market Signal、Confidence、Robustness、Jaccard 或 PMI。
- `scene/`：一个可见 `InstancedMesh`、一个透明放大命中 `InstancedMesh`、单批关系线、最多 5 条职业排名迁移轨迹、有界 Camera Director 和 demand render loop。
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
- Desktop 默认 5 个 DOM label，关系场实测 8 个；Mobile 通过 CSS 限制默认 3–4 个。Canvas 节点不进入 134 次 Tab 顺序。
- Reduced Motion 直接定位，保留排名变化信息。WebGL 不可用时保留搜索、职业、详情和关系列表。

## Measured performance

Real v6，Edge production build，1440×900 CSS viewport，高 DPR 模拟：

- 3D dynamic chunk：916,156 bytes raw，240,868 bytes gzip，196,675 bytes Brotli。
- 134 个真实节点；全局 2 draw calls，关系场 4 draw calls，0 textures。
- 静止采样期新增渲染帧 0；需求迁移 54 fps，关系迁移 59 fps。
- Desktop renderer DPR cap 1.55；Mobile cap 1.15。
- JS heap：约 14.4 MiB used / 26.8 MiB total。
- 产品级 console / GPU warning：0。Edge 报告了 Next.js 生成 CSS 的未使用 preload 提示，它不是 WebGL/GPU 错误。
- 3D 依赖只在本 Lab route 的 dynamic import 中，不进入正式首页 LCP critical path。

原始采样与人工评审产物由 `npm run capture:3d-review` 生成至 Git 忽略的 `output/3d-skill-field-review/`。
