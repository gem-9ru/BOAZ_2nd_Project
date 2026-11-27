// 돈 안전 (2026-11-26 사장님: "돈이 설정한 대로 잘 나가는지, 추가 지출은 없는지가 제일 중요"):
// 캠페인 예산 → 광고 세트 예산, 총예산 종류·금액 넣고 다시 읽기, 게시 앞 돈 확인. 맞을 때만 다음 칸 ([다 했어요]로도 못 건너뜀).
// 화면 구조는 2026-11-26 실제 광고 관리자(광고 세트 편집)에서 읽은 것을 그대로 본떴다.
import { beforeEach, describe, expect, it } from "vitest";
import { moneyProblems, readBudget, setEndDate, setLifetimeBudget, useAdsetBudget } from "../entrypoints/adsmanager.content/actions";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import type { GuideStepItem } from "../lib/guide";

const fast = { wait: async () => {} };

/** 광고 세트 '예산 및 일정' (mode: 목록 글자, amount: 금액 칸 값, end: 종료 날짜 칸 값 · null이면 스위치 꺼짐) */
function adset({ mode = "일일 예산", amount = "20,000", end = "2026년 12월 14일" as string | null, locked = false } = {}) {
  document.documentElement.lang = "ko";
  document.body.innerHTML = `
    <h2>예산 및 일정</h2>
    <label id="l1">총 예산</label><label id="l2">예산 모드</label>
    <div role="combobox" aria-haspopup="listbox" aria-labelledby="l1 l2 l3" ${locked ? 'aria-disabled="true"' : ""}><div id="l3">${mode}​</div></div>
    <label id="l4" for="daily">총 예산</label><input id="daily" type="text" aria-labelledby="l1 l4" placeholder="금액을 입력하세요" value="${amount}">
    <input placeholder="yyyy-mm-dd" value="2026년 12월 1일">
    <span id="l5">종료 날짜 설정</span><input type="checkbox" aria-labelledby="l5" ${end === null ? "" : "checked"}>
    <input placeholder="yyyy-mm-dd" value="${end ?? ""}">`;
  const combo = document.querySelector<HTMLElement>("[role=combobox]")!;
  combo.addEventListener("click", () => {   // 메타처럼: 누르면 목록이 열리고, 고르면 글자가 바뀐다
    if (document.querySelector("[role=listbox]")) return document.querySelector("[role=listbox]")!.remove();
    const list = document.createElement("div");
    list.setAttribute("role", "listbox");
    for (const name of ["일일 예산", "총예산"]) {
      const o = document.createElement("div");
      o.setAttribute("role", "option");
      o.textContent = name;
      o.addEventListener("click", () => { document.getElementById("l3")!.textContent = `${name}​`; list.remove(); });
      list.append(o);
    }
    document.body.append(list);
  });
}

/** 총예산일 때 (2026-11-26 실제 화면): '종료 날짜 설정' 스위치가 없고 '종료 날짜 기간' 목록 + 날짜 칸. warn = 메타 최소 금액 경고 */
function lifetime({ amount = "30,000", end = "2026년 12월 26일", warn = false } = {}) {
  document.documentElement.lang = "ko";
  document.body.innerHTML = `
    <h2>예산 및 일정</h2>
    <label id="l1">총 예산</label><label id="l2">예산 모드</label>
    <div role="combobox" aria-labelledby="l1 l2 l3"><div id="l3">총 예산\u200b</div></div>
    <input type="text" placeholder="금액을 입력하세요" value="${amount}">
    ${warn ? "<div><span>예산은 ₩40,080.00 이상이어야 하며, 그렇지 않으면 광고가 게재되지 않을 수 있습니다. 이 광고 세트의 예산을 늘려주세요.</span></div>" : ""}
    <input placeholder="yyyy-mm-dd" value="2026년 11월 26일">
    <span id="p1">종료 날짜 기간</span><div role="combobox" aria-labelledby="p1 p2"><div id="p2">30일</div></div>
    <input placeholder="yyyy-mm-dd" value="${end}">`;
}

