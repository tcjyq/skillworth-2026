"use client";

import Link from "next/link";
import { useApi } from "@/hooks/use-api";
import type { ChinaSkillWorthResponse, DataQuality, ReleaseMetadata, SkillRelationsResponse } from "@/lib/api/types";
import { PublicNavigation } from "@/features/visual-v2/public-navigation";
import { availabilityLabel, recencyLabel, sourceRoleLabel } from "@/features/visual-v2/market-metadata";
import styles from "@/features/visual-v2/visual-v2.module.css";

const marketSignals = [
  "有多少岗位需要这项技能",
  "有多少家公司需要这项技能",
  "它覆盖多少种岗位方向",
  "它是否常和其他重要技能一起出现",
  "当前证据是否足够稳定",
] as const;

const technicalDetails = [
  { title: "市场支持度（Market Signal）", body: "综合岗位需求、公司覆盖、岗位方向覆盖和技能共同出现程度，形成 0–100 的市场信号。" },
  { title: "学习性价比公式（SkillWorth formula）", body: "学习性价比分数 = 市场支持度 × 学习时间折减因子。学习时间越长，折减越明显。" },
  { title: "排名稳健性（Robustness）", body: "改变指标权重和学习时间假设后，观察名次波动范围；它不等于统计显著性。" },
  { title: "证据可信度（Confidence）", body: "根据样本支持、覆盖范围和数据可用性描述证据质量，与排名稳健性是两个概念。" },
  { title: "技能与岗位分类表（Taxonomy）", body: "用版本化词表统一技能别名和岗位方向；无法可靠匹配的内容不会被强行归类。" },
  { title: "岗位去重（Dedup）", body: "采用偏保守的规则合并疑似重复岗位，并保留原始来源映射，避免重复记录放大需求。" },
  { title: "来源准入门槛（Source Gate）", body: "只有经过审查、符合使用条件的数据源才可进入指标计算；未获授权的来源保持关闭。" },
  { title: "原始、标准化、分析三层（Bronze / Silver / Gold）", body: "原始记录只追加保存；标准化层清洗字段；分析层使用去重岗位。每一步都保留版本和追溯关系。" },
  { title: "本地分析引擎（DuckDB）", body: "用于读取可追溯的数据文件并生成分析结果，不改变指标定义。" },
  { title: "来源追溯（Provenance）", body: "每条记录保留来源、导入时间、原始标识和处理版本，结果可以回查到证据。" },
  { title: "系统架构（Architecture）", body: "采集与授权、数据处理、分析计算、API 和页面展示彼此分离；页面不重复计算排名。" },
] as const;

