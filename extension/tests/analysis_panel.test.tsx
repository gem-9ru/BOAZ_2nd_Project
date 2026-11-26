// v4.2 AN-COM ④: 분석 페이지는 크롬 탭, 광고 어시스턴트는 그 옆 사이드 패널(이 확장)
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AnalysisAssistant from "../entrypoints/sidepanel/steps/AnalysisAssistant";
import { parseAnalysisUrl } from "../lib/analysisTab";

const ok = (b: unknown) => Promise.resolve(new Response(JSON.stringify(b), { status: 200 }));
beforeEach(() => fakeBrowser.reset());
afterEach(() => vi.unstubAllGlobals());

describe("분석 페이지 주소 읽기", () => {
  it("reads code and step after # only on the analysis page", () => {
    expect(parseAnalysisUrl("http://localhost:8000/analysis#s=K&code=AB12&step=AN-02")).toEqual({ code: "AB12", step: "AN-02", send: null, budget: null });
    expect(parseAnalysisUrl("http://localhost:8000/analysis")).toEqual({ code: null, step: null, send: null, budget: null });
    // 공개 주소 ad-report.gem-9ru.com (분석 페이지 전용 주소, 2026-11-26)
    expect(parseAnalysisUrl("https://ad-report.gem-9ru.com/analysis#code=AB12&step=AN-01")).toEqual({ code: "AB12", step: "AN-01", send: null, budget: null });
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=AB12&step=AN-06&send=17")!.send).toBe("17");
    expect(parseAnalysisUrl("https://adsmanager.facebook.com/adsmanager#code=AB12")).toBeNull();
    // ③에서 고른 세트당 예산: 숫자·범위(1천 원~1천만 원)만 받는다
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=AB12&step=AN-06&send=17&budget=10000")!.budget).toBe(10000);
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=AB12&budget=12.5")!.budget).toBeNull();
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=AB12&budget=99999999999")!.budget).toBeNull();
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=<x>&step=AN-09")).toEqual({ code: null, step: null, send: null, budget: null });
  });
});

describe("분석 페이지 옆 광고 어시스턴트", () => {
  it("before upload (AN-00) it greets and explains the export without calling the server", () => {
    const f = vi.fn(); vi.stubGlobal("fetch", f);
    render(<AnalysisAssistant tab={{ tabId: 1, code: null, step: null, send: null }} dispatch={() => {}} />);
    expect(screen.getByText(/돌려 본 광고 결과를 올려 주시면/)).toBeTruthy();
    expect(screen.getByText("CSV는 어디서 받아요?")).toBeTruthy();
    expect(f).not.toHaveBeenCalled();
  });

  it("for each step: the alert bubble first, then the step summary and two suggestions; it follows step changes", async () => {
    const f = vi.fn((_u: string, init?: RequestInit) => {
      const b = JSON.parse(init!.body as string);
      if (b.question) return ok({ message: `답: ${b.question}` });
      return ok({ message: `${b.step} 요약`, suggestions: ["질문 하나", "질문 둘"],
        alerts: b.step === "AN-01" ? [{ level: "warn", text: "11/17 안 보여졌어요", todo: "시작 시간을 하루 여유 있게" }] : [] });
    });
    vi.stubGlobal("fetch", f);
    const { rerender } = render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-01", send: null }} dispatch={() => {}} />);
    expect(await screen.findByText("AN-01 요약")).toBeTruthy();
    const log = screen.getByText("AN-01 요약").parentElement!;
    expect(log.children[0]!.textContent).toContain("11/17 안 보여졌어요");   // 알림 말풍선이 먼저
    expect(screen.getByText(/분석 페이지 · ① 결론/)).toBeTruthy();
    rerender(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-02", send: null }} dispatch={() => {}} />);
    expect(await screen.findByText("AN-02 요약")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "질문 하나" }));
    expect(await screen.findByText("답: 질문 하나")).toBeTruthy();
    expect(JSON.parse((f.mock.calls.at(-1)![1] as RequestInit).body as string)).toMatchObject({ code: "AB12", step: "AN-02", question: "질문 하나" });
  });

  it("AN-06 [확장 프로그램으로 보내기] (send in the address) loads the test plan for EX-03", async () => {
    const plan = { code: "AB12", action: "한 번 더", change: { field_id: "meta.ad.media", label: "형식·미디어", new: "세로", note: "n", path: "광고 › 형식·미디어" }, summary: [], badge: null };
    vi.stubGlobal("fetch", vi.fn((u: string) => ok(String(u).includes("/plan/") ? plan : { message: "AN-06 요약", suggestions: [] })));
    const dispatch = vi.fn();
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "123" }} dispatch={dispatch} />);
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "planLoaded", plan }));
    const said = await screen.findByText(/테스트안을 받았어요 \(광고 › 형식·미디어\)/);
    // 탭만 바꿔서는 뭉치가 나오지 않는다 → 패널의 [다음 테스트 세팅]을 누르라고 말한다
    expect(said.textContent).toContain("[다음 테스트 세팅]");
    expect(said.textContent).not.toContain("광고 관리자로 가면");
  });

  it("the budget picked on ③ (budget in the address) replaces the plan's per-set amount", async () => {
    const plan = { code: "AB12", action: "한 번 더", change: { field_id: "meta.ad.media", label: "형식·미디어", new: "세로", note: "n", path: "광고 › 형식·미디어", per_set: 6000 }, summary: [], badge: null };
    vi.stubGlobal("fetch", vi.fn((u: string) => ok(String(u).includes("/plan/") ? plan : { message: "m", suggestions: [] })));
    const dispatch = vi.fn();
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "124", budget: 10000 }} dispatch={dispatch} />);
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "planLoaded", plan: { ...plan, change: { ...plan.change, per_set: 10000 } } }));
  });
});

describe("사이드 패널이 지금 탭을 따라간다", () => {
  it("when the active tab is the analysis page, the panel becomes its assistant (③ 분석)", async () => {
    const { default: App } = await import("../entrypoints/sidepanel/App");
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "AN-03 요약", suggestions: [] })));
    vi.spyOn(fakeBrowser.tabs, "query").mockResolvedValue([{ id: 9, active: true, url: "http://localhost:8000/analysis#code=AB12&step=AN-03" }] as never);
    render(<App />);
    expect(await screen.findByRole("region", { name: "분석 페이지 어시스턴트" })).toBeTruthy();
    expect(await screen.findByText("AN-03 요약")).toBeTruthy();
    expect(screen.getByText(/③ 분석/).getAttribute("aria-current")).toBe("step");
  });
});
