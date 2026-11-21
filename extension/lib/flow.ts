// 사이드 패널의 단계 상태 기계. 순수 함수만 둔다 (저장은 storage.ts).
import type { Analysis, Copy, Research } from "./api";

export type Step = "find" | "copy" | "questions" | "guide" | "wait" | "upload" | "result" | "fix";

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
  copy?: Copy;
  answers: Record<string, string>;
  settings: Setting[];
  guide: { mode: "create" | "edit" | "export"; index: number } | null;
  endDate?: string;
  result?: Analysis;
}

export type FlowEvent =
  | { type: "researched"; research: Research; product?: string }
  | { type: "confirmTarget"; target: Target; keywords: string[] }
  | { type: "pickCopy"; copy: Copy }
  | { type: "answer"; id: string; value: string }
  | { type: "questionsDone"; settings: Setting[]; endDate?: string }
  | { type: "guideProgress"; index: number }
  | { type: "guideDone" }
  | { type: "startExport" }
  | { type: "startUpload" }
  | { type: "analyzed"; result: Analysis }
  | { type: "startFix" }
  | { type: "reset" };

export function initialState(): FlowState {
  return { step: "find", keywords: [], answers: {}, settings: [], guide: null };
}

export function reduce(s: FlowState, ev: FlowEvent): FlowState {
  switch (ev.type) {
    case "researched":
      return { ...s, research: ev.research, product: ev.product ?? s.product };
    case "confirmTarget":
      return { ...s, target: ev.target, keywords: ev.keywords, step: "copy" };
    case "pickCopy":
      return { ...s, copy: ev.copy, step: "questions" };
    case "answer":
      return { ...s, answers: { ...s.answers, [ev.id]: ev.value } };
    case "questionsDone":
      return { ...s, settings: ev.settings, endDate: ev.endDate ?? s.endDate, step: "guide", guide: { mode: "create", index: 0 } };
    case "guideProgress":
      return s.guide ? { ...s, guide: { ...s.guide, index: ev.index } } : s;
    case "guideDone":
      return { ...s, step: "wait", guide: null };
    case "startExport":
      return { ...s, guide: { mode: "export", index: 0 } };
    case "startUpload":
      return { ...s, step: "upload", guide: null };
    case "analyzed":
      return { ...s, result: ev.result, step: "result" };
    case "startFix":
      return { ...s, step: "fix", guide: { mode: "edit", index: 0 } };
    case "reset":
      return initialState();
    default:
      return s;
  }
}
