import { describe, expect, it } from "vitest";
import { initialSceneState, sceneReducer } from "./scene-machine";

describe("scene director state machine", () => {
  it("searching a skill preserves active role context", () => {
    const role = sceneReducer(initialSceneState, {
      type: "select-role",
      role: { roleId: "data_engineer", label: "数据工程师", sampleSize: 38 },
    });
    const relation = sceneReducer(role, { type: "select-skill", skillId: "python", skillLabel: "Python" });
    expect(relation.mode).toBe("RELATION_ROLE");
    expect(relation.activeRole?.roleId).toBe("data_engineer");
  });

  it("searching a role enters ROLE_VALUE without auto-selecting a skill", () => {
    const state = sceneReducer(initialSceneState, {
      type: "select-role",
      role: { roleId: "devops_engineer", label: "DevOps", sampleSize: 21 },
    });
    expect(state.mode).toBe("ROLE_VALUE");
    expect(state.activeSkill).toBeNull();
  });

  it("clearing a role restores global context", () => {
    const role = sceneReducer(initialSceneState, {
      type: "select-role",
      role: { roleId: "devops_engineer", label: "DevOps", sampleSize: 21 },
    });
    const relation = sceneReducer(role, { type: "select-skill", skillId: "kubernetes", skillLabel: "Kubernetes" });
    const global = sceneReducer(relation, { type: "clear-role" });
    expect(global.mode).toBe("RELATION_GLOBAL");
    expect(global.activeRole).toBeNull();
    expect(global.activeSkill?.skillId).toBe("kubernetes");
  });

  it("keeps at most five continuous-exploration path items", () => {
    let state = initialSceneState;
    for (const skillId of ["python", "sql", "spark", "kafka", "docker", "git"]) {
      state = sceneReducer(state, { type: "select-skill", skillId, skillLabel: skillId });
    }
    expect(state.explorationPath.map((item) => item.id)).toEqual(["sql", "spark", "kafka", "docker", "git"]);
  });
});
