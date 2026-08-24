"use client";

import { createContext, useContext, useEffect, useMemo, useReducer } from "react";
import { initialSceneState, sceneReducer, type SceneAction, type SceneState } from "./scene-machine";

type SceneDirectorValue = { state: SceneState; dispatch: React.Dispatch<SceneAction> };

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
  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <SceneDirectorContext.Provider value={value}>{children}</SceneDirectorContext.Provider>;
}

export function useSceneDirector() {
  const value = useContext(SceneDirectorContext);
  if (!value) throw new Error("useSceneDirector must be used inside SceneDirectorProvider");
  return value;
}
