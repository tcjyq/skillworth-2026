export type SceneMode = "GLOBAL_VALUE" | "GLOBAL_DEMAND" | "ROLE_VALUE" | "RELATION_GLOBAL" | "RELATION_ROLE";
export type BaseSceneMode = Extract<SceneMode, "GLOBAL_VALUE" | "GLOBAL_DEMAND" | "ROLE_VALUE">;
export type TransitionPhase =
  | "IDLE"
  | "HIGHLIGHT"
  | "CAMERA_FLY"
  | "CONSTELLATION_MORPH"
  | "SETTLED"
  | "RETURN_LINES"
  | "RETURN_MORPH"
  | "RETURN_CAMERA";
export type FocusSource = "search" | "pointer" | "relation";

export type RoleContext = { roleId: string; label: string; sampleSize: number };
export type SkillContext = { skillId: string; label: string };
export type ExplorationItem = { id: string; label: string; entity: "skill" };

export type SceneState = {
  mode: SceneMode;
  activeRole: RoleContext | null;
  activeSkill: SkillContext | null;
  relationSkill: SkillContext | null;
  selectedRelationId: string | null;
  explorationPath: ExplorationItem[];
  reducedMotion: boolean;
  transitionToken: number;
  transitionPhase: TransitionPhase;
  focusSource: FocusSource | null;
  returnMode: BaseSceneMode;
  relationOriginMode: BaseSceneMode;
  homeResetToken: number;
  hasDepartedGlobalHome: boolean;
};

export const initialSceneState: SceneState = {
  mode: "GLOBAL_VALUE",
  activeRole: null,
  activeSkill: null,
  relationSkill: null,
  selectedRelationId: null,
  explorationPath: [],
  reducedMotion: false,
  transitionToken: 0,
  transitionPhase: "IDLE",
  focusSource: null,
  returnMode: "GLOBAL_VALUE",
  relationOriginMode: "GLOBAL_VALUE",
  homeResetToken: 0,
  hasDepartedGlobalHome: false,
};

export type SceneAction =
  | { type: "show-global-value" }
  | { type: "show-global-demand" }
  | { type: "select-role"; role: RoleContext }
  | { type: "focus-skill"; skillId: string; skillLabel: string; source: FocusSource }
  | { type: "select-relation"; skillId: string }
  | { type: "clear-role" }
  | { type: "clear-relation-selection" }
  | { type: "start-return" }
  | { type: "reset-to-global-home" }
  | { type: "mark-camera-departure" }
  | { type: "advance-transition"; token: number; phase: Exclude<TransitionPhase, "HIGHLIGHT" | "IDLE" | "RETURN_LINES"> }
  | { type: "finish-return"; token: number }
  | { type: "interrupt-focus"; token: number }
  | { type: "set-reduced-motion"; value: boolean };

function appendPath(path: ExplorationItem[], item: ExplorationItem) {
  const withoutDuplicate = path.filter((entry) => entry.id !== item.id);
  return [...withoutDuplicate, item].slice(-5);
}

function isGlobalValueHome(state: SceneState) {
  return state.mode === "GLOBAL_VALUE"
    && !state.activeRole
    && !state.activeSkill
    && !state.relationSkill
    && !state.selectedRelationId
    && state.transitionPhase === "IDLE";
}

export function shouldShowResetToGlobalHome(state: SceneState) {
  return state.hasDepartedGlobalHome || !isGlobalValueHome(state);
}

