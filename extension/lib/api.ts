// 서버(localhost:8000) 응답 모양. 서버 server/app.py와 같은 이름을 쓴다.

export interface Research {
  headline: string;
  keywords: { keyword: string; total_qc: number }[];
  audience: { keyword: string; female: number; ages: Record<string, number>; top_age: string } | null;
  fetched: string;
  source: "live" | "cache";
  /** 부분별 받은 날: product = 이 상품의 검색어·연령, baseline = 분야 평균 */
  sources?: { part: "product" | "baseline"; label: string; fetched: string; today: boolean }[];
  /** 광고에서 뺄 말 (만들기·매장·관련 낮음, 최대 20개) */
  negatives?: string[];
  notice: string | null;
  /** 아래 넷은 모두 선택: 예전 저장 상태도 그대로 열린다 */
  category?: (Category & { guessed: boolean }) | null;
  categories?: Category[];
  /** 분야를 못 정했을 때 가까운 분야 후보 (많은 순) */
  category_candidates?: Category[];
  segments?: Segment[];
  modifiers?: Modifier[];
  /** 상품 이름 그대로의 월 검색 수·찾는 사람 (분야를 모르면 audience 없음) */
  product_stats?: ProductStats | null;
}

export interface ProductStats {
  keyword: string;
  total_qc: number;
  /** 모바일 비중 0~1 */
  mobile: number | null;
  audience: { female: number; ages: Record<string, number>; top_age: string } | null;
  /** 몇 월에 많이 찾나 (쇼핑인사이트 클릭, 가장 많은 달 = 100) */
  trend?: { monthly: Record<string, number>; peak_month: number | null; seasonal: boolean } | null;
}

export interface Category { code: string; name: string }
export interface Segment {
  intent: "선물·답례" | "시즌" | "상품";
  label: string;
  keywords: string[];
  total_qc: number;
  lead: string;
  audience: { female: number; ages: Record<string, number>; top_age: string } | null;
  trend: { monthly: Record<string, number>; peak_month: number | null; seasonal: boolean } | null;
  trend_source: "search" | "shopping" | null;
  line: string;
}
export interface Modifier { word: string; group: string; total_qc: number; examples: string[] }

export interface Copy {
  primary_text: string;
  headline: string;
  /** 문구에 쓴 근거 낱말 */
  basis?: string[];
}

export interface Field {
  id: string;
  kind: "question" | "precheck";
  label: string;
  ask: string;
  options: string[] | null;
  default: string | null;
  why: string;
  /** 이 답을 고르면 바로 넘어가지 않고 보여 줄 할 일 (예: 페이스북 페이지가 없어요 → 만들기 링크) */
  help?: Record<string, OptionHelp> | null;
  /** 고른 뒤 같은 자리에서 이어 받는 주소 칸 (그 칸은 따로 묻지 않음). say·prefill은 고른 답별 */
  then_ask?: {
    /** 받은 주소를 넣을 칸 (답별로 다르면 답 → 칸) */
    field: string | Record<string, string>;
    say: Record<string, string>;
    /** 답 → 미리 채울 값 틀. 목록이면 다 채워지는 첫 틀 */
    prefill?: Record<string, string | string[]>;
    /** 상품 페이지 주소가 없을 때 바꿀 답 (예: 스토어 상품 페이지 → 인스타그램 프로필) */
    none?: Record<string, string>;
  } | null;
  /** 앞 답에 따라 권장 답을 바꿈: {앞 칸 id: {앞 답: 권장 답}} */
  default_if?: Record<string, Record<string, string>> | null;
  /** 앞 답에 따라 질문 아래에 붙일 한 줄: {앞 칸 id: {앞 답: 안내}} */
  note_if?: Record<string, Record<string, string>> | null;
  /** 선택지 밖 직접 정하기. dates: 시작일·종료일 (답 'yyyy-mm-dd~yyyy-mm-dd'),
   *  area: custom_for 답을 고르면 가게 주소·반경 (답 '가게 주변 5km · 서울 마포구 망원동') */
  custom?: "dates" | "area" | null;
  /** custom 칸을 여는 답 (area). 없으면 [날짜 직접 정하기]처럼 따로 버튼 */
  custom_for?: string[] | null;
  /** 고른 답 대신 세팅에 넣을 값 (예: 택배로 보내요 → 전국 (택배)) */
  answer_as?: Record<string, string> | null;
}

/** 할 일 체크리스트 한 줄. hint: keywords → ① 찾기에서 고른 검색어 한 줄 */
export interface HelpStep {
  text: string;
  link?: string;
  url?: string;
  hint?: "keywords";
}

export interface OptionHelp {
  say: string;
  /** 링크 하나 (steps가 없을 때) */
  link?: string;
  url?: string;
  /** 할 일이 여러 개면 체크리스트 */
  steps?: HelpStep[];
  /** 다 했을 때 누를 버튼과 그때 기록할 답 */
  done: string;
  done_value: string;
  /** 나중에 할게요: 고른 답 그대로 넘어감 */
  later: string;
}

