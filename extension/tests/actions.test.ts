// 사장님 대신 맞추는 복잡한 칸 (2026-11-25 실제 메타 화면에서 확인한 구조를 흉내 냄)
import { beforeEach, describe, expect, it } from "vitest";
import { parseAgeGender, setAgeGender, setEndDate, checkLocation } from "../entrypoints/adsmanager.content/actions";

const fast = { wait: () => Promise.resolve() };

beforeEach(() => { document.body.innerHTML = ""; });

describe("종료 날짜", () => {
  it("turns on '종료 날짜 설정' and types the date into the date box right after it (not the start date)", async () => {
    document.body.innerHTML = `
      <input placeholder="yyyy-mm-dd" id="start" value="2026년 11월 25일">
      <span id="l">종료 날짜 설정</span><input type="checkbox" id="cb" aria-labelledby="l">
      <input placeholder="yyyy-mm-dd" id="end" value="">`;
    expect(await setEndDate(document, "2026-12-09", fast)).toBe(true);
    expect((document.getElementById("cb") as HTMLInputElement).checked).toBe(true);
    expect((document.getElementById("end") as HTMLInputElement).value).toBe("2026-12-09");
    expect((document.getElementById("start") as HTMLInputElement).value).toBe("2026년 11월 25일");
  });
});

describe("연령·성별", () => {
  it("reads '30–39세 · 여성'", () => {
    expect(parseAgeGender("30–39세 · 여성")).toEqual({ min: "30", max: "39", gender: "여성" });
    expect(parseAgeGender("60–65세 · 전체")).toEqual({ min: "60", max: "65+", gender: "전체" });
  });

  it("opens the age box, picks min/max from the lists, and the gender radio", async () => {
    const combo = (label: string, now: string) => {
      const id = label === "최소 연령" ? "amin" : "amax";
      return `<span id="${id}">${label}</span><div role="combobox" aria-labelledby="${id}" data-name="${label}">${now}</div>`;
    };
    document.body.innerHTML = `<div role="button" id="age">연령18 - 65+</div>
      <span id="g1">전체</span><input type="radio" name="g" aria-labelledby="g1" checked>
      <span id="g3">여성</span><input type="radio" name="g" id="f" aria-labelledby="g3">`;
    document.getElementById("age")!.addEventListener("click", () => {
      document.body.insertAdjacentHTML("beforeend", combo("최소 연령", "18") + combo("최대 연령", "65+"));
      for (const c of Array.from(document.querySelectorAll<HTMLElement>("[role=combobox]"))) {
        c.addEventListener("click", () => {
          document.querySelectorAll("[role=listbox]").forEach((x) => x.remove());
          const list = Array.from({ length: 48 }, (_, i) => String(18 + i)).concat("65+");
          document.body.insertAdjacentHTML("beforeend", `<div role="listbox">${list.map((v) => `<div role="option">${v}</div>`).join("")}</div>`);
          document.querySelectorAll<HTMLElement>("[role=option]").forEach((o) => o.addEventListener("click", () => { c.textContent = o.textContent; document.querySelector("[role=listbox]")?.remove(); }));
        });
      }
    }, { once: true });
    expect(await setAgeGender(document, "30–39세 · 여성", fast)).toBe(true);
    const name = (n: string) => document.querySelector(`[data-name="${n}"]`)!.textContent;
    expect([name("최소 연령"), name("최대 연령")]).toEqual(["30", "39"]);
    expect((document.getElementById("f") as HTMLInputElement).checked).toBe(true);
  });
});

describe("연령·성별: 실제로 바뀌었는지 확인", () => {
  it("returns false when the page ignores the option click (values stay 18 / 65+), so the guide does not move on", async () => {
    document.body.innerHTML = `<span id="amin">최소 연령</span><div role="combobox" aria-labelledby="amin" id="min">18</div>
      <span id="amax">최대 연령</span><div role="combobox" aria-labelledby="amax" id="max">65+</div>
      <span id="g3">여성</span><input type="radio" name="g" aria-labelledby="g3">`;
    for (const c of Array.from(document.querySelectorAll<HTMLElement>("[role=combobox]"))) {
      c.addEventListener("click", () => {
        document.querySelectorAll("[role=listbox]").forEach((x) => x.remove());
        document.body.insertAdjacentHTML("beforeend", `<div role="listbox">${["18", "30", "39", "65+"].map((v) => `<div role="option">${v}</div>`).join("")}</div>`);
      });
    }
    expect(await setAgeGender(document, "30–39세 · 여성", fast)).toBe(false);
  });
});

describe("위치", () => {
  it("전국 + already 대한민국 → nothing to do; a neighborhood needs the owner", () => {
    document.body.innerHTML = `<div role="button" id="loc">위치포함된 위치:대한민국</div>`;
    expect(checkLocation(document, "전국 (택배)")).toBe(true);
    expect(checkLocation(document, "가게 반경 3km")).toBe(false);
  });
});
