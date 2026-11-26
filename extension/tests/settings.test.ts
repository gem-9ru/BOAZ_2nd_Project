import { describe, expect, it } from "vitest";
import { ageGroupToRange } from "../lib/settings";

describe("ageGroupToRange", () => {
  it("30 is 30–39", () => expect(ageGroupToRange("30")).toEqual({ ageMin: 30, ageMax: 39 }));
  it("60 is 60–65 (메타 최대 65)", () => expect(ageGroupToRange("60")).toEqual({ ageMin: 60, ageMax: 65 }));
  it("10 starts at 18 (메타 최소 18)", () => expect(ageGroupToRange("10")).toEqual({ ageMin: 18, ageMax: 19 }));
});

describe("ageSpan: 많이 찾는 옆 나이대까지 넣기", () => {
  it("30대 23% · 40대 29% · 50대 25% → 30~50대 (30–59세)", async () => {
    const { ageSpan, ageSpanLabel } = await import("../lib/settings");
    const s = ageSpan({ "10": 0.01, "20": 0.11, "30": 0.23, "40": 0.29, "50": 0.25, "60": 0.11 });
    expect(s).toEqual({ groups: ["30", "40", "50"], ageMin: 30, ageMax: 59 });
    expect(ageSpanLabel(s.groups)).toBe("30~50대");
  });

  it("stays one group when neighbors are small, and never goes below 18 or above 65", async () => {
    const { ageSpan } = await import("../lib/settings");
    expect(ageSpan({ "20": 0.1, "30": 0.6, "40": 0.14, "50": 0.16 })).toEqual({ groups: ["30"], ageMin: 30, ageMax: 39 });
    expect(ageSpan({ "10": 0.3, "20": 0.4, "30": 0.1 })).toMatchObject({ groups: ["10", "20"], ageMin: 18 });
    expect(ageSpan({ "50": 0.35, "60": 0.4 })).toMatchObject({ groups: ["50", "60"], ageMax: 65 });
  });

  it("a neighbor under half of the top group is left out even if over 15%", async () => {
    const { ageSpan } = await import("../lib/settings");
    expect(ageSpan({ "30": 0.17, "40": 0.5, "50": 0.2 }).groups).toEqual(["40"]);
  });
});
