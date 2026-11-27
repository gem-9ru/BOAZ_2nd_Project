import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import QuestionStep from "../entrypoints/sidepanel/steps/QuestionStep";
import { initialState, reduce, type FlowState } from "../lib/flow";
import { SETTING_ORDER, askedFields, buildSettings, endDateFrom, scheduleDays, scheduleFrom } from "../lib/settings";
import { FIELDS } from "./fixtures-fields";

const target = { ageMin: 30, ageMax: 39, gender: "female" as const };
const copy = { primary_text: "버터 듬뿍 수제 쿠키", headline: "수제 쿠키 선물" };

describe("buildSettings", () => {
  const answers = Object.fromEntries(FIELDS.map((x) => [x.id, x.default ?? ""]));
  const s = buildSettings(FIELDS, { ...answers, "meta.ad.website_url": "https://smartstore.naver.com/ovenlog" }, target, copy, { start: "2026-11-29", end: "2026-12-06" });

  it("returns 17 settings in screen order, campaign objective 트래픽 first, start date right before end date", () => {
    expect(s.map((x) => x.fieldId)).toEqual(SETTING_ORDER);
    expect(s).toHaveLength(17);
    const at = s.findIndex((x) => x.fieldId === "meta.adset.start_date");
    expect(s[at]).toEqual({ fieldId: "meta.adset.start_date", label: "시작 날짜", value: "2026-11-29" });
    expect(s[at + 1]!.fieldId).toBe("meta.adset.end_date");
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

  it("endDateFrom: '7일' runs 7 days counting today (not 8)", () => {
    expect(endDateFrom("7일", new Date("2026-11-29T10:00:00"))).toBe("2026-12-05");
    expect(scheduleDays(scheduleFrom("7일", new Date("2026-11-29T10:00:00")))).toBe(7);
  });

  it("scheduleFrom: chips start today; a picked range is used as is", () => {
    const today = new Date("2026-11-29T10:00:00");
    expect(scheduleFrom("14일", today)).toEqual({ start: "2026-11-29", end: "2026-12-12" });
    expect(scheduleFrom("2026-12-01~2026-12-14", today)).toEqual({ start: "2026-12-01", end: "2026-12-14" });
    expect(scheduleFrom("2026-12-01 09:00~2026-12-14 21:30", today))
      .toEqual({ start: "2026-12-01", end: "2026-12-14", startTime: "09:00", endTime: "21:30" });
    const s = buildSettings(FIELDS, {}, target, copy, scheduleFrom("2026-12-01 09:00~2026-12-14 21:30", today));
    expect(s.find((x) => x.fieldId === "meta.adset.start_date")!.value).toBe("2026-12-01 09:00");
    expect(s.find((x) => x.fieldId === "meta.adset.end_date")!.value).toBe("2026-12-14 21:30");
  });

  it("the first question starts with how many questions and that no money goes out until 게시", () => {
    render(<QuestionStep state={{ ...initialState(), step: "questions", target, copy }} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    const n = askedFields(FIELDS).length;
    expect(screen.getByText(new RegExp(`${n}가지만 물어볼게요`))).toBeTruthy();
    expect(screen.getByText(/'게시'를 누르기 전에는 돈이 나가지 않아요/)).toBeTruthy();
  });

  it("the intro is only on the first question", () => {
    const first = askedFields(FIELDS)[0]!;
    render(<QuestionStep state={{ ...initialState(), step: "questions", target, copy, answers: { [first.id]: first.default ?? "x" } }} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    expect(screen.queryByText(/가지만 물어볼게요/)).toBeNull();
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

  it("finishing the last question dispatches questionsDone with 17 settings and the picked dates", () => {
    const dispatch = vi.fn();
    const answers = Object.fromEntries(askedFields(FIELDS).slice(0, -1).map((x) => [x.id, x.default || "x"]));
    const state: FlowState = { ...initialState(), step: "questions", target, copy, answers };
    render(<QuestionStep state={state} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^1장/ }));
    const dones = dispatch.mock.calls.map((c) => c[0]).filter((e) => e.type === "questionsDone");
    expect(dones).toHaveLength(1);   // 한 번만 넘어간다 (QA Q-08)
    expect(dones[0].settings).toHaveLength(17);
  });

  it("photos are not asked again in ② (준비물 already did); the settings keep the media default", () => {
    expect(askedFields(FIELDS).map((x) => x.id)).not.toContain("meta.ad.media");
    const s = buildSettings(FIELDS, {}, target, copy, { start: "2026-11-29", end: "2026-12-05" });
    expect(s.find((x) => x.fieldId === "meta.ad.media")!.value).toBe("정사각형 사진");
  });

  it("'묻지 않고 이렇게 두었어요' leaves out cells 뭉치 guides (예: 예산 전략)", () => {
    const defaults = [{ id: "meta.campaign.budget_strategy", label: "예산 전략", default: "광고 세트 예산", why: "w" },
      { id: "meta.campaign.buying_type", label: "구매 유형", default: "경매", why: "w" }];
    render(<QuestionStep state={{ ...initialState(), step: "questions", target, copy }} dispatch={() => {}} fields={FIELDS} defaults={defaults} />);
    expect(screen.getByText(/묻지 않고 이렇게 두었어요 \(1칸\)/)).toBeTruthy();
    expect(screen.queryByText(/예산 전략:/)).toBeNull();
  });

  it("a picked range goes to questionsDone as startDate and endDate", () => {
    const dispatch = vi.fn();
    const answers = { ...Object.fromEntries(askedFields(FIELDS).slice(0, -1).map((x) => [x.id, x.default || "x"])),
      "meta.adset.end_date": "2099-03-01~2099-03-10" };
    render(<QuestionStep state={{ ...initialState(), step: "questions", target, copy, answers }} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^1장/ }));
    const done = dispatch.mock.calls.map((c) => c[0]).find((e) => e.type === "questionsDone");
    expect(done).toMatchObject({ startDate: "2099-03-01", endDate: "2099-03-10" });
    expect(done.settings.find((x: { fieldId: string }) => x.fieldId === "meta.adset.start_date").value).toBe("2099-03-01");
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

  it("'스마트스토어에서 안 팔아요' asks the Instagram address right away", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={base} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^스마트스토어에서 안 팔아요/ }));
    expect((screen.getByLabelText("인스타 프로필로 보낼 주소") as HTMLInputElement).value).toBe("https://www.instagram.com/ovenlog");
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.pre.store_product", value: "스마트스토어에서 안 팔아요" });
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.pre.insta_url", value: "https://www.instagram.com/ovenlog" });
  });

  it("no product page address → one tap switches to the Instagram profile address", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={base} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^올렸어요/ }));
    fireEvent.click(screen.getByRole("button", { name: /상품 페이지 주소가 없어요/ }));
    expect((screen.getByLabelText("인스타 프로필로 보낼 주소") as HTMLInputElement).value).toBe("https://www.instagram.com/ovenlog");
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.pre.store_product", value: "스마트스토어에서 안 팔아요" });
  });

  const atLoc = asked.findIndex((f) => f.id === "meta.adset.conversion_location");
  const upToLoc = Object.fromEntries(asked.slice(0, atLoc).map((f) => [f.id, f.default || "x"]));

  it("Instagram address from 준비물 → settings use it (클릭 주소 질문은 미리 채운 채 다시 보여 줌, 화면 검토 1)", () => {
    const answers = { ...upToLoc, "meta.pre.store_product": "아직이에요", "meta.pre.insta_url": "https://www.instagram.com/ovenlog" };
    expect(askedFields(FIELDS).map((f) => f.id)).toContain("meta.adset.conversion_location");
    const s = buildSettings(FIELDS, answers, target, copy, { start: "2026-11-29", end: "2026-12-05" });
    expect(s.find((x) => x.fieldId === "meta.adset.conversion_location")!.value).toBe("인스타그램 프로필");
    expect(s.find((x) => x.fieldId === "meta.ad.website_url")!.value).toBe("https://www.instagram.com/ovenlog");
  });

  it("on the click question too, no product page → Instagram profile", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={{ ...base, answers: { ...upToLoc, "meta.pre.ig_account": "ovenlog" } }} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^스토어 상품 페이지/ }));
    fireEvent.click(screen.getByRole("button", { name: /상품 페이지 주소가 없어요/ }));
    expect((screen.getByLabelText("인스타 주소") as HTMLInputElement).value).toBe("https://www.instagram.com/ovenlog");
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.adset.conversion_location", value: "인스타그램 프로필" });
  });

  it("store address from 준비물 → 스토어 상품 페이지 with that address", () => {
    const answers = { ...upToLoc, "meta.pre.store_product": "올렸어요", "meta.pre.store_url": "https://smartstore.naver.com/ovenlog/products/1" };
    const s = buildSettings(FIELDS, answers, target, copy, { start: "2026-11-29", end: "2026-12-05" });
    expect(s.find((x) => x.fieldId === "meta.adset.conversion_location")!.value).toBe("스토어 상품 페이지");
    expect(s.find((x) => x.fieldId === "meta.ad.website_url")!.value).toBe("https://smartstore.naver.com/ovenlog/products/1");
  });

  it("a destination answered in ② wins over the 준비물 address", () => {
    const answers = { "meta.pre.store_product": "올렸어요", "meta.pre.store_url": "https://a.com/1",
      "meta.adset.conversion_location": "인스타그램 프로필", "meta.ad.website_url": "https://www.instagram.com/x" };
    const s = buildSettings(FIELDS, answers, target, copy, { start: "2026-11-29", end: "2026-12-05" });
    expect(s.find((x) => x.fieldId === "meta.ad.website_url")!.value).toBe("https://www.instagram.com/x");
  });
});

