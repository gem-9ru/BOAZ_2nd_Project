import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import QuestionStep from "../entrypoints/sidepanel/steps/QuestionStep";
import { initialState, type FlowState } from "../lib/flow";
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
