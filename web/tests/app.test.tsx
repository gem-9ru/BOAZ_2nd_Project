// 분석 페이지 축소안 v5 (2026-11-26, 광고어시스턴트_분석페이지_축소안_v5.pdf): 업로드 → ① 결론 → ② 왜 그런지 → ③ 준비하기
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
  fireEvent.click(screen.getByRole("button", { name: "오븐로그 예시로 보기" }));
  return f;
}
const click = async (name: RegExp | string) => fireEvent.click(await screen.findByRole("button", { name }));
const open = (label: RegExp | string) => fireEvent.click(screen.getByText(label, { selector: "summary span" }));
const h1 = (name: string) => screen.findByRole("heading", { level: 1, name });
const upload = () => fireEvent.change(screen.getByLabelText("광고 결과 파일 (CSV)"), { target: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });

describe("⓪ 업로드", () => {
  it("has one job (the file), a settings status line, two examples and four folded help rows", () => {
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: "돌려 본 광고 결과를 올려 주세요" })).toBeTruthy();
    expect(screen.getByText("파일 하나만 올리면, 다음에 바꿔 볼 칸 1개를 뭉치가 찾아 드려요")).toBeTruthy();
    expect(screen.getByText("광고 결과 파일(CSV)을 여기로 끌어다 놓기")).toBeTruthy();
    expect(screen.getByText("파일을 올리면 눌러져요")).toBeTruthy();
    expect(screen.getByText("새 분석")).toBeTruthy();
    expect(screen.getByRole("button", { name: "내 광고 설정 5개만 직접 입력하기 ▸" })).toBeTruthy();
    for (const n of ["오븐로그 예시로 보기", "희수 실험 예시로 보기"]) expect(screen.getByRole("button", { name: n })).toBeTruthy();
    for (const t of ["결과 파일은 어떻게 받아요?", "꼭 있어야 하는 열", "내 광고 설정이 없어요", "아직 광고를 안 돌려 봤어요"]) expect(screen.getByText(t)).toBeTruthy();
    expect(screen.getByText("지출 금액 · 노출 · 링크 클릭 · 랜딩 페이지 조회")).toBeTruthy();   // 닫힌 줄에도 핵심 한 줄
    expect((screen.getByRole("button", { name: "분석 시작 ▶" }) as HTMLButtonElement).disabled).toBe(true);
    expect(document.body.textContent).not.toMatch(/20만 번|₩/);
  });

  it("the settings link opens the 5 questions in place; answers go with the upload", async () => {
    const f = vi.fn((_u: string, _i?: RequestInit) => ok(oven));
    vi.stubGlobal("fetch", f);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "내 광고 설정 5개만 직접 입력하기 ▸" }));
    for (const g of ["캠페인 목표", "세트당 하루 예산", "연령", "노출 위치", "소재 형식"]) expect(screen.getByRole("group", { name: g })).toBeTruthy();
    fireEvent.click(screen.getByLabelText("트래픽"));
    upload();
    await waitFor(() => expect(f.mock.calls.some(([u, o]) => String(u).endsWith("/analysis") && JSON.parse(String((o?.body as FormData).get("settings"))).hasOwnProperty("meta.campaign.objective"))).toBe(true));
  });

  it("from the extension: shows the received count instead of the link, and uploads with the key", async () => {
    window.history.replaceState(null, "", "/#s=K3yK3yK3yK3yK3y");
    const f = vi.fn((url: string, init?: RequestInit) => ok(String(url).includes("/settings/") ? { count: 14, settings: {} } : init?.method === "POST" ? oven : {}));
    vi.stubGlobal("fetch", f);
    render(<App />);
    expect(await screen.findByText(/확장 프로그램에서 자동으로 받았어요 \(14칸\)/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /5개만 직접 입력하기/ })).toBeNull();
    upload();
    await waitFor(() => expect(f.mock.calls.some(([u, o]) => String(u).endsWith("/analysis") && (o?.body as FormData).get("settings_key") === "K3yK3yK3yK3yK3y")).toBe(true));
  });

  it("a good file is checked in place and [분석 시작] turns on without settings", async () => {
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

  it("the not-yet checklist counts what is left", () => {
    render(<App />);
    open("아직 광고를 안 돌려 봤어요");
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes.length).toBe(4);
    fireEvent.click(boxes[0]!);
    expect(screen.getByText("1/4")).toBeTruthy();
  });
});

