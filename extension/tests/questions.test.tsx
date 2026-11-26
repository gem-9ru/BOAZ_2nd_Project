import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import QuestionStep from "../entrypoints/sidepanel/steps/QuestionStep";
import { initialState, reduce, type FlowState } from "../lib/flow";
import { SETTING_ORDER, askedFields, buildSettings, endDateFrom } from "../lib/settings";
import { FIELDS } from "./fixtures-fields";

const target = { ageMin: 30, ageMax: 39, gender: "female" as const };
const copy = { primary_text: "버터 듬뿍 수제 쿠키", headline: "수제 쿠키 선물" };

describe("buildSettings", () => {
  const answers = Object.fromEntries(FIELDS.map((x) => [x.id, x.default ?? ""]));
  const s = buildSettings(FIELDS, { ...answers, "meta.ad.website_url": "https://smartstore.naver.com/ovenlog" }, target, copy, "2026-12-06");

  it("returns 13 settings in screen order, campaign objective 트래픽 first", () => {
    expect(s.map((x) => x.fieldId)).toEqual(SETTING_ORDER);
    expect(s).toHaveLength(13);
    expect(s[0]).toEqual({ fieldId: "meta.campaign.objective", label: "캠페인 목표", value: "트래픽" });
  });

  it("age_gender comes from target and copy fields from the picked copy", () => {
    expect(s.find((x) => x.fieldId === "meta.adset.age_gender")!.value).toBe("30–39세 · 여성");
    expect(s.find((x) => x.fieldId === "meta.creative.copy.text")!.value).toBe("버터 듬뿍 수제 쿠키");
    expect(s.find((x) => x.fieldId === "meta.creative.copy.headline")!.value).toBe("수제 쿠키 선물");
    expect(s.find((x) => x.fieldId === "meta.adset.end_date")!.value).toBe("2026-12-06");
  });
});

describe("questions", () => {
  it("never asks objective or age_gender, at most 11", () => {
    const ids = askedFields(FIELDS).map((x) => x.id);
    expect(ids).not.toContain("meta.campaign.objective");
    expect(ids).not.toContain("meta.adset.age_gender");
    expect(ids.length).toBeLessThanOrEqual(11);
  });

  it("endDateFrom adds the chosen days", () => {
    expect(endDateFrom("7일", new Date("2026-11-29T10:00:00"))).toBe("2026-12-06");
  });

  it("QuestionStep shows one question at a time and moves on with the default", () => {
    const dispatch = vi.fn();
    const state: FlowState = { ...initialState(), step: "questions", target, copy };
    render(<QuestionStep state={state} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(1);
    expect(screen.getByText("페이스북 페이지?")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^있어요/ }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.pre.fb_page", value: "있어요" });
  });

  it("finishing the last question dispatches questionsDone with 13 settings", () => {
    const dispatch = vi.fn();
    const answers = Object.fromEntries(askedFields(FIELDS).slice(0, -1).map((x) => [x.id, x.default || "x"]));
    const state: FlowState = { ...initialState(), step: "questions", target, copy, answers };
    render(<QuestionStep state={state} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^정사각형 사진/ }));
    const done = dispatch.mock.calls.map((c) => c[0]).find((e) => e.type === "questionsDone");
    expect(done.settings).toHaveLength(13);
  });
});

describe("페이스북 페이지가 없어요 → 만들기 링크", () => {
  const help = { 없어요: { say: "페이지를 만들어 주세요", link: "페이스북 페이지 만들기", url: "https://www.facebook.com/pages/create",
    done: "만들었어요", done_value: "있어요", later: "나중에 만들게요" } };
  const fields = FIELDS.map((x) => (x.id === "meta.pre.fb_page" ? { ...x, help } : x));
  const state: FlowState = { ...initialState(), step: "questions", target, copy };

  it("'없어요' does not move on; it shows the create link in a new tab", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={state} dispatch={dispatch} fields={fields} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^없어요/ }));
    expect(dispatch).not.toHaveBeenCalled();
    const link = screen.getByRole("link", { name: /페이스북 페이지 만들기/ });
    expect(link.getAttribute("href")).toBe("https://www.facebook.com/pages/create");
    expect(link.getAttribute("target")).toBe("_blank");
  });

  it("'만들었어요' records 있어요, '나중에 만들게요' records 없어요, '다시 고르기' goes back", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={state} dispatch={dispatch} fields={fields} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^없어요/ }));
    fireEvent.click(screen.getByRole("button", { name: "만들었어요" }));
    expect(dispatch).toHaveBeenLastCalledWith({ type: "answer", id: "meta.pre.fb_page", value: "있어요" });
    fireEvent.click(screen.getByRole("button", { name: "나중에 만들게요" }));
    expect(dispatch).toHaveBeenLastCalledWith({ type: "answer", id: "meta.pre.fb_page", value: "없어요" });
    fireEvent.click(screen.getByRole("button", { name: "← 다시 고르기" }));
    expect(screen.getByRole("button", { name: /^있어요/ })).toBeTruthy();
  });
});

