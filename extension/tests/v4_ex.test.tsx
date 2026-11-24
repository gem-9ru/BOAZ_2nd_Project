// v4 회의(2026-11-25) 5-1장: 확장 EX-01 ② 세팅 · EX-02 ③ 분석 탭 · EX-03 바꿀 칸 받기
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import CodeStep from "../entrypoints/sidepanel/steps/CodeStep";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import PlanStep from "../entrypoints/sidepanel/steps/PlanStep";
import { initialState, type FlowState, type Plan } from "../lib/flow";
import type { GuideStepItem } from "../lib/guide";
import { SETTING_ORDER } from "../lib/settings";

// 첫 메시지 재시도(1.5초 × 6번)를 기다리지 않게 한 번만 보낸다
vi.mock("../lib/progress", () => ({
  sendWithRetry: async (send: () => Promise<unknown>) => { try { await send(); return true; } catch { return false; } },
}));

const ok = (b: unknown) => Promise.resolve(new Response(JSON.stringify(b), { status: 200 }));
const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: `칸 ${id}`, value: "v" }));

beforeEach(() => fakeBrowser.reset());
afterEach(() => vi.unstubAllGlobals());

function item(id: string): GuideStepItem {
  return { entry: { id, find: [{ aria: `없는 ${id}` }], done: "manual", fallback: { text: id, image: "guide/x.png" } }, value: "" } as unknown as GuideStepItem;
}

describe("EX-01 ② 세팅", () => {
  it("the character can go back one field", () => {
    document.documentElement.lang = "ko";
    const seen: number[] = [];
    const g = new Guide(document, [item("a"), item("b"), item("c")], 0, (i) => seen.push(i), 0);
    g.markDone(); g.markDone();
    expect(g.view().index).toBe(2);
    g.back();
    expect(g.view().index).toBe(1);
    expect(seen.at(-1)).toBe(1);
    g.back(); g.back();
    expect(g.view().index).toBe(0);
  });

  it("panel shows progress like 8/14 with a bar", () => {
    const state: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: 7 } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    expect(screen.getByText("8 / 14")).toBeTruthy();
    const bar = screen.getByRole("progressbar");
    expect(bar.getAttribute("aria-valuenow")).toBe("7");
    expect(bar.getAttribute("aria-valuemax")).toBe("14");
  });

  it("panel has [이전 칸] [다음 칸] that move the character on the Ads Manager tab", async () => {
    const tab = await fakeBrowser.tabs.create({ url: "https://adsmanager.facebook.com/adsmanager/manage" });
    const send = vi.spyOn(fakeBrowser.tabs, "sendMessage").mockResolvedValue(undefined);
    const state: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: 3 } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "다음 칸" }));
    await waitFor(() => expect(send).toHaveBeenCalledWith(tab.id, { type: "guide:move", delta: 1 }));
    fireEvent.click(screen.getByRole("button", { name: "이전 칸" }));
    await waitFor(() => expect(send).toHaveBeenCalledWith(tab.id, { type: "guide:move", delta: -1 }));
  });

  it("when the character can't be called it is a ▲ warning, not an error", async () => {
    vi.spyOn(fakeBrowser.tabs, "sendMessage").mockRejectedValue(new Error("no receiver"));
    const state: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0 } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "광고 관리자 열기" }));
    const w = await screen.findByRole("status");
    expect(w.textContent).toContain("▲");
    expect(w.textContent).toContain("캐릭터를 부르지 못했어요");
  });
});

