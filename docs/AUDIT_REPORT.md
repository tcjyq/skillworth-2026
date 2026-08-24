# 技值 SkillWorth Live 质量审计报告

审计日期：2026-08-09（Asia/Shanghai）  
审计范围：Data、Analytics、FastAPI、Next.js、依赖与项目治理  
审计原则：只直接修复明确、低风险、可验证的问题；数据代表性、算法外部效度和发布治理问题不以代码补丁掩盖。

## 1. 结论

当前仓库具备一条真实可执行的 Demo/Real 数据链路，核心统计口径、机会计算与迭代优化器没有发现明显公式级错误，也未发现硬编码分析结果、密钥或违规招聘采集实现。Bronze 输入未被审计过程覆盖，Silver 双跑结果完全一致；API、前端与生产构建通过验证。

项目尚不适合把当前 Real 数据作为“中国技术招聘市场”的正式决策依据。主要原因不是程序无法运行，而是 Real 数据只有一个陈旧来源、无薪资、岗位 taxonomy 覆盖极低，且技能抽取与岗位去重缺少足够大的人工标注生产基准。公开部署前还必须处理依赖公告、API 滥用保护和仓库许可证。

开放问题：Critical 0、High 7、Medium 10、Low 3。

## 2. Critical

未发现未解决的 Critical 级运行时或数据完整性问题。

## 3. High

### H-01 Real 数据不具备市场代表性

- 当前 9,919 条原始记录中只有 451 条属于结构化 China 范围，去重后 388 个岗位。
- 日期范围为 2024-03-05 至 2024-09-04；薪资覆盖为 0/388；来源数为 1，且岗位集中于两个企业官网域名。
- `other` 为 385/388（99.23%）。Platform-balanced Demand、跨平台偏差、跨源一致性和薪资关联没有足够证据。
- 状态：剩余。正式结论必须增加许可明确、更新且覆盖更广的来源；当前 Real Mode 只适合证明 Pipeline 和 unavailable 语义。

### H-02 Role Normalization 对真实宽岗位数据召回率过低

- Taxonomy 配置化且对已支持岗位的精确规则清晰，但当前 Real 数据只有 3/388 被归入非 `other` role。
- 状态：剩余。需要基于人工标注真实标题扩充 taxonomy，并单独报告每个 role 的 precision/recall，不能通过把未知岗位强行归类来提高覆盖。

### H-03 Skill Extraction 外部效度不足

- 现有 benchmark 只有 9 条 fixture；修复后为 TP=39、FP=0、FN=0、Precision/Recall/F1=1.0，但样本量不足以代表真实招聘语料。
- 审计实际发现 `CV`、`MD` 短别名会把普通招聘文本误识别为 Computer Vision、Markdown，说明原 benchmark 的满分不能代表生产质量。
- 状态：部分修复。已移除两个高歧义别名并增加负例；仍需建立更大的中文、英文、中英混合和非技术人工标注集，重点覆盖 `R`、`C`、`Go`、`AI`、`ML` 等短词。

### H-04 Dedup 缺少真实标注对，且规范岗位可能损失成员字段

- 实现采用 precision-first、complete-link 和 city/company/role/seniority/intern/business-unit 保护，单元测试覆盖主要 false-positive 防护。
- Real 结果 451 → 388，44 个重复组、去除 63 条，全部为 Level 1 exact；没有跨平台数据，也没有人工标注 pair benchmark，因此无法量化 false positive/false negative。
- `canonical_jobs` 取最早代表记录的规范字段，而技能集合会合并组内来源。若代表记录缺薪资而其他成员有薪资，规范岗位仍可能缺薪资。
- 状态：剩余。需要 pair-level gold set，并为 canonical 字段定义可审计的字段级合并策略。

### H-05 公开 API 缺少滥用保护

- API 当前只读、无 PII，已增加输入上限，但 `/portfolio/optimize` 等端点仍可触发较重计算。
- 未配置认证、rate limit、并发配额或反向代理请求预算。
- 状态：剩余。仅本机运行风险较低；公开部署前为 High，必须在 API gateway/反向代理和应用层确定策略。

### H-06 前端依赖存在无可用修复版本的安全公告

