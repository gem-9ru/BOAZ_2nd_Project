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
