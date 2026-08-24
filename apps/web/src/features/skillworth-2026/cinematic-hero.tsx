"use client";

import { memo, useCallback, useEffect, useRef } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import { compactNumber } from "./format";

type CinematicHeroProps = {
  robustPickCount: number | null;
  jobCount: number | null;
  companyCount: number | null;
  skillCount: number | null;
  windowLabel: string;
  sourceRole: string;
};

const ATMOSPHERE_SKILLS = ["Python", "SQL", "Docker", "Kubernetes", "RAG", "MARKET SIGNAL", "LEARNING EFFORT"];

export const CinematicHero = memo(function CinematicHero({ robustPickCount, jobCount, companyCount, skillCount, windowLabel, sourceRole }: CinematicHeroProps) {
  const heroRef = useRef<HTMLElement>(null);
  const frameRef = useRef<number | null>(null);

  useEffect(() => () => {
    if (frameRef.current != null) cancelAnimationFrame(frameRef.current);
  }, []);

  const moveAtmosphere = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    if (frameRef.current != null) cancelAnimationFrame(frameRef.current);
    const x = event.clientX;
    const y = event.clientY;
    frameRef.current = requestAnimationFrame(() => {
      const node = heroRef.current;
      if (!node) return;
      const bounds = node.getBoundingClientRect();
      const normalizedX = (x - bounds.left) / Math.max(bounds.width, 1);
      const normalizedY = (y - bounds.top) / Math.max(bounds.height, 1);
      node.style.setProperty("--hero-x", `${normalizedX * 100}%`);
      node.style.setProperty("--hero-y", `${normalizedY * 100}%`);
      node.style.setProperty("--hero-dx", `${(normalizedX - 0.5) * 14}px`);
      node.style.setProperty("--hero-dy", `${(normalizedY - 0.5) * 10}px`);
      node.style.setProperty("--hero-signal-dx", `${(normalizedX - 0.5) * 7}px`);
      node.style.setProperty("--hero-signal-dy", `${(normalizedY - 0.5) * 5}px`);
    });
  }, []);

  return (
    <section ref={heroRef} onPointerMove={moveAtmosphere} className="cinematic-hero" aria-labelledby="skillworth-question">
      <div className="hero-atmosphere" aria-hidden="true">
        <div className="hero-orbit" />
        {ATMOSPHERE_SKILLS.map((skill, index) => <span key={skill} className={`hero-signal hero-signal-${index + 1}`}>{skill}</span>)}
      </div>

      <div className="relative z-[1] mx-auto grid max-w-[1560px] gap-10 px-5 pb-10 pt-14 sm:px-8 sm:pb-12 sm:pt-18 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-end lg:px-12 lg:pb-14 lg:pt-22">
        <div className="min-w-0">
          <p className="font-mono text-[10px] uppercase tracking-[.16em] text-[var(--sw-accent)]">SKILLWORTH 2026 · CHINA OPEN TECH SAMPLE</p>
          <h1 id="skillworth-question" aria-label="2026，学什么技术最值？" className="hero-question mt-5 max-w-[980px] text-[clamp(2.35rem,5.45vw,5rem)] font-semibold leading-[.96] tracking-[-.038em]">
            <span>2026，学什么</span><span>技术最值？</span>
          </h1>
          <p className="mt-6 max-w-[690px] text-pretty text-[clamp(1rem,1.35vw,1.25rem)] leading-relaxed tracking-[-.015em] text-[var(--sw-text-secondary)]">从市场价值与学习投入重新看技术技能的性价比。</p>
          <p className="mt-2 text-sm text-[var(--sw-muted)]">基于 2026-08 当前可观察的中国公开技术岗位样本。</p>
        </div>

        <aside className="snapshot-module" aria-label="实时样本概览">
          <div className="snapshot-title"><span className="snapshot-pulse" aria-hidden="true" /> LIVE SNAPSHOT</div>
          <SnapshotMetric label="ROBUST PICKS" value={robustPickCount == null ? "—" : compactNumber(robustPickCount)} />
          <SnapshotMetric label="OBSERVED JOBS" value={jobCount == null ? "—" : compactNumber(jobCount)} />
          <SnapshotMetric label="COMPANIES" value={companyCount == null ? "—" : compactNumber(companyCount)} />
          <SnapshotMetric label="EVIDENCE" value="LIMITED" muted />
        </aside>
      </div>

      <div className="relative z-[1] border-y border-[var(--sw-line)]/80">
        <div className="hero-metadata mx-auto grid max-w-[1560px] grid-cols-2 px-5 sm:grid-cols-3 sm:px-8 lg:grid-cols-[125px_125px_145px_125px_195px_1fr] lg:px-12">
          <Metadata label="WINDOW" value={windowLabel.toUpperCase()} />
          <Metadata label="JOBS" value={jobCount == null ? "—" : compactNumber(jobCount)} />
          <Metadata label="COMPANIES" value={companyCount == null ? "—" : compactNumber(companyCount)} />
          <Metadata label="SKILLS" value={skillCount == null ? "—" : compactNumber(skillCount)} />
          <Metadata label="SCOPE" value="CHINA OPEN SAMPLE" />
          <div className="metadata-source col-span-2 flex min-h-16 items-center border-t border-[var(--sw-line)] py-3 text-[10px] leading-4 text-[var(--sw-muted)] sm:col-span-3 lg:col-span-1 lg:border-l lg:border-t-0 lg:pl-5">{sourceRole}<br className="hidden lg:block" /> · 不代表完整中国招聘市场</div>
        </div>
      </div>
    </section>
  );
});

function SnapshotMetric({ label, value, muted = false }: { label: string; value: string; muted?: boolean }) {
  return <div className="snapshot-row"><span>{label}</span><strong className={muted ? "text-[var(--sw-text-secondary)]" : "text-[var(--sw-accent)]"}>{value}</strong></div>;
}

function Metadata({ label, value }: { label: string; value: string }) {
  return <div className="metadata-cell min-w-0 border-r border-[var(--sw-line)] py-3.5 pr-3"><span className="block font-mono text-[9px] tracking-[.1em] text-[var(--sw-muted)]">{label}</span><span className="mt-1.5 block truncate font-mono text-xs text-[var(--sw-text)]">{value}</span></div>;
}
