// 화면 검토 (2026-11-26) 추천 6개: 처음부터·돈 칸 막힘·같은 세트 다시 확인·내보내기 돌아가기·특별 카테고리 '네'·목록 줄 key
import { fireEvent, render, screen } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import { initialState, reduce, type FlowState } from "../lib/flow";
import { stepsFor, type GuideStepItem } from "../lib/guide";
import { GUIDE } from "../lib/guideList";
import { handleProgress } from "../lib/progress";
import { SETTING_ORDER } from "../lib/settings";
import { loadState, saveState } from "../lib/storage";

beforeEach(() => fakeBrowser.reset());
const wait = () => new Promise((r) => setTimeout(r, 1000));   // 돈 확인은 구역을 띄우고 0.8초 뒤 읽는다
const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: id, value: "v" }));

describe("21. 처음부터", () => {
  it("뭉치 진행(rev)이 저장돼 있어도 처음으로 돌아간다", async () => {
    await saveState({ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 3 } });
    await handleProgress({ type: "guide:progress", index: 4, total: 18 });   // 배경이 rev를 올림
    const panel = await loadState();                                         // 패널은 onChanged로 이 상태를 따라감
    await saveState(reduce(panel, { type: "reset" }));
    const now = await loadState();
    expect(now.step).toBe("prep");
    expect(now.guide).toBeNull();
    expect(now.settings).toEqual([]);
  });
});

describe("22. 결과 내보내기 안내에서 돌아가기", () => {
  it("export 안내만 닫고 하던 화면(기다리기)은 그대로", async () => {
    const s: FlowState = { ...initialState(), step: "wait", settings, guide: { mode: "export", index: 1 } };
    const dispatch = vi.fn();
    render(<GuideStep state={s} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: /돌아가기/ }));
    expect(dispatch).toHaveBeenCalledWith({ type: "closeExport" });
    expect(reduce(s, { type: "closeExport" })).toMatchObject({ step: "wait", guide: null });
    expect(reduce({ ...s, guide: { mode: "create", index: 2 } }, { type: "closeExport" }).guide).toEqual({ mode: "create", index: 2 });   // 만들기 안내는 안 닫음
  });
});

describe("7. 특별 광고 카테고리 '네'", () => {
  it("'네'면 뭉치가 건너뛰지 않고 사장님이 직접 고르는 칸", () => {
    const pick = (v: string) => stepsFor("create", GUIDE, [{ fieldId: "meta.campaign.special_category", label: "", value: v }], [])
      .find((x) => x.entry.id === "meta.campaign.special_category")!.entry;
    expect(pick("아니요").auto).toBe("skip");
    expect(pick("네")).toMatchObject({ auto: "owner" });
    expect(pick("네").say).toContain("직접 골라");
  });
});

function money(id: string, auto: GuideStepItem["entry"]["auto"], value?: string): GuideStepItem {
  return { entry: { id, mode: "create", page: {}, find: [{ heading: "예산 및 일정" }], say: "돈 칸", done: "manual", fallback: { image: "", text: "" }, auto }, value };
}
function lifetime(end = true) {
  document.documentElement.lang = "ko";
  document.body.innerHTML = `<h2>예산 및 일정</h2><label id="l1">총 예산</label><label id="l2">예산 모드</label>
    <div role="combobox" aria-labelledby="l1 l2 l3"><div id="l3">총 예산</div></div>
    <input type="text" placeholder="금액을 입력하세요" value="30,000"><input placeholder="yyyy-mm-dd" value="2026년 11월 26일">
    ${end ? `<span id="p1">종료 날짜 기간</span><div role="combobox" aria-labelledby="p1"><div>30일</div></div><input placeholder="yyyy-mm-dd" value="2099년 12월 26일">` : ""}`;
}

