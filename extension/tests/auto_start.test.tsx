// 2026-11-26 사용자: "바로 자동진행하지 말고, 자동진행 버튼을 처음에 누르면 자동진행되게끔"
// 뭉치를 부르면 첫 칸을 가리킨 채 멈춰 있고, 말풍선의 [자동 진행]을 눌러야 칸을 채우기 시작한다.
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Character } from "../entrypoints/adsmanager.content/Character";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import type { GuideEntry } from "../lib/guide";

const entry: GuideEntry = { id: "x", mode: "create", page: {}, find: [{ aria: "없는 칸" }, { role: "button", text: "만들기", say: "'만들기'를 누를게요" }], say: "칸",
  done: "manual", fallback: { image: "", text: "" }, auto: "click" };

describe("자동 진행은 [자동 진행]을 눌러야 시작", () => {
  it("처음엔 꺼져 있어 아무것도 누르지 않고, 켜면 누른다", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="button" id="b">만들기</div>`;
    let clicks = 0;
    document.getElementById("b")!.addEventListener("click", () => clicks++);
    const g = new Guide(document, [{ entry }], 0, () => {}, 0);
    g.skipSurvey();
    g.followBuddy();   // 콘텐츠 스크립트가 하는 그대로 (setAuto는 부르지 않음)
    for (let i = 1; i <= 10; i++) { g.tick(); g.autoStep(i * 5000); }
    expect(g.view().auto).toBe(false);
    expect(clicks).toBe(0);
    g.setAuto(true);   // [자동 진행]
    g.arrived(document.getElementById("b"), 0);
    for (let i = 11; i <= 20; i++) { g.tick(); g.autoStep(i * 5000); }
    expect(clicks).toBeGreaterThan(0);
  });

  it("말풍선에 [자동 진행] 단추가 보이고, 누르면 켜는 함수를 부른다", () => {
    const toggle = vi.fn();
    render(<Character view={{ index: 0, total: 3, found: false, text: "여기", auto: false }} onToggleAuto={toggle}
      onDone={() => {}} onBack={() => {}} onClose={() => {}} />);
    const b = screen.getByRole("button", { name: "자동 진행" });
    expect(b.getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(b);
    expect(toggle).toHaveBeenCalledOnce();
  });
});
