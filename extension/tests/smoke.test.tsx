import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../entrypoints/sidepanel/App";

describe("side panel", () => {
  it("shows the 광고 코치 title", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "광고 코치" })).toBeTruthy();
  });
});
