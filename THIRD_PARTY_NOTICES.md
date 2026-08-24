# Third-Party Notices

## Scope of the SkillWorth MIT License

仓库根目录的 MIT License 仅覆盖 SkillWorth 自主创作的源代码与项目文档。它不重新许可第三方软件、招聘文本、外部数据集、商标或其他第三方内容；后者仍受各自许可、服务条款及其他适用权利约束。

## GSAP and @gsap/react

- Upstream: `greensock/GSAP`
- Packages: `gsap`, `@gsap/react`
- License: Webflow Standard "No Charge" GSAP License
- Repository: https://github.com/greensock/GSAP
- License: https://gsap.com/community/standard-license/

SkillWorth 在独立 Visual V2 与 3D 技能场实验路由中使用 GSAP core、ScrollTrigger 与 React hook，未复制 React Bits、Aceternity UI 或其他参考项目的组件源码。

## React Three Fiber, Drei, Three.js and camera-controls

- Packages: `@react-three/fiber` 9.7.0, `@react-three/drei` 10.7.8, `three` 0.180.0, `camera-controls` 3.1.2
- License: MIT
- Repositories: https://github.com/pmndrs/react-three-fiber, https://github.com/pmndrs/drei, https://github.com/mrdoob/three.js, https://github.com/yomotsu/camera-controls

SkillWorth 仅在 `/lab/3d-skill-field` 的客户端动态分包中使用这些库。原型使用项目自行实现的确定性布局、实例化节点、关系线和交互状态机，未复制第三方可视化产品源码。

## NextGig Global Job Postings — June 2026

- Source: `NextGig-Rocks/global-job-postings-multi-ats`
- Publisher/attribution: NextGig
- Revision: `fc9787e07b2a9b5f11a470c503c36e854abd6378`
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- Dataset page: https://huggingface.co/datasets/NextGig-Rocks/global-job-postings-multi-ats

SkillWorth 的 Connector 为本项目独立实现。数据集许可不改变上游招聘信息、个人信息或第三方商标可能适用的其他权利。

## Qarera Most In-demand Skills 2026

- Source: `yash2111/most-in-demand-skills-2026`
- Revision: `e12a94a46a334188082d329a175e11bc580f6ba2`
- License: Creative Commons Attribution 4.0 International (CC BY 4.0)
- DOI: `10.5281/zenodo.21204423`
- Dataset page: https://huggingface.co/datasets/yash2111/most-in-demand-skills-2026

该数据只作为隔离的外部技能排名基准，不并入 SkillWorth 岗位数据。

## Freehire public read API

- Upstream: `strelov1/freehire`
- Revision audited: `d7ab8697635528b47cea719a590eac485e1dfa2c`
- Software license: MIT, copyright 2026 freehire contributors
- Repository: https://github.com/strelov1/freehire
- API documentation: https://freehire.me/docs/api

SkillWorth 的 Connector 为独立实现，没有复制上游实质性代码。MIT 许可仅适用于 Freehire 软件，不自动授予第三方招聘文本的版权或再分发权。SkillWorth 默认只公开聚合结果，不批量再分发完整岗位描述。