describe("13. 돈 칸: 칸을 못 찾으면 사장님 확인으로", () => {
  it("종료 날짜 칸을 못 찾으면 멈추고, [다 했어요]를 한 번 더 누르면 넘어간다", { timeout: 8000 }, async () => {
    lifetime(false);
    const seen: number[] = [];
    const g = new Guide(document, [money("meta.money_check", "moneyCheck", "3만 원"), money("meta.publish", "stop")], 0, (i) => seen.push(i), 0);
    g.apply(); await wait();
    expect(g.view().index).toBe(0);
    expect(g.view().text).toContain("한 번 더 눌러");
    g.apply(); await wait();
    expect(seen).toEqual([1]);
  });

  it("값이 다르면(일일 예산) 몇 번을 눌러도 넘어가지 않는다", { timeout: 8000 }, async () => {
    lifetime(false);
    document.getElementById("l3")!.textContent = "일일 예산";
    const g = new Guide(document, [money("meta.money_check", "moneyCheck", "3만 원"), money("meta.publish", "stop")], 0, () => {}, 0);
    g.apply(); await wait();
    g.apply(); await wait();
    expect(g.view().index).toBe(0);
  });

  it("예산 공유 칸을 못 찾으면 같은 방식 (한 번 더 누르면 넘어감)", async () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<h2>예산</h2><span id="c2">광고 세트 예산</span><input type="radio" aria-labelledby="c2" checked>`;
    const seen: number[] = [];
    const g = new Guide(document, [{ ...money("meta.campaign.budget_strategy", "campaignBudget"), entry: { ...money("x", "campaignBudget").entry, id: "meta.campaign.budget_strategy", find: [{ heading: "예산" }] } }, money("next", "owner")], 0, (i) => seen.push(i), 0);
    g.apply(); await wait(); await wait();
    expect(g.view().text).toContain("공유하기'가 꺼져 있는지");
    g.apply(); await wait(); await wait();
    expect(seen).toEqual([1]);
  }, 10000);
});

describe("14. [이전 칸] 뒤 같은 돈 확인 칸으로 돌아와도 다시 확인된다", () => {
  it("같은 칸·같은 세트는 통과, 다른 돈 확인 칸에서 같은 세트면 막힘은 그대로", { timeout: 10000 }, async () => {
    lifetime();
    history.pushState({}, "", "/adsmanager/manage/adsets/edit?selected_adset_ids=111");
    const g = new Guide(document, [money("meta.money_check", "moneyCheck", "3만 원"), money("meta.publish", "stop")], 0, () => {}, 0);
    g.apply(); await wait();
    expect(g.view().index).toBe(1);
    g.back();
    g.apply(); await wait();
    expect(g.view().index).toBe(1);
  });
});

describe("26. 다음 테스트 목록 줄 key", () => {
  it("돈 확인 칸이 두 번 들어가도 React가 같은 key 경고를 내지 않는다", async () => {
    const err = vi.spyOn(console, "error").mockImplementation(() => {});
    const plan = { code: "EX01", action: "", change: { field_id: "meta.ad.primary_text", label: "기본 문구", old: "a", new: "b" }, summary: [], badge: null } as unknown as FlowState["plan"];
    const s: FlowState = { ...initialState(), step: "guide", settings: [...settings, { fieldId: "meta.money_check", label: "돈", value: "3만 원" }], plan,
      guide: { mode: "create", index: 0, next: "meta.ad.primary_text" } };
    render(<GuideStep state={s} dispatch={() => {}} />);
    expect(err.mock.calls.some((c) => String(c[0]).includes("same key"))).toBe(false);
    err.mockRestore();
  });
});

// ── 화면 검토 A·B·C 묶음 (2026-11-27) ──
import { Question } from "../entrypoints/sidepanel/steps/QuestionStep";
import AnalysisAssistant from "../entrypoints/sidepanel/steps/AnalysisAssistant";
import { askedFields } from "../lib/settings";
import { nextTestSteps } from "../lib/guide";
import { FIELDS as fieldsJson } from "./fixtures-fields";

describe("A. 답을 다시 정하는 길", () => {
  const filled: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: 5 },
    answers: { "meta.pre.store_product": "올렸어요", "meta.pre.store_url": "https://a.kr", "meta.adset.end_date": "14일", "meta.adset.lifetime_budget": "3만 원",
      "meta.adset.conversion_location": "인스타그램 프로필", "meta.ad.website_url": "https://www.instagram.com/old" } };

  it("9. [② 답 바꾸기]: 준비물 답만 남기고 ② 질문으로, 지운 답은 미리 채우기용으로", () => {
    const s = reduce(filled, { type: "editAnswers" });
    expect(s).toMatchObject({ step: "questions", guide: null });
    expect(Object.keys(s.answers)).toEqual(["meta.pre.store_product", "meta.pre.store_url"]);
    expect(s.prevAnswers?.["meta.adset.lifetime_budget"]).toBe("3만 원");
    render(<GuideStep state={filled} dispatch={vi.fn()} />);
    expect(screen.getByRole("button", { name: /② 답 바꾸기/ })).toBeTruthy();
  });

  it("2. 세팅까지 간 뒤 준비물을 다시 답하면 클릭 주소 질문만 다시 (옛 주소가 남지 않게)", () => {
    const s = reduce(filled, { type: "prepDone", missing: [] });
    expect(s.step).toBe("questions");
    expect(s.answers["meta.adset.conversion_location"]).toBeUndefined();
    expect(s.answers["meta.ad.website_url"]).toBeUndefined();
    expect(s.answers["meta.adset.lifetime_budget"]).toBe("3만 원");
    expect(reduce(initialState(), { type: "prepDone", missing: [] }).step).toBe("find");   // 처음이면 그대로 ① 찾기
  });

  it("1. 준비물에서 주소를 받아도 클릭 주소 질문은 나온다 (미리 채움)", () => {
    expect(askedFields(fieldsJson as never).map((f) => f.id)).toContain("meta.adset.conversion_location");
  });

  it("8. [← 이전 질문]으로 가면 직접 넣은 금액이 칸에 남아 있다", () => {
    const s = reduce({ ...initialState(), answers: { "meta.adset.lifetime_budget": "25,000원" } }, { type: "unanswer", id: "meta.adset.lifetime_budget" });
    const field = (fieldsJson as never as { id: string }[]).find((f) => f.id === "meta.adset.lifetime_budget") as never;
    render(<Question field={field} answers={s.answers} prev={s.prevAnswers} keywords={[]} checked={[]} onCheck={() => {}} onAnswer={() => {}} />);
    expect((screen.getByLabelText(/총예산/) as HTMLInputElement).value).toBe("25000");
  });

  it("[② 답 바꾸기]로 돌아오면 보기에서 고른 지난번 답에 표시", () => {
    const s = reduce({ ...initialState(), answers: { "meta.adset.end_date": "7일" } }, { type: "unanswer", id: "meta.adset.end_date" });
    const field = (fieldsJson as never as { id: string }[]).find((f) => f.id === "meta.adset.end_date") as never;
    render(<Question field={field} answers={s.answers} prev={s.prevAnswers} keywords={[]} checked={[]} onCheck={() => {}} onAnswer={() => {}} />);
    expect(screen.getByRole("button", { name: /7일/ }).textContent).toContain("지난번 답");
    expect(screen.getByRole("button", { name: /14일/ }).textContent).not.toContain("지난번 답");
  });

  it("[② 답 바꾸기]: 가게 주변처럼 보기 밖의 답은 한 줄로 보여 준다", () => {
    const s = reduce({ ...initialState(), answers: { "meta.adset.location": "가게 주변 5km · 서울 마포구 망원동" } }, { type: "unanswer", id: "meta.adset.location" });
    const field = (fieldsJson as never as { id: string }[]).find((f) => f.id === "meta.adset.location") as never;
    render(<Question field={field} answers={s.answers} prev={s.prevAnswers} keywords={[]} checked={[]} onCheck={() => {}} onAnswer={() => {}} />);
    expect(screen.getByText("✓ 지난번 답: 가게 주변 5km · 서울 마포구 망원동")).toBeTruthy();
  });

  it("다음 테스트 목록: 지난번 값 그대로인 칸에는 취소선을 긋지 않는다 (EX-03 '유지')", () => {
    render(<GuideStep state={{ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0, next: "meta.ad.media" } }} dispatch={vi.fn()} />);
    expect(document.querySelector(".line-through")).toBeNull();
  });

  it("18. 다음 테스트가 '일일 예산'을 바꾸라 해도 총예산 칸을 새 금액으로", () => {
    const base = { ...initialState(), settings: [...settings, { fieldId: "meta.adset.lifetime_budget", label: "총예산", value: "3만 원" }] };
    const s = reduce(base, { type: "startNextTest", fieldId: "meta.adset.daily_budget", label: "예산", value: "총예산을 넉넉하게", budget: "5만 원" });
    expect(s.guide?.next).toBe("meta.adset.lifetime_budget");
    expect(s.settings.find((x) => x.fieldId === "meta.adset.lifetime_budget")?.value).toBe("5만 원");
    expect(s.settings.some((x) => x.fieldId === "meta.adset.daily_budget")).toBe(false);
  });
});

describe("B. 사진 단계·분석 탭", () => {
  const media = () => stepsFor("create", GUIDE, [], []).find((x) => x.entry.id === "meta.ad.media")!;

  it("15. 사진 칸 1단계에서 [다 했어요]를 누르면 넘어가지 않고 남은 단계를 알린다 (한 번 더 누르면 넘어감)", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="button">크리에이티브 설정</div>`;
    const seen: number[] = [];
    const g = new Guide(document, [media(), money("next", "owner")], 0, (i) => seen.push(i), 0);
    g.apply();
    expect(seen).toEqual([]);
    expect(g.view().text).toContain("단계가 남았어요");
    g.apply();
    expect(seen).toEqual([1]);
  });

  it("16. 다음 테스트에서 바꿀 칸이 사진이면 끝 신호로 바로 지나가지 않는다", () => {
    const { send } = nextTestSteps(GUIDE, settings, "meta.ad.media");
    expect(send.find((x) => x.entry.id === "meta.ad.media")!.entry.doneWhen).toBeUndefined();
  });

  it("16. [이전 칸]으로 사진 칸에 돌아오면 끝 신호가 보여도 그 칸에 머문다", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="button">크리에이티브 설정</div><input aria-label="간단하게 광고를 소개하세요">`;
    const g = new Guide(document, [media(), money("next", "owner")], 1, () => {}, 0);
    g.back();
    expect(g.view().index).toBe(0);
  });

  it("23. 이미 받은 보내기는 분석 탭으로 돌아와도 다시 받지 않고, 결과를 받으면 남은 안내를 닫는다", async () => {
    const fetchSpy = vi.fn((_u: string) => Promise.resolve(new Response(JSON.stringify({ message: "m", suggestions: [] }))));
    vi.stubGlobal("fetch", fetchSpy);
    const dispatch = vi.fn();
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-06", send: "9" }} dispatch={dispatch} handled="9" />);
    await wait();
    expect(fetchSpy.mock.calls.some((c) => String(c[0]).includes("/plan/"))).toBe(false);
    const s = reduce({ ...initialState(), step: "wait", guide: { mode: "export", index: 1 } }, { type: "planLoaded", plan: {} as never, sent: "9" });
    expect(s).toMatchObject({ step: "plan", guide: null, planSent: "9" });
    vi.unstubAllGlobals();
  });
});

describe("C. 작은 것들", () => {
  it("12. 인스타 계정이 없으면 빈 괄호 대신 비워 두라는 말", () => {
    const say = (v: string) => stepsFor("create", GUIDE, [{ fieldId: "meta.pre.ig_account", label: "", value: v }], []).find((x) => x.entry.id === "meta.pre.ig_account")!.entry.say;
    expect(say("")).toContain("비워 두세요");
    expect(say("")).not.toContain("()");
    expect(say("ovenlog")).toContain("{value}");
  });

  it("5. 뺀 말로 다시 본 뒤에는 [뺀 말을 빼고 손님 다시 보기] 띠를 숨긴다", () => {
    const s = reduce(initialState(), { type: "researched", research: { keywords: [] } as never, product: "쿠키", dropped: ["선물"] });
    expect(s.droppedApplied).toEqual(["선물"]);
  });
});

describe("남은 기획 항목 (2026-11-27)", () => {
  it("11. 뭉치가 나가 있으면 지난 칸 이름을 눌러 그 칸으로 보낸다 (앞 칸으로만)", async () => {
    const tab = await fakeBrowser.tabs.create({ url: "https://adsmanager.facebook.com/adsmanager/manage", active: true });
    const send = vi.spyOn(fakeBrowser.tabs, "sendMessage").mockResolvedValue(undefined);
    render(<GuideStep state={{ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 3, away: true } }} dispatch={() => {}} />);
    fireEvent.click(screen.getAllByRole("button", { name: /뭉치를 이 칸으로 보내기/ })[1]!);
    await vi.waitFor(() => expect(send).toHaveBeenCalledWith(tab.id, { type: "guide:goto", index: 1 }));
    expect(screen.getAllByRole("button", { name: /뭉치를 이 칸으로 보내기/ })).toHaveLength(3);   // 지금 칸·뒤 칸은 누를 수 없음
  });

  it("11. 뭉치 goTo는 지난 칸으로만 간다", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<input aria-label="a"><input aria-label="b">`;
    const step = (id: string): GuideStepItem => ({ entry: { id, mode: "create", page: {}, find: [{ aria: id }], say: id, done: "manual", fallback: { image: "", text: "" }, auto: "owner" } });
    const g = new Guide(document, [step("a"), step("b"), step("c")], 1, () => {}, 0);
    g.goTo(2);
    expect(g.view().index).toBe(1);
    g.goTo(0);
    expect(g.view().index).toBe(0);
  });

  it("3. 결제 카드가 없어도 광고 관리자는 열 수 있고, 게시 칸에서 알린다", () => {
    render(<GuideStep state={{ ...initialState(), step: "guide", settings, answers: { "meta.pre.payment": "아직이에요" }, guide: { mode: "create", index: 0 } }} dispatch={() => {}} />);
    expect(screen.getByText(/결제 카드가 아직 없어요/)).toBeTruthy();
    expect(screen.getByRole("button", { name: /광고 관리자 열기/ }).hasAttribute("disabled")).toBe(false);
  });
});