function campaign(adsetChecked: boolean, share = true) {
  document.documentElement.lang = "ko";
  document.body.innerHTML = `
    <h2>예산</h2>
    <span id="c1">캠페인 예산</span><input type="radio" name="b" aria-labelledby="c1" ${adsetChecked ? "" : "checked"}>
    <span id="c2">광고 세트 예산</span><input type="radio" name="b" aria-labelledby="c2" ${adsetChecked ? "checked" : ""}>
    <input type="checkbox" aria-label="예산 일부를 다른 광고 세트와 공유하기" ${share ? "checked" : ""}>`;
}

describe("돈 칸 화면 조작", () => {
  beforeEach(() => adset());

  it("reads the budget mode and amount from the screen", () => {
    expect(readBudget(document)).toMatchObject({ found: true, mode: "daily", amount: 20000 });
  });

  it("switches to 총예산, types the amount, and only says ok after reading both back", async () => {
    expect(await setLifetimeBudget(document, "3만 원", fast)).toBe(true);
    expect(readBudget(document)).toMatchObject({ mode: "lifetime", amount: 30000 });
  });

  it("does not claim success when the screen did not take the amount", async () => {
    document.querySelector<HTMLInputElement>("#daily")!.addEventListener("input", (e) => { (e.target as HTMLInputElement).value = "20,000"; });
    expect(await setLifetimeBudget(document, "3만 원", fast)).toBe(false);
  });

  // 2026-11-26 실제 화면 (초안 120257356971480583): '총 예산'을 고른 뒤 메타가 늦게 바뀌어 첫 확인에서 실패('budget mode did not stick'),
  // 그사이 금액은 메타 기본값 ₩350,000. 사장님이 [다 했어요]로 다시 하자 맞게 들어갔다 → 조금 더 기다렸다 한 번 더 읽는다
  it("Meta switches to 총예산 a bit late: waits once more and still fills the amount", async () => {
    // 선택지를 누르면 글자가 30ms 뒤에야 바뀐다 (기다리는 시간은 40분의 1로 줄여 실제 순서만 본뜸)
    const slow = { wait: (ms: number) => new Promise<void>((r) => setTimeout(r, ms / 40)) };
    const orig = document.body.append;
    document.body.append = function (...nodes: (string | Node)[]) {
      for (const n of nodes) if (n instanceof HTMLElement && n.getAttribute("role") === "listbox") {
        n.querySelectorAll<HTMLElement>("[role=option]").forEach((o) => o.addEventListener("click", (e) => {
          e.stopImmediatePropagation();
          n.remove();
          setTimeout(() => { document.getElementById("l3")!.textContent = `${o.textContent}\u200b`; }, 30);
        }, { capture: true }));
      }
      orig.apply(document.body, nodes);
    };
    try {
      expect(await setLifetimeBudget(document, "3만 원", slow)).toBe(true);
      expect(readBudget(document)).toMatchObject({ mode: "lifetime", amount: 30000 });
    } finally {
      document.body.append = orig;
    }
  });

  it("gives up (owner's turn) when the budget mode is locked on 일일 예산", async () => {
    adset({ locked: true });
    expect(await setLifetimeBudget(document, "3만 원", fast)).toBe(false);
  });

  it("turns the campaign budget off by choosing 광고 세트 예산", async () => {
    campaign(false);
    expect(await useAdsetBudget(document, fast)).toBe(true);
    expect(document.querySelectorAll<HTMLInputElement>("input")[1]!.checked).toBe(true);
    expect(document.querySelector<HTMLInputElement>("input[type=checkbox]")!.checked).toBe(false);   // 예산 공유(최대 20%)는 끔
  });

  it("budget share: Meta asks '예산 공유를 해제하시겠어요?' → presses '예산 공유 해제' (2026-11-26 실제 화면에서 멈춘 곳)", async () => {
    campaign(true);
    const box = document.querySelector<HTMLInputElement>("input[type=checkbox]")!;
    box.addEventListener("click", (e) => {
      e.preventDefault();   // 메타는 바로 끄지 않고 확인 창을 띄운다
      document.body.insertAdjacentHTML("beforeend", `<div role="dialog"><div role="button" id="keep">예산 공유 계속 사용</div><div role="button" id="off">예산 공유 해제</div></div>`);
      document.getElementById("off")!.addEventListener("click", () => { box.checked = false; document.querySelector("[role=dialog]")!.remove(); });
    });
    expect(await useAdsetBudget(document, fast)).toBe(true);
    expect(box.checked).toBe(false);
    expect(document.querySelector("[role=dialog]")).toBeNull();
  });

  it("fails when the budget share box will not turn off", async () => {
    campaign(true);
    document.querySelector<HTMLInputElement>("input[type=checkbox]")!.addEventListener("click", (e) => e.preventDefault());
    expect(await useAdsetBudget(document, fast)).toBe(false);
  });

  it("end date: with 총예산 there is no switch, so it types into the box after '종료 날짜 기간'", async () => {
    lifetime();
    expect(await setEndDate(document, "2026-12-09", fast)).toBe(true);
    expect(document.querySelectorAll<HTMLInputElement>("input[placeholder='yyyy-mm-dd']")[1]!.value).toBe("2026-12-09");
    expect(document.querySelectorAll<HTMLInputElement>("input[placeholder='yyyy-mm-dd']")[0]!.value).toBe("2026년 11월 26일");   // 시작 날짜는 그대로
  });
});

