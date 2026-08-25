"use client";

import type { ChinaSkillWorthRecord, SkillRelationRecord } from "@/lib/api/types";
import styles from "../skill-field.module.css";
import { formatRelationEvidence } from "../scene/visual-system";

export function WebGLFallback({ skills, relations, onSelect }: { skills: ChinaSkillWorthRecord[]; relations: SkillRelationRecord[]; onSelect: (skillId: string) => void }) {
  const cpp = skills.find((skill) => skill.skill_id === "programming_cpp");
  return <section className={styles.fallback} aria-label="2D 技能列表">
    <header><h2>已切换到 2D 技能视图</h2><p>当前设备无法稳定初始化 WebGL。搜索、职业选择、技能详情和关系列表仍可使用。</p></header>
    {cpp?.demand_rank && cpp.skillworth_rank && <p className={styles.fallbackFinding}><strong>C++</strong><span>招聘需求 #{cpp.demand_rank} → 学习性价比 #{cpp.skillworth_rank}</span><small>热门，不一定最值得先学。</small></p>}
    <div className={styles.fallbackLists}>
      <div><h3>技能</h3>{skills.slice(0, 18).map((skill) => <button key={skill.skill_id} type="button" onClick={() => onSelect(skill.skill_id)}><span>{skill.skill}</span><small>{skill.skillworth_rank ? `学习性价比 #${skill.skillworth_rank}` : "仅观察"}</small></button>)}</div>
      <div><h3>当前关系</h3>{relations.length ? relations.slice(0, 12).map((relation) => <button key={relation.related_skill_id} type="button" onClick={() => onSelect(relation.related_skill_id)}><span>{relation.related_skill}</span><small>{formatRelationEvidence(relation.cooccurrence_count, relation.recency_window)}</small></button>) : <p>选择技能后查看关系。</p>}</div>
    </div>
  </section>;
}
