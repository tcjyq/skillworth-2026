# Freehire Public API Usage Audit

审计日期：2026-08-10（Asia/Shanghai）  
审计对象：`strelov1/freehire` 与 `https://freehire.me/api/v1`  
固定 revision：`d7ab8697635528b47cea719a590eac485e1dfa2c`  
结论：`usage_status = no_explicit_block_found`

该结论只表示在已检查的官方材料中没有发现明确禁止本地快照、聚合分析或本项目研究/作品集用途的条款，**不表示 SkillWorth 已获得 Freehire 或第三方岗位内容的完整授权**。

## 1. 已检查证据

| 项目 | 官方证据 | 结果 |
| --- | --- | --- |
| 上游仓库 | https://github.com/strelov1/freehire | 公开仓库；本轮固定 revision 如上 |
| 软件 License | https://github.com/strelov1/freehire/blob/d7ab8697635528b47cea719a590eac485e1dfa2c/LICENSE | MIT License，Copyright (c) 2026 freehire contributors |
| API 文档 | https://freehire.me/docs/api | job、search、facet、company 为公开、无需认证、允许跨域调用的 read-first API |
| API 源文档 | https://github.com/strelov1/freehire/blob/d7ab8697635528b47cea719a590eac485e1dfa2c/docs/API.md | `limit` 最大 100；`offset + limit` 不得超过 10,000；错误响应有统一 envelope |
| Robots | https://freehire.me/robots.txt | `User-agent: *` 下允许公开页面；只排除个人页面和无唯一内容的 discussion/new 页面 |
| Privacy Policy | https://freehire.me/privacy | 岗位来自公开公司招聘页及其他公开来源；Freehire 明确说明其不拥有这些岗位内容 |
| Rate-limit 规范 | https://github.com/strelov1/freehire/blob/d7ab8697635528b47cea719a590eac485e1dfa2c/openspec/specs/api-rate-limiting/spec.md | 被限流路由超限时返回 429 和 `Retry-After`；未公布公开 read API 的固定请求额度 |
| 实时响应头 | `GET /api/v1/jobs/facets?countries=cn`，2026-08-10T17:42:11+08:00 | 200；未返回公开 rate-limit、cache 或 redistribution header |

仓库固定 revision 中未发现 Terms of Service 或 Acceptable Use 文件；只发现 Privacy Policy。未发现独立的 hosted API 批量使用、缓存期限或岗位内容再分发许可。缺失条款不能解释为授权。

## 2. 允许的本阶段访问方式

- 只调用文档列出的 `GET /jobs/search`、`GET /jobs/facets` 和必要的公开 job/company read endpoint。
- 不使用登录、Cookie、Session、API key、private endpoint 或 Freehire 上游爬虫。
- 单线程顺序分页，默认每次请求之间等待，可通过配置提高等待时间但不能关闭为负数。
- page size 不超过 100；遵守 `offset + limit <= 10000`。
- 对 429 使用 `Retry-After`（如存在），否则使用指数退避；对临时 5xx/网络错误做有上限重试。
- API 原始响应落入本地、被 Git 忽略的 cache 和 Raw/Snapshot 区域；重复运行优先读取 cache。
- 每页记录请求 URL、访问时间、响应内容 hash；断点只从已校验 cache 继续。

## 3. 缓存、归档和再分发边界

- 本地保存只用于可复现分析、审计和作品集运行，不将该状态描述为 fully authorized。
- Snapshot metadata、聚合指标、方法与非原文派生结果可进入项目文档；批量完整 JD、第三方商标或个人信息不得提交或公开再分发。
- `source_url`、`source`、`external_id`、`company_slug` 和 Freehire public slug 必须保留，用于 provenance 和移除请求处理。
- 若 Freehire 后续发布更严格的 Terms、API policy、缓存期限或删除要求，应停止刷新并重新审计；历史快照的保留也需按新规则复核。
- Freehire 软件 MIT License 不自动覆盖原始 ATS、企业招聘网站或聚合源内容。若复制实质性 Freehire 代码，必须保留其版权和许可声明；当前 Connector 为 SkillWorth 独立实现。

## 4. Attribution

数据来源说明统一使用：

> Source catalogue and public API: freehire (`strelov1/freehire`), accessed 2026-08-10. Original job content remains attributable to the linked ATS/company source and is not bulk redistributed by SkillWorth.

## 5. Blocker 判断

| 检查项 | 是否发现明确禁止 | 处理 |
| --- | --- | --- |
| 本地保存公开 API 响应 | 未发现 | 允许受控、不可公开再分发的本地 Snapshot |
| 聚合统计分析 | 未发现 | 允许，必须保留 scope 和 disclaimer |
| 批量公开 API 调用 | 未发现明确禁令或公开 quota | 仅顺序、延迟、缓存、退避、可恢复访问；429 立即服从 |
| 研究/作品集用途 | 未发现明确禁止 | 仅使用 `no_explicit_block_found`，不写 fully authorized |
| 批量完整 JD 再分发 | 没有获得许可 | 禁止 |

本轮没有触发“立即停止”条件，可以继续实现 `FreehirePublicApiConnector`。该决定不改变 Freehire 的 `CHINA_SUPPLEMENTARY` Source Role，也不改变现有 Source Gate。
