import type { Field } from "../lib/api";

const f = (id: string, label: string, options: string[] | null, def: string | null, kind: Field["kind"] = "question"): Field =>
  ({ id, kind, label, ask: `${label}?`, options, default: def, why: "이유" });

export const FIELDS: Field[] = [
  f("meta.pre.fb_page", "페이스북 페이지", ["있어요", "없어요"], "있어요", "precheck"),
  f("meta.pre.ig_account", "인스타그램 계정", null, ""),
  { ...f("meta.pre.store_product", "스마트스토어 상품 페이지", ["올렸어요", "아직이에요", "스마트스토어에서 안 팔아요"], "올렸어요", "precheck"),
    help: { 아직이에요: { say: "스토어를 열고 상품을 올려 주세요.", done: "다 했어요", done_value: "올렸어요", later: "나중에 할게요",
      steps: [
        { text: "판매자 가입", link: "가입하기", url: "https://sell.smartstore.naver.com/#/join" },
        { text: "상품 등록", link: "상품 등록하기", url: "https://sell.smartstore.naver.com/#/products/create", hint: "keywords" as const },
        { text: "주소 복사하기" },
      ] } },
    then_ask: { field: { 올렸어요: "meta.pre.store_url", 아직이에요: "meta.pre.insta_url", "스마트스토어에서 안 팔아요": "meta.pre.insta_url" },
                say: { 올렸어요: "올린 상품 주소", 아직이에요: "인스타 프로필 주소", "스마트스토어에서 안 팔아요": "인스타 프로필로 보낼 주소" },
                prefill: { 아직이에요: "https://www.instagram.com/{meta.pre.ig_account}",
                           "스마트스토어에서 안 팔아요": "https://www.instagram.com/{meta.pre.ig_account}" },
                none: { 올렸어요: "스마트스토어에서 안 팔아요" } } },
  f("meta.campaign.objective", "캠페인 목표", ["스토어 방문 늘리기", "가게 알리기"], "스토어 방문 늘리기"),
  f("meta.campaign.special_category", "특별 광고 카테고리", ["아니요", "네"], "아니요"),
  { ...f("meta.adset.conversion_location", "전환 위치", ["스토어 상품 페이지", "인스타그램 프로필"], "스토어 상품 페이지"),
    then_ask: { field: "meta.ad.website_url", say: { "스토어 상품 페이지": "상품 페이지 주소", "인스타그램 프로필": "인스타 주소" },
                prefill: { "스토어 상품 페이지": "{meta.pre.store_url}",
                           "인스타그램 프로필": ["{meta.pre.insta_url}", "https://www.instagram.com/{meta.pre.ig_account}"] },
                none: { "스토어 상품 페이지": "인스타그램 프로필" } },
    default_if: { "meta.pre.store_product": { 아직이에요: "인스타그램 프로필" } },
    note_if: { "meta.pre.store_product": { 아직이에요: "스토어가 준비되면 바꿀 수 있어요." } } },
  { ...f("meta.adset.end_date", "종료 날짜", ["7일", "14일", "30일"], "14일"), custom: "dates" as const },
  { ...f("meta.adset.lifetime_budget", "총예산 (기간 전체)", ["1만 원", "3만 원", "5만 원"], "3만 원"), custom: "won" as const },
  { ...f("meta.adset.location", "타겟 – 위치", ["택배로 보내요", "가게에 와서 사요", "배달해요"], null), custom: "area" as const,
    custom_for: ["가게에 와서 사요", "배달해요"], answer_as: { "택배로 보내요": "전국 (택배)" } },
  f("meta.adset.age_gender", "타겟 – 연령·성별", null, "넓게"),
  f("meta.ad.format", "형식", ["1장 (단일 이미지)", "여러 장 (슬라이드)"], "1장 (단일 이미지)"),
  f("meta.ad.website_url", "웹사이트 URL", null, ""),
  f("meta.ad.media", "미디어", ["정사각형 사진", "세로 사진·영상", "둘 다"], "정사각형 사진"),
];
