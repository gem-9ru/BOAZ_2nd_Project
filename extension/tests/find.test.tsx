import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import FindStep from "../entrypoints/sidepanel/steps/FindStep";
import { initialState } from "../lib/flow";
import type { Research, Segment } from "../lib/api";

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
    expect(screen.getByText("30~50대 여성")).toBeTruthy();   // 40대가 가장 많고 30·50대도 많이 찾음
    expect(screen.getByText(/저장된 자료/)).toBeTruthy();
    expect(screen.getByText(/2026-11-15/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "이 사람들로 할게요" }));
    expect(dispatch).toHaveBeenCalledWith({
      type: "confirmTarget",
      target: { ageMin: 30, ageMax: 59, gender: "female" },
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
    fireEvent.click(screen.getByRole("button", { name: "이 손님들로 할게요" }));
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
    fireEvent.click(screen.getByRole("button", { name: "이 손님들로 할게요" }));
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
  it("first visit: '수제 쿠키로 먼저 보기' fills the box and searches", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(research), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const dispatch = vi.fn();
    render(<FindStep state={initialState()} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "수제 쿠키로 먼저 보기" }));
    expect((screen.getByLabelText("파는 상품") as HTMLInputElement).value).toBe("수제 쿠키");
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ type: "researched", product: "수제 쿠키" })));
  });

  it("shows a skeleton status while searching", async () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
    render(<FindStep state={initialState()} dispatch={() => {}} />);
    fireEvent.change(screen.getByLabelText("파는 상품"), { target: { value: "수제 쿠키" } });
    fireEvent.click(screen.getByRole("button", { name: "찾아보기" }));
    expect(screen.getByRole("status").textContent).toContain("네이버에서 찾는 중");
  });

  it("says the result is for the old product when the box was changed", () => {
    render(<FindStep state={{ ...initialState(), research, product: "수제 쿠키" }} dispatch={() => {}} />);
    fireEvent.change(screen.getByLabelText("파는 상품"), { target: { value: "강아지 간식" } });
    expect(screen.getByText(/'수제 쿠키' 결과예요/)).toBeTruthy();
  });

  it("explains why the confirm button is off when every keyword is dropped", () => {
    render(<FindStep state={{ ...initialState(), research, dropped: ["수제쿠키", "르뱅쿠키"] }} dispatch={() => {}} />);
    expect(screen.getByText(/검색어를 하나 이상 남겨 주세요/)).toBeTruthy();
  });

  it("labels each age bar with its share", () => {
    render(<FindStep state={{ ...initialState(), research }} dispatch={() => {}} />);
    expect(screen.getByText("34%")).toBeTruthy();
    expect(screen.getByText(/여성 82%/)).toBeTruthy();
  });
});

const CATEGORIES = [
  ["50000000", "패션의류"], ["50000001", "패션잡화"], ["50000002", "화장품/미용"], ["50000003", "디지털/가전"],
  ["50000004", "가구/인테리어"], ["50000005", "출산/육아"], ["50000006", "식품"], ["50000007", "스포츠/레저"],
  ["50000008", "생활/건강"], ["50000009", "여가/생활편의"], ["50000010", "면세점"], ["50005542", "도서"],
].map(([code, name]) => ({ code: code!, name: name! }));

const months = (peak: number): Record<string, number> => {
  const out: Record<string, number> = {};
  for (let i = 0; i < 12; i++) {
    const m = ((11 + i) % 12) + 1; // 2025-12 … 2026-11
    const y = m === 12 ? 2025 : 2026;
    out[`${y}-${String(m).padStart(2, "0")}`] = m === peak ? 100 : 20 + m;
  }
  return out;
};

