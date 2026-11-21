// 광고 관리자 화면에서 안내 목록의 칸을 찾는다. 난독화된 클래스 이름은 쓰지 않고 사람이 보는 글자로만 찾는다.
import type { FindStrategy } from "../../lib/guide";

const MAX_CLIMB = 4;   // 라벨에서 위로 몇 단계까지만 입력칸을 찾는다 (멀리 있는 검색칸을 잡지 않게)
const FIELD = "input, select, textarea, [role=combobox], [role=textbox], [contenteditable=true]";

function byAria(doc: Document, name: string): HTMLElement | null {
  return Array.from(doc.querySelectorAll<HTMLElement>("[aria-label]")).find((e) => e.getAttribute("aria-label")?.trim() === name) ?? null;
}

function textOf(e: Element): string {
  return (e.textContent ?? "").replace(/\s+/g, " ").trim();
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

function byRoleText(doc: Document, role: string, text: string): HTMLElement | null {
  const sel = role === "button" ? "[role=button], button" : `[role=${role}]`;
  return Array.from(doc.querySelectorAll<HTMLElement>(sel)).find((e) => textOf(e) === text) ?? null;
}

export function locate(doc: Document, strategies: FindStrategy[]): HTMLElement | null {
  for (const s of strategies) {
    const hit =
      "aria" in s ? byAria(doc, s.aria)
      : "labelText" in s ? byLabel(doc, s.labelText)
      : "placeholder" in s ? Array.from(doc.querySelectorAll<HTMLElement>("[placeholder]")).find((e) => e.getAttribute("placeholder") === s.placeholder) ?? null
      : byRoleText(doc, s.role, s.text);
    if (hit) return hit;
  }
  return null;
}

export function isKorean(doc: Document): boolean {
  return (doc.documentElement.lang || "").toLowerCase().startsWith("ko");
}
