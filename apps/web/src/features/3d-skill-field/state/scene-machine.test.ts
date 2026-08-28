import { describe, expect, it } from "vitest";
import { initialSceneState, sceneReducer } from "./scene-machine";

describe("scene director state machine", () => {
  it("searching a skill preserves active role context", () => {
    const role = sceneReducer(initialSceneState, {
      type: "select-role",
      role: { roleId: "data_engineer", label: "数据工程师", sampleSize: 38 },
    });
    const focusing = sceneReducer(role, { type: "focus-skill", skillId: "python", skillLabel: "Python", source: "search" });
    expect(focusing.mode).toBe("ROLE_VALUE");
    expect(focusing.transitionPhase).toBe("HIGHLIGHT");
    const relation = sceneReducer(focusing, { type: "advance-transition", token: focusing.transitionToken, phase: "CONSTELLATION_MORPH" });
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
    const focusing = sceneReducer(role, { type: "focus-skill", skillId: "kubernetes", skillLabel: "Kubernetes", source: "search" });
    const relation = sceneReducer(focusing, { type: "advance-transition", token: focusing.transitionToken, phase: "CONSTELLATION_MORPH" });
    const global = sceneReducer(relation, { type: "clear-role" });
    expect(global.mode).toBe("RELATION_GLOBAL");
    expect(global.activeRole).toBeNull();
    expect(global.activeSkill?.skillId).toBe("kubernetes");
  });

  it("keeps at most five continuous-exploration path items", () => {
    let state = initialSceneState;
    for (const skillId of ["python", "sql", "spark", "kafka", "docker", "git"]) {
      state = sceneReducer(state, { type: "focus-skill", skillId, skillLabel: skillId, source: "search" });
    }
    expect(state.explorationPath.map((item) => item.id)).toEqual(["sql", "spark", "kafka", "docker", "git"]);
  });

  it("ignores stale transition completions after the target changes", () => {
    const python = sceneReducer(initialSceneState, { type: "focus-skill", skillId: "python", skillLabel: "Python", source: "search" });
    const sql = sceneReducer(python, { type: "focus-skill", skillId: "sql", skillLabel: "SQL", source: "search" });
    const stale = sceneReducer(sql, { type: "advance-transition", token: python.transitionToken, phase: "CONSTELLATION_MORPH" });
    expect(stale.activeSkill?.skillId).toBe("sql");
    expect(stale.mode).toBe("GLOBAL_VALUE");
    expect(stale.transitionPhase).toBe("HIGHLIGHT");
  });

  it("keeps the selected highlight but stays in the base scene after a camera interrupt", () => {
    const focusing = sceneReducer(initialSceneState, { type: "focus-skill", skillId: "python", skillLabel: "Python", source: "pointer" });
    const flying = sceneReducer(focusing, { type: "advance-transition", token: focusing.transitionToken, phase: "CAMERA_FLY" });
    const interrupted = sceneReducer(flying, { type: "interrupt-focus", token: flying.transitionToken });
    expect(interrupted.mode).toBe("GLOBAL_VALUE");
    expect(interrupted.activeSkill?.skillId).toBe("python");
    expect(interrupted.relationSkill).toBeNull();
    expect(interrupted.transitionPhase).toBe("IDLE");
  });

  it("returns through line, node and camera phases before clearing relation state", () => {
    const focusing = sceneReducer(initialSceneState, { type: "focus-skill", skillId: "python", skillLabel: "Python", source: "search" });
    const morphing = sceneReducer(focusing, { type: "advance-transition", token: focusing.transitionToken, phase: "CONSTELLATION_MORPH" });
    const settled = sceneReducer(morphing, { type: "advance-transition", token: morphing.transitionToken, phase: "SETTLED" });
    const lines = sceneReducer(settled, { type: "start-return" });
    const nodes = sceneReducer(lines, { type: "advance-transition", token: lines.transitionToken, phase: "RETURN_MORPH" });
    const camera = sceneReducer(nodes, { type: "advance-transition", token: nodes.transitionToken, phase: "RETURN_CAMERA" });
    const returned = sceneReducer(camera, { type: "finish-return", token: camera.transitionToken });
    expect([lines.transitionPhase, nodes.transitionPhase, camera.transitionPhase]).toEqual(["RETURN_LINES", "RETURN_MORPH", "RETURN_CAMERA"]);
    expect(returned).toMatchObject({ mode: "GLOBAL_VALUE", activeSkill: null, relationSkill: null, transitionPhase: "IDLE" });
  });

  it("keeps role relation origin but returns the existing global action to GLOBAL_VALUE", () => {
    const role = sceneReducer(initialSceneState, { type: "select-role", role: { roleId: "devops_engineer", label: "DevOps", sampleSize: 21 } });
    const focusing = sceneReducer(role, { type: "focus-skill", skillId: "kubernetes", skillLabel: "Kubernetes", source: "search" });
    const relation = sceneReducer(focusing, { type: "advance-transition", token: focusing.transitionToken, phase: "CONSTELLATION_MORPH" });
    const returning = sceneReducer(relation, { type: "start-return" });
    expect(returning.relationOriginMode).toBe("ROLE_VALUE");
    expect(returning.returnMode).toBe("GLOBAL_VALUE");
    const morph = sceneReducer(returning, { type: "advance-transition", token: returning.transitionToken, phase: "RETURN_MORPH" });
    expect(morph.mode).toBe("GLOBAL_VALUE");
    expect(morph.activeRole).toBeNull();
  });

  it("treats a new focus during return as a fresh global generation", () => {
    const role = sceneReducer(initialSceneState, { type: "select-role", role: { roleId: "data_engineer", label: "数据工程师", sampleSize: 38 } });
    const focusing = sceneReducer(role, { type: "focus-skill", skillId: "kafka", skillLabel: "Kafka", source: "search" });
    const relation = sceneReducer(focusing, { type: "advance-transition", token: focusing.transitionToken, phase: "CONSTELLATION_MORPH" });
    const returning = sceneReducer(relation, { type: "start-return" });
    const python = sceneReducer(returning, { type: "focus-skill", skillId: "python", skillLabel: "Python", source: "search" });
    expect(python.mode).toBe("GLOBAL_VALUE");
    expect(python.activeRole).toBeNull();
    expect(python.relationOriginMode).toBe("GLOBAL_VALUE");
    expect(python.transitionPhase).toBe("HIGHLIGHT");
  });

  it("resets every exploration state to the global home generation", () => {
    const focused = sceneReducer(initialSceneState, { type: "focus-skill", skillId: "python", skillLabel: "Python", source: "search" });
    const relation = sceneReducer(focused, { type: "advance-transition", token: focused.transitionToken, phase: "CONSTELLATION_MORPH" });
    const selected = sceneReducer(relation, { type: "select-relation", skillId: "sql" });
    const home = sceneReducer(selected, { type: "reset-to-global-home" });
    expect(home).toMatchObject({ mode: "GLOBAL_VALUE", activeRole: null, activeSkill: null, relationSkill: null, selectedRelationId: null, explorationPath: [], transitionPhase: "IDLE", focusSource: null, returnMode: "GLOBAL_VALUE", relationOriginMode: "GLOBAL_VALUE" });
    expect(home.homeResetToken).toBe(initialSceneState.homeResetToken + 1);
    expect(home.transitionToken).toBeGreaterThan(selected.transitionToken);
  });
});
