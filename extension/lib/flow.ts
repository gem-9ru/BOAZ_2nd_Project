// 사이드 패널의 단계 상태 기계. 순수 함수만 둔다 (저장은 storage.ts).
import type { Change, Copy, Research, Segment } from "./api";

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
  category?: string;          // 고른 분야 코드
  segment?: Segment;          // 고른 손님 무리
  strengths?: string[];       // 고른 좋은 점
  answers: Record<string, string>;
  settings: Setting[];
  /** away: 뭉치가 광고 관리자에 나가 있음 (패널 제목 왼쪽 집이 빔). 닫으면 false → 집으로 돌아옴 */
  /** next: EX-03 [다음 테스트 세팅] — 이 칸만 '지금', 나머지는 이전 값으로 끝난 칸 (v4.2) */
  guide: { mode: "create" | "edit" | "export"; index: number; away?: boolean; next?: string } | null;
  endDate?: string;
  plan?: Plan;
}

export type FlowEvent =
  /** dropped: 같은 상품을 다시 찾을 때(분야 바꾸기·이 말로 다시 찾기) 사장님이 뺀 말을 그대로 둔다 */
  | { type: "researched"; research: Research; product?: string; dropped?: string[] }
  | { type: "toggleKeyword"; keyword: string }
  | { type: "pickCategory"; category: string }
  | { type: "pickSegment"; segment: Segment }
  | { type: "confirmTarget"; target: Target; keywords: string[]; segment?: Segment }
  | { type: "pickCopy"; copy: Copy; strengths?: string[] }
  | { type: "editFind" }
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
  | { type: "startNextTest"; fieldId: string; label: string; value: string }
  | { type: "reset" };

export function initialState(): FlowState {
  return { step: "find", keywords: [], dropped: [], answers: {}, settings: [], guide: null };
}

export function reduce(s: FlowState, ev: FlowEvent): FlowState {
  switch (ev.type) {
    case "toggleKeyword":
      return { ...s, dropped: s.dropped.includes(ev.keyword) ? s.dropped.filter((k) => k !== ev.keyword) : [...s.dropped, ev.keyword] };
    case "researched":
      return { ...s, research: ev.research, product: ev.product ?? s.product, dropped: ev.dropped ?? [], segment: undefined,
        category: ev.research.category?.code };
    case "pickCategory":
      return { ...s, category: ev.category, segment: undefined };
    case "pickSegment":
      return { ...s, segment: ev.segment };
    case "confirmTarget":
      return { ...s, target: ev.target, keywords: ev.keywords, segment: ev.segment ?? s.segment, step: "copy" };
    case "pickCopy":
      return { ...s, copy: ev.copy, strengths: ev.strengths ?? s.strengths, step: "questions" };
    case "editFind":
      return { ...s, step: "find" };
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
    case "startNextTest": {
      // ↺ 루프: EX-01 ② 세팅 목록으로 돌아가되, 바꿀 칸 1개만 새 값으로 (게시는 사장님이 직접)
      const has = s.settings.some((x) => x.fieldId === ev.fieldId);
      const settings = has
        ? s.settings.map((x) => (x.fieldId === ev.fieldId ? { ...x, value: ev.value } : x))
        : [...s.settings, { fieldId: ev.fieldId, label: ev.label, value: ev.value }];
      return { ...s, settings, step: "guide", guide: { mode: "create", index: 0, next: ev.fieldId } };
    }
    case "reset":
      return initialState();
    default:
      return s;
  }
}
