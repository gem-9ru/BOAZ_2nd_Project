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
});
