import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState, ErrorState, LowConfidenceBanner } from "./data-states";

describe("data states", () => {
  it("renders honest empty and low confidence messaging", () => {
    render(<><EmptyState title="暂无趋势" /><LowConfidenceBanner reasons={["样本太少", "来源太少"]} /></>);
    expect(screen.getByText("暂无趋势")).toBeInTheDocument();
    expect(screen.getByText(/样本太少；来源太少/)).toBeInTheDocument();
  });

  it("renders API errors without a stack", () => {
    render(<ErrorState message="FastAPI unavailable" />);
    expect(screen.getByText("FastAPI unavailable")).toBeInTheDocument();
  });
});
