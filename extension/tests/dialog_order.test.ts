// 2026-11-26 시연: 광고 만들기 창은 미디어 → 크리에이티브 설정(소스 URL) → 자르기 → 문구 → 이미지 생성 → 개선 사항 → 완료를
// [다음]으로 차례대로 지나가야 한다. 위쪽 단계 이름을 눌러 건너뛰면 사진 선택이 반영되지 않아 [다음]이 막혔다.
import { describe, expect, it } from "vitest";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import { locateWith } from "../entrypoints/adsmanager.content/locate";
import type { GuideEntry, GuideStepItem } from "../lib/guide";
import { GUIDE } from "../lib/guideList";

const create = GUIDE.filter((e) => e.mode === "create");
const entry = (id: string) => create.find((e) => e.id === id)!;

describe("광고 만들기 창: 단계 건너뛰지 않기", () => {
  it("문구·제목 칸은 위쪽 단계 이름('문구'·'크리에이티브 설정')을 눌러 건너뛰지 않고, 창 안에서는 [다음]으로 간다", () => {
    for (const id of ["meta.creative.copy.text", "meta.creative.copy.headline"]) {
      const hints = entry(id).find.filter((f) => f.say);
      expect(hints.some((f) => "text" in f && f.text === "문구")).toBe(false);
      expect(hints.some((f) => "text" in f && f.text === "다음" && f.inDialog)).toBe(true);
      expect(hints.filter((f) => "textStarts" in f && f.textStarts === "크리에이티브 설정").every((f) => f.pageOnly)).toBe(true);
    }
  });

  it("사진 칸은 '소스 URL' 칸이 보여야(= 사진을 고르고 [다음]을 눌러야) 끝난다. 문구 칸이 보인다고 끝나지 않는다", () => {
    const done = entry("meta.ad.media").doneWhen ?? [];
    expect(done.some((f) => "aria" in f && f.aria === "간단하게 광고를 소개하세요")).toBe(false);
    expect(done.some((f) => "placeholder" in f && f.placeholder === "광고 후 사람들이 방문하는 URL을 입력하세요")).toBe(true);
  });

  it("웹사이트 주소는 사진 바로 다음(크리에이티브 설정 단계)에, 돈 확인은 창을 닫고 한다", () => {
    const ids = create.map((e) => e.id);
    expect(ids.indexOf("meta.ad.website_url")).toBe(ids.indexOf("meta.ad.media") + 1);
    expect(entry("meta.ad.website_url").outsideDialog).toBeFalsy();
    expect(entry("meta.money_check").outsideDialog).toBe(true);
  });

  it("inDialog 힌트는 창 안에서만, pageOnly 힌트는 창이 없을 때만 찾는다", () => {
    document.body.innerHTML = `<div role="button">다음</div><div role="dialog" id="d"><div role="button">다음</div><div role="button">크리에이티브 설정</div></div>`;
    const dlg = document.getElementById("d")!;
    expect(locateWith(document, [{ role: "button", text: "다음", inDialog: true, say: "x" }])).toBeNull();
    expect(locateWith(dlg, [{ role: "button", text: "다음", inDialog: true, say: "x" }])?.el.parentElement).toBe(dlg);
    expect(locateWith(dlg, [{ role: "button", textStarts: "크리에이티브 설정", pageOnly: true, say: "x" }])).toBeNull();
  });
});

describe("창 마무리: [다 했어요] 뒤 다시 시도", () => {
  it("창 마무리 단추를 다 눌러 보고 멈춘 뒤 사장님이 [다 했어요]를 누르면, 다시 [다음]·[완료]를 눌러 본다", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="dialog" id="dlg"><div role="button" id="n" aria-disabled="true">다음</div></div>`;
    let presses = 0;
    document.getElementById("n")!.addEventListener("click", () => presses++);
    const e: GuideEntry = { id: "meta.money_check", mode: "create", page: { urlIncludes: "" }, find: [{ heading: "예산 및 일정" }], say: "돈 확인",
      done: "manual", fallback: { image: "", text: "" }, auto: "moneyCheck", level: "adset", outsideDialog: true };
    const steps: GuideStepItem[] = [{ entry: e, value: "3만 원" }];
    const g = new Guide(document, steps, 0, () => {}, 0);
    g.skipSurvey();
    g.setAuto(true);
    for (let i = 1; i <= 20; i++) { g.autoStep(i * 5000); g.tick(); }
    const before = presses;
    expect(g.view().waiting).toBe("owner");
    g.apply();   // [다 했어요]
    for (let i = 21; i <= 24; i++) { g.autoStep(i * 5000); g.tick(); }
    expect(presses).toBeGreaterThan(before);
  });
});

describe("접힌 구역 안의 칸 (연령: '타겟 추천' › '설정 표시')", () => {
  it("이 화면을 훑어 봐도 없던 칸이면, 또 끝까지 내려 보지 않고 보이는 '설정 표시'부터 누른다", () => {
    document.documentElement.lang = "ko";
    history.pushState({}, "", "/adsmanager/manage/adsets/edit");
    document.body.innerHTML = `<div id="sc" style="overflow-y:auto"><div role="button" id="show">설정 표시</div></div>`;
    const sc = document.getElementById("sc")!;
    Object.defineProperty(sc, "clientHeight", { value: 1000 });
    Object.defineProperty(sc, "scrollHeight", { value: 3000 });
    let shows = 0;
    document.getElementById("show")!.addEventListener("click", () => shows++);
    const e: GuideEntry = { id: "meta.adset.age_gender", mode: "create", page: { urlIncludes: "" }, say: "연령",
      find: [{ role: "button", textPattern: "^연령\\d" }, { role: "button", text: "설정 표시", say: "'설정 표시'를 눌러 연령 칸을 열게요" }],
      done: "manual", fallback: { image: "", text: "" }, auto: "ageGender", level: "adset" };
    const g = new Guide(document, [{ entry: e, value: "30~59세 · 여성" }], 0, () => {}, 0);
    g.skipSurvey();
    (g as unknown as { surveyedLevels: Set<string> }).surveyedLevels.add("adset");   // 광고 세트 화면은 이미 끝까지 훑음 (지도에 연령 없음)
    g.setAuto(true);
    g.autoStep(5000);   // 첫 걸음에 바로 누른다 (예전엔 화면을 끝까지 두 번 내려 본 뒤에야 눌렀다)
    expect(shows).toBe(1);
    expect(sc.scrollTop).toBe(0);
  });
});
