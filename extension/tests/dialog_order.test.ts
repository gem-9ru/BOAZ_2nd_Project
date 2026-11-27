// 2026-11-26 시연: 광고 만들기 창은 미디어 → 크리에이티브 설정(소스 URL) → 자르기 → 문구 → 이미지 생성 → 개선 사항 → 완료를
// [다음]으로 차례대로 지나가야 한다. 위쪽 단계 이름을 눌러 건너뛰면 사진 선택이 반영되지 않아 [다음]이 막혔다.
import { describe, expect, it } from "vitest";
import { Guide } from "../entrypoints/adsmanager.content/guideRunner";
import { locateWith } from "../entrypoints/adsmanager.content/locate";
import { stepsFor, type GuideEntry, type GuideStepItem } from "../lib/guide";
import { GUIDE } from "../lib/guideList";

const create = GUIDE.filter((e) => e.mode === "create");
const entry = (id: string) => create.find((e) => e.id === id)!;

describe("광고 만들기 창: 단계 건너뛰지 않기", () => {
  it("문구·제목 칸은 위쪽 단계 이름('문구'·'크리에이티브 설정')을 눌러 건너뛰지 않고, 창 안에서는 [다음]으로 간다", () => {
    for (const id of ["meta.creative.copy.text", "meta.creative.copy.headline"]) {
      const hints = entry(id).find.filter((f) => f.say);
      expect(hints.some((f) => "text" in f && f.text === "문구")).toBe(false);
      expect(hints.some((f) => "text" in f && f.text === "다음" && f.inDialog)).toBe(true);
      expect(hints.filter((f) => "textStarts" in f && f.textStarts === "크리에이티브 설정").every((f) => f.pageOnly)).toBe(true);
    }
  });

  it("사진 칸은 창 안의 '소스 URL' 칸이 보이거나, 창을 닫은 뒤 화면에 문구 칸이 생겨야 끝난다", () => {
    const done = entry("meta.ad.media").doneWhen ?? [];
    expect(done).toContainEqual({ placeholder: "광고 후 사람들이 방문하는 URL을 입력하세요", inDialog: true });
    expect(done).toContainEqual({ aria: "간단하게 광고를 소개하세요", pageOnly: true });   // 창 안 문구 칸으로는 끝나지 않는다
  });

  // 2026-11-26 실제 화면 (인스타그램 프로필 광고): 웹사이트 URL 칸이 사진을 고르기 전부터 광고 화면에 있다 → 예전엔 사진을 건너뛰었다
  it("화면에 웹사이트 URL 칸이 처음부터 있어도 사진 칸을 건너뛰지 않는다", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="button">크리에이티브 설정</div><input placeholder="광고 후 사람들이 방문하는 URL을 입력하세요">`;
    const seen: number[] = [];
    const g = new Guide(document, [{ entry: entry("meta.ad.media"), value: "사진" }, { entry: entry("meta.ad.website_url"), value: "https://x" }], 0, (i) => seen.push(i), 0);
    g.tick();
    expect(seen).toEqual([]);
    expect(g.view().text).toMatch(/^1\/3/);
    document.body.innerHTML = `<div role="button">크리에이티브 설정</div><div aria-label="간단하게 광고를 소개하세요" contenteditable="true"></div>`;   // 사진을 고르고 창을 닫음
    g.tick();
    expect(seen).toEqual([1]);
  });

  // 2026-11-26 실제 화면: 창 안 '크리에이티브 설정' 단계의 URL 칸에 넣은 값은 [완료] 뒤 광고 화면의 '웹사이트 URL'(필수)에 남지 않았다.
  // 광고 화면 칸에 넣은 값은 남고 창에도 '소스 URL'로 이어진다 → 사진 다음에 창을 마치고 광고 화면 칸에 넣는다
  it("웹사이트 주소는 사진 바로 다음, 창을 닫은 뒤 광고 화면 칸에 넣는다. 돈 확인도 창을 닫고 한다", () => {
    const ids = create.map((e) => e.id);
    expect(ids.indexOf("meta.ad.website_url")).toBe(ids.indexOf("meta.ad.media") + 1);
    expect(entry("meta.ad.website_url").outsideDialog).toBe(true);
    expect(entry("meta.money_check").outsideDialog).toBe(true);
  });

  it("창 안에 같은 이름 '다음'이 여럿이면 (사이트 링크 넘기기 화살표) 맨 아래 단추를 짚는다", () => {
    document.body.innerHTML = `<div role="dialog" id="d"><div role="button" id="arrow">다음</div><div id="foot"><div role="button" id="next">다음</div></div></div>`;
    const dlg = document.getElementById("d")!;
    expect(locateWith(dlg, [{ role: "button", text: "다음", inDialog: true, say: "x" }])?.el.id).toBe("next");
  });

  it("inDialog 힌트는 창 안에서만, pageOnly 힌트는 창이 없을 때만 찾는다", () => {
    document.body.innerHTML = `<div role="button">다음</div><div role="dialog" id="d"><div role="button">다음</div><div role="button">크리에이티브 설정</div></div>`;
    const dlg = document.getElementById("d")!;
    expect(locateWith(document, [{ role: "button", text: "다음", inDialog: true, say: "x" }])).toBeNull();
    expect(locateWith(dlg, [{ role: "button", text: "다음", inDialog: true, say: "x" }])?.el.parentElement).toBe(dlg);
    expect(locateWith(dlg, [{ role: "button", textStarts: "크리에이티브 설정", pageOnly: true, say: "x" }])).toBeNull();
  });
});

describe("창 마무리: [다 했어요] 뒤 다시 시도", () => {
  it("창 마무리 단추를 다 눌러 보고 멈춘 뒤 사장님이 [다 했어요]를 누르면, 다시 [다음]·[완료]를 눌러 본다", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="dialog" id="dlg"><div role="button" id="n" aria-disabled="true">다음</div></div>`;
    let presses = 0;
    document.getElementById("n")!.addEventListener("click", () => presses++);
    const e: GuideEntry = { id: "meta.money_check", mode: "create", page: { urlIncludes: "" }, find: [{ heading: "예산 및 일정" }], say: "돈 확인",
      done: "manual", fallback: { image: "", text: "" }, auto: "moneyCheck", level: "adset", outsideDialog: true };
    const steps: GuideStepItem[] = [{ entry: e, value: "3만 원" }];
    const g = new Guide(document, steps, 0, () => {}, 0);
    g.skipSurvey();
    g.setAuto(true);
    for (let i = 1; i <= 20; i++) { g.autoStep(i * 5000); g.tick(); }
    const before = presses;
    expect(g.view().waiting).toBe("owner");
    g.apply();   // [다 했어요]
    for (let i = 21; i <= 24; i++) { g.autoStep(i * 5000); g.tick(); }
    expect(presses).toBeGreaterThan(before);
  });
});

