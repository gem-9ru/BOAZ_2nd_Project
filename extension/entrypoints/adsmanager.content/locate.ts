// 광고 관리자 화면에서 안내 목록의 칸을 찾는다. 난독화된 클래스 이름은 쓰지 않고 사람이 보는 글자로만 찾는다.
import type { FindStrategy } from "../../lib/guide";

const MAX_CLIMB = 4;   // 라벨에서 위로 몇 단계까지만 입력칸을 찾는다 (멀리 있는 검색칸을 잡지 않게)
const FIELD = "input, select, textarea, [role=combobox], [role=textbox], [contenteditable=true]";

const RADIO_FIELD = `${FIELD}, [role=radio], [role=checkbox], [role=switch]`;

/** 같은 글자의 요소가 여럿이면 화면에 그려진 것을 먼저 (메타는 숨은 복제본을 둔다). 그려진 게 없으면 첫 번째. */
function firstShown(list: HTMLElement[]): HTMLElement | null {
  return list.find((e) => e.getClientRects().length > 0) ?? list[0] ?? null;
}

function byAria(doc: Document, name: string): HTMLElement | null {
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>("[aria-label]")).filter((e) => e.getAttribute("aria-label")?.trim() === name));
}

function textOf(e: Element): string {
  return (e.textContent ?? "").replace(/[\u200b\u200c\u200d\ufeff]/g, "").replace(/\s+/g, " ").trim();
}

/** 글자가 정확히 같은 가장 작은 요소를 찾고, 그 근처(같은 부모 → 위로 MAX_CLIMB 단계)의 첫 입력칸을 고른다. */
function byLabel(doc: Document, label: string): HTMLElement | null {
  const labels = Array.from(doc.body.querySelectorAll<HTMLElement>("*")).filter(
    (e) => textOf(e) === label && !Array.from(e.children).some((c) => textOf(c) === label),
  );
  for (const l of labels) {
    let box: HTMLElement | null = l.parentElement;
    for (let up = 0; box && box !== doc.body && up < MAX_CLIMB; up += 1, box = box.parentElement) {
      const field = box.querySelector<HTMLElement>(FIELD);
      if (field) return field;
    }
  }
  return null;
}

function byRoleText(doc: Document, role: string, match: (t: string) => boolean): HTMLElement | null {
  const sel = role === "button" ? "[role=button], button, a" : `[role=${role}]`;   // 메타의 "설정 표시" 같은 링크도 버튼처럼 누른다
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>(sel)).filter((e) => match(textOf(e))));
}

/** 메타는 칸 이름을 aria-labelledby로 잇는다: 연결된 요소 중 하나의 글자가 정확히 같으면 그 칸. */
function byLabelledBy(doc: Document, name: string): HTMLElement | null {
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>("[aria-labelledby]")).filter((e) => {
    if (!e.matches(RADIO_FIELD)) return false;
    const ids = (e.getAttribute("aria-labelledby") ?? "").split(/\s+/).filter(Boolean);
    return ids.some((id) => textOf(doc.getElementById(id) ?? doc.createElement("i")) === name);
  }));
}

function byHeading(doc: Document, text: string): HTMLElement | null {
  return firstShown(Array.from(doc.querySelectorAll<HTMLElement>("[role=heading], h1, h2, h3, h4")).filter((e) => textOf(e) === text));
}

function find(doc: Document, s: FindStrategy): HTMLElement | null {
  if ("aria" in s) return byAria(doc, s.aria);
  if ("labelledBy" in s) return byLabelledBy(doc, s.labelledBy);
  if ("labelText" in s) return byLabel(doc, s.labelText);
  if ("placeholder" in s) return firstShown(Array.from(doc.querySelectorAll<HTMLElement>("[placeholder]")).filter((e) => e.getAttribute("placeholder") === s.placeholder));
  if ("heading" in s) return byHeading(doc, s.heading);
  if ("textStarts" in s) return byRoleText(doc, s.role, (t) => t.startsWith(s.textStarts));
  return byRoleText(doc, s.role, (t) => t === s.text);
}

/** 앞에서부터 처음 찾은 칸과 그 방법의 순서. */
export function locateWith(doc: Document, strategies: FindStrategy[]): { el: HTMLElement; index: number } | null {
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
