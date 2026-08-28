"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useReducer } from "react";
import { initialSceneState, sceneReducer, type FocusSource, type SceneAction, type SceneState } from "./scene-machine";

type SceneDirectorValue = {
  state: SceneState;
  dispatch: React.Dispatch<SceneAction>;
  focusSkill: (skillId: string, skillLabel: string, source: FocusSource) => void;
};

const SceneDirectorContext = createContext<SceneDirectorValue | null>(null);

export function SceneDirectorProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(sceneReducer, initialSceneState);
  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => dispatch({ type: "set-reduced-motion", value: media.matches });
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (state.transitionPhase !== "RETURN_LINES") return;
    const token = state.transitionToken;
    const timer = window.setTimeout(() => dispatch({ type: "advance-transition", token, phase: "RETURN_MORPH" }), 150);
    return () => window.clearTimeout(timer);
  }, [state.transitionPhase, state.transitionToken]);
  const focusSkill = useCallback((skillId: string, skillLabel: string, source: FocusSource) => {
    dispatch({ type: "focus-skill", skillId, skillLabel, source });
  }, []);
  const value = useMemo(() => ({ state, dispatch, focusSkill }), [focusSkill, state]);
  return <SceneDirectorContext.Provider value={value}>{children}</SceneDirectorContext.Provider>;
}

export function useSceneDirector() {
  const value = useContext(SceneDirectorContext);
  if (!value) throw new Error("useSceneDirector must be used inside SceneDirectorProvider");
  return value;
}
