// 사장님 대신 맞추는 복잡한 칸 (시작·종료 날짜 · 연령·성별 · 위치).
// 2026-11-25 실제 메타 광고 세트 화면에서 확인한 구조: 날짜는 yyyy-mm-dd 글자 칸, 연령은 '최소/최대 연령' 목록(일부만 그림),
// 성별은 '전체/남성/여성' 라디오, 위치는 기본 '대한민국'. 게시와 관련된 것은 건드리지 않는다.
import { isoDate, parseWon } from "../../lib/settings";
import { byRoleText, firstShown, isChecked, reveal, textOf, typeInto } from "./locate";

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

/** 종료 날짜 칸을 찾는 기준: 일일 예산이면 '종료 날짜 설정' 스위치, 총예산이면 스위치 대신 '종료 날짜 기간' 목록(30일·직접 지정)이 나온다
 *  (2026-11-26 새 초안에서 확인: '총 예산'을 고르면 메타가 종료 날짜를 30일 뒤로 켜고 스위치를 없앤다). 날짜 칸은 그 뒤의 첫 칸. */
function endAnchor(doc: Document): { anchor: HTMLElement; on: boolean; isSwitch: boolean } | null {
  const sw = byLabelledName(doc, "input, [role=checkbox], [role=switch]", "종료 날짜 설정");
  if (sw) return { anchor: sw, on: isChecked(sw), isSwitch: true };
  const period = byLabelledName(doc, "[role=combobox]", "종료 날짜 기간");
  return period ? { anchor: period, on: true, isSwitch: false } : null;
}

function endBox(doc: Document, anchor: HTMLElement): HTMLInputElement | undefined {
  return Array.from(doc.querySelectorAll<HTMLInputElement>("input[placeholder='yyyy-mm-dd']"))
    .find((i) => anchor.compareDocumentPosition(i) & Node.DOCUMENT_POSITION_FOLLOWING);
}

/** 종료 날짜: (일일 예산이면) '종료 날짜 설정'을 켜고, 그 뒤 날짜 칸(시작 날짜 아님)에 yyyy-mm-dd로 넣는다.
 *  총예산이면 '종료 날짜 기간' 뒤 날짜 칸에 넣는다 (넣으면 기간이 '직접 지정'으로 바뀜, 실제 화면 확인). */
export async function setEndDate(doc: Document, value: string, pace: Pace = real): Promise<boolean> {
  const date = value.match(/\d{4}-\d{2}-\d{2}/)?.[0];
  let a = endAnchor(doc);
  if (!date || !a) return false;
  if (a.isSwitch && !a.on) { a.anchor.click(); await pace.wait(800); a = endAnchor(doc); if (!a) return false; }
  const sw = a.anchor;
  const box = endBox(doc, sw);
  if (!box) return false;
  box.scrollIntoView?.({ block: "center" });   // 화면에 안 보이는 날짜 칸은 메타가 입력을 무시한다
  await pace.wait(300);
  box.focus();
  typeInto(box, date);
  box.blur();
  await pace.wait(600);
  // 시작 날짜처럼 정말 들어갔는지 다시 읽는다 (안 들어가면 총예산의 메타 기본값 '30일 뒤'가 남는다, 감사 8)
  const got = dateOf(endBox(doc, sw)?.value ?? "");
  if (got !== date) { note("end date did not stick"); return false; }
  const time = value.match(/\b\d{2}:\d{2}\b/)?.[0];
  return time ? setTimeAfter(doc, box, time, pace) : true;
}

/** 날짜 칸 글자('2026년 12월 3일' · '2026-12-03') → '2026-12-03'. 못 읽으면 null */
export function dateOf(text: string): string | null {
  const m = text.match(/(\d{4})\D+(\d{1,2})\D+(\d{1,2})/);
  return m ? `${m[1]}-${m[2]!.padStart(2, "0")}-${m[3]!.padStart(2, "0")}` : null;
}

