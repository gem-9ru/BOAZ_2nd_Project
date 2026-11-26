/** 달별 막대 12개: 가장 많은 달만 강조색. 값은 상대값이라 '가장 많은 달 대비 비중'으로만 읽는다. */
export default function MonthBars({ monthly }: { monthly: Record<string, number> }) {
  // 'YYYY-MM' → 달 번호. 1월부터 12월 순서로 놓는다.
  const byMonth = new Map<number, number>();
  for (const [key, v] of Object.entries(monthly)) {
    const m = Number(key.split("-")[1]);
    if (m >= 1 && m <= 12) byMonth.set(m, v);
  }
  const months = [...byMonth.keys()].sort((a, b) => a - b);
  if (months.length === 0) return null;
  const max = Math.max(...months.map((m) => byMonth.get(m) ?? 0)) || 1;
  const share = (m: number) => Math.round(((byMonth.get(m) ?? 0) / max) * 100);
  const peak = months.find((m) => share(m) === 100);

  return (
    <div className="flex flex-col gap-1">
      <div className="flex h-10 items-end gap-0.5" role="img"
        aria-label={`달별 검색 비중: ${months.map((m) => `${m}월 ${share(m)}%`).join(", ")}`}>
        {months.map((m) => (
          <div key={m} aria-hidden
            className={`flex-1 rounded-t-sm border ${m === peak ? "border-accent bg-accent" : "border-soft bg-line"}`}
            style={{ height: `${Math.max(8, share(m))}%` }} />
        ))}
      </div>
      <div aria-hidden className="flex justify-between gap-2 text-small text-soft">
        <span>{months[0]}월</span>
        {peak && <span className="font-semibold text-accent-ink">가장 많은 달 {peak}월</span>}
        <span>{months[months.length - 1]}월</span>
      </div>
    </div>
  );
}