describe("게시 앞 돈 확인", () => {
  it("passes only when type, amount and end date all match", async () => {
    adset({ mode: "총예산", amount: "30,000" });
    expect(await moneyProblems(document, "3만 원", fast)).toEqual([]);
  });

  it("names each thing that differs", async () => {
    adset({ mode: "일일 예산", amount: "20,000", end: null });
    const p = await moneyProblems(document, "3만 원", fast);
    expect(p).toHaveLength(3);
    expect(p[0]).toContain("'일일 예산'이에요 → '총예산'으로");
    expect(p[1]).toContain("금액이 20,000원이에요 → 30,000원으로");
    expect(p[2]).toContain("종료 날짜가 없어요");
  });

  it("an empty end date box also counts as no end date", async () => {
    adset({ mode: "총예산", amount: "30,000", end: "" });
    expect((await moneyProblems(document, "3만 원", fast)).join()).toContain("종료 날짜가 없어요");
  });

  it("an amount that reads 0 (section not drawn yet) is never taken as right", async () => {
    adset({ mode: "총예산", amount: "0" });
    const p = (await moneyProblems(document, "3만 원", fast)).join();
    expect(p).toContain("금액을 읽지 못했어요");
  });

  it("with 총예산 the end date comes from '종료 날짜 기간', not the (gone) switch", async () => {
    lifetime();
    expect(await moneyProblems(document, "3만 원", fast)).toEqual([]);
  });

  it("passes Meta's own 'budget must be at least' warning on to the owner", async () => {
    lifetime({ warn: true });
    expect((await moneyProblems(document, "3만 원", fast)).join()).toContain("메타가 '예산은 40,080원 이상이어야 광고가 나가요'라고 해요");
  });

  it("no budget box on the ad set = campaign budget is on", async () => {
    document.body.innerHTML = "<h2>예산 및 일정</h2>";
    expect((await moneyProblems(document, "3만 원", fast)).join()).toContain("'광고 세트 예산'으로 바꿔 주세요");
  });
});

function item(id: string, auto: GuideStepItem["entry"]["auto"], value?: string, find: GuideStepItem["entry"]["find"] = [{ heading: "예산 및 일정" }]): GuideStepItem {
  return { entry: { id, mode: "create", page: {}, find, say: "돈 칸", done: "manual", fallback: { image: "x.png", text: "x" }, auto }, value };
}
const flush = () => new Promise((r) => setTimeout(r, 0));
const wait = () => new Promise((r) => setTimeout(r, 900));   // 돈 확인은 구역을 띄우고 0.8초 기다린 뒤 읽는다

