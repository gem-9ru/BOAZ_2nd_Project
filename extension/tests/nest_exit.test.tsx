// 광고 관리자 뭉치는 패널 둥지에서 '지금 막' 걸어 나왔을 때만 그 걸음(NEST_EXIT_MS)만큼 기다렸다가 들어온다
import { act, render, screen, waitFor } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Character } from "../entrypoints/adsmanager.content/Character";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import { NEST_EXIT_MS } from "../lib/character3d/motion";
import { initialState, reduce, type FlowState, type Plan } from "../lib/flow";
import { SETTING_ORDER } from "../lib/settings";

vi.mock("../lib/progress", () => ({
  sendWithRetry: async (send: () => Promise<unknown>) => { try { await send(); return true; } catch { return false; } },
}));

beforeEach(() => fakeBrowser.reset());
afterEach(() => vi.useRealTimers());

const left = (c: HTMLElement) => parseFloat((c.querySelector(".coach-mungchi") as HTMLElement).style.left);

describe("광고 관리자 뭉치 들어오기", () => {
  const view = { index: 0, total: 3, found: false, text: "여기" };
  it("walks in right away when it did not just leave the nest", () => {
    vi.useFakeTimers();
    const { container } = render(<Character view={view} onDone={() => {}} onBack={() => {}} onClose={() => {}} />);
    const start = left(container);
    act(() => { vi.advanceTimersByTime(300); });
    expect(left(container)).toBeLessThan(start);
  });
  it("waits while the panel shows it walking out of the nest", () => {
    vi.useFakeTimers();
    const { container } = render(<Character view={view} fromNest onDone={() => {}} onBack={() => {}} onClose={() => {}} />);
    const start = left(container);
    act(() => { vi.advanceTimersByTime(300); });
    expect(left(container)).toBe(start);
    act(() => { vi.advanceTimersByTime(NEST_EXIT_MS + 300); });
    expect(left(container)).toBeLessThan(start);
  });
});

describe("패널 → 광고 관리자: fromNest", () => {
  const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: `칸 ${id}`, value: "지난 값" }));
  const plan = { code: "AB12", change: { field_id: "meta.ad.media", label: "형식·미디어", new: "+ 세로(9:16) 1개", note: "" } } as unknown as Plan;
  const base: FlowState = reduce({ ...initialState(), step: "plan", plan, settings },
    { type: "startNextTest", fieldId: "meta.ad.media", label: "형식·미디어", value: "+ 세로(9:16) 1개" });

  async function opened(away: boolean) {
    const send = vi.spyOn(fakeBrowser.tabs, "sendMessage").mockResolvedValue(true as never);
    vi.spyOn(fakeBrowser.tabs, "query").mockResolvedValue([{ id: 7, active: true, url: "https://adsmanager.facebook.com/x" }] as never);
    const state = { ...base, guide: { ...base.guide!, away } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    screen.getByRole("button", { name: away ? "어시스턴트 다시 부르기" : "광고 관리자 열기" }).click();
    await waitFor(() => expect(send).toHaveBeenCalled());
    return (send.mock.calls[0]![1] as { fromNest?: boolean }).fromNest;
  }
  it("says fromNest only when 뭉치 was at home", async () => {
    expect(await opened(false)).toBe(true);
  });
  it("does not when 뭉치 was already out on Ads Manager", async () => {
    expect(await opened(true)).toBeUndefined();
  });
});
