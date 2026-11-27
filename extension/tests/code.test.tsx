import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CodeStep from "../entrypoints/sidepanel/steps/CodeStep";
import PlanStep from "../entrypoints/sidepanel/steps/PlanStep";
import { initialState, reduce, type Plan } from "../lib/flow";
import { stepsFor } from "../lib/guide";
import { GUIDE } from "../lib/guideList";

const plan: Plan = {
  code: "75R7KD", action: "한 번 더",
  change: { field_id: "meta.adset.end_date", label: "종료 날짜", new: "세트당 총 151,000원이 쓰일 때까지 더 돌리기", note: "확실히 고르려면 이만큼 더 필요해요" },
  summary: ["이번에 알게 된 것: B가 나을 확률 79% (B 쪽이에요)", "아직 모르는 것: 도착 수가 적어요", "다음에 바꿀 것: 세트당 총 151,000원까지 더 돌리기"],
  badge: { word: "B 쪽이에요", prob: 0.79 },
};
const ok = (b: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(b), { status }));

beforeEach(() => fakeBrowser.reset());
afterEach(() => vi.unstubAllGlobals());

describe("③ 코드 넣기", () => {
  it("opens the analysis page in a new tab", async () => {
    const create = vi.spyOn(fakeBrowser.tabs, "create");
    render(<CodeStep state={{ ...initialState(), step: "upload" }} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "분석 페이지 열기 (새 창)" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ url: "http://localhost:8000/analysis" }));
  });

  it("says so when the settings could not be handed to the analysis page", async () => {
    const create = vi.spyOn(fakeBrowser.tabs, "create");
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response("{}", { status: 500 }))));
    const settings = [{ fieldId: "meta.campaign.objective", label: "목표", value: "트래픽" }];
    render(<CodeStep state={{ ...initialState(), step: "upload", settings }} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "분석 페이지 열기 (새 창)" }));
    await waitFor(() => expect(create).toHaveBeenCalledWith({ url: "http://localhost:8000/analysis" }));
    expect((await screen.findByRole("alert")).textContent).toContain("세팅값을 넘기지 못했어요");
  });

  it("tidies the code and fetches the plan", async () => {
    const f = vi.fn((_url: string) => ok(plan));
    vi.stubGlobal("fetch", f);
    const dispatch = vi.fn();
    render(<CodeStep state={{ ...initialState(), step: "upload" }} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("분석 페이지의 코드 6자리"), { target: { value: " 75r7kd " } });
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "planLoaded", plan }));
    expect(String(f.mock.calls[0]![0])).toBe("http://localhost:8000/plan/75R7KD");
  });

  it("explains how to fix a short or unknown code, right under the box", async () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ detail: "코드를 찾지 못했어요. 분석 페이지의 코드를 다시 확인해 주세요." }, 404)));
    render(<CodeStep state={{ ...initialState(), step: "upload" }} dispatch={() => {}} />);
    const box = screen.getByLabelText("분석 페이지의 코드 6자리");
    fireEvent.change(box, { target: { value: "75" } });
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    expect(screen.getByRole("alert").textContent).toContain("6자리");
    expect(screen.getByRole("alert").textContent).toContain("③ 준비하기");   // 분석 페이지에 실제로 코드가 있는 곳 (축소안 v5: 3단계)
    expect(screen.getByRole("alert").textContent).not.toContain("다음에 할 일");
    fireEvent.change(box, { target: { value: "ZZZZZZ" } });
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("다시 확인해 주세요"));
  });
});

describe("③ 다음에 할 일 (코드로 받은 것)", () => {
  it("shows the one change (v4: 3줄 요약 대신 변경안 카드 + 챗봇)", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: [] })));
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={() => {}} />);
    expect(screen.getAllByText(/종료 날짜/).length).toBeGreaterThan(0);
    expect(screen.getByText(/세트당 총 151,000원이 쓰일 때까지 더 돌리기/)).toBeTruthy();
  });

  it("flow: planLoaded → plan step, and the edit guide uses the plan's change", () => {
    const s = reduce({ ...initialState(), step: "upload" }, { type: "planLoaded", plan });
    expect(s.step).toBe("plan");
    expect(stepsFor("edit", GUIDE, [], s.plan ? [s.plan.change] : []).map((x) => x.entry.id)).toEqual(["meta.adset.end_date"]);
  });
});

