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
) & {
  say?: string;
  /** 열린 창 안에서만 찾는다 (예: 창의 [다음]. 창이 없으면 편집 화면의 [다음]을 잘못 누르지 않게) */
  inDialog?: boolean;
  /** 창이 없을 때만 찾는다 (예: '크리에이티브 설정' 버튼. 창 안 위쪽 단계 이름을 눌러 단계를 건너뛰지 않게) */
  pageOnly?: boolean;
};

/** 자동 진행에서 이 칸을 어떻게 할지: 고르기·넣기는 대신 하고, 날짜·지역·사진처럼 복잡한 칸은 사장님을 기다리고, 게시 앞에선 멈춘다. */
/** 돈이 걸린 칸 (2026-11-26 사장님: "돈이 설정한 대로 잘 나가는지, 추가 지출은 없는지가 제일 중요"):
 *  campaignBudget = 캠페인 '예산 전략'을 광고 세트 예산으로, lifetimeBudget = 광고 세트 총예산 금액,
 *  moneyCheck = 게시 앞 돈 확인. 셋 다 화면에서 다시 읽어 맞을 때만 다음 칸 ([다 했어요]로도 건너뛰지 못함) */
export type MoneyKind = "campaignBudget" | "lifetimeBudget" | "moneyCheck";
export type AutoKind = "click" | "type" | "skip" | "owner" | "stop" | "startDate" | "endDate" | "ageGender" | "location" | MoneyKind;

/** 칸이 있는 화면: list = 캠페인 목록(만들기 창), 나머지는 편집 화면 왼쪽 목록의 세 줄 */
export type Level = "list" | "campaign" | "adset" | "ad";

/** 한 칸 안의 하위 단계 (예: 사진 = ① '크리에이티브 설정' 열기 ② '이미지 광고' 누르기 ③ 사진 고르기).
 *  화면에 나타난 가장 뒤 단계가 지금 단계다. 다음 단계의 요소가 나타나면 그게 '넘어가는 신호'. */
export interface GuideStage {
  /** 이 단계에서 짚을 것 (앞에서부터 처음 찾은 것). 방법에 say가 있으면 그 말을 한다 */
  find: FindStrategy[];
  say: string;
  /** buddy = 뭉치가 대신 누름, owner = 사장님이 직접 (뭉치는 짚고 기다림) */
  by: "buddy" | "owner";
  /** page = 열린 창이 없을 때만 찾는다 (메타 사진 창 위쪽 단계 표시에도 '크리에이티브 설정' 버튼이 있어서),
   *  dialog = 열린 창 안에서만 찾는다 (편집 화면 아래의 '다음'을 잡지 않게) */
  where?: "page" | "dialog";
}

export interface GuideEntry {
  id: string;
  mode: "create" | "edit" | "export";
  page: { urlIncludes?: string; titleText?: string };
  /** stages가 있으면 find는 첫 단계와 같게 둔다 (칸 위치 지도·검사용) */
  find: FindStrategy[];
  say: string;
  done: "value" | "page" | "manual";
  fallback: { image: string; text: string };
  publish?: true;
  auto?: AutoKind;
  level?: Level;
  stages?: GuideStage[];
  /** 이게 화면에 나타나면 이 칸은 끝 → 바로 다음 칸 (예: 사진을 넣어야 생기는 '기본 문구' 칸) */
  doneWhen?: FindStrategy[];
  /** 이 칸은 열린 창 밖(광고 화면)에 있다. 창이 열려 있으면 칸이 아직 안 그려졌어도 창을 마칠 때까지 기다린다
   *  (메타 '크리에이티브 설정' 창 뒤의 '웹사이트 URL': 창이 열린 동안에는 칸이 그려지지 않는다) */
  outsideDialog?: true;
}

export interface GuideStepItem {
  entry: GuideEntry;
  value?: string;
}

/** 패널 ↔ 광고 관리자(캐릭터) ↔ 배경 스크립트가 주고받는 메시지. 이름을 틀리면 타입 검사에서 걸린다. */
export type GuideMsg =
  | { type: "guide:start"; steps: GuideStepItem[]; startIndex: number;   // 패널 → 캐릭터: 안내 시작
      /** EX-03 다음 테스트: 첫 칸(바꿀 칸 1개)만 밝게, 나머지 화면은 흐리게 + '나머지는 그대로(유지)' */
      focus?: boolean }
  | { type: "guide:move"; delta: number }                                  // 패널 → 캐릭터: [이전 칸]·[다음 칸]
  | { type: "guide:progress"; index: number; total: number }               // 캐릭터 → 배경: 몇 번째 칸까지 왔나
  | { type: "guide:closed" };                                              // 캐릭터 → 배경: 집에 돌아감

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
    (e.stages ?? []).forEach((s, i) => {
      if (s.find.length === 0 || !s.say.trim()) problems.push(`${e.id}: ${i + 1}단계의 찾는 방법·말이 비어 있음`);
      for (const f of s.find) {
        const words = Object.values(f).map(String);
        if (words.some((v) => v.trim().startsWith("."))) problems.push(`${e.id}: ${i + 1}단계에 클래스 이름은 쓰지 않음`);
        // 뭉치가 대신 누르는 단계는 게시와 관련된 버튼을 짚으면 안 된다 ('동의하고 게시'는 절대 누르지 않음)
        if (s.by === "buddy" && words.some((v) => /게시|publish/i.test(v))) problems.push(`${e.id}: ${i + 1}단계가 게시 버튼을 누르려 함`);
      }
    });
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

/** EX-03 [다음 테스트 세팅] (v4.2): ② 세팅 목록 전체(all)는 보여 주되, 캐릭터에게는 바꿀 칸 1개 + 새 금액·날짜 + 게시 직전 확인만(send) 보낸다.
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
  const money = all.find((s) => s.entry.auto === "moneyCheck");   // 게시 앞 돈 확인은 다음 테스트에도 늘 거친다
  // 복제한 세트는 지난 금액·지난(이미 끝난) 날짜를 그대로 가져온다 → 새 금액·날짜 칸도 늘 짚는다
  const fresh = ["meta.adset.lifetime_budget", "meta.adset.start_date", "meta.adset.end_date"].map((id) => all.find((s) => s.entry.id === id));
  const send = [target, ...fresh, money, publish].filter((x, i, a): x is GuideStepItem => Boolean(x) && a.indexOf(x) === i);
  return { all, send };
}
