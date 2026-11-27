// 감사 20 (2026-11-26): 확률을 100%로 단정하지 않는다
import { describe, expect, it } from "vitest";
import { probText } from "../src/ui";

describe("나을 확률 글자", () => {
  it("99.5%를 넘으면 '99% 넘게', 그 아래는 그대로", () => {
    expect(probText(0.999)).toBe("99% 넘게");
    expect(probText(0.9)).toBe("90%");
  });
});
