"use client";

import { ArrowCounterClockwise, Crosshair, X } from "@phosphor-icons/react";
import { shouldShowResetToGlobalHome, type SceneState } from "../state/scene-machine";
import styles from "../skill-field.module.css";

export function SceneModeControl({ state, onValue, onDemand, onReturnGlobal, onResetHome, onClearRole }: {
  state: SceneState;
  onValue: () => void;
  onDemand: () => void;
  onReturnGlobal: () => void;
  onResetHome: () => void;
  onClearRole: () => void;
}) {
  const globalMode = state.mode === "GLOBAL_VALUE" || state.mode === "GLOBAL_DEMAND";
  const showResetHome = shouldShowResetToGlobalHome(state);
  return <div className={styles.modeRow} aria-label="星域模式">
    {globalMode && <div className={styles.modeControl}>
      <button type="button" aria-pressed={state.mode === "GLOBAL_VALUE"} onClick={onValue}>学习优先</button>
      <button type="button" aria-pressed={state.mode === "GLOBAL_DEMAND"} onClick={onDemand}>只看招聘需求</button>
    </div>}
    {!globalMode && <button type="button" className={styles.textControl} onClick={onReturnGlobal}><ArrowCounterClockwise size={15} />回到全局</button>}
    <button type="button" className={`${styles.textControl} ${styles.homeReset}`} data-visible={showResetHome} aria-hidden={!showResetHome} disabled={!showResetHome} tabIndex={showResetHome ? undefined : -1} onClick={onResetHome}><ArrowCounterClockwise size={15} />回到全景</button>
    {state.activeRole && <button type="button" className={styles.textControl} onClick={onClearRole}><X size={15} />清除职业范围</button>}
  </div>;
}

export function ExplorationPath({ state, onSelect }: { state: SceneState; onSelect: (id: string, label: string) => void }) {
  if (!state.explorationPath.length && !state.activeRole) return null;
  return <nav aria-label="最近探索路径" className={styles.explorationPath}>
    <Crosshair size={14} aria-hidden="true" />
    {state.activeRole && <span>{state.activeRole.label}</span>}
    {state.explorationPath.map((item) => <button key={item.id} type="button" onClick={() => onSelect(item.id, item.label)}>{item.label}</button>)}
  </nav>;
}
