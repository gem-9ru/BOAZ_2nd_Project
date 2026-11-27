// 사이드 패널의 단계 상태 기계. 순수 함수만 둔다 (저장은 storage.ts).
import type { Change, Copy, Research, Segment } from "./api";

export type Step = "prep" | "find" | "copy" | "questions" | "guide" | "wait" | "upload" | "plan";

/** 분석 페이지가 4자리 코드로 넘겨주는 '다음에 할 일' (서버 GET /plan/{code}). */
export interface Plan {
  code: string;
  action: string;
  change: Change;
  summary: string[];
  badge: { word: string; prob: number } | null;
  /** v4: 그대로 둘 칸 · 하지 말 것 (분석 페이지 매트릭스) */
  keep?: { field_id: string; path: string; value: string; reason: string }[];
  watch?: { field_id: string; path: string; text: string; need_per_set?: number }[];
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
  /** 지금 손님 결과를 찾을 때 이미 뺀 말 ([뺀 말을 빼고 손님 다시 보기] 띠를 다시 본 뒤엔 숨기려고, 화면 검토 5) */
  droppedApplied?: string[];
  copy?: Copy;
  category?: string;          // 고른 분야 코드
  segment?: Segment;          // 고른 손님 무리
  strengths?: string[];       // 고른 좋은 점
  answers: Record<string, string>;
  /** [← 이전 질문]·[② 답 바꾸기]로 지운 답 → 그 질문을 다시 볼 때 칸을 미리 채운다 (화면 검토 8) */
  prevAnswers?: Record<string, string>;
  /** 할 일 체크리스트에서 사장님이 체크한 줄 (질문 id → 줄 번호). 스토어 개설은 며칠 걸릴 수 있어 저장해 둔다 */
  checks: Record<string, number[]>;
  settings: Setting[];
  /** away: 뭉치가 광고 관리자에 나가 있음 (패널 제목 왼쪽 집이 빔). 닫으면 false → 집으로 돌아옴 */
  /** next: EX-03 [다음 테스트 세팅] — 이 칸만 '지금', 나머지는 이전 값으로 끝난 칸 (v4.2) */
  guide: { mode: "create" | "edit" | "export"; index: number; away?: boolean; next?: string } | null;
  /** 광고 시작일 (YYYY-MM-DD). 오늘보다 뒤면 예약 광고 */
  startDate?: string;
  endDate?: string;
  plan?: Plan;
  /** 이미 받은 분석 페이지 보내기 (분석 탭을 오갈 때마다 테스트안을 다시 받아 진행 중인 화면을 되돌리지 않게, 화면 검토 23) */
  planSent?: string;
  /** [다음 테스트 세팅]을 누르기 전 값 — [결과 화면으로 돌아가기]면 되돌린다. 게시까지 끝내면(guideDone) 버린다 */
  beforeNext?: { settings: Setting[]; startDate?: string; endDate?: string };
  /** 시작 전 준비물에서 아직 안 된 꼭 필요한 것 (이름). 하나라도 있으면 [광고 관리자 열기]를 막는다 */
  prepMissing?: string[];
  /** 저장 차례: 배경 스크립트가 뭉치 진행을 쓸 때마다 1씩 올린다 (패널이 옛 상태로 진행을 덮어쓰지 않게, 감사 7) */
  rev?: number;
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
  /** 안내 목록에서 ② 답(기간·금액·지역·클릭 주소 등)을 다시 정하기. 준비물 답은 그대로 (화면 검토 9) */
  | { type: "editAnswers" }
  | { type: "toggleCheck"; key: string; index: number }
  | { type: "questionsDone"; settings: Setting[]; startDate?: string; endDate?: string }
  | { type: "guideProgress"; index: number }
  | { type: "guideOpened" }
  | { type: "guideClosed" }
  | { type: "guideDone" }
  | { type: "startExport" }
  /** 결과 내보내기 안내를 그만 보기 (파일을 직접 받았거나 뭉치를 닫았을 때) → 하던 화면(기다리기·코드 넣기)으로 */
  | { type: "closeExport" }
  | { type: "startUpload" }
  /** sent: 분석 페이지 [확장 프로그램으로 보내기] 표시 (주소의 send=). 같은 보내기를 다시 받지 않게 기억한다 */
  | { type: "planLoaded"; plan: Plan; sent?: string }
  /** startDate·endDate·budget: 다음 테스트의 새 날짜(YYYY-MM-DD)와 세트당 총예산('5,400원'). 지난 날짜·금액을 그대로 쓰지 않게 */
  | { type: "startNextTest"; fieldId: string; label: string; value: string; startDate?: string; endDate?: string; budget?: string }
  | { type: "backToPlan" }
  | { type: "prepDone"; missing: string[] }
  | { type: "openPrep" }
  | { type: "reset" };

const BUDGET_ID = "meta.adset.lifetime_budget";
const CLICK_TO = "meta.adset.conversion_location";
const CLICK_URL = "meta.ad.website_url";

export function initialState(): FlowState {
  return { step: "prep", keywords: [], dropped: [], answers: {}, checks: {}, settings: [], guide: null };
}

export function reduce(s: FlowState, ev: FlowEvent): FlowState {
  switch (ev.type) {
    case "toggleKeyword":
      return { ...s, dropped: s.dropped.includes(ev.keyword) ? s.dropped.filter((k) => k !== ev.keyword) : [...s.dropped, ev.keyword] };
    case "researched":
      return { ...s, research: ev.research, product: ev.product ?? s.product, dropped: ev.dropped ?? [], droppedApplied: ev.dropped ?? [], segment: undefined,
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
      const { [ev.id]: was, ...rest } = s.answers;
      return { ...s, answers: rest, prevAnswers: was === undefined ? s.prevAnswers : { ...s.prevAnswers, [ev.id]: was } };
    }
    case "editAnswers": {
      // 준비물(meta.pre.*) 답만 두고 ② 질문을 처음부터 다시 (지운 답은 칸 미리 채우기로). 날짜도 오늘 기준으로 다시 정해진다
      const keep = Object.fromEntries(Object.entries(s.answers).filter(([k]) => k.startsWith("meta.pre.")));
      const gone = Object.fromEntries(Object.entries(s.answers).filter(([k]) => !k.startsWith("meta.pre.")));
      return { ...s, answers: keep, prevAnswers: { ...s.prevAnswers, ...gone }, step: "questions", guide: null };
    }
    case "toggleCheck": {
      const got = s.checks[ev.key] ?? [];
      const next = got.includes(ev.index) ? got.filter((i) => i !== ev.index) : [...got, ev.index].sort((a, b) => a - b);
      return { ...s, checks: { ...s.checks, [ev.key]: next } };
    }
    case "questionsDone":
      return { ...s, settings: ev.settings, startDate: ev.startDate ?? s.startDate, endDate: ev.endDate ?? s.endDate,
        step: "guide", guide: { mode: "create", index: 0 } };
    case "guideProgress":
      return s.guide ? { ...s, guide: { ...s.guide, index: ev.index } } : s;
    case "guideOpened":
      return s.guide ? { ...s, guide: { ...s.guide, away: true } } : s;
    case "guideClosed":
      return s.guide ? { ...s, guide: { ...s.guide, away: false } } : s;
    case "guideDone":
      return { ...s, step: "wait", guide: null, beforeNext: undefined };
    case "startExport":
      return { ...s, guide: { mode: "export", index: 0 } };
    case "closeExport":
      return s.guide?.mode === "export" ? { ...s, guide: null } : s;
    case "startUpload":
      return { ...s, step: "upload", guide: null };
    case "planLoaded":
      // 안내(내보내기 등)가 남아 있으면 닫는다: 결과 화면과 안내 화면이 한 화면에 겹치지 않게
      return { ...s, plan: ev.plan, step: "plan", guide: null, planSent: ev.sent ?? s.planSent };
    case "startNextTest": {
      // ↺ 루프: EX-01 ② 세팅 목록으로 돌아가되, 바꿀 칸 1개만 새 값으로 (게시는 사장님이 직접)
      // 분석이 '일일 예산'을 바꾸라고 해도 이 도구는 총예산만 쓴다 → 총예산 칸을 새 금액으로 (하루 예산 안내가 총예산 확인과 부딪히지 않게, 화면 검토 18)
      const daily = ev.fieldId === "meta.adset.daily_budget";
      const fieldId = daily ? BUDGET_ID : ev.fieldId;
      const value = daily ? ev.budget ?? s.settings.find((x) => x.fieldId === BUDGET_ID)?.value ?? "" : ev.value;
      const has = s.settings.some((x) => x.fieldId === fieldId);
      const fresh: Record<string, string | undefined> = { "meta.adset.start_date": ev.startDate, "meta.adset.end_date": ev.endDate,
        "meta.adset.lifetime_budget": ev.budget, "meta.money_check": ev.budget };
      const settings = (has ? s.settings : [...s.settings, { fieldId, label: ev.label, value }])
        .map((x) => (x.fieldId === fieldId ? { ...x, value } : fresh[x.fieldId] ? { ...x, value: fresh[x.fieldId]! } : x));
      return { ...s, settings, startDate: ev.startDate ?? s.startDate, endDate: ev.endDate ?? s.endDate,
        beforeNext: s.beforeNext ?? { settings: s.settings, startDate: s.startDate, endDate: s.endDate },
        step: "guide", guide: { mode: "create", index: 0, next: fieldId } };
    }
    case "backToPlan":
      return s.beforeNext ? { ...s, ...s.beforeNext, beforeNext: undefined, step: "plan", guide: null } : s;
    case "prepDone": {
      // 처음이면 ① 찾기로. 세팅까지 갔다가 준비물을 다시 답했으면: 클릭 주소 질문만 새 준비물 답으로 다시 묻고 세팅 목록을 새로 만든다
      // (예전 주소가 그대로 광고에 들어가지 않게, 화면 검토 2)
      if (!s.settings.length) return { ...s, prepMissing: ev.missing, step: "find" };
      const { [CLICK_TO]: _c, [CLICK_URL]: _u, ...answers } = s.answers;
      return { ...s, prepMissing: ev.missing, answers, step: "questions", guide: null };
    }
    case "openPrep":
      return { ...s, step: "prep" };
    case "reset":
      // rev를 지금 시각으로: 저장소에 남은 옛 진행(step·guide)이 '더 새 것'으로 이기지 않게. 패널이 배경의 마지막 쓰기를
      // 아직 못 받았어도(rev가 뒤처져도) 시각이 늘 더 크다. 배경은 저장된 rev에 1씩 더하니 그 뒤 순서도 그대로 (화면 검토 21)
      return { ...initialState(), rev: Math.max((s.rev ?? 0) + 1, Date.now()) };
    default:
      return s;
  }
}
