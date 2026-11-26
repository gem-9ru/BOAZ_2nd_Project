// 사장님 대신 맞추는 복잡한 칸 (시작·종료 날짜 · 연령·성별 · 위치).
// 2026-11-25 실제 메타 광고 세트 화면에서 확인한 구조: 날짜는 yyyy-mm-dd 글자 칸, 연령은 '최소/최대 연령' 목록(일부만 그림),
// 성별은 '전체/남성/여성' 라디오, 위치는 기본 '대한민국'. 게시와 관련된 것은 건드리지 않는다.
import { isoDate } from "../../lib/settings";
import { byRoleText, firstShown, isChecked, textOf, typeInto } from "./locate";

export interface Pace { wait: (ms: number) => Promise<void> }

/** 콘솔에 남기는 진단 줄 (광고 관리자 탭의 개발자 도구에서 '[ad-coach]'로 찾는다). 값·키는 넣지 않는다. */
function note(...parts: unknown[]): void {
  if (typeof console !== "undefined" && !(globalThis as { __AD_COACH_QUIET__?: boolean }).__AD_COACH_QUIET__) console.debug("[ad-coach]", ...parts);
}
const real: Pace = { wait: (ms) => new Promise((r) => setTimeout(r, ms)) };

/** aria-labelledby가 가리키는 이름표 글자가 name인 요소 (selector에 맞는 것 중 화면에 그려진 것 먼저). */
function byLabelledName(doc: Document, selector: string, name: string): HTMLElement | null {
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>(selector)).filter((e) =>
    (e.getAttribute("aria-labelledby") ?? "").split(/\s+/).some((id) => textOf(doc.getElementById(id)) === name)));
}

/** 날짜 칸 뒤의 '시간'(0~23)·'분'(0~59) 스핀 버튼에 HH:MM을 넣고, 정말 그 값이 됐는지 본다 (2026-11-26 실제 화면: aria-label 시간·분, 24시간제).
 *  실제 메타는 값 넣기·가짜 키 이벤트를 무시해서 대개 false가 나온다 → 사장님이 시각만 맞추면 된다. 이미 같은 값이면 true.
 *  다음 날짜 칸이 나오기 전까지만 찾는다 (시작 칸의 시각과 종료 칸의 시각을 섞지 않게). */
async function setTimeAfter(doc: Document, dateBox: HTMLElement, time: string, pace: Pace): Promise<boolean> {
  const [h, m] = time.split(":");
  const all = Array.from(doc.querySelectorAll<HTMLElement>("input[placeholder='yyyy-mm-dd'], [role=spinbutton]"));
  const after = all.slice(all.indexOf(dateBox) + 1);
  const stop = after.findIndex((e) => e.getAttribute("placeholder") === "yyyy-mm-dd");
  const spins = stop < 0 ? after : after.slice(0, stop);
  const hour = spins.find((e) => e.getAttribute("aria-label") === "시간");
  const min = spins.find((e) => e.getAttribute("aria-label") === "분");
  if (!hour || !min) { note("time boxes not found"); return false; }
  for (const [el, want] of [[hour, h!], [min, m!]] as const) {
    if (Number(el.getAttribute("aria-valuenow")) === Number(want)) continue;
    el.focus();
    typeInto(el, want);
    el.blur();
    await pace.wait(300);
    const now = Number(el.getAttribute("aria-valuenow") ?? (el as HTMLInputElement).value);
    if (now !== Number(want)) { note("time did not stick", el.getAttribute("aria-label")); return false; }
  }
  return true;
}

/** 시작 날짜: 오늘(또는 지난 날·빈 값)이면 메타 기본값(오늘)이 맞다 → 손대지 않음.
 *  뒤 날짜면 '종료 날짜 설정' 스위치 앞의 마지막 날짜 칸(스위치가 없으면 첫 날짜 칸)에 yyyy-mm-dd로 넣고, 정말 바뀌었는지 본다.
 *  2026-11-26 새 세트(임시 저장)에서 확인: 날짜 칸이 화면에 보일 때 yyyy-mm-dd를 넣으면 '2026년 12월 3일'로 받아 준다 (안 보이면 무시됨 → 먼저 스크롤).
 *  시각 칸(시간·분 스핀 버튼)은 진짜 키 입력만 받아서 대신 넣지 못한다 → 날짜까지 넣고 시각은 사장님께 (false). */
