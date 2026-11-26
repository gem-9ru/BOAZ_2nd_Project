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

afterEach(() => vi.unstubAllGlobals());

function showExample() {
  const f = vi.fn((url: string, init?: RequestInit) => {
    const u = String(url);
    if (u.includes("/simulate")) {
      const b = JSON.parse(init!.body as string);
      const daily = b.days ? b.budget / b.days : null;
      return ok({ ...sim, tried: b.budget <= 5308 && (daily == null || daily <= 2643), days: b.days, daily, daily_max: 2643, daily_tried: daily == null || daily <= 2643,
        daily_min: 1336, below_daily_min: daily != null && daily < 1336, next_test: { total: 20000, per_set_lo: 1000, per_set_hi: 2000, share_lo: 0.076, share_hi: 0.2, source: "Feit" } });
    }
    if (u.includes("/assistant")) {
      const b = JSON.parse(init!.body as string);
      return ok(b.question ? { message: `답: ${b.question}`, source: "llm" }
        : { message: `${b.step} 첫 말`, suggestions: ["질문 하나", "질문 둘"], alerts: b.step === "AN-01" ? [oven.alerts[0]] : [] });
    }
    return ok(oven);
  });
  vi.stubGlobal("fetch", f);
  render(<App />);
  fireEvent.click(screen.getByRole("button", { name: "오븐로그 예시로 보기" }));
  return f;
}

describe("AN-00 예시 2건", () => {
  it("[희수 실험 예시로 보기] asks the server for the heesu example and shows its file name", async () => {
    const f = vi.fn((url: string) => ok(String(url).includes("/assistant") ? { message: "m", suggestions: [] } : oven));
    vi.stubGlobal("fetch", f);
    render(<App />);
    expect(screen.getByRole("button", { name: "오븐로그 예시로 보기" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "희수 실험 예시로 보기" }));
    await screen.findByRole("heading", { level: 1, name: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요" });
    expect(f.mock.calls.some(([u]) => String(u) === "/analysis/example?name=heesu")).toBe(true);
    expect(screen.getByText(/희수_메타AB_20261117-20261120\.csv/)).toBeTruthy();
  });
});

describe("AN-02 메타 관련성 진단 (보조 신호)", () => {
  it("shows the below-average rankings as a reference list under the funnel table", async () => {
    const text = "메타 품질 순위: A(자동) 평균 이하 — 같은 손님을 두고 경쟁하는 광고보다 소재 품질이 낮게 보여요 → 소재 · 형식";
    const withRank = { ...oven, matrix: { ...oven.matrix, rankings: true, meta_signals: [{ row: "1", key: "quality", text }] } };
    vi.stubGlobal("fetch", vi.fn((url: string) => ok(String(url).includes("/assistant") ? { message: "m", suggestions: [] } : withRank)));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "오븐로그 예시로 보기" }));
    await next("왜 그런지 보기 ▶");
    const box = await screen.findByRole("region", { name: "메타 진단" });
    expect(within(box).getByText(`① ${text}`)).toBeTruthy();
    expect(screen.getByText(/신호등과 결론은 우리 숫자로만 정해요/)).toBeTruthy();
  });
});

describe("화면 0 시작", () => {
  it("offers upload, example and test-prep with one promise line", () => {
    render(<App />);
    // 점검 G: 계산 횟수 대신 하는 일 (화면설계서 v4.2 AN-00 '결과 파일과 광고 설정을 올리면 분석이 시작돼요')
    expect(screen.getByText("결과 파일과 광고 설정을 올리면 다음에 바꿔 볼 칸 1개와 예상 손님 수를 알려 드려요.")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/20만 번/);
    expect(screen.getByLabelText("광고 결과 파일 (CSV)")).toBeTruthy();
    expect(screen.getByRole("button", { name: "오븐로그 예시로 보기" })).toBeTruthy();
    expect(document.body.textContent).not.toContain("₩");
    expect(screen.getByRole("button", { name: "아직 안 돌려 봤어요" })).toBeTruthy();
  });

  it("upload area accepts a dropped file and speaks Korean", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ error: "x 다시 내보내 주세요" }), { status: 400 }))));
    render(<App />);
    expect(screen.getByText("파일 고르기")).toBeTruthy();
    const zone = screen.getByText(/끌어다 놓거나/).closest("label")!;
    fireEvent.drop(zone, { dataTransfer: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });
    await waitFor(() => expect(screen.getByRole("alert")).toBeTruthy());
  });

  it("names the columns it needs and warns about '조회'", () => {
    render(<App />);
    expect(screen.getByText(/랜딩 페이지 조회/, { selector: "li" })).toBeTruthy();
    expect(screen.getByText(/'조회'는 랜딩 페이지 조회가 아니에요/)).toBeTruthy();
  });

  it("test-prep is a checklist with what is left", () => {
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "아직 안 돌려 봤어요" }));
    const boxes = screen.getAllByRole("checkbox");
    expect(boxes.length).toBe(4);
    expect(screen.getByText("0/4")).toBeTruthy();
    fireEvent.click(boxes[0]!);
    expect(screen.getByText("1/4")).toBeTruthy();
  });

  it("a bad file shows how to fix it right under the upload box", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ error: "링크 클릭 열이 없어요. 다시 내보내 주세요." }), { status: 400 }))));
    render(<App />);
    fireEvent.change(screen.getByLabelText("광고 결과 파일 (CSV)"), { target: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("다시 내보내"));
  });
});