describe("going back and checking the web address", () => {
  const asked = askedFields(FIELDS);
  const base: FlowState = { ...initialState(), step: "questions", target, copy };

  it("이전 질문 clears the previous answer", () => {
    const dispatch = vi.fn();
    const answers = { [asked[0]!.id]: asked[0]!.default ?? "있어요" };
    render(<QuestionStep state={{ ...base, answers }} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "← 이전 질문" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "unanswer", id: asked[0]!.id });
  });

  it("no 이전 질문 on the first question", () => {
    render(<QuestionStep state={base} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(screen.queryByRole("button", { name: "← 이전 질문" })).toBeNull();
  });

  it("the click destination asks its address on the same question, and it must look like a web address", () => {
    expect(asked.some((f) => f.id === "meta.ad.website_url")).toBe(false);   // 따로 묻지 않음
    const at = asked.findIndex((f) => f.id === "meta.adset.conversion_location");
    const answers = Object.fromEntries(asked.slice(0, at).map((f) => [f.id, f.default || "x"]));
    const dispatch = vi.fn();
    render(<QuestionStep state={{ ...base, answers }} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^스토어 상품 페이지/ }));
    expect(dispatch).not.toHaveBeenCalled();
    const box = screen.getByLabelText("상품 페이지 주소");
    fireEvent.change(box, { target: { value: "오븐로그" } });
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(screen.getByText(/https:\/\/ 로 시작하는 주소/)).toBeTruthy();
    expect(dispatch).not.toHaveBeenCalled();
    fireEvent.change(box, { target: { value: "smartstore.naver.com/ovenlog" } });
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.adset.conversion_location", value: "스토어 상품 페이지" });
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.ad.website_url", value: "https://smartstore.naver.com/ovenlog" });
  });

  it("인스타그램 프로필 fills the address from the Instagram ID given earlier", () => {
    const at = asked.findIndex((f) => f.id === "meta.adset.conversion_location");
    const answers = { ...Object.fromEntries(asked.slice(0, at).map((f) => [f.id, f.default || "x"])), "meta.pre.ig_account": "@ovenlog " };
    const dispatch = vi.fn();
    render(<QuestionStep state={{ ...base, answers }} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^인스타그램 프로필/ }));
    expect((screen.getByLabelText("인스타 주소") as HTMLInputElement).value).toBe("https://www.instagram.com/ovenlog");
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.ad.website_url", value: "https://www.instagram.com/ovenlog" });
  });
});

