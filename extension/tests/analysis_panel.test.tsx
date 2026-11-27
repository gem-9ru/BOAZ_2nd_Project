// v4.2 AN-COM ④: 분석 페이지는 크롬 탭, 광고 어시스턴트는 그 옆 사이드 패널(이 확장)
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import AnalysisAssistant from "../entrypoints/sidepanel/steps/AnalysisAssistant";
import { nextMoney } from "../entrypoints/sidepanel/steps/PlanStep";
import { parseAnalysisUrl } from "../lib/analysisTab";

const ok = (b: unknown) => Promise.resolve(new Response(JSON.stringify(b), { status: 200 }));
beforeEach(() => fakeBrowser.reset());
afterEach(() => vi.unstubAllGlobals());

describe("분석 페이지 주소 읽기", () => {
  it("reads code and step after # only on the analysis page", () => {
    expect(parseAnalysisUrl("http://localhost:8000/analysis#s=K&code=AB12&step=AN-02")).toEqual({ code: "AB12", step: "AN-02", send: null, budget: null, days: null });
    expect(parseAnalysisUrl("http://localhost:8000/analysis")).toEqual({ code: null, step: null, send: null, budget: null, days: null });
    // 공개 주소 ad-report.gem-9ru.com (분석 페이지 전용 주소, 2026-11-26)
    expect(parseAnalysisUrl("https://ad-report.gem-9ru.com/analysis#code=AB12&step=AN-01")).toEqual({ code: "AB12", step: "AN-01", send: null, budget: null, days: null });
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=AB12&step=AN-06&send=17")!.send).toBe("17");
    expect(parseAnalysisUrl("https://adsmanager.facebook.com/adsmanager#code=AB12")).toBeNull();
    // ③에서 고른 세트당 예산: 숫자·범위(1천 원~1천만 원)만 받는다
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=AB12&step=AN-06&send=17&budget=10000")!.budget).toBe(10000);
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=AB12&budget=12.5")!.budget).toBeNull();
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=AB12&budget=99999999999")!.budget).toBeNull();
    // ③에서 고른 기간: 1~30일 정수만
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=AB12&step=AN-06&send=17&days=7")!.days).toBe(7);
    for (const bad of ["0", "31", "1.5", "99", "x"]) expect(parseAnalysisUrl(`http://localhost:8000/analysis#code=AB12&days=${bad}`)!.days).toBeNull();
    expect(parseAnalysisUrl("http://localhost:8000/analysis#code=<x>&step=AN-09")).toEqual({ code: null, step: null, send: null, budget: null, days: null });
  });
});

