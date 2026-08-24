import styles from "./visual-v2.module.css";

export function VisualLoading({ label, variant = "panel" }: { label: string; variant?: "panel" | "explore" }) {
  const variantClass = variant === "explore" ? styles.visualLoadingExplore : "";

  return <div className={`${styles.visualLoading} ${variantClass}`} role="status" aria-busy="true">
    <div className={styles.loadingSignal} aria-hidden="true"><span /><span /><span /><span /></div>
    <div className={styles.loadingLines} aria-hidden="true"><i /><i /><i /></div>
    <p>{label}</p>
  </div>;
}
