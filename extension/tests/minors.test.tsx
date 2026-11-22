import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ReportApp from "../entrypoints/report/App";
import FindStep from "../entrypoints/sidepanel/steps/FindStep";
import App from "../entrypoints/sidepanel/App";
import { initialState, reduce } from "../lib/flow";
import type { Analysis, Research } from "../lib/api";
import fixture from "./fixtures/analysis.json";

const research: Research = {
  headline: "h", fetched: "2026-11-22", source: "live", notice: null,
  keywords: [{ keyword: "수제쿠키", total_qc: 100 }, { keyword: "르뱅쿠키", total_qc: 50 }],
  audience: { keyword: "수제쿠키", female: 0.8, ages: { "30": 0.4 }, top_age: "30" },
};

describe("deferred minors", () => {
  it("funnel with zero impressions draws no NaN widths", () => {
    const r = { ...(fixture as unknown as Analysis), charts: { ...(fixture as unknown as Analysis).charts, funnel: { impressions: 0, link_clicks: 0, landing_page_views: 0 } } };
    const { container } = render(<ReportApp result={r} />);
    const bars = Array.from(container.querySelectorAll<HTMLElement>("ol li div div"));
    expect(bars).toHaveLength(3);
    for (const b of bars) expect(b.style.width).toBe("0%");      // 잘못된 값이면 브라우저가 무시해 막대가 꽉 차 보인다
  });

  it("dropped keywords live in the flow state and survive a re-render", () => {
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: /르뱅쿠키/ }));
    expect(dispatch).toHaveBeenCalledWith({ type: "toggleKeyword", keyword: "르뱅쿠키" });
    const s = reduce({ ...initialState(), research }, { type: "toggleKeyword", keyword: "르뱅쿠키" });
    expect(s.dropped).toEqual(["르뱅쿠키"]);
    expect(reduce(s, { type: "toggleKeyword", keyword: "르뱅쿠키" }).dropped).toEqual([]);
  });

  it("questions step shows a loading line while fields load", async () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));   // 영영 안 끝나는 요청
    const { fakeBrowser } = await import("wxt/testing/fake-browser");
    await fakeBrowser.storage.local.set({ "coach.v3.state": { ...initialState(), step: "questions" } });
    render(<App />);
    expect(await screen.findByText("질문을 불러오는 중이에요…")).toBeTruthy();
    vi.unstubAllGlobals();
  });
});