async function next(name: RegExp | string) {
  fireEvent.click(await screen.findByRole("button", { name }));
}

const OWNER_BAD = ["₩", "유력", "보류", "채택", "코치"];
/** v4.2 AN-TXT: 사장님 화면(🔎 접기 밖)에 '₩'·개발 판정어·'코치'·지표 숫자가 없는지. */
function ownerTextOk() {
  const main = document.querySelector("main")!.cloneNode(true) as HTMLElement;
  main.querySelectorAll("details").forEach((d) => d.remove());
  for (const w of OWNER_BAD) expect(main.textContent, w).not.toContain(w);
  expect(main.textContent).not.toMatch(/CPM \d|CTR \d|CPC \d/);
}

describe("7단계 결과 (v4.2)", () => {
  it("AN-01 shows the one field as a 테스트 제안 (no verdict badge), and keep/watch/dont with customers first", async () => {
    showExample();
    expect(await screen.findByRole("heading", { level: 1, name: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요" })).toBeTruthy();
    expect(screen.getByText("나머지 칸은 그대로 둬야 무엇 덕분인지 알 수 있어요")).toBeTruthy();
    const card = screen.getByRole("region", { name: "테스트할 칸" });
    expect(within(card).getByText("광고 › 형식·미디어")).toBeTruthy();
    expect(within(card).getByText(/세로\(9:16\) 소재를 넣은 세트를 하나 더 만들어 보세요/)).toBeTruthy();
    expect(within(card).getByText("테스트 제안")).toBeTruthy();
    expect(within(card).getByText(/6,000원씩 같이 돌려서 직접 비교해요/)).toBeTruthy();
    expect(within(card).queryByText(/쪽이에요|확실해요/)).toBeNull();
    for (const h of ["유지", "지켜보기", "하지 말기"]) expect(screen.getByText(h)).toBeTruthy();
    expect(screen.getByText(/노출 위치 = 직접 고르기\(수동\)/)).toBeTruthy();
    expect(screen.getByText(/같은 돈으로 손님 A 10명 · B 14명/)).toBeTruthy();
    expect(screen.getByText("B 쪽이에요")).toBeTruthy();
    expect(screen.getByText(/광고비 10,616원 · 보여진 횟수 1,822번 · 클릭 30번/)).toBeTruthy();
    expect(screen.getByText(/알림 신청이 1건뿐이에요 → 같은 세팅으로 기간을 늘리거나 예산을 더 써야 알 수 있어요/)).toBeTruthy();   // 지켜보기 이유: 기간·예산과 이어지게
    expect(screen.getByText(/분석 · 오븐로그_메타AB_20261117-20261120\.csv/)).toBeTruthy();   // 머리에 파일 이름
    ownerTextOk();
    // 작은 카드를 누르면 AN-03 내 세팅 카드의 그 행으로
    fireEvent.click(screen.getByRole("button", { name: /지켜보기/ }));
    expect(screen.getByRole("heading", { level: 1, name: "내 다른 설정은 괜찮나요?" })).toBeTruthy();
    expect(screen.getByText(/선택한 칸: 예산/)).toBeTruthy();
  });

  it("alert bar puts this step's warning first, counts by name, and opens all", async () => {
    showExample();
    const bar = await screen.findByRole("region", { name: "알림" });
    expect(within(bar).getByText(/11\/17 두 세트 모두 하루 종일 안 보여졌어요/)).toBeTruthy();
    expect(within(bar).getByText("주의 2 · 참고 1")).toBeTruthy();
    fireEvent.click(within(bar).getByRole("button", { name: "모두 보기" }));
    expect(within(bar).getByText(/메타는 '노출 위치 자동'을 권하지만/)).toBeTruthy();
    expect(within(bar).queryByText(/써 본 적 없는|가설/)).toBeNull();   // AN-05 알림은 그 단계부터
  });

  it("[다음] walks the steps; AN-02 is a people-count table, AN-03 uses 테스트/다시 보기/그대로", async () => {
    showExample();
    await next("왜 그런지 보기 ▶");
    expect(await screen.findByRole("heading", { level: 1, name: "어디서 막혔나요?" })).toBeTruthy();
        expect(screen.getByText(/B\(수동\)가 15% 싸요/)).toBeTruthy();
    expect(screen.getByText(/1,000번 보여지면 A 약 16번 · B 약 17번 눌렸어요 → 괜찮아요/)).toBeTruthy();   // 노출은 횟수 (점검 A)
    expect(screen.getByText("A·B 차이는 광고가 보이는 값뿐이에요. B(수동)를 유지하면 되고, 그 아래는 괜찮아요")).toBeTruthy();   // ①과 이어지게 (점검 F)
    expect(screen.getByText(/누른 100명 중 A 77명 · B 82명 → 괜찮아요/)).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "알림" })).getByText(/알림 신청이 1건뿐이라 '들어온 뒤 행동'은 아직 몰라요/)).toBeTruthy();
    expect(screen.getByText(/알림 신청 A 0건 · B 1건/)).toBeTruthy();
    expect(screen.queryByRole("region", { name: "메타 진단" })).toBeNull();   // 오븐로그 파일엔 관련성 진단 열이 없음 → 건너뜀
    expect(screen.getByText(/파일에 없거나 노출이 적어 비어 있어서 건너뛰었어요/)).toBeTruthy();
    ownerTextOk();
    await next("내 세팅 보기 ▶");
    expect(screen.getByRole("heading", { level: 1, name: "내 다른 설정은 괜찮나요?" })).toBeTruthy();
    expect(screen.getByText(/테스트할 칸 1개, 다시 볼 칸 2개/)).toBeTruthy();
    for (const t of ["전체", "테스트", "다시 보기", "그대로"]) expect(screen.getByRole("tab", { name: new RegExp(`^${t} \\d`) })).toBeTruthy();
    expect(screen.getAllByText(/↓ 광고비 15% 싸요/).length).toBeGreaterThan(0);
    ownerTextOk();
    await next("값 비교 보기 ▶");
    expect(screen.getByRole("heading", { level: 1, name: "어떤 값이 더 나았나요?" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /① 확인·결론/ }));
    expect(screen.getByRole("heading", { level: 1, name: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요" })).toBeTruthy();
  });

  it("future steps are locked except ⑥, and [이 테스트 바로 준비 →] jumps to ⑥", async () => {
    showExample();
    await screen.findByText("광고 › 형식·미디어");
    expect((screen.getByRole("button", { name: /③ 세팅 카드/ }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: /⑥ 보내기/ }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "이 테스트 바로 준비 →" }));
    expect(screen.getByRole("heading", { level: 1, name: "이 테스트를 광고 관리자에 준비해요" })).toBeTruthy();
  });

  it("AN-04 ★ leads with cost per customer; CPM range in owner words; CPC·CTR only inside 🔎; placements get a blue ● 참고만", async () => {
    showExample();
    for (const n of ["왜 그런지 보기 ▶", "내 세팅 보기 ▶", "값 비교 보기 ▶"]) await next(n);
    expect(screen.getByText("B(수동)가 같은 돈으로 손님을 더 데려왔어요")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "손님 1명당 비용" })).toBeTruthy();
    expect(screen.getByText("531원")).toBeTruthy();
    expect(screen.getByText("379원")).toBeTruthy();
    expect(screen.getByText(/같은 돈\(5,308원\)으로 온 손님/)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /광고비는 확실히 B가 쌌어요/ })).toBeTruthy();
    expect(screen.getByText(/보통 6,342원 \(적게 5,92\d원 ~ 많이 6,78\d원\)/)).toBeTruthy();
    expect(screen.getByText(/B 쪽으로 굳어지고 있어요/)).toBeTruthy();
    const fold = screen.getByText("이 숫자는 어떻게 나왔나요?").closest("details")!;
    expect(within(fold).getByText("클릭 1번에 드는 돈 (CPC)")).toBeTruthy();
    ownerTextOk();
    fireEvent.click(screen.getByRole("tab", { name: "날짜별" }));
    expect(screen.getByText("79%")).toBeTruthy();
    const days = screen.getByText("26%").closest("ol")!;   // 설계서: 11/18 26% 아직 몰라요 → 11/19 65% 아직 몰라요 → 11/20 79% B 쪽이에요
    expect([...days.querySelectorAll("li")].map((li) => li.textContent!.replace(/^→/, "").replace(/[○◐●]/, ""))).toEqual(["11/1826%아직 몰라요", "11/1965%아직 몰라요", "11/2079%B 쪽이에요"]);
    fireEvent.click(screen.getByRole("tab", { name: "노출 위치별" }));
    expect(screen.getAllByText("참고만").length).toBeGreaterThan(0);
    expect(screen.getAllByText("참고만")[0]!.closest("span")!.className).toContain("bg-reference");
    expect(screen.getByText(/평균이 나쁜 자리를 바로 끄지 마세요/)).toBeTruthy();
    expect(screen.getByText(/A는 100원 중 73원, B는 100원 중 70원/)).toBeTruthy();
  });

  it("AN-05 shows ranges as '보통 ○명 (적게 ~ 많이)', marks untried budgets as 가설, shows Test & Roll and the check", async () => {
    const f = showExample();
    for (const n of ["왜 그런지 보기 ▶", "내 세팅 보기 ▶", "값 비교 보기 ▶", "바꾸면 어떻게 돼요? ▶"]) await next(n);
    await waitFor(() => expect(screen.getAllByText(/보통 78명 \(적게 55명 ~ 많이 108명\)/).length).toBeGreaterThan(0));
    expect(screen.getByText("10번 중 8번은 이 안에 들어요")).toBeTruthy();
    const slider = screen.getByLabelText("예산") as HTMLInputElement;
    expect(slider.step).toBe("5000");
    fireEvent.change(slider, { target: { value: "20000" } });
    await waitFor(() => expect(f.mock.calls.some(([u, o]) => String(u).includes("/simulate") && JSON.parse((o as RequestInit).body as string).budget === 80000)).toBe(true));
    expect(screen.getAllByText("가설").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "다음 테스트에 쓸 돈 (Test & Roll)" })).toBeTruthy();
    expect(screen.getByText("예측이 맞았나? (검증)")).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "알림" })).getByText("주의 2 · 참고 2")).toBeTruthy();
    ownerTextOk();
  });

  it("AN-05 period toggle 4일/7일 changes the daily amount and warns under Meta's daily minimum (오븐로그 11/17과 같은 경우)", async () => {
    const f = showExample();
    for (const n of ["왜 그런지 보기 ▶", "내 세팅 보기 ▶", "값 비교 보기 ▶", "바꾸면 어떻게 돼요? ▶"]) await next(n);
    expect((screen.getByRole("radio", { name: "4일" }) as HTMLInputElement).checked).toBe(true);
    // 권하는 금액(6,000원 · 4일)은 하루 최소를 넘는다 → 결론·보내기와 같은 금액, 경고 없음
    expect(screen.getByText("하루 약 1,500원")).toBeTruthy();
    await waitFor(() => expect(screen.getByText(/세트당 총 6,000원을 4일 동안 쓰면/)).toBeTruthy());
    expect(screen.queryByText(/메타 하루 최소/)).toBeNull();
    fireEvent.change(screen.getByLabelText("예산"), { target: { value: "5000" } });
    expect(screen.getByText("하루 약 1,250원")).toBeTruthy();
    await waitFor(() => expect(screen.getByText(/메타 하루 최소\(약 1,336원\)보다 적어요 → 광고가 안 나갈 수 있어요/)).toBeTruthy());
    fireEvent.change(screen.getByLabelText("예산"), { target: { value: "10000" } });
    fireEvent.click(screen.getByRole("radio", { name: "7일" }));
    expect(screen.getByText("하루 약 1,430원")).toBeTruthy();
    await waitFor(() => expect(screen.getByText(/세트당 총 1만 원을 7일 동안 쓰면/)).toBeTruthy());
    await waitFor(() => expect(screen.queryByText(/메타 하루 최소/)).toBeNull());
    expect(f.mock.calls.some(([u, o]) => String(u).includes("/simulate") && JSON.parse((o as RequestInit).body as string).days === 7)).toBe(true);
  });

  it("AN-06 prepares the test: 지금 세트/새 세트, 4-item checklist without ALT numbers, send with a toast", async () => {
    showExample();
    const writeText = vi.fn(() => Promise.resolve());
    Object.assign(navigator, { clipboard: { writeText } });
    fireEvent.click(await screen.findByRole("button", { name: "이 테스트 바로 준비 →" }));
    expect(screen.getByText(oven.code)).toBeTruthy();
    expect(screen.getByText(/새 세트: \+ 세로\(9:16\) 1개/)).toBeTruthy();
    expect(screen.getByText("세로 소재를 넣은 세트 하나만 더 만들면 돼요")).toBeTruthy();   // 설계서 AN-06 한 줄 요약
    expect(screen.getByText(/세트당 총 6,000원, 4일/)).toBeTruthy();   // ①·⑤와 같은 금액 (하루 최소 넘김)
    expect(screen.getAllByRole("checkbox").length).toBe(4);
    expect(screen.getByText("두 세트는 같은 날 같이 시작")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/ALT-\d/);
    expect(within(screen.getByRole("region", { name: "알림" })).getByText(/주의 2건은 다음 테스트 체크리스트에 넣었어요/)).toBeTruthy();
    const print = vi.fn(); vi.stubGlobal("print", print);
    fireEvent.click(screen.getByRole("button", { name: "결과 PDF" }));
    expect(print).toHaveBeenCalled();   // 브라우저 인쇄 → 'PDF로 저장'
    fireEvent.click(screen.getByRole("button", { name: "확장 프로그램으로 보내기" }));
    await waitFor(() => expect(screen.getByText(/오른쪽 광고 어시스턴트로 보냈어요/)).toBeTruthy());
    expect(writeText).toHaveBeenCalledWith(oven.code);
    expect(new URLSearchParams(window.location.hash.slice(1)).get("send")).toBeTruthy();   // 옆 패널이 이걸 보고 테스트안을 받음
  });

  it("AN-06 근거 탭 '가상 케이스' shows the 6-case table and says it is not used for the verdict", async () => {
    showExample();
    fireEvent.click(await screen.findByRole("button", { name: "이 테스트 바로 준비 →" }));
    fireEvent.click(screen.getByRole("tab", { name: "가상 케이스" }));
    const table = screen.getByRole("table", { name: "가상 케이스 6개 결과" });
    expect(within(table).getAllByRole("row")).toHaveLength(7);   // 머리 1 + 케이스 6
    const v5 = within(table).getByRole("row", { name: /V5 B 웹사이트 주소 잘못/ });
    expect(within(v5).getByText("광고 › 웹사이트 URL: 주소·속도 점검")).toBeTruthy();
    expect(within(v5).getByText("페이지 도착 적음")).toBeTruthy();
    expect(within(table).getByRole("row", { name: /V6 좁은 지역/ }).textContent).toContain("반복 노출");
    expect(table.textContent).not.toMatch(/네이버/);   // 네이버 광고는 돌리지 않음 → 메타 설정 케이스만
    expect(screen.queryByText(/같은 설정 두 세트\(V2\)를 40번/)).toBeNull();
    expect(screen.getByText(/판정에는 쓰지 않아요/)).toBeTruthy();
  });
});