describe("스마트스토어에 아직 안 올렸어요 → 체크리스트와 주소", () => {
  const asked = askedFields(FIELDS);
  const at = asked.findIndex((f) => f.id === "meta.pre.store_product");
  const before = Object.fromEntries(asked.slice(0, at).map((f) => [f.id, f.default || "x"]));
  const base: FlowState = { ...initialState(), step: "questions", target, copy, keywords: ["수제 쿠키", "선물 쿠키", "답례품", "쿠키 세트"],
    answers: { ...before, "meta.pre.ig_account": "ovenlog" } };

  it("toggleCheck adds and removes a done step; checks start empty", () => {
    expect(initialState().checks).toEqual({});
    const once = reduce(initialState(), { type: "toggleCheck", key: "meta.pre.store_product", index: 1 });
    expect(once.checks).toEqual({ "meta.pre.store_product": [1] });
    expect(reduce(once, { type: "toggleCheck", key: "meta.pre.store_product", index: 1 }).checks).toEqual({ "meta.pre.store_product": [] });
  });

  it("'아직이에요' shows 3 checkboxes, links in new tabs, done count and the first 3 keywords", () => {
    const dispatch = vi.fn();
    const state = { ...base, checks: { "meta.pre.store_product": [0] } };
    render(<QuestionStep state={state} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^아직이에요/ }));
    expect(dispatch).not.toHaveBeenCalled();
    const boxes = screen.getAllByRole("checkbox") as HTMLInputElement[];
    expect(boxes).toHaveLength(3);
    expect(boxes[0]!.checked).toBe(true);
    expect(screen.getByText("1 / 3")).toBeTruthy();
    expect(screen.getByRole("link", { name: /가입하기/ }).getAttribute("target")).toBe("_blank");
    expect(screen.getByText(/수제 쿠키 · 선물 쿠키 · 답례품/)).toBeTruthy();
    expect(screen.queryByText(/쿠키 세트/)).toBeNull();
    fireEvent.click(boxes[1]!);
    expect(dispatch).toHaveBeenCalledWith({ type: "toggleCheck", key: "meta.pre.store_product", index: 1 });
  });

  it("no keyword line when ① has no keywords", () => {
    render(<QuestionStep state={{ ...base, keywords: [] }} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^아직이에요/ }));
    expect(screen.queryByText(/네이버에서 잘 찾아져요/)).toBeNull();
  });

  it("'다 했어요' asks the product address and records 올렸어요 + store_url", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={base} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^아직이에요/ }));
    fireEvent.click(screen.getByRole("button", { name: "다 했어요" }));
    expect(dispatch).not.toHaveBeenCalled();
    fireEvent.change(screen.getByLabelText("올린 상품 주소"), { target: { value: "smartstore.naver.com/ovenlog/products/1" } });
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.pre.store_product", value: "올렸어요" });
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.pre.store_url", value: "https://smartstore.naver.com/ovenlog/products/1" });
  });

  it("'나중에 할게요' asks the Instagram address prefilled, and records 아직이에요 + insta_url", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={base} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^아직이에요/ }));
    fireEvent.click(screen.getByRole("button", { name: "나중에 할게요" }));
    expect((screen.getByLabelText("인스타 프로필 주소") as HTMLInputElement).value).toBe("https://www.instagram.com/ovenlog");
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.pre.store_product", value: "아직이에요" });
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.pre.insta_url", value: "https://www.instagram.com/ovenlog" });
  });

  const atLoc = asked.findIndex((f) => f.id === "meta.adset.conversion_location");
  const upToLoc = Object.fromEntries(asked.slice(0, atLoc).map((f) => [f.id, f.default || "x"]));

  it("not yet on the store → 인스타그램 프로필 is 권장 with a note, and the store address box starts empty", () => {
    const answers = { ...upToLoc, "meta.pre.store_product": "아직이에요", "meta.pre.insta_url": "https://www.instagram.com/ovenlog",
      "meta.adset.conversion_location": "인스타그램 프로필", "meta.ad.website_url": "https://www.instagram.com/ovenlog" };
    delete (answers as Record<string, string>)["meta.adset.conversion_location"];
    render(<QuestionStep state={{ ...base, answers }} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(screen.getByRole("button", { name: /^인스타그램 프로필/ }).textContent).toContain("권장");
    expect(screen.getByRole("button", { name: /^스토어 상품 페이지/ }).textContent).not.toContain("권장");
    expect(screen.getByText("스토어가 준비되면 바꿀 수 있어요.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /^스토어 상품 페이지/ }));
    expect((screen.getByLabelText("상품 페이지 주소") as HTMLInputElement).value).toBe("");
  });

  it("the product address given earlier fills the store address box", () => {
    const answers = { ...upToLoc, "meta.pre.store_product": "올렸어요", "meta.pre.store_url": "https://smartstore.naver.com/ovenlog/products/1" };
    render(<QuestionStep state={{ ...base, answers }} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(screen.getByRole("button", { name: /^스토어 상품 페이지/ }).textContent).toContain("권장");
    fireEvent.click(screen.getByRole("button", { name: /^스토어 상품 페이지/ }));
    expect((screen.getByLabelText("상품 페이지 주소") as HTMLInputElement).value).toBe("https://smartstore.naver.com/ovenlog/products/1");
  });
});

describe("unanswer", () => {
  it("removes one answer", async () => {
    const { reduce } = await import("../lib/flow");
    const s = reduce({ ...initialState(), answers: { a: "1", b: "2" } }, { type: "unanswer", id: "b" });
    expect(s.answers).toEqual({ a: "1" });
  });
});
