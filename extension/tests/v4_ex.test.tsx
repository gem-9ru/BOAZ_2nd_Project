// v4 회의(2026-11-25) 5-1장: 확장 EX-01 ② 세팅 · EX-02 ③ 분석 탭 · EX-03 바꿀 칸 받기
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import CodeStep from "../entrypoints/sidepanel/steps/CodeStep";
import GuideStep, { isLoginPage } from "../entrypoints/sidepanel/steps/GuideStep";
import PlanStep from "../entrypoints/sidepanel/steps/PlanStep";
import { initialState, reduce, type FlowState, type Plan } from "../lib/flow";
import { nextTestSteps, type GuideStepItem } from "../lib/guide";
import { GUIDE } from "../lib/guideList";
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

  it("panel shows progress like 8/18 with a bar", () => {
    const state: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: 7 } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    expect(screen.getByText("8 / 18")).toBeTruthy();
    const bar = screen.getByRole("progressbar");
    expect(bar.getAttribute("aria-valuenow")).toBe("7");
    expect(bar.getAttribute("aria-valuemax")).toBe("18");
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

describe("뭉치 부르기: 어느 탭으로, 못 받으면", () => {
  it("prefers the Ads Manager tab the owner is looking at in this window", async () => {
    await fakeBrowser.tabs.create({ url: "https://adsmanager.facebook.com/adsmanager/manage/a", active: false });
    const mine = await fakeBrowser.tabs.create({ url: "https://adsmanager.facebook.com/adsmanager/manage/b", active: true });
    const send = vi.spyOn(fakeBrowser.tabs, "sendMessage").mockResolvedValue(undefined);
    const state: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0 } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "광고 관리자 열기" }));
    await waitFor(() => expect(send).toHaveBeenCalled());
    expect(send.mock.calls[0]![0]).toBe(mine.id);
  });

  it("a tab opened before the extension was reloaded gets refreshed, then 뭉치 is called again", async () => {
    const tab = await fakeBrowser.tabs.create({ url: "https://adsmanager.facebook.com/adsmanager/manage/a", active: true });
    const reload = vi.spyOn(fakeBrowser.tabs, "reload").mockResolvedValue(undefined);
    let fixed = false;
    reload.mockImplementation(async () => { fixed = true; });
    const send = vi.spyOn(fakeBrowser.tabs, "sendMessage").mockImplementation(async () => { if (!fixed) throw new Error("Receiving end does not exist"); });
    const state: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0 } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "광고 관리자 열기" }));
    await waitFor(() => expect(reload).toHaveBeenCalledWith(tab.id));
    await waitFor(() => expect(send.mock.calls.length).toBeGreaterThan(1));
    expect(screen.queryByText(/캐릭터를 부르지 못했어요/)).toBeNull();
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
  change: { field_id: "meta.ad.media", label: "형식·미디어", new: "세로(9:16) 소재를 넣은 세트를 하나 더 만들어 보세요", note: "돈의 72%가 릴스에",
    path: "광고 › 형식·미디어", certainty: { level: "보류", label: "아직 몰라요", why: "돌려 본 적 없음" },
    checklist: ["시작 시간을 하루 여유 있게", "클릭이 30번 넘게 모일 때까지 그대로 두기", "바꾸는 칸은 형식·미디어 1개만", "두 세트는 같은 날 같이 시작"],
    ...{ tag: "테스트 제안", new_short: "+ 세로(9:16) 1개" } },
  summary: ["a", "b", "c"], badge: { word: "B 쪽이에요", prob: 0.79 },
  keep: [{ field_id: "meta.adset.placements", path: "광고 세트 › 노출 위치", value: "직접 고르기(수동)", reason: "↓ 광고비 15% 싸요 · 확실해요" }],
  dont: ["여러 칸을 한 번에 바꾸지 않기 — 이유"],
};

