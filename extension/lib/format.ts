// 화면에 숫자를 짧게 보여 주는 도우미.

/** 12000 → '1.2만', 950 → '950' */
export function compact(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(n >= 100000 ? 0 : 1).replace(/\.0$/, "")}만` : n.toLocaleString();
}
