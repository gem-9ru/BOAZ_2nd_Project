// 광고 › 사진(미디어) 칸: 하위 단계로 나눠 뭉치가 버벅이지 않고 차례로 넘어가는지.
// ① '크리에이티브 설정' 열기(뭉치) ② '이미지 광고' 누르기(뭉치) ③ 사진 고르기(사장님) ④ '기본 문구' 칸이 뜨면 다음 칸.
import { beforeEach, describe, expect, it } from "vitest";
import raw from "../guide/meta_traffic.json";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import { validateGuide, type GuideEntry, type GuideStepItem } from "../lib/guide";

const GUIDE = raw as GuideEntry[];
const media = GUIDE.find((e) => e.mode === "create" && e.id === "meta.ad.media")!;
const next: GuideEntry = { id: "n", mode: "create", page: {}, find: [{ aria: "간단하게 광고를 소개하세요" }], say: "문구", done: "value",
  fallback: { image: "x.png", text: "문구" }, auto: "type" };

/** 메타 흉내 (2026-11-25 실제 화면 확인): 버튼 → role=menu의 menuitem '이미지 광고' → 미디어 창.
 *  창 위쪽엔 단계 표시(미디어·크리에이티브 설정·자르기·문구 버튼)가 있고, '다음'이 먼저 뜨고 '업로드'는 delay.upload 뒤에 뜬다. */
function fakeMeta(delay = { menu: 0, dialog: 0, upload: 0 }) {
  document.body.innerHTML = `<div id="sc" style="overflow-y:auto"><div role="button" id="cs">크리에이티브 설정</div></div>`;
  const sc = document.getElementById("sc")!;
  Object.defineProperty(sc, "clientHeight", { value: 1000 });
  Object.defineProperty(sc, "scrollHeight", { value: 4000 });
  const clicks = { cs: 0, image: 0 };
  const later = (ms: number, f: () => void) => (ms ? setTimeout(f, ms) : f());
  document.getElementById("cs")!.addEventListener("click", () => {
    clicks.cs += 1;
    later(delay.menu, () => {
      if (document.getElementById("menu")) return;
      document.body.insertAdjacentHTML("beforeend", `<div role="menu" id="menu"><div role="menuitem" id="img">이미지 광고</div><div role="menuitem">동영상 광고</div></div>`);
      document.getElementById("img")!.addEventListener("click", () => {
        clicks.image += 1;
        later(delay.dialog, () => {
          document.getElementById("menu")?.remove();
          document.body.insertAdjacentHTML("beforeend", `<div role="dialog" id="dlg"><div role="button">미디어</div><div role="button" id="dcs">크리에이티브 설정</div>
            <div role="button">자르기</div><div role="button">문구</div><div id="body"></div><div role="button" id="dnext">다음</div></div>`);
          later(delay.upload, () => document.getElementById("body")!.insertAdjacentHTML("beforeend", `<div role="button" id="up">업로드</div>`));
        });
      });
    });
  });
  return { sc, clicks };
}

const steps = (): GuideStepItem[] => [{ entry: media, value: "세로 9:16 사진" }, { entry: next, value: "바삭한 쿠키" }];
const run = (g: Guide, from: number, n: number, gap = 500) => { for (let i = 0; i < n; i++) { g.tick(); g.autoStep(from + i * gap); } return from + n * gap; };

beforeEach(() => { document.documentElement.lang = "ko"; history.pushState({}, "", "/"); });

