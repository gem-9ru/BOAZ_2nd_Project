// EX-03 다음 테스트 (v4 5-1장): 광고 관리자에서 바꿀 칸 1개만 밝게, 나머지는 흐리게 + '유지'
import { render, screen, waitFor } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Character } from "../entrypoints/adsmanager.content/Character";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import { initialState, reduce, type FlowState, type Plan } from "../lib/flow";
import { SETTING_ORDER } from "../lib/settings";

vi.mock("../lib/progress", () => ({
  sendWithRetry: async (send: () => Promise<unknown>) => { try { await send(); return true; } catch { return false; } },
}));

beforeEach(() => fakeBrowser.reset());

function field() {
  document.body.innerHTML = `<input id="f">`;
  const f = document.getElementById("f")!;
  f.getClientRects = () => [{ width: 200, height: 40 }] as unknown as DOMRectList;
  f.getBoundingClientRect = () => ({ left: 100, top: 300, right: 300, bottom: 340, width: 200, height: 40 }) as DOMRect;
  f.scrollIntoView = vi.fn();
  return f;
}

describe("EX-03 나머지 칸 흐리게", () => {
  it("the changed field is lit, the rest is dimmed and tagged '그대로 (유지)'", () => {
    const f = field();
    const { container } = render(<Character view={{ index: 0, total: 3, found: true, text: "여기", target: f }} keepOthers
      onDone={() => {}} onBack={() => {}} onClose={() => {}} />);
    expect(container.querySelector(".coach-ring")!.className).toContain("coach-ring-focus");
    expect(screen.getByText("이 칸만 바꿔요 · 나머지 칸은 그대로 (유지)")).toBeTruthy();
    expect(screen.getByText(/나머지 칸은 지난번 그대로 두세요/)).toBeTruthy();
  });

  it("a normal guide run keeps the light dim and no tag", () => {
    const f = field();
    const { container } = render(<Character view={{ index: 0, total: 3, found: true, text: "여기", target: f }}
      onDone={() => {}} onBack={() => {}} onClose={() => {}} />);
    expect(container.querySelector(".coach-ring")!.className).not.toContain("coach-ring-focus");
    expect(screen.queryByText(/나머지 칸은 그대로/)).toBeNull();
  });

  it("[다음 테스트 세팅] asks the character to focus; a first-time setup does not", async () => {
    const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: `칸 ${id}`, value: "지난 값" }));
    const plan = { code: "AB12", change: { field_id: "meta.ad.media", label: "형식·미디어", new: "+ 세로(9:16) 1개", note: "" } } as unknown as Plan;
    const send = vi.spyOn(fakeBrowser.tabs, "sendMessage").mockResolvedValue(true as never);
    vi.spyOn(fakeBrowser.tabs, "query").mockResolvedValue([{ id: 7, active: true, url: "https://adsmanager.facebook.com/x" }] as never);

    const next: FlowState = reduce({ ...initialState(), step: "plan", plan, settings },
      { type: "startNextTest", fieldId: "meta.ad.media", label: "형식·미디어", value: "+ 세로(9:16) 1개" });
    const a = render(<GuideStep state={next} dispatch={() => {}} />);
    screen.getByRole("button", { name: "광고 관리자 열기" }).click();
    await waitFor(() => expect(send).toHaveBeenCalled());
    expect((send.mock.calls[0]![1] as { focus?: boolean }).focus).toBe(true);
    a.unmount();

    send.mockClear();
    render(<GuideStep state={{ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 0 } }} dispatch={() => {}} />);
    screen.getByRole("button", { name: "광고 관리자 열기" }).click();
    await waitFor(() => expect(send).toHaveBeenCalled());
    expect((send.mock.calls[0]![1] as { focus?: boolean }).focus).toBeUndefined();
  });
});
