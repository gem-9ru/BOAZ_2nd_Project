// 캐릭터 안내 목록(guide/*.json)의 모양, 검사, 단계 만들기.
// 메타 광고 관리자는 화면 구조가 자주 바뀌므로 '어디를 짚을지'는 코드가 아니라 이 목록에서 고친다.
import type { Change } from "./api";
import type { Setting } from "./flow";

export type FindStrategy =
  | { aria: string }
  | { labelText: string }
  | { placeholder: string }
  | { role: string; text: string };

export interface GuideEntry {
  id: string;
  mode: "create" | "edit" | "export";
  page: { urlIncludes?: string; titleText?: string };
  find: FindStrategy[];
  say: string;
  done: "value" | "page" | "manual";
  fallback: { image: string; text: string };
  publish?: true;
}

export interface GuideStepItem {
  entry: GuideEntry;
  value?: string;
}

export function validateGuide(entries: GuideEntry[], settingIds: string[]): string[] {
  const problems: string[] = [];
  for (const e of entries) {
    if (e.mode === "create" && !e.publish && !settingIds.includes(e.id)) problems.push(`${e.id}: 세팅값 목록에 없는 칸`);
    if (e.find.length === 0) problems.push(`${e.id}: 찾는 방법이 비어 있음`);
    for (const f of e.find) {
      for (const v of Object.values(f)) {
        if (!String(v).trim()) problems.push(`${e.id}: 찾는 글자가 비어 있음`);
        else if (String(v).trim().startsWith(".")) problems.push(`${e.id}: 클래스 이름은 쓰지 않음 (${v})`);
      }
    }
    if (!e.say.trim() || !e.fallback.text.trim()) problems.push(`${e.id}: 말풍선·대체 문장이 비어 있음`);
  }
  return problems;
}

export function stepsFor(mode: GuideEntry["mode"], entries: GuideEntry[], settings: Setting[], changes: Change[]): GuideStepItem[] {
  if (mode === "create") {
    return entries
      .filter((e) => e.mode === "create")
      .map((entry) => ({ entry, value: settings.find((s) => s.fieldId === entry.id)?.value }));
  }
  if (mode === "edit") {
    return changes.flatMap((c) => {
      const entry = entries.find((e) => e.mode === "edit" && e.id === c.field_id);
      return entry ? [{ entry, value: c.new }] : [];
    });
  }
  return entries.filter((e) => e.mode === "export").map((entry) => ({ entry }));
}
