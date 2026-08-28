"use client";

import { ArrowRight } from "@phosphor-icons/react";
import type { FinalFindings } from "./findings";

export function StoryPrelude() {
  return (
    <section className="border-b border-[var(--sw-line)]" aria-labelledby="findings-intro-title">
      <div className="mx-auto grid max-w-[1560px] gap-4 px-5 py-9 sm:px-8 md:grid-cols-[260px_1fr] lg:px-12">
        <div><p className="section-kicker">ANALYSIS FREEZE V1</p><h2 id="findings-intro-title" className="mt-3 text-xl font-semibold tracking-[-.025em]">KEY FINDINGS</h2></div>
        <p className="max-w-[820px] text-pretty text-[15px] leading-7 text-[var(--sw-text-secondary)] lg:text-sm">答案不是一张排行榜：先看学习效率前沿，再看需求与技值的背离；目标岗位会改变答案，技能组合有不同强度，而排名必须连同敏感性区间一起读。</p>
      </div>
    </section>
  );
}

export function FrontierFindings({ findings }: { findings: FinalFindings | null }) {
  if (!findings) return <NarrativeLoading label="正在读取冻结的 Frontier 证据" />;
  return (
    <div className="grid border-b border-[var(--sw-line)] lg:grid-cols-2" aria-label="Efficiency Frontier 与 Demand divergence">
      <article className="py-7 pr-0 lg:border-r lg:border-[var(--sw-line)] lg:pr-10">
        <p className="section-kicker">01 · EFFICIENCY FRONTIER</p>
        <h3 aria-label="EFFICIENCY FRONTIER · Python → SQL → Git" className="mt-4 text-2xl font-semibold tracking-[-.03em] text-[var(--sw-text)] sm:text-3xl">Python → SQL → Git</h3>
        <p className="mt-3 max-w-[610px] text-[15px] leading-7 text-[var(--sw-muted)] lg:text-xs lg:leading-6">在通过候选门槛且排名稳健的具体技能中，三者组成当前 180d 的效率前沿。</p>
        <dl className="mt-6 divide-y divide-[var(--sw-line)] border-y border-[var(--sw-line)]">
          {findings.frontier.map((skill) => (
            <div key={skill.skill_id} className="grid grid-cols-[1fr_repeat(3,auto)] items-baseline gap-4 py-3 text-xs">
              <dt className="font-medium text-[var(--sw-text)]">{skill.skill}</dt>
              <dd className="font-mono text-[var(--sw-text-secondary)]">Signal {skill.market_signal.toFixed(2)}</dd>
              <dd className="font-mono text-[var(--sw-text-secondary)]">{skill.learning_hours_expected}h</dd>
              <dd className="font-mono text-[var(--sw-accent)]">#{skill.skillworth_rank} · {skill.skillworth_score.toFixed(2)}</dd>
            </div>
          ))}
        </dl>
      </article>

      <article className="py-7 lg:pl-10">
        <p className="section-kicker">02 · DEMAND ≠ SKILLWORTH</p>
        <h3 className="mt-4 text-2xl font-semibold tracking-[-.03em] text-[var(--sw-text)] sm:text-3xl">C++ 的需求很强，学习决策排序不同</h3>
        <div className="mt-6 flex flex-wrap items-center gap-3 font-mono text-sm">
          <span className="border-y border-[var(--sw-line-strong)] py-2 text-[var(--sw-text)]">Demand #{findings.cpp.demandRank}</span>
          <ArrowRight aria-hidden="true" className="text-[var(--sw-muted)]" size={16} />
          <span className="border-y border-[var(--sw-line-strong)] py-2 text-[var(--sw-warning)]">SkillWorth #{findings.cpp.skillworthRank}</span>
        </div>
        <p className="mt-5 max-w-[610px] text-[15px] leading-7 text-[var(--sw-text-secondary)] lg:text-xs lg:leading-6">{findings.cpp.jobCount} 个岗位；在从零达到可用于初级岗位任务的 <strong className="font-mono font-medium text-[var(--sw-text)]">{findings.cpp.learningHours}h 预期学习投入假设</strong>下，市场信号会被学习投入折损。这不是“C++ 不值得学”，而是需求排名不等于学习投资优先级。</p>
      </article>
    </div>
  );
}

