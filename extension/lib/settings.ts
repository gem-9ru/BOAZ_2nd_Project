// 찾기·질문 답을 광고 관리자에 넣을 값으로 바꾸는 순수 함수들.
import type { Target } from "./flow";

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
