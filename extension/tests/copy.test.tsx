import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import CopyStep, { forgetCopyWork } from "../entrypoints/sidepanel/steps/CopyStep";
import { initialState } from "../lib/flow";

afterEach(() => vi.unstubAllGlobals());
beforeEach(() => forgetCopyWork());   // 문구 화면 기억은 테스트마다 비운다

const three = [1, 2, 3].map((i) => ({ primary_text: `본문 ${i}`, headline: `제목 ${i}` }));

describe("CopyStep", () => {
  it("asks for strengths, shows three copies, and picks one", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "template" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const dispatch = vi.fn();
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "수제 쿠키", keywords: ["수제쿠키"] }} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("상품의 좋은 점"), { target: { value: "버터 듬뿍" } });
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => expect(screen.getAllByRole("radio", { name: /안:/ })).toHaveLength(3));
    expect(JSON.parse(f.mock.calls[0]![1].body)).toEqual({ product: "수제 쿠키", strengths: ["버터 듬뿍"], keywords: ["수제쿠키"], avoid: [], tone: "친근하게" });
    expect(screen.queryByRole("button", { name: "이 문구로 할게요" })).toBeNull();   // 고르기 전엔 정하기 버튼 없음
    fireEvent.click(screen.getByRole("radio", { name: "2안: 제목 2" }));
    fireEvent.click(screen.getByRole("button", { name: "이 문구로 할게요" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "pickCopy", copy: three[1] });
  });

  it("passes the left-out words and can write again", async () => {
    const f = vi.fn().mockImplementation(async () => new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const research = { headline: "", keywords: [], audience: null, fetched: "", source: "live" as const, notice: null, negatives: ["쿠키만들기"] };
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "수제 쿠키", keywords: ["수제쿠키"], research }} dispatch={() => {}} />);
    fireEvent.change(screen.getByLabelText("상품의 좋은 점"), { target: { value: "버터 듬뿍" } });
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => expect(screen.getAllByRole("radio", { name: /안:/ })).toHaveLength(3));
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
    expect(screen.getByText("이 손님에게 쓰는 문구예요")).toBeTruthy();
    expect(screen.getByText(/선물로 찾는 손님/).textContent).toContain("12월에 많음");
    fireEvent.click(screen.getByRole("button", { name: "바꾸기" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "editFind" });
  });

  it("non-seasonal segment: no peak month shown or sent", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const flatSeg = { ...(seg as object), trend: { monthly: {}, peak_month: 3, seasonal: false } } as never;
    render(<CopyStep state={{ ...withMods(), segment: flatSeg }} dispatch={() => {}} />);
    expect(screen.getByText(/선물로 찾는 손님/).textContent).not.toContain("월에 많음");
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

  it("the picked copy can be edited; the preview follows and an edited copy drops its basis", async () => {
    const withBasis = three.map((c) => ({ ...c, basis: ["버터 듬뿍"] }));
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: withBasis, source: "claude" }), { status: 200 })));
    const dispatch = vi.fn();
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "수제 쿠키" }} dispatch={dispatch} />);
    fireEvent.change(screen.getByLabelText("상품의 좋은 점"), { target: { value: "버터 듬뿍" } });
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => screen.getByRole("radio", { name: "1안: 제목 1" }));
    fireEvent.click(screen.getByRole("radio", { name: "1안: 제목 1" }));
    fireEvent.change(screen.getByLabelText("제목 (고쳐도 돼요)"), { target: { value: "버터 듬뿍 쿠키" } });
    fireEvent.click(screen.getByRole("radio", { name: "페이스북 피드" }));   // 제목이 보이는 자리
    expect(screen.getByText("버터 듬뿍 쿠키")).toBeTruthy();   // 미리 보기
    expect(screen.getByText("8/40자")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "이 문구로 할게요" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "pickCopy", copy: { headline: "버터 듬뿍 쿠키", primary_text: "본문 1" } });
  });

  it("too long a headline blocks the pick", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 })));
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "쿠키" }} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => screen.getByRole("radio", { name: "1안: 제목 1" }));
    fireEvent.click(screen.getByRole("radio", { name: "1안: 제목 1" }));
    fireEvent.change(screen.getByLabelText("제목 (고쳐도 돼요)"), { target: { value: "가".repeat(41) } });
    expect(screen.getByRole("button", { name: "이 문구로 할게요" }).hasAttribute("disabled")).toBe(true);
    expect(screen.getByText("41/40자")).toBeTruthy();
  });

  it("the owner can write the copy themselves without asking, even with no chips picked", () => {
    const dispatch = vi.fn();
    render(<CopyStep state={withMods()} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "문구를 직접 쓸게요" }));
    fireEvent.change(screen.getByLabelText("제목 (고쳐도 돼요)"), { target: { value: "오늘 구운 쿠키" } });
    fireEvent.change(screen.getByLabelText("본문 (고쳐도 돼요)"), { target: { value: "매일 아침 구워 보내요." } });
    fireEvent.click(screen.getByRole("button", { name: "이 문구로 할게요" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "pickCopy", copy: { headline: "오늘 구운 쿠키", primary_text: "매일 아침 구워 보내요." } });
  });

  it("after getting three, '직접 쓰기' is a fourth choice", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 })));
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "쿠키" }} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => screen.getByRole("radio", { name: "직접 쓰기" }));
    fireEvent.click(screen.getByRole("radio", { name: "직접 쓰기" }));
    expect((screen.getByLabelText("제목 (고쳐도 돼요)") as HTMLInputElement).value).toBe("");
  });

  it("chip groups come from the server (any names), '그 밖' last", () => {
    const mixed = [{ word: "보온", group: "기능", total_qc: 9, examples: [] }, { word: "컴퓨터", group: "그 밖", total_qc: 8, examples: [] },
      { word: "스텐", group: "재질", total_qc: 7, examples: [] }];
    render(<CopyStep state={{ ...withMods(), research: { ...research, modifiers: mixed } }} dispatch={() => {}} />);
    const labels = screen.getAllByText(/^(기능|재질|그 밖)$/).map((e) => e.textContent);
    expect(labels).toEqual(["기능", "재질", "그 밖"]);
  });

  it("shows copy-shaped placeholders while writing", async () => {
    let done!: (r: Response) => void;
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise<Response>((r) => { done = r; })));
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "쿠키" }} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    expect(screen.getByRole("status").textContent).toContain("문구 3개를 쓰는 중이에요");
    done(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 }));
    await waitFor(() => expect(screen.queryByRole("status")).toBeNull());
  });

  it("writing again keeps the earlier copies (folded) and keeps the pick", async () => {
    const next = [4, 5, 6].map((i) => ({ primary_text: `본문 ${i}`, headline: `제목 ${i}` }));
    const f = vi.fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify({ copies: next, source: "claude" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    const dispatch = vi.fn();
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "쿠키" }} dispatch={dispatch} />);
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => screen.getByRole("radio", { name: "2안: 제목 2" }));
    fireEvent.click(screen.getByRole("radio", { name: "2안: 제목 2" }));
    fireEvent.click(screen.getByRole("button", { name: "다른 문구로 다시 써 주세요" }));
    await waitFor(() => screen.getByRole("radio", { name: "4안: 제목 4" }));
    expect(screen.getByText("새로 쓴 문구")).toBeTruthy();
    expect(screen.getByText("앞에서 쓴 문구 (1~3안)")).toBeTruthy();
    expect((screen.getByRole("radio", { name: "2안: 제목 2" }) as HTMLInputElement).checked).toBe(true);
    fireEvent.click(screen.getByRole("button", { name: "이 문구로 할게요" }));
    expect(dispatch).toHaveBeenCalledWith({ type: "pickCopy", copy: three[1] });
  });

  it("explains the number next to each chip", () => {
    render(<CopyStep state={withMods()} dispatch={() => {}} />);
    expect(screen.getByText(/칩 옆 숫자는 한 달에 그 말로 네이버에서 찾는 횟수예요/)).toBeTruthy();
  });
});

