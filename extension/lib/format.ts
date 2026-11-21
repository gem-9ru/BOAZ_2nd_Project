/** 0.01233 → "1.2%" */
export function pct(x: number, digits = 1): string {
  return `${(x * 100).toFixed(digits)}%`;
}

/** 범위는 항상 두 숫자로: "1.2% ~ 2.2%" */
export function pctRange([lo, hi]: [number, number] | number[]): string {
  return `${pct(lo!)} ~ ${pct(hi!)}`;
}

export const GRADE_LABEL = { checked: "실측 근거", hypothesis: "가설" } as const;
