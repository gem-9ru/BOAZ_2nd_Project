// 캐릭터 안내 목록(guide/*.json)의 모양, 검사, 단계 만들기.
// 메타 광고 관리자는 화면 구조가 자주 바뀌므로 '어디를 짚을지'는 코드가 아니라 이 목록에서 고친다.
import type { Change } from "./api";
import type { Setting } from "./flow";

/** 찾는 방법. say가 있으면 '힌트': 진짜 칸이 아직 없을 때 그 전 단계(버튼·구역)를 짚고 이 말을 한다. */
export type FindStrategy = (
  | { aria: string }
  | { labelledBy: string }
  | { labelText: string }
  | { placeholder: string }
  | { heading: string }
  | { role: string; text: string }
  | { role: string; textStarts: string }
  | { role: string; textPattern: string }   // 정규식 (예: "^연령\\d" → '연령18 - 65+'만, 도움말 링크 제외)
) & { say?: string };

/** 자동 진행에서 이 칸을 어떻게 할지: 고르기·넣기는 대신 하고, 날짜·지역·사진처럼 복잡한 칸은 사장님을 기다리고, 게시 앞에선 멈춘다. */
export type AutoKind = "click" | "type" | "skip" | "owner" | "stop" | "endDate" | "ageGender" | "location";

/** 칸이 있는 화면: list = 캠페인 목록(만들기 창), 나머지는 편집 화면 왼쪽 목록의 세 줄 */
export type Level = "list" | "campaign" | "adset" | "ad";

export interface GuideEntry {
  id: string;
  mode: "create" | "edit" | "export";
  page: { urlIncludes?: string; titleText?: string };
  find: FindStrategy[];
  say: string;
  done: "value" | "page" | "manual";
  fallback: { image: string; text: string };
  publish?: true;
  auto?: AutoKind;
  level?: Level;
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

/** EX-03 [다음 테스트 세팅] (v4.2): ② 세팅 목록 전체(all)는 보여 주되, 캐릭터에게는 바꿀 칸 1개 + 게시 직전 확인만(send) 보낸다.
 *  바꿀 칸이 만들기 목록에 없으면(예: 노출 위치) 수정 안내의 같은 칸을 게시 앞에 넣는다. 나머지 칸은 지난번 값으로 끝난 칸. */
export function nextTestSteps(entries: GuideEntry[], settings: Setting[], fieldId: string): { all: GuideStepItem[]; send: GuideStepItem[] } {
  const all = stepsFor("create", entries, settings, []);
  let target = all.find((s) => s.entry.id === fieldId);
  if (!target) {
    const edit = entries.find((e) => e.mode === "edit" && e.id === fieldId);
    if (edit) {
      target = { entry: edit, value: settings.find((s) => s.fieldId === fieldId)?.value };
      const at = all.findIndex((s) => s.entry.publish);
      all.splice(at < 0 ? all.length : at, 0, target);
    }
  }
  const publish = all.find((s) => s.entry.publish);
  const send = [target, publish].filter((x): x is GuideStepItem => Boolean(x));
  return { all, send };
}
