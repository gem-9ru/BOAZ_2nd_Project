import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
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
