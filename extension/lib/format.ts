// 화면에 숫자를 짧게 보여 주는 도우미.

/** 검색 횟수 'N번'. under = 네이버가 "< 10"으로 준 칸 수(PC·모바일): 둘 다면 '20번 미만', 하나면 '약 N번' */
export function times(n: number, under = 0): string {
  return under >= 2 ? "20번 미만" : under === 1 ? `약 ${compact(n)}번` : `${compact(n)}번`;
}

/** 두 낱말 이상 상품에서 검색어가 끝 낱말만 같으면 그 낱말 ('강아지 간식'·'다이어트간식' → '간식'). 아니면 null.
 *  (서버는 끝 낱말만 같아도 내 상품으로 본다: '캠핑 의자'의 '의자' 검색어를 살리려고) */
export function onlyLastWord(product: string, keyword: string): string | null {
  const pieces = product.trim().split(/\s+/).filter((w) => w.length >= 2);
  if (pieces.length < 2) return null;
  const k = keyword.replace(/\s/g, "");
  const last = pieces[pieces.length - 1]!;
  if (k.includes(pieces.join("")) || pieces.slice(0, -1).some((w) => k.includes(w))) return null;
  return k.includes(last) ? last : null;
}

/** 12000 → '1.2만', 950 → '950' */
export function compact(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(n >= 100000 ? 0 : 1).replace(/\.0$/, "")}만` : n.toLocaleString();
}
