// 광고 문구에 쓸 수 없는 말 (근거를 댈 수 없는 최상급·보장 표현).
// server/engine/copywriter.py의 BANNED와 같아야 한다 (server/tests/test_copy_rules_sync.py가 확인).
export const BANNED = ["최저가", "최저", "1위", "1등", "최고", "최상", "최초", "국내 유일", "세계 유일", "유일", "넘버원",
  "no.1", "no 1", "100%", "무조건", "보장", "완치", "특효"];

/** 효능·질병을 말하는 낱말: 칩으로 고를 수는 있지만 '낫는다'고 쓰면 광고 심의에 걸린다 (화장품·식품을 약처럼 광고) */
export const HEALTH = ["탈모", "여드름", "아토피", "습진", "불면", "비염", "변비", "염증", "피부염", "치료", "완화", "면역", "혈압", "당뇨", "관절", "통증"];
export const isHealth = (word: string) => HEALTH.some((h) => word.includes(h));

/** 글에 들어 있는 금지 표현, 나온 순서대로 ('최저가'가 있으면 그 안의 '최저'는 따로 안 셈). */
export function bannedIn(text: string): string[] {
  const src = text.toLowerCase();
  let low = src;
  const out: string[] = [];
  for (const b of [...BANNED].sort((x, y) => y.length - x.length)) {
    if (low.includes(b)) { out.push(b); low = low.split(b).join(" ".repeat(b.length)); }
  }
  return out.sort((x, y) => src.indexOf(x) - src.indexOf(y));   // 글에 나온 순서대로
}