export function RoleReversalStory({ findings, onSelectRole }: { findings: FinalFindings | null; onSelectRole: (role: "devops_engineer" | "data_engineer") => void }) {
  return (
    <section className="cinematic-reveal border-y border-[var(--sw-line)]" aria-labelledby="role-story-title">
      <div className="mx-auto max-w-[1560px] px-5 py-18 sm:px-8 lg:px-12 lg:py-22">
        <div className="grid gap-4 md:grid-cols-[260px_1fr]">
          <div><p className="section-kicker">03 · ROLE REVERSAL</p><h2 id="role-story-title" className="mt-3 text-xl font-semibold tracking-[-.025em] sm:text-2xl">YOUR ROLE CHANGES THE ANSWER</h2></div>
          <p className="max-w-[720px] text-[15px] leading-7 text-[var(--sw-muted)] lg:text-xs lg:leading-6">同一套 SkillWorth 方法，换成目标岗位切片后，专业技术栈会越过全局通用技能。样本量必须与角色排名同时阅读。</p>
        </div>
        {findings ? <div className="mt-9 grid border-y border-[var(--sw-line)] lg:grid-cols-2">
          {findings.roles.map((role, index) => (
            <article key={role.role} className={`py-7 ${index === 0 ? "lg:border-r lg:border-[var(--sw-line)] lg:pr-10" : "border-t border-[var(--sw-line)] lg:border-t-0 lg:pl-10"}`}>
              <div className="flex items-baseline justify-between gap-5"><h3 className="text-2xl font-semibold tracking-[-.03em]">{role.role}</h3><span className="font-mono text-xs text-[var(--sw-accent)]">n={role.sampleSize}</span></div>
              {role.sampleSize < 30 && <p className="mt-3 text-xs leading-5 text-[var(--sw-warning)]">小样本，仅供方向参考</p>}
              <div className="mt-6 divide-y divide-[var(--sw-line)]">
                {role.skills.map((skill) => <div key={skill.skill} className="grid grid-cols-[1fr_auto] items-center py-4"><span className="text-sm text-[var(--sw-text-secondary)]">{skill.skill}</span><strong className="font-mono text-base font-medium text-[var(--sw-text)]">#{skill.globalRank} → #{skill.roleRank}</strong></div>)}
              </div>
              <button onClick={() => onSelectRole(role.role === "DevOps" ? "devops_engineer" : "data_engineer")} className="sw-focus mt-5 inline-flex min-h-11 items-center gap-2 text-sm text-[var(--sw-accent)] hover:text-[#e0ed9b] lg:text-xs">查看 {role.role} 排名 <ArrowRight size={14} /></button>
            </article>
          ))}
        </div> : <NarrativeLoading label="正在读取角色切片证据" />}
      </div>
    </section>
  );
}

export function SynergyStory({ findings }: { findings: FinalFindings | null }) {
  return (
    <section className="cinematic-reveal mx-auto max-w-[1560px] px-5 py-18 sm:px-8 lg:px-12 lg:py-22" aria-labelledby="synergy-story-title">
      <div className="grid gap-4 md:grid-cols-[260px_1fr]">
        <div><p className="section-kicker">04 · SKILL SYNERGY</p><h2 id="synergy-story-title" className="mt-3 text-xl font-semibold tracking-[-.025em] sm:text-2xl">SKILLS COME IN STACKS</h2></div>
        <p className="max-w-[760px] text-[15px] leading-7 text-[var(--sw-muted)] lg:text-xs lg:leading-6">Absolute cooccurrence 回答“共同出现了多少次”；Jaccard / PMI affinity 回答“相对各自出现频率，它们有多偏好一起出现”。两者不能混为同一个强度。</p>
      </div>
      {findings ? <div className="mt-9 grid border-y border-[var(--sw-line)] lg:grid-cols-[.9fr_1.1fr]">
        <article className="py-8 lg:border-r lg:border-[var(--sw-line)] lg:pr-12">
          <p className="section-kicker">SCALE STRENGTH · ABSOLUTE</p><h3 className="mt-4 text-3xl font-semibold tracking-[-.035em]">{findings.synergy.scale.pair}</h3>
          <p className="mt-5 font-mono text-2xl text-[var(--sw-accent)]">{findings.synergy.scale.cooccurrence} co-jobs</p>
          <p className="mt-2 font-mono text-xs text-[var(--sw-muted)]">Jaccard {findings.synergy.scale.jaccard.toFixed(4)} · PMI {findings.synergy.scale.pmi.toFixed(4)}</p>
        </article>
        <article className="border-t border-[var(--sw-line)] py-8 lg:border-t-0 lg:pl-12">
          <p className="section-kicker">AFFINITY STRENGTH · RELATIVE</p>
          <div className="mt-2 divide-y divide-[var(--sw-line)]">
            {findings.synergy.affinity.map((pair) => <div key={pair.pair} className="grid gap-2 py-5 sm:grid-cols-[1fr_auto] sm:items-center"><div><h3 className="text-lg font-medium text-[var(--sw-text)]">{pair.pair}</h3><p className="mt-1 font-mono text-[10px] text-[var(--sw-muted)]">{pair.cooccurrence} co-jobs</p></div><p className="flex flex-wrap gap-x-2 font-mono text-xs text-[var(--sw-text-secondary)]"><span>Jaccard {pair.jaccard.toFixed(4)}</span><span className="text-[var(--sw-line-strong)]">/</span><span>PMI {pair.pmi.toFixed(4)}</span></p></div>)}
          </div>
        </article>
      </div> : <NarrativeLoading label="正在读取技能图证据" />}
      {findings && <p className="mt-5 max-w-[920px] text-[15px] leading-7 text-[var(--sw-muted)] lg:text-xs lg:leading-6">网络分母为 <strong className="font-mono font-medium text-[var(--sw-text-secondary)]">{findings.synergy.sampleSize.toLocaleString("en-US")} all-active canonical jobs</strong>，不是 180d 独立网络。共现是关联，不是因果，也不表示这些技能必须一起学。</p>}
    </section>
  );
}

export function RobustCoreHeading({ findings }: { findings: FinalFindings | null }) {
  return (
    <div className="mb-8 grid gap-5 md:grid-cols-[260px_1fr]" aria-labelledby="picks-title">
      <div><p className="section-kicker">05 · ROBUST CORE</p><h2 id="picks-title" className="mt-3 text-xl font-semibold tracking-[-.025em] sm:text-2xl">TRUST THE CORE, NOT EVERY RANK</h2></div>
      <div>
        <p className="max-w-[760px] text-[15px] leading-7 text-[var(--sw-muted)] lg:text-xs lg:leading-6">头部技能在既有权重情景下形成稳定核心；长尾必须读区间，而不是把当前单一名次当成确定事实。</p>
        {findings ? <div className="mt-5 flex flex-wrap gap-x-6 gap-y-3 border-y border-[var(--sw-line)] py-4">
          {findings.robustCore.map((item) => <span key={item.skill} className="inline-flex items-baseline gap-2 text-xs"><span className="text-[var(--sw-text-secondary)]">{item.skill}</span><strong className={`font-mono font-medium ${item.max - item.min <= 2 ? "text-[var(--sw-accent)]" : "text-[var(--sw-warning)]"}`}>{item.min}–{item.max}</strong></span>)}
        </div> : <NarrativeLoading label="正在读取排名敏感性区间" />}
        <p className="mt-4 text-[13px] leading-6 text-[var(--sw-muted)] lg:text-[11px] lg:leading-5">90d / 365d / all-active 的窗口一致性只作为 supporting evidence；窗口重叠且不是 trend。</p>
      </div>
    </div>
  );
}

function NarrativeLoading({ label }: { label: string }) {
  return <p role="status" className="border-y border-[var(--sw-line)] py-8 text-xs text-[var(--sw-muted)]">{label}…</p>;
}
