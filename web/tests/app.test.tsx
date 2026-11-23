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
  const f = vi.fn((url: string, _init?: RequestInit) => (String(url).includes("/simulate") ? ok(sim) : ok(oven)));
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

describe("결과 (1차: 0~6, 9, 11)", () => {
  it("1 데이터 점검: what was read and the safety notes", async () => {
    showExample();
    const sec = await screen.findByRole("region", { name: /데이터 점검/ });
    expect(within(sec).getByText(/4일/)).toBeTruthy();
    expect(within(sec).getByText(/클릭 후 7일/)).toBeTruthy();
    expect(within(sec).getByText(/같은 사람/)).toBeTruthy();
  });

  it("2 게재 이상 알림 comes before the conclusion", async () => {
    showExample();
    const alert = await screen.findByRole("region", { name: /게재 이상 알림/ });
    const verdict = screen.getByRole("region", { name: /한 줄 결론/ });
    expect(within(alert).getByText(/11\/17은 두 세트 모두/)).toBeTruthy();
    expect(alert.compareDocumentPosition(verdict) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("3 한 줄 결론: one of the three words, 79%, and the sure thing", async () => {
    showExample();
    const sec = await screen.findByRole("region", { name: /한 줄 결론/ });
    expect(within(sec).getByText("B 쪽이에요")).toBeTruthy();
    expect(within(sec).getAllByText(/79%/).length).toBeGreaterThan(0);
    expect(within(sec).getByText(/약 18% 더 많이 보여줬어요/)).toBeTruthy();
    expect(within(sec).getByText("확실해요")).toBeTruthy();
  });

  it("4 핵심 숫자: owner words first, A and B side by side with ▲", async () => {
    showExample();
    const sec = await screen.findByRole("region", { name: /핵심 숫자/ });
    expect(within(sec).getByText(/1,000원으로 데려온 방문자/)).toBeTruthy();
    expect(within(sec).getByText("(CPC)")).toBeTruthy();
    expect(within(sec).getAllByText(/▲/).length).toBeGreaterThan(0);
  });

  it("5 퍼널: rates in owner words", async () => {
    showExample();
    const sec = await screen.findByRole("region", { name: /퍼널/ });
    expect(within(sec).getAllByText(/100명이 보면 약 2명이 눌렀어요/).length).toBeGreaterThan(0);
  });

  it("6 얼마나 믿을 수 있나: what can and cannot be said", async () => {
    showExample();
    const sec = await screen.findByRole("region", { name: /얼마나 믿을 수 있나/ });
    for (const h of ["확실히 말할 수 있어요", "방향만 말할 수 있어요", "아직 말할 수 없어요"]) expect(within(sec).getByText(h)).toBeTruthy();
    expect(within(sec).getByText(/매출에 더 좋은지/)).toBeTruthy();
  });

  it("9 예산 시뮬레이터: moving the budget asks the server again", async () => {
    const f = showExample();
    const sec = await screen.findByRole("region", { name: /예산 시뮬레이터/ });
    await waitFor(() => expect(within(sec).getByText(/73~133/)).toBeTruthy());
    fireEvent.change(within(sec).getByLabelText("예산"), { target: { value: "100000" } });
    await waitFor(() => expect(f.mock.calls.some(([u, o]) => String(u).includes("/simulate") && JSON.parse((o as RequestInit).body as string).budget === 100000)).toBe(true));
  });

  it("11 다음에 할 일: three lines, one change, a code copied with a toast", async () => {
    showExample();
    const writeText = vi.fn(() => Promise.resolve());
    Object.assign(navigator, { clipboard: { writeText } });
    const sec = await screen.findByRole("region", { name: /다음에 할 일/ });
    expect(within(sec).getByText(/이번에 알게 된 것/)).toBeTruthy();
    expect(within(sec).getByText(oven.code)).toBeTruthy();
    fireEvent.click(within(sec).getByRole("button", { name: "코드 복사" }));
    await waitFor(() => expect(screen.getByText("코드를 복사했어요")).toBeTruthy());
    expect(writeText).toHaveBeenCalledWith(oven.code);
  });
});

describe("접근성 (ui-styling 점검표)", () => {
  it("moves focus to the result title and announces it", async () => {
    showExample();
    const title = await screen.findByRole("heading", { level: 1, name: "이번 광고에서 알게 된 것" });
    await waitFor(() => expect(document.activeElement).toBe(title));
    expect(screen.getByText("결과를 다 계산했어요")).toBeTruthy();
  });

  it("has a skip link to the conclusion", async () => {
    showExample();
    const link = await screen.findByRole("link", { name: "결론으로 바로 가기" });
    expect(link.getAttribute("href")).toBe("#conclusion");
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

  it("announces simulator updates politely", async () => {
    showExample();
    const sec = await screen.findByRole("region", { name: /예산 시뮬레이터/ });
    expect(sec.querySelector('[aria-live="polite"]')).not.toBeNull();
  });
});