describe("EX-03 바꿀 칸 받기", () => {
  it("pins the test card (v4.2: '테스트 제안' tag, no 유력), keep (유지) and the 4-item checklist", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "첫 말", suggestions: ["q1", "q2"] })));
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    const card = screen.getByRole("region", { name: "바꿀 칸" });
    expect(within(card).getByText("광고 › 형식·미디어")).toBeTruthy();
    expect(within(card).getByText("+ 세로(9:16) 1개")).toBeTruthy();
    expect(within(card).getByText("테스트 제안")).toBeTruthy();
    expect(within(card).queryByText(/유력|보류|채택/)).toBeNull();
    expect(screen.getByText(/유지/)).toBeTruthy();
    expect(screen.getByText(/직접 고르기\(수동\)/)).toBeTruthy();
    expect(screen.getByText(/복제한 세트에서 이 칸만 바꾸세요/)).toBeTruthy();
    expect(screen.getByText("다음 테스트 체크리스트")).toBeTruthy();
    expect(screen.getAllByRole("checkbox").length).toBe(4);
    expect(screen.getByText("두 세트는 같은 날 같이 시작")).toBeTruthy();
  });

  it("an old dev label (유력) is still shown in owner words only", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: [] })));
    const old = { ...plan, change: { ...plan.change, certainty: { level: "유력" as const, label: "유력", why: "실측" }, tag: undefined } };
    render(<PlanStep state={{ ...initialState(), step: "plan", plan: old }} dispatch={() => {}} />);
    const card = screen.getByRole("region", { name: "바꿀 칸" });
    expect(within(card).getByText("B 쪽이에요")).toBeTruthy();
    expect(within(card).queryByText("유력")).toBeNull();
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
    fireEvent.click(screen.getByRole("button", { name: "그 칸으로 이동" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "startFix" });
  });
});

describe("EX-03 [다음 테스트 세팅] ↺ (v4.2)", () => {
  const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: `칸 ${id}`, value: "지난 값" }));

  it("the button sends the owner back to ② 세팅 with only the changed field as the new value", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: [] })));
    const dispatch = vi.fn();
    render(<PlanStep state={{ ...initialState(), step: "plan", plan, settings }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "다음 테스트 세팅 ▶" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "startNextTest", fieldId: "meta.ad.media", label: "형식·미디어", value: "+ 세로(9:16) 1개" });
    const s = reduce({ ...initialState(), step: "plan", plan, settings }, dispatch.mock.calls[0]![0]);
    expect(s.step).toBe("guide");
    expect(s.guide).toEqual({ mode: "create", index: 0, next: "meta.ad.media" });
    expect(s.settings.find((x) => x.fieldId === "meta.ad.media")!.value).toBe("+ 세로(9:16) 1개");
    expect(s.settings.filter((x) => x.value === "지난 값")).toHaveLength(settings.length - 1);
  });

  it("② 세팅 list: only the changed field is '지금', the rest are done with last values; the character gets just that field + publish check", async () => {
    const state: FlowState = reduce({ ...initialState(), step: "plan", plan, settings },
      { type: "startNextTest", fieldId: "meta.ad.media", label: "형식·미디어", value: "+ 세로(9:16) 1개" });
    render(<GuideStep state={state} dispatch={() => {}} />);
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(18);
    const now = items.filter((li) => li.getAttribute("aria-current") === "step");
    expect(now).toHaveLength(1);
    expect(now[0]!.textContent).toContain("+ 세로(9:16) 1개");
    expect(now[0]!.textContent).toContain("지금");
    expect(items.filter((li) => li.className.includes("line-through"))).toHaveLength(15);   // 나머지 15칸은 끝난 칸, 돈 확인·게시 확인만 남음
    expect(screen.getByText(/복제한 세트에서 '칸 meta.ad.media' 칸만 바꾸면 돼요/)).toBeTruthy();
    const send = vi.spyOn(fakeBrowser.tabs, "sendMessage").mockResolvedValue(true as never);
    vi.spyOn(fakeBrowser.tabs, "query").mockResolvedValue([{ id: 7, active: true, url: "https://adsmanager.facebook.com/x" }] as never);
    fireEvent.click(screen.getByRole("button", { name: "광고 관리자 열기" }));
    await waitFor(() => expect(send).toHaveBeenCalled());
    const msg = send.mock.calls[0]![1] as { steps: { entry: { id: string } }[] };
    expect(msg.steps.map((x) => x.entry.id)).toEqual(["meta.ad.media", "meta.money_check", "meta.publish"]);
  });

  it("a field only in the edit guide (노출 위치) is put before the publish check", () => {
    const steps = nextTestSteps(GUIDE, settings, "meta.adset.placements");
    expect(steps.send.map((x) => x.entry.id)).toEqual(["meta.adset.placements", "meta.money_check", "meta.publish"]);
    expect(steps.all.at(-2)!.entry.id).toBe("meta.adset.placements");
  });
});

