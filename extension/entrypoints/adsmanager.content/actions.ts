// 사장님 대신 맞추는 복잡한 칸 (종료 날짜 · 연령·성별 · 위치).
// 2026-11-25 실제 메타 광고 세트 화면에서 확인한 구조: 날짜는 yyyy-mm-dd 글자 칸, 연령은 '최소/최대 연령' 목록(일부만 그림),
// 성별은 '전체/남성/여성' 라디오, 위치는 기본 '대한민국'. 게시와 관련된 것은 건드리지 않는다.
import { typeInto } from "./locate";

export interface Pace { wait: (ms: number) => Promise<void> }

/** 콘솔에 남기는 진단 줄 (광고 관리자 탭의 개발자 도구에서 '[ad-coach]'로 찾는다). 값·키는 넣지 않는다. */
function note(...parts: unknown[]): void {
  if (typeof console !== "undefined" && !(globalThis as { __AD_COACH_QUIET__?: boolean }).__AD_COACH_QUIET__) console.debug("[ad-coach]", ...parts);
}
const real: Pace = { wait: (ms) => new Promise((r) => setTimeout(r, ms)) };

function text(e: Element | null): string {
  return (e?.textContent ?? "").replace(/[​‌‍﻿]/g, "").replace(/\s+/g, " ").trim();
}

/** aria-labelledby가 가리키는 이름표 글자가 name인 요소 (selector에 맞는 것 중 화면에 그려진 것 먼저). */
function byLabel(doc: Document, selector: string, name: string): HTMLElement | null {
  const list = Array.from(doc.querySelectorAll<HTMLElement>(selector)).filter((e) =>
    (e.getAttribute("aria-labelledby") ?? "").split(/\s+/).some((id) => text(doc.getElementById(id)) === name));
  return list.find((e) => e.getClientRects().length > 0) ?? list[0] ?? null;
}

function button(doc: Document, test: (t: string) => boolean): HTMLElement | null {
  const list = Array.from(doc.querySelectorAll<HTMLElement>("[role=button], button, a")).filter((e) => test(text(e)));
  return list.find((e) => e.getClientRects().length > 0) ?? list[0] ?? null;
}

/** 종료 날짜: '종료 날짜 설정'을 켜고, 그 스위치 바로 뒤에 오는 날짜 칸(시작 날짜 아님)에 yyyy-mm-dd로 넣는다. */
export async function setEndDate(doc: Document, value: string, pace: Pace = real): Promise<boolean> {
  const date = value.match(/\d{4}-\d{2}-\d{2}/)?.[0];
  const sw = byLabel(doc, "input, [role=checkbox], [role=switch]", "종료 날짜 설정");
  if (!date || !sw) return false;
  const on = sw instanceof HTMLInputElement ? sw.checked : sw.getAttribute("aria-checked") === "true";
  if (!on) { sw.click(); await pace.wait(800); }
  const box = Array.from(doc.querySelectorAll<HTMLInputElement>("input[placeholder='yyyy-mm-dd']"))
    .find((i) => sw.compareDocumentPosition(i) & Node.DOCUMENT_POSITION_FOLLOWING);
  if (!box) return false;
  box.focus();
  typeInto(box, date);
  box.blur();
  await pace.wait(600);
  return true;
}

/** '30–39세 · 여성' → 메타 목록 값. 65 이상은 '65+'. 성별 '전체'는 메타의 '전체'. */
export function parseAgeGender(value: string): { min: string; max: string; gender: "전체" | "남성" | "여성" } | null {
  const m = value.match(/(\d{2})\s*[–-]\s*(\d{2})/);
  if (!m) return null;
  const max = Number(m[2]) >= 65 ? "65+" : m[2]!;
  const gender = /여성/.test(value) ? "여성" : /남성/.test(value) ? "남성" : "전체";
  return { min: m[1]!, max, gender };
}

/** 목록(combobox)을 열고 선택지를 찾아 누른다. 메타는 선택지를 일부만 그리므로 목록을 내리며 찾는다. */
async function pickOption(doc: Document, name: string, want: string, pace: Pace): Promise<boolean> {
  const box = byLabel(doc, "[role=combobox]", name);
  if (!box) return false;
  if (text(box) === want) return true;
  box.click();
  await pace.wait(700);
  const find = () => Array.from(doc.querySelectorAll<HTMLElement>("[role=option]")).find((o) => text(o) === want);
  let hit = find();
  const first = doc.querySelector<HTMLElement>("[role=option]");
  let sc: HTMLElement | null = first?.parentElement ?? null;
  while (sc && !(sc.scrollHeight > sc.clientHeight + 5)) sc = sc.parentElement;
  for (let y = 0; !hit && sc && y <= sc.scrollHeight; y += 60) {
    sc.scrollTop = y;
    await pace.wait(120);
    hit = find();
  }
  if (!hit) { box.click(); note("age option not found", name, want); return false; }   // 못 찾으면 목록을 닫고 사장님께
  hit.click();
  await pace.wait(500);
  // 메타가 다시 그렸을 수 있으니 칸을 새로 찾아, 정말 그 값이 됐는지 본다
  const now = text(byLabel(doc, "[role=combobox]", name));
  if (now !== want) { note("age pick did not stick", name, want, now); return false; }
  return true;
}

/** 연령·성별: 연령 칸을 열어(필요하면 '설정 표시') 최소·최대 연령을 고르고 성별 라디오를 고른다. */
export async function setAgeGender(doc: Document, value: string, pace: Pace = real): Promise<boolean> {
  const want = parseAgeGender(value);
  if (!want) return false;
  if (!byLabel(doc, "[role=combobox]", "최소 연령")) {
    const show = button(doc, (t) => t === "설정 표시");
    if (show) { show.click(); await pace.wait(1000); }
    const age = button(doc, (t) => /^연령\d/.test(t));
    if (age) { age.click(); await pace.wait(1000); }
    note("age opened", { show: Boolean(show), age: Boolean(age), boxes: Boolean(byLabel(doc, "[role=combobox]", "최소 연령")) });
  }
  if (!(await pickOption(doc, "최소 연령", want.min, pace))) return false;
  if (!(await pickOption(doc, "최대 연령", want.max, pace))) return false;
  let radio = byLabel(doc, "input[type=radio], [role=radio]", want.gender);
  if (!radio) {
    const g = button(doc, (t) => /^성별/.test(t));
    if (g) { g.click(); await pace.wait(800); }
    radio = byLabel(doc, "input[type=radio], [role=radio]", want.gender);
  }
  if (!radio) { note("gender radio not found", want.gender); return false; }
  const on = radio instanceof HTMLInputElement ? radio.checked : radio.getAttribute("aria-checked") === "true";
  if (!on) radio.click();
  await pace.wait(400);
  const checked = radio instanceof HTMLInputElement ? radio.checked : radio.getAttribute("aria-checked") === "true";
  if (!checked) { note("gender radio did not stick", want.gender); return false; }
  note("age/gender set", want.min, want.max, want.gender);
  return true;
}

/** 위치: '전국'이면 메타 기본값 '대한민국'이 이미 맞다 → 할 일 없음(true). 동네·반경은 지도에서 직접 골라야 해서 false. */
export function checkLocation(doc: Document, value: string): boolean {
  if (!/전국/.test(value)) return false;
  return /대한민국/.test(text(button(doc, (t) => t.startsWith("위치"))));
}
