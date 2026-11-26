// 화면 검토 (2026-11-26) 추천 6개: 처음부터·돈 칸 막힘·같은 세트 다시 확인·내보내기 돌아가기·특별 카테고리 '네'·목록 줄 key
import { fireEvent, render, screen } from "@testing-library/react";
import { fakeBrowser } from "wxt/testing/fake-browser";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import GuideStep from "../entrypoints/sidepanel/steps/GuideStep";
import { initialState, reduce, type FlowState } from "../lib/flow";
import { stepsFor, type GuideStepItem } from "../lib/guide";
import { GUIDE } from "../lib/guideList";
import { handleProgress } from "../lib/progress";
import { SETTING_ORDER } from "../lib/settings";
import { loadState, saveState } from "../lib/storage";

beforeEach(() => fakeBrowser.reset());
const wait = () => new Promise((r) => setTimeout(r, 1000));   // 돈 확인은 구역을 띄우고 0.8초 뒤 읽는다
const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: id, value: "v" }));

describe("21. 처음부터", () => {
  it("뭉치 진행(rev)이 저장돼 있어도 처음으로 돌아간다", async () => {
    await saveState({ ...initialState(), step: "guide", settings, guide: { mode: "create", index: 3 } });
    await handleProgress({ type: "guide:progress", index: 4, total: 18 });   // 배경이 rev를 올림
    const panel = await loadState();                                         // 패널은 onChanged로 이 상태를 따라감
    await saveState(reduce(panel, { type: "reset" }));
    const now = await loadState();
    expect(now.step).toBe("prep");
    expect(now.guide).toBeNull();
    expect(now.settings).toEqual([]);
  });
});

describe("22. 결과 내보내기 안내에서 돌아가기", () => {
  it("export 안내만 닫고 하던 화면(기다리기)은 그대로", async () => {
    const s: FlowState = { ...initialState(), step: "wait", settings, guide: { mode: "export", index: 1 } };
    const dispatch = vi.fn();
    render(<GuideStep state={s} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: /돌아가기/ }));
    expect(dispatch).toHaveBeenCalledWith({ type: "closeExport" });
    expect(reduce(s, { type: "closeExport" })).toMatchObject({ step: "wait", guide: null });
    expect(reduce({ ...s, guide: { mode: "create", index: 2 } }, { type: "closeExport" }).guide).toEqual({ mode: "create", index: 2 });   // 만들기 안내는 안 닫음
  });
});

describe("7. 특별 광고 카테고리 '네'", () => {
  it("'네'면 뭉치가 건너뛰지 않고 사장님이 직접 고르는 칸", () => {
    const pick = (v: string) => stepsFor("create", GUIDE, [{ fieldId: "meta.campaign.special_category", label: "", value: v }], [])
      .find((x) => x.entry.id === "meta.campaign.special_category")!.entry;
    expect(pick("아니요").auto).toBe("skip");
    expect(pick("네")).toMatchObject({ auto: "owner" });
    expect(pick("네").say).toContain("직접 골라");
  });
});

function money(id: string, auto: GuideStepItem["entry"]["auto"], value?: string): GuideStepItem {
  return { entry: { id, mode: "create", page: {}, find: [{ heading: "예산 및 일정" }], say: "돈 칸", done: "manual", fallback: { image: "", text: "" }, auto }, value };
}
function lifetime(end = true) {
  document.documentElement.lang = "ko";
  document.body.innerHTML = `<h2>예산 및 일정</h2><label id="l1">총 예산</label><label id="l2">예산 모드</label>
    <div role="combobox" aria-labelledby="l1 l2 l3"><div id="l3">총 예산</div></div>
    <input type="text" placeholder="금액을 입력하세요" value="30,000"><input placeholder="yyyy-mm-dd" value="2026년 11월 26일">
    ${end ? `<span id="p1">종료 날짜 기간</span><div role="combobox" aria-labelledby="p1"><div>30일</div></div><input placeholder="yyyy-mm-dd" value="2099년 12월 26일">` : ""}`;
}

describe("13. 돈 칸: 칸을 못 찾으면 사장님 확인으로", () => {
  it("종료 날짜 칸을 못 찾으면 멈추고, [다 했어요]를 한 번 더 누르면 넘어간다", { timeout: 8000 }, async () => {
    lifetime(false);
    const seen: number[] = [];
    const g = new Guide(document, [money("meta.money_check", "moneyCheck", "3만 원"), money("meta.publish", "stop")], 0, (i) => seen.push(i), 0);
    g.apply(); await wait();
    expect(g.view().index).toBe(0);
    expect(g.view().text).toContain("한 번 더 눌러");
    g.apply(); await wait();
    expect(seen).toEqual([1]);
  });

  it("값이 다르면(일일 예산) 몇 번을 눌러도 넘어가지 않는다", { timeout: 8000 }, async () => {
    lifetime(false);
    document.getElementById("l3")!.textContent = "일일 예산";
    const g = new Guide(document, [money("meta.money_check", "moneyCheck", "3만 원"), money("meta.publish", "stop")], 0, () => {}, 0);
    g.apply(); await wait();
    g.apply(); await wait();
    expect(g.view().index).toBe(0);
  });

  it("예산 공유 칸을 못 찾으면 같은 방식 (한 번 더 누르면 넘어감)", async () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<h2>예산</h2><span id="c2">광고 세트 예산</span><input type="radio" aria-labelledby="c2" checked>`;
    const seen: number[] = [];
    const g = new Guide(document, [{ ...money("meta.campaign.budget_strategy", "campaignBudget"), entry: { ...money("x", "campaignBudget").entry, id: "meta.campaign.budget_strategy", find: [{ heading: "예산" }] } }, money("next", "owner")], 0, (i) => seen.push(i), 0);
    g.apply(); await wait(); await wait();
    expect(g.view().text).toContain("공유하기'가 꺼져 있는지");
    g.apply(); await wait(); await wait();
    expect(seen).toEqual([1]);
  }, 10000);
});

describe("14. [이전 칸] 뒤 같은 돈 확인 칸으로 돌아와도 다시 확인된다", () => {
  it("같은 칸·같은 세트는 통과, 다른 돈 확인 칸에서 같은 세트면 막힘은 그대로", { timeout: 10000 }, async () => {
    lifetime();
    history.pushState({}, "", "/adsmanager/manage/adsets/edit?selected_adset_ids=111");
    const g = new Guide(document, [money("meta.money_check", "moneyCheck", "3만 원"), money("meta.publish", "stop")], 0, () => {}, 0);
    g.apply(); await wait();
    expect(g.view().index).toBe(1);
    g.back();
    g.apply(); await wait();
    expect(g.view().index).toBe(1);
  });
});

describe("26. 다음 테스트 목록 줄 key", () => {
  it("돈 확인 칸이 두 번 들어가도 React가 같은 key 경고를 내지 않는다", async () => {
    const err = vi.spyOn(console, "error").mockImplementation(() => {});
    const plan = { code: "EX01", action: "", change: { field_id: "meta.ad.primary_text", label: "기본 문구", old: "a", new: "b" }, summary: [], badge: null } as unknown as FlowState["plan"];
    const s: FlowState = { ...initialState(), step: "guide", settings: [...settings, { fieldId: "meta.money_check", label: "돈", value: "3만 원" }], plan,
      guide: { mode: "create", index: 0, next: "meta.ad.primary_text" } };
    render(<GuideStep state={s} dispatch={() => {}} />);
    expect(err.mock.calls.some((c) => String(c[0]).includes("same key"))).toBe(false);
    err.mockRestore();
  });
});
