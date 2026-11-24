import type { Metric, Result } from "../api";
import { pct } from "../ui";

/** 같은 확률·범위를 사장님 문장으로. 비교 기준이 '같은 돈'이라 지출 규모가 달라도 공정하다. */
export function sentence(m: Metric, r: Result): string {
  const [a, b] = r.summary.arms;
  const win = m.better === "B" ? b! : a!;
  const lose = m.better === "B" ? a! : b!;
  const ratio = (x: number | null, y: number | null) => (x && y ? Math.abs(x / y - 1) : null);
  switch (m.key) {
    case "cpm": return `같은 돈으로 ${m.better}가 광고를 약 ${pct(ratio(lose.cpm, win.cpm))} 더 많이 보여줬어요`;
    case "cpc": return `${m.better}가 클릭 1번에 약 ${Math.round(Math.abs((lose.cpc ?? 0) - (win.cpc ?? 0))).toLocaleString()}원 덜 들었어요`;
    case "ctr": return `${m.better} 광고를 본 사람이 약 ${pct(ratio(win.ctr, lose.ctr))} 더 많이 눌렀어요`;
    default: return `같은 돈으로 ${m.better}가 손님을 약 ${pct(ratio(win.visits_per_1000won, lose.visits_per_1000won))} 더 데려왔어요`;
  }
}
