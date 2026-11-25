import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { isKorean, locate } from "../entrypoints/adsmanager.content/locate";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import type { GuideStepItem } from "../lib/guide";

const html = readFileSync(resolve(__dirname, "fixtures/adset.html"), "utf8");

beforeEach(() => {
  document.documentElement.innerHTML = html;
  document.documentElement.lang = "ko";
});

describe("locate", () => {
  it("finds an input by aria-label", () => {
    expect(locate(document, [{ aria: "위치" }])?.getAttribute("aria-label")).toBe("위치");
  });
  it("finds the input next to label text '연령'", () => {
    expect(locate(document, [{ labelText: "연령" }])?.id).toBe("age-min");
  });
  it("finds by placeholder and by role+text", () => {
    expect(locate(document, [{ placeholder: "웹사이트 URL 입력" }])?.tagName).toBe("INPUT");
    expect(locate(document, [{ role: "button", text: "게시" }])?.textContent).toBe("게시");
  });
  it("tries strategies in order and returns null when nothing matches", () => {
    expect(locate(document, [{ aria: "없는 칸" }, { labelText: "연령" }])?.id).toBe("age-min");
    expect(locate(document, [{ aria: "없는 칸" }])).toBeNull();
  });
  it("isKorean reads the page language", () => {
    expect(isKorean(document)).toBe(true);
    document.documentElement.lang = "en";
    expect(isKorean(document)).toBe(false);
  });
});

function step(id: string, find: GuideStepItem["entry"]["find"], extra: Partial<GuideStepItem["entry"]> = {}, value?: string): GuideStepItem {
  return {
    entry: { id, mode: "create", page: {}, find, say: "여기에 {value}을(를) 넣으세요", done: "value",
             fallback: { image: "guide/placeholder.png", text: `'${id}' 칸을 찾아 주세요` }, ...extra },
    value,
  };
}

describe("Guide runner", () => {
  it("first bubble asks to switch language when the page is not Korean", () => {
    document.documentElement.lang = "en";
    const g = new Guide(document, [step("a", [{ aria: "위치" }])], 0, () => {});
    expect(g.view().text).toContain("화면 언어를 한국어로 바꿔 주세요");
  });

  it("shows the value bubble on the found element and advances on change", () => {
    const seen: number[] = [];
    const g = new Guide(document, [step("age", [{ labelText: "연령" }], {}, "30–39세"), step("loc", [{ aria: "위치" }])], 0, (i) => seen.push(i));
    expect(g.view()).toMatchObject({ found: true, text: "여기에 30–39세을(를) 넣으세요", copy: "30–39세" });
    document.getElementById("age-min")!.dispatchEvent(new Event("change", { bubbles: true }));
    expect(seen).toEqual([1]);
    expect(g.view().found).toBe(true);
  });

  it("falls back to the screenshot text after retries when the element is missing", () => {
    const g = new Guide(document, [step("missing", [{ aria: "없는 칸" }])], 0, () => {}, 0);
    g.retryNow(); g.retryNow(); g.retryNow();
    expect(g.view()).toMatchObject({ found: false, text: "'missing' 칸을 찾아 주세요", image: "guide/placeholder.png" });
  });

  it("never clicks the publish button", () => {
    let clicks = 0;
    const btn = locate(document, [{ role: "button", text: "게시" }])!;
    btn.addEventListener("click", () => clicks++);
    const g = new Guide(document, [step("meta.publish", [{ role: "button", text: "게시" }], { publish: true, done: "manual" })], 0, () => {});
    expect(g.view()).toMatchObject({ found: true, publish: true });
    g.markDone();
    expect(clicks).toBe(0);
  });
});

