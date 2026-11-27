// 분석 페이지 최종안 (2026-11-27, 광고어시스턴트_분석페이지_최종안.html · 예산 슬라이더 A): 업로드 → ① 결론 → ② 왜 그런지 → ③ 준비하기
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import oneSet from "./fixtures/one_set.json";
import oven from "./fixtures/oven.json";
import twoSets from "./fixtures/two_sets_a_wins.json";

const ok = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
const sim = { budget: 30000, runs: 200000, arm: "B", impressions: { median: 5000, lo: 4500, hi: 5600 },
  link_clicks: { median: 100, lo: 73, hi: 133 }, visits: { median: 78, lo: 55, hi: 108 },
  histogram: [{ lo: 60, hi: 80, count: 100000 }, { lo: 80, hi: 140, count: 100000 }], limits: "한계" };
const JUDGE: Record<number, number> = { 5000: 0.69, 6000: 0.89, 10000: 0.9995 };   // 서버 judge_chance 오븐로그 값

afterEach(() => { vi.unstubAllGlobals(); window.history.replaceState(null, "", "/"); });

function show(result: unknown = oven) {
  const f = vi.fn((url: string, init?: RequestInit) => {
    if (String(url).includes("/simulate/grid")) {
      const days = JSON.parse(init!.body as string).days as number;
      const budgets = [...Array.from({ length: 28 }, (_, i) => 3000 + i * 1000), ...Array.from({ length: 14 }, (_, i) => 35000 + i * 5000)];
      const rows = budgets.map((b) => ({ budget: b,
        visits: { median: (b * 16) / 6000, lo: (b * 11) / 6000, hi: (b * 22) / 6000 }, judge: b >= 10000 ? 0.999 : b >= 6000 ? 0.89 : 0.69,
        hard: b < 6000, tried: b <= 5308, daily_tried: b / days <= 2643, below_daily_min: b / days < 1336, daily_min: 1336, daily_max: 2643 }));
      return ok({ arm: "B", days, rows, mid: 30000, many_from: 50000 });
    }
    if (String(url).includes("/simulate")) {
      const b = JSON.parse(init!.body as string);
      const daily = b.days ? b.budget / b.days : null;
      return ok({ ...sim, budget: b.budget, judge: JUDGE[b.budget] ?? 0.5, tried: b.budget <= 5308, days: b.days, daily, daily_max: 2643,
        daily_tried: daily == null || daily <= 2643, daily_min: 1336, below_daily_min: daily != null && daily < 1336,
        next_test: { total: 100000, per_set_lo: 4000, per_set_hi: 10000, share_lo: 0.076, share_hi: 0.2, source: "Feit" } });
    }
    return ok(result);
  });
  vi.stubGlobal("fetch", f);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "베이커리 실험 2 예시" }));   // 오븐로그 = 베이커리 실험 2 (최종안(1))
  return f;
}
const click = async (name: RegExp | string) => fireEvent.click(await screen.findByRole("button", { name }));
const open = (label: RegExp | string) => fireEvent.click(screen.getByText(label, { selector: "summary span" }));
const h1 = (name: string) => screen.findByRole("heading", { level: 1, name });
const upload = () => fireEvent.change(screen.getByLabelText("광고 결과 파일 (CSV)"), { target: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });

