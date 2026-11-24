import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

// v4 7장: 확장 프로그램과 분석 페이지가 같은 색을 써야 한 서비스로 보인다.
// 색의 단일 원천은 design-system/tokens.json 이고, node design-system/build.cjs 가 두 앱의 CSS를 만든다.
const root = resolve(__dirname, "../..");
const read = (p: string) => readFileSync(resolve(root, p), "utf8");
const tokens = JSON.parse(read("design-system/tokens.json"));
const themeCss = read("extension/assets/tokens.css").toLowerCase();
const overlayCss = read("extension/assets/overlay-tokens.css").toLowerCase();
const webCss = read("web/src/tokens.css").toLowerCase();

/** "{semantic.tone.accent}" 같은 참조를 끝까지 따라간다. */
function value(ref: string): string {
  let node = tokens;
  for (const k of ref.replace(/^\{|\}$/g, "").split(".")) node = node[k];
  const v: string = node.$value;
  return v.startsWith("{") ? value(v) : v.toLowerCase();
}

describe("확장과 분석 페이지 색 (design-system/tokens.json)", () => {
  it.each([
    ["accent", "accent"],
    ["accent-ink", "accent-ink"],
    ["accent-soft", "accent-soft"],
    ["ink", "ink"],
    ["soft", "ink-soft"],
    ["cream", "bg"],
    ["paper", "surface"],
    ["block", "block"],
    ["warn", "warn"],
    ["warn-mark", "warn-mark"],
    ["info", "info"],
    ["ok", "ok"],
  ])("확장 --color-%s 와 분석 페이지 --tone-%s 가 같다", (ext, tone) => {
    const hex = value(`semantic.tone.${tone}`);
    expect(themeCss).toContain(`--color-${ext}: ${hex};`);
    expect(webCss).toContain(`--tone-${tone}: ${hex};`);
  });

  it("v4 회의 색이 원천에 그대로 있다", () => {
    expect(value("semantic.tone.accent")).toBe("#5b3fd9");
    expect(value("semantic.tone.action-hover")).toBe("#4528b0");
    expect(value("semantic.tone.accent-soft")).toBe("#efebff");
    expect([value("semantic.tone.block"), value("semantic.tone.warn-mark"), value("semantic.tone.info"), value("semantic.tone.ok")])
      .toEqual(["#d93025", "#e8710a", "#1a73e8", "#1e8e3e"]);
  });

  it("오버레이 테두리·캐릭터도 메인 색 변수를 쓴다", () => {
    expect(overlayCss).toContain(`--coach-ring: ${value("semantic.tone.accent")};`);
    expect(overlayCss).toContain(`--character-body: ${value("semantic.tone.accent")};`);
    const overlay = read("extension/entrypoints/adsmanager.content/overlay.css");
    const character = read("extension/entrypoints/adsmanager.content/Character.tsx");
    expect(overlay).not.toMatch(/#[0-9a-f]{3,6}\b/i);
    expect(character).not.toMatch(/#[0-9a-f]{3,6}\b/i);
  });

  it("생성된 CSS가 원천과 같고 대비 검사를 통과한다 (build.cjs --check)", () => {
    expect(() => execFileSync(process.execPath, [resolve(root, "design-system/build.cjs"), "--check"], { stdio: "pipe" })).not.toThrow();
  });
});