describe("locate on real Ads Manager markup (2026-11-22)", () => {
  beforeEach(() => {
    document.body.innerHTML = `
      <span id="l1">트래픽</span><input type="radio" aria-labelledby="l1">
      <span id="l2">웹사이트 URL</span><input id="url" type="text" aria-labelledby="l2 extra"><span id="extra">설명</span>
      <div role="button">연령18 - 65+</div>
      <div role="heading">크리에이티브 테스트​</div>
      <div role="button">만들기​</div>`;
  });
  it("finds a field by its aria-labelledby text", () => {
    expect(locate(document, [{ labelledBy: "트래픽" }])?.getAttribute("type")).toBe("radio");
    expect(locate(document, [{ labelledBy: "웹사이트 URL" }])?.id).toBe("url");
  });
  it("finds a summary button by the start of its text", () => {
    expect(locate(document, [{ role: "button", textStarts: "연령" }])?.textContent).toBe("연령18 - 65+");
  });
  it("finds a section heading and ignores zero-width spaces", () => {
    expect(locate(document, [{ heading: "크리에이티브 테스트" }])?.getAttribute("role")).toBe("heading");
    expect(locate(document, [{ role: "button", text: "만들기" }])).not.toBeNull();
  });
});

describe("Guide runner with a hint step", () => {
  it("points at the hint first, then moves to the real field when it appears", () => {
    document.body.innerHTML = `<div role="button">만들기</div>`;
    const item = step("meta.campaign.objective", [
      { labelledBy: "트래픽" },
      { role: "button", text: "만들기", say: "먼저 '+ 만들기'를 누르세요" },
    ], {}, "트래픽");
    const progress: number[] = [];
    const g = new Guide(document, [item], 0, (i) => progress.push(i), 0);
    expect(g.view().text).toBe("먼저 '+ 만들기'를 누르세요");
    g.view().target!.dispatchEvent(new Event("change"));
    expect(progress).toEqual([]);   // 힌트에서는 다음 단계로 넘어가지 않는다
    document.body.insertAdjacentHTML("beforeend", `<span id="t">트래픽</span><input type="radio" aria-labelledby="t">`);
    g.tick();
    expect(g.view().text).toBe("여기에 트래픽을(를) 넣으세요");
    g.view().target!.dispatchEvent(new Event("change"));
    expect(progress).toEqual([1]);
  });
});

describe("locate prefers what is on screen", () => {
  it("skips a hidden copy with the same text", () => {
    document.body.innerHTML = `<div role="heading" id="h1">대표 계정</div><div role="heading" id="h2">대표 계정</div>`;
    const [a, b] = [document.getElementById("h1")!, document.getElementById("h2")!];
    a.getClientRects = () => ([] as unknown as DOMRectList);
    b.getClientRects = () => ([{ width: 100, height: 20 }] as unknown as DOMRectList);
    expect(locate(document, [{ heading: "대표 계정" }])?.id).toBe("h2");
  });
});

describe("reveal", () => {
  it("scrolls the nearest drawn ancestor when the field itself is not drawn yet (Meta draws far sections lazily)", async () => {
    const { reveal } = await import("../entrypoints/adsmanager.content/locate");
    document.body.innerHTML = `<div id="sec"><div><input id="f"></div></div>`;
    const sec = document.getElementById("sec")!, f = document.getElementById("f")!, mid = f.parentElement!;
    const drawn = [{ width: 10, height: 10 }] as unknown as DOMRectList, none = [] as unknown as DOMRectList;
    f.getClientRects = () => none; mid.getClientRects = () => none; sec.getClientRects = () => drawn;
    sec.scrollIntoView = vi.fn(); f.scrollIntoView = vi.fn();
    expect(reveal(f)).toBe(false);
    expect(sec.scrollIntoView).toHaveBeenCalled();
    f.getClientRects = () => drawn;
    expect(reveal(f)).toBe(true);
    expect(f.scrollIntoView).toHaveBeenCalled();
  });
});

describe("button-like links", () => {
  it("'설정 표시' is a plain <a> on Ads Manager but counts as a button", () => {
    document.body.innerHTML = `<a><span>설정 표시</span></a>`;
    expect(locate(document, [{ role: "button", text: "설정 표시" }])?.tagName).toBe("A");
  });
});

