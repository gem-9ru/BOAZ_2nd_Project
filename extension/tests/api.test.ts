import { afterEach, describe, expect, it, vi } from "vitest";
import { BadInput, ServerDown, ServerError, research } from "../lib/api";

afterEach(() => vi.unstubAllGlobals());

describe("api", () => {
  it("throws ServerDown when fetch rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(research("수제 쿠키")).rejects.toBeInstanceOf(ServerDown);
  });

  it("throws BadInput with the server message on 400", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ error: "열이 없어요" }), { status: 400 })));
    await expect(research("x")).rejects.toThrow("열이 없어요");
    await expect(research("x")).rejects.toBeInstanceOf(BadInput);
  });

  it("shows the server's own words when busy (429, 503)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => new Response(JSON.stringify({ error: "1분 뒤에 다시 해 주세요." }), { status: 429 })));
    await expect(research("x")).rejects.toThrow("1분 뒤에");
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => new Response(JSON.stringify({ detail: "잠시 뒤에 다시" }), { status: 503 })));
    await expect(research("x")).rejects.toThrow("잠시 뒤에");
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async () => new Response("oops", { status: 500 })));
    await expect(research("x")).rejects.toBeInstanceOf(ServerError);
  });

  it("posts product and seeds to /research", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ keywords: [] }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    await research("수제 쿠키", { seeds: ["수제쿠키"] });
    expect(f.mock.calls[0]![0]).toBe("http://localhost:8000/research");
    expect(JSON.parse(f.mock.calls[0]![1].body)).toEqual({ product: "수제 쿠키", seeds: ["수제쿠키"] });
  });

  it("research body omits undefined keys", async () => {
    const f = vi.fn().mockResolvedValue(new Response(JSON.stringify({ keywords: [] }), { status: 200 }));
    vi.stubGlobal("fetch", f);
    await research("립밤", { category: "50000002", keywords: ["립밤"] });
    expect(f.mock.calls[0]![1].body).toBe('{"product":"립밤","category":"50000002","keywords":["립밤"]}');
  });
});