export async function setStartDate(doc: Document, value: string, pace: Pace = real, today: Date = new Date()): Promise<boolean> {
  const date = value.match(/\d{4}-\d{2}-\d{2}/)?.[0];
  const time = value.match(/\b\d{2}:\d{2}\b/)?.[0];
  const now = isoDate(today);
  if (!date || (date <= now && !time)) return true;   // 오늘 바로 시작 → 메타 기본값 그대로
  const boxes = Array.from(doc.querySelectorAll<HTMLInputElement>("input[placeholder='yyyy-mm-dd']"));
  const sw = byLabelledName(doc, "input, [role=checkbox], [role=switch]", "종료 날짜 설정");
  const before = sw ? boxes.filter((i) => sw.compareDocumentPosition(i) & Node.DOCUMENT_POSITION_PRECEDING) : boxes.slice(0, 1);
  const box = before[before.length - 1];
  if (!box) { note("start date box not found"); return false; }
  // 이미 시작한 세트는 메타가 시작 날짜 칸을 잠근다 (2026-11-26 실제 화면 확인) → 사장님께
  if (box.disabled) { note("start date box is locked"); return false; }
  if (date > now) {
    box.scrollIntoView?.({ block: "center" });
    await pace.wait(300);
    box.focus();
    typeInto(box, date);
    box.blur();
    await pace.wait(600);
    const [y, m, d] = date.split("-").map(Number);
    const got = box.value;
    const stuck = got.includes(date) || (got.includes(String(y)) && new RegExp(`\\b0?${m}\\D+0?${d}\\b`).test(got));
    if (!stuck) { note("start date did not stick"); return false; }
  }
  return time ? setTimeAfter(doc, box, time, pace) : true;
}

/** 종료 날짜: '종료 날짜 설정'을 켜고, 그 스위치 바로 뒤에 오는 날짜 칸(시작 날짜 아님)에 yyyy-mm-dd로 넣는다. */
export async function setEndDate(doc: Document, value: string, pace: Pace = real): Promise<boolean> {
  const date = value.match(/\d{4}-\d{2}-\d{2}/)?.[0];
  const sw = byLabelledName(doc, "input, [role=checkbox], [role=switch]", "종료 날짜 설정");
  if (!date || !sw) return false;
  const on = isChecked(sw);
  if (!on) { sw.click(); await pace.wait(800); }
  const box = Array.from(doc.querySelectorAll<HTMLInputElement>("input[placeholder='yyyy-mm-dd']"))
    .find((i) => sw.compareDocumentPosition(i) & Node.DOCUMENT_POSITION_FOLLOWING);
  if (!box) return false;
  box.scrollIntoView?.({ block: "center" });   // 화면에 안 보이는 날짜 칸은 메타가 입력을 무시한다
  await pace.wait(300);
  box.focus();
  typeInto(box, date);
  box.blur();
  await pace.wait(600);
  const time = value.match(/\b\d{2}:\d{2}\b/)?.[0];
  return time ? setTimeAfter(doc, box, time, pace) : true;
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
  const box = byLabelledName(doc, "[role=combobox]", name);
  if (!box) return false;
  if (textOf(box) === want) return true;
  box.click();
  await pace.wait(700);
  const find = () => Array.from(doc.querySelectorAll<HTMLElement>("[role=option]")).find((o) => textOf(o) === want);
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
  const now = textOf(byLabelledName(doc, "[role=combobox]", name));
  if (now !== want) { note("age pick did not stick", name, want, now); return false; }
  return true;
}

/** 연령·성별: 연령 칸을 열어(필요하면 '설정 표시') 최소·최대 연령을 고르고 성별 라디오를 고른다. */
export async function setAgeGender(doc: Document, value: string, pace: Pace = real): Promise<boolean> {
  const want = parseAgeGender(value);
  if (!want) return false;
  if (!byLabelledName(doc, "[role=combobox]", "최소 연령")) {
    const show = byRoleText(doc, "button", (t) => t === "설정 표시");
    if (show) { show.click(); await pace.wait(1000); }
    const age = byRoleText(doc, "button", (t) => /^연령\d/.test(t));
    if (age) { age.click(); await pace.wait(1000); }
    note("age opened", { show: Boolean(show), age: Boolean(age), boxes: Boolean(byLabelledName(doc, "[role=combobox]", "최소 연령")) });
  }
  if (!(await pickOption(doc, "최소 연령", want.min, pace))) return false;
  if (!(await pickOption(doc, "최대 연령", want.max, pace))) return false;
  let radio = byLabelledName(doc, "input[type=radio], [role=radio]", want.gender);
  if (!radio) {
    const g = byRoleText(doc, "button", (t) => /^성별/.test(t));
    if (g) { g.click(); await pace.wait(800); }
    radio = byLabelledName(doc, "input[type=radio], [role=radio]", want.gender);
  }
  if (!radio) { note("gender radio not found", want.gender); return false; }
  const on = isChecked(radio);
  if (!on) radio.click();
  await pace.wait(400);
  const checked = isChecked(radio);
  if (!checked) { note("gender radio did not stick", want.gender); return false; }
  note("age/gender set", want.min, want.max, want.gender);
  return true;
}

/** 위치: '전국'이면 메타 기본값 '대한민국'이 이미 맞다 → 할 일 없음(true). 동네·반경은 지도에서 직접 골라야 해서 false. */
export function checkLocation(doc: Document, value: string): boolean {
  if (!/전국/.test(value)) return false;
  return /대한민국/.test(textOf(byRoleText(doc, "button", (t) => t.startsWith("위치"))));
}
