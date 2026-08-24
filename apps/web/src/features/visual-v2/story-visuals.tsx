import type { FinalFindings } from "@/features/skillworth-2026/findings";
import styles from "./visual-v2.module.css";

export function CppMoment({ findings }: { findings: FinalFindings | null }) {
  const cpp = findings?.cpp;
  return <div className={styles.cppMomentVisual}>
    <div className={styles.cppSkill}>C++</div>
    <div className={styles.cppRanks}><div><span>招聘需求排名</span><strong>{cpp ? `#${cpp.demandRank}` : "—"}</strong></div><div className={styles.cppTransition}><small>加入学习投入后</small><i aria-hidden="true">→</i></div><div><span>学习性价比排名</span><strong>{cpp ? `#${cpp.skillworthRank}` : "—"}</strong></div></div>
    <dl className={styles.cppFacts}><div><dt>支持证据</dt><dd>{cpp?.jobCount ?? "—"} 个岗位 · {cpp?.companyCount ?? "—"} 家公司</dd></div><div><dt>当前学习投入假设</dt><dd>约 {cpp?.learningHours ?? "—"} 小时</dd></div></dl>
    <p className={styles.cppAnnotation}>招聘需求很强；计入学习时间后，学习性价比排名降至第 {cpp?.skillworthRank ?? "—"}。</p>
    <p className={styles.chartSource}>样本：998 个岗位 · 近 180 天 · 数据截止 2026-08-10</p>
  </div>;
}