describe("준비 안내(hint)는 단계를 끝내지 않는다", () => {
  beforeEach(() => { document.documentElement.lang = "ko"; document.body.innerHTML = `<div role="button">만들기</div>`; });
  it("view marks a hint, and recheck() finds the real field without advancing", () => {
    const seen: number[] = [];
    const g = new Guide(document, [step("meta.campaign.objective", [{ labelledBy: "트래픽" }, { role: "button", text: "만들기", say: "먼저 '+ 만들기'를 누르세요" }])], 0, (i) => seen.push(i), 0);
    expect(g.view()).toMatchObject({ found: true, hint: true, text: "먼저 '+ 만들기'를 누르세요" });
    document.body.insertAdjacentHTML("beforeend", `<span id="t">트래픽</span><input type="radio" aria-labelledby="t">`);
    g.recheck();
    expect(g.view()).toMatchObject({ found: true, hint: false, index: 0 });
    expect(seen).toEqual([]);
  });
});

describe("[다음 칸] = 페이지에서 대신 고르기·넣기·누르기 (게시는 절대 안 함)", () => {
  beforeEach(() => { document.documentElement.lang = "ko"; });

  it("a hint button ('+ 만들기') is clicked for the owner, without finishing the step", () => {
    document.body.innerHTML = `<div role="button" id="b">만들기</div>`;
    let clicked = 0;
    document.getElementById("b")!.addEventListener("click", () => clicked++);
    const seen: number[] = [];
    const g = new Guide(document, [step("meta.campaign.objective", [{ labelledBy: "트래픽" }, { role: "button", text: "만들기", say: "먼저 '+ 만들기'를 누르세요" }], {}, "트래픽")], 0, (i) => seen.push(i), 0);
    g.apply();
    expect(clicked).toBe(1);
    expect(seen).toEqual([]);
  });

  it("a choice (트래픽 radio) is picked and the step moves on", () => {
    document.body.innerHTML = `<span id="t">트래픽</span><input type="radio" name="o" aria-labelledby="t">`;
    const seen: number[] = [];
    const g = new Guide(document, [step("meta.campaign.objective", [{ labelledBy: "트래픽" }], {}, "트래픽"), step("next", [{ aria: "없음" }])], 0, (i) => seen.push(i), 0);
    g.apply();
    expect((document.querySelector("input") as HTMLInputElement).checked).toBe(true);
    expect(seen).toEqual([1]);
  });

  it("a text field gets the value typed in (React가 알아채게 input·change 이벤트) and moves on", () => {
    document.body.innerHTML = `<input id="u" aria-label="웹사이트 URL">`;
    const u = document.getElementById("u") as HTMLInputElement;
    const events: string[] = [];
    u.addEventListener("input", () => events.push("input"));
    const seen: number[] = [];
    const g = new Guide(document, [step("meta.ad.website_url", [{ aria: "웹사이트 URL" }], {}, "https://shop.example"), step("next", [{ aria: "없음" }])], 0, (i) => seen.push(i), 0);
    g.apply();
    expect(u.value).toBe("https://shop.example");
    expect(events).toContain("input");
    expect(seen).toEqual([1]);
  });

  it("never clicks a publish button, even through [다음 칸]", () => {
    document.body.innerHTML = `<div role="button" id="p">동의하고 게시</div>`;
    let clicks = 0;
    document.getElementById("p")!.addEventListener("click", () => clicks++);
    const g = new Guide(document, [step("meta.publish", [{ role: "button", text: "동의하고 게시" }], { publish: true, done: "manual" })], 0, () => {}, 0);
    g.apply();
    expect(clicks).toBe(0);
  });

  it("never clicks a hint button whose text is about publishing", () => {
    document.body.innerHTML = `<div role="button" id="p">검토 후 게시</div>`;
    let clicks = 0;
    document.getElementById("p")!.addEventListener("click", () => clicks++);
    const g = new Guide(document, [step("x", [{ aria: "없음" }, { role: "button", text: "검토 후 게시", say: "눌러요" }])], 0, () => {}, 0);
    g.apply();
    expect(clicks).toBe(0);
  });
});