export function MethodologyPage() {
  const result = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=main&robustness=all&recency_window=180d");
  const quality = useApi<DataQuality>("/data-quality");
  const release = useApi<ReleaseMetadata>("/release-metadata");
  const devops = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d&role=devops_engineer");
  const sparse = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d&role=technical_product_manager");
  const devopsRelations = useApi<SkillRelationsResponse>("/market/china-skill-relations?core_skill_id=devops_kubernetes&recency_window=180d&role_id=devops_engineer");
  const scope = result.data;
  const success = !result.error && scope && scope.job_count > 0 && scope.records.length > 0 ? scope : undefined;
  const empty = !result.error && scope && (scope.job_count === 0 || scope.records.length === 0);

  return <div className={`${styles.page} ${styles.methodologyPage}`}>
    <PublicNavigation />
    <main id="main-content" className={styles.methodologyMain}>
      <header className={styles.methodologyHero}>
        <nav aria-label="面包屑" className={styles.breadcrumb}><Link href="/#top">首页</Link><span aria-hidden="true">›</span><span>方法与数据</span></nav>
        <h1>这个排名是怎么算出来的？</h1>
        <p>先说容易理解的版本：我们比较技能在招聘市场中的支持度，再把学习时间考虑进去。它是学习决策参考，不是就业结果预测。</p>
      </header>

      <section className={styles.studentMethod} aria-label="学生可读的方法说明">
        <article className={styles.methodScope}>
          <div><h2>我们分析了什么？</h2><p>{success ? `当前结果来自${sourceRoleLabel(success.source_role)}。` : "数据成功读取后，这里会显示当前样本来源与范围。"}</p></div>
          {success ? <><dl>
            <div><dt>岗位</dt><dd>{success.job_count}</dd></div>
            <div><dt>公司</dt><dd>{success.company_count}</dd></div>
            <div><dt>技能</dt><dd>{success.skill_count}</dd></div>
            <div><dt>观察窗口</dt><dd>{recencyLabel(success.recency_window)}</dd></div>
          </dl>
          <p className={styles.methodMeta}>来源访问日：{success.access_date ?? "不可用"} · {release.data?.source_snapshot === success.snapshot && release.data.generated_at ? `安全产物生成日：${release.data.generated_at.slice(0, 10)}` : "安全产物生成日：不可用"} · 快照 {success.snapshot} · {sourceRoleLabel(success.source_role)} · {success.source_count} 个来源 · {success.market_scope}</p></> : <div className={styles.exploreState} role="status">{result.error ? <><p>当前数据暂时无法读取</p><button type="button" onClick={() => void result.mutate()}>重试</button></> : empty ? "当前筛选条件下没有可展示的技能" : "正在读取当前市场样本……"}</div>}
        </article>

        <article className={styles.methodQuestion}>
          <div><h2>数据怎样变成结果？</h2><p>来源、清洗、去重与观察窗口采用不同分母。生成日期表示产物完成时间，不表示当天新增岗位。</p></div>
          <div className={styles.evidenceList}>
            <p>Freehire 是当前唯一中国补充来源。原始导入、Silver 标准化、Gold canonical 去重后，按已冻结的 180 天窗口计算排名；完整真实数据只在本地管线处理，公开站点提供预计算只读聚合。</p>
            {quality.data ? <ul>
              <li>质量快照：{quality.data.silver_row_count} 条 Silver；角色明确匹配 {Math.round(quality.data.role_parse_rate * quality.data.silver_row_count)} / {quality.data.silver_row_count}，城市明确匹配 {Math.round(quality.data.city_parse_rate * quality.data.silver_row_count)} / {quality.data.silver_row_count}。分子由安全快照比率和 Silver 分母还原；这是 Silver 字段覆盖，不是 180 天 Gold 岗位比例。</li>
              <li>无法匹配的岗位方向保留为 other；未知字段不填 0，不把覆盖率当作模型准确率。技能覆盖显示为当前窗口的 {success?.skill_count ?? "不可用"} 项观测技能，岗位级抽取覆盖分子未随安全产物发布。</li>
            </ul> : <p>字段质量暂不可用；不会用 0 代替缺失值。</p>}
            <p>来源边界：单一补充样本不代表完整中国市场。薪资与趋势证据暂不可用；正式人工 Gold 评测未完成。</p>
          </div>
        </article>

        <article className={styles.methodQuestion}>
          <div><h2>三个可以复核的问题</h2><p>每个发现只适用于同一快照和 180 天窗口；请连同样本和限制阅读。</p></div>
          <div className={styles.evidenceList}>
            {(() => { const cpp = success?.records.find((record) => record.skill_id === "programming_cpp"); return <section><h3>热门就应先学吗？</h3><p>{cpp?.demand_rank != null && cpp.skillworth_rank != null ? `C++ 需求第 ${cpp.demand_rank}、学习性价比第 ${cpp.skillworth_rank}；假设从零学习约 ${cpp.learning_hours_expected} 小时。` : "当前证据暂不可用。"}方法是比较同一窗口的需求排名和含学习时间假设的排名。行动建议：先核对目标岗位与已有基础；不能据此说 C++ 不值得学。</p></section>; })()}
            {(() => { const relation = devopsRelations.data?.records.find((record) => record.related_skill_id === "devops_terraform"); const kubernetes = devops.data?.records.find((record) => record.skill_id === "devops_kubernetes"); return <section><h3>岗位方向需要什么组合？</h3><p>{relation && kubernetes && devops.data ? `DevOps 方向 ${devops.data.job_count} 个岗位中，Kubernetes 出现于 ${kubernetes.job_count} 个岗位；Kubernetes 与 Terraform 共同出现于 ${relation.cooccurrence_count} 个岗位。` : "当前岗位关系证据暂不可用。"}方法是对 canonical 岗位按技能对去重计数。行动建议：把共现当作技能组合线索，再读岗位要求；共现不代表因果或每个岗位必备。</p></section>; })()}
            <section><h3>何时不该给排名？</h3><p>{sparse.data ? `技术产品经理方向只有 ${sparse.data.job_count} 个岗位；当前 ${sparse.data.records.filter((record) => record.skillworth_rank != null).length} 项技能进入主排名层。` : "当前稀疏岗位证据暂不可用。"}样本稀疏时保留观察结果，先扩大合法样本再比较，不把空排名写成零需求或职业结论。</p></section>
          </div>
        </article>

        <article className={styles.methodQuestion}>
          <div><h2>名次会随假设变化吗？</h2><p>以下范围来自当前已计算的敏感性字段，保持同一快照与 180 天窗口。</p></div>
          <div className={styles.evidenceList}>{["programming_python", "database_sql", "programming_cpp"].map((id) => { const item = success?.records.find((record) => record.skill_id === id); return item && item.skillworth_rank != null ? <p key={id}>{item.skill}：基准第 {item.skillworth_rank} 名；{item.sensitivity_rank_min != null && item.sensitivity_rank_max != null ? `预设参数情景中第 ${item.sensitivity_rank_min}–${item.sensitivity_rank_max} 名。` : "敏感性范围暂不可用。"}</p> : null; })}<p>变化的是需求权重、广度和学习成本折算等模型假设；岗位样本不变。学习时间折算参数变化不等于测得个人学习时长，也不是未来预测。</p></div>
        </article>

        <article className={styles.methodQuestion}>
          <div><h2>市场价值怎么看？</h2><p>我们不只数岗位，还会看需求是否分散在不同公司和岗位方向中。</p></div>
          <ul>{marketSignals.map((item) => <li key={item}>{item}</li>)}</ul>
        </article>

        <article className={styles.methodQuestion}>
          <div><h2>为什么考虑学习时间？</h2><p>两个技能都被市场需要时，达到可用于初级岗位任务所需的时间不同。把学习投入纳入比较，才能回答“下一项先学什么”这一类问题。</p></div>
          <aside><strong>市场支持</strong><span>+</span><strong>学习投入</strong><span>→</span><strong>学习性价比</strong></aside>
        </article>

        <article className={styles.methodQuestion}>
          <div><h2>学习时间准确吗？</h2><p>这是模型假设，不是每个人的真实学习时间。它描述“从零达到可用于初级岗位任务”的预估区间，会受基础、课程和练习强度影响。</p></div>
          <p className={styles.trustStatement}>不能把学习时间当作课程时长、掌握承诺或就业保证。</p>
        </article>

        <article className={styles.methodLimits}>
          <div><h2>现在不能回答什么？</h2><p>这些限制直接公开，不用缺失数据制造看似完整的答案。</p></div>
          <dl>
            <div><dt>薪资比较</dt><dd>{success ? availabilityLabel(success.salary_signal_status) : "暂不可用"}</dd></div>
            <div><dt>市场趋势</dt><dd>{success ? availabilityLabel(success.trend_signal_status) : "暂不可用"}</dd></div>
            <div><dt>完整中国市场代表性</dt><dd>不具备</dd></div>
          </dl>
        </article>
      </section>

      <section className={styles.technicalAppendix} aria-labelledby="technical-title">
        <details>
          <summary id="technical-title"><span>查看技术细节</span><small>适合希望核对公式、数据处理和系统边界的读者</small></summary>
          <div className={styles.technicalGrid}>{technicalDetails.map((item) => <article key={item.title}><h2>{item.title}</h2><p>{item.body}</p></article>)}</div>
        </details>
      </section>
    </main>
    <footer className={styles.footer}><span>SkillWorth 2026</span><span>方法透明比假装完整更重要</span></footer>
  </div>;
}
