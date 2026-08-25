"use client";

import { useState } from "react";
import type { SkillRelationRecord } from "@/lib/api/types";
import styles from "../skill-field.module.css";

export function RelationRail({ relations, selectedId, onSelect, onLimitChange }: { relations: SkillRelationRecord[]; selectedId: string | null; onSelect: (skillId: string) => void; onLimitChange: (limit: number) => void }) {
  const [expanded, setExpanded] = useState(false);
  if (!relations.length) return null;
  return <div className={styles.relationRail} aria-label="一级技能关系">
    <p>关系证据</p>
    <div>{relations.slice(0, expanded ? 7 : 5).map((relation) => <button
      key={relation.related_skill_id}
      type="button"
      aria-pressed={selectedId === relation.related_skill_id}
      onPointerEnter={() => onSelect(relation.related_skill_id)}
      onClick={() => onSelect(relation.related_skill_id)}
    ><span>{relation.related_skill}</span><small>{relation.cooccurrence_count} 个共同岗位</small></button>)}
    {!expanded && relations.length > 5 && <button type="button" onClick={() => { setExpanded(true); onLimitChange(7); }}><span>再看 2 个</span><small>扩展主星</small></button>}</div>
  </div>;
}
