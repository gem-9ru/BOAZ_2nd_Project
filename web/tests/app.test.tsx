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
  fireEvent.click(screen.getByRole("button", { name: "예시로 보기 (오븐로그 실측)" }));
  return f;
}

describe("화면 0 시작", () => {
  it("offers upload, example and test-prep with one promise line", () => {
    render(<App />);
    expect(screen.getByText(/20만 번 계산해/)).toBeTruthy();
    expect(screen.getByLabelText("메타 결과 CSV")).toBeTruthy();
    expect(screen.getByRole("button", { name: "예시로 보기 (오븐로그 실측)" })).toBeTruthy();
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
    fireEvent.change(screen.getByLabelText("메타 결과 CSV"), { target: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("다시 내보내"));
  });
});

async function next(name: RegExp | string) {
  fireEvent.click(await screen.findByRole("button", { name }));
}

describe("7단계 결과 (v4)", () => {
  it("AN-01 shows the one field to change first, with certainty and keep/watch/dont", async () => {
    showExample();
    expect(await screen.findByRole("heading", { level: 1, name: "그래서 뭘 바꾸면 돼요?" })).toBeTruthy();
    expect(screen.getByText("광고 › 형식·미디어")).toBeTruthy();
    expect(screen.getByText(/세로\(9:16\) 소재 추가/)).toBeTruthy();
    expect(screen.getByText("유력")).toBeTruthy();
    for (const h of ["그대로 두기", "지켜보기", "하지 말기"]) expect(screen.getByText(h)).toBeTruthy();
    expect(screen.getByText(/수동 · 피드만노출/)).toBeTruthy();
    expect(screen.getByText(/파일 확인: 4일/)).toBeTruthy();
  });

  it("alert bar shows the worst alert, counts by shape, and opens all", async () => {
    showExample();
    const bar = await screen.findByRole("region", { name: "알림" });
    expect(within(bar).getByText(/11\/17/)).toBeTruthy();
    expect(within(bar).getByText("■ 0 · ▲ 2 · ● 1")).toBeTruthy();
    fireEvent.click(within(bar).getByRole("button", { name: "모두 보기" }));
    expect(within(bar).getByText(/메타는 자동 노출 위치를 권하지만/)).toBeTruthy();
  });

  it("[다음] walks the steps with labels naming the next screen; past steps can be revisited", async () => {
    showExample();
    await next("왜 그 칸인지 보기");
    expect(await screen.findByRole("heading", { level: 1, name: "어디서 막혔나요?" })).toBeTruthy();
    expect(screen.getByText("1. 노출 단가 (CPM)")).toBeTruthy();
    expect(screen.getByText(/CPM이 15% 비쌈/)).toBeTruthy();
    await next("내 세팅 카드 보기");
    expect(screen.getByText("광고 관리자 순서로 본 내 세팅")).toBeTruthy();
    expect(screen.getByText("변경")).toBeTruthy();
    await next("값 비교 보기");
    expect(screen.getByRole("heading", { level: 1, name: "어떤 값이 더 나았어요?" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /① 결론/ }));
    expect(screen.getByRole("heading", { level: 1, name: "그래서 뭘 바꾸면 돼요?" })).toBeTruthy();
  });

  it("future steps are locked except ⑥, and [바로 적용하기] jumps to ⑥", async () => {
    showExample();
    await screen.findByText("광고 › 형식·미디어");
    expect((screen.getByRole("button", { name: /③ 내 세팅/ }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: /⑥ 보내기/ }) as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(screen.getByRole("button", { name: "바로 적용하기" }));
    expect(screen.getByRole("heading", { level: 1, name: "이제 어떻게 적용해요?" })).toBeTruthy();
  });

  it("AN-04 ★ tabs: metrics, by day (26→65→79%), placements with adjusted CTR and '참고만'", async () => {
    showExample();
    for (const n of ["왜 그 칸인지 보기", "내 세팅 카드 보기", "값 비교 보기"]) await next(n);
    expect(screen.getByText("확실히 말할 수 있어요")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "날짜별" }));
    expect(screen.getByText("79%")).toBeTruthy();
    fireEvent.click(screen.getByRole("tab", { name: "노출 위치별" }));
    expect(screen.getAllByText("참고만").length).toBeGreaterThan(0);
    expect(screen.getByText(/Breakdown effect/)).toBeTruthy();
  });

  it("AN-05 simulator moves in 5,000 steps, marks untried budgets as 가설, shows Test & Roll and backtest", async () => {
    const f = showExample();
    for (const n of ["왜 그 칸인지 보기", "내 세팅 카드 보기", "값 비교 보기", "바꾸면 얼마나 좋아지나 보기"]) await next(n);
    const slider = screen.getByLabelText("예산") as HTMLInputElement;
    expect(slider.step).toBe("5000");
    fireEvent.change(slider, { target: { value: "20000" } });
    await waitFor(() => expect(screen.getByText("가설")).toBeTruthy());
    expect(f.mock.calls.some(([u, o]) => String(u).includes("/simulate") && JSON.parse((o as RequestInit).body as string).budget === 20000)).toBe(true);
    expect(screen.getByText(/Test & Roll/)).toBeTruthy();
    expect(screen.getByText("이 계산, 맞은 적 있어요?")).toBeTruthy();
  });

  it("AN-06 sends the code to the extension with a toast, and lists the checklist", async () => {
    showExample();
    const writeText = vi.fn(() => Promise.resolve());
    Object.assign(navigator, { clipboard: { writeText } });
    fireEvent.click(await screen.findByRole("button", { name: "바로 적용하기" }));
    expect(screen.getByText(oven.code)).toBeTruthy();
    expect(screen.getAllByRole("checkbox").length).toBeGreaterThan(0);
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
    expect(within(panel).getByText(/11\/17/)).toBeTruthy();
    await next("왜 그 칸인지 보기");
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
    const title = await screen.findByRole("heading", { level: 1, name: "그래서 뭘 바꾸면 돼요?" });
    await waitFor(() => expect(document.activeElement).toBe(title));
    expect(screen.getByText("결과를 다 계산했어요")).toBeTruthy();
  });

  it("links the upload error to the file input", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.resolve(new Response(JSON.stringify({ error: "다시 내보내 주세요" }), { status: 400 }))));
    render(<App />);
    const input = screen.getByLabelText("메타 결과 CSV");
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
    expect(await screen.findByText(/세팅값 13개를 받았어요/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: /내 세팅 알려 주기/ })).toBeNull();
    fireEvent.change(screen.getByLabelText("메타 결과 CSV"), { target: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });
    await waitFor(() => expect(f.mock.calls.some(([u, o]) => String(u).endsWith("/analysis") && (o?.body as FormData).get("settings_key") === "K3yK3yK3yK3yK3y")).toBe(true));
  });

  it("without the extension: 5 questions (목표·예산·연령·노출 위치·소재 형식) go with the upload", async () => {
    const f = vi.fn((_url: string, _init?: RequestInit) => ok(oven));
    vi.stubGlobal("fetch", f);
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: /내 세팅 알려 주기/ }));
    for (const g of ["캠페인 목표", "세트당 하루 예산", "연령", "노출 위치", "소재 형식"]) expect(screen.getByRole("group", { name: g })).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "수동" }));
    fireEvent.change(screen.getByLabelText("세트당 하루 예산 (원)"), { target: { value: "1350" } });
    fireEvent.change(screen.getByLabelText("메타 결과 CSV"), { target: { files: [new File(["a"], "x.csv", { type: "text/csv" })] } });
    await waitFor(() => expect(f).toHaveBeenCalled());
    const body = f.mock.calls[0]![1]!.body as FormData;
    expect(JSON.parse(body.get("settings") as string)).toMatchObject({ "meta.adset.placements": "수동", "meta.adset.daily_budget": "1350" });
  });

  it("AN-03 shows every received setting in Ads Manager order with 변경·유지·그대로", async () => {
    const withSettings = { ...oven, matrix: { ...oven.matrix, settings: [
      { field_id: "meta.campaign.objective", path: "캠페인 › 캠페인 목표", value: "트래픽", kind: "그대로", note: "이번 결과로는 바꿀 이유가 없어요." },
      { field_id: "meta.adset.placements", path: "광고 세트 › 노출 위치", value: "수동", kind: "유지", note: "CPM 15% 저렴" },
      { field_id: "meta.ad.media", path: "광고 › 형식·미디어", value: "정사각 이미지", kind: "변경", note: "릴스용 세로 추가" },
    ] } };
    vi.stubGlobal("fetch", vi.fn((url: string) => ok(String(url).includes("/assistant") ? { message: "m", suggestions: [] } : withSettings)));
    render(<App />);
    fireEvent.click(screen.getByRole("button", { name: "예시로 보기 (오븐로그 실측)" }));
    await next("왜 그 칸인지 보기");
    await next("내 세팅 카드 보기");
    expect(screen.getByText("캠페인 목표")).toBeTruthy();
    expect(screen.getByText(/지금 값: 트래픽/)).toBeTruthy();
    expect(screen.getByText("그대로")).toBeTruthy();
    expect(screen.queryByText(/결과 파일로 알 수 있는 칸만/)).toBeNull();
  });
});