export interface PresetField {
  id: string;
  label: string;
  default: string;
  why: string;
}

export interface Change {
  field_id: string;
  label: string;
  new: string;
  note: string;
  /** v4: 광고 관리자 위치 ("광고 › 형식·미디어"), 지금 값, 확실도, 다음 테스트 체크리스트 */
  path?: string;
  now?: string | null;
  certainty?: { level: "채택" | "유력" | "보류"; label: string; why: string };
  checklist?: string[];
}


/** 서버 주소: 빌드할 때 WXT_API_BASE로 정한다 (배포: https://boaz-ad-assistant.gem-9ru.com). 없으면 내 컴퓨터 서버. */
export function apiBase(fromBuild: string | undefined): string {
  return (fromBuild || "http://localhost:8000").replace(/\/+$/, "");
}
export const BASE = apiBase(import.meta.env.WXT_API_BASE as string | undefined);

/** 서버가 꺼져 있거나 닿지 않음. */
export class ServerDown extends Error {
  constructor() {
    super("도우미 서버에 연결할 수 없어요. 서버를 켠 뒤 다시 시도해 주세요.");
  }
}

/** 서버는 켜져 있지만 처리하다 문제가 생김 (5xx 등). */
export class ServerError extends Error {
  constructor() {
    super("서버에서 문제가 생겼어요. 잠시 뒤 다시 시도해 주세요.");
  }
}

/** 서버가 입력을 거절함 (message는 사장님께 그대로 보여 줘도 되는 문장). */
export class BadInput extends Error {}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ServerDown();
  }
  const body = await res.json().catch(() => ({}));
  if (res.status === 400 || res.status === 404) throw new BadInput(body.error ?? body.detail ?? "입력을 확인해 주세요.");
  if (!res.ok) throw new ServerError();
  return body as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function research(product: string, opts: { seeds?: string[]; category?: string; keywords?: string[] } = {}): Promise<Research> {
  const body: Record<string, unknown> = { product };
  if (opts.seeds) body.seeds = opts.seeds;
  if (opts.category) body.category = opts.category;
  if (opts.keywords) body.keywords = opts.keywords;
  return call("/research", json(body));
}

export function copies(body: { product: string; strengths: string[]; keywords: string[]; avoid: string[];
  segment?: { intent: string; label: string; peak_month?: number | null } }): Promise<{ copies: Copy[]; source: string }> {
  return call("/copies", json(body));
}

/** 나이대마다 그 안의 여성 비중 (막대를 여성·남성으로 나눠 그리기). 같은 말은 한 번만 묻는다. */
const splitCache = new Map<string, Promise<Record<string, number>>>();
export function audienceSplit(keyword: string, category: string, ages: Record<string, number>): Promise<Record<string, number>> {
  const key = `${category}|${keyword}`;
  let p = splitCache.get(key);
  if (!p) {
    p = call<{ female_by_age: Record<string, number> }>("/audience/split", json({ keyword, category, ages }))
      .then((r) => r.female_by_age ?? {})
      .catch(() => { splitCache.delete(key); return {}; });
    splitCache.set(key, p);
  }
  return p;
}

export function fields(): Promise<{ fields: Field[]; defaults: PresetField[] }> {
  return call("/fields");
}


export const ANALYSIS_PAGE = `${BASE}/analysis`;

/** 분석 페이지의 4자리 코드 → 다음에 할 일. */
export function plan(code: string): Promise<import("./flow").Plan> {
  return call(`/plan/${encodeURIComponent(code)}`);
}

export interface AssistantAlert { level: "block" | "warn" | "info"; text: string; todo: string }

/** 광고 어시스턴트: 질문이 없으면 첫 말 + 추천 질문(분석 페이지 단계면 그 단계 알림도), 있으면 분석 결과로 설명 (EX-03). */
export function askAssistant(code: string, step: string, question?: string): Promise<{ message: string; suggestions?: string[]; alerts?: AssistantAlert[] }> {
  return call("/assistant", json({ code, step, question }));
}

/** 세팅값(칸 id → 값)을 서버에 맡기고 키만 받는다. 분석 페이지 주소에는 이 키만 붙인다 (값은 URL에 넣지 않음). */
export function keepSettings(settings: Record<string, string>): Promise<{ key: string; count: number }> {
  return call("/settings", json({ settings }));
}

/** 분석 페이지 주소: 세팅값을 맡겼으면 #s=키 (# 뒤는 서버 기록에 남지 않음). 실패하면 그냥 연다 → 분석 페이지가 5문항으로 묻는다. */
export async function analysisPageUrl(settings: Record<string, string>): Promise<string> {
  if (!Object.keys(settings).length) return ANALYSIS_PAGE;
  try {
    const { key } = await keepSettings(settings);
    return `${ANALYSIS_PAGE}#s=${encodeURIComponent(key)}`;
  } catch {
    return ANALYSIS_PAGE;
  }
}
