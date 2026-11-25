import { render } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Character } from "../entrypoints/adsmanager.content/Character";
import { loadState } from "../lib/storage";

beforeEach(() => fakeBrowser.reset());

describe("old ③ path is gone", () => {
  it("a saved 'result' state from the old upload path moves to code entry", async () => {
    await fakeBrowser.storage.local.set({ "coach.v3.state": { step: "result", result: { status: "hold" }, keywords: [], dropped: [], answers: {}, settings: [], guide: null } });
    const s = await loadState();
    expect(s.step).toBe("upload");
    expect("result" in s).toBe(false);
  });
});

describe("Character", () => {
  it("goes back to a field that Meta stopped drawing after the user scrolled away", () => {
    vi.useFakeTimers();
    document.body.innerHTML = `<div id="sec"><input id="f"></div>`;
    const sec = document.getElementById("sec")!, f = document.getElementById("f")!;
    const drawn = [{ width: 10, height: 10 }] as unknown as DOMRectList, none = [] as unknown as DOMRectList;
    let fieldDrawn = true;
    f.getClientRects = () => (fieldDrawn ? drawn : none);
    sec.getClientRects = () => drawn;
    f.getBoundingClientRect = () => ({ left: 0, top: 0, right: 10, bottom: 10, width: fieldDrawn ? 10 : 0, height: 10 }) as DOMRect;
    f.scrollIntoView = vi.fn(); sec.scrollIntoView = vi.fn();
    render(<Character view={{ index: 0, total: 1, found: true, text: "여기", target: f }} onDone={() => {}} onBack={() => {}} onClose={() => {}} />);
    expect(f.scrollIntoView).toHaveBeenCalledTimes(1);
    fieldDrawn = false;
    vi.advanceTimersByTime(700);
    expect(sec.scrollIntoView).toHaveBeenCalled();
    vi.useRealTimers();
  });
});

describe("뭉치 (3D 캐릭터) on Ads Manager", () => {
  const reduced = (on: boolean) => vi.stubGlobal("matchMedia", (q: string) => ({ matches: on && q.includes("reduce"), addEventListener() {}, removeEventListener() {} }));

  it("comes out from home (top right, next to the side panel) and falls back to 2D without WebGL", () => {
    document.body.innerHTML = "";
    const { container } = render(<Character view={{ index: 0, total: 2, found: false, text: "칸을 찾아 주세요" }} onDone={() => {}} onBack={() => {}} onClose={() => {}} />);
    const m = container.querySelector(".coach-mungchi") as HTMLElement;
    expect(parseFloat(m.style.left)).toBeGreaterThan(window.innerWidth - 120);
    expect(parseFloat(m.style.top)).toBeLessThan(40);
    expect(container.querySelector('[data-character="flat"]')).not.toBeNull();
    expect(container.querySelector('[aria-label="광고 어시스턴트 뭉치"]')).not.toBeNull();
  });

  it("stands beside the field and points at it", () => {
    reduced(true);
    document.body.innerHTML = `<input id="f">`;
    const f = document.getElementById("f")!;
    f.getClientRects = () => [{ width: 200, height: 40 }] as unknown as DOMRectList;
    f.getBoundingClientRect = () => ({ left: 100, top: 300, right: 300, bottom: 340, width: 200, height: 40 }) as DOMRect;
    f.scrollIntoView = vi.fn();
    const { container } = render(<Character view={{ index: 0, total: 1, found: true, text: "여기", target: f }} onDone={() => {}} onBack={() => {}} onClose={() => {}} />);
    const m = container.querySelector(".coach-mungchi") as HTMLElement;
    expect(m.dataset.mode).toBe("point");
    expect(parseFloat(m.style.left)).toBeGreaterThanOrEqual(300);
    vi.unstubAllGlobals();
  });

  it("닫기 walks back home first, then closes", () => {
    reduced(true);
    document.body.innerHTML = "";
    const onClose = vi.fn();
    const { getByRole } = render(<Character view={{ index: 0, total: 1, found: false, text: "x" }} onDone={() => {}} onBack={() => {}} onClose={onClose} />);
    getByRole("button", { name: "안내 닫기" }).click();
    return new Promise<void>((done) => setTimeout(() => { expect(onClose).toHaveBeenCalled(); vi.unstubAllGlobals(); done(); }, 0));
  });
});

