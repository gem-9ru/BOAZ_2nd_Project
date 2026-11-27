import { render, screen, within } from "@testing-library/react";
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
    const items = within(screen.getAllByRole("list")[0]!).getAllByRole("listitem");   // 칸 목록만 (아래 '다른 할 일' 카드 빼고)
    expect(items).toHaveLength(18);
    expect(items[2]!.getAttribute("aria-current")).toBe("step");
    expect(screen.getByRole("button", { name: "광고 관리자 열기" })).toBeTruthy();
  });
});

describe("WaitStep", () => {
  it("after guideDone shows the come-back date from endDate", () => {
    render(<WaitStep state={{ ...initialState(), step: "wait", endDate: "2026-12-06" }} dispatch={() => {}} />);
    expect(screen.getByText(/12월 7일에 결과를 보러 오세요/)).toBeTruthy();   // 날짜는 '12월 7일' 모양으로 (2026-12-07 아님)
    expect(screen.queryByText(/2026-12-07/)).toBeNull();
    expect(screen.getByText(/이 패널을 다시 열면/)).toBeTruthy();   // 알림이 따로 안 가니 어디로 오는지 말한다
    expect(screen.getByRole("button", { name: "결과 분석하기" })).toBeTruthy();
    expect(screen.queryByText(/에 시작해요/)).toBeNull();
  });

  it("a start date in the future is said in one line", () => {
    render(<WaitStep state={{ ...initialState(), step: "wait", startDate: "2099-12-01", endDate: "2099-12-14" }} dispatch={() => {}} />);
    expect(screen.getByText(/광고는 12월 1일에 시작해요/)).toBeTruthy();
  });
});
