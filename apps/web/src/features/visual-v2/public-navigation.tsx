"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import styles from "./visual-v2.module.css";

const sections = [
  { id: "findings", label: "研究结论" },
  { id: "roles", label: "选职业方向" },
  { id: "explore", label: "查技术技能" },
] as const;

export function PublicNavigation() {
  const pathname = usePathname();
  const onHomepage = pathname === "/";
  const [activeSection, setActiveSection] = useState(onHomepage ? "findings" : "methodology");

  useEffect(() => {
    if (!onHomepage) return;

    const targets = [...sections.map((item) => item.id), "method-boundary"];
    const observer = new IntersectionObserver((entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (visible) setActiveSection(visible.target.id === "method-boundary" ? "methodology" : visible.target.id);
    }, { rootMargin: "-28% 0px -58%", threshold: [0, 0.15, 0.4] });

    targets.forEach((id) => {
      const target = document.getElementById(id);
      if (target) observer.observe(target);
    });
    return () => observer.disconnect();
  }, [onHomepage]);

  const homePath = onHomepage ? "#top" : "/#top";
  return <header className={styles.publicHeader} data-motion-nav>
    <Link href={homePath} className={styles.publicBrand} aria-label="SkillWorth 2026 首页">SkillWorth <span>2026</span></Link>
    <nav aria-label="公开产品导航">
      {sections.map((item) => <Link key={item.id} href={onHomepage ? `#${item.id}` : `/#${item.id}`} aria-current={activeSection === item.id ? "location" : undefined}>{item.label}</Link>)}
      <Link href="/methodology" aria-current={activeSection === "methodology" ? "page" : undefined}>方法与数据</Link>
    </nav>
  </header>;
}
