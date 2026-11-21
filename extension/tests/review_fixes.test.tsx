import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { ServerError, research } from "../lib/api";
import { stepsFor } from "../lib/guide";
import { GUIDE } from "../lib/guideList";
import { initialState, reduce, type FlowState } from "../lib/flow";
import { handleProgress, sendWithRetry } from "../lib/progress";
import { loadState, saveState } from "../lib/storage";
import { locate } from "../entrypoints/adsmanager.content/locate";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import UploadStep from "../entrypoints/sidepanel/steps/UploadStep";
import type { Analysis, Change } from "../lib/api";
import type { GuideStepItem } from "../lib/guide";

afterEach(() => vi.unstubAllGlobals());
beforeEach(() => fakeBrowser.reset());

const item = (find: GuideStepItem["entry"]["find"], done: "value" | "manual" = "value"): GuideStepItem => ({
  entry: { id: "x", mode: "create", page: {}, find, say: "{value}", done, fallback: { image: "guide/placeholder.png", text: "못 찾음" } },
  value: "v",
});

describe("server errors", () => {
  it("a 500 is a server error, not 'server down'", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("boom", { status: 500 })));
    const err = await research("x").catch((e) => e);
    expect(err).toBeInstanceOf(ServerError);
    expect(err.message).toContain("서버에서 문제가 생겼어요");
  });
});

describe("edit guide coverage", () => {
  it("creative changes have edit entries", () => {
    const changes: Change[] = [
      { field_id: "meta.creative.copy", label: "문구", new: "새 문구 3개", note: "" },
      { field_id: "meta.ad.creative_test", label: "크리에이티브 테스트", new: "켜기", note: "" },
    ];
    expect(stepsFor("edit", GUIDE, [], changes).map((s) => s.entry.id)).toEqual(["meta.creative.copy", "meta.ad.creative_test"]);
  });

  it("with no edit steps the panel lists the changes as manual text and opens no tab", () => {
    const result = { changes: [{ field_id: "meta.unknown", label: "어떤 칸", new: "새 값", note: "" }] } as unknown as Analysis;
    const state: FlowState = { ...initialState(), step: "fix", result, guide: { mode: "edit", index: 0 } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    expect(screen.getByText(/어떤 칸 → 새 값/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "광고 관리자 열기" })).toBeNull();
    expect(screen.getByRole("button", { name: "바꿨어요" })).toBeTruthy();
  });
});

describe("guide runner robustness", () => {
  beforeEach(() => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = "";
  });

  it("a text step advances on change (commit), not on the first keystroke", () => {
    document.body.innerHTML = '<input aria-label="제목">';
    const seen: number[] = [];
    new Guide(document, [item([{ aria: "제목" }]), item([{ aria: "제목" }])], 0, (i) => seen.push(i), 0);
    const el = document.querySelector("input")!;
    el.dispatchEvent(new Event("input", { bubbles: true }));
    expect(seen).toEqual([]);
    el.dispatchEvent(new Event("change", { bubbles: true }));
    expect(seen).toEqual([1]);
  });

  it("label search does not climb to an unrelated input far away", () => {
    document.body.innerHTML = '<div><input id="search"><div><div><div><div><div><span>제목</span></div></div></div></div></div></div>';
    expect(locate(document, [{ labelText: "제목" }])).toBeNull();
  });

  it("re-seeks on tick: a field that appears later is found, even after fallback", () => {
    const g = new Guide(document, [item([{ aria: "연령" }])], 0, () => {}, 0);
    g.retryNow(); g.retryNow(); g.retryNow();
    expect(g.view().found).toBe(false);
    document.body.innerHTML = '<input aria-label="연령">';
    g.tick();
    expect(g.view().found).toBe(true);
  });

  it("re-seeks when the found element was replaced by a re-render", () => {
    document.body.innerHTML = '<input aria-label="연령" id="old">';
    const g = new Guide(document, [item([{ aria: "연령" }])], 0, () => {}, 0);
    document.body.innerHTML = '<input aria-label="연령" id="new">';
    g.tick();
    expect(g.view().target?.id).toBe("new");
  });
});

describe("progress while the panel is closed", () => {
  it("background writes guide progress and completion into storage", async () => {
    let s = initialState();
    s = reduce(s, { type: "questionsDone", settings: [], endDate: "2026-12-06" });
    await saveState(s);
    await handleProgress({ type: "guide:progress", index: 3, total: 14 });
    expect((await loadState()).guide?.index).toBe(3);
    await handleProgress({ type: "guide:progress", index: 14, total: 14 });
    expect((await loadState()).step).toBe("wait");
  });

  it("finishing the export guide moves to upload", async () => {
    await saveState(reduce({ ...initialState(), step: "wait" }, { type: "startExport" }));
    await handleProgress({ type: "guide:progress", index: 3, total: 3 });
    expect((await loadState()).step).toBe("upload");
  });
});

describe("starting the guide", () => {
  it("retries sending until the content script answers", async () => {
    let calls = 0;
    const send = vi.fn(async () => { calls += 1; if (calls < 3) throw new Error("no listener"); });
    expect(await sendWithRetry(send, 5, 0)).toBe(true);
    expect(calls).toBe(3);
  });

  it("reports failure after the last try", async () => {
    expect(await sendWithRetry(async () => { throw new Error("x"); }, 3, 0)).toBe(false);
  });
});

describe("upload retry", () => {
  it("shows 다시 시도 after a failure and re-sends the same file", async () => {
    const f = vi.fn().mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(new Response(JSON.stringify({ status: "hold" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const dispatch = vi.fn();
    render(<UploadStep state={{ ...initialState(), step: "upload" }} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("결과 파일 (CSV)"), { target: { files: [new File(["x"], "a.csv")] } });
    await waitFor(() => expect(screen.getByRole("button", { name: "다시 시도" })).toBeTruthy());
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "analyzed", result: { status: "hold" } }));
  });
});
