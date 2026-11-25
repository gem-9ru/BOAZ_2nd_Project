import { beforeEach, describe, expect, it } from "vitest";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { initialState, reduce, type FlowState } from "../lib/flow";
import { loadState, saveState } from "../lib/storage";
import type { Copy, Research, Segment } from "../lib/api";

const research: Research = {
  headline: "쿠키선물세트를 찾는 사람은 30대 여성이 분야 평균의 1.82배",
  keywords: [{ keyword: "수제쿠키", total_qc: 1000 }],
  audience: { keyword: "쿠키선물세트", female: 0.82, ages: { "30": 0.3 }, top_age: "30" },
  fetched: "2026-11-15", source: "cache", notice: null,
};
const copy: Copy = { primary_text: "버터 듬뿍 수제 쿠키", headline: "수제 쿠키" };
const target = { ageMin: 30, ageMax: 39, gender: "female" as const };

function toGuide(): FlowState {
  let s = initialState();
  s = reduce(s, { type: "researched", research });
  s = reduce(s, { type: "confirmTarget", target, keywords: ["수제쿠키"] });
  s = reduce(s, { type: "pickCopy", copy });
  s = reduce(s, { type: "answer", id: "meta.adset.end_date", value: "7일" });
  return reduce(s, { type: "questionsDone", settings: [{ fieldId: "meta.campaign.objective", label: "목표", value: "트래픽" }] });
}

describe("flow", () => {
  beforeEach(() => fakeBrowser.reset());

  it("goes find → copy → questions → guide", () => {
    let s = initialState();
    expect(s.step).toBe("find");
    s = reduce(s, { type: "researched", research });
    expect(s.step).toBe("find");
    s = reduce(s, { type: "confirmTarget", target, keywords: ["수제쿠키"] });
    expect(s.step).toBe("copy");
    s = reduce(s, { type: "pickCopy", copy });
    expect(s.step).toBe("questions");
    const g = toGuide();
    expect(g.step).toBe("guide");
    expect(g.guide).toEqual({ mode: "create", index: 0 });
    expect(g.answers["meta.adset.end_date"]).toBe("7일");
  });

  it("guideDone in create mode goes to wait and clears guide", () => {
    const s = reduce(toGuide(), { type: "guideDone" });
    expect(s.step).toBe("wait");
    expect(s.guide).toBeNull();
  });

  it("planLoaded → plan, startFix → fix with edit guide at 0, guideDone → wait", () => {
    let s = reduce(reduce(toGuide(), { type: "guideDone" }), { type: "startUpload" });
    expect(s.step).toBe("upload");
    s = reduce(s, { type: "planLoaded", plan: { code: "AB23", action: "한 번 더", summary: [], badge: null,
      change: { field_id: "meta.adset.end_date", label: "종료 날짜", new: "7일 더", note: "" } } });
    expect(s.step).toBe("plan");
    s = reduce(s, { type: "startFix" });
    expect(s.step).toBe("fix");
    expect(s.guide).toEqual({ mode: "edit", index: 0 });
    s = reduce(s, { type: "guideDone" });
    expect(s.step).toBe("wait");
  });

  it("guideProgress moves index only while guiding", () => {
    expect(reduce(toGuide(), { type: "guideProgress", index: 4 }).guide?.index).toBe(4);
    expect(reduce(initialState(), { type: "guideProgress", index: 4 }).guide).toBeNull();
  });

  it("guide index survives save/load", async () => {
    await saveState(reduce(toGuide(), { type: "guideProgress", index: 4 }));
    const back = await loadState();
    expect(back.step).toBe("guide");
    expect(back.guide?.index).toBe(4);
  });

  it("loadState with nothing saved is the initial state", async () => {
    expect(await loadState()).toEqual(initialState());
  });

  it("unknown event leaves state unchanged", () => {
    const s = toGuide();
    expect(reduce(s, { type: "bogus" } as never)).toBe(s);
  });

  it("reset returns to initial state", () => {
    expect(reduce(toGuide(), { type: "reset" })).toEqual(initialState());
  });
});

const seg: Segment = { intent: "선물·답례", label: "선물용", keywords: ["쿠키선물"], total_qc: 500, lead: "쿠키선물", audience: null, trend: null, trend_source: null, line: "" };
describe("분야·손님 무리 상태", () => {
  it("pickCategory clears segment", () => {
    const s = reduce({ ...initialState(), segment: seg }, { type: "pickCategory", category: "50000002" });
    expect(s.category).toBe("50000002"); expect(s.segment).toBeUndefined();
  });
  it("pickSegment sets segment", () => expect(reduce(initialState(), { type: "pickSegment", segment: seg }).segment).toEqual(seg));
  it("confirmTarget keeps segment and goes to copy", () => {
    const s = reduce(initialState(), { type: "confirmTarget", target, keywords: ["a"], segment: seg });
    expect(s.segment).toEqual(seg); expect(s.step).toBe("copy");
  });
  it("pickCopy keeps strengths", () => expect(reduce(initialState(), { type: "pickCopy", copy, strengths: ["촉촉"] }).strengths).toEqual(["촉촉"]));
  it("editFind goes back to find", () => expect(reduce({ ...initialState(), step: "copy" }, { type: "editFind" }).step).toBe("find"));
  it("researched clears segment and takes category", () => {
    const s = reduce({ ...initialState(), segment: seg }, { type: "researched", research: { ...research, category: { code: "1", name: "n", guessed: true } } });
    expect(s.segment).toBeUndefined(); expect(s.category).toBe("1");
  });
});