describe("⓪ 업로드", () => {
  it("one file box, a settings status line, two bakery examples, one 도움말 fold, and [분석 시작] at the bottom", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "돌려 본 광고 결과를 올려 주세요" })).toBeTruthy();
    expect(screen.getByText("파일 하나만 올리면, 다음에 바꿔 볼 칸 1개를 뭉치가 찾아 드려요")).toBeTruthy();
    expect(screen.getByText("광고 결과 파일(CSV·엑셀)을 여기로 끌어다 놓기")).toBeTruthy();
    expect(screen.getByText("새 분석")).toBeTruthy();
    for (const n of ["베이커리 실험 1 예시", "베이커리 실험 2 예시"]) expect(screen.getByRole("button", { name: n })).toBeTruthy();
    expect(screen.getAllByText("도움말", { selector: "summary span" }).length).toBe(1);
    expect(screen.getByText("결과 파일 받는 법 · 꼭 있어야 하는 열 · 광고를 아직 안 돌렸을 때")).toBeTruthy();
    expect(screen.getByText("파일을 올리면 눌러져요")).toBeTruthy();
    expect((screen.getByRole("button", { name: "분석 시작 ▶" }) as HTMLButtonElement).disabled).toBe(true);
    expect(document.body.textContent).not.toMatch(/20만 번|₩|오븐로그|희수|모닝빈/);
  });

  it("the settings link opens 도움말 with the 5 questions; answers go with the upload", async () => {
    const f = vi.fn((_u: string, _i?: RequestInit) => ok(oven));
    vi.stubGlobal("fetch", f);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "내 광고 설정 5개만 직접 입력하기 ▸" }));
    for (const g of ["캠페인 목표", "세트당 하루 예산", "연령", "노출 위치", "소재 형식"]) expect(screen.getByRole("group", { name: g })).toBeTruthy();
    fireEvent.click(screen.getByLabelText("트래픽"));
    upload();
    await waitFor(() => expect(f.mock.calls.some(([u, o]) => String(u).endsWith("/analysis") && JSON.parse(String((o?.body as FormData).get("settings"))).hasOwnProperty("meta.campaign.objective"))).toBe(true));
  });

  it("the settings link reopens 도움말 every time, even after it was closed", () => {
    vi.stubGlobal("fetch", vi.fn(() => ok({})));
    render(<App />);
    const link = screen.getByRole("button", { name: "내 광고 설정 5개만 직접 입력하기 ▸" });
    fireEvent.click(link);
    expect(screen.getByRole("group", { name: "캠페인 목표" })).toBeTruthy();
    open("도움말");   // 닫기
    expect(screen.queryByRole("group", { name: "캠페인 목표" })).toBeNull();
    fireEvent.click(link);
    expect(screen.getByRole("group", { name: "캠페인 목표" })).toBeTruthy();
  });

  it("from the extension: says it was received instead of the link, and uploads with the key", async () => {
    window.history.replaceState(null, "", "/#s=K3yK3yK3yK3yK3y");
    const f = vi.fn((url: string, init?: RequestInit) => ok(String(url).includes("/settings/") ? { count: 14, settings: {} } : init?.method === "POST" ? oven : {}));
    vi.stubGlobal("fetch", f);
    render(<App />);
    expect(await screen.findByText(/내 광고 설정은 확장 프로그램에서 자동으로 받았어요/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /5개만 직접 입력하기/ })).toBeNull();
    upload();
    await waitFor(() => expect(f.mock.calls.some(([u, o]) => String(u).endsWith("/analysis") && (o?.body as FormData).get("settings_key") === "K3yK3yK3yK3yK3y")).toBe(true));
  });

  it("a good file is checked in place and [분석 시작] turns on", async () => {
    vi.stubGlobal("fetch", vi.fn(() => ok(oven)));
    render(<App />);
    upload();
    expect(await screen.findByText(/✓ x\.csv · \d+줄 확인/)).toBeTruthy();
    const start = screen.getByRole("button", { name: "분석 시작 ▶" }) as HTMLButtonElement;
    expect(start.disabled).toBe(false);
    fireEvent.click(start);
    expect(await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요")).toBeTruthy();
  });

  it("a blocked file shows the fix right under the file box and keeps [분석 시작] off", async () => {
    const block = { level: "block", mark: "■", kind: "missing_column", text: "'랜딩 페이지 조회' 열이 없어요", todo: "내보내기에서 이 열을 추가해 다시 받아 주세요.", screen: "AN-00" };
    vi.stubGlobal("fetch", vi.fn(() => ok({ ...oven, blocked: true, alerts: [block] })));
    render(<App />);
    upload();
    expect((await screen.findByRole("alert")).textContent).toContain("다시 받아 주세요");
    expect((screen.getByRole("button", { name: "분석 시작 ▶" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("a server error is linked to the file input", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ error: "다시 내보내 주세요" }), { status: 400 }))));
    render(<App />);
    upload();
    const alert = await screen.findByRole("alert");
    expect(screen.getByLabelText("광고 결과 파일 (CSV)").getAttribute("aria-describedby")).toBe(alert.id);
  });

  it("the not-yet checklist inside 도움말 counts what is left", () => {
    render(<App />);
    open("도움말");
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes.length).toBe(4);
    fireEvent.click(boxes[0]!);
    expect(screen.getByText("1/4")).toBeTruthy();
  });

  it("example 1 (first button) is the heesu experiment; the result is named 베이커리 실험 1", async () => {
    const f = vi.fn((_u: string) => ok(oven));
    vi.stubGlobal("fetch", f);
    render(<App />);
    const [one, two] = screen.getAllByRole("button", { name: /베이커리 실험 \d 예시/ });
    expect([one!.textContent, two!.textContent]).toEqual(["🧪베이커리 실험 1 예시", "🍪베이커리 실험 2 예시"]);
    fireEvent.click(one!);
    await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요");
    expect(f.mock.calls.some(([u]) => String(u) === "/analysis/example?name=heesu")).toBe(true);
    expect(screen.getByText(/베이커리실험1_메타AB/)).toBeTruthy();
  });
});

