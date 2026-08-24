import styles from "./visual-v2.module.css";

export function VisualLoading({ label, variant = "panel" }: { label: string; variant?: "panel" | "explore" }) {
  const variantClass = variant === "explore" ? styles.visualLoadingExplore : "";

  return <div className={`${styles.visualLoading} ${variantClass}`} role="status" aria-busy="true" aria-label={label}>
    <div className={styles.loadingSignal} aria-hidden="true">
      <span className={styles.loadingOrigin}><i /></span>
      <div className={styles.loadingEvidence}>
        <span data-loading-evidence><i /></span>
        <span data-loading-evidence><i /></span>
        <span data-loading-evidence><i /></span>
      </div>
    </div>
    <p><span aria-hidden="true" />{label}</p>
  </div>;
}