describe("EX-01 ④ 세팅 중 알림 · EX-02 ④ 세팅 요약 (v4.2)", () => {
  const base = SETTING_ORDER.map((id) => ({ fieldId: id, label: `칸 ${id}`, value: "v" }));

  it("end date row says the total budget must beat 'daily minimum × days' (원, 이유 → 할 일)", async () => {
    const { daysUntil } = await import("../entrypoints/sidepanel/steps/GuideStep");
    expect(daysUntil("2026-11-30", new Date(2026, 10, 24))).toBe(7);
    const end = new Date(); end.setDate(end.getDate() + 6);
    const iso = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(end.getDate()).padStart(2, "0")}`;
    const settings = base.map((x) => (x.fieldId === "meta.adset.end_date" ? { ...x, value: iso } : x));
    render(<GuideStep state={{ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0 } }} dispatch={() => {}} />);
    expect(screen.getByText(/하루 최소 약 1,336원 × 7일 = 약 9,400원'보다 적으면 광고가 안 나갈 수 있어요 → 세트마다 그 이상으로/)).toBeTruthy();
  });

  it("publish check warns when a required field is empty", () => {
    const settings = base.map((x) => (x.fieldId === "meta.creative.copy.headline" ? { ...x, value: "" } : x));
    render(<GuideStep state={{ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0 } }} dispatch={() => {}} />);
    expect(screen.getByText(/칸 meta.creative.copy.headline 칸이 비어 있어요 → 채운 뒤 게시해 주세요/)).toBeTruthy();
  });

  it("③ 분석 shows this ad's settings that go along to the analysis page", () => {
    const settings = base.map((x) => ({ ...x, value: { "meta.campaign.objective": "트래픽", "meta.adset.age_gender": "30–39세 · 여성", "meta.ad.media": "정사각 이미지" }[x.fieldId] ?? "" }));
    render(<CodeStep state={{ ...initialState(), step: "upload", settings }} dispatch={() => {}} />);
    const card = screen.getByRole("region", { name: "이번 광고 세팅" });
    expect(within(card).getByText("트래픽 · 30–39세 · 여성")).toBeTruthy();
    expect(within(card).getByText("소재: 정사각 이미지")).toBeTruthy();
  });
});

describe("처음 쓰는 사장님: 로그인 화면", () => {
  it("광고 관리자 대신 페이스북 로그인 화면이 뜨면 직접 로그인하라고 알리고, 로그인 뒤 광고 관리자가 뜨면 뭉치를 이어서 부른다", async () => {
    vi.restoreAllMocks();   // 앞 테스트가 바꿔 둔 탭 찾기(query) 흉내를 지운다
    const tab = await fakeBrowser.tabs.create({ url: "https://www.facebook.com/login.php?next=https%3A%2F%2Fadsmanager.facebook.com%2F", active: true });
    const send = vi.spyOn(fakeBrowser.tabs, "sendMessage").mockResolvedValue(undefined);
    const state: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0 } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "광고 관리자 열기" }));
    expect(await screen.findByText(/페이스북에 로그인해 주세요/)).toBeTruthy();
    expect(send).not.toHaveBeenCalled();
    await fakeBrowser.tabs.update(tab.id!, { url: "https://adsmanager.facebook.com/adsmanager/manage/campaigns" });
    await waitFor(() => expect(send).toHaveBeenCalled(), { timeout: 4000 });
    expect(send.mock.calls[0]![0]).toBe(tab.id);
    expect(screen.queryByText(/페이스북에 로그인해 주세요/)).toBeNull();
  });

  it("로그인 화면 주소를 알아본다 (광고 관리자 주소는 아님)", () => {
    expect(isLoginPage("https://www.facebook.com/login.php?next=x")).toBe(true);
    expect(isLoginPage("https://business.facebook.com/business/loginpage/?next=x")).toBe(true);
    expect(isLoginPage("https://www.facebook.com/checkpoint/1501092823525282/")).toBe(true);
    expect(isLoginPage("https://adsmanager.facebook.com/adsmanager/manage/campaigns?act=1")).toBe(false);
  });
});