describe("① 결론", () => {
  it("one conclusion card (button + text link), two summary cards, no folds", async () => {
    show();
    expect(await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요")).toBeTruthy();
    expect(screen.getByText("나머지 칸은 그대로 둬야 무엇 덕분인지 알 수 있어요")).toBeTruthy();
    const card = screen.getByRole("region", { name: "테스트할 칸" });
    expect(within(card).getByText("광고 › 형식 · 미디어")).toBeTruthy();
    expect(within(card).getByText(/^세로\(9:16\) 소재를 넣은 세트를/).textContent).toBe("세로(9:16) 소재를 넣은 세트를 하나 더 만들어 같이 돌려 보세요");
    expect(within(card).getByText("테스트 제안")).toBeTruthy();
    expect(card.textContent).toContain("돈의 72%가 인스타 릴스(세로 화면)에서 나갔는데, 세로 소재가 없었어요.");
    expect(within(card).getByText("세로 소재가 방문자를 더 데려올지는 이번 테스트로 확인해요.")).toBeTruthy();
    expect(within(card).getByRole("button", { name: "왜 이 칸인지 보기" })).toBeTruthy();
    const rest = screen.getByRole("list", { name: "나머지 칸" });
    expect(within(rest).getByText("✓ 그대로 두세요")).toBeTruthy();
    expect(within(rest).getByText("노출 위치 = 직접 고르기(수동)")).toBeTruthy();
    expect(within(rest).getByText("광고비가 확실히 쌌어요")).toBeTruthy();   // 79%(방문자) 대신 확실한 근거
    expect(within(rest).getByText("확실해요")).toBeTruthy();
    expect(within(rest).getByText("다음엔 이렇게")).toBeTruthy();
    expect(within(rest).getByText("시작은 하루 여유 있게")).toBeTruthy();
    expect(within(rest).getByText("첫날이 비었고, 알림 신청은 1건뿐이라 행동은 아직 몰라요")).toBeTruthy();
    expect(document.querySelector("main details")).toBeNull();
    expect(document.querySelector("main")!.textContent).not.toMatch(/손님|₩|유력|보류|채택/);
  });

  it("[이 테스트 준비하기 →] goes straight to ③; '왜 이 칸인지 보기' goes to ②", async () => {
    show();
    await click("이 테스트 준비하기 →");
    expect(await h1("이 테스트를 준비해요")).toBeTruthy();
    await click(/① 결론/);
    await click("왜 이 칸인지 보기");
    expect(await h1("왜 이 칸이에요?")).toBeTruthy();
  });

  it("alert bar: only the most important line (no counts, no [모두 보기]); none on ③", async () => {
    show();
    const bar = await screen.findByRole("region", { name: "알림" });
    expect(within(bar).getByText(/11\/17은 광고가 안 나가서 그날은 빼고 봤어요/)).toBeTruthy();
    expect(within(bar).queryByRole("button")).toBeNull();
    expect(bar.textContent).not.toMatch(/주의 2|참고 1/);
    await click("이 테스트 준비하기 →");
    await h1("이 테스트를 준비해요");
    expect(screen.queryByRole("region", { name: "알림" })).toBeNull();
  });

  it("stepper: three steps; ③ can be reached directly, ② only after ①; the hash tells the side panel the step", async () => {
    show();
    await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요");
    expect((screen.getByRole("button", { name: /② 왜 그런지/ }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: /③ 준비하기/ }) as HTMLButtonElement).disabled).toBe(false);
    const q = () => new URLSearchParams(window.location.hash.slice(1));
    expect(q().get("code")).toBe(oven.code);
    expect(q().get("step")).toBe("AN-01");
    await click("왜 이 칸인지 보기");
    await waitFor(() => expect(q().get("step")).toBe("AN-02"));
    await click("준비하기 ▶");
    await waitFor(() => expect(q().get("step")).toBe("AN-06"));
  });

  it("a blocked result shows no conclusion and cannot jump ahead", async () => {
    const block = { level: "block", mark: "■", kind: "not_same_days", text: "두 세트를 같은 날 같이 돌리지 않아서 비교할 수 없어요.", todo: "같은 날 같이 시작한 기간만 골라 다시 내보내 주세요.", screen: "AN-00" };
    show({ ...oven, blocked: true, alerts: [block, ...oven.alerts] });
    expect(await h1("이 파일로는 아직 결론을 낼 수 없어요")).toBeTruthy();
    expect(screen.queryByRole("region", { name: "테스트할 칸" })).toBeNull();
    expect((screen.getByRole("button", { name: /③ 준비하기/ }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("browser [뒤로] goes to the previous step instead of leaving the result", async () => {
    show();
    await click("왜 이 칸인지 보기");
    await h1("왜 이 칸이에요?");
    window.history.replaceState(null, "", window.location.pathname + "#code=" + oven.code + "&step=AN-01");
    fireEvent.popState(window);
    expect(await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요")).toBeTruthy();
  });

  it("browser [뒤로] on ① goes back to the upload screen", async () => {
    show();
    await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요");
    window.history.replaceState(null, "", window.location.pathname);
    fireEvent.popState(window);
    expect(await screen.findByRole("heading", { level: 1, name: "돌려 본 광고 결과를 올려 주세요" })).toBeTruthy();    window.history.replaceState(null, "", window.location.pathname + "#code=" + oven.code + "&step=AN-01");   // [앞으로]
    fireEvent.popState(window);
    expect(await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요")).toBeTruthy();
  });

  it("[다른 파일] (small link) asks first, because the result would be lost", async () => {
    show();
    await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요");
    const confirm = vi.fn(() => false);
    vi.stubGlobal("confirm", confirm);
    fireEvent.click(screen.getByRole("button", { name: "다른 파일" }));
    expect(confirm).toHaveBeenCalled();
    expect(screen.getByRole("heading", { level: 1, name: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요" })).toBeTruthy();
  });
});

describe("①b 세트가 1개일 때", () => {
  it("same conclusion card, but 'no comparison' line, two baseline cards and the info box", async () => {
    show(oneSet);
    expect(await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요")).toBeTruthy();
    expect(screen.getByText(/세트가 1개라 비교할 대상이 없었어요/)).toBeTruthy();
    const cards = screen.getByRole("list", { name: "기준값과 비교" });
    expect(within(cards).getByText("누른 뒤 페이지 도착")).toBeTruthy();
    expect(within(cards).getByText("43% (범위 28%~60%) · 기준 60%")).toBeTruthy();
    expect(within(cards).getAllByText("– 아직 몰라요").length).toBe(2);
    expect(screen.getByText(/'확실해요 \/ ○ 쪽이에요'가 나오지 않아요/)).toBeTruthy();
    expect(screen.queryByRole("list", { name: "나머지 칸" })).toBeNull();
  });
});

describe("② 왜 그런지", () => {
  async function why(result: unknown = oven) {
    show(result);
    await click("왜 이 칸인지 보기");
    await h1("왜 이 칸이에요?");
  }

  it("three reasons in the final order (릴스 → 방문 1명당 비용 → 광고비 범위), each with one graph and a badge, then one 더 자세히", async () => {
    await why();
    expect(screen.getByText("이유 3가지와 그 근거 숫자예요. 위에서부터 읽으면 돼요")).toBeTruthy();
    const reasons = [...document.querySelectorAll("main section")].filter((x) => x.querySelector("figure"));
    expect(reasons.map((x) => x.querySelector("p")!.firstChild!.textContent)).toEqual([
      "돈이 인스타 릴스로 갔는데, 세로 소재가 없었어요", "같은 돈으로 방문자를 B(수동)가 더 데려왔어요", "광고비 자체는 확실히 B가 쌌어요"]);
    expect(screen.getByText("세트당 5,308원으로 방문자 A 10명 · B 14명")).toBeTruthy();
    expect(screen.getByText(/B가 나을 확률/).textContent).toMatch(/B가 나을 확률 79% · 날짜가 쌓일수록 26% → 65% → 79%로 B 쪽으로 굳어지는 중/);
    expect(screen.getByText("광고 1,000번 보여 주는 데 드는 돈 · 두 범위가 안 겹쳐요")).toBeTruthy();
    expect(screen.getByText(/^A 적게 [\d,]+원 ~ 많이 [\d,]+원 · B 적게/)).toBeTruthy();
    expect(screen.getByText(/메타는 '자동'을 권했지만, 우리가 돌려 본 2번 모두 수동이 쌌어요 \(베이커리 실험 1은 36%\) → 노출 위치는 지금처럼 그대로/)).toBeTruthy();
    expect(screen.getByText("확실해요")).toBeTruthy();
    expect(screen.getByText("B 쪽이에요")).toBeTruthy();
    expect(screen.getByText("들어온 뒤 행동(알림 신청 1건)은 아직 몰라요")).toBeTruthy();
    expect(screen.getAllByText("더 자세히", { selector: "summary span" }).length).toBe(1);
    expect(screen.getByText("단계별 신호 · 노출 위치별 클릭 · 내 세팅 칸별 상태 · 계산 방법")).toBeTruthy();
  });

  it("with settings that lack a vertical creative, reason 1 says so and names the creative", async () => {
    const c = { ...oven.matrix.change, now: "정사각 1장 + AI 이미지 2장", reason: "돈의 72%가 인스타 릴스(세로 화면)에서 나갔는데, 세로 소재가 없었어요." };
    await why({ ...oven, matrix: { ...oven.matrix, change: c } });
    expect(screen.getByText("돈이 인스타 릴스로 갔는데, 세로 소재가 없었어요")).toBeTruthy();
    expect(screen.getByText("소재는 정사각 1장 + AI 이미지 2장이었어요 → 이번에 테스트할 칸")).toBeTruthy();
  });

  it("더 자세히 keeps the old screens: funnel table (with Meta rankings), placements, settings, method", async () => {
    const text = "메타 품질 순위: A(자동) 평균 이하 — 소재 품질이 낮게 보여요 → 소재 · 형식";
    await why({ ...oven, matrix: { ...oven.matrix, rankings: true, meta_signals: [{ row: "1", key: "quality", text }] } });
    open("더 자세히");
    expect(within(screen.getByRole("region", { name: "메타 진단" })).getByText(`① ${text}`)).toBeTruthy();
    expect(screen.getByText("보이는 값 ↓ · 누르는 정도 ✓ · 도착 ✓ · 행동 –")).toBeTruthy();
    expect(screen.getAllByText("참고만").length).toBeGreaterThan(0);
    expect(screen.getByRole("tablist", { name: "상태로 거르기" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "방문 1명당 비용" })).toBeTruthy();
  });

  it("when A wins, the numbers are told from A's side", async () => {
    await why(twoSets);
    expect(screen.getByText(/A가 나을 확률/).textContent).toMatch(/A가 나을 확률 95%/);
    expect(screen.queryByText(/B가 나을 확률/)).toBeNull();
  });

  it("a single ad set (①b): '기준 대비' reasons with ✓ / ↓ / – instead of verdict badges", async () => {
    await why(oneSet);
    expect(screen.getByText(/누른 뒤 페이지 도착: 43% \(범위 28%~60%\)/)).toBeTruthy();
    expect(screen.getAllByText("– 아직 몰라요").length).toBeGreaterThan(0);
    expect(screen.queryByText(/확실해요|쪽이에요/)).toBeNull();
  });
});

describe("③ 준비하기 (예산 슬라이더, 최종안(1))", () => {
  async function prep(result: unknown = oven) {
    const f = show(result);
    await click("이 테스트 준비하기 →");
    await h1("이 테스트를 준비해요");
    return f;
  }
  const slider = async () => (await screen.findByRole("slider", { name: "세트당 총액" })) as HTMLInputElement;
  const key = (el: HTMLElement, k: string, n = 1) => { for (let i = 0; i < n; i++) fireEvent.keyDown(el, { key: k }); };

  it("one slider from 3천 to 10만 원 starting at the recommended amount, period chips, and the visitor range as the answer", async () => {
    const f = await prep();
    expect(screen.getByText("지금 세트는 그대로 두고, 세로 소재를 넣은 세트 하나만 더 만들면 돼요")).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "지금 세트" })).getByText("정사각 1 + AI 이미지 2")).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "지금 세트" })).getByText("노출 위치 직접 고르기 · 나머지 그대로")).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "새 세트" })).getByText("광고 › 형식 · 미디어")).toBeTruthy();
    expect(screen.getByRole("heading", { name: /세트당 얼마로 돌릴까요\?/ })).toBeTruthy();
    const s = await slider();
    expect(s.getAttribute("aria-valuemin")).toBe("3000");
    expect(s.getAttribute("aria-valuemax")).toBe("100000");
    expect(s.getAttribute("aria-valuetext")).toBe("6,000원 (추천)");
    expect(screen.getByText("추천")).toBeTruthy();
    for (const t of ["3천", "1만", "3만", "5만", "10만 원"]) expect(screen.getByText(t)).toBeTruthy();
    expect(screen.getByText("3만 원까지는 1,000원씩, 그 위는 5,000원씩 움직여요")).toBeTruthy();
    expect((screen.getByRole("radio", { name: "4일" }) as HTMLInputElement).checked).toBe(true);
    expect(screen.getByText("하루 약 1,500원")).toBeTruthy();
    expect(screen.getByText("방문자 보통 16명")).toBeTruthy();
    expect(screen.getByText("(적게 11명 ~ 많이 22명)")).toBeTruthy();
    expect(screen.getByText("지금 세팅(B 수동)으로 계산 · 10번 중 8번은 이 안에 들어요 · 세로 소재 효과는 아직 재 본 적 없어요")).toBeTruthy();
    expect(screen.queryByText(/판단하기 어려워요/)).toBeNull();
    expect(screen.getByText(/금액은/).textContent).toContain("결제·게시를 하지 않아요");
    key(s, "ArrowRight", 6);   // 1,000원씩
    expect(s.getAttribute("aria-valuetext")).toBe("12,000원");
    expect(screen.getByText("방문자 보통 32명")).toBeTruthy();
    expect(screen.getAllByText("가설").length).toBeGreaterThan(0);   // 하루 3,000원 > 써 본 최대 2,643원
    key(s, "End");
    expect(s.getAttribute("aria-valuetext")).toBe("100,000원");
    expect(screen.getByText("금액이 커지면 같은 사람에게 여러 번 보여서, 방문자가 금액만큼 늘지 않을 수 있어요")).toBeTruthy();
    key(s, "ArrowLeft");
    expect(s.getAttribute("aria-valuetext")).toBe("95,000원");   // 3만 원 위는 5,000원씩
    expect(f.mock.calls.filter(([u]) => String(u).includes("/simulate/grid")).length).toBe(1);   // 결과표는 기간마다 한 번
    fireEvent.click(screen.getByRole("radio", { name: "7일" }));
    await waitFor(() => expect(f.mock.calls.filter(([u]) => String(u).includes("/simulate/grid")).length).toBe(2));
  });

  it("under Meta's daily minimum warns with what to do; an amount the owner picked stays, but 7 days shows the warning for it", async () => {
    await prep();
    const s = await slider();
    key(s, "ArrowLeft");   // 5,000원
    expect(screen.getByText(/하루 1,250원은 메타 하루 최소\(약 1,336원\)보다 적어요 → 광고가 안 나갈 수 있어요\. 기간을 줄이거나 총예산을 늘려 주세요/)).toBeTruthy();
    key(s, "ArrowRight");   // 6,000원 → 4일이면 괜찮음
    expect(screen.queryByText(/하루 최소/)).toBeNull();
    fireEvent.click(screen.getByRole("radio", { name: "7일" }));
    expect(await screen.findByText(/하루 860원은 메타 하루 최소/)).toBeTruthy();   // 사장님이 고른 금액은 그대로
  });

  it("untouched slider follows the recommendation: 7일 moves it to the smallest amount over the daily minimum; checklist says 7일", async () => {
    await prep();
    const s = await slider();
    expect(s.getAttribute("aria-valuetext")).toBe("6,000원 (추천)");
    expect(screen.getByText("4일 동안 그대로 두기")).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "7일" }));
    await waitFor(() => expect(s.getAttribute("aria-valuetext")).toBe("10,000원 (추천)"));   // 1,336 × 7 = 9,352원 → 10,000원
    expect(screen.queryByText(/메타 하루 최소/)).toBeNull();
    expect(screen.getByText("7일 동안 그대로 두기")).toBeTruthy();
  });

  it("the price bubble stays inside the card at both ends", async () => {
    await prep();
    const s = await slider();
    key(s, "Home");
    expect(screen.getByText("3,000원", { selector: "span.absolute" }).className).toMatch(/translate-x-\[0\.75rem\]/);
    key(s, "End");
    expect(screen.getByText("100,000원", { selector: "span.absolute" }).className).toMatch(/calc\(100%-0\.75rem\)/);
  });

  it("🔎 inside the budget box compares 2x and 4x of the picked amount with solid/dotted lines, from the result table (no extra server calls)", async () => {
    const f = await prep();
    const before = f.mock.calls.filter(([u]) => /\/simulate$/.test(String(u))).length;
    expect(screen.getByText("금액 2배·4배 비교 · 실선/점선 뜻 · 계산 방법")).toBeTruthy();
    open("이 숫자는 어떻게 나왔나요?");
    expect(await screen.findByRole("heading", { name: "금액을 2배·4배로 하면" })).toBeTruthy();
    expect(await screen.findByText("12,000원")).toBeTruthy();
    expect(screen.getByText(/실선 = 써 본 금액 · 점선 = 써 본 적 없는 금액/)).toBeTruthy();
    expect(screen.getAllByText("이 숫자는 어떻게 나왔나요?").length).toBe(1);
    expect(screen.getByText("보통 16명 (적게 11명 ~ 많이 22명)")).toBeTruthy();   // 6,000원 · 써 본 금액 (하루 1,500원)
    expect(screen.getByText("보통 64명 (적게 44명 ~ 많이 88명)")).toBeTruthy();   // 24,000원 = 6,000원 × 4
    expect(screen.getAllByText("가설").length).toBeGreaterThan(0);                 // 24,000원은 하루 6,000원 > 2,643원
    key(await slider(), "ArrowRight", 3);
    expect(screen.getByText("보통 48명 (적게 33명 ~ 많이 66명)")).toBeTruthy();   // 슬라이더를 따라 바로 (9,000원 × 2 = 18,000원)
    expect(f.mock.calls.filter(([u]) => /\/simulate$/.test(String(u))).length).toBe(before);
    expect(screen.getByText("계산 방법")).toBeTruthy();
  });

  it("the 4-item checklist (final wording) and send with the picked budget; the code stays on screen", async () => {
    await prep();
    expect(screen.getByRole("heading", { name: /돌리기 전에 4가지만/ })).toBeTruthy();
    for (const t of ["두 세트를 같은 날 같이 시작, 시작은 하루 여유 있게", "바꾸는 칸은 형식 · 미디어 1개만", "4일 동안 그대로 두기"]) expect(screen.getByText(t)).toBeTruthy();
    expect(screen.getByText("딱 하루만").tagName).toBe("B");
    expect(document.body.textContent).not.toMatch(/ALT-/);
    key(await slider(), "ArrowRight", 4);
    vi.stubGlobal("navigator", { clipboard: { writeText: () => Promise.resolve() } });
    fireEvent.click(screen.getByRole("button", { name: "확장 프로그램으로 보내기 →" }));
    expect(await screen.findByText(/오른쪽 광고 어시스턴트 패널로 보냈어요/)).toBeTruthy();
    expect(new URLSearchParams(window.location.hash.slice(1)).get("budget")).toBe("10000");
    expect((await screen.findByText(/패널로 보냈어요 · 세트당 10,000원 · 코드/)).textContent).toContain(oven.code);
  });

  it("one 더 자세히 fold: Test & Roll, backtest and evidence (6 virtual cases not used for the verdict)", async () => {
    await prep();
    expect(screen.getByText("전체 예산으로 정하기 (Test & Roll) · 예측이 맞았나 · 근거")).toBeTruthy();
    open("더 자세히");
    expect(await screen.findByRole("heading", { name: "다음 테스트에 쓸 돈 (Test & Roll)" }, { timeout: 2000 })).toBeTruthy();
    expect(screen.getByText(/예측이 맞았나\? \(검증\)/)).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "가상 케이스" }));
    expect(screen.getByText(/판정에는 쓰지 않아요/)).toBeTruthy();
    expect(screen.getByText(/베이커리 실험 1 28 : 72/)).toBeTruthy();
  });

  it("send row: [◀ 왜 그런지] · 계획 파일 · PDF 받기 · [보내기]", async () => {
    await prep();
    expect(screen.getByRole("button", { name: "계획 파일" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "PDF 받기" })).toBeTruthy();
    await click("◀ 왜 그런지");
    expect(await h1("왜 이 칸이에요?")).toBeTruthy();
  });
});

describe("QA 2026-11-27: 새로고침해도 같은 결과·단계 (N-06)", () => {
  it("주소에 결과 코드가 있으면 서버에서 다시 받아 그 단계로 연다", async () => {
    const f = vi.fn((url: string) => ok({ ...oven, code: "AB23" }));
    vi.stubGlobal("fetch", f);
    window.history.replaceState(null, "", "/analysis#code=AB23&step=AN-02");
    render(<App />);
    await waitFor(() => expect(f.mock.calls.some((c) => String(c[0]).includes("/analysis/result/AB23"))).toBe(true));
    await waitFor(() => expect(window.location.hash).toContain("code=AB23"));
    expect(window.location.hash).toContain("step=AN-02");
    window.history.replaceState(null, "", "/analysis");
  });

  it("서버에서 지워졌으면 업로드 화면 그대로 (코드는 주소에서 지움)", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ detail: "지워졌어요" }), { status: 404 }))));
    window.history.replaceState(null, "", "/analysis#code=ZZZZ&step=AN-02");
    render(<App />);
    await waitFor(() => expect(window.location.hash).not.toContain("code=ZZZZ"));
    expect(screen.getByLabelText("광고 결과 파일 (CSV)")).toBeTruthy();
  });
});