describe("Guide runner: 돈 칸은 맞을 때만 넘어간다", () => {
  it("money check stops with what differs, and [다 했어요] re-checks instead of skipping", { timeout: 8000 }, async () => {
    adset({ mode: "일일 예산", amount: "20,000" });
    const seen: number[] = [];
    const g = new Guide(document, [item("meta.money_check", "moneyCheck", "3만 원"), item("meta.publish", "stop")], 0, (i) => seen.push(i), 0);
    g.apply();
    await wait();
    expect(g.view().index).toBe(0);
    expect(g.view().waiting).toBe("owner");
    expect(g.view().text).toContain("▲ 돈 확인");
    expect(g.view().text).toContain("'총예산'으로");
    g.apply();   // [다 했어요]를 눌러도 화면이 그대로면 그대로
    await wait();
    expect(g.view().index).toBe(0);
    adset({ mode: "총예산", amount: "30,000" });   // 사장님이 고침
    g.apply();
    await wait();
    expect(seen).toEqual([1]);
  });

  it("lifetime budget step fills in and moves on only after reading it back", async () => {
    adset();
    const seen: number[] = [];
    const g = new Guide(document, [item("meta.adset.lifetime_budget", "lifetimeBudget", "3만 원"), item("next", "owner")], 0, (i) => seen.push(i), 0);
    g.apply();
    await new Promise((r) => setTimeout(r, 4200));   // 실제 기다림(띄우기 0.8 · 목록 열기 0.7 · 고르기 0.8 · 넣기 1초)
    expect(readBudget(document)).toMatchObject({ mode: "lifetime", amount: 30000 });
    expect(seen).toEqual([1]);
  }, 8000);

  it("campaign budget step stays put when it cannot find the choice", async () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = "<h2>예산</h2>";
    const g = new Guide(document, [item("meta.campaign.budget_strategy", "campaignBudget", undefined, [{ heading: "예산" }]), item("next", "owner")], 0, () => {}, 0);
    g.apply();
    await flush();
    expect(g.view().index).toBe(0);
    expect(g.view().text).toContain("끄지 못했어요 → 캠페인 화면 '예산'에서 직접 맞춰 주세요");
  });
});

describe("감사 1·2: 예산 공유 칸·두 세트 돈 확인 (2026-11-26)", () => {
  it("예산 공유 칸을 못 찾으면 '껐다'고 넘어가지 않는다 (메타가 아직 안 그렸을 수 있음)", async () => {
    campaign(false);
    document.querySelector("input[type=checkbox]")!.remove();
    expect(await useAdsetBudget(document, fast)).toBe("unseen");   // '껐다'(true)가 아니라 '못 봄' → 사장님 확인
  });

  it("두 세트 돈 확인: 두 번째 확인이 첫 번째와 같은 세트(주소의 광고 세트 id)면 통과하지 않는다", async () => {
    lifetime({ amount: "30,000", end: "2026년 12월 26일" });
    history.pushState({}, "", "/adsmanager/manage/adsets/edit?selected_adset_ids=111");
    const money = { entry: { id: "meta.money_check", mode: "create", page: { urlIncludes: "" }, find: [{ heading: "예산 및 일정" }], say: "돈 확인",
      done: "manual", fallback: { image: "", text: "" }, auto: "moneyCheck", level: "adset" }, value: "3만 원" } as GuideStepItem;
    const g = new Guide(document, [money, { ...money }, { ...money, entry: { ...money.entry, id: "end", find: [{ aria: "없음" }] } }], 0, () => {}, 0);
    const settle = () => new Promise((r) => setTimeout(r, 500));   // 돈 확인은 구역을 띄운 뒤 0.8초 기다려 읽는다
    g.apply(); await settle(); await settle();
    expect(g.view().index).toBe(1);   // 첫 세트 통과
    g.apply(); await settle(); await settle();
    expect(g.view().index).toBe(1);   // 같은 세트를 또 읽음 → 멈춤
    expect(g.view().text).toMatch(/아까 확인한 세트/);
    history.pushState({}, "", "/adsmanager/manage/adsets/edit?selected_adset_ids=222");   // '그대로' 세트를 엶
    g.apply(); await settle(); await settle();
    expect(g.view().index).toBe(2);
  });
});
