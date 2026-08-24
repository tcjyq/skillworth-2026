import type { FinalFindings } from "@/features/skillworth-2026/findings";
import type { ChinaSkillWorthResponse } from "@/lib/api/types";
import { marketScopeLine } from "./market-metadata";
import styles from "./visual-v2.module.css";

export function CppMoment({ findings, metadata }: { findings: FinalFindings; metadata: ChinaSkillWorthResponse }) {
  const cpp = findings.cpp;
  return <div className={styles.cppMomentVisual}>
    <div className={styles.cppSkill}>C++</div>
    <div className={styles.cppRanks}><div data-cpp-sequence="demand"><span>招聘需求排名</span><strong>#{cpp.demandRank}</strong></div><div className={styles.cppTransition} data-cpp-sequence="investment"><small>加入学习投入后</small><i aria-hidden="true">→</i></div><div data-cpp-sequence="result"><span>学习性价比排名</span><strong>#{cpp.skillworthRank}</strong></div></div>
    <dl className={styles.cppFacts} data-cpp-support><div><dt>支持证据</dt><dd>{cpp.jobCount} 个岗位 · {cpp.companyCount} 家公司</dd></div><div><dt>当前学习投入假设</dt><dd>约 {cpp.learningHours} 小时</dd></div></dl>
    <p className={styles.cppAnnotation} data-cpp-support>招聘需求很强；计入学习时间后，学习性价比排名降至第 {cpp.skillworthRank}。</p>
    <p className={styles.chartSource}>{marketScopeLine(metadata)}</p>
  </div>;
}