describe("② 문구 미리 보기·금지 표현", () => {
  const three = [1, 2, 3].map((i) => ({ primary_text: `본문 ${i}`, headline: `제목 ${i}` }));
  const start = async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 })));
    render(<CopyStep state={{ ...initialState(), step: "copy", product: "쿠키" }} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => screen.getByRole("radio", { name: "1안: 제목 1" }));
  };

  it("only the picked copy shows the full feed preview", async () => {
    await start();
    expect(screen.queryAllByText("사진 자리")).toHaveLength(0);
    fireEvent.click(screen.getByRole("radio", { name: "2안: 제목 2" }));
    expect(screen.getAllByText("사진 자리")).toHaveLength(1);
  });

  it("the owner's photo shows in the preview without uploading", async () => {
    const created = vi.fn(() => "blob:local-1");
    vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: created, revokeObjectURL: vi.fn() }));
    await start();
    fireEvent.click(screen.getByRole("radio", { name: "1안: 제목 1" }));
    const file = new File(["x"], "cookie.png", { type: "image/png" });
    fireEvent.change(screen.getByLabelText("내 상품 사진 넣어 보기"), { target: { files: [file] } });
    expect(created).toHaveBeenCalledWith(file);
    expect(document.querySelector('img[src="blob:local-1"]')).toBeTruthy();
    expect(screen.getByText("사진 바꾸기")).toBeTruthy();
  });

  it("banned words are flagged while editing and block the pick", async () => {
    await start();
    fireEvent.click(screen.getByRole("radio", { name: "1안: 제목 1" }));
    fireEvent.change(screen.getByLabelText("본문 (고쳐도 돼요)"), { target: { value: "동네 최저가 100% 수제" } });
    expect(screen.getByRole("alert").textContent).toContain("'최저가', '100%' 같은 말은 근거를 댈 수 없는 말이라");
    expect(screen.getByRole("button", { name: "이 문구로 할게요" }).hasAttribute("disabled")).toBe(true);
  });
});

