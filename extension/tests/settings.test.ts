import { describe, expect, it } from "vitest";
import { ageGroupToRange } from "../lib/settings";

describe("ageGroupToRange", () => {
  it("30 is 30–39", () => expect(ageGroupToRange("30")).toEqual({ ageMin: 30, ageMax: 39 }));
  it("60 is 60–65 (메타 최대 65)", () => expect(ageGroupToRange("60")).toEqual({ ageMin: 60, ageMax: 65 }));
  it("10 starts at 18 (메타 최소 18)", () => expect(ageGroupToRange("10")).toEqual({ ageMin: 18, ageMax: 19 }));
});