describe("접힌 구역 안의 칸 (연령: '타겟 추천' › '설정 표시')", () => {
  it("이 화면을 훑어 봐도 없던 칸이면, 또 끝까지 내려 보지 않고 보이는 '설정 표시'부터 누른다", () => {
    document.documentElement.lang = "ko";
    history.pushState({}, "", "/adsmanager/manage/adsets/edit");
    document.body.innerHTML = `<div id="sc" style="overflow-y:auto"><div role="button" id="show">설정 표시</div></div>`;
    const sc = document.getElementById("sc")!;
    Object.defineProperty(sc, "clientHeight", { value: 1000 });
    Object.defineProperty(sc, "scrollHeight", { value: 3000 });
    let shows = 0;
    document.getElementById("show")!.addEventListener("click", () => shows++);
    const e: GuideEntry = { id: "meta.adset.age_gender", mode: "create", page: { urlIncludes: "" }, say: "연령",
      find: [{ role: "button", textPattern: "^연령\\d" }, { role: "button", text: "설정 표시", say: "'설정 표시'를 눌러 연령 칸을 열게요" }],
      done: "manual", fallback: { image: "", text: "" }, auto: "ageGender", level: "adset" };
    const g = new Guide(document, [{ entry: e, value: "30~59세 · 여성" }], 0, () => {}, 0);
    g.skipSurvey();
    (g as unknown as { surveyedLevels: Set<string> }).surveyedLevels.add("adset");   // 광고 세트 화면은 이미 끝까지 훑음 (지도에 연령 없음)
    g.setAuto(true);
    g.autoStep(5000);   // 첫 걸음에 바로 누른다 (예전엔 화면을 끝까지 두 번 내려 본 뒤에야 눌렀다)
    expect(shows).toBe(1);
    expect(sc.scrollTop).toBe(0);
  });
});