describe("광고 어시스턴트 = 크롬 확장 프로그램 사이드 패널 (v4.2 AN-COM ④)", () => {
  afterEach(() => { window.history.replaceState(null, "", "/"); });

  it("the page has no built-in assistant; it writes code and step after # for the side panel", async () => {
    showExample();
    await screen.findByRole("heading", { level: 1, name: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요" });
    expect(screen.queryByRole("complementary", { name: "광고 어시스턴트" })).toBeNull();
    expect(screen.getByText(/크롬 오른쪽 광고 어시스턴트\(확장 프로그램 패널\)에 물어보세요/)).toBeTruthy();
    expect(new URLSearchParams(window.location.hash.slice(1)).get("code")).toBe(oven.code);
    expect(new URLSearchParams(window.location.hash.slice(1)).get("step")).toBe("AN-01");
    await next("왜 그런지 보기 ▶");
    await waitFor(() => expect(new URLSearchParams(window.location.hash.slice(1)).get("step")).toBe("AN-02"));
  });

  it("keeps the settings key from the extension in the hash", async () => {
    window.history.replaceState(null, "", "/#s=K3yK3yK3yK3yK3y");
    showExample();
    await screen.findByRole("heading", { level: 1, name: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요" });
    const q = new URLSearchParams(window.location.hash.slice(1));
    expect(q.get("s")).toBe("K3yK3yK3yK3yK3y");
    expect(q.get("code")).toBe(oven.code);
  });
});

describe("접근성", () => {
  it("moves focus to the step title and announces the result", async () => {
    showExample();
    const title = await screen.findByRole("heading", { level: 1, name: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요" });
    await waitFor(() => expect(document.activeElement).toBe(title));
    expect(screen.getByText("결과를 다 계산했어요")).toBeTruthy();
  });

  it("links the upload error to the file input", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ error: "다시 내보내 주세요" }), { status: 400 }))));
    render(<App />);
    const input = screen.getByLabelText("광고 결과 파일 (CSV)");
    fireEvent.change(input, { target: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });
    const alert = await screen.findByRole("alert");
    expect(alert.id).toBeTruthy();
    expect(input.getAttribute("aria-describedby")!.split(" ")).toContain(alert.id);
  });
});

