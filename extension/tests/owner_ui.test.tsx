// 2026-11-26 사용자 "다 작업해줘": 사장님이 직접 할 칸을 눈에 띄게, 첫 말풍선에 [자동 진행] 안내, 말풍선 UI/UX, 패널 [처음부터]
// 출처: 그날 실제 시연에서 사진 고르기를 놓침 · ui-ux-pro-max(누르는 곳 44px, 대비, 화면 읽기) · UX_설계원칙.md 7장
import { fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import { Character } from "../entrypoints/adsmanager.content/Character";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import { initialState, type FlowState } from "../lib/flow";
import type { GuideEntry } from "../lib/guide";
import { SETTING_ORDER } from "../lib/settings";

const noop = () => {};
const base = { index: 0, total: 3, found: false, text: "여기" };

describe("말풍선: 사장님 차례 표시", () => {
  it("사장님이 직접 할 칸이면 맨 위에 '직접 눌러 주세요' 꼬리표", () => {
    const { container } = render(<Character view={{ ...base, owner: true, waiting: "owner", text: "사진을 직접 골라 주세요" }} onDone={noop} onBack={noop} onClose={noop} />);
    const tag = container.querySelector(".coach-owner")!;
    expect(tag.textContent).toBe("직접 눌러 주세요");
    expect(tag.querySelector("strong")!.textContent).toBe("직접");                       // '직접'만 크게
    expect(container.querySelector(".coach-bubble-owner")).not.toBeNull();               // 두꺼운 테두리
    expect(container.querySelector(".coach-text .coach-direct")!.textContent).toBe("직접");   // 글 속 '직접'도 꼬리표
    expect(screen.getByRole("button", { name: "다 했어요" }).className).toContain("coach-primary-owner");   // 큰 주 버튼
  });
  it("게시 칸이면 '직접 게시해 주세요' + [게시했어요]도 크게", () => {
    const { container } = render(<Character view={{ ...base, publish: true }} onDone={noop} onBack={noop} onClose={noop} />);
    expect(container.querySelector(".coach-owner")!.textContent).toBe("직접 게시해 주세요");
    expect(screen.getByRole("button", { name: "게시했어요" }).className).toContain("coach-primary-owner");
  });
  it("뭉치가 하는 칸이면 꼬리표 없음", () => {
    const { container } = render(<Character view={base} onDone={noop} onBack={noop} onClose={noop} />);
    expect(container.querySelector(".coach-owner")).toBeNull();
    expect(screen.getByRole("button", { name: "다음 칸" }).className).not.toContain("coach-primary-owner");
  });
  it("Guide: auto owner 칸은 자동 진행이 꺼져 있어도 owner로 알린다", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<h2>대표 계정</h2>`;
    const e: GuideEntry = { id: "p", mode: "create", page: {}, find: [{ heading: "대표 계정" }], say: "페이지", done: "manual", fallback: { image: "", text: "" }, auto: "owner" };
    expect(new Guide(document, [{ entry: e }], 0, noop, 0).view().owner).toBe(true);
    expect(new Guide(document, [{ entry: { ...e, auto: "click" } }], 0, noop, 0).view().owner).toBeFalsy();
  });
});

describe("첫 말풍선: [자동 진행] 안내", () => {
  it("첫 칸에서 자동 진행이 꺼져 있으면 한 줄 안내 + 단추 강조", () => {
    render(<Character view={{ ...base, auto: false }} onToggleAuto={noop} onDone={noop} onBack={noop} onClose={noop} />);
    expect(screen.getByText(/\[자동 진행\]을 누르면 뭉치가 칸을 차례로 채워요/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "자동 진행" }).className).toContain("coach-attn");
  });
  it("켜져 있거나 첫 칸이 아니면 안내 없음", () => {
    render(<Character view={{ ...base, index: 1, auto: false }} onToggleAuto={noop} onDone={noop} onBack={noop} onClose={noop} />);
    expect(screen.queryByText(/\[자동 진행\]을 누르면/)).toBeNull();
  });
});

describe("말풍선 UI/UX", () => {
  it("화면 읽기: 바뀌는 안내만 알림 영역 (단추는 밖)", () => {
    render(<Character view={base} onDone={noop} onBack={noop} onClose={noop} />);
    const status = screen.getByRole("status");
    expect(status.textContent).toContain("여기");
    expect(status.querySelector("button")).toBeNull();
  });
  it("단추 높이 44px·걷는 중에도 읽히는 투명도·글자 크기는 토큰으로", () => {
    const css = readFileSync(resolve(__dirname, "../entrypoints/adsmanager.content/overlay.css"), "utf8");
    expect(css).toMatch(/min-height:\s*var\(--coach-button-min-height\)/);
    const tokens = readFileSync(resolve(__dirname, "../assets/overlay-tokens.css"), "utf8");
    expect(tokens).toMatch(/--coach-button-min-height:\s*44px/);
    expect(tokens).toMatch(/--coach-font-size:\s*16px/);
    expect(tokens).toMatch(/--coach-moving-opacity:\s*0?\.85/);
  });
});

describe("패널 안내 목록", () => {
  const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: `칸 ${id}`, value: "v" }));
  const state = (index: number): FlowState => ({ ...initialState(), step: "guide", settings, guide: { mode: "create", index } });
  it("사장님이 직접 할 칸 줄에 '직접' 표시", () => {
    render(<GuideStep state={state(0)} dispatch={noop} />);
    const page = screen.getAllByRole("listitem").find((li) => li.textContent!.includes("meta.pre.fb_page"))!;
    expect(page.textContent).toContain("직접");
    const budget = screen.getAllByRole("listitem").find((li) => li.textContent!.includes("meta.adset.lifetime_budget"))!;
    expect(budget.textContent).not.toContain("직접");
  });
  it("[1번 칸부터 다시]는 1번 칸으로 되돌린다 (첫 칸이면 없음)", () => {
    const dispatch = vi.fn();
    const { unmount } = render(<GuideStep state={state(9)} dispatch={dispatch} />);
    const b = screen.getByRole("button", { name: "1번 칸부터 다시" });
    expect(b.className).toContain("min-h-11");
    fireEvent.click(b);
    expect(dispatch).toHaveBeenCalledWith({ type: "guideProgress", index: 0 });
    unmount();
    render(<GuideStep state={state(0)} dispatch={noop} />);
    expect(screen.queryByRole("button", { name: "1번 칸부터 다시" })).toBeNull();
  });
});

describe("사장님 차례면 뭉치는 가리키기 대신 손을 흔들며 기다린다", () => {
  function field() {
    document.body.innerHTML = `<input id="f">`;
    const f = document.getElementById("f")!;
    f.getClientRects = () => [{ width: 200, height: 40 }] as unknown as DOMRectList;
    f.getBoundingClientRect = () => ({ left: 100, top: 300, right: 300, bottom: 340, width: 200, height: 40 }) as DOMRect;
    f.scrollIntoView = vi.fn();
    return f;
  }
  const reduce = () => vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("reduce"), addEventListener: noop, removeEventListener: noop }));
  it("기다리는 중(owner)이면 wave, 아니면 point", () => {
    reduce();
    const f = field();
    const { container, rerender } = render(<Character view={{ ...base, found: true, target: f, owner: true, waiting: "owner" }} onDone={noop} onBack={noop} onClose={noop} />);
    expect(container.ownerDocument.querySelector(".coach-mungchi")!.getAttribute("data-mode")).toBe("wave");
    rerender(<Character view={{ ...base, found: true, target: f }} onDone={noop} onBack={noop} onClose={noop} />);
    expect(container.ownerDocument.querySelector(".coach-mungchi")!.getAttribute("data-mode")).toBe("point");
    vi.unstubAllGlobals();
  });
});
