// 광고 관리자 화면에서 안내 목록의 칸을 찾는다. 난독화된 클래스 이름은 쓰지 않고 사람이 보는 글자로만 찾는다.
import type { FindStrategy, Level } from "../../lib/guide";

const MAX_CLIMB = 4;   // 라벨에서 위로 몇 단계까지만 입력칸을 찾는다 (멀리 있는 검색칸을 잡지 않게)
const FIELD = "input, select, textarea, [role=combobox], [role=textbox], [contenteditable=true]";

const RADIO_FIELD = `${FIELD}, [role=radio], [role=checkbox], [role=switch]`;

/** 같은 글자의 요소가 여럿이면 화면에 그려진 것을 먼저 (메타는 숨은 복제본을 둔다). 그려진 게 없으면 첫 번째. */
function firstShown(list: HTMLElement[]): HTMLElement | null {
  return list.find((e) => e.getClientRects().length > 0) ?? list[0] ?? null;
}

type Root = Document | Element;

function byAria(doc: Root, name: string): HTMLElement | null {
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>("[aria-label]")).filter((e) => e.getAttribute("aria-label")?.trim() === name));
}

function textOf(e: Element): string {
  return (e.textContent ?? "").replace(/[\u200b\u200c\u200d\ufeff]/g, "").replace(/\s+/g, " ").trim();
}

/** 글자가 정확히 같은 가장 작은 요소를 찾고, 그 근처(같은 부모 → 위로 MAX_CLIMB 단계)의 첫 입력칸을 고른다. */
function byLabel(doc: Root, label: string): HTMLElement | null {
  const top = doc instanceof Document ? doc.body : doc;
  const labels = Array.from(top.querySelectorAll<HTMLElement>("*")).filter(
    (e) => textOf(e) === label && !Array.from(e.children).some((c) => textOf(c) === label),
  );
  for (const l of labels) {
    let box: HTMLElement | null = l.parentElement;
    for (let up = 0; box && box !== top && up < MAX_CLIMB; up += 1, box = box.parentElement) {
      const field = box.querySelector<HTMLElement>(FIELD);
      if (field) return field;
    }
  }
  return null;
}

function byRoleText(doc: Root, role: string, match: (t: string) => boolean): HTMLElement | null {
  const sel = role === "button" ? "[role=button], button, a" : `[role=${role}]`;   // 메타의 "설정 표시" 같은 링크도 버튼처럼 누른다
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>(sel)).filter((e) => match(textOf(e))));
}

/** 메타는 칸 이름을 aria-labelledby로 잇는다: 연결된 요소 중 하나의 글자가 정확히 같으면 그 칸. */
function byLabelledBy(doc: Root, name: string): HTMLElement | null {
  const owner = doc instanceof Document ? doc : doc.ownerDocument;
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>("[aria-labelledby]")).filter((e) => {
    if (!e.matches(RADIO_FIELD)) return false;
    const ids = (e.getAttribute("aria-labelledby") ?? "").split(/\s+/).filter(Boolean);
    return ids.some((id) => textOf(owner.getElementById(id) ?? owner.createElement("i")) === name);
  }));
}

function byHeading(doc: Root, text: string): HTMLElement | null {
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>("[role=heading], h1, h2, h3, h4")).filter((e) => textOf(e) === text));
}

function find(doc: Root, s: FindStrategy): HTMLElement | null {
  if ("aria" in s) return byAria(doc, s.aria);
  if ("labelledBy" in s) return byLabelledBy(doc, s.labelledBy);
  if ("labelText" in s) return byLabel(doc, s.labelText);
  if ("placeholder" in s) return firstShown(Array.from(doc.querySelectorAll<HTMLElement>("[placeholder]")).filter((e) => e.getAttribute("placeholder") === s.placeholder));
  if ("heading" in s) return byHeading(doc, s.heading);
  if ("textStarts" in s) return byRoleText(doc, s.role, (t) => t.startsWith(s.textStarts));
  if ("textPattern" in s) { const re = new RegExp(s.textPattern); return byRoleText(doc, s.role, (t) => re.test(t)); }
  return byRoleText(doc, s.role, (t) => t === s.text);
}

/** 앞에서부터 처음 찾은 칸과 그 방법의 순서. */
/** root를 주면 그 안에서만 찾는다 (열린 창 안). */
export function locateWith(doc: Document | Element, strategies: FindStrategy[]): { el: HTMLElement; index: number } | null {
  for (let i = 0; i < strategies.length; i += 1) {
    const el = find(doc, strategies[i]!);
    if (el) return { el, index: i };
  }
  return null;
}

export function locate(doc: Document, strategies: FindStrategy[]): HTMLElement | null {
  return locateWith(doc, strategies)?.el ?? null;
}

export function isKorean(doc: Document): boolean {
  return (doc.documentElement.lang || "").toLowerCase().startsWith("ko");
}

/** 칸을 화면 가운데로. 메타는 먼 구역을 그리지 않아 칸 크기가 0일 수 있다 → 그려진 가장 가까운 상위 구역을 먼저 보여
 *  다음 확인 때 칸이 그려지게 한다. 칸이 그려져 있으면 true. */
export function reveal(el: HTMLElement): boolean {
  if (el.getClientRects().length > 0) {
    el.scrollIntoView({ block: "center", behavior: "smooth" });
    return true;
  }
  let a: HTMLElement | null = el.parentElement;
  while (a && a.getClientRects().length === 0) a = a.parentElement;
  a?.scrollIntoView({ block: "center" });
  return false;
}

// ── [다음 칸]이 페이지에서 대신 해 주는 일 ──

const CHOICE_TYPES = new Set(["radio", "checkbox"]);