describe("세팅값 받기 (v4 8장 입력 ②)", () => {
  afterEach(() => { window.location.hash = ""; });

  it("from the extension: reads the session key from #s=, shows how many, and uploads with the key", async () => {
    window.location.hash = "#s=K3yK3yK3yK3yK3y";
    const f = vi.fn((url: string, init?: RequestInit) => {
      if (String(url).includes("/settings/")) return ok({ count: 13, settings: {} });
      if (init?.method === "POST" && String(url).endsWith("/analysis")) return ok(oven);
      return ok({ message: "m", suggestions: [] });
    });
    vi.stubGlobal("fetch", f);
    render(<App />);
    expect(await screen.findByText(/자동으로 받음 \(13칸\)/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "5개만 직접 입력" })).toBeNull();
    fireEvent.change(screen.getByLabelText("광고 결과 파일 (CSV)"), { target: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });
    await waitFor(() => expect(f.mock.calls.some(([u, o]) => String(u).endsWith("/analysis") && (o?.body as FormData).get("settings_key") === "K3yK3yK3yK3yK3y")).toBe(true));
  });

  it("without the extension: 5 questions (목표·예산·연령·노출 위치·소재 형식) go with the upload", async () => {
    window.history.replaceState(null, "", "/");   // 앞 테스트의 늦게 끝난 화면이 남긴 # 지우기
    const f = vi.fn((_url: string, _init?: RequestInit) => ok(oven));
    vi.stubGlobal("fetch", f);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "5개만 직접 입력" }));
    for (const g of ["캠페인 목표", "세트당 하루 예산", "연령", "노출 위치", "소재 형식"]) expect(screen.getByRole("group", { name: g })).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "수동" }));
    fireEvent.change(screen.getByLabelText("세트당 하루 예산 (원)"), { target: { value: "1350" } });
    fireEvent.change(screen.getByLabelText("광고 결과 파일 (CSV)"), { target: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });
    await waitFor(() => expect(f).toHaveBeenCalled());
    const body = f.mock.calls[0]![1]!.body as FormData;
    expect(JSON.parse(body.get("settings") as string)).toMatchObject({ "meta.adset.placements": "수동", "meta.adset.daily_budget": "1350" });
  });

  it("AN-03 shows every received setting in Ads Manager order with 테스트·다시 보기·그대로", async () => {
    const withSettings = { ...oven, matrix: { ...oven.matrix, settings: [
      { field_id: "meta.campaign.objective", path: "캠페인 › 캠페인 목표", value: "트래픽", kind: "그대로", note: "—" },
      { field_id: "meta.adset.placements", path: "광고 세트 › 노출 위치", value: "수동", kind: "그대로", note: "↓ 광고비 15% 싸요 · 확실해요" },
      { field_id: "meta.ad.media", path: "광고 › 형식·미디어", value: "정사각 이미지", kind: "테스트", note: "릴스에 세로 소재가 없어요" },
    ] } };
    vi.stubGlobal("fetch", vi.fn((url: string) => ok(String(url).includes("/assistant") ? { message: "m", suggestions: [] } : withSettings)));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "오븐로그 예시로 보기" }));
    await next("왜 그런지 보기 ▶");
    await next("내 세팅 보기 ▶");
    expect(screen.getByText("캠페인 목표")).toBeTruthy();
    expect(screen.getByText("트래픽")).toBeTruthy();
    expect(screen.getByRole("tab", { name: "그대로 2" })).toBeTruthy();
    expect(screen.getByText("정사각 이미지").closest("tr")!.className).toContain("border-l-accent");
    expect(screen.queryByText(/결과 파일로 알 수 있는 칸만/)).toBeNull();
  });
});