// 2026-11-26 실제 화면: 문구 칸 앞의 준비 버튼을 3번 눌러도 칸이 안 생겨 사장님을 기다리다가, 사장님이 [다 했어요]를 누르면 문구를 넣지 않고 넘어갔다
describe("뭉치가 넣는 칸: 준비 단계에서 기다리다가", () => {
  const e: GuideEntry = { id: "meta.creative.copy.text", mode: "create", page: { urlIncludes: "" }, say: "문구를 넣을게요",
    find: [{ aria: "간단하게 광고를 소개하세요" }, { role: "button", text: "열기", say: "'열기'를 눌러 주세요" }],
    done: "manual", fallback: { image: "", text: "" }, auto: "type" };
  function waitingAtHint() {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="button">열기</div>`;
    const seen: number[] = [];
    const g = new Guide(document, [{ entry: e, value: "바삭한 쿠키" }, { entry: { ...e, id: "next" }, value: "x" }], 0, (i) => seen.push(i), 0);
    g.skipSurvey();
    g.setAuto(true);
    for (let i = 1; i <= 20; i++) { g.tick(); g.autoStep(i * 5000); }
    expect(g.view().waiting).toBe("owner");
    return { g, seen };
  }
  const field = () => { document.body.insertAdjacentHTML("beforeend", `<input aria-label="간단하게 광고를 소개하세요">`); return document.querySelector("input")!; };

  it("진짜 칸이 나타나면 [다 했어요] 없이 뭉치가 이어서 넣는다", async () => {
    const { g, seen } = waitingAtHint();
    const input = field();
    for (let i = 21; i <= 30; i++) { g.tick(); g.autoStep(i * 5000); }
    await new Promise((r) => setTimeout(r, 800));
    expect(input.value).toBe("바삭한 쿠키");
    expect(seen).toEqual([1]);
  });

  it("[다 했어요]는 준비 단계를 마친 것: 칸을 건너뛰지 않고, 나타난 칸에 넣는다", async () => {
    const { g, seen } = waitingAtHint();
    const input = field();
    g.apply();   // [다 했어요]
    expect(seen).toEqual([]);
    for (let i = 21; i <= 30; i++) { g.tick(); g.autoStep(i * 5000); }
    await new Promise((r) => setTimeout(r, 800));
    expect(input.value).toBe("바삭한 쿠키");
    expect(seen).toEqual([1]);
  });

  it("칸이 끝내 안 생기면 [다 했어요]를 한 번 더 눌러 넘어갈 수 있다", () => {
    const { g, seen } = waitingAtHint();
    g.apply();
    expect(seen).toEqual([]);
    for (let i = 21; i <= 40; i++) { g.tick(); g.autoStep(i * 5000); }
    expect(g.view().waiting).toBe("owner");
    g.apply();
    expect(seen).toEqual([1]);
  });
});

describe("웹사이트 URL: 창 안 같은 칸이 아니라 창을 닫은 뒤 광고 화면 칸에", () => {
  it("창 안에 같은 URL 칸이 있어도 넣지 않고, 창 맨 아래 '다음'을 눌러 창을 마친다", () => {
    document.documentElement.lang = "ko";
    const ph = "광고 후 사람들이 방문하는 URL을 입력하세요";
    document.body.innerHTML = `<input id="page" placeholder="${ph}"><div role="dialog" id="d"><input id="inner" placeholder="${ph}">
      <div role="button" id="arrow">다음</div><div role="button" id="next">다음</div></div>`;
    let nexts = 0;
    document.getElementById("next")!.addEventListener("click", () => { nexts += 1; document.getElementById("d")!.remove(); });
    const g = new Guide(document, [{ entry: entry("meta.ad.website_url"), value: "https://x.kr" }], 0, () => {}, 0);
    g.skipSurvey();
    g.setAuto(true);
    for (let i = 1; i <= 6; i++) { g.tick(); g.autoStep(i * 5000); }
    expect((document.getElementById("inner") as HTMLInputElement | null)?.value ?? "").toBe("");
    expect(nexts).toBe(1);
    expect((document.getElementById("page") as HTMLInputElement).value).toBe("https://x.kr");   // 창이 닫힌 뒤 광고 화면 칸에 넣었다
  });
});

// 2026-11-26 실제 화면 (초안 120257356838250583): 광고 화면 '기본 문구' 칸에 aria-label이 없고, '간단하게 광고를 소개하세요'는
// 칸 위에 보이는 안내 글자(span)였다. 그 글자 바로 옆 textarea가 진짜 칸. 창 안에서는 이 방법으로 찾지 않는다 (광고 화면 칸에만 넣음)
describe("문구 칸: 이름표 없이 안내 글자만 있는 화면", () => {
  const copy = () => entry("meta.creative.copy.text");
  it("광고 화면에서는 안내 글자 옆 칸을 찾는다", () => {
    document.body.innerHTML = `<div><span>기본 문구</span><div><span>간단하게 광고를 소개하세요</span><textarea id="t"></textarea></div></div>`;
    expect(locateWith(document, copy().find)?.el.id).toBe("t");
  });
  it("열린 창 안에서는 이 방법으로 찾지 않는다", () => {
    document.body.innerHTML = `<div role="dialog" id="d"><span>간단하게 광고를 소개하세요</span><textarea id="t"></textarea></div>`;
    expect(locateWith(document.getElementById("d")!, copy().find)?.el.id).not.toBe("t");
  });
});

// 2026-11-26 실제 화면 (초안 120257356838250583): 세팅값이 '여러 장 (슬라이드)'인데 뭉치는 늘 '단일 이미지 또는 동영상'을 짚었다
describe("형식 칸: 세팅값에 맞는 선택지", () => {
  const fmt = GUIDE.find((e) => e.mode === "create" && e.id === "meta.ad.format")!;
  const page = `<span id="a">단일 이미지 또는 동영상</span><input type="radio" aria-labelledby="a" id="single">
    <span id="b">슬라이드</span><input type="radio" aria-labelledby="b" id="slide">`;
  const pick = (value: string) => {
    document.body.innerHTML = page;
    const item = stepsFor("create", [fmt], [{ fieldId: "meta.ad.format", label: "형식", value }], [])[0]!;
    return locateWith(document, item.entry.find)?.el.id;
  };
  it("'여러 장 (슬라이드)'면 슬라이드를 짚는다", () => expect(pick("여러 장 (슬라이드)")).toBe("slide"));
  it("'1장 (단일 이미지)'면 단일 이미지를 짚는다", () => expect(pick("1장 (단일 이미지)")).toBe("single"));
});

// 2026-11-26 실제 화면 (초안 120257356971480583): 형식이 슬라이드면 '크리에이티브 설정' 대신 '슬라이드 추가'(0/10개)가 있고,
// 사진·제목을 장마다 넣는다. 뭉치는 사진 칸을 사진 없이 지나갔다 → 슬라이드면 사진·제목은 사장님이 직접 ('슬라이드 추가'를 짚고 기다림)
describe("슬라이드: 사진·제목은 사장님이 직접", () => {
  const settings = (format: string) => [
    { fieldId: "meta.ad.format", label: "형식", value: format },
    { fieldId: "meta.ad.media", label: "사진", value: "정사각형 사진" },
    { fieldId: "meta.creative.copy.headline", label: "제목", value: "수제 쿠키" },
  ];
  const ids = ["meta.ad.media", "meta.creative.copy.headline"];
  const items = (format: string) => stepsFor("create", create.filter((e) => ids.includes(e.id)), settings(format), []);

  it("슬라이드면 두 칸 다 사장님 차례이고 '슬라이드 추가'를 짚는다 (하위 단계 없음)", () => {
    for (const s of items("여러 장 (슬라이드)")) {
      expect(s.entry.auto).toBe("owner");
      expect(s.entry.stages).toBeUndefined();
      expect(s.entry.doneWhen).toBeUndefined();
      expect(s.entry.find).toEqual([{ role: "button", text: "슬라이드 추가" }]);
      expect(s.entry.say).toMatch(/^여기는 사장님이 직접/);
    }
    expect(items("여러 장 (슬라이드)")[0]!.entry.say).toContain("2장 이상");   // 메타: '슬라이드를 2개 이상 추가하세요' (2026-11-26 실제 화면)
  });

  it("단일 이미지면 지금 그대로", () => {
    const [media, head] = items("1장 (단일 이미지)");
    expect(media!.entry.stages?.length).toBe(3);
    expect(head!.entry.auto).toBe("type");
  });

  it("슬라이드 화면에서 뭉치는 사진 칸에서 멈춰 기다린다 (지나가지 않음)", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="button">슬라이드 추가</div><div aria-label="간단하게 광고를 소개하세요" contenteditable="true"></div>`;
    const seen: number[] = [];
    const g = new Guide(document, items("여러 장 (슬라이드)"), 0, (i) => seen.push(i), 0);
    g.skipSurvey();
    g.setAuto(true);
    for (let i = 1; i <= 10; i++) { g.tick(); g.autoStep(i * 5000); }
    expect(seen).toEqual([]);
    expect(g.view().waiting).toBe("owner");
  });
});

