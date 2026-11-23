import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import FindStep from "../entrypoints/sidepanel/steps/FindStep";
import { initialState } from "../lib/flow";
import type { Research } from "../lib/api";

const research: Research = {
  headline: "쿠키선물세트를 찾는 사람은 30대 여성이 분야 평균의 1.82배",
  keywords: [{ keyword: "수제쿠키", total_qc: 12000 }, { keyword: "르뱅쿠키", total_qc: 5000 }],
  audience: { keyword: "쿠키선물세트", female: 0.82, ages: { "20": 0.09, "30": 0.31, "40": 0.34, "50": 0.21 }, top_age: "30" },
  fetched: "2026-11-15", source: "cache", notice: null,
};

afterEach(() => vi.unstubAllGlobals());

describe("FindStep", () => {
  it("keeps the typed product and shows a retry message when the server is down", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    render(<FindStep state={initialState()} dispatch={() => {}} />);
    fireEvent.change(screen.getByLabelText("파는 상품"), { target: { value: "수제 쿠키" } });
    fireEvent.click(screen.getByRole("button", { name: "찾아보기" }));
    await waitFor(() => expect(screen.getByText(/도우미 서버에 연결할 수 없어요/)).toBeTruthy());
    expect((screen.getByLabelText("파는 상품") as HTMLInputElement).value).toBe("수제 쿠키");
    expect(screen.getByRole("button", { name: "다시 시도" })).toBeTruthy();
  });

  it("searches when Enter is pressed in the product box", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(research), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const dispatch = vi.fn();
    render(<FindStep state={initialState()} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("파는 상품"), { target: { value: "수제 쿠키" } });
    fireEvent.submit(screen.getByLabelText("파는 상품"));
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ type: "researched" })));
  });

  it("shows the top group from top_age, the cache source line, and confirms the target", () => {
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research, product: "수제 쿠키" }} dispatch={dispatch} />);
    expect(screen.getByText("30대 여성")).toBeTruthy();
    expect(screen.getByText(/저장된 자료/)).toBeTruthy();
    expect(screen.getByText(/2026-11-15/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "이 사람들로 할게요" }));
    expect(dispatch).toHaveBeenCalledWith({
      type: "confirmTarget",
      target: { ageMin: 30, ageMax: 39, gender: "female" },
      keywords: ["수제쿠키", "르뱅쿠키"],
    });
  });

  it("confirms without the keywords the user dropped", () => {
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research, dropped: ["르뱅쿠키"] }} dispatch={dispatch} />);
    expect(screen.getByRole("button", { name: /르뱅쿠키/ }).getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(screen.getByRole("button", { name: "이 사람들로 할게요" }));
    expect(dispatch.mock.calls[0]![0].keywords).toEqual(["수제쿠키"]);
  });

  it("does not dead-end when Naver has nothing: the owner picks age and gender and goes on", () => {
    const empty: Research = { headline: "", keywords: [], audience: null, fetched: "", source: "cache",
      notice: "네이버에서 이 상품 검색 자료를 찾지 못했어요. 상품을 다른 말로 적어 보세요." };
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research: empty, product: "수제 쿠키" }} dispatch={dispatch} />);
    expect(screen.getByText(/검색 자료를 찾지 못했어요/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "직접 정하고 계속할게요" }));
    fireEvent.click(screen.getByRole("radio", { name: "40대" }));
    fireEvent.click(screen.getByRole("radio", { name: "여성" }));
    fireEvent.click(screen.getByRole("button", { name: "이 사람들로 할게요" }));
    expect(dispatch).toHaveBeenCalledWith({
      type: "confirmTarget",
      target: { ageMin: 40, ageMax: 49, gender: "female" },
      keywords: ["수제 쿠키"],
    });
  });

  it("manual pick starts at 30s, everyone", () => {
    const empty: Research = { headline: "", keywords: [], audience: null, fetched: "", source: "cache", notice: "추천할 만한 검색어를 찾지 못했어요." };
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research: empty, product: "수제 쿠키" }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "직접 정하고 계속할게요" }));
    expect((screen.getByRole("radio", { name: "30대" }) as HTMLInputElement).checked).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "이 사람들로 할게요" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "confirmTarget", target: { ageMin: 30, ageMax: 39, gender: "all" }, keywords: ["수제 쿠키"] });
  });

  it("source line names each part with its own date: today's lookup vs a saved baseline", () => {
    const withParts: Research = { ...research, source: "live", fetched: "2026-11-15", sources: [
      { part: "product", label: "검색어·연령", fetched: "2026-11-22", today: true },
      { part: "baseline", label: "분야 평균", fetched: "2026-11-15", today: false },
    ] };
    render(<FindStep state={{ ...initialState(), research: withParts }} dispatch={() => {}} />);
    const line = screen.getByText(/출처:/).textContent ?? "";
    expect(line).toContain("검색어·연령 오늘 조회");
    expect(line).toContain("분야 평균 11월 15일 저장본");
    expect(line).not.toContain("저장된 자료");
  });

  it("shows the words left out (만들기·매장·관련 낮은 말) under the keywords", () => {
    const r: Research = { ...research, negatives: ["쿠키만들기", "광주맛집"] };
    render(<FindStep state={{ ...initialState(), research: r }} dispatch={() => {}} />);
    expect(screen.getByText(/광고에서 뺄 말 2개/)).toBeTruthy();
    expect(screen.getByText("쿠키만들기")).toBeTruthy();
    expect(screen.getByText("광주맛집")).toBeTruthy();
  });
});

