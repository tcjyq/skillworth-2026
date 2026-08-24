import { describe, expect, it } from "vitest";
import { money, percent, roleName, signedPercent } from "./format";

describe("formatters", () => {
  it("does not invent missing values", () => {
    expect(percent(null)).toBe("—");
    expect(money(undefined)).toBe("—");
  });

  it("formats actual decimal metrics", () => {
    expect(percent(.125)).toBe("12.5%");
    expect(signedPercent(-.08)).toBe("-8.0%");
    expect(roleName("data_analyst")).toBe("数据分析师");
  });
});