describe("재검토 고치기 (2026-11-27 오후)", () => {
  const withNext: FlowState = { ...initialState(), step: "guide", settings: settings.map((x) => (x.fieldId === "meta.ad.website_url" ? { ...x, value: "https://a.kr" } : x)),
    answers: { "meta.pre.store_product": "올렸어요", "meta.pre.store_url": "https://new.kr" }, guide: { mode: "create", index: 2, next: "meta.ad.media" } };

  it("A1. 다음 테스트 중 준비물을 마쳐도 다음 테스트가 그대로 (안내 목록으로)", () => {
    const s = reduce(withNext, { type: "prepDone", missing: [] });
    expect(s).toMatchObject({ step: "guide", guide: { next: "meta.ad.media" } });
    // 주소가 그대로면 질문으로 보내지 않는다
    const same = reduce({ ...withNext, guide: { mode: "create", index: 0 }, answers: { ...withNext.answers, "meta.pre.store_url": "https://a.kr" } }, { type: "prepDone", missing: [] });
    expect(same.step).toBe("guide");
  });

  it("A1·A2. 옛 저장본: 결제 카드 누락은 빼고, 'fix'는 안내를 닫고 결과 화면", async () => {
    await fakeBrowser.storage.local.set({ "coach.v3.state": { ...initialState(), step: "fix", guide: { mode: "edit", index: 0 }, prepMissing: ["광고 계정 결제 수단", "페이스북 페이지"] } });
    const s = await loadState();
    expect(s).toMatchObject({ step: "plan", guide: null, prepMissing: ["페이스북 페이지"] });
  });

  it("A4. 두 세트 돈 확인: [이전 칸]으로 오가도 영영 막히지 않는다", { timeout: 15000 }, async () => {
    lifetime();
    const m = money("meta.money_check", "moneyCheck", "3만 원");
    const g = new Guide(document, [m, { ...m }, money("meta.publish", "stop")], 0, () => {}, 0);
    history.pushState({}, "", "/x?selected_adset_ids=A"); g.apply(); await wait();   // k0 ← A
    history.pushState({}, "", "/x?selected_adset_ids=B"); g.back(); g.apply(); await wait();   // k0 ← B (A 기록은 지워짐)
    history.pushState({}, "", "/x?selected_adset_ids=A"); g.apply(); await wait();   // k1 ← A
    expect(g.view().index).toBe(2);
  });

  it("A8. 금액 칸이 정말 비어 있으면 두 번 눌러도 넘어가지 않는다", { timeout: 8000 }, async () => {
    lifetime();
    (document.querySelector("input[placeholder='금액을 입력하세요']") as HTMLInputElement).value = "";
    const g = new Guide(document, [money("meta.money_check", "moneyCheck", "3만 원"), money("meta.publish", "stop")], 0, () => {}, 0);
    g.apply(); await wait(); g.apply(); await wait();
    expect(g.view().index).toBe(0);
    expect(g.view().text).toContain("금액 칸이 비어 있어요");
  });

  it("B9. 예전 뭉치가 보낸 진행(다른 안내 표시)은 버린다", async () => {
    await saveState({ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0, sig: "new" } });
    await handleProgress({ type: "guide:progress", index: 9, total: 18, sig: "old" });
    expect((await loadState()).guide?.index).toBe(0);
    await handleProgress({ type: "guide:progress", index: 3, total: 18, sig: "new" });
    expect((await loadState()).guide?.index).toBe(3);
  });
});