describe("① 결론", () => {
  it("one conclusion card with a 테스트 제안 tag, one main button, two summaries and two folds", async () => {
    show();
    expect(await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요")).toBeTruthy();
    expect(screen.getByText("세로 소재를 넣은 세트를 하나 더 만들어, 지금 세트와 같이 돌려 보면 돼요")).toBeTruthy();
    const card = screen.getByRole("region", { name: "테스트할 칸" });
    expect(within(card).getByText("광고 › 형식·미디어")).toBeTruthy();
    expect(within(card).getByText(/세로\(9:16\) 소재 세트 하나 더/)).toBeTruthy();
    expect(within(card).getByText("테스트 제안")).toBeTruthy();
    expect(card.textContent).toContain("돈의 72%가 인스타 릴스");
    expect(within(card).getByText("세로 소재가 방문자를 더 데려올지는 아직 몰라요 → 이번 테스트로 확인해요.")).toBeTruthy();
    const rest = screen.getByRole("list", { name: "나머지 칸" });
    expect(within(rest).getByText("노출 위치 = 직접 고르기")).toBeTruthy();
    expect(within(rest).getByText("확실해요")).toBeTruthy();
    expect(within(rest).getByText("시작 날짜 · 예산")).toBeTruthy();
    expect(within(rest).getByText("첫날 안 보여졌어요 · 알림 신청 1건뿐")).toBeTruthy();
    expect(screen.getByText("11/17~20 · 광고비 10,616원 · 클릭 30번")).toBeTruthy();
    expect(within(rest).getByText("광고비가 15% 쌌어요")).toBeTruthy();
    expect(screen.getByText("여기서 바로 준비해도 돼요")).toBeTruthy();
    expect(screen.queryByText(/하지 말기/)).toBeNull();   // ③ 체크리스트로 옮김
    expect(document.querySelector("main")!.textContent).not.toMatch(/손님|₩|유력|보류|채택/);
  });

  it("[이 테스트 준비하기 →] goes straight to ③; [왜 그런지 보기 ▶] is a secondary button to ②", async () => {
    show();
    await click("이 테스트 준비하기 →");
    expect(await h1("이 테스트를 준비해요")).toBeTruthy();
    await click(/① 결론/);
    await click("왜 그런지 보기 ▶");
    expect(await h1("왜 이 칸이에요?")).toBeTruthy();
  });

  it("alert bar: the most serious one in short words, counts, and [모두 보기 ▾]", async () => {
    show();
    const bar = await screen.findByRole("region", { name: "알림" });
    expect(within(bar).getByText(/11\/17은 두 세트 모두 하루 종일 안 보여졌어요 → 이 날은 비교에서 뺐어요/)).toBeTruthy();
    expect(within(bar).getByText("주의 2 · 참고 1")).toBeTruthy();
    fireEvent.click(within(bar).getByRole("button", { name: "모두 보기 ▾" }));
    expect(within(bar).getAllByRole("listitem").length).toBe(3);
  });

  it("stepper: three steps; ③ can be reached directly, ② only after ①; the hash tells the side panel the step", async () => {
    show();
    await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요");
    expect((screen.getByRole("button", { name: /② 왜 그런지/ }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: /③ 준비하기/ }) as HTMLButtonElement).disabled).toBe(false);
    const q = () => new URLSearchParams(window.location.hash.slice(1));
    expect(q().get("code")).toBe(oven.code);
    expect(q().get("step")).toBe("AN-01");
    await click("왜 그런지 보기 ▶");
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
    expect((screen.getByRole("button", { name: "왜 그런지 보기 ▶" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("browser [뒤로] goes to the previous step instead of leaving the result", async () => {
    show();
    await click("왜 그런지 보기 ▶");
    await h1("왜 이 칸이에요?");
    window.history.replaceState(null, "", window.location.pathname + "#code=" + oven.code + "&step=AN-01");
    fireEvent.popState(window);
    expect(await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요")).toBeTruthy();
  });

  it("the 다시 보기 card says where the to-do went", async () => {
    show();
    expect(await screen.findByText("→ ③ 준비하기 체크리스트에 넣었어요")).toBeTruthy();
  });

  it("[다른 파일 올리기] asks first, because the result would be lost", async () => {
    show();
    await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요");
    const confirm = vi.fn(() => false);
    vi.stubGlobal("confirm", confirm);
    fireEvent.click(screen.getByRole("button", { name: "다른 파일 올리기" }));
    expect(confirm).toHaveBeenCalled();
    expect(screen.getByRole("heading", { level: 1, name: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요" })).toBeTruthy();
  });
});

describe("② 왜 그런지", () => {
  async function why(result: unknown = oven) {
    show(result);
    await click("왜 그런지 보기 ▶");
    await h1("왜 이 칸이에요?");
  }

  it("three reasons that end in a badge, then six folds with a preview on each", async () => {
    await why();
    expect(screen.getByText(/돈은 릴스로 몰렸고, 나머지 설정은 괜찮았어요/)).toBeTruthy();
    expect(screen.getByText("돈의 72%가 인스타 릴스(세로 화면)에서 나갔어요")).toBeTruthy();
    expect(screen.getByText("노출 위치는 직접 고르기(수동)가 광고비 15% 쌌어요")).toBeTruthy();
    expect(screen.getByText(/메타는 '자동'을 권했지만, 우리가 돌려 본 2번 모두 수동이 쌌어요/)).toBeTruthy();
    expect(screen.getByText(/같은 돈\(5,308원\)으로 방문자 A \d+명 · B \d+명/)).toBeTruthy();
    expect(screen.getByText(/방문 1명당 A [\d,]+원 · B [\d,]+원 · B가 나을 확률 \d+%/)).toBeTruthy();
    expect(screen.getByText("들어온 뒤 행동(알림 신청 1건)은 아직 몰라요")).toBeTruthy();
    expect(screen.getByText("보이는 값 ↓ · 누르는 정도 ✓ · 도착 ✓ · 행동 –")).toBeTruthy();
    expect(screen.getByText(/^A [\d,]+원~[\d,]+원 · B [\d,]+원~[\d,]+원$/)).toBeTruthy();
    expect(screen.getByText(/^테스트 1 · 다시 보기 \d · 그대로 1$/)).toBeTruthy();
    expect(screen.getByText("베이지안 · 논문 · 한계")).toBeTruthy();
    expect(screen.queryByText(/▲ 기준 미달/)).toBeNull();
  });

  it("with settings that lack a vertical creative, it names what the creative was", async () => {
    const c = { ...oven.matrix.change, now: "정사각 1장 + AI 이미지 2장", reason: "돈의 72%가 인스타 릴스(세로 화면)에서 나갔는데, 세로 소재가 없었어요." };
    await why({ ...oven, matrix: { ...oven.matrix, change: c } });
    expect(screen.getByText("돈은 릴스로 갔는데 세로 소재가 없었고, 나머지 설정은 괜찮았어요")).toBeTruthy();
    expect(screen.getByText("돈의 72%가 인스타 릴스(세로 화면)에서 나갔어요")).toBeTruthy();
    expect(screen.getByText("그런데 소재는 정사각 1장 + AI 이미지 2장이었어요 → 이번에 테스트할 칸")).toBeTruthy();
  });

  it("folds keep the old screens: funnel table (with Meta rankings), dates, placements, settings", async () => {
    const text = "메타 품질 순위: A(자동) 평균 이하 — 소재 품질이 낮게 보여요 → 소재 · 형식";
    await why({ ...oven, matrix: { ...oven.matrix, rankings: true, meta_signals: [{ row: "1", key: "quality", text }] } });
    open("어디서 막혔나 · 단계별 신호");
    expect(within(screen.getByRole("region", { name: "메타 진단" })).getByText(`① ${text}`)).toBeTruthy();
    expect(screen.getByText(/1,000번 보이면 A 약 \d+번 · B 약 \d+번 눌려요/)).toBeTruthy();
    open("날짜별로 확률이 어떻게 굳어졌나");
    expect(screen.getAllByText("B 쪽이에요").length).toBeGreaterThan(0);
    open("노출 위치별 클릭");
    expect(screen.getAllByText("참고만").length).toBeGreaterThan(0);
    open("내 세팅 칸별 상태");
    expect(screen.getByRole("tablist", { name: "상태로 거르기" })).toBeTruthy();
    open("계산 방법 · 근거");
    expect(screen.getByRole("heading", { name: "방문 1명당 비용" })).toBeTruthy();
  });

  it("when A wins, the numbers are told from A's side", async () => {
    await why(twoSets);
    expect(screen.getByText(/A가 나을 확률 95%/)).toBeTruthy();
    expect(screen.queryByText(/B가 나을 확률/)).toBeNull();
  });

  it("a single ad set: no A/B reason, the funnel row 1 is '–'", async () => {
    await why(oneSet);
    expect(screen.queryByText(/같은 돈\(/)).toBeNull();
    open("어디서 막혔나 · 단계별 신호");
    const row1 = screen.getByText(/비교할 세트가 하나라 광고비 비교는 없어요/).closest("tr")!;
    expect(row1.querySelector('[aria-label="아직 몰라요"]')).toBeTruthy();
  });
});

describe("③ 준비하기", () => {
  async function prep(result: unknown = oven) {
    const f = show(result);
    await click("이 테스트 준비하기 →");
    await h1("이 테스트를 준비해요");
    return f;
  }

  it("now vs new set, then budget as a decision question with chips", async () => {
    await prep();
    expect(screen.getByText("지금 세트는 그대로 두고, 세로 소재를 넣은 세트 하나만 더 만들면 돼요")).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "지금 세트" })).getByText("노출 위치 직접 고르기 · 나머지 그대로")).toBeTruthy();
    const n = screen.getByRole("region", { name: "새 세트" });
    expect(within(n).getByText("+ 세로(9:16) 1개")).toBeTruthy();
    expect(within(n).getByText("테스트 제안")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "예산 · 세트당 총액 (4일)" })).toBeTruthy();
    expect((screen.getByRole("radio", { name: "6,000원" }) as HTMLInputElement).checked).toBe(true);
    const answer = () => screen.getByText(/결과를 판단할 수 있을 가능성/).textContent;
    await waitFor(() => expect(answer()).toContain("약 90%"));
    expect(screen.getByText("5,000원 약 70% · 10,000원 거의 확실")).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: /5,000원/ }));
    expect(answer()).toContain("약 70%");
    expect(screen.getByText(/성공 확률 아님/)).toBeTruthy();
    expect(screen.getByText(/금액을/).textContent).toContain("결제·게시를 하지 않아요");
  });

  it("budget folds keep the visitor range (가설, daily minimum), Test & Roll and the backtest", async () => {
    await prep();
    open("예상 방문자 수 보기");
    expect((await screen.findAllByText(/보통 78명 \(적게 55명 ~ 많이 108명\)/, {}, { timeout: 2000 })).length).toBeGreaterThan(0);
    expect(screen.getAllByText("가설").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByRole("radio", { name: "7일" }));
    fireEvent.change(screen.getByRole("slider", { name: "예산" }), { target: { value: "5000" } });
    expect(await screen.findByText(/메타 하루 최소/, {}, { timeout: 2000 })).toBeTruthy();
    open("전체 예산으로 정하기");
    expect(await screen.findByRole("heading", { name: "다음 테스트에 쓸 돈 (Test & Roll)" }, { timeout: 2000 })).toBeTruthy();
    open("예측이 맞았나?");
    expect(screen.getByText(/예측이 맞았나\? \(검증\)/)).toBeTruthy();
  });

  it("the 4-item checklist (no ALT numbers) and send with a toast; the alert bar says warnings moved here", async () => {
    await prep();
    expect(screen.getByRole("heading", { name: "체크리스트 4개" })).toBeTruthy();
    for (const t of ["시작은 하루 여유 있게", "두 세트를 같은 날 같이 시작", "바꾸는 칸은 형식·미디어 1개만 (여러 칸 한 번에 바꾸지 않기)"]) expect(screen.getByText(t)).toBeTruthy();
    expect(screen.getByText(/딱 하루만 연장/)).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/ALT-/);
    expect(within(screen.getByRole("region", { name: "알림" })).getByText(/주의 2건은 아래 체크리스트에 넣었어요/)).toBeTruthy();
    vi.stubGlobal("navigator", { clipboard: { writeText: () => Promise.resolve() } });
    fireEvent.click(screen.getByRole("button", { name: "확장 프로그램으로 보내기 →" }));
    expect(await screen.findByText(/오른쪽 광고 어시스턴트로 보냈어요/)).toBeTruthy();
    expect(new URLSearchParams(window.location.hash.slice(1)).get("send")).toBeTruthy();
  });

  it("a chip under Meta's daily minimum gets ▲ and a warning; the default says why; send carries the picked budget and leaves the code on screen", async () => {
    await prep();
    expect(await screen.findByText(/기본 6,000원 = 하루 약 1,500원 × 4일 · 메타 하루 최소\(약 1,336원\)를 넘는 가장 작은 금액/)).toBeTruthy();
    expect(screen.getByRole("radio", { name: "5,000원 (하루 최소보다 적어요)" })).toBeTruthy();   // 5,000원 칩에만
    expect(screen.getByRole("radio", { name: "6,000원" })).toBeTruthy();
    expect(screen.queryByText(/광고가 안 나갈 수 있어요/)).toBeNull();
    fireEvent.click(screen.getByRole("radio", { name: /5,000원/ }));
    expect(screen.getByText(/하루 1,250원은 메타 하루 최소\(약 1,336원\)보다 적어요 → 광고가 안 나갈 수 있어요\. 6,000원 이상을 골라 주세요/)).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "10,000원" }));
    vi.stubGlobal("navigator", { clipboard: { writeText: () => Promise.resolve() } });
    fireEvent.click(screen.getByRole("button", { name: "확장 프로그램으로 보내기 →" }));
    expect(new URLSearchParams(window.location.hash.slice(1)).get("budget")).toBe("10000");
    const line = await screen.findByText(/보냈어요 · 세트당 10,000원 · 코드/);
    expect(line.textContent).toContain(oven.code);
  });

  it("evidence is one fold with the 5 tabs, including 6 virtual cases not used for the verdict", async () => {
    await prep();
    open(/^근거 · 메타 공식 신호/);
    fireEvent.click(screen.getByRole("tab", { name: "가상 케이스" }));
    expect(screen.getByText(/판정에는 쓰지 않아요/)).toBeTruthy();
    expect(screen.getAllByRole("row").length).toBe(7);
    fireEvent.click(screen.getByRole("tab", { name: "한계" }));
    expect(screen.getByText(/겹쳐 보일 수 있어요/)).toBeTruthy();
  });

  it("navigation: [◀ 왜 그런지] and [처음으로]", async () => {
    await prep();
    await click("처음으로");
    expect(await h1("다음엔 이 칸 1개만 바꿔서 테스트해 보세요")).toBeTruthy();
  });
});