describe("③ 코드 넣기: 쉬운 말", () => {
  it("does not use jargon like '분석 기준' or '테스트안', and says where the code is", () => {
    render(<CodeStep state={{ ...initialState(), step: "upload" }} dispatch={() => {}} />);
    const text = document.body.textContent ?? "";
    expect(text).not.toMatch(/분석 기준|테스트안/);
    expect(text).toMatch(/\[확장 프로그램으로 보내기\]/);
  });
});

describe("③ 결과 화면: 체크리스트 · 하지 말 것", () => {
  const p: Plan = { ...plan, change: { ...plan.change, checklist: ["시작 시간을 하루 여유 있게", "두 세트는 같은 날 같이 시작"] },
    dont: ["여러 칸 한 번에 변경 — 무엇 덕분인지 모르게 돼요."],
    watch: [{ field_id: "meta.adset.end_date", path: "광고 세트 › 시작·종료 날짜", text: "첫날 안 보여졌어요 → 다음엔 시작 시간을 하루 여유 있게" }] };

  it("a ticked checklist line is saved (stays after the panel is closed and opened again)", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: [] })));
    const dispatch = vi.fn();
    render(<PlanStep state={{ ...initialState(), step: "plan", plan: p, checks: { "plan:75R7KD": [1] } }} dispatch={dispatch} />);
    const boxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(boxes.map((b) => b.checked)).toEqual([false, true]);
    fireEvent.click(boxes[0]!);
    expect(dispatch).toHaveBeenCalledWith({ type: "toggleCheck", key: "plan:75R7KD", index: 0 });
  });

  it("shows what not to do and what to watch from the analysis", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: [] })));
    render(<PlanStep state={{ ...initialState(), step: "plan", plan: p }} dispatch={() => {}} />);
    expect(screen.getByText(/여러 칸 한 번에 변경/)).toBeTruthy();
    expect(screen.getByText(/첫날 안 보여졌어요/)).toBeTruthy();
  });
});

describe("③ 코드 넣기: 받은 단계 ✓ (EX-02 ③)", () => {
  const ended = [{ fieldId: "meta.adset.end_date", label: "종료", value: "2026-11-20" }];
  it("[짚어 주기] only notes the start; the ✓ comes when the owner returns from the export guide", () => {
    const dispatch = vi.fn();
    const { unmount } = render(<CodeStep state={{ ...initialState(), step: "upload", settings: ended }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "내보내기 버튼 짚어 주기" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "toggleCheck", key: "upload:2026-11-20", index: 9 });
    expect(dispatch).not.toHaveBeenCalledWith({ type: "toggleCheck", key: "upload:2026-11-20", index: 0 });
    expect(dispatch).toHaveBeenCalledWith({ type: "startExport" });
    unmount();
    // 안내를 닫고 이 화면이 다시 그려짐 → 1번 ✓
    const back = vi.fn();
    render(<CodeStep state={{ ...initialState(), step: "upload", settings: ended, checks: { "upload:2026-11-20": [9] } }} dispatch={back} />);
    expect(back).toHaveBeenCalledWith({ type: "toggleCheck", key: "upload:2026-11-20", index: 0 });
  });

  it("shows ✓ for done steps and the number for the rest", () => {
    render(<CodeStep state={{ ...initialState(), step: "upload", settings: ended, checks: { "upload:2026-11-20": [0, 9] } }} dispatch={() => {}} />);
    const items = screen.getAllByRole("listitem");
    expect(items[0]!.textContent).toMatch(/^✓ 했어요/);
    expect(items[1]!.textContent).toMatch(/^2/);
  });
});
