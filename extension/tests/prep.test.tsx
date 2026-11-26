import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import PrepStep from "../entrypoints/sidepanel/steps/PrepStep";
import type { Field } from "../lib/api";
import { initialState, reduce } from "../lib/flow";
import { askedFields, prepFields, prepMissing, SETTING_ORDER } from "../lib/settings";

const pre = (id: string, label: string, options: string[], required = false): Field =>
  ({ id, kind: "precheck", label, ask: `${label}?`, options, default: options[0]!, why: "이유", stage: "사전 점검", required });
const PREP: Field[] = [
  pre("meta.pre.fb_login", "페이스북 개인 계정", ["로그인할 수 있어요", "계정이 없어요"], true),
  pre("meta.pre.fb_page", "페이스북 페이지", ["있어요", "없어요"], true),
  pre("meta.pre.payment", "결제 수단", ["등록했어요", "아직이에요"], true),
  pre("meta.pre.media", "광고 사진·영상", ["있어요", "아직이에요"]),
];
const QUESTION: Field = { id: "meta.adset.end_date", kind: "question", label: "종료 날짜", ask: "언제까지?", options: ["7일"], default: "7일", why: "" };

describe("시작 전 준비물: 어떤 칸인가", () => {
  it("'사전 점검' 칸은 준비물 화면에서 묻고 ② 세팅에서는 다시 묻지 않는다", () => {
    expect(prepFields([...PREP, QUESTION]).map((f) => f.id)).toEqual(PREP.map((f) => f.id));
    expect(askedFields([...PREP, QUESTION]).map((f) => f.id)).toEqual(["meta.adset.end_date"]);
  });

  it("꼭 있어야 하는 칸이 첫 답(있어요 등)이 아니면 빠진 것으로 센다 (안 꼭 필요한 칸은 세지 않음)", () => {
    const answers = { "meta.pre.fb_login": "로그인할 수 있어요", "meta.pre.fb_page": "없어요", "meta.pre.payment": "등록했어요", "meta.pre.media": "아직이에요" };
    expect(prepMissing(PREP, answers)).toEqual(["페이스북 페이지"]);
    expect(prepMissing(PREP, {})).toEqual(["페이스북 개인 계정", "페이스북 페이지", "결제 수단"]);
  });
});

describe("시작 전 준비물: 흐름", () => {
  it("처음 열면 준비물 화면부터, 다 보면 ① 찾기로", () => {
    expect(initialState().step).toBe("prep");
    const s = reduce(initialState(), { type: "prepDone", missing: ["결제 수단"] });
    expect(s.step).toBe("find");
    expect(s.prepMissing).toEqual(["결제 수단"]);
    expect(reduce(s, { type: "openPrep" }).step).toBe("prep");
  });

  it("한 칸씩 묻고, 다 답하면 무엇이 빠졌는지 보여 준 뒤 [시작할게요]로 넘어간다", () => {
    const dispatch = vi.fn();
    const { rerender } = render(<PrepStep state={{ ...initialState() }} dispatch={dispatch} fields={PREP} />);
    expect(screen.getByText(/페이스북 개인 계정\?/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /로그인할 수 있어요/ }));
    expect(dispatch).toHaveBeenCalledWith({ type: "answer", id: "meta.pre.fb_login", value: "로그인할 수 있어요" });

    const answers = { "meta.pre.fb_login": "로그인할 수 있어요", "meta.pre.fb_page": "있어요", "meta.pre.payment": "아직이에요", "meta.pre.media": "있어요" };
    rerender(<PrepStep state={{ ...initialState(), answers }} dispatch={dispatch} fields={PREP} />);
    expect(screen.getByText(/결제 수단은\(는\) 광고 관리자에 들어가기 전에 꼭/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "시작할게요" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "prepDone", missing: ["결제 수단"] });
  });
});

describe("시작 전 준비물: 광고 관리자 열기", () => {
  const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: `칸 ${id}`, value: "v" }));

  it("꼭 있어야 하는 준비물이 빠졌으면 [광고 관리자 열기]를 막고 무엇이 빠졌는지 보여 준다", () => {
    const dispatch = vi.fn();
    render(<GuideStep state={{ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0 }, prepMissing: ["결제 수단"] }} dispatch={dispatch} />);
    expect((screen.getByRole("button", { name: "광고 관리자 열기" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByText(/결제 수단/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "준비물 다시 보기" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "openPrep" });
  });

  it("준비물이 다 됐으면 그대로 열 수 있다", () => {
    render(<GuideStep state={{ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0 }, prepMissing: [] }} dispatch={() => {}} />);
    expect((screen.getByRole("button", { name: "광고 관리자 열기" }) as HTMLButtonElement).disabled).toBe(false);
  });
});
