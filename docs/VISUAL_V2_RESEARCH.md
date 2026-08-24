# SkillWorth Visual V2 研究与参考矩阵

## 研究结论

当前首页的问题不是配色或组件精度，而是叙事单位仍然是独立 Section。每个 Finding 都重新建立标题、容器和图形，用户看到的是五张相邻的说明页，而不是同一批技能在不同问题下改变位置、关系与可信度的连续推理。

Visual V2 应把页面主语从“区块”改成“数据对象”：Python、SQL、Git、C++、Kubernetes 等节点在滚动中保持身份连续，只改变位置、尺度、连线、排名区间和注释。一次过渡只表达一个含义变化；装饰层只能提供空间与焦点，不能抢占数据层。

技术选择收敛为：

- 使用 GSAP + ScrollTrigger + `@gsap/react` 统一管理桌面端 pinned scene、时间线和清理。
- 图形使用代码原生 SVG / HTML，不引入 Three.js、React Three Fiber 或 3D force graph。
- Skill Synergy 使用可读的 2D 关系场。当前冻结证据只有三组明确关系，3D 会制造并不存在的网络复杂度，并显著恶化移动端、无障碍与性能。
- 移动端不 pin 长画布，改为相同状态机驱动的短场景、横向位移和逐步注释。
- reduced motion 保留五个静态状态和完整文字证据，只取消 scrub、视差和路径动画。

## Visual Reference Matrix

评分 1–5；“可复用”只表示经许可允许且对原型有实际价值，不等于已经复制代码。

| Repository / Reference | Visual | Interaction | Dataviz | SkillWorth 可吸收 | 可复用范围 | License | Risk | 结论 |
| --- | ---: | ---: | ---: | --- | --- | --- | --- | --- |
| `basementstudio/scrollytelling` | 4 | 5 | 3 | Root / Waypoint / label 的时间线思维；React 生命周期清理；layered pinning | 可研究 API；原型直接使用底层 GSAP，避免额外抽象 | MIT；GSAP 另受 GreenSock Standard License | 额外框架会掩盖本项目自己的 Scene Director | Recommended as architecture reference |
| `vasturiano/react-force-graph` | 4 | 5 | 5 | 邻域高亮、click-to-focus、动态数据、2D Canvas 与 3D WebGL 的一致交互模型 | 本轮不引入代码；借鉴邻域 dim/focus | MIT | 3D 透视遮挡、标签冲突、GPU 与移动端成本；小数据会显得空洞 | 2D ideas recommended; 3D rejected |
| `shehzadres/Webgl-Data-Globe` | 5 | 5 | 4 | Scene Director、摄像机预设、统一时间线、零逐帧分配、adaptive DPR | 只吸收架构思想，不复制 globe/shader | MIT | 地球、粒子和 shader 语言与 SkillWorth 数据语义无关 | Director pattern recommended |
| `the-pudding/svelte-starter` | 4 | 4 | 5 | prose + visualization 关系、注释、响应式降级、motion toggle、可访问控件 | 只吸收新闻叙事方法，不迁移 Svelte | MIT；logo / fonts 明确不可复用 | Starter 正在迁移，部分 helper 尚未迁移 | Strong editorial reference |
| `plouc/nivo` | 4 | 4 | 5 | 响应式容器、SVG/Canvas 选择、主题、图层与注释接口 | 不引入依赖；现有自定义叙事图形更合适 | MIT | 现成 chart 容易把原型拉回 Dashboard 语法 | Implementation reference only |
| `uiverse-io/galaxy` | 3 | 4 | 1 | 小型 toggle、tooltip、loading / hover 的状态完整性 | 本轮不复制组件；已有项目控件足够 | MIT；建议保留原作者/Uiverse attribution | 3000+ 元素质量不一致，拼装感强 | Reject for page language |
| `DavidHDev/react-bits` | 5 | 5 | 1 | mask、gradual blur、scroll reveal 的材质参考；识别哪些效果应克制使用 | 不复制源码 | MIT + Commons Clause；禁止单独或组件包形式再销售、再许可或再分发组件 | 未来开源仓库存在 source redistribution 风险，且模板辨识度高 | Visual reference only; code rejected |
| `zedfar/d3js-storytelling-viz` | 3 | 4 | 5 | 1 state = 1 insight；1 transition = 1 meaning change；稳定 key；focus through dimming | 不复制代码 | README 只有实验项目说明，无明确授权文本 | 无明确许可证；移动响应仍在 future enhancements | Grammar recommended; code rejected |
| Aceternity UI | 5 | 5 | 1 | tracing beam、timeline、spotlight 的焦点组织与层级参考 | 自行实现同类简单视觉思想；不复制 component source | 免费/Pro 组件条款需逐项确认，未发现适合本轮开源再分发的统一授权 | 强品牌模板感；source redistribution 不确定 | Reference only; code rejected |
| GSAP / ScrollTrigger | 4 | 5 | 4 | pin、scrub、timeline label、matchMedia、SVG/DOM 同步编排 | 直接作为依赖使用；仅用 core + ScrollTrigger | GreenSock Standard “no charge” license，允许商业使用，需保留依赖许可 | 错误 pin / cleanup 会造成滚动跳跃和内存泄漏 | Recommended and used |
| `btahir/react-kino` | 4 | 4 | 2 | 轻量 ProgressValue、逐帧 DOM 写入、SSR guard、reduced-motion fallback | 不引入；借鉴“不因滚动每帧触发 React render” | 需要在采用前再次核对仓库 LICENSE | 新项目成熟度与维护风险 | Useful supplemental reference |
| `Poolchaos/flow-story` | 4 | 5 | 4 | waypoint、相机状态与性能上限的产品化思路 | 不复用代码 | PolyForm Noncommercial 1.0.0 | 非商业限制；3D 仍不适合本轮冻结数据 | Study only; code rejected |

## 许可证与归属决定

本轮计划新增的第三方运行时依赖只有 `gsap` 与 `@gsap/react`。原型不会复制 React Bits、Aceternity、Uiverse、D3 Storytelling、Webgl Data Globe、The Pudding 或 react-force-graph 的组件源码。最终若依赖落地，应在 `THIRD_PARTY_NOTICES.md` 增加 GSAP 许可说明；研究文档保留其余项目的参考归属。

## 参考来源

- <https://github.com/basementstudio/scrollytelling>
- <https://github.com/vasturiano/react-force-graph>
- <https://github.com/shehzadres/Webgl-Data-Globe>
- <https://github.com/the-pudding/svelte-starter>
- <https://github.com/plouc/nivo>
- <https://github.com/uiverse-io/galaxy>
- <https://github.com/DavidHDev/react-bits>
- <https://github.com/zedfar/d3js-storytelling-viz>
- <https://ui.aceternity.com>
- <https://github.com/greensock/GSAP>
- <https://github.com/btahir/react-kino>
- <https://github.com/Poolchaos/flow-story>