const segs: Segment[] = [
  { intent: "상품", label: "상품 자체로 찾는 손님", keywords: ["수제쿠키", "르뱅쿠키"], total_qc: 17000, lead: "수제쿠키",
    audience: { female: 0.7, ages: { "20": 0.4, "30": 0.3, "40": 0.2 }, top_age: "20" },
    trend: { monthly: months(5), peak_month: 5, seasonal: false }, trend_source: "search", line: "20대 여성이 많이 찾아요" },
  { intent: "선물·답례", label: "선물로 찾는 손님", keywords: ["답례품쿠키", "쿠키선물세트"], total_qc: 5400, lead: "답례품쿠키",
    audience: { female: 0.81, ages: { "20": 0.1, "30": 0.5, "40": 0.3 }, top_age: "30" },
    trend: { monthly: months(12), peak_month: 12, seasonal: true }, trend_source: "shopping", line: "30대 여성이 분야 평균의 2.8배, 12월에 가장 많이 찾아요" },
  { intent: "시즌", label: "시즌에 찾는 손님", keywords: ["크리스마스쿠키"], total_qc: 1200, lead: "크리스마스쿠키",
    audience: null, trend: null, trend_source: null, line: "누가 찾는지 자료가 아직 없어요" },
];

const withSegs: Research = {
  ...research,
  keywords: [
    { keyword: "수제쿠키", total_qc: 12000 }, { keyword: "르뱅쿠키", total_qc: 5000 },
    { keyword: "답례품쿠키", total_qc: 3000 }, { keyword: "쿠키선물세트", total_qc: 2400 }, { keyword: "크리스마스쿠키", total_qc: 1200 },
  ],
  category: { code: "50000006", name: "식품", guessed: true },
  categories: CATEGORIES,
  segments: segs,
  modifiers: [],
};

const okFetch = () => {
  const f = vi.fn().mockResolvedValue(new Response(JSON.stringify(withSegs), { status: 200 }));
  vi.stubGlobal("fetch", f);
  return f;
};
const sentBody = (f: ReturnType<typeof vi.fn>) => JSON.parse((f.mock.calls[0]![1] as RequestInit).body as string);

