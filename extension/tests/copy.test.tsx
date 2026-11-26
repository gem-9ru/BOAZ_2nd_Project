import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import CopyStep from "../entrypoints/sidepanel/steps/CopyStep";
import { initialState } from "../lib/flow";

afterEach(() => vi.unstubAllGlobals());

const three = [1, 2, 3].map((i) => ({ primary_text: `본문 ${i}`, headline: `제목 ${i}` }));

describe("CopyStep", () => {
  it("asks for strengths, shows three copies, and picks one", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "template" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const dispatch = vi.fn();
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "수제 쿠키", keywords: ["수제쿠키"] }} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("상품의 좋은 점"), { target: { value: "버터 듬뿍" } });
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => expect(screen.getAllByRole("button", { name: /이 문구로/ })).toHaveLength(3));
    expect(JSON.parse(f.mock.calls[0]![1].body)).toEqual({ product: "수제 쿠키", strengths: ["버터 듬뿍"], keywords: ["수제쿠키"], avoid: [] });
    fireEvent.click(screen.getAllByRole("button", { name: /이 문구로/ })[1]!);
    expect(dispatch).toHaveBeenCalledWith({ type: "pickCopy", copy: three[1] });
  });

  it("passes the left-out words and can write again", async () => {
    const f = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const research = { headline: "", keywords: [], audience: null, fetched: "", source: "live" as const, notice: null, negatives: ["쿠키만들기"] };
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "수제 쿠키", keywords: ["수제쿠키"], research }} dispatch={() => {}} />);
    fireEvent.change(screen.getByLabelText("상품의 좋은 점"), { target: { value: "버터 듬뿍" } });
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => expect(screen.getAllByRole("button", { name: /이 문구로/ })).toHaveLength(3));
    expect(JSON.parse(f.mock.calls[0]![1].body).avoid).toEqual(["쿠키만들기"]);
    fireEvent.click(screen.getByRole("button", { name: "다른 문구로 다시 써 주세요" }));
    await waitFor(() => expect(f).toHaveBeenCalledTimes(2));
  });

  const mods = [
    { word: "개별포장", group: "포장", total_qc: 12000, examples: [] },
    { word: "버터", group: "맛·재료", total_qc: 800, examples: [] },
  ];
  const research = { headline: "", keywords: [], audience: null, fetched: "", source: "live" as const, notice: null, negatives: [], modifiers: mods };
  const seg = { intent: "선물·답례" as const, label: "선물로 찾는 손님", keywords: [], total_qc: 1, lead: "", audience: null,
    trend: { monthly: {}, peak_month: 12, seasonal: true }, trend_source: null } as never;
  const withMods = () => ({ ...initialState(), step: "copy" as const, product: "수제 쿠키", keywords: ["수제쿠키"], research, segment: seg });

  it("modifier chips grouped and required", () => {
    render(<CopyStep state={withMods()} dispatch={() => {}} />);
    expect(screen.getByText("포장")).toBeTruthy();
    expect(screen.getByText("맛·재료")).toBeTruthy();
    expect(screen.queryByText("배송")).toBeNull();
    expect(screen.getByRole("button", { name: /개별포장/ }).getAttribute("aria-pressed")).toBe("false");
    expect(screen.getByRole("button", { name: "문구 써 주세요" }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByText("▲ 하나 이상 고르거나 적어 주세요")).toBeTruthy();
  });

  it("sends picked chips, typed words and segment", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    render(<CopyStep state={withMods()} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /개별포장/ }));
    fireEvent.change(screen.getByLabelText("직접 적기"), { target: { value: "버터 듬뿍" } });
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => expect(f).toHaveBeenCalled());
    const body = JSON.parse(f.mock.calls[0]![1].body);
    expect(body.strengths).toEqual(["개별포장", "버터 듬뿍"]);
    expect(body.segment.label).toBe("선물로 찾는 손님");
    expect(body.segment.peak_month).toBe(12);
  });

  it("shows basis under each copy", async () => {
    const withBasis = three.map((c) => ({ ...c, basis: ["개별포장", "선물로 찾는 손님"] }));
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: withBasis, source: "claude" }), { status: 200 })));
    render(<CopyStep state={withMods()} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /개별포장/ }));
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => expect(screen.getAllByText("근거: 개별포장 · 선물로 찾는 손님")).toHaveLength(3));
  });

  it("change customer goes back to find", () => {
    const dispatch = vi.fn();
    render(<CopyStep state={withMods()} dispatch={dispatch} />);
    expect(screen.getByText(/고른 손님: 선물로 찾는 손님/).textContent).toContain("12월에 많음");
    fireEvent.click(screen.getByRole("button", { name: "바꾸기" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "editFind" });
  });

  it("non-seasonal segment: no peak month shown or sent", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const flatSeg = { ...(seg as object), trend: { monthly: {}, peak_month: 3, seasonal: false } } as never;
    render(<CopyStep state={{ ...withMods(), segment: flatSeg }} dispatch={() => {}} />);
    expect(screen.getByText(/고른 손님: 선물로 찾는 손님/).textContent).not.toContain("월에 많음");
    fireEvent.click(screen.getByRole("button", { name: /개별포장/ }));
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => expect(f).toHaveBeenCalled());
    const body = JSON.parse(f.mock.calls[0]![1].body);
    expect(body.segment).toEqual({ intent: "선물·답례", label: "선물로 찾는 손님" });
  });

  it("'그 밖' group is last and shown open (brands are filtered on the server), with a one-line hint", () => {
    const others = [...mods, { word: "보온", group: "그 밖", total_qc: 5000, examples: [] }, { word: "경량", group: "그 밖", total_qc: 900, examples: [] }];
    render(<CopyStep state={{ ...withMods(), research: { ...research, modifiers: others } }} dispatch={() => {}} />);
    expect(screen.getByRole("button", { name: /보온/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /경량/ })).toBeTruthy();
    const groupLabels = screen.getAllByText(/^(포장|맛·재료|그 밖)$/).map((e) => e.textContent);
    expect(groupLabels[groupLabels.length - 1]).toBe("그 밖");
    expect(screen.getByText("다른 가게·브랜드 이름이 보이면 고르지 마세요. 문구에 그대로 들어가요.")).toBeTruthy();
  });

  it("old state without modifiers still lets owner type", () => {
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "쿠키" }} dispatch={() => {}} />);
    expect(screen.getByRole("button", { name: "문구 써 주세요" }).hasAttribute("disabled")).toBe(false);
  });
});
