"use client";

import Link from "next/link";
import { useApi } from "@/hooks/use-api";
import type { ChinaSkillWorthResponse } from "@/lib/api/types";
import { PublicNavigation } from "@/features/visual-v2/public-navigation";
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
  const scope = result.data;

  return <div className={`${styles.page} ${styles.methodologyPage}`}>
    <PublicNavigation />
    <main id="main-content" className={styles.methodologyMain}>
      <header className={styles.methodologyHero}>
        <nav aria-label="面包屑" className={styles.breadcrumb}><Link href="/lab/visual-v2#top">首页</Link><span aria-hidden="true">›</span><span>方法与数据</span></nav>
        <h1>这个排名是怎么算出来的？</h1>
        <p>先说容易理解的版本：我们比较技能在招聘市场中的支持度，再把学习时间考虑进去。它是学习决策参考，不是就业结果预测。</p>
      </header>

      <section className={styles.studentMethod} aria-label="学生可读的方法说明">
        <article className={styles.methodScope}>
          <div><h2>我们分析了什么？</h2><p>当前结果来自可观察的中国公开技术岗位补充样本。</p></div>
          <dl>
            <div><dt>岗位</dt><dd>{scope?.job_count ?? "—"}</dd></div>
            <div><dt>公司</dt><dd>{scope?.company_count ?? "—"}</dd></div>
            <div><dt>技能</dt><dd>{scope?.skill_count ?? "—"}</dd></div>
            <div><dt>观察窗口</dt><dd>近 180 天</dd></div>
          </dl>
          <p className={styles.methodMeta}>数据截止 2026-08-10 · Freehire 中国公开技术岗位补充样本 · 当前仅有一个补充来源</p>
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
            <div><dt>薪资比较</dt><dd>不可用</dd></div>
            <div><dt>市场趋势</dt><dd>不可用</dd></div>
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
