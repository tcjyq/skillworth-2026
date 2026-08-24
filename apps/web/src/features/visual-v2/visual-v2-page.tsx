"use client";

import { ArrowDown, ArrowRight } from "@phosphor-icons/react";
import { useGSAP } from "@gsap/react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Link from "next/link";
import { useMemo, useRef } from "react";
import { deriveFinalFindings } from "@/features/skillworth-2026/findings";
import { useApi } from "@/hooks/use-api";
import type { ChinaSkillWorthResponse, RelatedSkills } from "@/lib/api/types";
import { ExploreMode } from "./explore-mode";
import { PublicNavigation } from "./public-navigation";
import { RoleFirst } from "./role-first";
import { CppMoment } from "./story-visuals";
import styles from "./visual-v2.module.css";

gsap.registerPlugin(ScrollTrigger, useGSAP);

export function VisualV2Page() {
  const root = useRef<HTMLDivElement>(null);
  const frozenGlobal = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=main&robustness=all&recency_window=180d");
  const frozenDevops = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=main&robustness=all&recency_window=180d&role=devops_engineer");
  const frozenData = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=main&robustness=all&recency_window=180d&role=data_engineer");
  const frozenAllActive = useApi<ChinaSkillWorthResponse>("/market/china-skillworth?eligibility=main&robustness=all&recency_window=all_active");
  const pythonRelated = useApi<RelatedSkills>("/skills/programming_python/related");
  const numpyRelated = useApi<RelatedSkills>("/skills/data_analysis_numpy/related");
  const grafanaRelated = useApi<RelatedSkills>("/skills/devops_grafana/related");
  const findings = useMemo(() => deriveFinalFindings({ global: frozenGlobal.data, devops: frozenDevops.data, data: frozenData.data, allActive: frozenAllActive.data, pythonRelated: pythonRelated.data, numpyRelated: numpyRelated.data, grafanaRelated: grafanaRelated.data }), [frozenAllActive.data, frozenData.data, frozenDevops.data, frozenGlobal.data, grafanaRelated.data, numpyRelated.data, pythonRelated.data]);

  useGSAP(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    gsap.fromTo("[data-cpp-ranks]", { scale: 0.88 }, { scale: 1, ease: "none", scrollTrigger: { trigger: "[data-cpp-moment]", start: "top bottom", end: "center center", scrub: 0.6 } });
  }, { scope: root });

  const scope = frozenGlobal.data;
  return <div ref={root} className={styles.page}>
    <PublicNavigation />

    <main>
      <section id="top" className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroMeta}><span>面向中国大学生的技能学习决策参考</span><span>数据截止 2026-08-10</span></div>
        <h1 id="hero-title">2026，学什么技术最值？</h1>
        <div className={styles.heroConclusion}>
          <strong>Python · SQL · Git</strong>
          <p>当前最稳健的学习性价比选择</p>
        </div>
        <div className={styles.authorityStrip}>
          <dl><div><dt>岗位</dt><dd>{scope?.job_count ?? "—"}</dd></div><div><dt>公司</dt><dd>{scope?.company_count ?? "—"}</dd></div><div><dt>技能</dt><dd>{scope?.skill_count ?? "—"}</dd></div><div><dt>观察窗口</dt><dd>近 180 天</dd></div></dl>
          <p><b>来源</b> Freehire 中国公开技术岗位补充样本<br /><span>不代表完整中国技术招聘市场</span></p>
        </div>
        <div className={styles.heroActions}><a className={styles.primaryAction} href="#cpp"><span>看看为什么</span><ArrowDown size={20} /></a><a className={styles.secondaryAction} href="#roles">找适合我的方向</a></div>
      </section>

      <section id="findings" className={styles.story} aria-label="SkillWorth 研究结论">
        <article id="cpp" className={`${styles.heroMoment} ${styles.cppChapter}`} data-cpp-moment>
          <div className={styles.momentCopy}><p>一个反直觉发现</p><h2>C++ 招聘需求排第 3，<br />但学习性价比只排第 35</h2><p>同一项技能，招聘需求和学习性价比是两种不同排名。学习性价比（SkillWorth）会同时考虑市场支持和学习投入。</p></div>
          <div data-cpp-ranks><CppMoment findings={findings} /></div>
        </article>
      </section>

      <RoleFirst />
      <ExploreMode />

      <section id="method-boundary" className={styles.limitations}>
        <div><h2>方法与数据边界</h2><p>{scope?.disclaimer ?? "该样本不代表完整中国招聘市场。"} 学习性价比比较的是当前可观察样本中的学习投入与市场支持，不预测薪资、录用概率或未来趋势。</p>
          <dl className={styles.methodFacts}>
            <div><dt>分析范围</dt><dd>{scope?.job_count ?? "—"} 个岗位 · {scope?.company_count ?? "—"} 家公司 · {scope?.skill_count ?? "—"} 项技能</dd></div>
            <div><dt>时间</dt><dd>近 180 天 · 数据截止 2026-08-10</dd></div>
            <div><dt>来源</dt><dd>Freehire 中国公开技术岗位补充样本 · 当前仅有一个补充来源</dd></div>
            <div><dt>当前不能提供</dt><dd>薪资比较{scope?.salary_signal_status === "unavailable" ? "不可用" : "可用"} · 市场趋势{scope?.trend_signal_status === "unavailable" ? "不可用" : "可用"}</dd></div>
            <div><dt>学习时间</dt><dd>来自模型假设，不是课程完成或就业结果保证</dd></div>
            <div><dt>市场边界</dt><dd>当前样本不是完整中国招聘市场</dd></div>
          </dl>
        </div>
        <Link href="/methodology">查看方法与数据 <ArrowRight size={18} /></Link>
      </section>
    </main>
    <footer className={styles.footer}><span>SkillWorth 2026</span><span>学习决策参考，不构成就业或课程承诺</span></footer>
  </div>;
}