describe("FindStep — 분야·손님 무리", () => {
  it("guessed category is shown and can be changed", async () => {
    const f = okFetch();
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키", category: "50000006" }} dispatch={dispatch} />);
    expect(screen.getByText(/'수제 쿠키'는 '식품'\(으\)로 볼게요/)).toBeTruthy();
    expect(screen.queryByRole("radiogroup", { name: "분야" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "바꾸기" }));
    expect(screen.getAllByRole("radio", { name: /./ }).length).toBeGreaterThanOrEqual(12);
    fireEvent.click(screen.getByRole("radio", { name: "화장품/미용" }));
    await waitFor(() => expect(f).toHaveBeenCalled());
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith({ type: "pickCategory", category: "50000002" }));
    const body = sentBody(f);
    expect(body.category).toBe("50000002");
    expect(body.product).toBe("수제 쿠키");
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ type: "researched" })));
  });

  it("unknown category asks before showing segments", () => {
    const r: Research = { ...withSegs, category: null, segments: [] };
    render(<FindStep state={{ ...initialState(), research: r, product: "수제 쿠키" }} dispatch={() => {}} />);
    expect(screen.getByText("분야를 골라 주시면 손님을 찾아볼게요")).toBeTruthy();
    expect(screen.getByRole("radiogroup", { name: "분야" })).toBeTruthy();
    expect(screen.getByRole("radio", { name: "도서" })).toBeTruthy();
    expect(screen.queryByText(/직접 정하고 계속할게요/)).toBeNull();
    // 부르는 말은 그대로 보인다
    expect(screen.getByText("손님은 이렇게도 불러요")).toBeTruthy();
  });

  it("unknown category with candidates shows them first; picking one sends category", async () => {
    const f = okFetch();
    const dispatch = vi.fn();
    const r: Research = { ...withSegs, category: null, segments: [],
      category_candidates: [{ code: "50000007", name: "스포츠/레저" }, { code: "50000004", name: "가구/인테리어" }] };
    render(<FindStep state={{ ...initialState(), research: r, product: "캠핑의자" }} dispatch={dispatch} />);
    expect(screen.getByText("이 중 어디에 가까워요?")).toBeTruthy();
    expect(screen.getAllByRole("radio")).toHaveLength(2);
    expect(screen.queryByRole("radio", { name: "도서" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "다른 분야" }));
    expect(screen.getAllByRole("radio").length).toBeGreaterThanOrEqual(12);
    fireEvent.click(screen.getByRole("radio", { name: "도서" }));
    await waitFor(() => expect(f).toHaveBeenCalled());
    expect(sentBody(f).category).toBe("50005542");
  });

  it("candidate pick sends its category", async () => {
    const f = okFetch();
    const r: Research = { ...withSegs, category: null, segments: [],
      category_candidates: [{ code: "50000007", name: "스포츠/레저" }, { code: "50000004", name: "가구/인테리어" }] };
    render(<FindStep state={{ ...initialState(), research: r, product: "캠핑의자" }} dispatch={vi.fn()} />);
    fireEvent.click(screen.getByRole("radio", { name: "스포츠/레저" }));
    await waitFor(() => expect(f).toHaveBeenCalled());
    expect(sentBody(f).category).toBe("50000007");
  });

  it("segment cards: pick one, confirm sends segment", () => {
    const dispatch = vi.fn();
    const { rerender } = render(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키" }} dispatch={dispatch} />);
    const group = screen.getByRole("radiogroup", { name: "광고를 보여 줄 손님" });
    expect(within(group).getAllByRole("radio")).toHaveLength(3);
    expect(screen.getByText("▲ 광고를 보여 줄 손님을 하나 골라 주세요.")).toBeTruthy();
    expect((screen.getByRole("button", { name: "이 손님들로 할게요" }) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(within(group).getAllByRole("radio")[1]!);
    expect(dispatch).toHaveBeenCalledWith({ type: "pickSegment", segment: segs[1] });
    rerender(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키", segment: segs[1] }} dispatch={dispatch} />);
    expect(screen.getByText(/주로 찾는 말: 답례품쿠키 · 이 무리 전체 한 달 5,400회/)).toBeTruthy();
    expect(screen.getByText(/네이버 쇼핑 클릭 기준/)).toBeTruthy();
    expect(screen.queryByText(/대표 검색어|달별 자료|쇼핑인사이트/)).toBeNull();   // 개발자 말 없음
    fireEvent.click(screen.getByRole("button", { name: "이 손님들로 할게요" }));
    const ev = dispatch.mock.calls.at(-1)![0];
    expect(ev.type).toBe("confirmTarget");
    expect(ev.segment.intent).toBe("선물·답례");
    expect(ev.target).toEqual({ ageMin: 30, ageMax: 49, gender: "female" });   // 30대 50% · 40대 30% → 30~40대
    expect(ev.keywords).toEqual(withSegs.keywords.map((k) => k.keyword));
  });

  it("single segment is preselected", () => {
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research: { ...withSegs, segments: [segs[1]!] }, product: "수제 쿠키" }} dispatch={dispatch} />);
    expect(dispatch.mock.calls.filter(([e]) => e.type === "pickSegment")).toEqual([[{ type: "pickSegment", segment: segs[1] }]]);
  });

  it("dropping a segment lead offers re-search", async () => {
    const f = okFetch();
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키", category: "50000006", dropped: ["답례품쿠키"] }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "이 말로 손님 다시 찾기" }));
    await waitFor(() => expect(f).toHaveBeenCalled());
    const body = sentBody(f);
    expect(body.keywords).not.toContain("답례품쿠키");
    expect(body.keywords).toContain("수제쿠키");
    expect(body.category).toBe("50000006");
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ type: "researched", dropped: ["답례품쿠키"] })));
  });

  it("segment without audience needs manual age/gender", () => {
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키", segment: segs[2] }} dispatch={dispatch} />);
    const btn = screen.getByRole("button", { name: "이 손님들로 할게요" }) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    fireEvent.click(screen.getByRole("radio", { name: "30대" }));
    fireEvent.click(screen.getByRole("radio", { name: "여성" }));
    expect(btn.disabled).toBe(false);
    fireEvent.click(btn);
    expect(dispatch.mock.calls.at(-1)![0]).toMatchObject({ type: "confirmTarget", target: { ageMin: 30, ageMax: 39, gender: "female" }, segment: segs[2] });
  });

  it("month bars label peak month", () => {
    render(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키" }} dispatch={() => {}} />);
    const imgs = screen.getAllByRole("img", { name: /달별 검색 비중/ });
    expect(imgs.some((i) => (i.getAttribute("aria-label") ?? "").includes("12월 100%"))).toBe(true);
    expect(imgs[0]!.getAttribute("aria-label")).toMatch(/^달별 검색 비중: 1월 \d+%/);
  });

  it("old saved research without segments still renders", () => {
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research, product: "수제 쿠키" }} dispatch={dispatch} />);
    expect(screen.queryByRole("button", { name: "이 손님들로 할게요" })).toBeNull();
    expect(screen.queryByRole("radiogroup", { name: "광고를 보여 줄 손님" })).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "이 사람들로 할게요" }));
    expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ type: "confirmTarget", keywords: ["수제쿠키", "르뱅쿠키"] }));
  });

  it("no segments with a category goes to the manual pick", () => {
    render(<FindStep state={{ ...initialState(), research: { ...withSegs, segments: [] }, product: "수제 쿠키" }} dispatch={() => {}} />);
    expect(screen.getByText(/이 말로 찾는 손님 자료를 찾지 못했어요/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "직접 정하고 계속할게요" })).toBeTruthy();
  });

  it("retry after a failed re-search sends the chips toggled since, and keeps them dropped", async () => {
    const f = vi.fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValue(new Response(JSON.stringify(withSegs), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const dispatch = vi.fn();
    const base = { ...initialState(), research: withSegs, product: "수제 쿠키", category: "50000006" };
    const { rerender } = render(<FindStep state={{ ...base, dropped: ["답례품쿠키"] }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "이 말로 손님 다시 찾기" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "다시 시도" })).toBeTruthy());
    // 오류 뒤 남은 결과에서 칩 하나를 더 끈다
    fireEvent.click(screen.getByRole("button", { name: /르뱅쿠키/ }));
    expect(dispatch).toHaveBeenCalledWith({ type: "toggleKeyword", keyword: "르뱅쿠키" });
    rerender(<FindStep state={{ ...base, dropped: ["답례품쿠키", "르뱅쿠키"] }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "다시 시도" }));
    await waitFor(() => expect(f).toHaveBeenCalledTimes(2));
    const body = JSON.parse((f.mock.calls[1]![1] as RequestInit).body as string);
    expect(body.keywords).not.toContain("르뱅쿠키");
    expect(body.keywords).not.toContain("답례품쿠키");
    expect(body.keywords).toContain("수제쿠키");
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith(
      expect.objectContaining({ type: "researched", dropped: ["답례품쿠키", "르뱅쿠키"] })));
  });

  it("a failing category pick keeps the current category and picked segment, and offers retry", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키", category: "50000006", segment: segs[1] }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "바꾸기" }));
    fireEvent.click(screen.getByRole("radio", { name: "화장품/미용" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "다시 시도" })).toBeTruthy());
    expect(screen.getByText(/도우미 서버에 연결할 수 없어요/)).toBeTruthy();
    expect(dispatch.mock.calls.some(([e]) => e.type === "pickCategory" || e.type === "researched")).toBe(false);
    expect(screen.getByText(/'수제 쿠키'는 '식품'\(으\)로 볼게요/)).toBeTruthy();
    const picked = within(screen.getByRole("radiogroup", { name: "광고를 보여 줄 손님" })).getAllByRole("radio")[1] as HTMLInputElement;
    expect(picked.checked).toBe(true);
  });
});

