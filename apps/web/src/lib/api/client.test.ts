import { describe, expect, it } from "vitest";
import { marketQuery } from "./client";

describe("marketQuery", () => {
  it("serializes only active FastAPI filters", () => {
    expect(marketQuery({ role_id: "data_analyst", city_code: "shanghai", published_from: "2026-01-01" })).toBe("?role_id=data_analyst&city_code=shanghai&published_from=2026-01-01");
  });

  it("keeps repeated source filters and omits blanks", () => {
    expect(marketQuery({ source_id: ["public_a", "manual_b"], city_code: "" })).toBe("?source_id=public_a&source_id=manual_b");
  });
});
