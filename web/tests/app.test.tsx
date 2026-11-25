import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";
import oven from "./fixtures/oven.json";

const ok = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
const sim = { budget: 30000, runs: 200000, arm: "B", impressions: { median: 5000, lo: 4500, hi: 5600 },
  link_clicks: { median: 100, lo: 73, hi: 133 }, visits: { median: 78, lo: 55, hi: 108 },
  histogram: [{ lo: 60, hi: 80, count: 100000 }, { lo: 80, hi: 140, count: 100000 }], limits: "한계" };

afterEach(() => vi.unstubAllGlobals());

function showExample() {
  const f = vi.fn((url: string, init?: RequestInit) => {
    const u = String(url);
    if (u.includes("/simulate")) return ok({ ...sim, tried: JSON.parse(init!.body as string).budget <= 5308, next_test: { total: 20000, per_set_lo: 1000, per_set_hi: 2000, share_lo: 0.076, share_hi: 0.2, source: "Feit" } });
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

describe("화면 0 시작", () => {
  it("offers upload, example and test-prep with one promise line", () => {
    render(<App />);
    expect(screen.getByText(/20만 번 계산해/)).toBeTruthy();
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
    expect(within(card).getByText(/5,000원씩 같이 돌려서 직접 비교해요/)).toBeTruthy();
    expect(within(card).queryByText(/쪽이에요|확실해요/)).toBeNull();
    for (const h of ["유지", "지켜보기", "하지 말기"]) expect(screen.getByText(h)).toBeTruthy();
    expect(screen.getByText(/노출 위치 = 직접 고르기\(수동\)/)).toBeTruthy();
    expect(screen.getByText(/같은 돈으로 손님 A 10명 · B 14명/)).toBeTruthy();
    expect(screen.getByText("B 쪽이에요")).toBeTruthy();
    expect(screen.getByText(/광고비 10,616원 · 보여진 횟수 1,822번 · 클릭 30번/)).toBeTruthy();
    ownerTextOk();
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
    expect(screen.getByText("광고가 보이는 단계에서만 A가 비쌌고, 그 아래는 괜찮아요")).toBeTruthy();
    expect(screen.getByText(/B\(수동\)가 15% 싸요/)).toBeTruthy();
    expect(screen.getByText(/1,000명이 보면 A 약 16명 · B 약 17명 → 괜찮아요/)).toBeTruthy();
    expect(screen.getByText(/누른 100명 중 A 77명 · B 82명 → 괜찮아요/)).toBeTruthy();
    expect(within(screen.getByRole("region", { name: "알림" })).getByText(/클릭이 적어서 아직 몰라요/)).toBeTruthy();
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

  it("AN-06 prepares the test: 지금 세트/새 세트, 4-item checklist without ALT numbers, send with a toast", async () => {
    showExample();
    const writeText = vi.fn(() => Promise.resolve());
    Object.assign(navigator, { clipboard: { writeText } });
    fireEvent.click(await screen.findByRole("button", { name: "이 테스트 바로 준비 →" }));
    expect(screen.getByText(oven.code)).toBeTruthy();
    expect(screen.getByText(/새 세트: \+ 세로\(9:16\) 1개/)).toBeTruthy();
    expect(screen.getAllByRole("checkbox").length).toBe(4);
    expect(screen.getByText("두 세트는 같은 날 같이 시작")).toBeTruthy();
    expect(document.body.textContent).not.toMatch(/ALT-\d/);
    expect(within(screen.getByRole("region", { name: "알림" })).getByText(/주의 2건은 다음 테스트 체크리스트에 넣었어요/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "확장 프로그램으로 보내기" }));
    await waitFor(() => expect(screen.getByText(/코드를 복사했어요/)).toBeTruthy());
    expect(writeText).toHaveBeenCalledWith(oven.code);
  });
});

describe("광고 어시스턴트 (오른쪽 고정)", () => {
  it("greets each step once with two suggestions and the alert bubble for that screen", async () => {
    showExample();
    const panel = await screen.findByRole("complementary", { name: "광고 어시스턴트" });
    await waitFor(() => expect(within(panel).getByText("AN-01 첫 말")).toBeTruthy());
    expect(within(panel).getByRole("button", { name: "질문 하나" })).toBeTruthy();
    const log = panel.querySelector("[aria-live]")!;
    expect(log.children[0]!.textContent).toContain("11/17");   // v4.2: 알림 말풍선이 먼저, 그다음 이 단계 요약
    expect(log.children[1]!.textContent).toBe("AN-01 첫 말");
    await next("왜 그런지 보기 ▶");
    await waitFor(() => expect(within(panel).getByText("AN-02 첫 말")).toBeTruthy());
  });

  it("a suggested question gets an answer", async () => {
    showExample();
    const panel = await screen.findByRole("complementary", { name: "광고 어시스턴트" });
    fireEvent.click(await within(panel).findByRole("button", { name: "질문 하나" }));
    await waitFor(() => expect(within(panel).getByText("답: 질문 하나")).toBeTruthy());
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
