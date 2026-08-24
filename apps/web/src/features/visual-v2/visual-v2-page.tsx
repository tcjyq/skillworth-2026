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
import { accessDateLabel, availabilityLabel, recencyLabel, sourceRoleLabel } from "./market-metadata";
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
  const findingRequests = [frozenGlobal, frozenDevops, frozenData, frozenAllActive, pythonRelated, numpyRelated, grafanaRelated];
  const findingError = findingRequests.some((request) => Boolean(request.error));
  const findingLoading = !findingError && findingRequests.some((request) => !request.data);
  const availableFindings = findingError ? null : findings;

  useGSAP(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    gsap.fromTo("[data-cpp-ranks]", { scale: 0.88 }, { scale: 1, ease: "none", scrollTrigger: { trigger: "[data-cpp-moment]", start: "top bottom", end: "center center", scrub: 0.6 } });
  }, { scope: root });

  const scope = frozenGlobal.data;
  const scopeSuccess = !frozenGlobal.error && scope && scope.job_count > 0 && scope.records.length > 0 ? scope : undefined;
  const scopeEmpty = !frozenGlobal.error && scope && (scope.job_count === 0 || scope.records.length === 0);

  function retryFindings() {
    for (const request of findingRequests) void request.mutate();
  }

  return <div ref={root} className={styles.page}>
    <PublicNavigation />

    <main>
      <section id="top" className={styles.hero} aria-labelledby="hero-title">
        <div className={styles.heroMeta}><span>面向中国大学生的技能学习决策参考</span><span>{scopeSuccess ? accessDateLabel(scopeSuccess.access_date) : frozenGlobal.error ? "当前数据暂时无法读取" : scopeEmpty ? "当前样本暂无可展示数据" : "正在读取当前市场样本……"}</span></div>
        <h1 id="hero-title">2026，学什么技术最值？</h1>
        <div className={styles.heroConclusion}>
          {availableFindings ? <><strong>{availableFindings.frontier.map((record) => record.skill).join(" · ")}</strong><p>当前最稳健的学习性价比选择</p></> : findingError ? <><strong>当前数据暂时无法读取</strong><p>不会用手写排名替代失败的 API 结果</p></> : findingLoading ? <><strong>正在读取当前市场样本……</strong><p>结论将在证据完整后显示</p></> : <><strong>当前样本暂不支持冻结结论</strong><p>保留不可用状态，不制造推荐结果</p></>}
        </div>
        <div className={styles.authorityStrip}>
          {scopeSuccess ? <><dl><div><dt>岗位</dt><dd>{scopeSuccess.job_count}</dd></div><div><dt>公司</dt><dd>{scopeSuccess.company_count}</dd></div><div><dt>技能</dt><dd>{scopeSuccess.skill_count}</dd></div><div><dt>观察窗口</dt><dd>{recencyLabel(scopeSuccess.recency_window)}</dd></div></dl>
          <p><b>来源</b> {sourceRoleLabel(scopeSuccess.source_role)}<br /><span>{scopeSuccess.disclaimer}</span></p></> : <p role="status">{frozenGlobal.error ? "当前数据暂时无法读取" : scopeEmpty ? "当前筛选条件下没有可展示的技能" : "正在读取当前市场样本……"}</p>}
        </div>
        <div className={styles.heroActions}><a className={styles.primaryAction} href="#cpp"><span>看看为什么</span><ArrowDown size={20} /></a><a className={styles.secondaryAction} href="#roles">找适合我的方向</a></div>
      </section>

      <section id="findings" className={styles.story} aria-label="SkillWorth 研究结论">
        <article id="cpp" className={`${styles.heroMoment} ${styles.cppChapter}`} data-cpp-moment>
          <div className={styles.momentCopy}><p>一个反直觉发现</p><h2>{availableFindings ? <>C++ 招聘需求排第 {availableFindings.cpp.demandRank}，<br />但学习性价比只排第 {availableFindings.cpp.skillworthRank}</> : findingError ? "当前数据暂时无法读取" : findingLoading ? "正在读取当前冻结发现……" : "当前样本暂不支持这项冻结发现"}</h2><p>同一项技能，招聘需求和学习性价比是两种不同排名。学习性价比（SkillWorth）会同时考虑市场支持和学习投入。</p>{findingError && <button type="button" onClick={retryFindings}>重试</button>}</div>
          {availableFindings && scopeSuccess ? <div data-cpp-ranks><CppMoment findings={availableFindings} metadata={scopeSuccess} /></div> : <div className={styles.exploreState} role="status">{findingError ? "冻结发现所需证据暂时无法读取" : findingLoading ? "正在读取支持证据……" : "当前样本没有足够证据展示该发现"}</div>}
        </article>
      </section>

      <RoleFirst />
      <ExploreMode />

      <section id="method-boundary" className={styles.limitations}>
        <div><h2>方法与数据边界</h2>{scopeSuccess ? <><p>{scopeSuccess.disclaimer} 学习性价比比较的是当前可观察样本中的学习投入与市场支持，不预测薪资、录用概率或未来趋势。</p>
          <dl className={styles.methodFacts}>
            <div><dt>分析范围</dt><dd>{scopeSuccess.job_count} 个岗位 · {scopeSuccess.company_count} 家公司 · {scopeSuccess.skill_count} 项技能</dd></div>
            <div><dt>时间</dt><dd>{recencyLabel(scopeSuccess.recency_window)} · {accessDateLabel(scopeSuccess.access_date)} · 快照 {scopeSuccess.snapshot}</dd></div>
            <div><dt>来源</dt><dd>{sourceRoleLabel(scopeSuccess.source_role)} · {scopeSuccess.market_scope} · {scopeSuccess.source_count} 个来源</dd></div>
            <div><dt>当前不能提供</dt><dd>薪资比较{availabilityLabel(scopeSuccess.salary_signal_status)} · 市场趋势{availabilityLabel(scopeSuccess.trend_signal_status)}</dd></div>
            <div><dt>学习时间</dt><dd>来自模型假设，不是课程完成或就业结果保证</dd></div>
            <div><dt>市场边界</dt><dd>当前样本不是完整中国招聘市场</dd></div>
          </dl></> : <div className={styles.exploreState} role="status">{frozenGlobal.error ? <><p>当前数据暂时无法读取</p><button type="button" onClick={() => void frozenGlobal.mutate()}>重试</button></> : scopeEmpty ? "当前筛选条件下没有可展示的技能" : "正在读取当前市场样本……"}</div>}
        </div>
        <Link href="/methodology">查看方法与数据 <ArrowRight size={18} /></Link>
      </section>
    </main>
    <footer className={styles.footer}><span>SkillWorth 2026</span><span>学习决策参考，不构成就业或课程承诺</span></footer>
  </div>;
}