describe("분석 페이지 옆 광고 어시스턴트", () => {
  it("before upload (AN-00) it greets and explains the export without calling the server", () => {
    const f = vi.fn(); vi.stubGlobal("fetch", f);
    const { rerender } = render(<AnalysisAssistant tab={{ tabId: 1, code: null, step: null, send: null }} dispatch={() => {}} flowStep="wait" />);
    expect(screen.getByText(/결과 파일\(CSV\)을 올리고 \[분석 시작 ▶\]을 눌러요/)).toBeTruthy();   // 할 일 한 줄
    expect(screen.getByRole("button", { name: /광고 관리자에서 내보내기 짚어 주기/ })).toBeTruthy();
    // 광고를 만들기 전(① 찾기)에는 내보내기 안내를 띄우지 않는다 (찾기 화면과 겹치지 않게)
    rerender(<AnalysisAssistant tab={{ tabId: 1, code: null, step: null, send: null }} dispatch={() => {}} flowStep="find" />);
    expect(screen.queryByRole("button", { name: /내보내기 짚어 주기/ })).toBeNull();
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
    expect(screen.getByText(/\[이 테스트 준비하기 →\]를 눌러요/)).toBeTruthy();   // 지금 왼쪽에서 누를 것
    rerender(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-02", send: null }} dispatch={() => {}} />);
    expect(await screen.findByText("AN-02 요약")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "질문 하나" }));
    expect(await screen.findByText("답: 질문 하나")).toBeTruthy();
    expect(JSON.parse((f.mock.calls.at(-1)![1] as RequestInit).body as string)).toMatchObject({ code: "AB12", step: "AN-02", question: "질문 하나" });
  });

  it("AN-06 [확장 프로그램으로 보내기] (send in the address) loads the test plan for EX-03", async () => {
    const plan = { code: "AB12", action: "한 번 더", change: { field_id: "meta.ad.media", label: "형식·미디어", new: "세로", note: "n", path: "광고 › 형식·미디어" }, summary: [], badge: null };
    let give!: () => void;
    const planReady = new Promise<void>((r) => { give = r; });
    vi.stubGlobal("fetch", vi.fn((u: string) => String(u).includes("/plan/") ? planReady.then(() => ok(plan)) : ok({ message: "AN-06 요약", suggestions: [] })));
    const dispatch = vi.fn();
    const tab = { tabId: 1, code: "AB12", step: "AN-06", send: "123" };
    const { rerender } = render(<AnalysisAssistant tab={tab} dispatch={dispatch} />);
    // 받는 동안: 방금 누른 [보내기]를 또 누르라고 하지 않는다
    expect(screen.getByText(/받는 중이에요/)).toBeTruthy();
    expect(screen.queryByText(/\[확장 프로그램으로 보내기 →\]를 눌러요/)).toBeNull();
    give();
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "planLoaded", plan, sent: "123" }));
    // 받은 뒤(App이 planSent·plan을 넘김): '받았어요' 카드 + 광고 관리자로 가는 버튼 하나
    const update = vi.spyOn(fakeBrowser.tabs, "update").mockResolvedValue({} as never);
    vi.spyOn(fakeBrowser.windows, "update").mockResolvedValue({} as never);
    // 지금 창의 광고 관리자 탭(7)을 다른 창의 탭(8)보다 먼저 (사이드 패널은 창마다 따로)
    const ads = "https://adsmanager.facebook.com/adsmanager/manage/campaigns";
    vi.spyOn(fakeBrowser.tabs, "query").mockImplementation((async (q: { currentWindow?: boolean }) =>
      q.currentWindow ? [{ id: 7, windowId: 1, url: ads }] : [{ id: 8, windowId: 2, url: ads }, { id: 7, windowId: 1, url: ads }]) as never);
    rerender(<AnalysisAssistant tab={tab} dispatch={dispatch} handled="123" plan={plan as never} />);
    const card = screen.getByRole("region", { name: "받은 바꿀 칸" });
    expect(card.textContent).toContain("광고 › 형식·미디어");
    fireEvent.click(screen.getByRole("button", { name: "광고 관리자에서 다음 테스트 준비 ▶" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith(7, { active: true }));
  });

  it("when the plan cannot be fetched it says how to retry and gives the code fallback", async () => {
    vi.stubGlobal("fetch", vi.fn((u: string) => String(u).includes("/plan/")
      ? Promise.resolve(new Response(JSON.stringify({ detail: "서버가 잠깐 쉬어요" }), { status: 500 }))
      : ok({ message: "m", suggestions: [] })));
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "9" }} dispatch={() => {}} />);
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeTruthy();
    expect(screen.getByText(/코드 4자리로 넣기/).textContent).toContain("AB12");
  });

  it("the budget picked on ③ (budget in the address) replaces the plan's per-set amount", async () => {
    const plan = { code: "AB12", action: "한 번 더", change: { field_id: "meta.ad.media", label: "형식·미디어", new: "세로", note: "n", path: "광고 › 형식·미디어", per_set: 6000 }, summary: [], badge: null };
    vi.stubGlobal("fetch", vi.fn((u: string) => ok(String(u).includes("/plan/") ? plan : { message: "m", suggestions: [] })));
    const dispatch = vi.fn();
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "124", budget: 10000 }} dispatch={dispatch} />);
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "planLoaded", plan: { ...plan, change: { ...plan.change, per_set: 10000, picked: true } }, sent: "124" }));
  });

  it("the period picked on ③ (days in the address) replaces the plan's days, and the card shows amount · days", async () => {
    const plan = { code: "AB12", action: "한 번 더", change: { field_id: "meta.ad.media", label: "형식·미디어", new: "세로", note: "n", path: "광고 › 형식·미디어", per_set: 6000, days: 4 }, summary: [], badge: null };
    vi.stubGlobal("fetch", vi.fn((u: string) => ok(String(u).includes("/plan/") ? plan : { message: "m", suggestions: [] })));
    const dispatch = vi.fn();
    const tab = { tabId: 1, code: "AB12", step: "AN-06", send: "125", budget: 10000, days: 7 };
    const { rerender } = render(<AnalysisAssistant tab={tab} dispatch={dispatch} />);
    const got = { ...plan, change: { ...plan.change, per_set: 10000, picked: true, days: 7 } };
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "planLoaded", plan: got, sent: "125" }));
    rerender(<AnalysisAssistant tab={tab} dispatch={dispatch} handled="125" plan={got as never} />);
    expect(screen.getByRole("region", { name: "받은 바꿀 칸" }).textContent).toContain("세트당 10,000원 · 7일");
  });

  it("the card shows the same amount as the next screen: raised to Meta's daily minimum × days", async () => {
    const plan = { code: "AB12", action: "한 번 더", change: { field_id: "meta.ad.media", label: "형식·미디어", new: "세로", note: "n", per_set: 3000, days: 7 }, summary: [], badge: null };
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: [] })));
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "1" }} dispatch={() => {}} handled="1" plan={plan as never} />);
    // 3,000원 · 7일은 하루 최소(1,336원 × 7일 = 9,400원)보다 적다 → 다음 화면처럼 9,400원
    expect(screen.getByRole("region", { name: "받은 바꿀 칸" }).textContent).toContain("세트당 9,400원 · 7일");
  });

  it("a budget test (underspent ad): the amount the owner sent wins over the server's 'need more' amount", async () => {
    const plan = { code: "AB12", action: "a", change: { field_id: "meta.adset.daily_budget", label: "예산", new: "넉넉하게", note: "n", per_set: 6000, days: 4 },
      watch: [{ field_id: "meta.adset.daily_budget", path: "광고 세트 › 예산", text: "더 모아야", need_per_set: 82000 }], summary: [], badge: null };
    vi.stubGlobal("fetch", vi.fn((u: string) => ok(String(u).includes("/plan/") ? plan : { message: "m", suggestions: [] })));
    const dispatch = vi.fn();
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "5", budget: 6000 }} dispatch={dispatch} />);
    await waitFor(() => expect(dispatch).toHaveBeenCalled());
    const got = dispatch.mock.calls[0]![0].plan;
    expect(nextMoney(got, []).amount).toBe(6000);           // 사장님이 보낸 6,000원 (82,000원이 아니라)
    expect(nextMoney({ ...plan } as never, []).amount).toBe(82000);   // 코드로 넣어 고른 금액이 없으면 '더 모아야 할 금액'
  });

  it("when the assistant cannot be reached on ①, the to-do line names no button (it may be blocked)", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("{}", { status: 500 }))));
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-01", send: null }} dispatch={() => {}} />);
    expect(await screen.findByText("왼쪽 결론 화면의 안내를 따라 주세요.", { exact: false })).toBeTruthy();
    expect(screen.queryByText(/\[이 테스트 준비하기 →\]/)).toBeNull();
  });

  it("[광고 관리자에서 다음 테스트 준비] reuses an Ads Manager tab that fell onto the login page", async () => {
    const plan = { code: "AB12", action: "a", change: { field_id: "meta.ad.media", label: "l", new: "n", note: "n" }, summary: [], badge: null };
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: [] })));
    const update = vi.spyOn(fakeBrowser.tabs, "update").mockResolvedValue({} as never);
    const create = vi.spyOn(fakeBrowser.tabs, "create").mockResolvedValue({} as never);
    vi.spyOn(fakeBrowser.windows, "update").mockResolvedValue({} as never);
    vi.spyOn(fakeBrowser.tabs, "query").mockResolvedValue([{ id: 4, windowId: 1, url: "https://www.facebook.com/login/?next=adsmanager" }] as never);
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "1" }} dispatch={() => {}} handled="1" plan={plan as never} />);
    fireEvent.click(screen.getByRole("button", { name: "광고 관리자에서 다음 테스트 준비 ▶" }));
    await waitFor(() => expect(update).toHaveBeenCalledWith(4, { active: true }));
    expect(create).not.toHaveBeenCalled();
  });

  it("when the server lost the result (restarted), it says to upload again instead of retry / code", async () => {
    vi.stubGlobal("fetch", vi.fn((u: string) => String(u).includes("/plan/")
      ? Promise.resolve(new Response(JSON.stringify({ detail: "코드를 찾지 못했어요." }), { status: 404 }))
      : ok({ message: "m", suggestions: [] })));
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "9" }} dispatch={() => {}} />);
    expect((await screen.findByRole("alert")).textContent).toContain("파일을 다시 올리고 보내 주세요");
    expect(screen.queryByRole("button", { name: "다시 시도" })).toBeNull();
    expect(screen.queryByText(/코드 4자리로 넣기/)).toBeNull();
  });

  it("sending twice quickly: a late answer for the first send does not overwrite the second", async () => {
    const plan = (per_set: number) => ({ code: "AB12", action: "a", change: { field_id: "meta.ad.media", label: "l", new: "n", note: "n", per_set }, summary: [], badge: null });
    const waits: ((r: Response) => void)[] = [];
    vi.stubGlobal("fetch", vi.fn((u: string) => String(u).includes("/plan/") ? new Promise<Response>((r) => waits.push(r)) : ok({ message: "m", suggestions: [] })));
    const dispatch = vi.fn();
    const { rerender } = render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "1", budget: 6000 }} dispatch={dispatch} />);
    rerender(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "2", budget: 10000 }} dispatch={dispatch} />);
    await waitFor(() => expect(waits).toHaveLength(2));
    waits[1]!(new Response(JSON.stringify(plan(6000)), { status: 200 }));   // 두 번째 답 먼저
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ type: "planLoaded", sent: "2" })));
    waits[0]!(new Response(JSON.stringify(plan(6000)), { status: 200 }));   // 첫 번째 답이 늦게 옴 → 버린다
    await new Promise((r) => setTimeout(r, 20));
    expect(dispatch).toHaveBeenCalledTimes(1);
    expect(dispatch.mock.calls[0]![0].plan.change.per_set).toBe(10000);
  });
});

