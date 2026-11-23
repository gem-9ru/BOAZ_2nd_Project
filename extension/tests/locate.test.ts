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
