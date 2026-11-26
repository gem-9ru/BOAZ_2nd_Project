// 찾기·질문 답을 광고 관리자에 넣을 값으로 바꾸는 순수 함수들.
import type { Copy, Field } from "./api";
import type { Setting, Target } from "./flow";

const META_MIN_AGE = 18;
const META_MAX_AGE = 65;

/** 네이버 연령대("30") → 메타 연령 범위. 18세부터는 이 도구 선택 (메타는 한국에서 만 14세부터 광고 가능, 18세 미만은 상세 타게팅 불가 — 메타 도움말 229435355723442, 2026-11-26 확인). 65는 메타의 '65세 이상'. */
export function ageGroupToRange(group: string): { ageMin: number; ageMax: number } {
  const start = Number(group);
  return { ageMin: Math.max(start, META_MIN_AGE), ageMax: Math.min(start + 9, META_MAX_AGE) };
}

/** 광고를 보여 줄 나이대: 가장 많이 찾는 나이대에서 시작해, 바로 옆 나이대가 AGE_SPAN_MIN 이상이면서
 *  가장 많은 나이대의 절반 이상이면 넓힌다 (30대 23% · 40대 29% · 50대 25% → 30~50대). 두 옆 중 큰 쪽부터. */
export const AGE_SPAN_MIN = 0.15;
const AGE_GROUPS = ["10", "20", "30", "40", "50", "60"];

export function ageSpan(ages: Record<string, number>): { groups: string[]; ageMin: number; ageMax: number } {
  const have = AGE_GROUPS.filter((a) => a in ages);
  if (have.length === 0) return { groups: ["30"], ...ageGroupToRange("30") };
  const share = (a?: string) => (a ? ages[a] ?? 0 : 0);
  const top = have.reduce((b, a) => (share(a) > share(b) ? a : b));
  const ok = (a?: string) => !!a && share(a) >= AGE_SPAN_MIN && share(a) >= share(top) / 2;
  let lo = AGE_GROUPS.indexOf(top), hi = lo;
  for (;;) {
    const left = AGE_GROUPS[lo - 1], right = AGE_GROUPS[hi + 1];
    const pick = [left, right].filter(ok).sort((x, y) => share(y) - share(x))[0];
    if (!pick) break;
    if (pick === left) lo -= 1; else hi += 1;
  }
  const groups = AGE_GROUPS.slice(lo, hi + 1);
  return { groups, ageMin: ageGroupToRange(groups[0]!).ageMin, ageMax: ageGroupToRange(groups[groups.length - 1]!).ageMax };
}

/** ['30','40','50'] → '30~50대', ['40'] → '40대' */
export function ageSpanLabel(groups: string[]): string {
  return groups.length > 1 ? `${groups[0]}~${groups[groups.length - 1]}대` : `${groups[0]}대`;
}

/** 여성 비중 → 성별 타겟 (60% 이상이면 여성, 40% 이하면 남성, 그 사이는 전체). */
export function genderFrom(female: number): Target["gender"] {
  return female >= 0.6 ? "female" : female <= 0.4 ? "male" : "all";
}

export const GENDER_LABEL: Record<Target["gender"], string> = { female: "여성", male: "남성", all: "전체" };


/** 광고 관리자 화면 순서 (캠페인 → 광고 세트 → 광고). 캐릭터 안내도 이 순서. */
export const SETTING_ORDER = [
  "meta.campaign.objective",
  "meta.campaign.special_category",
  "meta.campaign.budget_strategy",   // 돈: 캠페인 예산이면 메타가 하루 예산으로 계속 쓴다 → 광고 세트 예산으로
  "meta.adset.conversion_location",
  "meta.adset.lifetime_budget",   // 광고 관리자 '예산 및 일정': 예산이 날짜보다 위
  "meta.adset.start_date",
  "meta.adset.end_date",
  "meta.adset.location",
  "meta.adset.age_gender",
  "meta.pre.fb_page",
  "meta.pre.ig_account",
  "meta.ad.format",
  "meta.ad.media",
  "meta.ad.website_url",   // 광고 만들기 창 '크리에이티브 설정' 단계의 '소스 URL' (문구보다 앞, 2026-11-26 실제 화면)
  "meta.creative.copy.text",
  "meta.creative.copy.headline",
  "meta.money_check",   // 게시 앞 돈 확인 (총예산 종류·금액·종료 날짜를 화면에서 다시 읽음)
];

/** 묻지 않고 앞 단계에서 채우는 칸: 목표(트래픽 고정), 연령·성별(① 찾기). */
const PREFILLED = new Set(["meta.campaign.objective", "meta.adset.age_gender"]);
const OBJECTIVE = "트래픽";

/** 시작 전 준비물 화면에서 묻는 칸 (meta_fields.yaml stage '사전 점검'). ② 세팅에서는 다시 묻지 않는다 */
export const PREP_STAGE = "사전 점검";

export function prepFields(fields: Field[]): Field[] {
  return fields.filter((f) => f.stage === PREP_STAGE);
}

/** 꼭 있어야 하는 준비물 중 아직 안 된 것의 이름 (답이 없거나 첫 답 '있어요' 등이 아님) */
export function prepMissing(fields: Field[], answers: Record<string, string>): string[] {
  return prepFields(fields).filter((f) => f.required && answers[f.id] !== f.options?.[0]).map((f) => f.label);
}

