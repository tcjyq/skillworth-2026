"use client";

import type { SkillRelationRecord } from "@/lib/api/types";
import styles from "../skill-field.module.css";

export function RelationRail({ relations, selectedId, onSelect }: { relations: SkillRelationRecord[]; selectedId: string | null; onSelect: (skillId: string) => void }) {
  if (!relations.length) return null;
  return <div className={styles.relationRail} aria-label="一级技能关系">
    <p>关系证据</p>
    <div>{relations.slice(0, 7).map((relation) => <button
      key={relation.related_skill_id}
      type="button"
      aria-pressed={selectedId === relation.related_skill_id}
      onPointerEnter={() => onSelect(relation.related_skill_id)}
      onClick={() => onSelect(relation.related_skill_id)}
    ><span>{relation.related_skill}</span><small>{relation.cooccurrence_count} 个共同岗位</small></button>)}</div>
  </div>;
}