// 2026-11-26 실제 화면: '수동 트래픽 캠페인'을 고르는 동안 말풍선 번호가 이미 '2/18'이었다 → 만들기 창은 끝까지 1번 칸
describe("캠페인 만들기 창은 1번 칸", () => {
  it("트래픽 → 계속 → 수동 트래픽 캠페인 → 계속까지 1번, 캠페인 화면이 뜨면 2번 ('+ 만들기'는 한 번만)", () => {
    document.documentElement.lang = "ko";
    document.body.innerHTML = `<div role="button" id="make">만들기</div>`;
    let makes = 0;
    const page1 = `<div role="dialog" id="d"><span id="t">트래픽</span><input type="radio" aria-labelledby="t" id="traffic"><div role="button" id="go1">계속</div></div>`;
    const page2 = `<div role="dialog" id="d"><div><div><label><input type="radio" id="manual">수동 트래픽 캠페인</label></div></div><div role="button" id="go2">계속</div></div>`;
    document.getElementById("make")!.addEventListener("click", () => {
      makes += 1;
      document.body.insertAdjacentHTML("beforeend", page1);
      document.getElementById("go1")!.addEventListener("click", () => {
        if (!(document.getElementById("traffic") as HTMLInputElement).checked) return;
        document.getElementById("d")!.outerHTML = page2;
        document.getElementById("go2")!.addEventListener("click", () => {
          if (!(document.getElementById("manual") as HTMLInputElement).checked) return;
          document.getElementById("d")!.remove();
          document.body.insertAdjacentHTML("beforeend", `<span id="c">카테고리</span><div role="combobox" aria-labelledby="c"></div>`);
        });
      });
    });
    const objective = create.find((e) => e.id === "meta.campaign.objective")!;
    const special = create.find((e) => e.id === "meta.campaign.special_category")!;
    const seen: number[] = [];
    const g = new Guide(document, [{ entry: objective, value: "트래픽" }, { entry: special, value: "아니요" }], 0, (i) => seen.push(i), 0);
    g.skipSurvey();
    g.setAuto(true);
    const counts: number[] = [];
    for (let i = 1; i <= 60 && !seen.length; i++) { g.tick(); g.autoStep(i * 5000); counts.push(g.view().index); }
    expect(makes).toBe(1);
    expect(document.querySelector("[role=combobox]")).not.toBeNull();   // 창을 다 지나 캠페인 화면('카테고리')이 뜬 뒤에야 2번
    expect(seen).toEqual([1]);
    expect(counts.slice(0, -1).every((n) => n === 0)).toBe(true);
    expect(special.find.some((f) => f.say)).toBe(false);   // 2번 칸엔 만들기 창 안내가 없다
  });
});
