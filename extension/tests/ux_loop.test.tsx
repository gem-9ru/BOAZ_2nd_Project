// 게시 뒤 고리 UI/UX 점검 (2026-11-26): 큰 글씨 · 안심 문장 · 주 버튼 위치 · 누르는 크기 · 끝나기 전 분석 · 코드 칸 접기
import { render, screen } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CodeStep from "../entrypoints/sidepanel/steps/CodeStep";
import PlanStep from "../entrypoints/sidepanel/steps/PlanStep";
import WaitStep from "../entrypoints/sidepanel/steps/WaitStep";
import { bubbleClass } from "../entrypoints/sidepanel/ui/Chat";
import { initialState, type Plan } from "../lib/flow";

const ok = (b: unknown) => Promise.resolve(new Response(JSON.stringify(b), { status: 200 }));
const plan: Plan = {
  code: "AB12", action: "다른 변수",
  change: { field_id: "meta.ad.media", label: "형식·미디어", new: "세로 소재", note: "릴스에 돈이 몰려요", path: "광고 › 형식·미디어",
    checklist: ["두 세트는 같은 날 같이 시작"], ...{ per_set: 5000 } },
  summary: [], badge: null,
};
const budget = [{ fieldId: "meta.adset.lifetime_budget", label: "총예산", value: "10,000원" }];

beforeEach(() => { fakeBrowser.reset(); vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: ["질문 하나"] }))); });
afterEach(() => vi.unstubAllGlobals());

describe("1. 돈·날짜·어시스턴트 말은 본문 크기", () => {
  it("money box and checklist are body size, and chat bubbles too", () => {
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    const box = screen.getByRole("region", { name: "다음 테스트 돈·기간" });
    expect(box.className).toContain("text-body");
    expect(box.className).not.toContain("text-caption");
    expect(screen.getByText("두 세트는 같은 날 같이 시작").closest("ul")!.className).toContain("text-body");
    expect(bubbleClass("assistant")).toContain("text-body");
    expect(bubbleClass("me")).toContain("text-body");
  });
});

describe("2. 기다리기: 돈이 얼마까지만 나가는지", () => {
  it("says the per-set cap and that it stops by itself after the end date", () => {
    render(<WaitStep state={{ ...initialState(), step: "wait", endDate: "2099-12-06", settings: budget }} dispatch={() => {}} />);
    expect(screen.getByText(/세트 하나에 총 10,000원까지만 나가요/)).toBeTruthy();
    expect(screen.getByText(/12월 6일이 지나면 저절로 멈춰요/)).toBeTruthy();
  });
});

