// [닫기] → 뭉치가 집(패널 제목 왼쪽)으로 돌아온다. 진행(몇 번째 칸)은 그대로 둬서 다시 열면 이어서.
import { fakeBrowser } from "wxt/testing/fake-browser";
import { beforeEach, describe, expect, it } from "vitest";
import { initialState, reduce } from "../lib/flow";
import { handleClosed } from "../lib/progress";
import { loadState, saveState } from "../lib/storage";

beforeEach(() => fakeBrowser.reset());

describe("뭉치 돌아오기", () => {
  it("opening sends 뭉치 out, closing brings it home and keeps the step", () => {
    const s0 = { ...initialState(), step: "guide" as const, guide: { mode: "create" as const, index: 3 } };
    const out = reduce(s0, { type: "guideOpened" });
    expect(out.guide?.away).toBe(true);
    const back = reduce(out, { type: "guideClosed" });
    expect(back.guide).toEqual({ mode: "create", index: 3, away: false });
  });

  it("the background writes the return when the overlay closes", async () => {
    await saveState({ ...initialState(), step: "guide", guide: { mode: "create", index: 2, away: true } });
    await handleClosed();
    expect((await loadState()).guide).toMatchObject({ index: 2, away: false });
  });
});