describe("FindStep — 이 상품 검색 카드", () => {
  const stats = { keyword: "수제쿠키", total_qc: 9320, mobile: 0.526,
    audience: { female: 0.7, ages: { "20": 0.2, "30": 0.45, "40": 0.35 }, top_age: "30" } };

  it("shows the product's monthly searches, device split and who searches it", () => {
    render(<FindStep state={{ ...initialState(), research: { ...withSegs, product_stats: stats }, product: "수제 쿠키" }} dispatch={() => {}} />);
    expect(screen.getByText("'수제쿠키' 검색")).toBeTruthy();
    expect(screen.getByText("9,320회")).toBeTruthy();
    expect(screen.getByText("모바일 53% · PC 47%")).toBeTruthy();
    expect(screen.getByRole("img", { name: /30대 45%/ })).toBeTruthy();
  });

  it("without a category shows the count and asks for the category", () => {
    const r: Research = { ...withSegs, category: null, segments: [], product_stats: { ...stats, audience: null } };
    render(<FindStep state={{ ...initialState(), research: r, product: "수제 쿠키" }} dispatch={() => {}} />);
    expect(screen.getByText("9,320회")).toBeTruthy();
    expect(screen.getByText("분야를 고르면 누가 찾는지도 보여 드릴게요.")).toBeTruthy();
  });
});