describe("3. 결과 화면: 주 버튼이 위로", () => {
  it("[다음 테스트 세팅] comes right after the money box, before the checklist and the chatbot", () => {
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    const go = screen.getByRole("button", { name: "다음 테스트 세팅 ▶" });
    const before = (a: Node, b: Node) => Boolean(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
    expect(before(screen.getByRole("region", { name: "다음 테스트 돈·기간" }), go)).toBe(true);
    expect(before(go, screen.getByText("두 세트는 같은 날 같이 시작"))).toBe(true);
    expect(before(go, screen.getByRole("region", { name: "광고 어시스턴트" }))).toBe(true);
  });
});

describe("4. 누르는 곳은 44px 이상", () => {
  const tall = (el: HTMLElement) => expect(el.className).toMatch(/min-h-11|min-h-12|py-3/);
  it("small text buttons, chips, ask button and checklist rows", async () => {
    render(<WaitStep state={{ ...initialState(), step: "wait" }} dispatch={() => {}} />);
    tall(screen.getByRole("button", { name: "결과 내보내는 법 보기" }));
    render(<CodeStep state={{ ...initialState(), step: "upload" }} dispatch={() => {}} />);
    tall(screen.getByRole("button", { name: "내보내기 버튼 짚어 주기" }));
    tall(screen.getByRole("button", { name: "분석 페이지 열기 (새 창)" }));
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    tall(screen.getByRole("button", { name: "다른 코드 넣기" }));
    tall(screen.getByText("두 세트는 같은 날 같이 시작").closest("label")!);
    tall(await screen.findByRole("button", { name: "질문 하나" }));
    tall(screen.getAllByRole("button", { name: "묻기" })[0]!);
  });
});

describe("5. 광고가 끝나기 전에는 [결과 분석하기]를 작게", () => {
  it("before the end it is a plain button with 'from' date; after the end it is the big button", () => {
    const { unmount } = render(<WaitStep state={{ ...initialState(), step: "wait", endDate: "2099-12-06" }} dispatch={() => {}} />);
    expect(screen.getByRole("button", { name: "결과 분석하기" }).className).not.toContain("bg-accent");
    expect(screen.getByText(/12월 7일부터 눌러 주세요/)).toBeTruthy();
    unmount();
    render(<WaitStep state={{ ...initialState(), step: "wait", endDate: "2020-01-01" }} dispatch={() => {}} />);
    expect(screen.getByRole("button", { name: "결과 분석하기" }).className).toContain("bg-accent");
  });
});

describe("6. 코드 칸은 '보내기가 안 되면'으로 접어 둔다", () => {
  it("the code box sits inside a closed disclosure; opening the analysis page is the main way", () => {
    render(<CodeStep state={{ ...initialState(), step: "upload" }} dispatch={() => {}} />);
    const box = screen.getByLabelText("분석 페이지의 코드 4자리");
    const fold = box.closest("details")!;
    expect(fold).toBeTruthy();
    expect(fold.open).toBe(false);
    expect(fold.querySelector("summary")!.textContent).toMatch(/보내기가 안 되면/);
    expect(screen.getByRole("button", { name: "분석 페이지 열기 (새 창)" }).className).toContain("bg-accent");
  });
});


describe("7. 다음 테스트 세팅에서 결과 화면으로 돌아가기", () => {
  it("backToPlan returns to the result screen and undoes the new value, dates and amount", async () => {
    const { reduce } = await import("../lib/flow");
    const before = { ...initialState(), step: "plan" as const, plan, startDate: "2026-11-17", endDate: "2026-11-20",
      settings: [...budget, { fieldId: "meta.ad.media", label: "형식·미디어", value: "가로 사진" }] };
    const next = reduce(before, { type: "startNextTest", fieldId: "meta.ad.media", label: "형식·미디어", value: "세로 소재",
      startDate: "2026-11-27", endDate: "2026-11-30", budget: "5,400원" });
    expect(next.step).toBe("guide");
    const back = reduce(next, { type: "backToPlan" });
    expect(back.step).toBe("plan");
    expect(back.guide).toBeNull();
    expect(back.settings).toEqual(before.settings);
    expect([back.startDate, back.endDate]).toEqual(["2026-11-17", "2026-11-20"]);
    // 게시까지 끝내면(guideDone) 되돌릴 값은 버린다
    const done = reduce(next, { type: "guideDone" });
    expect(reduce(done, { type: "backToPlan" }).step).toBe("wait");
  });
});

describe("8. 어시스턴트 첫 답을 기다리는 동안", () => {
  it("shows a loading line (not an empty box)", async () => {
    const { default: AnalysisAssistant } = await import("../entrypoints/sidepanel/steps/AnalysisAssistant");
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));
    render(<AnalysisAssistant tab={{ tabId: 1, code: "AB12", step: "AN-01", send: null }} dispatch={() => {}} />);
    expect(screen.getByRole("status").textContent).toMatch(/불러오는 중/);
  });
});

describe("9. 묻기 칸 이름이 보인다", () => {
  it("the ask box has a visible label (not only a placeholder)", async () => {
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    const label = document.querySelector('label[for="ex-ask"]')!;
    expect(label.textContent).toBe("어시스턴트에게 묻기");
    expect(label.className).not.toContain("sr-only");
  });
});

describe("화면 확인(2026-11-26, 400px)에서 본 것", () => {
  it("the ask box hint is short enough to show whole in a narrow panel", () => {
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    expect((document.getElementById("ex-ask") as HTMLInputElement).placeholder).toBe("예: CPM이 뭐예요?");
  });

  it("the change card does not stick to the top while scrolling (it hid a fifth of the panel)", () => {
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    expect(screen.getByRole("region", { name: "바꿀 칸" }).className).not.toContain("sticky");
  });

  it("this ad's settings show the end date as '11월 20일', like the other screens", () => {
    render(<CodeStep state={{ ...initialState(), step: "upload", settings: [
      { fieldId: "meta.campaign.objective", label: "목표", value: "트래픽" },
      { fieldId: "meta.adset.end_date", label: "종료 날짜", value: "2026-11-20 09:00" }] }} dispatch={() => {}} />);
    const box = screen.getByRole("region", { name: "이번 광고 세팅" });
    expect(box.textContent).toContain("종료 날짜: 11월 20일");
    expect(box.textContent).not.toContain("2026-11-20");
  });
});
