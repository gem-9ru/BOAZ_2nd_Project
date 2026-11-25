// 사이드 패널의 단계 상태 기계. 순수 함수만 둔다 (저장은 storage.ts).
import type { Change, Copy, Research } from "./api";

export type Step = "find" | "copy" | "questions" | "guide" | "wait" | "upload" | "plan" | "fix";

/** 분석 페이지가 4자리 코드로 넘겨주는 '다음에 할 일' (서버 GET /plan/{code}). */
export interface Plan {
  code: string;
  action: string;
  change: Change;
  summary: string[];
  badge: { word: string; prob: number } | null;
  /** v4: 그대로 둘 칸 · 하지 말 것 (분석 페이지 매트릭스) */
  keep?: { field_id: string; path: string; value: string; reason: string }[];
  watch?: { field_id: string; path: string; text: string }[];
  dont?: string[];
}

export interface Target {
  ageMin: number;
  ageMax: number;
  gender: "all" | "female" | "male";
}

export interface Setting {
  fieldId: string;
  label: string;
  value: string;
}

export interface FlowState {
  step: Step;
  product?: string;
  research?: Research;
  target?: Target;
  keywords: string[];
  dropped: string[];          // ① 찾기에서 뺀 키워드 (패널을 다시 열어도 유지)
  copy?: Copy;
  answers: Record<string, string>;
  settings: Setting[];
  /** away: 뭉치가 광고 관리자에 나가 있음 (패널 제목 왼쪽 집이 빔). 닫으면 false → 집으로 돌아옴 */
  guide: { mode: "create" | "edit" | "export"; index: number; away?: boolean } | null;
  endDate?: string;
  plan?: Plan;
}

export type FlowEvent =
  | { type: "researched"; research: Research; product?: string }
  | { type: "toggleKeyword"; keyword: string }
  | { type: "confirmTarget"; target: Target; keywords: string[] }
  | { type: "pickCopy"; copy: Copy }
  | { type: "answer"; id: string; value: string }
  | { type: "unanswer"; id: string }
  | { type: "questionsDone"; settings: Setting[]; endDate?: string }
  | { type: "guideProgress"; index: number }
  | { type: "guideOpened" }
  | { type: "guideClosed" }
  | { type: "guideDone" }
  | { type: "startExport" }
  | { type: "startUpload" }
  | { type: "planLoaded"; plan: Plan }
  | { type: "startFix" }
  | { type: "reset" };

export function initialState(): FlowState {
  return { step: "find", keywords: [], dropped: [], answers: {}, settings: [], guide: null };
}

export function reduce(s: FlowState, ev: FlowEvent): FlowState {
  switch (ev.type) {
    case "toggleKeyword":
      return { ...s, dropped: s.dropped.includes(ev.keyword) ? s.dropped.filter((k) => k !== ev.keyword) : [...s.dropped, ev.keyword] };
    case "researched":
      return { ...s, research: ev.research, product: ev.product ?? s.product, dropped: [] };
    case "confirmTarget":
      return { ...s, target: ev.target, keywords: ev.keywords, step: "copy" };
    case "pickCopy":
      return { ...s, copy: ev.copy, step: "questions" };
    case "answer":
      return { ...s, answers: { ...s.answers, [ev.id]: ev.value } };
    case "unanswer": {
      const { [ev.id]: _drop, ...rest } = s.answers;
      return { ...s, answers: rest };
    }
    case "questionsDone":
      return { ...s, settings: ev.settings, endDate: ev.endDate ?? s.endDate, step: "guide", guide: { mode: "create", index: 0 } };
    case "guideProgress":
      return s.guide ? { ...s, guide: { ...s.guide, index: ev.index } } : s;
    case "guideOpened":
      return s.guide ? { ...s, guide: { ...s.guide, away: true } } : s;
    case "guideClosed":
      return s.guide ? { ...s, guide: { ...s.guide, away: false } } : s;
    case "guideDone":
      return { ...s, step: "wait", guide: null };
    case "startExport":
      return { ...s, guide: { mode: "export", index: 0 } };
    case "startUpload":
      return { ...s, step: "upload", guide: null };
    case "planLoaded":
      return { ...s, plan: ev.plan, step: "plan" };
    case "startFix":
      return { ...s, step: "fix", guide: { mode: "edit", index: 0 } };
    case "reset":
      return initialState();
    default:
      return s;
  }
}
