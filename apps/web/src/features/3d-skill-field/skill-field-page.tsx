"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { ExperienceSwitcher } from "@/components/experience-switcher/experience-switcher";
import type { ChinaSkillWorthResponse, RolesResponse, SkillRelationsResponse } from "@/lib/api/types";
import { useApi } from "@/hooks/use-api";
import { buildSceneModel } from "./data/adapters";
import { roleEvidence } from "./layout";
import { SceneDirectorProvider, useSceneDirector } from "./state/scene-store";
import { CanvasBoundary } from "./ui/canvas-boundary";
import { DetailPanel } from "./ui/detail-panel";
import { RelationRail } from "./ui/relation-rail";
import { ExplorationPath, SceneModeControl } from "./ui/scene-controls";
import { SearchCommand } from "./ui/search-command";
import { WebGLFallback } from "./ui/webgl-fallback";
import styles from "./skill-field.module.css";

const SkillFieldCanvas = dynamic(() => import("./scene/skill-field-canvas"), {
  ssr: false,
  loading: () => <div className={styles.canvasLoading} aria-label="正在初始化 3D 技能星域"><span /></div>,
});

const GLOBAL_PATH = "/market/china-skillworth?eligibility=all&robustness=all&recency_window=180d";

function supportsWebGL() {
  const forced = new URLSearchParams(window.location.search).get("fallback") === "1";
  if (forced) return false;
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") || canvas.getContext("webgl"));
  } catch { return false; }
}

function sceneCopy(mode: string, role: string | null, skill: string | null, skillCount: number) {
  if (mode === "GLOBAL_DEMAND") return { title: "如果只看招聘需求，答案会怎么变？", description: "越靠近中心，当前岗位样本中出现得越多。星点大小仍表示岗位覆盖。" };
  if (mode === "ROLE_VALUE") return { title: `做${role ?? "这个职业"}，答案会怎么变？`, description: "越靠近中心，越值得在这个职业方向优先关注。" };
  if (mode.startsWith("RELATION")) return { title: `${skill ?? "这个技能"}，通常和哪些技能一起出现？`, description: "越靠近中心，关联越紧密；线越明显，共同岗位证据越多。" };
  return { title: `${skillCount} 项技术，哪些更值得你先学？`, description: "越靠近中心，越值得优先关注。星点略大，在当前岗位样本中出现得越多。" };
}

