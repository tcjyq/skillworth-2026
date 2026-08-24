import { describe, expect, it } from "vitest";
import { paretoFrontier } from "./pareto";

describe("paretoFrontier", () => {
  it("keeps only skills not dominated by lower effort and higher signal", () => {
    const result = paretoFrontier([
      { skill_id: "sql", learning_hours_expected: 100, market_signal: 36 },
      { skill_id: "python", learning_hours_expected: 160, market_signal: 48 },
      { skill_id: "java", learning_hours_expected: 220, market_signal: 28 },
      { skill_id: "git", learning_hours_expected: 55, market_signal: 24 },
    ]);

    expect(result.map((item) => item.skill_id)).toEqual(["git", "sql", "python"]);
  });

  it("keeps equal-effort points only when their signal is maximal", () => {
    const result = paretoFrontier([
      { skill_id: "a", learning_hours_expected: 100, market_signal: 20 },
      { skill_id: "b", learning_hours_expected: 100, market_signal: 30 },
    ]);

    expect(result.map((item) => item.skill_id)).toEqual(["b"]);
  });
});
