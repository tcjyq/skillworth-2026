"use client";

import { ArrowDown, ArrowRight } from "@phosphor-icons/react";
import { useGSAP } from "@gsap/react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Link from "next/link";
import { useEffect, useMemo, useRef } from "react";
import { ExperienceSwitcher } from "@/components/experience-switcher/experience-switcher";
import { deriveFinalFindings } from "@/features/skillworth-2026/findings";
import { useApi } from "@/hooks/use-api";
import type { ChinaSkillWorthResponse, RelatedSkills } from "@/lib/api/types";
import { ExploreMode } from "./explore-mode";
import { PublicNavigation } from "./public-navigation";
import { RoleFirst } from "./role-first";
import { CppMoment } from "./story-visuals";
import { VisualLoading } from "./visual-loading";
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

  useEffect(() => {
    if (findingLoading || window.location.hash !== "#analysis-results") return;
    const frame = window.requestAnimationFrame(() => document.getElementById("analysis-results")?.scrollIntoView({ block: "start" }));
    return () => window.cancelAnimationFrame(frame);
  }, [findingLoading]);

  useGSAP(() => {
    const media = gsap.matchMedia();
    media.add({ desktop: "(min-width: 900px) and (pointer: fine)", reduceMotion: "(prefers-reduced-motion: reduce)" }, (context) => {
      const { desktop, reduceMotion } = context.conditions as { desktop: boolean; reduceMotion: boolean };
      if (reduceMotion) return;

      gsap.timeline({ defaults: { ease: "expo.out" } })
        .fromTo("[data-motion-nav]", { clipPath: "inset(0 50% 100% 50%)" }, { clipPath: "inset(0 0% 0% 0%)", duration: 0.8 })
        .fromTo("[data-motion-hero-meta]", { scaleX: 0, opacity: 0.35, transformOrigin: "left center" }, { scaleX: 1, opacity: 1, duration: 0.62 }, 0.08)
        .fromTo("[data-motion-title] > span:first-child", { clipPath: "inset(100% 0 0 0)", yPercent: 16 }, { clipPath: "inset(0% 0 0 0)", yPercent: 0, duration: 0.72 }, 0.18)
        .fromTo("[data-motion-title] > span:last-child", { clipPath: "inset(100% 0 0 0)", yPercent: 10 }, { clipPath: "inset(0% 0 0 0)", yPercent: 0, duration: 0.82 }, 0.31)
        .fromTo("[data-motion-aperture]", { autoAlpha: 0, scale: 0.82, rotate: -31 }, { autoAlpha: 1, scale: 1, rotate: -17, duration: 1.05 }, 0.3)
        .fromTo("[data-motion-conclusion]", { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.72 }, 0.48)
        .fromTo("[data-motion-authority]", { clipPath: "inset(0 0 100% 0)" }, { clipPath: "inset(0 0 0% 0)", duration: 0.62 }, 0.58)
        .fromTo("[data-motion-actions]", { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.58 }, 0.68);

      if (!desktop) return;
      const hero = root.current?.querySelector<HTMLElement>("[data-signal-hero]");
      const aperture = root.current?.querySelector<HTMLElement>("[data-motion-aperture]");
      if (!hero || !aperture) return;
      const moveX = gsap.quickTo(aperture, "x", { duration: 0.75, ease: "power3.out" });
      const moveY = gsap.quickTo(aperture, "y", { duration: 0.75, ease: "power3.out" });
      const handlePointerMove = (event: PointerEvent) => {
        const bounds = hero.getBoundingClientRect();
        const x = Math.max(-1, Math.min(1, ((event.clientX - bounds.left) / bounds.width - 0.5) * 2));
        const y = Math.max(-1, Math.min(1, ((event.clientY - bounds.top) / bounds.height - 0.5) * 2));
        moveX(x * 13);
        moveY(y * 9);
        hero.style.setProperty("--signal-focus-x", `${50 + x * 3.5}%`);
        hero.style.setProperty("--signal-focus-y", `${50 + y * 3.5}%`);
      };
      const handlePointerLeave = () => {
        moveX(0);
        moveY(0);
        hero.style.setProperty("--signal-focus-x", "50%");
        hero.style.setProperty("--signal-focus-y", "50%");
      };
      hero.addEventListener("pointermove", handlePointerMove, { passive: true });
      hero.addEventListener("pointerleave", handlePointerLeave);
      return () => {
        hero.removeEventListener("pointermove", handlePointerMove);
        hero.removeEventListener("pointerleave", handlePointerLeave);
      };
    });
    return () => media.revert();
  }, { scope: root });

  useGSAP(() => {
    const ranks = root.current?.querySelector("[data-cpp-ranks]");
    const chapter = root.current?.querySelector("[data-cpp-moment]");
    if (!ranks || !chapter) return;

    const media = gsap.matchMedia();
    media.add("(min-width: 900px) and (prefers-reduced-motion: no-preference)", () => {
      const demand = ranks.querySelector("[data-cpp-sequence='demand']");
      const investment = ranks.querySelector("[data-cpp-sequence='investment']");
      const result = ranks.querySelector("[data-cpp-sequence='result']");
      const support = ranks.querySelectorAll("[data-cpp-support]");
      const holdState = { progress: 0 };
      if (!demand || !investment || !result) return;
      gsap.timeline({
        defaults: { ease: "none" },
        scrollTrigger: {
          id: "cpp-scroll-story",
          trigger: chapter,
          start: "top top",
          end: "+=160%",
          scrub: true,
          pin: chapter,
          pinSpacing: true,
        },
      })
        .addLabel("scene", 0)
        .fromTo(demand, { autoAlpha: 0.28, scale: 0.95, filter: "brightness(.58)" }, { autoAlpha: 1, scale: 1, filter: "brightness(1)", duration: 0.18 }, "scene")
        .addLabel("demand", 0.18)
        .addLabel("investment", 0.38)
        .fromTo(investment, { autoAlpha: 0.12, scaleX: 0.3, transformOrigin: "left center" }, { autoAlpha: 1, scaleX: 1, duration: 0.2 }, "investment")
        .addLabel("rank-shift", 0.58)
        .to(demand, { opacity: 0.62, filter: "brightness(.72)", duration: 0.08 }, "rank-shift")
        .addLabel("result", 0.66)
        .fromTo(result, { autoAlpha: 0.18, x: -14, filter: "blur(7px) brightness(.72)" }, { autoAlpha: 1, x: 0, filter: "blur(0px) brightness(1)", duration: 0.11 }, "result")
        .fromTo(support, { autoAlpha: 0.35 }, { autoAlpha: 1, duration: 0.12 }, 0.7)
        .addLabel("result-complete", 0.77)
        .to(holdState, { progress: 1, duration: 0.23 }, "result-complete")
        .addLabel("hold", 0.82)
        .addLabel("end", 1);
    });
    return () => media.revert();
  }, { scope: root, dependencies: [Boolean(availableFindings)], revertOnUpdate: true });

  const scope = frozenGlobal.data;
  const scopeSuccess = !frozenGlobal.error && scope && scope.job_count > 0 && scope.records.length > 0 ? scope : undefined;
  const scopeEmpty = !frozenGlobal.error && scope && (scope.job_count === 0 || scope.records.length === 0);

  function retryFindings() {
    for (const request of findingRequests) void request.mutate();
  }

  return <div ref={root} className={styles.page}>
    <PublicNavigation />

    <main>
      <section id="top" className={styles.hero} aria-labelledby="hero-title" data-signal-hero>
        <div className={styles.heroAtmosphere} aria-hidden="true"><span className={styles.heroAperture} data-motion-aperture><i className={styles.heroFocus} /></span><span className={styles.heroHalo} /></div>
        <div className={styles.heroMeta} data-motion-hero-meta><span>面向中国大学生的技能学习决策参考</span><span>{scopeSuccess ? accessDateLabel(scopeSuccess.access_date) : frozenGlobal.error ? "当前数据暂时无法读取" : scopeEmpty ? "当前样本暂无可展示数据" : "正在读取当前市场样本……"}</span></div>
        <h1 id="hero-title" aria-label="2026，学什么技术最值？" data-motion-title><span>2026，</span><span>学什么技术最值？</span></h1>
        <div className={styles.heroConclusion} data-motion-conclusion>
          {availableFindings ? <><strong>{availableFindings.frontier.map((record) => record.skill).join(" · ")}</strong><p>当前最稳健的学习性价比选择</p></> : findingError ? <><strong>当前数据暂时无法读取</strong><p>不会用手写排名替代失败的 API 结果</p></> : findingLoading ? <><strong>正在读取当前市场样本……</strong><p>结论将在证据完整后显示</p></> : <><strong>当前样本暂不支持冻结结论</strong><p>保留不可用状态，不制造推荐结果</p></>}
        </div>
        <div className={styles.authorityStrip} data-motion-authority>
          {scopeSuccess ? <><dl><div><dt>岗位</dt><dd>{scopeSuccess.job_count}</dd></div><div><dt>公司</dt><dd>{scopeSuccess.company_count}</dd></div><div><dt>技能</dt><dd>{scopeSuccess.skill_count}</dd></div><div><dt>观察窗口</dt><dd>{recencyLabel(scopeSuccess.recency_window)}</dd></div></dl>
          <p><b>来源</b> {sourceRoleLabel(scopeSuccess.source_role)}<br /><span>{scopeSuccess.disclaimer}</span></p></> : <p role="status">{frozenGlobal.error ? "当前数据暂时无法读取" : scopeEmpty ? "当前筛选条件下没有可展示的技能" : "正在读取当前市场样本……"}</p>}
        </div>
        <div className={styles.heroActions} data-motion-actions><a className={styles.primaryAction} href="#cpp"><span>看看为什么</span><ArrowDown size={20} /></a><a className={styles.secondaryAction} href="#roles">找适合我的方向</a></div>
        <div className={styles.heroSignalRail} aria-hidden="true"><span>MARKET SUPPORT · LEARNING INVESTMENT · EVIDENCE BOUNDARY · MARKET SUPPORT · LEARNING INVESTMENT · EVIDENCE BOUNDARY ·</span><span>MARKET SUPPORT · LEARNING INVESTMENT · EVIDENCE BOUNDARY · MARKET SUPPORT · LEARNING INVESTMENT · EVIDENCE BOUNDARY ·</span></div>
      </section>

      <section id="findings" className={styles.story} aria-label="SkillWorth 研究结论">
        <article id="cpp" className={`${styles.heroMoment} ${styles.cppChapter}`} data-cpp-moment>
          <div className={styles.momentCopy} data-cpp-copy><p>一个反直觉发现</p><h2>{availableFindings ? <>C++ 招聘需求排第 {availableFindings.cpp.demandRank}，<br />但学习性价比只排第 {availableFindings.cpp.skillworthRank}</> : findingError ? "当前数据暂时无法读取" : findingLoading ? "正在读取当前冻结发现……" : "当前样本暂不支持这项冻结发现"}</h2><p>同一项技能，招聘需求和学习性价比是两种不同排名。学习性价比（SkillWorth）会同时考虑市场支持和学习投入。</p>{findingError && <button type="button" onClick={retryFindings}>重试</button>}</div>
          {availableFindings && scopeSuccess ? <div data-cpp-ranks><CppMoment findings={availableFindings} metadata={scopeSuccess} /></div> : findingLoading ? <VisualLoading label="正在读取支持证据……" variant="panel" /> : <div className={styles.exploreState} role="status">{findingError ? "冻结发现所需证据暂时无法读取" : "当前样本没有足够证据展示该发现"}</div>}
        </article>
      </section>

      <section id="analysis-results" className={styles.analysisGateway} aria-labelledby="analysis-results-title">
        <div className={styles.analysisGatewayHeading}>
          <ExperienceSwitcher current="analysis" />
          <div>
            <p>数据分析结果</p>
            <h2 id="analysis-results-title">从目标职业出发，找到更值得投入的技能</h2>
          </div>
        </div>
        <div className={styles.fieldInvitation}>
          <p>自己探索其他技术</p>
          <strong>{scopeSuccess ? `在 ${scopeSuccess.skill_count} 项技能中自由探索，搜索你关心的技能或职业。` : "在当前市场样本中自由探索，搜索你关心的技能或职业。"}</strong>
          <span>看学习优先级，也看技能之间的关联关系。</span>
          <Link href="/skill-field">进入 3D 技能星域 <ArrowRight size={18} /></Link>
        </div>
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