describe("자동 진행 (창 넘기기 · 칸 채우기 · 스크롤하며 찾기)", () => {
  beforeEach(() => { document.documentElement.lang = "ko"; });
  const at = (s: Partial<GuideStepItem["entry"]>) => s;

  it("finds the real age field, not the '연령 및 성별 타게팅 정보' help link", () => {
    document.body.innerHTML = `<a href="#">연령 및 성별 타게팅 정보</a><div role="button" id="age">연령18 - 65+</div>`;
    expect(locate(document, [{ role: "button", textPattern: "^연령\\d" }])?.id).toBe("age");
  });

  it("walks a whole screen by itself: clicks the hint, picks the choice, types the text", () => {
    document.body.innerHTML = `<div role="button" id="mk">만들기</div>`;
    document.getElementById("mk")!.addEventListener("click", () => {
      document.body.insertAdjacentHTML("beforeend", `<span id="t">트래픽</span><input type="radio" id="r" aria-labelledby="t"><input id="u" aria-label="웹사이트 URL">`);
    });
    const seen: number[] = [];
    const g = new Guide(document, [
      step("meta.campaign.objective", [{ labelledBy: "트래픽" }, { role: "button", text: "만들기", say: "만들기" }], at({ auto: "click" }), "트래픽"),
      step("meta.ad.website_url", [{ aria: "웹사이트 URL" }], at({ auto: "type" }), "https://shop.example"),
      step("next", [{ aria: "없음" }], at({ auto: "owner" })),
    ], 0, (i) => seen.push(i), 0);
    g.setAuto(true);
    let now = 0;
    for (let i = 0; i < 12; i++) { now += 3000; g.tick(); g.autoStep(now); }
    expect((document.getElementById("r") as HTMLInputElement).checked).toBe(true);
    expect((document.getElementById("u") as HTMLInputElement).value).toBe("https://shop.example");
    expect(seen).toEqual([1, 2]);
  });

  it("stops for fields the owner must set (날짜·지역·연령·사진) and goes on after [다 했어요]", () => {
    document.body.innerHTML = `<div role="button" id="loc">위치포함된 위치:대한민국</div>`;
    const seen: number[] = [];
    const g = new Guide(document, [step("meta.adset.location", [{ role: "button", textStarts: "위치" }], at({ auto: "owner", done: "manual" }), "전국"), step("x", [{ aria: "없음" }])], 0, (i) => seen.push(i), 0);
    g.setAuto(true);
    g.autoStep(5000);
    expect(g.view()).toMatchObject({ waiting: "owner", index: 0 });
    g.apply();
    expect(seen).toEqual([1]);
    expect(g.view().auto).toBe(true);
  });

  it("stops before publishing and never clicks it", () => {
    document.body.innerHTML = `<div role="button" id="p">동의하고 게시</div>`;
    let clicks = 0;
    document.getElementById("p")!.addEventListener("click", () => clicks++);
    const g = new Guide(document, [step("meta.publish", [{ role: "button", text: "동의하고 게시" }], at({ publish: true, auto: "stop", done: "manual" }))], 0, () => {}, 0);
    g.setAuto(true);
    for (let t = 0; t < 10; t++) g.autoStep(t * 3000);
    expect(clicks).toBe(0);
    expect(g.view()).toMatchObject({ waiting: "publish", auto: false });
  });

  it("scrolls the editor down to find a field Meta hasn't drawn yet, before using a '다음' hint", () => {
    document.body.innerHTML = `<div id="sc" style="overflow-y:auto"><div role="button" id="nx">다음</div></div>`;
    const sc = document.getElementById("sc")!;
    Object.defineProperty(sc, "clientHeight", { value: 1000 });
    Object.defineProperty(sc, "scrollHeight", { value: 3000 });
    let nextClicks = 0;
    document.getElementById("nx")!.addEventListener("click", () => nextClicks++);
    sc.addEventListener("scroll", () => {
      if (sc.scrollTop >= 1200 && !document.getElementById("loc")) sc.insertAdjacentHTML("afterbegin", `<div role="button" id="loc">위치포함된 위치:대한민국</div>`);
    });
    const g = new Guide(document, [step("meta.adset.location", [{ role: "button", textStarts: "위치" }, { role: "button", text: "다음", say: "다음" }], at({ auto: "owner", done: "manual" })), step("y", [{ aria: "없음" }])], 0, () => {}, 0);
    g.setAuto(true);
    let now = 0;
    for (let i = 0; i < 6; i++) { now += 3000; g.autoStep(now); sc.dispatchEvent(new Event("scroll")); g.tick(); }
    expect(sc.scrollTop).toBeGreaterThan(0);
    expect(nextClicks).toBe(0);
    expect(g.view().target?.id).toBe("loc");
  });
});