/** '30–39세 · 여성' → 메타 목록 값. 65 이상은 '65+'. 성별 '전체'는 메타의 '전체'. */
export function parseAgeGender(value: string): { min: string; max: string; gender: "전체" | "남성" | "여성" } | null {
  const m = value.match(/(\d{2})\s*[–-]\s*(\d{2})/);
  if (!m) return null;
  const max = Number(m[2]) >= 65 ? "65+" : m[2]!;
  const gender = /여성/.test(value) ? "여성" : /남성/.test(value) ? "남성" : "전체";
  return { min: m[1]!, max, gender };
}

/** '제어 옵션'의 '최소 연령' 버튼(접힘: '최소 연령18세 · …', 펼침: '최소 연령'). 펼치면 바로 옆 구역에 같은 이름 '최소 연령' 목록이 생긴다 (2026-11-26 실제 화면, 18~25만). */
function controlAgeButton(doc: Document): HTMLElement | null {
  return byRoleText(doc, "button", (t) => /^최소 연령(\s*\d|$)/.test(t));
}
function controlAgeBox(doc: Document): HTMLElement | null {
  return controlAgeButton(doc)?.nextElementSibling?.querySelector<HTMLElement>("[role=combobox]") ?? null;
}
/** '타겟 추천'의 연령 목록 (위쪽 '제어 옵션'의 같은 이름 칸은 뺀다) */
function suggestBox(doc: Document, name: string): HTMLElement | null {
  const control = controlAgeBox(doc);
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>("[role=combobox]")).filter((e) => e !== control &&
    (e.getAttribute("aria-labelledby") ?? "").split(/\s+/).some((id) => textOf(doc.getElementById(id)) === name)));
}
const CONTROL_AGE_MAX = 25;   // 메타가 꼭 지키는 최소 연령은 25세까지만 고를 수 있다

/** 목록(combobox)을 열고 선택지를 찾아 누른다. 메타는 선택지를 일부만 그리므로 목록을 내리며 찾는다. */
async function pickOption(doc: Document, name: string, want: string, pace: Pace, get: () => HTMLElement | null = () => suggestBox(doc, name)): Promise<boolean> {
  const box = get();
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
  const now = textOf(get());
  if (now !== want) { note("age pick did not stick", name, want, now); return false; }
  return true;
}