describe("광고 기간: 날짜 직접 정하기", () => {
  const asked = askedFields(FIELDS);
  const at = asked.findIndex((f) => f.id === "meta.adset.end_date");
  const answers = Object.fromEntries(asked.slice(0, at).map((f) => [f.id, f.default || "x"]));
  const state: FlowState = { ...initialState(), step: "questions", target, copy, answers };

  function open(dispatch = vi.fn()) {
    render(<QuestionStep state={state} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: "날짜 직접 정하기" }));
    return dispatch;
  }

  it("shows start and end date boxes; start is today by default", () => {
    open();
    const start = screen.getByLabelText("시작일") as HTMLInputElement;
    expect(start.type).toBe("date");
    expect(start.value).toBe(scheduleFrom("7일").start);
    expect((screen.getByLabelText("종료일") as HTMLInputElement).type).toBe("date");
  });

  it("a start before today and an end not after the start are told how to fix, right below", () => {
    const dispatch = open();
    fireEvent.change(screen.getByLabelText("시작일"), { target: { value: "2020-01-01" } });
    fireEvent.change(screen.getByLabelText("종료일"), { target: { value: "2099-01-10" } });
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(screen.getByText("오늘이나 그 뒤 날짜로 골라 주세요.")).toBeTruthy();
    fireEvent.change(screen.getByLabelText("시작일"), { target: { value: "2099-01-10" } });
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(screen.getByText("종료일을 시작일 다음 날 이후로 골라 주세요.")).toBeTruthy();
    expect(dispatch).not.toHaveBeenCalled();
  });

  it("a good range shows how long, and records 'start~end'", () => {
    const dispatch = open();
    fireEvent.change(screen.getByLabelText("시작일"), { target: { value: "2099-12-01" } });
    fireEvent.change(screen.getByLabelText("종료일"), { target: { value: "2099-12-14" } });
    expect(screen.getByText("12월 1일부터 12월 14일까지, 14일 동안 광고해요.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.adset.end_date", value: "2099-12-01~2099-12-14" });
  });

  it("times are optional; when given they are said and recorded", () => {
    const dispatch = open();
    expect((screen.getByLabelText("시작 시각") as HTMLInputElement).type).toBe("time");
    fireEvent.change(screen.getByLabelText("시작일"), { target: { value: "2099-12-01" } });
    fireEvent.change(screen.getByLabelText("종료일"), { target: { value: "2099-12-14" } });
    fireEvent.change(screen.getByLabelText("시작 시각"), { target: { value: "09:00" } });
    fireEvent.change(screen.getByLabelText("종료 시각"), { target: { value: "21:30" } });
    expect(screen.getByText("12월 1일 오전 9시부터 12월 14일 오후 9시 30분까지, 14일 동안 광고해요.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.adset.end_date", value: "2099-12-01 09:00~2099-12-14 21:30" });
  });

  it("다시 고르기 goes back to the day chips", () => {
    open();
    fireEvent.click(screen.getByRole("button", { name: "← 다시 고르기" }));
    expect(screen.getByRole("button", { name: /^14일/ })).toBeTruthy();
  });
});

