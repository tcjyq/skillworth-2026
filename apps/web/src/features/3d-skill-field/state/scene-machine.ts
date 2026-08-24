export type SceneMode = "GLOBAL_VALUE" | "GLOBAL_DEMAND" | "ROLE_VALUE" | "RELATION_GLOBAL" | "RELATION_ROLE";

export type RoleContext = { roleId: string; label: string; sampleSize: number };
export type SkillContext = { skillId: string; label: string };
export type ExplorationItem = { id: string; label: string; entity: "skill" };

export type SceneState = {
  mode: SceneMode;
  activeRole: RoleContext | null;
  activeSkill: SkillContext | null;
  selectedRelationId: string | null;
  explorationPath: ExplorationItem[];
  reducedMotion: boolean;
  transitionToken: number;
};

export const initialSceneState: SceneState = {
  mode: "GLOBAL_VALUE",
  activeRole: null,
  activeSkill: null,
  selectedRelationId: null,
  explorationPath: [],
  reducedMotion: false,
  transitionToken: 0,
};

export type SceneAction =
  | { type: "show-global-value" }
  | { type: "show-global-demand" }
  | { type: "select-role"; role: RoleContext }
  | { type: "select-skill"; skillId: string; skillLabel: string }
  | { type: "select-relation"; skillId: string }
  | { type: "clear-role" }
  | { type: "clear-selection" }
  | { type: "return-global" }
  | { type: "set-reduced-motion"; value: boolean };

function appendPath(path: ExplorationItem[], item: ExplorationItem) {
  const withoutDuplicate = path.filter((entry) => entry.id !== item.id);
  return [...withoutDuplicate, item].slice(-5);
}

export function sceneReducer(state: SceneState, action: SceneAction): SceneState {
  const transitionToken = state.transitionToken + 1;
  switch (action.type) {
    case "show-global-value":
      return { ...state, mode: "GLOBAL_VALUE", activeRole: null, activeSkill: null, selectedRelationId: null, transitionToken };
    case "show-global-demand":
      return { ...state, mode: "GLOBAL_DEMAND", activeRole: null, activeSkill: null, selectedRelationId: null, transitionToken };
    case "select-role":
      return { ...state, mode: "ROLE_VALUE", activeRole: action.role, activeSkill: null, selectedRelationId: null, explorationPath: [], transitionToken };
    case "select-skill": {
      const activeSkill = { skillId: action.skillId, label: action.skillLabel };
      return {
        ...state,
        mode: state.activeRole ? "RELATION_ROLE" : "RELATION_GLOBAL",
        activeSkill,
        selectedRelationId: null,
        explorationPath: appendPath(state.explorationPath, { id: action.skillId, label: action.skillLabel, entity: "skill" }),
        transitionToken,
      };
    }
    case "select-relation":
      return { ...state, selectedRelationId: action.skillId, transitionToken };
    case "clear-role":
      return {
        ...state,
        mode: state.activeSkill ? "RELATION_GLOBAL" : "GLOBAL_VALUE",
        activeRole: null,
        selectedRelationId: null,
        transitionToken,
      };
    case "clear-selection":
      return {
        ...state,
        mode: state.activeRole ? "ROLE_VALUE" : "GLOBAL_VALUE",
        activeSkill: null,
        selectedRelationId: null,
        transitionToken,
      };
    case "return-global":
      return { ...initialSceneState, reducedMotion: state.reducedMotion, transitionToken };
    case "set-reduced-motion":
      return { ...state, reducedMotion: action.value };
  }
}
