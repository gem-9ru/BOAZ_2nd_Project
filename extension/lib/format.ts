// 화면에 숫자를 짧게 보여 주는 도우미.

/** 검색 횟수 'N번'. under = 네이버가 "< 10"으로 준 칸 수(PC·모바일): 둘 다면 '20번 미만', 하나면 '약 N번' */
export function times(n: number, under = 0): string {
  return under >= 2 ? "20번 미만" : under === 1 ? `약 ${compact(n)}번` : `${compact(n)}번`;
}

/** 12000 → '1.2만', 950 → '950' */
export function compact(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(n >= 100000 ? 0 : 1).replace(/\.0$/, "")}만` : n.toLocaleString();
}