function SkillFieldExperience() {
  const { state, dispatch } = useSceneDirector();
  const global = useApi<ChinaSkillWorthResponse>(GLOBAL_PATH);
  const roles = useApi<RolesResponse>("/roles");
  const rolePath = state.activeRole ? `${GLOBAL_PATH}&role=${state.activeRole.roleId}` : null;
  const role = useApi<ChinaSkillWorthResponse>(rolePath);
  const relationParams = state.activeSkill ? new URLSearchParams({
    core_skill_id: state.activeSkill.skillId,
    recency_window: "180d",
    ...(state.activeRole ? { role_id: state.activeRole.roleId } : {}),
  }) : null;
  const relations = useApi<SkillRelationsResponse>(relationParams ? `/market/china-skill-relations?${relationParams}` : null);
  const [webgl, setWebgl] = useState<boolean | null>(null);
  const [relationExpansion, setRelationExpansion] = useState<{ skillId: string; limit: number } | null>(null);
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setWebgl(supportsWebGL()));
    return () => window.cancelAnimationFrame(frame);
  }, []);

  const globalRecords = useMemo(() => global.data?.records ?? [], [global.data?.records]);
  const effectiveState = useMemo(() => state.activeRole && role.data
    ? { ...state, activeRole: { ...state.activeRole, sampleSize: role.data.job_count } }
    : state, [role.data, state]);
  const roleGate = effectiveState.activeRole ? roleEvidence(effectiveState.activeRole.sampleSize) : null;
  const scopedRecords = useMemo(() => state.activeRole
    ? roleGate?.canRank ? role.data?.records ?? [] : globalRecords.map((record) => ({ ...record, skillworth_rank: null, demand_rank: null }))
    : globalRecords, [globalRecords, role.data?.records, roleGate?.canRank, state.activeRole]);
  const relationPrimaryLimit = relationExpansion && relationExpansion.skillId === state.activeSkill?.skillId ? relationExpansion.limit : 5;
  const model = useMemo(() => buildSceneModel({
    mode: state.mode,
    records: scopedRecords,
    globalRecords,
    activeSkillId: state.activeSkill?.skillId ?? null,
    selectedRelationId: state.selectedRelationId,
    relations: relations.data?.records ?? [],
    relationPrimaryLimit,
  }), [globalRecords, relationPrimaryLimit, relations.data?.records, scopedRecords, state.activeSkill?.skillId, state.mode, state.selectedRelationId]);
  const selectedRecord = (state.activeSkill
    ? scopedRecords.find((record) => record.skill_id === state.activeSkill?.skillId) ?? globalRecords.find((record) => record.skill_id === state.activeSkill?.skillId)
    : null) ?? null;
  const selectedRelation = relations.data?.records.find((item) => item.related_skill_id === state.selectedRelationId) ?? null;
  const sceneLimitations = [...new Set([
    ...(roleGate?.warning ? [roleGate.warning] : []),
    ...(relations.data?.limitations ?? []),
  ])];
  const cpp = globalRecords.find((record) => record.skill_id === "programming_cpp");
  const copy = sceneCopy(state.mode, effectiveState.activeRole?.label ?? null, state.activeSkill?.label ?? null, global.data?.skill_count ?? 0);

  const selectSkill = (skillId: string, label?: string) => {
    const record = globalRecords.find((item) => item.skill_id === skillId);
    dispatch({ type: "select-skill", skillId, skillLabel: label ?? record?.skill ?? skillId });
  };
  const selectRole = (roleId: string, label: string, sampleSize: number) => dispatch({ type: "select-role", role: { roleId, label, sampleSize } });
  const fallback = <WebGLFallback skills={scopedRecords} relations={relations.data?.records ?? []} onSelect={(skillId) => selectSkill(skillId)} />;

  const pageHeader = <header className={styles.localHeader}>
    <Link href="/lab/visual-v2#top" className={styles.localBrand} aria-label="返回 SkillWorth 2026">SkillWorth <span>2026</span><small>3D 技能星域 · Lab</small></Link>
    <div className={styles.experienceNavigation}><ExperienceSwitcher current="field" /></div>
    <nav className={styles.localAuxNavigation} aria-label="3D 技能星域辅助导航"><Link href="/methodology">方法与数据</Link><span>Signal Aperture Lab</span></nav>
  </header>;

  if (global.isLoading || roles.isLoading) return <main className={styles.page}>{pageHeader}<section className={styles.pageContent} aria-labelledby="skill-field-title"><div className={styles.pageIntro}><p>Signal Aperture Lab</p><h1 id="skill-field-title">3D 技能星域</h1><span>在可交互空间中探索学习优先级与技能关系。</span></div><section className={styles.visualizationFrame} aria-label="3D 技能星域可视化窗口"><div className={styles.canvasLoading} aria-label="正在读取技能星域"><span /></div></section></section></main>;
  if (global.error || roles.error || !global.data || !roles.data) return <main className={styles.page}>{pageHeader}<section className={styles.pageContent} aria-labelledby="skill-field-title"><div className={styles.pageIntro}><p>Signal Aperture Lab</p><h1 id="skill-field-title">3D 技能星域</h1><span>在可交互空间中探索学习优先级与技能关系。</span></div><section className={styles.visualizationFrame} aria-label="3D 技能星域可视化窗口"><div className={styles.canvasError}><h2>技能星域暂时无法加载</h2><p>分析数据未就绪。你可以稍后重试，现有 Visual V2.3.1 不受影响。</p><button type="button" onClick={() => { void global.mutate(); void roles.mutate(); }}>重试</button></div></section><footer className={styles.footer}><Link href="/lab/visual-v2#analysis-results">返回分析结果</Link><Link href="/methodology">查看计算方法与证据边界</Link></footer></section></main>;
  const globalData = global.data;

  return <main className={styles.page}>
    {pageHeader}
    <section className={styles.pageContent} aria-labelledby="skill-field-title">
      <div className={styles.pageIntro}>
        <p>Signal Aperture Lab</p>
        <h1 id="skill-field-title">3D 技能星域</h1>
        <span>在 {globalData.skill_count} 项技术中探索学习优先级与技能关系。</span>
      </div>
      <div className={styles.stageTop}>
        <SearchCommand skills={globalRecords} roles={roles.data.records} onSelectSkill={selectSkill} onSelectRole={selectRole} />
        <SceneModeControl state={effectiveState} onValue={() => dispatch({ type: "show-global-value" })} onDemand={() => dispatch({ type: "show-global-demand" })} onReturnGlobal={() => dispatch({ type: "return-global" })} onClearRole={() => dispatch({ type: "clear-role" })} />
      </div>
      <div className={styles.scopeRail} aria-label="数据范围"><span>{globalData.job_count} 个岗位 · {globalData.company_count} 家公司 · {globalData.skill_count} 项观测技能 · 近 180 天 · {globalData.source_role === "china_supplementary" ? "中国公开技术岗位补充样本" : globalData.source_role}</span></div>
      <div className={styles.sceneContext}>
        <p>{copy.description}<small>只看远近，不看方向。</small></p>
        {effectiveState.activeRole && <strong>{effectiveState.activeRole.label} · {effectiveState.activeRole.sampleSize} 个岗位样本</strong>}
      </div>
      <ExplorationPath state={effectiveState} onSelect={selectSkill} />
      <section className={styles.visualizationFrame} data-testid="skill-field-frame" aria-label="3D 技能星域可视化窗口">
        <header className={styles.frameHeader}><span>交互式可视化窗口</span><small>{copy.title}</small></header>
        <div className={styles.scenePane}>
          {webgl === null ? <div className={styles.canvasLoading}><span /></div> : webgl ? <CanvasBoundary fallback={fallback}><SkillFieldCanvas model={model} mode={state.mode} activeSkillId={state.activeSkill?.skillId ?? null} selectedRelationId={state.selectedRelationId} reducedMotion={state.reducedMotion} transitionToken={state.transitionToken} onSelect={selectSkill} onClearSelection={() => dispatch({ type: "clear-selection" })} onContextLost={() => setWebgl(false)} /></CanvasBoundary> : fallback}
          <div className={styles.legend} aria-label="图例"><span><i />越近，优先级越高</span><span><i />星点略大，岗位覆盖越高</span></div>
          {(state.mode === "GLOBAL_VALUE" || state.mode === "GLOBAL_DEMAND") && <div className={styles.valueCoreHint} data-testid="value-core-annotation"><span>价值核心</span>越靠近这里，越值得优先关注<small>只看远近，不看方向</small></div>}
          {sceneLimitations.map((item) => <p className={styles.sceneWarning} key={item}>{item}</p>)}
          {roleGate?.status === "insufficient" && <button className={styles.sceneAlternative} type="button" onClick={() => dispatch({ type: "clear-role" })}>查看全局{state.activeSkill ? "关系" : "星域"}</button>}
          {(state.mode === "GLOBAL_VALUE" || state.mode === "GLOBAL_DEMAND") && cpp?.demand_rank && cpp.skillworth_rank && <div key={state.mode} className={styles.rankShift} role="status"><span>C++</span><strong>{state.mode === "GLOBAL_DEMAND" ? `招聘需求 #${cpp.demand_rank}` : `#${cpp.demand_rank} → #${cpp.skillworth_rank} · 热门，不一定最值得先学。`}</strong></div>}
          <p className={styles.touchHint} data-testid="skill-field-touch-hint">单指旋转 · 双指缩放</p>
        </div>
      </section>
      <DetailPanel state={effectiveState} record={selectedRecord} relation={selectedRelation} onSelectRelation={selectSkill} />
      <RelationRail key={state.activeSkill?.skillId ?? "none"} relations={relations.data?.records ?? []} selectedId={state.selectedRelationId} onSelect={(skillId) => dispatch({ type: "select-relation", skillId })} onLimitChange={(limit) => setRelationExpansion({ skillId: state.activeSkill?.skillId ?? "", limit })} />
      <footer className={styles.footer}><p>{globalData.disclaimer}</p><Link href="/lab/visual-v2#analysis-results">返回分析结果</Link><Link href="/methodology">查看计算方法与证据边界</Link></footer>
    </section>
  </main>;
}

export function SkillFieldPage() {
  return <SceneDirectorProvider><SkillFieldExperience /></SceneDirectorProvider>;
}
