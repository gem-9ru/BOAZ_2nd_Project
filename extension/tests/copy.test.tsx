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
});