describe("한 화면에 말풍선 뭉치는 한 번만 (2026-11-27)", () => {
  it("② 세팅 첫 질문: 안내 말풍선과 질문 말풍선이 이어지면 뭉치 그림은 마지막(질문)에만", async () => {
    const QuestionStep = (await import("../entrypoints/sidepanel/steps/QuestionStep")).default;
    const target = { ageMin: 30, ageMax: 39, gender: "all" as const };
    const copy = { headline: "h", primary_text: "t" } as never;
    const { container } = render(<QuestionStep state={{ ...initialState(), step: "questions", target, copy }} dispatch={() => {}} fields={fieldsJson} defaults={[]} />);
    expect(container.querySelectorAll("img").length).toBe(1);
    expect(screen.getByText(/가지만 물어볼게요/)).toBeTruthy();
  });
});

describe("QA 2026-11-27: 머리 단계 표시 (H-04·H-05)", () => {
  const app = async (state: Partial<FlowState>, tabUrl = "https://example.com/") => {
    const { default: App } = await import("../entrypoints/sidepanel/App");
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ message: "m", suggestions: [], fields: [], defaults: [] })))));
    vi.spyOn(fakeBrowser.tabs, "query").mockResolvedValue([{ id: 9, active: true, url: tabUrl }] as never);
    await fakeBrowser.storage.local.set({ "coach.v3.state": { ...initialState(), ...state } });
    render(<App />);
  };

  it("H-04. 종료일이 지난 기다리기 화면은 ③ 강조 + '결과를 볼 때예요'", async () => {
    await app({ step: "wait", endDate: "2020-01-01", settings });
    await vi.waitFor(() => expect(screen.getByText(/③ 분석/).closest("li")!.getAttribute("aria-current")).toBe("step"));
    expect(screen.getByText("결과를 볼 때예요", { exact: false })).toBeTruthy();
    vi.restoreAllMocks(); vi.unstubAllGlobals();
  });

  it("H-05. 분석 탭을 보고 있어도 광고 켜기 전(문구)이면 ② 세팅 그대로", async () => {
    await app({ step: "copy" }, "http://localhost:8000/analysis#code=AB12CD&step=AN-01");
    await vi.waitFor(() => expect(screen.getByText(/② 세팅/).closest("li")!.getAttribute("aria-current")).toBe("step"));
    vi.restoreAllMocks(); vi.unstubAllGlobals();
  });
});