describe("예외 파일 (행동 열 없음 · A가 이김 / 세트 1개)", () => {
  function show(result: unknown) {
    vi.stubGlobal("fetch", vi.fn((url: string, init?: RequestInit) => {
      if (String(url).includes("/simulate")) return ok({ ...sim, tried: true, next_test: { total: 100000, per_set_lo: 4000, per_set_hi: 10000, share_lo: 0.076, share_hi: 0.2, source: "Feit" } });
      void init;
      return ok(result);
    }));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "오븐로그 예시로 보기" }));
  }

  it("when A wins, numbers are told from A's side (A가 나을 확률 95%), and ④ says the action column is missing", async () => {
    show(twoSets);
    expect(await screen.findByText("기본 문구를 바꾼 세트를 하나 더 만들어 보세요")).toBeTruthy();
    expect(screen.getByText(/노출 위치 = 자동 \(Advantage\+\)/)).toBeTruthy();
    await next("왜 그런지 보기 ▶");
    expect(screen.getByText(/행동 숫자가 파일에 없어요/)).toBeTruthy();
    await next("내 세팅 보기 ▶");
    expect(screen.queryByText(/다시 볼 칸 0개/)).toBeNull();
    await next("값 비교 보기 ▶");
    expect(screen.getByText("A(자동)가 같은 돈으로 손님을 더 데려왔어요")).toBeTruthy();
    const main = screen.getByRole("heading", { name: "손님 1명당 비용" }).closest("section")!;
    expect(within(main).getByText(/^A가 나을 확률/)).toBeTruthy();
    expect(within(main).getByText("95%")).toBeTruthy();
    expect(within(main).queryByText(/B가 나을 확률/)).toBeNull();
    expect(screen.getByText("하루씩 쌓일수록 A 쪽으로 굳어지고 있어요")).toBeTruthy();
  });

  it("a single ad set: no A/B wording, ① is '–', AN-04 still has a one-line summary", async () => {
    show(oneSet);
    expect(await screen.findByText(/페이지 속도·주소 점검/)).toBeTruthy();
    await next("왜 그런지 보기 ▶");
    const row1 = screen.getByText(/비교할 세트가 하나라 광고비 비교는 없어요/).closest("tr")!;
    expect(row1.querySelector('[aria-label="아직 몰라요"]')).toBeTruthy();
    await next("내 세팅 보기 ▶");
    await next("값 비교 보기 ▶");
    expect(screen.getByText("비교할 세트가 하나라 값 비교는 없어요")).toBeTruthy();
  });
});