describe("이미 고른 준비 선택지는 건너뛴다", () => {
  it("'수동 트래픽 캠페인' is already picked → [다음 칸] presses '계속' instead of picking it again", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<label><span>수동 트래픽 캠페인</span><input type="radio" checked></label><div role="button" id="go">계속</div>`;
    let go = 0;
    document.getElementById("go")!.addEventListener("click", () => go++);
    const g = new Guide(document, [step("meta.campaign.special_category", [{ labelledBy: "카테고리" }, { labelText: "수동 트래픽 캠페인", say: "고르고 계속" }, { role: "button", text: "계속", say: "계속" }], { auto: "skip", done: "manual" })], 0, () => {}, 0);
    g.apply();
    expect(go).toBe(1);
  });
});

import { currentLevel, goToLevel } from "../entrypoints/adsmanager.content/locate";

describe("화면 넘나들며 찾기 (캠페인 · 광고 세트 · 광고)", () => {
  const EDIT = "/adsmanager/manage/{l}/edit/standalone";
  const tree = () => {
    document.body.innerHTML = `<div role="grid">
      <div role="row"><div role="rowheader" aria-label="캠페인" tabindex="0">새 트래픽 캠페인</div></div>
      <div role="row"><div role="rowheader" aria-label="광고 세트" tabindex="0">새 트래픽 광고 세트</div></div>
      <div role="row"><div role="rowheader" aria-label="광고" tabindex="0">새 트래픽 광고</div></div></div>`;
    for (const [name, l] of [["캠페인", "campaigns"], ["광고 세트", "adsets"], ["광고", "ads"]] as const) {
      document.querySelector(`[aria-label="${name}"]`)!.addEventListener("click", () => {
        history.pushState({}, "", EDIT.replace("{l}", l));
        document.querySelectorAll(".page").forEach((e) => e.remove());
        if (l === "adsets") document.body.insertAdjacentHTML("beforeend", `<div class="page"><div role="button" id="loc">위치포함된 위치:대한민국</div></div>`);
        if (l === "ads") document.body.insertAdjacentHTML("beforeend", `<div class="page"><input id="url" aria-label="웹사이트 URL"></div>`);
      });
    }
  };
  beforeEach(() => { document.documentElement.lang = "ko"; history.pushState({}, "", "/"); });

  it("knows which screen it is on from the address", () => {
    expect(currentLevel(document)).toBe("list");
    history.pushState({}, "", EDIT.replace("{l}", "adsets"));
    expect(currentLevel(document)).toBe("adset");
  });

  it("moves through the editor's left list (same page, no reload)", () => {
    tree();
    history.pushState({}, "", EDIT.replace("{l}", "campaigns"));
    expect(goToLevel(document, "ad")).toBe(true);
    expect(currentLevel(document)).toBe("ad");
  });

  it("auto: a field on another screen → goes there and finds it", () => {
    tree();
    history.pushState({}, "", EDIT.replace("{l}", "campaigns"));
    const g = new Guide(document, [step("meta.ad.website_url", [{ aria: "웹사이트 URL" }], { auto: "type", level: "ad" }, "https://shop.example"), step("z", [{ aria: "없음" }])], 0, () => {}, 0);
    g.skipSurvey();   // 지도 없이 넘나들기만 확인
    g.setAuto(true);
    let now = 0;
    for (let i = 0; i < 4; i++) { now += 3000; g.autoStep(now); g.tick(); }
    expect(currentLevel(document)).toBe("ad");
    expect((document.getElementById("url") as HTMLInputElement).value).toBe("https://shop.example");
  });

  it("[이전 칸] back to a field on the previous screen goes back there too", () => {
    tree();
    history.pushState({}, "", EDIT.replace("{l}", "ads"));
    document.querySelector<HTMLElement>('[aria-label="광고"]')!.click();
    const g = new Guide(document, [step("meta.adset.location", [{ role: "button", textStarts: "위치" }], { auto: "owner", level: "adset" }), step("meta.ad.website_url", [{ aria: "웹사이트 URL" }], { auto: "type", level: "ad" })], 1, () => {}, 0);
    g.back();
    expect(currentLevel(document)).toBe("adset");
    g.tick();
    expect(g.view().target?.id).toBe("loc");
  });
});

describe("복잡한 칸도 대신 맞춘다 (종료 날짜)", () => {
  it("auto: end date is typed by 뭉치 and the guide moves on without stopping", async () => {
    document.documentElement.lang = "ko";
    history.pushState({}, "", "/");
    document.body.innerHTML = `<span id="l">종료 날짜 설정</span><input type="checkbox" id="cb" aria-labelledby="l"><input placeholder="yyyy-mm-dd" id="end">`;
    const seen: number[] = [];
    const g = new Guide(document, [step("meta.adset.end_date", [{ labelledBy: "종료 날짜 설정" }], { auto: "endDate", done: "manual" }, "2026-12-09"), step("n", [{ aria: "없음" }])], 0, (i) => seen.push(i), 0);
    g.setAuto(true);
    g.autoStep(5000);   // 먼저 가리켜 보여 주고
    g.autoStep(9000);   // 그다음 대신 넣기
    await new Promise((r) => setTimeout(r, 2000));
    expect((document.getElementById("end") as HTMLInputElement).value).toBe("2026-12-09");
    expect(seen).toEqual([1]);
    expect(g.view().waiting).toBeUndefined();
  });
});

describe("[다 했어요]는 다시 시도하지 않는다", () => {
  it("after a failed auto fill, the owner's [다 했어요] just moves on", async () => {
    document.documentElement.lang = "ko";
    history.pushState({}, "", "/");
    document.body.innerHTML = `<div role="button" id="age">연령18 - 65+</div>`;
    const seen: number[] = [];
    const g = new Guide(document, [step("meta.adset.age_gender", [{ role: "button", textPattern: "^연령\\d" }], { auto: "ageGender" }, "30–39세 · 여성"), step("n", [{ aria: "없음" }])], 0, (i) => seen.push(i), 0);
    g.setAuto(true);
    g.autoStep(5000);
    g.autoStep(9000);
    await new Promise((r) => setTimeout(r, 3500));
    expect(g.view().waiting).toBe("owner");
    g.apply();
    expect(seen).toEqual([1]);
  }, 8000);
});

describe("칸 위치 지도: 처음에 세 화면을 훑어 두고 바로 점프", () => {
  const EDIT = "/adsmanager/manage/{l}/edit/standalone";
  const setup = () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="grid">
      <div role="row"><div role="rowheader" aria-label="캠페인">c</div></div>
      <div role="row"><div role="rowheader" aria-label="광고 세트">s</div></div>
      <div role="row"><div role="rowheader" aria-label="광고">a</div></div></div>
      <div id="sc" style="overflow-y:auto"></div>`;
    const sc = document.getElementById("sc")!;
    Object.defineProperty(sc, "clientHeight", { value: 1000 });
    Object.defineProperty(sc, "scrollHeight", { value: 3000 });
    const draw = () => {
      sc.innerHTML = "";
      const l = currentLevel(document);
      if (l === "adset" && sc.scrollTop >= 1200) sc.innerHTML = `<div role="button" id="loc">위치포함된 위치:대한민국</div>`;
      if (l === "ad") sc.innerHTML = `<input id="url" aria-label="웹사이트 URL">`;
    };
    sc.addEventListener("scroll", draw);
    for (const [name, l] of [["캠페인", "campaigns"], ["광고 세트", "adsets"], ["광고", "ads"]] as const)
      document.querySelector(`[aria-label="${name}"]`)!.addEventListener("click", () => { history.pushState({}, "", EDIT.replace("{l}", l)); sc.scrollTop = 0; draw(); });
    history.pushState({}, "", EDIT.replace("{l}", "campaigns"));
    return sc;
  };
  const steps = () => [
    step("meta.adset.location", [{ role: "button", textStarts: "위치" }], { auto: "owner", level: "adset" }),
    step("meta.ad.website_url", [{ aria: "웹사이트 URL" }], { auto: "type", level: "ad" }, "https://shop.example"),
  ];

  it("surveys campaign → ad set → ad and remembers where each field is", async () => {
    setup();
    const g = new Guide(document, steps(), 0, () => {}, 0);
    const map = await g.survey({ wait: () => Promise.resolve() });
    expect(map["meta.adset.location"]).toMatchObject({ level: "adset" });
    expect(map["meta.adset.location"]!.scrollTop).toBeGreaterThanOrEqual(1200);
    expect(map["meta.ad.website_url"]).toMatchObject({ level: "ad", scrollTop: 0 });
  });

  it("with the map, the first auto step jumps straight to the field's height", async () => {
    const sc = setup();
    const g = new Guide(document, steps(), 0, () => {}, 0);
    await g.survey({ wait: () => Promise.resolve() });
    goToLevel(document, "adset");
    g.setAuto(true);
    g.autoStep(10_000);
    expect(sc.scrollTop).toBeGreaterThanOrEqual(1200);
    g.tick();
    expect(g.view().target?.id).toBe("loc");
  });
});

