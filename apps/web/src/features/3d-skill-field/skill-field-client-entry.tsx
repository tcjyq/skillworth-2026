"use client";

import dynamic from "next/dynamic";
import styles from "./skill-field.module.css";

const SkillFieldPage = dynamic(
  () => import("./skill-field-page").then((module) => module.SkillFieldPage),
  {
    ssr: false,
    loading: () => <main className={styles.page} aria-busy="true"><div className={styles.canvasLoading} aria-label="正在初始化 3D 技能星域"><span /></div></main>,
  },
);

export function SkillFieldClientEntry() {
  return <SkillFieldPage />;
}
