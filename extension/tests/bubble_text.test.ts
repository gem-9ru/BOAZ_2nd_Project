// 2026-11-26 사용자 "다 작업해줘": 말풍선 글자를 실제 동작·다른 화면과 맞춘다 (출처: 그날 실제 크롬 실행)
import { describe, expect, it } from "vitest";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import { shownDates, type GuideEntry } from "../lib/guide";
import { GUIDE } from "../lib/guideList";

const entry = (id: string) => GUIDE.find((e) => e.mode === "create" && e.id === id)!;

describe("말풍선 글자", () => {
  it("날짜는 다른 화면처럼 '11월 26일' (뭉치가 칸에 넣는 값은 그대로)", () => {
    expect(shownDates("2026-11-26 ~ 2026-12-02")).toBe("11월 26일 ~ 12월 2일");
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<input placeholder="yyyy-mm-dd">`;
    const e: GuideEntry = { id: "d", mode: "create", page: {}, find: [{ placeholder: "yyyy-mm-dd" }], say: "시작 날짜를 {value}(으)로 맞춰요",
      done: "manual", fallback: { image: "", text: "" }, auto: "startDate" };
    const g = new Guide(document, [{ entry: e, value: "2026-11-26" }], 0, () => {}, 0);
    expect(g.view().text).toBe("시작 날짜를 11월 26일(으)로 맞춰요");
  });

  it("특별 광고 카테고리: 자동 진행이면 뭉치가 넘기니 '다음 칸을 누르세요'라고 하지 않는다", () => {
    expect(entry("meta.campaign.special_category").say).not.toContain("'다음 칸'을 누르세요");
  });

  it("전환 위치: 메타 화면의 '웹사이트'를 고르고, 손님이 가는 곳(인스타그램 프로필 등)을 따로 말한다", () => {
    const say = entry("meta.adset.conversion_location").say;
    expect(say).toContain("'웹사이트'");
    expect(say).toMatch(/\{value\}.*주소로 가요/);
  });

  it("페이지·인스타 칸: 이미 골라져 있으면 맞는지만 보면 된다고 말한다", () => {
    for (const id of ["meta.pre.fb_page", "meta.pre.ig_account"]) expect(entry(id).say).toContain("이미 골라져 있으면");
  });
});
