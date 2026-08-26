import Link from "next/link";
import styles from "./experience-switcher.module.css";

type ExperienceSwitcherProps = {
  current: "analysis" | "field";
};

const destinations = [
  { id: "analysis", href: "/lab/visual-v2#analysis-results", label: "分析结果" },
  { id: "field", href: "/lab/3d-skill-field", label: "3D 技能星域" },
] as const;

export function ExperienceSwitcher({ current }: ExperienceSwitcherProps) {
  return <nav className={styles.switcher} aria-label="分析结果与 3D 技能星域">
    {destinations.map((destination) => <Link
      key={destination.id}
      href={destination.href}
      aria-current={destination.id === current ? "page" : undefined}
    >
      {destination.label}
    </Link>)}
  </nav>;
}