/** 준비물에서 사진을 확인했으니 ② 세팅에서 다시 묻지 않는 칸 (값은 기본값, 사진은 사장님이 올림) */
const NOT_ASKED = new Set(["meta.ad.media"]);

/** 준비물에서 받은 상품·인스타 주소 → 광고를 누르면 갈 곳과 그 주소 (② 세팅에서 다시 묻지 않게) */
export function routeFromPrep(answers: Record<string, string>): Record<string, string> {
  const store = answers["meta.pre.store_url"], insta = answers["meta.pre.insta_url"], pick = answers["meta.pre.store_product"];
  if (pick === "올렸어요" && store) return { "meta.adset.conversion_location": "스토어 상품 페이지", "meta.ad.website_url": store };
  if (pick && pick !== "올렸어요" && insta) return { "meta.adset.conversion_location": "인스타그램 프로필", "meta.ad.website_url": insta };
  return {};
}

export function askedFields(fields: Field[], answers: Record<string, string> = {}): Field[] {
  const follow = new Set(fields.flatMap((f) => {                                   // 다른 질문에서 이어 받는 칸
    const to = f.then_ask?.field;
    return !to ? [] : typeof to === "string" ? [to] : Object.values(to);
  }));
  const routed = routeFromPrep(answers);
  return fields.filter((f) => !PREFILLED.has(f.id) && !NOT_ASKED.has(f.id) && !follow.has(f.id) && !(f.id in routed) && f.stage !== PREP_STAGE);
}

/** 메타가 받는 하루 최소 예산 약값 (원) — 오븐로그 11/17 사례, 서버 rules.yaml loop.meta_daily_min과 같은 값 (설계서 v4.2 EX-01 ④). */
export const META_DAILY_MIN = 1336;

/** '3만 원' · '25,000원' · '10000' → 원. 못 읽으면 null. */
export function parseWon(text: string | undefined): number | null {
  const t = (text ?? "").replace(/[,\s원]/g, "");
  const n = t.endsWith("만") ? Number(t.slice(0, -1)) * 10000 : Number(t);
  return t && Number.isFinite(n) && n > 0 ? n : null;
}

/** 광고 기간 일수 (시작일·종료일 모두 셈). */
export function scheduleDays(s: Schedule): number {
  return Math.round((Date.parse(s.end) - Date.parse(s.start)) / 86400000) + 1;
}

/** 이 기간에 광고가 나가려면 세트마다 적어도 넣어야 할 총예산 (하루 최소 × 기간, 백 원 단위 올림). */
export function minBudget(days: number): number {
  return Math.ceil((META_DAILY_MIN * days) / 100) * 100;
}

/** 날짜 → YYYY-MM-DD (그 컴퓨터 날짜 기준). */
export function isoDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** "7일" → 오늘 포함 7일째 날짜 (YYYY-MM-DD). 날짜 직접 정하기·scheduleDays처럼 시작일·종료일을 모두 센다. */
export function endDateFrom(choice: string, today: Date = new Date()): string {
  const days = parseInt(choice, 10) || 14;
  return isoDate(new Date(today.getFullYear(), today.getMonth(), today.getDate() + days - 1));
}

/** 시작일·종료일 (YYYY-MM-DD). 시각(HH:MM)은 사장님이 정했을 때만 — 없으면 광고 관리자 기본 시각 그대로 */
export interface Schedule { start: string; end: string; startTime?: string; endTime?: string }

/** 광고 기간 답 → 시작일·종료일. "14일"은 오늘부터, "2026-12-01 09:00~2026-12-14"는 사장님이 직접 고른 그대로 (시각은 선택). */
export function scheduleFrom(choice: string, today: Date = new Date()): Schedule {
  const m = /^(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?~(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?$/.exec(choice.trim());
  if (m) return { start: m[1]!, end: m[3]!, ...(m[2] ? { startTime: m[2] } : {}), ...(m[4] ? { endTime: m[4] } : {}) };
  return { start: isoDate(today), end: endDateFrom(choice, today) };
}

export function buildSettings(fields: Field[], answers: Record<string, string>, target: Target, copy: Copy, schedule: Schedule): Setting[] {
  const label = (id: string) => fields.find((f) => f.id === id)?.label ?? id;
  const value: Record<string, string> = {
    "meta.ad.media": fields.find((f) => f.id === "meta.ad.media")?.default ?? "",
    ...routeFromPrep(answers),
    ...answers,
    "meta.campaign.objective": OBJECTIVE,
    "meta.adset.age_gender": `${target.ageMin}–${target.ageMax}세 · ${GENDER_LABEL[target.gender]}`,
    "meta.adset.start_date": schedule.startTime ? `${schedule.start} ${schedule.startTime}` : schedule.start,
    "meta.adset.end_date": schedule.endTime ? `${schedule.end} ${schedule.endTime}` : schedule.end,
    "meta.creative.copy.text": copy.primary_text,
    "meta.creative.copy.headline": copy.headline,
    "meta.campaign.budget_strategy": "광고 세트 예산",
    "meta.money_check": answers["meta.adset.lifetime_budget"] ?? "",   // 확인할 총예산 금액
  };
  const extra: Record<string, string> = { "meta.creative.copy.text": "기본 문구", "meta.creative.copy.headline": "제목", "meta.adset.start_date": "시작 날짜",
    "meta.campaign.budget_strategy": "예산 전략", "meta.money_check": "게시 전 돈 확인" };
  return SETTING_ORDER.map((id) => ({ fieldId: id, label: extra[id] ?? label(id), value: value[id] ?? "" }));
}
