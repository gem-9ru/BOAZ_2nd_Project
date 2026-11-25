import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CodeStep from "../entrypoints/sidepanel/steps/CodeStep";
import PlanStep from "../entrypoints/sidepanel/steps/PlanStep";
import { initialState, reduce, type Plan } from "../lib/flow";
import { stepsFor } from "../lib/guide";
import { GUIDE } from "../lib/guideList";

const plan: Plan = {
  code: "75R7", action: "한 번 더",
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

  it("tidies the code and fetches the plan", async () => {
    const f = vi.fn((_url: string) => ok(plan));
    vi.stubGlobal("fetch", f);
    const dispatch = vi.fn();
    render(<CodeStep state={{ ...initialState(), step: "upload" }} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("분석 페이지의 코드 4자리"), { target: { value: " 75r7 " } });
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "planLoaded", plan }));
    expect(String(f.mock.calls[0]![0])).toBe("http://localhost:8000/plan/75R7");
  });

  it("explains how to fix a short or unknown code, right under the box", async () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ detail: "코드를 찾지 못했어요. 분석 페이지의 코드를 다시 확인해 주세요." }, 404)));
    render(<CodeStep state={{ ...initialState(), step: "upload" }} dispatch={() => {}} />);
    const box = screen.getByLabelText("분석 페이지의 코드 4자리");
    fireEvent.change(box, { target: { value: "75" } });
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    expect(screen.getByRole("alert").textContent).toContain("4자리");
    fireEvent.change(box, { target: { value: "ZZZZ" } });
    fireEvent.click(screen.getByRole("button", { name: "가져오기" }));
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("다시 확인해 주세요"));
  });
});

describe("③ 다음에 할 일 (코드로 받은 것)", () => {
  it("shows the one change (v4: 3줄 요약 대신 변경안 카드 + 챗봇), and 그 칸으로 이동 starts the edit guide on that field", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({ message: "m", suggestions: [] })));
    const dispatch = vi.fn();
    render(<PlanStep state={{ ...initialState(), step: "plan", plan }} dispatch={dispatch} />);
    expect(screen.getByText(/종료 날짜/)).toBeTruthy();
    expect(screen.getByText(/세트당 총 151,000원이 쓰일 때까지 더 돌리기/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "그 칸으로 이동" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "startFix" });
  });

  it("flow: planLoaded → plan step, and the edit guide uses the plan's change", () => {
    const s = reduce({ ...initialState(), step: "upload" }, { type: "planLoaded", plan });
    expect(s.step).toBe("plan");
    const fix = reduce(s, { type: "startFix" });
    expect(stepsFor("edit", GUIDE, [], fix.plan ? [fix.plan.change] : []).map((x) => x.entry.id)).toEqual(["meta.adset.end_date"]);
  });
});