/** 연령·성별: 연령 칸을 열어(필요하면 '설정 표시') 최소·최대 연령을 고르고 성별 라디오를 고른다. */
export async function setAgeGender(doc: Document, value: string, pace: Pace = real): Promise<boolean> {
  const want = parseAgeGender(value);
  if (!want) return false;
  if (!suggestBox(doc, "최소 연령")) {
    const show = byRoleText(doc, "button", (t) => t === "설정 표시");
    if (show) { show.click(); await pace.wait(1000); }
    const age = byRoleText(doc, "button", (t) => /^연령\d/.test(t));
    if (age) { age.click(); await pace.wait(1000); }
    note("age opened", { show: Boolean(show), age: Boolean(age), boxes: Boolean(suggestBox(doc, "최소 연령")) });
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
  return setControlMinAge(doc, want.min, pace);
}

/** 꼭 지키는 '최소 연령' (제어 옵션): 추천 나이는 메타가 넘을 수 있어서, 최소 나이만은 여기에도 넣는다 (25세까지만 됨).
 *  이 칸이 없는 화면이면 할 일 없음(true). */
async function setControlMinAge(doc: Document, min: string, pace: Pace): Promise<boolean> {
  const btn = controlAgeButton(doc);
  if (!btn) { note("control age not found"); return true; }
  if (!controlAgeBox(doc)) {
    reveal(btn);
    await pace.wait(800);
    btn.click();
    await pace.wait(1000);
  }
  const want = String(Math.min(Number(min), CONTROL_AGE_MAX));
  const ok = await pickOption(doc, "최소 연령", want, pace, () => controlAgeBox(doc));
  note("control min age", want, ok);
  return ok;
}

/** 위치: '전국'이면 메타 기본값 '대한민국'이 이미 맞다 → 할 일 없음(true). 동네·반경은 지도에서 직접 골라야 해서 false. */
export function checkLocation(doc: Document, value: string): boolean {
  if (!/전국/.test(value)) return false;
  return /대한민국/.test(textOf(byRoleText(doc, "button", (t) => t.startsWith("위치"))));
}

// ── 돈이 걸린 칸 (2026-11-26 실제 광고 세트 편집 화면에서 확인) ──
// 캠페인 '예산 전략': 라디오 '캠페인 예산' / '광고 세트 예산' (aria-labelledby 이름표)
// 광고 세트 '예산 및 일정': '예산 모드' 이름표가 붙은 목록(combobox, 글자 '일일 예산'·'총예산') + 그 뒤 '금액을 입력하세요' 칸(값 '20,000')
// 이미 돌린 세트는 목록이 aria-disabled="true"로 잠긴다. 넣은 뒤엔 언제나 화면에서 다시 읽어 확인한다.
// 주의: 메타는 화면 밖 구역을 그리지 않는다. 그리기 전의 금액 칸은 값이 '0'으로 읽힌다 (같은 날 실제 화면 확인)
// → 읽기 전에 구역을 화면에 띄우고, 0·빈 값은 '못 읽음'(null)으로 보고 맞다고 하지 않는다.
// 새 초안 기본값(2026-11-26): 일일 예산 ₩20,000 · 종료 날짜 꺼짐 → 그대로 게시하면 끌 때까지 하루 2만 원씩 나간다.
// '총 예산'(목록 글자는 띄어 씀)을 고르면 메타가 금액을 ₩350,000으로 바꾸고 종료 날짜를 30일 뒤로 켠다 → 금액을 꼭 다시 넣는다.

const AMOUNT = "input[placeholder='금액을 입력하세요']";

/** 광고 세트 예산 칸: 종류(daily·lifetime·null=못 읽음), 금액(원), 목록·금액 칸. 칸이 없으면(캠페인 예산 사용) found = false */
export function readBudget(doc: Document): { found: boolean; mode: "daily" | "lifetime" | null; amount: number | null; combo: HTMLElement | null; input: HTMLInputElement | null } {
  const combo = byLabelledName(doc, "[role=combobox]", "예산 모드");
  if (!combo) return { found: false, mode: null, amount: null, combo: null, input: null };
  const t = textOf(combo);
  const mode = /총\s?예산/.test(t) ? "lifetime" : /일일\s?예산/.test(t) ? "daily" : null;
  const input = Array.from(doc.querySelectorAll<HTMLInputElement>(AMOUNT))
    .find((i) => combo.compareDocumentPosition(i) & Node.DOCUMENT_POSITION_FOLLOWING) ?? null;
  const n = Number((input?.value ?? "").split(".")[0]!.replace(/[^\d]/g, ""));   // '30,000.00' → 30000 (소수점 뒤는 버림, 감사 18)
  return { found: true, mode, amount: n > 0 ? n : null, combo, input };
}

/** 캠페인 '예산 전략'을 '광고 세트 예산'으로 (캠페인 예산이면 광고 세트에 총예산 칸이 없고 메타가 캠페인 하루 예산으로 쓴다),
 *  '예산 공유(최대 20%)'는 끈다. 둘 다 정말 그렇게 됐는지 다시 읽어 본다. */
export async function useAdsetBudget(doc: Document, pace: Pace = real): Promise<boolean | "unseen"> {
  const radio = byLabelledName(doc, "input[type=radio], [role=radio]", "광고 세트 예산");
  if (!radio) { note("adset budget radio not found"); return false; }
  if (!isChecked(radio)) { radio.click(); await pace.wait(800); }
  const now = byLabelledName(doc, "input[type=radio], [role=radio]", "광고 세트 예산");
  if (!(now && isChecked(now))) { note("adset budget radio did not stick"); return false; }
  // '예산 일부를 다른 광고 세트와 공유하기'(최대 20%)는 새 캠페인에서 기본으로 켜져 있다 (2026-11-26 새 초안에서 확인).
  // 켜 두면 A·B 중 한 세트가 자기 총예산보다 더 쓸 수 있다 → 끈다. 누르면 0.5초쯤 뒤에 반영된다
  const share = () => doc.querySelector<HTMLInputElement>(`input[type=checkbox][aria-label="${SHARE}"]`);
  if (share()?.checked) {
    share()!.click();
    await pace.wait(1200);
    // 메타는 바로 끄지 않고 '예산 공유를 해제하시겠어요?' 창을 띄운다 (2026-11-26 실제 화면) → '예산 공유 해제'
    const off = byRoleText(doc, "button", (t) => t === "예산 공유 해제");
    if (off) { off.click(); await pace.wait(1200); }
  }
  if (share()?.checked) { note("budget share did not turn off"); return false; }
  // 칸을 못 찾으면 꺼졌는지 알 수 없다 (메타는 화면 밖 구역을 안 그린다) → '껐다'고 넘어가지 않고 사장님께
  if (!share()) { reveal(now); await pace.wait(800); }
  if (!share()) { note("budget share box not found"); return "unseen"; }   // 못 찾음 ≠ 켜져 있음 → 사장님이 보고 한 번 더 누르면 넘어간다
  return !share()!.checked;
}

/** 지금 편집 중인 광고 세트 id (광고 관리자 주소의 selected_adset_ids). 두 세트 돈 확인이 같은 세트를 두 번 읽지 않게 쓴다 */
export function currentAdsetId(doc: Document): string | null {
  const ids = new URLSearchParams(doc.defaultView?.location.search ?? "").get("selected_adset_ids");
  return ids ? ids.split(",")[0]! : null;
}

const SHARE = "예산 일부를 다른 광고 세트와 공유하기";

/** 돈 확인 문구 끝: 칸을 화면에서 못 찾아 '다르다'고 말할 수 없는 경우. 이것만 남으면 [다 했어요]를 두 번째 눌렀을 때 넘어간다 (화면 검토 13) */
export const UNSEEN = " (화면에서 칸을 못 찾았어요 → 직접 확인하셨으면 '다 했어요'를 한 번 더 눌러 주세요)";

/** 광고 세트 예산을 '총예산' + 금액으로. 목록을 열어 '총예산'을 고르고 금액을 넣은 뒤, 화면에서 다시 읽어 둘 다 맞을 때만 true. */
export async function setLifetimeBudget(doc: Document, value: string, pace: Pace = real): Promise<boolean> {
  const want = parseWon(value);
  if (!want) { note("no budget value"); return false; }
  let b = readBudget(doc);
  if (!b.combo) { note("budget mode box not found"); return false; }
  reveal(b.combo);   // 구역이 그려져야 금액 칸 값이 맞게 읽힌다
  await pace.wait(800);
  b = readBudget(doc);
  if (!b.combo) { note("budget mode box went away"); return false; }
  if (b.mode !== "lifetime") {
    if (b.combo.getAttribute("aria-disabled") === "true") { note("budget mode is locked"); return false; }
    b.combo.scrollIntoView?.({ block: "center" });
    b.combo.click();
    await pace.wait(700);
    const opt = Array.from(doc.querySelectorAll<HTMLElement>("[role=option]")).find((o) => /^총\s?예산/.test(textOf(o)));
    if (!opt) { b.combo.click(); note("lifetime option not found"); return false; }   // 목록을 닫고 사장님께
    opt.click();
    await pace.wait(800);
    b = readBudget(doc);
    // 메타가 늦게 바뀔 때가 있다 (2026-11-26 실제 화면: 첫 확인에선 아직 일일, 조금 뒤 총 예산) → 한 번 더 기다려 읽는다
    if (b.mode !== "lifetime") { await pace.wait(1500); b = readBudget(doc); }
    if (b.mode !== "lifetime") { note("budget mode did not stick"); return false; }
  }
  if (b.amount !== want) {
    if (!b.input) { note("budget amount box not found"); return false; }
    b.input.scrollIntoView?.({ block: "center" });
    await pace.wait(300);
    b.input.focus();
    typeInto(b.input, String(want));
    b.input.blur();
    await pace.wait(700);
    b = readBudget(doc);
  }
  const ok = b.mode === "lifetime" && b.amount === want;
  if (!ok) note("budget did not stick", b.mode, b.amount === want);
  return ok;
}

/** 게시 앞 돈 확인: 광고 세트 화면에서 다시 읽어 다른 것을 사장님 말로 돌려준다 (빈 목록 = 다 맞음).
 *  - 예산 칸이 없음(캠페인 예산) · 종류가 총예산이 아님 · 금액이 세팅값과 다름 · 종료 날짜가 꺼졌거나 비어 있음 */
export async function moneyProblems(doc: Document, value: string, pace: Pace = real): Promise<string[]> {
  const want = parseWon(value);
  const out: string[] = [];
  const first = readBudget(doc);
  if (first.combo) { reveal(first.combo); await pace.wait(800); }   // 구역이 그려져야 금액이 '0'이 아닌 진짜 값으로 읽힌다
  const b = readBudget(doc);
  const won = (n: number) => `${n.toLocaleString()}원`;
  if (!want) out.push("② 세팅에서 정한 총예산이 없어요 → 패널 ② 세팅에서 금액을 정해 주세요");
  if (!b.found) {
    out.push("광고 세트에 예산 칸이 없어요 → 캠페인 '예산 전략'을 '광고 세트 예산'으로 바꿔 주세요");
  } else {
    if (b.mode !== "lifetime") out.push(`예산 종류가 '${b.mode === "daily" ? "일일 예산" : textOf(b.combo) || "알 수 없음"}'이에요 → '총예산'으로 바꿔 주세요`);
    if (want && b.amount === null) out.push(`금액을 읽지 못했어요 (비었거나 아직 화면에 안 그려짐) → '예산 및 일정'을 화면에 띄우고 ${won(want)}인지 확인해 주세요${UNSEEN}`);
    else if (want && b.amount !== want) out.push(`금액이 ${won(b.amount!)}이에요 → ${won(want)}으로 넣어 주세요`);
  }
  const end = endAnchor(doc);
  const endValue = end && end.on ? endBox(doc, end.anchor)?.value.trim() : "";
  if (!end) out.push(`종료 날짜 칸을 찾지 못했어요 → '예산 및 일정'에서 종료 날짜가 들어 있는지 확인해 주세요${UNSEEN}`);
  else if (!endValue) out.push("종료 날짜가 없어요 → '종료 날짜 설정'을 켜고 날짜를 넣어 주세요 (없으면 끌 때까지 계속 나가요)");
  else if ((dateOf(endValue) ?? "9999") < isoDate(new Date())) out.push("종료 날짜가 이미 지났어요 → 오늘 이후 날짜로 바꿔 주세요");
  // 메타 자체 경고: '예산은 ₩40,080.00 이상이어야 하며, 그렇지 않으면 광고가 게재되지 않을 수 있습니다' (하루 최소 × 기간보다 적을 때)
  const low = Array.from(doc.querySelectorAll<HTMLElement>("body *")).map((e) => (e.children.length ? "" : textOf(e)))
    .map((t) => t.match(/예산은 ₩([\d,]+)(?:\.\d+)? 이상이어야/)).find(Boolean);
  if (low) out.push(`메타가 '예산은 ${low[1]}원 이상이어야 광고가 나가요'라고 해요 → 금액을 늘리거나 기간을 줄여 주세요`);
  return out;
}
