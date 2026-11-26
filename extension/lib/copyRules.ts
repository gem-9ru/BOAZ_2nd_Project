// 광고 문구에 쓸 수 없는 말 (근거를 댈 수 없는 최상급·보장 표현).
// server/engine/copywriter.py의 BANNED와 같아야 한다 (server/tests/test_copy_rules_sync.py가 확인).
export const BANNED = ["최저가", "최저", "1위", "1등", "최고", "최상", "최초", "국내 유일", "세계 유일", "유일", "넘버원",
  "no.1", "no 1", "100%", "무조건", "보장", "완치", "특효"];

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
