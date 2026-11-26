// 준비물·② 세팅 질문 UI/UX: 누르는 크기, '나중에'의 무게, 포커스, 돈 설명 크기, 권장 표시, 빠진 준비물 다음 할 일, 폼 피드백
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PrepStep from "../entrypoints/sidepanel/steps/PrepStep";
import QuestionStep from "../entrypoints/sidepanel/steps/QuestionStep";
import type { Field } from "../lib/api";
import { initialState, type FlowState } from "../lib/flow";
import { askedFields } from "../lib/settings";
import { FIELDS } from "./fixtures-fields";

const target = { ageMin: 30, ageMax: 39, gender: "female" as const };
const copy = { primary_text: "버터 쿠키", headline: "쿠키" };
const asked = askedFields(FIELDS);
const upTo = (id: string) => Object.fromEntries(asked.slice(0, asked.findIndex((f) => f.id === id)).map((f) => [f.id, f.default || "x"]));
const q = (answers: Record<string, string> = {}): FlowState => ({ ...initialState(), step: "questions", target, copy, answers });

const help = { say: "페이지를 만들어 주세요", link: "만들기", url: "https://www.facebook.com/pages/create", done: "만들었어요", done_value: "있어요", later: "나중에 만들게요" };
const PAGE: Field = { id: "meta.pre.fb_page", kind: "precheck", label: "페이스북 페이지", ask: "페이지 있으세요?", options: ["있어요", "없어요"],
  default: "있어요", why: "이유", stage: "사전 점검", required: true, help: { 없어요: help } };

describe("누르는 크기 (44px 이상)", () => {
  it("이전 질문 · 다시 고르기 · 나중에 링크도 높이 44px(min-h-11)", () => {
    render(<QuestionStep state={q({ [asked[0]!.id]: "아니요" })} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(screen.getByRole("button", { name: "← 이전 질문" }).className).toContain("min-h-11");
  });
  it("준비물 요약의 다시 답하기도 44px", () => {
    render(<PrepStep state={{ ...initialState(), answers: { "meta.pre.fb_page": "있어요" } }} dispatch={() => {}} fields={[PAGE]} />);
    expect(screen.getByRole("button", { name: "다시 답하기" }).className).toContain("min-h-11");
  });
});

describe("'나중에'도 같은 무게", () => {
  it("나중에 만들게요는 테두리 버튼, 다시 고르기도 44px", () => {
    render(<PrepStep state={initialState()} dispatch={() => {}} fields={[PAGE]} />);
    fireEvent.click(screen.getByRole("button", { name: /^없어요/ }));
    const later = screen.getByRole("button", { name: "나중에 만들게요" });
    expect(later.className).toContain("border");
    expect(later.className).toContain("min-h-11");
    expect(screen.getByRole("button", { name: "← 다시 고르기" }).className).toContain("min-h-11");
  });
});

describe("포커스", () => {
  it("새 질문이 나오면 그 질문 제목으로 포커스가 간다", () => {
    render(<QuestionStep state={q()} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(document.activeElement).toBe(screen.getByRole("heading", { level: 2 }));
  });
});

describe("돈 설명은 본문 크기", () => {
  it("총예산 질문의 설명은 text-body·진한 글자", () => {
    render(<QuestionStep state={q({ ...upTo("meta.adset.lifetime_budget"), "meta.adset.end_date": "14일" })} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    const why = screen.getAllByText("이유").find((e) => e.tagName === "P")!;
    expect(why.className).toContain("text-body");
    expect(why.className).toContain("text-ink");
  });
  it("돈과 상관없는 질문의 설명은 그대로 작게", () => {
    render(<QuestionStep state={q()} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(screen.getAllByText("이유").find((e) => e.tagName === "P")!.className).toContain("text-caption");
  });
});

describe("권장 표시", () => {
  it("권장은 '권장' 글자로만, 고른 것처럼 굵은 테두리를 쓰지 않음", () => {
    render(<QuestionStep state={q()} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    const rec = screen.getByRole("button", { name: /^있어요\s*권장/ });
    expect(rec.className).not.toContain("border-ink");
    expect(rec.className).not.toContain("font-semibold");
  });
});

describe("빠진 준비물: 다음 할 일", () => {
  it("꼭 필요한데 빠진 칸은 [만드는 법 보기] → 그 칸의 만드는 법이 바로 열림", () => {
    const dispatch = vi.fn();
    const { rerender } = render(<PrepStep state={{ ...initialState(), answers: { "meta.pre.fb_page": "없어요" } }} dispatch={dispatch} fields={[PAGE]} />);
    fireEvent.click(screen.getByRole("button", { name: "만드는 법 보기" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "unanswer", id: "meta.pre.fb_page" });
    rerender(<PrepStep state={initialState()} dispatch={dispatch} fields={[PAGE]} />);
    expect(screen.getByRole("link", { name: /만들기/ })).toBeTruthy();
  });
});

describe("인스타그램 칸", () => {
  it("칸 이름은 '인스타그램 아이디', 예시가 있음", () => {
    render(<QuestionStep state={q(upTo("meta.pre.ig_account"))} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect((screen.getByLabelText("인스타그램 아이디") as HTMLInputElement).placeholder).toContain("예:");
  });
});

describe("폼 피드백", () => {
  it("금액을 숫자로 못 읽으면 고치는 법을 칸 아래에 보여 줌", () => {
    render(<QuestionStep state={q({ ...upTo("meta.adset.lifetime_budget"), "meta.adset.end_date": "14일" })} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "금액 직접 넣기" }));
    const box = screen.getByLabelText("기간 전체 총예산 (원)");
    fireEvent.change(box, { target: { value: "삼만원" } });
    const err = screen.getByText(/숫자로 넣어 주세요/);
    expect(box.getAttribute("aria-describedby")).toContain(err.id);
  });
  it("주소 오류 문구는 칸에 연결됨 (aria-describedby)", () => {
    render(<QuestionStep state={q(upTo("meta.adset.conversion_location"))} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^스토어 상품 페이지/ }));
    const box = screen.getByLabelText("상품 페이지 주소");
    fireEvent.change(box, { target: { value: "오븐로그" } });
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(box.getAttribute("aria-describedby")).toBe(screen.getByRole("alert").id);
  });
});

describe("묻지 않고 둔 칸", () => {
  it("펼치는 줄도 44px", () => {
    render(<QuestionStep state={q()} dispatch={() => {}} fields={FIELDS} defaults={[{ id: "x", label: "구매 유형", default: "경매", why: "w" }]} />);
    expect(screen.getByText(/묻지 않고 이렇게 두었어요/).className).toContain("min-h-11");
  });
});