- `npm audit --omit=dev`：3 个 High，链路为 Next.js → `@playwright/test` → `playwright`，对应浏览器下载时未验证 SSL 证书真实性的 [GHSA-7mvr-c777-76hp](https://github.com/advisories/GHSA-7mvr-c777-76hp)。这是安装/供应链风险，不是页面请求直接可利用漏洞。
- 完整依赖另有 Vitest Critical：[GHSA-5xrq-8626-4rwp](https://github.com/advisories/GHSA-5xrq-8626-4rwp)。项目只运行 `vitest run`，没有启动 Vitest UI server，因此当前正常测试流程不可达，但开发依赖仍需跟踪。
- npm 对当前锁定版本均报告 `fixAvailable=false`。
- 状态：剩余。不要盲目降级或强制覆盖；持续跟踪上游修复，并在 CI 中固定 registry、锁文件和依赖审计。

### H-07 仓库没有项目级 LICENSE

- 公开数据集许可证已有记录，但代码仓库本身没有 LICENSE，不能据此推断代码可复制、分发或商用。
- 状态：剩余。许可证选择属于所有者决策，本轮未代替用户授权。

## 4. Medium

### M-01 Source import 不是事务化、可恢复工作流

Bronze 与 manifest 会先落盘；若 Silver/Gold/Warehouse 后续失败，相同 artifact 的重复保护会阻止原命令直接重试。数据没有被覆盖，但恢复体验和 run 状态机不完整。应增加 run state、resume/rebuild-from-run 语义。

### M-02 Platform-balanced Demand 的来源内分母仍是来源 posting

Pooled coverage 以 canonical jobs 为分母；平台均衡值先计算各 source posting coverage 再做不加权平均。该实现符合当前文档定义，但同平台内部重复 posting 仍可能影响来源内覆盖率。需要明确这是“来源观测覆盖”还是“来源内 canonical 覆盖”，并增加多来源夹具验证。

### M-03 Salary Parser 缺少业务上界与异常值政策

必需格式、面议、非法值、日薪、年薪和 13/14 薪均有测试；非有限数字现已拒绝。当前仍没有按角色/城市配置的合理上界或 winsorization 政策，极端但可解析的正数可能进入模型。必须在 methodology 中先定义规则再实现。

### M-04 Skill Graph 仍可能被超高频技能支配

已有 low-support 过滤、Jaccard 和 PMI，默认图权重不是纯 co-occurrence；但没有 hub cap、degree normalization 或按 role 分层的生产验证。需要用真实多源数据检查社区稳定性和高频通用技能的中心性影响。

### M-05 Cache 没有容量上限和数据版本失效策略

TTL cache 已避免在 loader 执行期间持有全局锁，但 key 数量没有 LRU/size bound，数据快照切换也没有主动失效。长期公开服务可能积累高基数查询。

### M-06 DuckDB 生命周期与健康检查耦合

多个 service 调用会创建短生命周期只读连接；`market/summary` 会组合多次分析查询。应用初始化还依赖 warehouse 可用，warehouse 缺失时可能在 `/health` 表达降级前就启动失败。应评估只读连接池/请求级连接和惰性初始化。

### M-07 前端无法完整表达 Data Mode 与来源新鲜度

业务数字均从 FastAPI 获取，没有发现硬编码分析结果；但 API 未统一暴露 `data_mode`、当前 snapshot 和完整 source freshness，页面也有少量自己的低置信阈值。应让 UI 消费同一 Confidence Engine 和 source metadata，避免前后端规则漂移。

### M-08 Fresh checkout 缺少完整 Demo 一键重建入口

现有 CLI 能构建 Silver、抽取技能、去重和 Warehouse，但 Skill Network 等派生产物没有统一 bootstrap 命令。README 已说明运行前置条件，但从全新 checkout 仍不能只按一条命令恢复所有 API 依赖。

### M-09 Python 环境与声明技术栈不完全一致

当前 `.venv` 的核心 runtime import 和 `pip check` 通过，但 scikit-learn 未安装，`pyproject.toml` 也未声明它；同时 Python 依赖只有版本范围，没有锁文件。当前代码未导入 scikit-learn，因此不是运行时故障，但与项目技术栈声明不一致。

### M-10 审计可见性与测试覆盖仍有限

仓库没有 `.git`，无法检查历史提交、staged 内容或用 `git diff` 精确证明变更边界。前端只有 6 个 Vitest 用例，Python 没有静态类型/覆盖率门槛；本轮通过代码搜索、165 个 pytest 和 22 个浏览器用例补偿，但不能证明没有所有 dead code。

## 5. Low

### L-01 TestClient 上游弃用警告

pytest 保留 1 条 Starlette `TestClient`/httpx 弃用警告。当前不影响测试结果，后续随 FastAPI/Starlette 测试栈升级处理。

### L-02 本地运行产物仍会占用磁盘

`.run/`、Playwright trace、`.next`、缓存和派生数据已被忽略或不进入源代码，但不会自动清理。审计没有删除可能仍被用户进程使用的旧日志。

### L-03 Disabled 占位来源使用 `example.invalid`

官方就业、企业官网、Public/Research Dataset 的占位 terms URL 明确不可用且 adapter 默认 disabled。这是安全默认值，不是正式来源元数据；启用前必须替换并完成许可评审。

## 6. 本轮已修复

### Data 与 Analytics

- 移除高歧义 skill aliases `CV`、`MD`，taxonomy 升级为 1.0.1，并增加非技术负例 fixture。
- 重跑 Demo/Real Skill Extraction、Warehouse 和 Skill Graph；Real skill coverage 从 152/388（39.18%）校正为 145/388（37.37%）。
- Salary Parser 拒绝 NaN/Infinity；Warehouse numeric data tests 同步检查有限值。
- 修正文档中的 Skill Demand denominator、3M/6M trend 表述、canonical representative 限制和 Personal ROI 公式。
- `source-status` 现在读取并校验各 Data Mode 的当前 manifest；Real 来源正确报告 451 条和同步时间，不再显示 `never/0`。

### Backend

- Pydantic filter/portfolio/optimizer models 禁止未知字段，并限制字符串、来源、技能和 override 数量。
- TTL cache loader 移出全局锁，避免无关慢查询串行化；增加并发回归测试。
- 文件缺失错误不再向客户端泄露本机绝对路径。
- 增加 `nosniff`、frame deny、referrer 和 permissions policy 响应头。

### Frontend 与 E2E

- 数据来源状态从误导性的“在线/就绪”调整为“已导入”。
- Methodology 页面 Personal ROI 公式与后端加权和/学习成本衰减实现对齐。
- Playwright 使用独立 API/Web 端口，避免复用用户正在运行的旧服务；为 Windows/POSIX 正确构造 `PYTHONPATH`。
- 按 Next.js 官方配置仅允许本机 `127.0.0.1` 作为额外开发 origin，修复客户端资源被阻止、页面停在 loading 的问题。
- 新增筛选状态/API 刷新和 API 失败错误态的 E2E 覆盖。

### Project

- 新增根 README，替换前端默认脚手架 README；明确启动、验证、数据口径、采集合规和仓库无 LICENSE 的事实。
- `.gitignore` 增加 `.run/`；PRD、Methodology 与 Real Dataset Report 同步到当前实现和 taxonomy 1.0.1。
- 未发现密钥、Token、付费 LLM 默认调用、验证码/登录/反爬/rate-limit 绕过或招聘私有接口逆向代码。

## 7. 验证结果

| 检查 | 结果 |
| --- | --- |
| Silver 可复现双跑 | 输入哈希不变；两份 Parquet SHA-256 相同；质量报告相同 |
| Real current 路径 | 12/12 路径存在；current 与 manifest source/run 一致 |
| pytest | 165 passed，1 个上游弃用 warning |
| ESLint | passed |
| TypeScript | passed |
| Vitest | 3 files / 6 tests passed |
| Playwright | desktop + mobile，22 passed |
| Next.js production build | passed；12 个静态页面生成 |
| pip check | no broken requirements |
| Python runtime imports | 核心已使用依赖导入成功 |
| npm audit | production 3 High；all dependencies 3 High + 1 Critical；当前无可用自动修复 |

## 8. 建议顺序

1. 先建立 200～500 条人工标注 JD 与 dedup pair benchmark，按来源、语言、岗位和非技术文本分层。
2. 引入第二个许可明确且更新的来源，再验证 platform-balanced demand、跨源一致性与 dedup。
3. 扩充 role taxonomy，使目标技术岗位的 `other` 比例降到可接受范围后，才开放个人学习推荐的正式 Real Mode。
4. 公开部署前完成 API rate limit/并发预算、依赖公告处置和项目 LICENSE 决策。
5. 增加一键 Demo bootstrap、Python 锁文件、覆盖率门槛和 CI 质量门。
