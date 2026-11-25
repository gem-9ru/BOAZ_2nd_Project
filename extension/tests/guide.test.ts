import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import raw from "../guide/meta_traffic.json";
import { stepsFor, validateGuide, type GuideEntry } from "../lib/guide";
import { SETTING_ORDER } from "../lib/settings";

const entries = raw as GuideEntry[];
const settings = SETTING_ORDER.map((id) => ({ fieldId: id, label: id, value: `값-${id}` }));

describe("guide list", () => {
  it("passes validation", () => expect(validateGuide(entries, SETTING_ORDER)).toEqual([]));

  it("create entries follow the setting order, then the publish entry last", () => {
    const create = entries.filter((e) => e.mode === "create");
    expect(create.slice(0, -1).map((e) => e.id)).toEqual(SETTING_ORDER);
    const last = create[create.length - 1]!;
    expect(last.publish).toBe(true);
    expect(last.done).toBe("manual");
  });

  it("every fallback image exists in public/", () => {
    for (const e of entries) expect(existsSync(resolve(__dirname, "../public", e.fallback.image)), e.id).toBe(true);
  });

  it("flags class selectors, empty text and unknown create ids", () => {
    const bad: GuideEntry = { ...entries[0]!, id: "meta.unknown", find: [{ aria: ".x1abc" }, { labelText: "" }] };
    const problems = validateGuide([bad], SETTING_ORDER);
    expect(problems.some((p) => p.includes("클래스"))).toBe(true);
    expect(problems.some((p) => p.includes("비어"))).toBe(true);
    expect(problems.some((p) => p.includes("meta.unknown"))).toBe(true);
  });
});

describe("stepsFor", () => {
  it("create carries each setting's value, publish has none", () => {
    const steps = stepsFor("create", entries, settings, []);
    expect(steps).toHaveLength(14);
    expect(steps[0]!.value).toBe("값-meta.campaign.objective");
    expect(steps[13]!.value).toBeUndefined();
  });

  it("edit returns only entries for the changed fields, with the new value", () => {
    const steps = stepsFor("edit", entries, [], [{ field_id: "meta.adset.placements", label: "노출 위치", new: "Audience Network 제외", note: "" }]);
    expect(steps.map((s) => s.entry.id)).toEqual(["meta.adset.placements"]);
    expect(steps[0]!.value).toBe("Audience Network 제외");
  });

  it("export returns the three export entries", () => {
    expect(stepsFor("export", entries, [], []).map((s) => s.entry.mode)).toEqual(["export", "export", "export"]);
  });
});

describe("every field the analysis can ask to change has an edit guide", () => {
  it("covers all field ids in server/specs/rules.yaml plus the ones next_step uses", async () => {
    const { readFileSync } = await import("node:fs");
    const rules = readFileSync(resolve(__dirname, "../../server/specs/rules.yaml"), "utf8");
    const ids = new Set([...rules.matchAll(/meta\.(?:adset|ad|creative|campaign)\.[a-z_.]+/g)].map((m) => m[0]));
    ids.add("meta.adset.end_date"); ids.add("meta.creative.copy");
    const edit = new Set(entries.filter((e) => e.mode === "edit").map((e) => e.id));
    expect([...ids].filter((id) => !edit.has(id))).toEqual([]);
  });
});
