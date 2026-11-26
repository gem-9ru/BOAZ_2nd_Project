// ② 세팅 총예산: 질문(기간에 맞춘 최소 금액 · ▲) → 뭉치 안내 칸 → 세팅 중 알림이 실제 금액으로 판정 (설계서 v4.2 EX-01 ④)
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import QuestionStep from "../entrypoints/sidepanel/steps/QuestionStep";
import { initialState, type FlowState } from "../lib/flow";
import { GUIDE } from "../lib/guideList";
import { SETTING_ORDER, askedFields, minBudget, parseWon } from "../lib/settings";
import { FIELDS } from "./fixtures-fields";

const BUDGET = "meta.adset.lifetime_budget";
const target = { ageMin: 30, ageMax: 39, gender: "female" as const };
const copy = { primary_text: "버터 듬뿍 수제 쿠키", headline: "수제 쿠키 선물" };

/** 총예산 질문 앞까지 답한 상태 (기간은 period) */
function atBudget(period: string): FlowState {
  const asked = askedFields(FIELDS);
  const before = asked.slice(0, asked.findIndex((f) => f.id === BUDGET));
  const answers = Object.fromEntries(before.map((f) => [f.id, f.default || "x"]));
  return { ...initialState(), step: "questions", target, copy, answers: { ...answers, "meta.adset.end_date": period } };
}

function isoIn(days: number): string {
  const d = new Date(); d.setDate(d.getDate() + days);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

describe("parseWon · minBudget", () => {
  it("reads 만 원 and comma amounts", () => {
    expect(parseWon("3만 원")).toBe(30000);
    expect(parseWon("25,000원")).toBe(25000);
    expect(parseWon("10000")).toBe(10000);
    expect(parseWon("v")).toBeNull();
    expect(parseWon("")).toBeNull();
  });
  it("is daily minimum × days, rounded up to 100원", () => {
    expect(minBudget(7)).toBe(9400);
    expect(minBudget(14)).toBe(18800);
  });
});

describe("총예산 질문", () => {
  it("comes right after the period and before nothing it depends on", () => {
    const ids = askedFields(FIELDS).map((f) => f.id);
    expect(ids.indexOf(BUDGET)).toBe(ids.indexOf("meta.adset.end_date") + 1);
    expect(SETTING_ORDER.indexOf(BUDGET)).toBe(SETTING_ORDER.indexOf("meta.adset.start_date") - 1);   // 광고 관리자: 예산이 날짜 위
  });

  it("tells the minimum for the chosen period and marks too-small options with ▲", () => {
    render(<QuestionStep state={atBudget("14일")} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(screen.getByText(/광고 기간이 14일이라 적어도 약 18,800원/)).toBeTruthy();   // 오늘 포함 14일
    expect(screen.getByRole("button", { name: /^1만 원.*14일 동안 쓰기엔 적어요/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /^3만 원\s*권장$/ })).toBeTruthy();
  });

  it("the question says the amount is the whole spend, not per ad set", () => {
    render(<QuestionStep state={atBudget("14일")} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(screen.queryByText(/세트마다/)).toBeNull();
  });

  it("30일: 권장 moves to the smallest amount that is enough (3만 원 is short)", () => {
    render(<QuestionStep state={atBudget("30일")} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(screen.getByRole("button", { name: /^5만 원\s*권장$/ })).toBeTruthy();
    const three = screen.getByRole("button", { name: /^3만 원/ });
    expect(three.textContent).not.toContain("권장");
    expect(three.className).not.toContain("font-semibold");
  });

  it("typing an amount: shows it in 원, warns when short, answers '25,000원'", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={atBudget("7일")} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "금액 직접 넣기" }));
    const box = screen.getByLabelText("기간 전체 총예산 (원)");
    fireEvent.change(box, { target: { value: "5000" } });
    expect(screen.getByText(/약 9,400원보다 적어서 광고가 안 나갈 수 있어요/)).toBeTruthy();   // 7일 × 1,336원
    fireEvent.change(box, { target: { value: "25000" } });
    expect(screen.queryByText(/적어서 광고가 안 나갈 수 있어요/)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: BUDGET, value: "25,000원" });
  });
});

describe("뭉치 안내 칸 · 세팅 중 알림", () => {
  it("the guide has a create step for the budget, before the start date, that the character fills in and re-reads", () => {
    const ids = GUIDE.filter((e) => e.mode === "create").map((e) => e.id);
    expect(ids.indexOf(BUDGET)).toBe(ids.indexOf("meta.adset.start_date") - 1);
    expect(GUIDE.find((e) => e.id === BUDGET)!.auto).toBe("lifetimeBudget");
  });

  const withBudget = (budget: string) => SETTING_ORDER.map((id) => ({ fieldId: id, label: `칸 ${id}`,
    value: id === "meta.adset.end_date" ? isoIn(6) : id === BUDGET ? budget : "v" }));

  it("warns ▲ with the real numbers when the budget is short for the period", () => {
    render(<GuideStep state={{ ...initialState(), step: "guide", settings: withBudget("5,000원"), guide: { mode: "create", index: 0 } }} dispatch={() => {}} />);
    expect(screen.getAllByText(/총예산 5,000원이 '하루 최소 약 1,336원 × 7일 = 약 9,400원'보다 적어요 → 광고가 안 나갈 수 있어요/).length).toBeGreaterThan(0);
  });

  it("stays quiet when the budget is enough", () => {
    render(<GuideStep state={{ ...initialState(), step: "guide", settings: withBudget("3만 원"), guide: { mode: "create", index: 0 } }} dispatch={() => {}} />);
    expect(screen.queryByText(/하루 최소 약 1,336원/)).toBeNull();
  });
});