export function sceneReducer(state: SceneState, action: SceneAction): SceneState {
  const transitionToken = state.transitionToken + 1;
  switch (action.type) {
    case "show-global-value":
      return { ...state, mode: "GLOBAL_VALUE", returnMode: "GLOBAL_VALUE", relationOriginMode: "GLOBAL_VALUE", activeRole: null, activeSkill: null, relationSkill: null, selectedRelationId: null, transitionPhase: "IDLE", focusSource: null, hasDepartedGlobalHome: state.hasDepartedGlobalHome || !isGlobalValueHome(state), transitionToken };
    case "show-global-demand":
      return { ...state, mode: "GLOBAL_DEMAND", returnMode: "GLOBAL_DEMAND", relationOriginMode: "GLOBAL_DEMAND", activeRole: null, activeSkill: null, relationSkill: null, selectedRelationId: null, transitionPhase: "IDLE", focusSource: null, hasDepartedGlobalHome: true, transitionToken };
    case "select-role":
      return { ...state, mode: "ROLE_VALUE", returnMode: "ROLE_VALUE", relationOriginMode: "ROLE_VALUE", activeRole: action.role, activeSkill: null, relationSkill: null, selectedRelationId: null, explorationPath: [], transitionPhase: "IDLE", focusSource: null, hasDepartedGlobalHome: true, transitionToken };
    case "focus-skill": {
      const activeSkill = { skillId: action.skillId, label: action.skillLabel };
      const interruptsReturn = state.transitionPhase.startsWith("RETURN_");
      const returnMode = state.mode === "RELATION_GLOBAL" || state.mode === "RELATION_ROLE"
        ? state.returnMode
        : state.mode;
      const baseMode = interruptsReturn ? state.returnMode : state.mode;
      const activeRole = interruptsReturn ? null : state.activeRole;
      return {
        ...state,
        mode: state.reducedMotion ? activeRole ? "RELATION_ROLE" : "RELATION_GLOBAL" : baseMode,
        activeRole,
        activeSkill,
        relationSkill: state.reducedMotion ? activeSkill : state.relationSkill,
        returnMode,
        relationOriginMode: interruptsReturn
          ? state.returnMode
          : state.mode === "RELATION_GLOBAL" || state.mode === "RELATION_ROLE" ? state.relationOriginMode : returnMode,
        selectedRelationId: null,
        explorationPath: appendPath(state.explorationPath, { id: action.skillId, label: action.skillLabel, entity: "skill" }),
        transitionPhase: state.reducedMotion ? "CONSTELLATION_MORPH" : "HIGHLIGHT",
        focusSource: action.source,
        hasDepartedGlobalHome: true,
        transitionToken,
      };
    }
    case "select-relation":
      return { ...state, selectedRelationId: action.skillId, hasDepartedGlobalHome: true };
    case "clear-role":
      return {
        ...state,
        mode: state.activeSkill ? "RELATION_GLOBAL" : "GLOBAL_VALUE",
        returnMode: "GLOBAL_VALUE",
        relationOriginMode: "GLOBAL_VALUE",
        activeRole: null,
        selectedRelationId: null,
        transitionToken,
      };
    case "clear-relation-selection":
      return { ...state, selectedRelationId: null };
    case "start-return":
      if (!state.relationSkill) return state;
      return { ...state, mode: state.reducedMotion ? "GLOBAL_VALUE" : state.mode, returnMode: "GLOBAL_VALUE", activeRole: state.reducedMotion ? null : state.activeRole, transitionPhase: state.reducedMotion ? "RETURN_MORPH" : "RETURN_LINES", selectedRelationId: null, focusSource: null, transitionToken };
    case "reset-to-global-home":
      return { ...initialSceneState, reducedMotion: state.reducedMotion, transitionToken, homeResetToken: state.homeResetToken + 1 };
    case "mark-camera-departure":
      return state.hasDepartedGlobalHome ? state : { ...state, hasDepartedGlobalHome: true };
    case "advance-transition": {
      if (action.token !== state.transitionToken) return state;
      if (action.phase === "CONSTELLATION_MORPH") {
        if (!state.activeSkill) return state;
        return {
          ...state,
          mode: state.activeRole ? "RELATION_ROLE" : "RELATION_GLOBAL",
          relationSkill: state.activeSkill,
          transitionPhase: action.phase,
        };
      }
      if (action.phase === "RETURN_MORPH") {
        return { ...state, mode: state.returnMode, activeRole: null, transitionPhase: action.phase, selectedRelationId: null };
      }
      if (action.phase === "SETTLED") return { ...state, transitionPhase: action.phase };
      if (action.phase === "RETURN_CAMERA") return { ...state, transitionPhase: action.phase };
      if (action.phase === "CAMERA_FLY") return { ...state, transitionPhase: action.phase };
      return state;
    }
    case "finish-return":
      if (action.token !== state.transitionToken) return state;
      return { ...state, activeSkill: null, relationSkill: null, selectedRelationId: null, transitionPhase: "IDLE", focusSource: null };
    case "interrupt-focus":
      if (action.token !== state.transitionToken || !["HIGHLIGHT", "CAMERA_FLY"].includes(state.transitionPhase)) return state;
      return { ...state, transitionPhase: "IDLE", focusSource: null };
    case "set-reduced-motion":
      return { ...state, reducedMotion: action.value };
  }
}