describe("준비 버튼을 끝없이 누르지 않는다", () => {
  beforeEach(() => { document.documentElement.lang = "ko"; history.pushState({}, "", "/"); });

  it("a field the owner must do (사진): opens '크리에이티브 설정' once, then waits", () => {
    document.body.innerHTML = `<div role="button" id="cs">크리에이티브 설정</div>`;
    let clicks = 0;
    document.getElementById("cs")!.addEventListener("click", () => clicks++);
    const g = new Guide(document, [step("meta.ad.media", [{ role: "button", textStarts: "크리에이티브 설정", say: "사진을 고르세요" }], { auto: "owner", done: "manual" })], 0, () => {}, 0);
    g.setAuto(true);
    for (let i = 1; i <= 20; i++) { g.autoStep(i * 3000); g.tick(); }
    expect(clicks).toBe(1);
    expect(g.view().waiting).toBe("owner");
  });

  it("any hint pressed 3 times without progress → stops and hands over", () => {
    document.body.innerHTML = `<div role="button" id="nx">다음</div>`;
    let clicks = 0;
    document.getElementById("nx")!.addEventListener("click", () => clicks++);
    const g = new Guide(document, [step("meta.ad.website_url", [{ aria: "웹사이트 URL" }, { role: "button", text: "다음", say: "다음" }], { auto: "type" }, "https://x")], 0, () => {}, 0);
    g.setAuto(true);
    for (let i = 1; i <= 30; i++) { g.autoStep(i * 3000); g.tick(); }
    expect(clicks).toBe(3);
    expect(g.view().waiting).toBe("owner");
  });
});

