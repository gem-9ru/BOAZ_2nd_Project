import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import ResultStep from "../entrypoints/sidepanel/steps/ResultStep";
import UploadStep from "../entrypoints/sidepanel/steps/UploadStep";
import ReportApp from "../entrypoints/report/App";
import { initialState } from "../lib/flow";
import { stepsFor } from "../lib/guide";
import { GUIDE } from "../lib/guideList";
import type { Analysis } from "../lib/api";
import fixture from "./fixtures/analysis.json";

const hold = fixture as unknown as Analysis;
const fired: Analysis = {
  ...hold,
  status: "fired",
  finding: { id: "rule.placement_quality", title: "노출 위치 품질", funnel: "클릭", message: "클릭의 50%가 다른 앱 광고 자리에서 나왔어요." },
  changes: [{ field_id: "meta.adset.placements", label: "노출 위치", new: "Audience Network 제외", note: "싸지만 안 팔리는 자리를 빼요" }],
  expect: { metric: "visit_rate", label: "클릭 뒤 도착률", current: [0.6, 0.9], expected: [0.63, 1.0], prob_better: null, grade: "hypothesis" },
};

afterEach(() => vi.unstubAllGlobals());

describe("ResultStep", () => {
  it("renders three cards: problem, change, expectation", () => {
    render(<ResultStep state={{ ...initialState(), step: "result", result: fired }} dispatch={() => {}} />);
    expect(screen.getByRole("heading", { name: "노출 위치 품질" })).toBeTruthy();
    expect(screen.getByText(/Audience Network 제외/)).toBeTruthy();
    expect(screen.getByText("가설")).toBeTruthy();
  });

  it("hold shows '아직 판단하기 일러요' and the B probability", () => {
    render(<ResultStep state={{ ...initialState(), step: "result", result: hold }} dispatch={() => {}} />);
    expect(screen.getByRole("heading", { name: "아직 판단하기 일러요" })).toBeTruthy();
    expect(screen.getByText(/B_피드만노출\(AN제외\)이 나을 확률 약 61%/)).toBeTruthy();
    expect(screen.getByText("가설")).toBeTruthy();
  });

  it("expectation is a range, never a single number", () => {
    render(<ResultStep state={{ ...initialState(), step: "result", result: hold }} dispatch={() => {}} />);
    expect(screen.getByText(/1\.2%\s*~\s*2\.2%/)).toBeTruthy();
    expect(screen.getByText(/1\.3%\s*~\s*2\.0%/)).toBeTruthy();
  });

  it("바꾸러 가기 starts the fix; edit steps cover only the changed fields", () => {
    const dispatch = vi.fn();
    render(<ResultStep state={{ ...initialState(), step: "result", result: fired }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "바꾸러 가기" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "startFix" });
    expect(stepsFor("edit", GUIDE, [], fired.changes).map((s) => s.entry.id)).toEqual(["meta.adset.placements"]);
  });
});

describe("UploadStep", () => {
  it("shows the server's message on a bad file and keeps the upload control", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "'광고 세트' 열이 없어요." }), { status: 400 })));
    const dispatch = vi.fn();
    render(<UploadStep state={{ ...initialState(), step: "upload" }} dispatch={dispatch} />);
    const input = screen.getByLabelText("결과 파일 (CSV)");
    fireEvent.change(input, { target: { files: [new File(["x"], "bad.csv", { type: "text/csv" })] } });
    await waitFor(() => expect(screen.getByRole("alert").textContent).toContain("열이 없어요"));
    expect(screen.getByLabelText("결과 파일 (CSV)")).toBeTruthy();
    expect(dispatch).not.toHaveBeenCalled();
  });

  it("dispatches analyzed on success", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(hold), { status: 200 })));
    const dispatch = vi.fn();
    render(<UploadStep state={{ ...initialState(), step: "upload" }} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("결과 파일 (CSV)"), { target: { files: [new File(["x"], "a.csv")] } });
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "analyzed", result: hold }));
  });
});

describe("report", () => {
  it("renders the funnel 1,822 → 30 → 24 and the A/B probability", () => {
    render(<ReportApp result={hold} />);
    expect(screen.getByText("1,822")).toBeTruthy();
    expect(screen.getByText("30")).toBeTruthy();
    expect(screen.getByText("24")).toBeTruthy();
    expect(screen.getAllByText(/61%/).length).toBeGreaterThan(0);
    expect(screen.getByRole("table", { name: "일별 숫자" })).toBeTruthy();
  });
});
