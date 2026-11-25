import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import FindStep from "../entrypoints/sidepanel/steps/FindStep";
import App from "../entrypoints/sidepanel/App";
import { initialState, reduce } from "../lib/flow";
import type { Research } from "../lib/api";

const research: Research = {
  headline: "h", fetched: "2026-11-22", source: "live", notice: null,
  keywords: [{ keyword: "수제쿠키", total_qc: 100 }, { keyword: "르뱅쿠키", total_qc: 50 }],
  audience: { keyword: "수제쿠키", female: 0.8, ages: { "30": 0.4 }, top_age: "30" },
};

describe("deferred minors", () => {
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
