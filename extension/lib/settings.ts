// 찾기·질문 답을 광고 관리자에 넣을 값으로 바꾸는 순수 함수들.
import type { Copy, Field } from "./api";
import type { Setting, Target } from "./flow";

const META_MIN_AGE = 18;
const META_MAX_AGE = 65;

/** 네이버 연령대("30") → 메타 연령 범위 (메타는 18~65세). */
export function ageGroupToRange(group: string): { ageMin: number; ageMax: number } {
  const start = Number(group);
  return { ageMin: Math.max(start, META_MIN_AGE), ageMax: Math.min(start + 9, META_MAX_AGE) };
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
  "meta.adset.conversion_location",
  "meta.adset.end_date",
  "meta.adset.location",
  "meta.adset.age_gender",
  "meta.pre.fb_page",
  "meta.pre.ig_account",
  "meta.ad.format",
  "meta.ad.media",
  "meta.creative.copy.text",
  "meta.creative.copy.headline",
  "meta.ad.website_url",
];

/** 묻지 않고 앞 단계에서 채우는 칸: 목표(트래픽 고정), 연령·성별(① 찾기). */
const PREFILLED = new Set(["meta.campaign.objective", "meta.adset.age_gender"]);
const OBJECTIVE = "트래픽";

export function askedFields(fields: Field[]): Field[] {
  return fields.filter((f) => !PREFILLED.has(f.id));
}

/** "7일" → 오늘부터 7일 뒤 날짜 (YYYY-MM-DD). */
export function endDateFrom(choice: string, today: Date = new Date()): string {
  const days = parseInt(choice, 10) || 14;
  const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() + days);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function buildSettings(fields: Field[], answers: Record<string, string>, target: Target, copy: Copy, endDate: string): Setting[] {
  const label = (id: string) => fields.find((f) => f.id === id)?.label ?? id;
  const value: Record<string, string> = {
    ...answers,
    "meta.campaign.objective": OBJECTIVE,
    "meta.adset.age_gender": `${target.ageMin}–${target.ageMax}세 · ${GENDER_LABEL[target.gender]}`,
    "meta.adset.end_date": endDate,
    "meta.creative.copy.text": copy.primary_text,
    "meta.creative.copy.headline": copy.headline,
  };
  const extra: Record<string, string> = { "meta.creative.copy.text": "기본 문구", "meta.creative.copy.headline": "제목" };
  return SETTING_ORDER.map((id) => ({ fieldId: id, label: extra[id] ?? label(id), value: value[id] ?? "" }));
}
