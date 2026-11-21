import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import WaitStep from "../entrypoints/sidepanel/steps/WaitStep";
import { initialState, type FlowState } from "../lib/flow";
import { SETTING_ORDER } from "../lib/settings";

const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: `칸 ${id}`, value: "v" }));

describe("GuideStep", () => {
  it("lists every step with the current one marked", () => {
    const state: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: 2 } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(14);
    expect(items[2]!.getAttribute("aria-current")).toBe("step");
    expect(screen.getByRole("button", { name: "광고 관리자 열기" })).toBeTruthy();
  });
});

describe("WaitStep", () => {
  it("after guideDone shows the come-back date from endDate", () => {
    render(<WaitStep state={{ ...initialState(), step: "wait", endDate: "2026-12-06" }} dispatch={() => {}} />);
    expect(screen.getByText(/2026-12-07에 결과를 보러 오세요/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "결과 파일 올리기" })).toBeTruthy();
  });
});