describe("EX-02 ③ 분석 탭", () => {
  it("tells the export setting (일 · 노출 위치), points at 내보내기, and opens the page in a new window", async () => {
    const dispatch = vi.fn();
    const create = vi.spyOn(fakeBrowser.tabs, "create");
    render(<CodeStep state={{ ...initialState(), step: "upload" }} dispatch={dispatch} />);
    expect(screen.getAllByText(/일 · 노출 위치/).length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("button", { name: "내보내기 버튼 짚어 주기" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "startExport" });
    fireEvent.click(screen.getByRole("button", { name: "분석 페이지 열기 (새 창)" }));
    await waitFor(() => expect(create).toHaveBeenCalled());
  });
});

describe("5단계: 세팅값을 분석 페이지로 (값은 URL에 넣지 않고 키만)", () => {
  it("opening the analysis page first leaves this ad's settings on the server and passes only the key", async () => {
    const f = vi.fn((_u: string, _i?: RequestInit) => ok({ key: "K3yK3yK3yK3yK3y", count: 2 }));
    vi.stubGlobal("fetch", f);
    const create = vi.spyOn(fakeBrowser.tabs, "create");
    const state: FlowState = { ...initialState(), step: "upload", settings: [
      { fieldId: "meta.adset.end_date", label: "종료 날짜", value: "2026-11-20" },
      { fieldId: "meta.ad.website_url", label: "웹사이트 URL", value: "https://shop.example/a" },
      { fieldId: "meta.pre.fb_page", label: "페이지", value: "" },
    ] };
    render(<CodeStep state={state} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "분석 페이지 열기 (새 창)" }));
    await waitFor(() => expect(create).toHaveBeenCalled());
    const body = JSON.parse((f.mock.calls[0]![1] as RequestInit).body as string);
    expect(String(f.mock.calls[0]![0])).toMatch(/\/settings$/);
    expect(body.settings).toEqual({ "meta.adset.end_date": "2026-11-20", "meta.ad.website_url": "https://shop.example/a" });
    const url = (create.mock.calls[0]![0] as { url: string }).url;
    expect(url).toBe("http://localhost:8000/analysis#s=K3yK3yK3yK3yK3y");
    expect(url).not.toContain("shop.example");
  });

  it("if the server can't keep them, the page still opens (5문항으로 대신)", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new TypeError("down"))));
    const create = vi.spyOn(fakeBrowser.tabs, "create");
    const state: FlowState = { ...initialState(), step: "upload", settings: [{ fieldId: "meta.adset.end_date", label: "종료 날짜", value: "2026-11-20" }] };
    render(<CodeStep state={state} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "분석 페이지 열기 (새 창)" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ url: "http://localhost:8000/analysis" }));
  });
});

const plan: Plan = {
  code: "AB12", action: "한 번 더",
  change: { field_id: "meta.ad.media", label: "형식·미디어", new: "릴스용 세로(9:16) 소재 추가", note: "돈의 72%가 릴스에",
    path: "광고 › 형식·미디어", certainty: { level: "유력", label: "유력", why: "실측" }, checklist: ["다음 테스트는 이 칸 1개만"] },
  summary: ["a", "b", "c"], badge: { word: "B 쪽이에요", prob: 0.79 },
  keep: [{ field_id: "meta.adset.placements", path: "광고 세트 › 노출 위치", value: "수동 · 피드만", reason: "CPM 15% 저렴" }],
  dont: ["여러 칸을 한 번에 바꾸지 않기 — 이유"],
};

describe("EX-03 바꿀 칸 받기", () => {
  it("pins the change card with path, certainty, keep (유지) and checklist", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "첫 말", suggestions: ["q1", "q2"] })));
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    const card = screen.getByRole("region", { name: "바꿀 칸" });
    expect(within(card).getByText("광고 › 형식·미디어")).toBeTruthy();
    expect(within(card).getByText("유력")).toBeTruthy();
    expect(screen.getByText(/유지/)).toBeTruthy();
    expect(screen.getByText(/수동 · 피드만/)).toBeTruthy();
    expect(screen.getByText("다음 테스트는 이 칸 1개만")).toBeTruthy();
  });

  it("the chatbot greets from the server and answers a suggested question", async () => {
    const f = vi.fn((_u: string, init?: RequestInit) => {
      const b = JSON.parse(init!.body as string);
      return ok(b.question ? { message: `답: ${b.question}` } : { message: "이 칸만 짚어 드릴게요", suggestions: ["왜 이 칸이에요?", "언제 다시 봐요?"] });
    });
    vi.stubGlobal("fetch", f);
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    expect(await screen.findByText("이 칸만 짚어 드릴게요")).toBeTruthy();
    expect(JSON.parse((f.mock.calls[0]![1] as RequestInit).body as string)).toMatchObject({ code: "AB12", step: "EX-03" });
    fireEvent.click(screen.getByRole("button", { name: "왜 이 칸이에요?" }));
    expect(await screen.findByText("답: 왜 이 칸이에요?")).toBeTruthy();
  });

  it("[다음 테스트 세팅] goes back to EX-01 after fixing", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: [] })));
    const dispatch = vi.fn();
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "바꾸러 가기" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "startFix" });
  });
});