describe("열린 창(크리에이티브 설정 등)이 있을 때", () => {
  beforeEach(() => { document.documentElement.lang = "ko"; history.pushState({}, "", "/"); });

  it("finds only inside the open dialog, never the field hidden behind it", () => {
    document.body.innerHTML = `<input id="behind" aria-label="웹사이트 URL">
      <div role="dialog" id="dlg"><div role="button" id="d-next">다음</div></div>`;
    const g = new Guide(document, [step("meta.ad.website_url", [{ aria: "웹사이트 URL" }], { auto: "type" }, "https://x")], 0, () => {}, 0);
    expect(g.view().target).toBeUndefined();
    expect(g.view().text).toMatch(/열린 창/);
  });

  it("auto never surveys, scrolls the page, or presses a hint while a field is behind a dialog", () => {
    document.body.innerHTML = `<input id="behind" aria-label="웹사이트 URL">
      <div role="dialog"><div role="button" id="d-next">다음</div></div>`;
    let presses = 0;
    document.getElementById("d-next")!.addEventListener("click", () => presses++);
    const g = new Guide(document, [step("meta.ad.website_url", [{ aria: "웹사이트 URL" }, { role: "button", text: "다음", say: "다음" }], { auto: "type", level: "ad" }, "https://x")], 0, () => {}, 0);
    g.setAuto(true);
    for (let i = 1; i <= 10; i++) { g.autoStep(i * 5000); g.tick(); }
    expect(presses).toBe(0);
    expect(g.view().waiting).toBe("owner");
  });

  it("ignores a zero-size dialog the page keeps hidden (메타 '알림 기본 설정')", () => {
    document.body.innerHTML = `<div role="button" id="make">만들기</div>
      <div role="dialog" id="hidden-dlg"><span>알림</span><span>기본 설정</span></div>`;
    const box = (w: number, h: number) => () => [{ width: w, height: h, top: 0, left: 0, right: w, bottom: h, x: 0, y: 0, toJSON: () => ({}) }] as unknown as DOMRectList;
    document.body.getClientRects = box(1000, 800);
    document.getElementById("make")!.getClientRects = box(80, 30);
    document.getElementById("hidden-dlg")!.getClientRects = () => [] as unknown as DOMRectList;
    const g = new Guide(document, [step("meta.campaign.objective", [{ labelledBy: "트래픽" }, { role: "button", text: "만들기", say: "먼저 '+ 만들기'를 누르세요" }], { auto: "click", level: "campaign" })], 0, () => {}, 0);
    expect(g.view().target?.id).toBe("make");
    expect(g.view().text).not.toMatch(/열린 창/);
  });

  it("a field inside the dialog is found normally", () => {
    document.body.innerHTML = `<div role="dialog"><span id="h">제목</span><input id="head" aria-labelledby="h"></div>`;
    const g = new Guide(document, [step("meta.creative.copy.headline", [{ labelledBy: "제목" }], { auto: "type" }, "수제 쿠키")], 0, () => {}, 0);
    expect(g.view().target?.id).toBe("head");
  });
});