describe("사이드 패널이 지금 탭을 따라간다", () => {
  it("App passes the flow step: the export button shows while waiting, not on the result screen", async () => {
    const { default: App } = await import("../entrypoints/sidepanel/App");
    const { STATE_KEY } = await import("../lib/storage");
    const { initialState } = await import("../lib/flow");
    vi.spyOn(fakeBrowser.tabs, "query").mockResolvedValue([{ id: 9, active: true, url: "http://localhost:8000/analysis" }] as never);
    await fakeBrowser.storage.local.set({ [STATE_KEY]: { ...initialState(), step: "wait", endDate: "2020-01-01" } });
    const { unmount } = render(<App />);
    expect(await screen.findByRole("button", { name: /광고 관리자에서 내보내기 짚어 주기/ })).toBeTruthy();
    unmount();
    await fakeBrowser.storage.local.set({ [STATE_KEY]: { ...initialState(), step: "plan" } });
    render(<App />);
    expect(await screen.findByText(/\[분석 시작 ▶\]을 눌러요/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /내보내기 짚어 주기/ })).toBeNull();
  });

  it("when the active tab is the analysis page, the panel becomes its assistant (③ 분석)", async () => {
    const { default: App } = await import("../entrypoints/sidepanel/App");
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "AN-03 요약", suggestions: [] })));
    vi.spyOn(fakeBrowser.tabs, "query").mockResolvedValue([{ id: 9, active: true, url: "http://localhost:8000/analysis#code=AB12&step=AN-03" }] as never);
    // 광고를 켠 뒤(wait)라야 머리 단계가 ③ (광고 전에는 분석 탭이어도 그 단계 그대로, 재검토 B11)
    const { STATE_KEY } = await import("../lib/storage");
    const { initialState } = await import("../lib/flow");
    await fakeBrowser.storage.local.set({ [STATE_KEY]: { ...initialState(), step: "wait" } });
    render(<App />);
    expect(await screen.findByRole("region", { name: "분석 페이지 어시스턴트" })).toBeTruthy();
    expect(await screen.findByText("AN-03 요약")).toBeTruthy();
    await waitFor(() => expect(screen.getByText(/③ 분석/).getAttribute("aria-current")).toBe("step"));
  });
});