describe("나이대마다 여성·남성 · 몇 월에 많이 찾나", () => {
  const stats = { keyword: "텀블러", total_qc: 128900, mobile: 0.7,
    audience: { female: 0.66, ages: { "20": 0.08, "30": 0.19, "40": 0.39, "50": 0.26 }, top_age: "40" },
    trend: { monthly: { "2026-01": 40, "2026-05": 100, "2026-09": 30 }, peak_month: 5, seasonal: true } };

  it("asks the split for the product word and draws the legend once it arrives", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ female_by_age: { "30": 0.64, "40": 0.67 } }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    render(<FindStep state={{ ...initialState(), research: { ...withSegs, product_stats: stats }, product: "텀블러" }} dispatch={() => {}} />);
    await waitFor(() => expect(screen.getAllByText("막대 안에서 아래가 여성, 위가 남성이에요").length).toBeGreaterThan(0));
    const call = f.mock.calls.find((c) => String(c[0]).endsWith("/audience/split"))!;
    expect(JSON.parse((call[1] as RequestInit).body as string)).toMatchObject({ keyword: "텀블러", category: "50000006" });
    expect(screen.getAllByRole("img", { name: /40대 39% \(여성 67%\)/ }).length).toBeGreaterThan(0);
  });

  it("shows the busiest month separately", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    render(<FindStep state={{ ...initialState(), research: { ...withSegs, product_stats: stats }, product: "텀블러" }} dispatch={() => {}} />);
    expect(screen.getByText("언제 많이 찾나요?")).toBeTruthy();
    expect(screen.getByText("5월에 가장 많이 찾아요")).toBeTruthy();
  });
});

describe("타깃 확인·고치기", () => {
  const state = () => ({ ...initialState(), research: withSegs, product: "수제 쿠키", segment: segs[1] });

  it("shows what goes into Ads Manager above the button", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    render(<FindStep state={state()} dispatch={() => {}} />);
    expect(screen.getByText(/30–49세 · 여성만 · 검색어 5개/)).toBeTruthy();
  });

  it("the owner can change ages and gender; the confirm sends the changed target", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    const dispatch = vi.fn();
    render(<FindStep state={state()} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "나이·성별 바꾸기" }));
    expect(screen.getByText(/남성 19%에게는 광고가 안 보여요/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText("나이 까지"), { target: { value: "30" } });
    fireEvent.click(screen.getByRole("radio", { name: /남녀 모두/ }));
    expect(screen.getByText(/30–39세 · 남녀 모두 · 검색어 5개/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "이 손님들로 할게요" }));
    expect(dispatch.mock.calls.at(-1)![0].target).toEqual({ ageMin: 30, ageMax: 39, gender: "all" });
    fireEvent.click(screen.getByRole("button", { name: "추천대로 되돌리기" }));
    expect(screen.getByText(/30–49세 · 여성만 · 검색어 5개/)).toBeTruthy();
  });

  it("the product card is one line, details folded", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    const stats = { keyword: "수제쿠키", total_qc: 129000, mobile: 0.5,
      audience: { female: 0.7, ages: { "30": 0.25, "40": 0.3, "50": 0.25 }, top_age: "40" },
      trend: { monthly: { "2026-12": 100 }, peak_month: 12, seasonal: true } };
    render(<FindStep state={{ ...state(), research: { ...withSegs, product_stats: stats } }} dispatch={() => {}} />);
    expect(screen.getByText("한 달 13만회 · 12월에 가장 많이 · 30~50대 여성이 많이 찾아요")).toBeTruthy();
    expect(screen.getByText("자세히 ▾")).toBeTruthy();
  });

  it("keyword chips sit below the customer groups, folded with a count", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    const { container } = render(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키", segment: segs[1] }} dispatch={() => {}} />);
    expect(screen.getByText("검색어 5개를 넣어요")).toBeTruthy();
    const order = [...container.querySelectorAll("[role=radiogroup], details")].map((e) => e.getAttribute("role") ?? "details");
    expect(order.indexOf("radiogroup")).toBeLessThan(order.lastIndexOf("details"));
  });

  it("the empty screen says what the search will show", () => {
    render(<FindStep state={initialState()} dispatch={() => {}} />);
    expect(screen.getByText("찾아보면 이렇게 알려 드려요")).toBeTruthy();
    expect(screen.getByText("· 누가 찾는지 (나이·성별)")).toBeTruthy();
  });
});