describe("글 편집기(문구)에 넣기", () => {
  beforeEach(() => { document.documentElement.lang = "ko"; history.pushState({}, "", "/"); });

  it("types into a rich editor and moves on only when the text is really there", async () => {
    document.body.innerHTML = `<div contenteditable="true" role="combobox" aria-label="간단하게 광고를 소개하세요" id="ed"></div>`;
    const seen: number[] = [];
    const g = new Guide(document, [step("meta.creative.copy.text", [{ aria: "간단하게 광고를 소개하세요" }], { auto: "type" }, "바삭한 수제 쿠키"), step("n", [{ aria: "없음" }])], 0, (i) => seen.push(i), 0);
    g.apply();
    await new Promise((r) => setTimeout(r, 1200));
    expect(document.getElementById("ed")!.textContent).toBe("바삭한 수제 쿠키");
    expect(seen).toEqual([1]);
  });

  it("if the editor ignores it, copies the text and asks the owner to paste (⌘V)", async () => {
    document.body.innerHTML = `<div contenteditable="true" aria-label="간단하게 광고를 소개하세요" id="ed"></div>`;
    const ed = document.getElementById("ed")!;
    new MutationObserver(() => { if (ed.textContent) ed.textContent = ""; }).observe(ed, { childList: true, characterData: true, subtree: true });   // 편집기가 받아 주지 않음
    let copied = "";
    Object.assign(navigator, { clipboard: { writeText: (t: string) => { copied = t; return Promise.resolve(); } } });
    const seen: number[] = [];
    const g = new Guide(document, [step("meta.creative.copy.text", [{ aria: "간단하게 광고를 소개하세요" }], { auto: "type" }, "바삭한 수제 쿠키"), step("n", [{ aria: "없음" }])], 0, (i) => seen.push(i), 0);
    g.apply();
    await new Promise((r) => setTimeout(r, 1200));
    expect(seen).toEqual([]);
    expect(copied).toBe("바삭한 수제 쿠키");
    expect(g.view()).toMatchObject({ waiting: "owner" });
    expect(g.view().text).toMatch(/⌘V/);
  });
});