describe("② 문구 칩 수·직접 적기·말투·손님 카드·다음 안내", () => {
  const mods = [
    { word: "개별포장", group: "포장", total_qc: 12000, examples: [] }, { word: "버터", group: "맛", total_qc: 800, examples: [] },
    { word: "초코", group: "맛", total_qc: 700, examples: [] }, { word: "대용량", group: "양", total_qc: 600, examples: [] },
  ];
  const research = { headline: "", keywords: [], audience: null, fetched: "", source: "live" as const, notice: null, negatives: [], modifiers: mods };
  const base = () => ({ ...initialState(), step: "copy" as const, product: "수제 쿠키", research,
    target: { ageMin: 30, ageMax: 49, gender: "female" as const } });

  it("counts picked chips and warns gently over three", () => {
    render(<CopyStep state={base()} dispatch={() => {}} />);
    for (const w of ["개별포장", "버터", "초코", "대용량"]) fireEvent.click(screen.getByRole("button", { name: new RegExp(w) }));
    expect(screen.getByText(/좋은 점 4개 골랐어요 · 많이 고르면 문구가 길고 흐려질 수 있어요/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "문구 써 주세요" }).hasAttribute("disabled")).toBe(false);   // 막지는 않음
  });

  it("typed words become chips on Enter and can be removed", () => {
    render(<CopyStep state={base()} dispatch={() => {}} />);
    const box = screen.getByLabelText("직접 적기");
    fireEvent.change(box, { target: { value: "당일 구움" } });
    fireEvent.keyDown(box, { key: "Enter" });
    expect((box as HTMLInputElement).value).toBe("");
    expect(screen.getByRole("list", { name: "직접 적은 말" }).textContent).toContain("당일 구움");
    fireEvent.click(screen.getByRole("button", { name: "당일 구움 빼기" }));
    expect(screen.queryByRole("list", { name: "직접 적은 말" })).toBeNull();
  });

  it("sends the picked tone", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: [], source: "claude" }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    render(<CopyStep state={base()} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: /개별포장/ }));
    fireEvent.click(screen.getByRole("radio", { name: "감성적으로" }));
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => expect(f).toHaveBeenCalled());
    expect(JSON.parse(f.mock.calls[0]![1].body).tone).toBe("감성적으로");
  });

  it("shows the target from ① and what comes next", () => {
    render(<CopyStep state={base()} dispatch={() => {}} />);
    expect(screen.getByText("30–49세 · 여성만")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "문구를 직접 쓸게요" }));
    expect(screen.getByText(/다음: 광고 설정 질문 몇 개에 답하면/)).toBeTruthy();
  });
});