describe("무리 카드 한 줄 · 검색어 쓰임 · 가까운 분야", () => {
  it("each customer card says who searches without opening it", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    render(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키" }} dispatch={() => {}} />);
    const group = screen.getByRole("radiogroup", { name: "광고를 보여 줄 손님" });
    expect(within(group).getByText("30~40대 여성")).toBeTruthy();   // 30대 50% · 40대 30%, 여성 81%
  });

  it("says the keywords go into the copy, not into Meta targeting", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("{}", { status: 200 })));
    render(<FindStep state={{ ...initialState(), research: withSegs, product: "수제 쿠키", segment: segs[1] }} dispatch={() => {}} />);
    expect(screen.getByText(/이 말들은 ② 문구를 쓸 때 넣어요. 메타 광고는 검색어로 손님을 고르지 않아서/)).toBeTruthy();
  });

  it("changing the category shows the nearby ones first, the rest behind '다른 분야'", () => {
    const r = { ...withSegs, category_candidates: [{ code: "50000008", name: "생활/건강" }] };
    render(<FindStep state={{ ...initialState(), research: r, product: "수제 쿠키", category: "50000006" }} dispatch={() => {}} />);
    fireEvent.click(screen.getAllByRole("button", { name: "바꾸기" })[0]!);
    expect(screen.getByText("이 중 어디에 가까워요?")).toBeTruthy();
    expect(screen.getAllByRole("radio", { name: /식품|생활\/건강/ })).toHaveLength(2);
    fireEvent.click(screen.getByRole("button", { name: "다른 분야" }));
    expect(screen.getAllByRole("radio", { name: /./ }).length).toBeGreaterThanOrEqual(12);
  });
});

describe("무리 하나 · 다시 찾아볼 말 · 짧은 출처 · 최근 상품", () => {
  afterEach(() => { try { localStorage.clear(); } catch { /* */ } });

  it("explains why there is only one customer group", () => {
    render(<FindStep state={{ ...initialState(), research: { ...withSegs, segments: [segs[0]!] }, product: "수제 쿠키" }} dispatch={() => {}} />);
    expect(screen.getByText(/한 무리로 봤어요/)).toBeTruthy();
  });

  it("no data: offers other words and searches with one on click", async () => {
    const empty: Research = { headline: "", keywords: [], audience: null, fetched: "", source: "cache",
      notice: "추천할 만한 검색어를 찾지 못했어요.", suggestions: ["버터쿠키", "쿠키"] };
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify(withSegs), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const dispatch = vi.fn();
    render(<FindStep state={{ ...initialState(), research: empty, product: "수제 버터 쿠키" }} dispatch={dispatch} />);
    expect(screen.getByText("이 말로 다시 찾아볼까요?")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "버터쿠키" }));
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ type: "researched", product: "버터쿠키" })));
  });

  it("source line is short; details are folded", () => {
    const r = { ...withSegs, sources: [{ part: "product" as const, label: "검색어·연령", fetched: "2026-11-15", today: false }] };
    render(<FindStep state={{ ...initialState(), research: r, product: "수제 쿠키" }} dispatch={() => {}} />);
    expect(screen.getByText(/네이버 자료 · 11월 15일 기준/)).toBeTruthy();
    expect(screen.getByText(/출처: 네이버 검색광고·데이터랩 — 검색어·연령 11월 15일 저장본/)).toBeTruthy();   // 펼치면 보이는 자세한 줄
  });

  it("remembers recent products and searches again from a chip", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify(withSegs), { status: 200 }));
    vi.stubGlobal("fetch", f);
    localStorage.setItem("ad-coach.recent-products", JSON.stringify(["텀블러", "립밤"]));
    const dispatch = vi.fn();
    render(<FindStep state={initialState()} dispatch={dispatch} />);
    expect(screen.getByText("최근에 찾은 상품")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "립밤" }));
    await waitFor(() => expect(dispatch).toHaveBeenCalledWith(expect.objectContaining({ type: "researched", product: "립밤" })));
    expect(JSON.parse(localStorage.getItem("ad-coach.recent-products")!)[0]).toBe("립밤");
  });
});