describe("사진 칸 하위 단계", () => {
  it("guide JSON: media has 3 stages (buddy, buddy, owner) and a done signal, and passes validation", () => {
    expect(media.stages?.map((s) => s.by)).toEqual(["buddy", "buddy", "owner"]);
    expect(media.doneWhen).toEqual([{ aria: "간단하게 광고를 소개하세요" }]);
    expect(validateGuide(GUIDE.filter((e) => e.id === "meta.ad.media"), ["meta.ad.media"])).toEqual([]);
  });

  it("① 열기 → ② 이미지 광고 → ③ 사장님이 사진 → ④ 문구 칸이 뜨면 바로 다음 칸 (각 버튼은 한 번만)", () => {
    const { clicks } = fakeMeta();
    const seen: number[] = [];
    const g = new Guide(document, steps(), 0, (i) => seen.push(i), 0);
    g.setAuto(true);
    expect(g.view()).toMatchObject({ target: document.getElementById("cs"), hint: true });
    expect(g.view().text).toMatch(/^1\/3 · '크리에이티브 설정'/);

    let t = run(g, 1000, 6);
    expect(clicks.cs).toBe(1);
    expect(g.view().target?.id).toBe("img");   // 메뉴가 뜨자마자 그쪽으로
    expect(g.view().text).toMatch(/^2\/3 · '이미지 광고'/);

    t = run(g, t, 6);
    expect(clicks.image).toBe(1);
    expect(g.view()).toMatchObject({ waiting: "owner" });
    expect(g.view().target?.id).toBe("up");
    expect(g.view().text).toMatch(/^3\/3 · 사진을 고르거나 '업로드'로 올리세요 \(세로 9:16 사진\)/);

    // 사장님이 사진을 고름 → 창이 문구 단계로 바뀜
    document.getElementById("dlg")!.innerHTML = `<div contenteditable="true" aria-label="간단하게 광고를 소개하세요"></div>`;
    run(g, t, 1);
    expect(seen).toEqual([1]);
    expect(clicks).toEqual({ cs: 1, image: 1 });
  });

  it("다음 요소가 늦게 떠도: 기다리는 동안 스크롤하지 않고, 다시 누르지 않고, 뜨면 바로 그쪽으로", async () => {
    const { sc, clicks } = fakeMeta({ menu: 1200, dialog: 0, upload: 0 });
    const g = new Guide(document, steps(), 0, () => {}, 0);
    g.setAuto(true);
    const t = run(g, 1000, 4);   // 가리킨 뒤 누름
    expect(clicks.cs).toBe(1);
    run(g, t, 4, 400);   // 메뉴가 아직 안 뜸 (누른 뒤 기다리는 시간 안)
    expect(clicks.cs).toBe(1);
    expect(sc.scrollTop).toBe(0);
    expect(g.view().target?.id).toBe("cs");
    await new Promise((r) => setTimeout(r, 1300));
    g.tick();
    expect(g.view().target?.id).toBe("img");
  });

  it("창이 잠깐 다시 그려져 사라져도 앞 단계로 되돌아가지 않는다", () => {
    fakeMeta();
    const g = new Guide(document, steps(), 0, () => {}, 0);
    g.setAuto(true);
    run(g, 1000, 12);
    expect(g.view().target?.id).toBe("up");
    const dlg = document.getElementById("dlg")!;
    dlg.remove();   // 한 번 사라졌다가
    g.tick();
    expect(g.view().text).toMatch(/^3\/3/);
    document.body.appendChild(dlg);   // 다시 나타남
    g.tick();
    expect(g.view().target?.id).toBe("up");
    expect(g.view().text).toMatch(/^3\/3/);
  });

  it("사장님이 창을 닫아 정말 앞으로 돌아가면, 뭉치는 다시 누르지 않고 기다린다", () => {
    const { clicks } = fakeMeta();
    const g = new Guide(document, steps(), 0, () => {}, 0);
    g.setAuto(true);
    let t = run(g, 1000, 12);
    document.getElementById("dlg")!.remove();
    t = run(g, t, 10);
    expect(g.view().target?.id).toBe("cs");
    expect(g.view().waiting).toBe("owner");
    expect(clicks.cs).toBe(1);
  });

  it("눌러도 메뉴가 안 뜨면 두 번까지만 누르고 사장님께 넘긴다", () => {
    document.body.innerHTML = `<div role="button" id="cs">크리에이티브 설정</div>`;
    let clicks = 0;
    document.getElementById("cs")!.addEventListener("click", () => clicks++);
    const g = new Guide(document, steps(), 0, () => {}, 0);
    g.setAuto(true);
    run(g, 1000, 60);
    expect(clicks).toBe(2);
    expect(g.view().waiting).toBe("owner");
  });

  it("[다음 칸]을 직접 누르면: 뭉치 단계는 그 버튼을 누르고, 사장님 단계에선 다음 칸", () => {
    const { clicks } = fakeMeta();
    const seen: number[] = [];
    const g = new Guide(document, steps(), 0, (i) => seen.push(i), 0);
    g.apply();
    g.tick();
    expect(clicks.cs).toBe(1);
    g.apply();
    g.tick();
    expect(clicks.image).toBe(1);
    expect(g.view().target?.id).toBe("up");
    g.apply();
    expect(seen).toEqual([1]);
  });

  it("실제 화면처럼 '업로드'가 늦게 떠도: '다음'에 먼저 가지 않고, 창 안 '크리에이티브 설정'으로 되돌아가지 않는다", async () => {
    const { clicks } = fakeMeta({ menu: 0, dialog: 0, upload: 700 });
    const g = new Guide(document, steps(), 0, () => {}, 0);
    g.setAuto(true);
    const targets: (string | undefined)[] = [];
    let t = 1000;
    for (let i = 0; i < 12; i++) { g.tick(); g.autoStep(t); t += 500; targets.push(g.view().target?.id); }
    expect(clicks).toEqual({ cs: 1, image: 1 });
    expect(targets).not.toContain("dnext");
    expect(targets).not.toContain("dcs");
    await new Promise((r) => setTimeout(r, 800));
    for (let i = 0; i < 6; i++) { g.tick(); g.autoStep(t); t += 500; }
    expect(g.view()).toMatchObject({ waiting: "owner" });
    expect(g.view().target?.id).toBe("up");
    // 사진을 고르고 '다음' → 창이 '크리에이티브 설정'·'자르기' 단계로 (업로드 없음, '다음'만) → 뭉치는 '다음'을 짚는다
    document.getElementById("body")!.innerHTML = "<p>자르기</p>";
    for (let i = 0; i < 4; i++) g.tick();
    expect(g.view().target?.id).toBe("dnext");
    expect(g.view().text).toMatch(/^3\/3 · 사진을 골랐으면/);
  });

  it("validateGuide: 뭉치가 누르는 단계에 게시 버튼이 있으면 잡는다", () => {
    const bad: GuideEntry = { ...media, stages: [{ by: "buddy", find: [{ role: "button", text: "동의하고 게시" }], say: "누를게요" }] };
    expect(validateGuide([bad], ["meta.ad.media"]).join()).toMatch(/게시 버튼/);
  });
});
