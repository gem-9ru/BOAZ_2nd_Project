import type { Field } from "../lib/api";

const f = (id: string, label: string, options: string[] | null, def: string | null, kind: Field["kind"] = "question"): Field =>
  ({ id, kind, label, ask: `${label}?`, options, default: def, why: "이유" });

export const FIELDS: Field[] = [
  f("meta.pre.fb_page", "페이스북 페이지", ["있어요", "없어요"], "있어요", "precheck"),
  f("meta.pre.ig_account", "인스타그램 계정", null, ""),
  f("meta.campaign.objective", "캠페인 목표", ["스토어 방문 늘리기", "가게 알리기"], "스토어 방문 늘리기"),
  f("meta.campaign.special_category", "특별 광고 카테고리", ["아니요", "네"], "아니요"),
  f("meta.adset.conversion_location", "전환 위치", ["스토어 상품 페이지", "인스타그램 프로필"], "스토어 상품 페이지"),
  f("meta.adset.end_date", "종료 날짜", ["7일", "14일", "30일"], "14일"),
  f("meta.adset.location", "타겟 – 위치", ["전국 (택배)", "내 지역만"], "전국 (택배)"),
  f("meta.adset.age_gender", "타겟 – 연령·성별", null, "넓게"),
  f("meta.ad.format", "형식", ["1장 (단일 이미지)", "여러 장 (슬라이드)"], "1장 (단일 이미지)"),
  f("meta.ad.website_url", "웹사이트 URL", null, ""),
  f("meta.ad.media", "미디어", ["정사각형 사진", "세로 사진·영상", "둘 다"], "정사각형 사진"),
];