describe("준비 안내일 때 말풍선 버튼", () => {
  it("[다음 칸] asks the guide to act (guide.apply clicks the hint button instead of skipping the field)", () => {
    document.body.innerHTML = `<div role="button" id="b">만들기</div>`;
    const b = document.getElementById("b")!;
    b.getClientRects = () => [{ width: 10, height: 10 }] as unknown as DOMRectList;
    b.getBoundingClientRect = () => ({ left: 10, top: 10, right: 80, bottom: 40, width: 70, height: 30 }) as DOMRect;
    b.scrollIntoView = vi.fn();
    const onDone = vi.fn();
    const { getByRole } = render(<Character view={{ index: 0, total: 3, found: true, hint: true, text: "먼저 '+ 만들기'를 누르세요", target: b }}
      onDone={onDone} onBack={() => {}} onClose={() => {}} />);
    getByRole("button", { name: "다음 칸" }).click();
    expect(onDone).toHaveBeenCalled();
  });
});

describe("작은 칸(라디오)은 이름표까지 합쳐 짚는다", () => {
  const box = (l: number, t: number, w: number, h: number) => ({ left: l, top: t, right: l + w, bottom: t + h, width: w, height: h }) as DOMRect;
  it("the ring and 뭉치 cover the radio and its label, and there is no [값 복사] ([다음 칸]이 값을 넣어 줌)", () => {
    vi.stubGlobal("matchMedia", (q: string) => ({ matches: q.includes("reduce"), addEventListener() {}, removeEventListener() {} }));
    document.body.innerHTML = `<input type="radio" id="r" aria-labelledby="l"><span id="l">트래픽</span>`;
    const r = document.getElementById("r")!, l = document.getElementById("l")!;
    for (const el of [r, l]) { el.getClientRects = () => [{ width: 10, height: 10 }] as unknown as DOMRectList; el.scrollIntoView = vi.fn(); }
    r.getBoundingClientRect = () => box(100, 300, 20, 20);
    l.getBoundingClientRect = () => box(130, 298, 60, 24);
    const { container, queryByRole } = render(<Character view={{ index: 0, total: 14, found: true, text: "'트래픽'을 고르세요", target: r, copy: "트래픽" }}
      onDone={() => {}} onBack={() => {}} onClose={() => {}} />);
    const ring = container.querySelector(".coach-ring") as HTMLElement;
    expect(parseFloat(ring.style.width)).toBeGreaterThanOrEqual(90);
    const m = container.querySelector(".coach-mungchi") as HTMLElement;
    expect(parseFloat(m.style.left)).toBeGreaterThanOrEqual(190);
    expect(queryByRole("button", { name: "값 복사" })).toBeNull();
    vi.unstubAllGlobals();
  });
});

describe("자동 진행 버튼", () => {
  const base = { index: 2, total: 14, found: true, text: "위치를 전국으로 맞추세요." };
  it("waiting for the owner shows [다 했어요] and [멈추기]", () => {
    document.body.innerHTML = "";
    const { getByRole } = render(<Character view={{ ...base, auto: true, waiting: "owner" }} onDone={() => {}} onBack={() => {}} onClose={() => {}} onToggleAuto={() => {}} />);
    expect(getByRole("button", { name: "다 했어요" })).toBeTruthy();
    expect(getByRole("button", { name: "멈추기" })).toBeTruthy();
  });
  it("at publish the only way on is [게시했어요] (the owner publishes first)", () => {
    document.body.innerHTML = "";
    const onDone = vi.fn();
    const { queryByRole, getByRole } = render(<Character view={{ ...base, waiting: "publish" }} onDone={onDone} onBack={() => {}} onClose={() => {}} onToggleAuto={() => {}} />);
    expect(queryByRole("button", { name: "다음 칸" })).toBeNull();
    expect(queryByRole("button", { name: "다 했어요" })).toBeNull();
    expect(queryByRole("button", { name: "자동 진행" })).toBeNull();
    getByRole("button", { name: "게시했어요" }).click();
    expect(onDone).toHaveBeenCalled();
  });
});