describe("점검 2026-11-26", () => {
  function showResult(result: unknown) {
    vi.stubGlobal("fetch", vi.fn((url: string) => ok(String(url).includes("/simulate") ? { ...sim, tried: true } : result)));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "오븐로그 예시로 보기" }));
  }

  it("a blocked file shows no conclusion and cannot jump to ⑥", async () => {
    const block = { level: "block", mark: "■", kind: "not_same_days", text: "두 세트를 같은 날 같이 돌리지 않아서 비교할 수 없어요.", todo: "같은 날 같이 시작한 기간만 골라 다시 내보내 주세요.", screen: "AN-00" };
    showResult({ ...oven, blocked: true, alerts: [block, ...oven.alerts] });
    expect(await screen.findByRole("heading", { level: 1, name: "이 파일로는 아직 결론을 낼 수 없어요" })).toBeTruthy();
    expect(screen.getByText(/같은 날 같이 시작한 기간만 골라 다시 내보내 주세요/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "이 테스트 바로 준비 →" })).toBeNull();
    expect(screen.queryByRole("region", { name: "테스트할 칸" })).toBeNull();
    expect((screen.getByRole("button", { name: /⑥ 보내기/ }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("AN-04 card does not say B brought more customers when the verdict is 아직 몰라요", async () => {
    const v = oven.verdict!;
    const keep = [{ ...oven.matrix.keep[0]!, title: "B(수동) 세트 그대로 (노출 위치 · 연령·성별 함께)" }];
    showResult({ ...oven, matrix: { ...oven.matrix, keep }, replay: oven.replay.map((d) => ({ ...d, word: "아직 몰라요" })),
      verdict: { ...v, badge: { ...v.badge, word: "아직 몰라요", level: "보류", capped: ["한쪽에 돈이 몰려서 한 단계 낮췄어요"] } } });
    expect(await screen.findByText("B(수동) 세트 그대로 (노출 위치 · 연령·성별 함께)")).toBeTruthy();   // 여러 칸이 함께 다르면 한 칸 이름을 붙이지 않음
    for (const n of ["왜 그런지 보기 ▶", "내 세팅 보기 ▶", "값 비교 보기 ▶"]) await next(n);
    expect(screen.getByText("어느 쪽이 손님을 더 데려왔는지는 아직 몰라요")).toBeTruthy();
    expect(screen.queryByText("B가 같은 돈으로 손님을 더 데려왔어요")).toBeNull();
    expect(screen.getByText("B가 조금 더 데려왔지만 아직 우연일 수 있어요")).toBeTruthy();
    expect(screen.getByText("하루씩 쌓일수록 B 쪽으로 기울지만 아직 몰라요")).toBeTruthy();
  });

  it("evidence grade is not shown as a letter that looks like set A", async () => {
    render(<App />);
    expect(screen.getByText("근거: 실측")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/근거 A/);
  });
});

describe("UI/UX 점검 2026-11-26", () => {
  it("AN-05: when the server lost the result, the lead says so and offers one way out", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => String(url).includes("/simulate")
      ? Promise.resolve(new Response(JSON.stringify({ error: "분석 결과나 광고 세트를 찾지 못했어요. 파일을 다시 올려 주세요." }), { status: 404 }))
      : ok(oven)));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "오븐로그 예시로 보기" }));
    for (const n of ["왜 그런지 보기 ▶", "내 세팅 보기 ▶", "값 비교 보기 ▶", "바꾸면 어떻게 돼요? ▶"]) await next(n);
    await waitFor(() => expect(screen.getByRole("heading", { level: 2, name: /분석 결과나 광고 세트를 찾지 못했어요/ })).toBeTruthy());
    expect(screen.queryByText("계산하는 중…")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "파일 다시 올리기" }));
    expect(screen.getByRole("heading", { level: 1, name: "돌려 본 광고 결과를 올려 주세요" })).toBeTruthy();
  });

  it("AN-01 has one main button; [왜 그런지 보기] is a secondary button", async () => {
    showExample();
    await screen.findByRole("button", { name: "이 테스트 바로 준비 →" });
    expect(screen.getByRole("button", { name: "왜 그런지 보기 ▶" }).className).not.toMatch(/bg-button/);
    await next("왜 그런지 보기 ▶");
    expect(screen.getByRole("button", { name: "내 세팅 보기 ▶" }).className).toMatch(/bg-button/);   // 다른 단계는 [다음]이 주 버튼
  });

  it("[다른 파일 올리기] asks first, because the result would be lost", async () => {
    showExample();
    await screen.findByRole("button", { name: "이 테스트 바로 준비 →" });
    const confirm = vi.fn(() => false); vi.stubGlobal("confirm", confirm);
    fireEvent.click(screen.getByRole("button", { name: "다른 파일 올리기" }));
    expect(confirm).toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "이 테스트 바로 준비 →" })).toBeTruthy();
    confirm.mockReturnValue(true);
    fireEvent.click(screen.getByRole("button", { name: "다른 파일 올리기" }));
    expect(screen.getByRole("heading", { level: 1, name: "돌려 본 광고 결과를 올려 주세요" })).toBeTruthy();
  });
});

