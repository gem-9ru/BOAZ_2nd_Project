import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import App from "../entrypoints/sidepanel/App";

describe("side panel", () => {
  it("shows the Ad assistant title", () => {
    render(<App />);
    expect(screen.getByRole("heading", { name: "Ad assistant" })).toBeTruthy();
  });
});