describe("광고 지역: 손님이 상품을 어떻게 받나요?", () => {
  const asked = askedFields(FIELDS);
  const at = asked.findIndex((f) => f.id === "meta.adset.location");
  const answers = Object.fromEntries(asked.slice(0, at).map((f) => [f.id, f.default || "x"]));
  const state: FlowState = { ...initialState(), step: "questions", target, copy, answers };

  it("three ways, none marked 권장", () => {
    render(<QuestionStep state={state} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    for (const o of ["택배로 보내요", "가게에 와서 사요", "배달해요"]) {
      const b = screen.getByRole("button", { name: new RegExp(`^${o}`) });
      expect(b.textContent).not.toContain("권장");
    }
  });

  it("택배로 보내요 → 전국 (택배)", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={state} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^택배로 보내요/ }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.adset.location", value: "전국 (택배)" });
  });

  it("가게에 와서 사요 → shop address + radius (5km by default); an empty address cannot go on", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={state} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^가게에 와서 사요/ }));
    expect(dispatch).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "5km" }).getAttribute("aria-pressed")).toBe("true");
    const next = screen.getByRole("button", { name: "다음" }) as HTMLButtonElement;
    expect(next.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText(/가게 주소/), { target: { value: "   " } });
    expect(next.disabled).toBe(true);
    fireEvent.change(screen.getByLabelText(/가게 주소/), { target: { value: " 서울 마포구 망원동 " } });
    fireEvent.click(screen.getByRole("button", { name: "3km" }));
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.adset.location", value: "가게 주변 3km · 서울 마포구 망원동" });
  });

  it("배달해요 → same address box, 5km when not changed", () => {
    const dispatch = vi.fn();
    render(<QuestionStep state={state} dispatch={dispatch} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^배달해요/ }));
    fireEvent.change(screen.getByLabelText(/가게 주소/), { target: { value: "부산 해운대구 우동" } });
    fireEvent.click(screen.getByRole("button", { name: "다음" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.adset.location", value: "가게 주변 5km · 부산 해운대구 우동" });
  });

  it("다시 고르기 goes back to the three ways", () => {
    render(<QuestionStep state={state} dispatch={() => {}} fields={FIELDS} defaults={[]} />);
    fireEvent.click(screen.getByRole("button", { name: /^배달해요/ }));
    fireEvent.click(screen.getByRole("button", { name: "← 다시 고르기" }));
    expect(screen.getByRole("button", { name: /^택배로 보내요/ })).toBeTruthy();
  });
});

describe("unanswer", () => {
  it("removes one answer", async () => {
    const { reduce } = await import("../lib/flow");
    const s = reduce({ ...initialState(), answers: { a: "1", b: "2" } }, { type: "unanswer", id: "b" });
    expect(s.answers).toEqual({ a: "1" });
  });
});
