// 달별 자료(가장 많은 달 = 100)로 '지금이 많이 찾는 때인지' 한 줄. 이번 달 자료가 아직 없으면 작년 같은 달로 본다.

export function nowLine(monthly: Record<string, number>, today: Date = new Date()): string | null {
  const m = today.getMonth() + 1;
  const keys = Object.keys(monthly).filter((k) => Number(k.split("-")[1]) === m).sort();
  if (keys.length === 0) return null;
  const v = monthly[keys[keys.length - 1]!] ?? 0;
  const top = Math.max(...Object.values(monthly)) || 100;
  const share = Math.round((v / top) * 100);
  const peakKey = Object.keys(monthly).reduce((a, b) => ((monthly[b] ?? 0) > (monthly[a] ?? 0) ? b : a));
  const peak = Number(peakKey.split("-")[1]);
  const ahead = (peak - m + 12) % 12;   // 가장 많은 달까지 남은 달 수
  if (share >= 80) return `지금(${m}월)은 많이 찾는 때예요.`;
  if (ahead >= 1 && ahead <= 2) return `곧 많이 찾는 때예요 (${peak}월). 지금(${m}월)은 가장 많은 달의 ${share}% 정도예요.`;
  return `지금(${m}월)은 가장 많은 달의 ${share}% 정도예요.`;
}
