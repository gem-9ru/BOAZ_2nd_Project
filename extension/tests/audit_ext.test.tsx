// 감사 6·7·8·12·13·14·18 (2026-11-26): 어시스턴트 다시 부르기, 진행 덮어쓰기, 종료 날짜, 게시 막기, 금액 읽기
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { moneyProblems, setEndDate } from "../entrypoints/adsmanager.content/actions";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import { isPublishLike } from "../entrypoints/adsmanager.content/locate";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import { initialState, type FlowState } from "../lib/flow";
import { guideSignature, type GuideStepItem } from "../lib/guide";
import { GUIDE } from "../lib/guideList";
import { handleProgress } from "../lib/progress";
import { parseWon, SETTING_ORDER } from "../lib/settings";
import { loadState, saveState } from "../lib/storage";

const fast = { wait: async () => {} };
beforeEach(() => fakeBrowser.reset());

describe("6. 다시 부른 뒤 예전 뭉치", () => {
  it("멈춘(kill) 뭉치는 하던 일이 끝나도 다음 칸으로 넘기지 않는다 (진행 저장도 안 함)", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<input aria-label="제목">`;
    const moved: number[] = [];
    const step = (id: string): GuideStepItem => ({ entry: { id, mode: "create", page: { urlIncludes: "" }, find: [{ aria: "제목" }], say: "x",
      done: "manual", fallback: { image: "", text: "" }, auto: "type", level: "ad" }, value: "v" });
    const g = new Guide(document, [step("a"), step("b")], 0, (i) => moved.push(i), 0);
    g.kill();
    g.markDone();
    expect(moved).toEqual([]);
  });
});

describe("7. 패널이 뭉치 진행을 덮어쓰지 않는다", () => {
  it("배경이 먼저 쓴 진행(더 새 rev)은 패널의 옛 상태로 덮이지 않고, 패널이 바꾼 답은 남는다", async () => {
    const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: id, value: "v" }));
    await saveState({ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 3 } });
    const stale = await loadState();
    await handleProgress({ type: "guide:progress", index: 4, total: 18 });   // 배경: 4번 칸으로
    await saveState({ ...stale, answers: { x: "새 답" } });                  // 패널: 옛 상태(3번)로 저장
    const now = await loadState();
    expect(now.guide?.index).toBe(4);
    expect(now.answers.x).toBe("새 답");
  });
});

describe("8. 종료 날짜", () => {
  it("넣었는데 칸에 안 들어갔으면 성공이라 하지 않는다", async () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<input placeholder="yyyy-mm-dd" value="2026년 11월 26일">
      <span id="s">종료 날짜 설정</span><input type="checkbox" aria-labelledby="s" checked>
      <input id="end" placeholder="yyyy-mm-dd" value="2026년 12월 26일">`;
    document.getElementById("end")!.addEventListener("input", (e) => { (e.target as HTMLInputElement).value = "2026년 12월 26일"; });   // 메타가 무시
    expect(await setEndDate(document, "2026-12-03", fast)).toBe(false);
  });

  it("돈 확인: 종료 날짜가 이미 지났으면 막는다", async () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<h2>예산 및 일정</h2><label id="l1">총 예산</label><label id="l2">예산 모드</label>
      <div role="combobox" aria-labelledby="l1 l2 l3"><div id="l3">총 예산</div></div>
      <input placeholder="금액을 입력하세요" value="30,000">
      <input placeholder="yyyy-mm-dd" value="2020년 1월 1일">
      <span id="p1">종료 날짜 기간</span><div role="combobox" aria-labelledby="p1"><div>직접 지정</div></div>
      <input placeholder="yyyy-mm-dd" value="2020년 1월 5일">`;
    expect((await moneyProblems(document, "3만 원", fast)).join()).toMatch(/종료 날짜가 이미 지났어요/);
  });
});

describe("12. 자동 진행은 같은 안내를 다시 받을 때만 이어 간다", () => {
  it("칸 목록이 같으면 같은 표시, 다르면 다른 표시", () => {
    const a = GUIDE.filter((e) => e.mode === "create").map((entry) => ({ entry }));
    expect(guideSignature(a)).toBe(guideSignature([...a]));
    expect(guideSignature(a)).not.toBe(guideSignature(a.slice(1)));
  });
});

describe("13. 게시 막기", () => {
  it("게시 버튼 안의 아이콘·title로만 이름을 단 버튼·이름표로 이어진 버튼도 게시로 본다", () => {
    document.body.innerHTML = `<div role="button" id="b1"><i id="icon"></i><span>게시</span></div>
      <button id="b2" title="동의하고 게시"></button><span id="lb">검토 후 게시</span><div role="button" id="b3" aria-labelledby="lb"></div>
      <div role="button" id="ok">다음</div>`;
    expect(isPublishLike(document.getElementById("icon")!)).toBe(true);
    expect(isPublishLike(document.getElementById("b2")!)).toBe(true);
    expect(isPublishLike(document.getElementById("b3")!)).toBe(true);
    expect(isPublishLike(document.getElementById("ok")!)).toBe(false);
  });
});

describe("14. 게시 칸에서 패널의 [다음 칸]", () => {
  it("게시하지 않았는데 끝난 것으로 넘기지 않는다", async () => {
    const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: id, value: "v" }));
    const last = GUIDE.filter((e) => e.mode === "create").length - 1;
    await fakeBrowser.tabs.create({ url: "https://adsmanager.facebook.com/adsmanager/manage", active: true });
    const send = vi.spyOn(fakeBrowser.tabs, "sendMessage").mockResolvedValue(undefined);
    const state: FlowState = { ...initialState(), step: "guide", settings, guide: { mode: "create", index: last, away: true } };
    render(<GuideStep state={state} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "다음 칸" }));
    await waitFor(() => expect(screen.getByText(/게시는 사장님이 직접/)).toBeTruthy());
    expect(send).not.toHaveBeenCalled();
  });
});

describe("18. 금액 읽기", () => {
  it("숫자·쉼표·만·원 모양만 받는다", () => {
    expect(parseWon("3만 원")).toBe(30000);
    expect(parseWon("25,000원")).toBe(25000);
    expect(parseWon("1e3")).toBeNull();
    expect(parseWon("0x10")).toBeNull();
  });
});