/** 고르는 칸(라디오·체크박스·스위치). */
export function isChoice(el: HTMLElement): boolean {
  const role = el.getAttribute("role");
  return (el instanceof HTMLInputElement && CHOICE_TYPES.has(el.type)) || role === "radio" || role === "checkbox" || role === "switch";
}

export function isChecked(el: HTMLElement): boolean {
  return el instanceof HTMLInputElement ? el.checked : el.getAttribute("aria-checked") === "true";
}

/** 글자를 넣는 칸. */
export function isTextField(el: HTMLElement): boolean {
  return (el instanceof HTMLInputElement && !CHOICE_TYPES.has(el.type)) || el instanceof HTMLTextAreaElement || el.isContentEditable
    || el.getAttribute("contenteditable") === "true";
}

/** 게시와 관련된 버튼은 어떤 경우에도 누르지 않는다. */
export function isPublishLike(el: HTMLElement): boolean {
  return /게시|publish/i.test(el.textContent ?? "") || /게시|publish/i.test(el.getAttribute("aria-label") ?? "");
}

/** React가 알아채게 값 넣기: 원래 value setter로 넣고 input·change 이벤트.
 *  글 편집기(contenteditable, 메타 '기본 문구')는 커서를 칸 안에 두고 붙여넣기 → 안 되면 글자 입력 명령.
 *  (2026-11-25 실제 화면: 커서 없이 넣으면 안 들어가고, 커서를 끝에 두고 입력 명령을 쓰면 두 번 들어갔다 → 전체 선택 후 바꾸기) */
export function typeInto(el: HTMLElement, value: string): void {
  if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) {
    const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, "value")?.set?.call(el, value);
    el.dispatchEvent(new Event("input", { bubbles: true }));
    el.dispatchEvent(new Event("change", { bubbles: true }));
    return;
  }
  const doc = el.ownerDocument;
  const has = () => (el.textContent ?? "").includes(value);
  const selectAll = () => {
    el.focus();
    const sel = doc.getSelection();
    const range = doc.createRange();
    range.selectNodeContents(el);
    sel?.removeAllRanges();
    sel?.addRange(range);
  };
  selectAll();
  try {
    const dt = new DataTransfer();
    dt.setData("text/plain", value);
    el.dispatchEvent(new ClipboardEvent("paste", { clipboardData: dt, bubbles: true, cancelable: true }));
  } catch { /* DataTransfer가 없는 환경 */ }
  if (has()) return;
  selectAll();
  const ok = typeof doc.execCommand === "function" && doc.execCommand("insertText", false, value);
  if (!ok) el.textContent = value;   // 글자 입력 명령이 없는 환경(시험용)에서만
  el.dispatchEvent(new Event("input", { bubbles: true }));
}

/** 넣은 값이 실제로 칸에 있는지 (편집기가 받아 줬는지). */
export function hasValue(el: HTMLElement, value: string): boolean {
  const now = el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement ? el.value : el.textContent ?? "";
  return now.replace(/\s+/g, " ").includes(value.replace(/\s+/g, " ").trim());
}

/** 편집 화면의 스크롤 영역: 화면에 보이는 가장 큰 세로 스크롤 상자 (메타는 아래 구역을 스크롤해야 그린다). within을 주면 그 안(열린 창)에서. */
export function mainScroller(doc: Document, within?: Element): HTMLElement | null {
  let best: HTMLElement | null = null;
  for (const e of Array.from((within ?? doc).querySelectorAll<HTMLElement>("*"))) {
    const oy = (doc.defaultView?.getComputedStyle(e).overflowY ?? "") || e.style.overflowY;
    if (!/(auto|scroll)/.test(oy) || e.scrollHeight <= e.clientHeight + 50 || e.clientHeight < 300) continue;
    if (!best || e.clientHeight * e.clientWidth > best.clientHeight * best.clientWidth) best = e;
  }
  return best;
}

// ── 화면 넘나들기: 편집 화면 왼쪽 목록(캠페인 · 광고 세트 · 광고) ──

const LEVEL_PATH: Record<string, Level> = { campaigns: "campaign", adsets: "adset", ads: "ad" };
const LEVEL_NAME: Record<Exclude<Level, "list">, string> = { campaign: "캠페인", adset: "광고 세트", ad: "광고" };

/** 지금 화면: 주소의 …/manage/{campaigns|adsets|ads}/edit… 로 안다. 편집 화면이 아니면 list. */
export function currentLevel(doc: Document): Level {
  const m = (doc.location?.pathname ?? "").match(/\/manage\/(campaigns|adsets|ads)\/edit/);
  return m ? LEVEL_PATH[m[1]!]! : "list";
}

/** 왼쪽 목록의 그 줄(aria-label "캠페인"·"광고 세트"·"광고")을 눌러 같은 페이지 안에서 화면을 바꾼다. 줄이 없으면 false. */
export function goToLevel(doc: Document, level: Level): boolean {
  if (level === "list") return false;
  const row = doc.querySelector<HTMLElement>(`[role=rowheader][aria-label="${LEVEL_NAME[level]}"]`);
  if (!row) return false;
  row.click();
  return true;
}

/** 지금 열려 있는 창(크리에이티브 설정·미디어 등): 화면에 그려진 큰 [role=dialog] 중 마지막. 없으면 null.
 *  창이 열려 있으면 그 뒤의 칸은 가려져 누를 수 없으므로 창 안에서만 찾는다. */
export function openDialog(doc: Document): HTMLElement | null {
  const list = Array.from(doc.querySelectorAll<HTMLElement>("[role=dialog], [aria-modal=true]"))
    .filter((d) => d.isConnected && (d.getClientRects().length > 0 || d.childElementCount > 0) && !d.closest("ad-coach-buddy"));
  return list.at(-1) ?? null;
}
