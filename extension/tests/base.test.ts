import { describe, expect, it } from "vitest";
import { apiBase } from "../lib/api";

describe("server address", () => {
  it("defaults to the local server and takes the deployed one from the build setting", () => {
    expect(apiBase(undefined)).toBe("http://localhost:8000");
    expect(apiBase("https://boaz-ad-assistant.gem-9ru.com/")).toBe("https://boaz-ad-assistant.gem-9ru.com");
  });
});