describe("QA 2026-11-27: 사이드 패널 QA에서 나온 것", () => {
  it("G-03. 준비물을 다시 답하면 안내 목록의 준비물 칸 값도 바뀐다", () => {
    const s0: FlowState = { ...initialState(), step: "prep", settings: settings.map((x) => (x.fieldId === "meta.pre.fb_page" ? { ...x, value: "없어요" } : x)),
      answers: { "meta.pre.fb_page": "있어요" }, guide: { mode: "create", index: 3 } };
    const s = reduce(s0, { type: "prepDone", missing: [] });
    expect(s.step).toBe("guide");
    expect(s.settings.find((x) => x.fieldId === "meta.pre.fb_page")?.value).toBe("있어요");
  });

  it("뒤로 가는 길: ② 첫 질문 → 문구, 코드 넣기 → 기다리기", () => {
    expect(reduce({ ...initialState(), step: "questions" }, { type: "editCopy" }).step).toBe("copy");
    expect(reduce({ ...initialState(), step: "upload" }, { type: "backToWait" }).step).toBe("wait");
    expect(reduce({ ...initialState(), step: "plan" }, { type: "backToWait" }).step).toBe("plan");
  });

  it("P-05. 준비물 주소 칸은 주소 없이 넘어갈 수 있다", () => {
    const field = { ...fieldsJson.find((f) => f.id === "meta.pre.store_product")!, stage: "사전 점검" };
    const onAnswer = vi.fn();
    render(<Question field={field} answers={{}} keywords={[]} checked={[]} onCheck={() => {}} onAnswer={onAnswer} />);
    fireEvent.click(screen.getByRole("button", { name: new RegExp(`^${field.options![0]}`) }));
    expect(screen.queryByText(new RegExp(`^${field.options![0]}로 보낼게요`))).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /주소 없이 넘어가기/ }));
    expect(onAnswer).toHaveBeenCalledWith(field.options![0]);
  });
});