describe("점검 A·C·E·H", () => {
  it("AN-04: thresholds name the real side and the bars carry their own labels", async () => {
    showExample();
    for (const n of ["왜 그런지 보기 ▶", "내 세팅 보기 ▶", "값 비교 보기 ▶"]) await next(n);
    expect(document.body.textContent).not.toMatch(/○ 쪽이에요/);
    expect(screen.getByText(/70% 넘으면 'B 쪽이에요'/)).toBeTruthy();
    const card = screen.getByRole("heading", { name: "손님 1명당 비용" }).closest("section")!;
    expect(within(card).getByText("70%")).toBeTruthy();
    expect(within(card).getByText("90%")).toBeTruthy();
    const cost = screen.getByRole("heading", { name: /광고비는 확실히 B가 쌌어요/ }).closest("section")!;
    expect(within(cost).getByText(/^4,\d{3}원$/)).toBeTruthy();   // 범위 그림 왼쪽 끝 금액
    expect(within(cost).getByText(/^6,\d{3}원$/)).toBeTruthy();   // 오른쪽 끝 금액
  });

  it("AN-03 without settings explains the empty value instead of a bare dash", async () => {
    showExample();
    for (const n of ["왜 그런지 보기 ▶", "내 세팅 보기 ▶"]) await next(n);
    const table = screen.getByRole("table");
    expect(within(table).getAllByText("확장에서 넘기면 보여요").length).toBe(3);
  });
});

describe("점검 B", () => {
  it("AN-05 next-test money follows the spec wording and says why the classic amount is bigger", async () => {
    vi.stubGlobal("fetch", vi.fn((url: string) => ok(String(url).includes("/simulate")
      ? { ...sim, tried: true, next_test: { total: 100000, per_set_lo: 4000, per_set_hi: 10000, share_lo: 0.076, share_hi: 0.2, source: "Feit" } } : oven)));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "오븐로그 예시로 보기" }));
    for (const n of ["왜 그런지 보기 ▶", "내 세팅 보기 ▶", "값 비교 보기 ▶", "바꾸면 어떻게 돼요? ▶"]) await next(n);
    // 화면설계서 v4.2 AN-05 ④: '세트당 5,000원이면 최소한은 돼요 · 확실히 알려면 조금 더 필요할 수 있어요'
    expect(await screen.findByText("세트당 총 6,000원이면 최소한은 돼요 · 확실히 알려면 조금 더 필요할 수 있어요")).toBeTruthy();
    expect(screen.getByText(/작게 시험할 때는 '확실해요'까지 가지 않아도 돼요/)).toBeTruthy();
  });
});