describe("② 문구 기억 · 자리별 미리 보기 · 틀 문장 알림", () => {
  const three = [1, 2, 3].map((i) => ({ primary_text: `본문 ${i}`, headline: `제목 ${i}` }));
  const st = () => ({ ...initialState(), step: "copy" as const, product: "쿠키" });

  it("leaving and coming back keeps the copies, the pick and the edit", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 })));
    const first = render(<CopyStep state={st()} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => screen.getByRole("radio", { name: "2안: 제목 2" }));
    fireEvent.click(screen.getByRole("radio", { name: "2안: 제목 2" }));
    fireEvent.change(screen.getByLabelText("제목 (고쳐도 돼요)"), { target: { value: "고친 제목" } });
    first.unmount();   // ① 찾기로 갔다가
    render(<CopyStep state={st()} dispatch={() => {}} />);   // 돌아옴
    expect((screen.getByRole("radio", { name: "2안: 제목 2" }) as HTMLInputElement).checked).toBe(true);
    expect((screen.getByLabelText("제목 (고쳐도 돼요)") as HTMLInputElement).value).toBe("고친 제목");
  });

  it("a different customer group starts fresh", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 })));
    const first = render(<CopyStep state={st()} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => screen.getByRole("radio", { name: "1안: 제목 1" }));
    first.unmount();
    const seg = { intent: "선물·답례", label: "선물로 찾는 손님", keywords: [], total_qc: 1, lead: "", audience: null, trend: null, trend_source: null, line: "" } as never;
    render(<CopyStep state={{ ...st(), segment: seg }} dispatch={() => {}} />);
    expect(screen.queryByRole("radio", { name: "1안: 제목 1" })).toBeNull();
  });

  it("switches the preview between instagram feed, facebook feed and story", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "claude" }), { status: 200 })));
    render(<CopyStep state={st()} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => screen.getByRole("radio", { name: "1안: 제목 1" }));
    fireEvent.click(screen.getByRole("radio", { name: "1안: 제목 1" }));
    expect((screen.getByRole("radio", { name: "인스타 피드" }) as HTMLInputElement).checked).toBe(true);
    expect(screen.getByText(/인스타 피드에서는 제목이 거의 안 보여요/)).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "스토리" }));
    expect(screen.getByText(/스토리에서는 제목이 안 보이고/)).toBeTruthy();
    fireEvent.click(screen.getByRole("radio", { name: "페이스북 피드" }));
    expect(screen.queryByText(/제목이 거의 안 보여요|제목이 안 보이고/)).toBeNull();
  });

  it("says when the copies came from the fallback template", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ copies: three, source: "template" }), { status: 200 })));
    render(<CopyStep state={st()} dispatch={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "문구 써 주세요" }));
    await waitFor(() => expect(screen.getByText(/기본 문장 틀로 썼어요/)).toBeTruthy());
  });
});
