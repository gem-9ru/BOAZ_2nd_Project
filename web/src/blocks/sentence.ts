import type { Metric, Result } from "../api";
import { pct, won } from "../ui";

/** 같은 확률·범위를 사장님 문장으로 (v4.2: 사장님 말 먼저, 금액은 '원'). 비교 기준이 '같은 돈'이라 지출 규모가 달라도 공정하다. */
export function sentence(m: Metric, r: Result): string {
  const [a, b] = r.summary.arms;
  const win = m.better === "B" ? b! : a!;
  const lose = m.better === "B" ? a! : b!;
  const ratio = (x: number | null, y: number | null) => (x && y ? Math.abs(x / y - 1) : null);
  switch (m.key) {
    case "cpm": return `${m.better}가 광고비가 약 ${pct(ratio(win.cpm, lose.cpm))} 쌌어요`;
    case "cpc": return `${m.better}가 클릭 1번에 약 ${won(Math.abs((lose.cpc ?? 0) - (win.cpc ?? 0)))} 덜 들었어요`;
    case "ctr": return `${m.better} 광고를 본 사람이 약 ${pct(ratio(win.ctr, lose.ctr))} 더 많이 눌렀어요`;
    default: return r.verdict?.badge.word === "아직 몰라요" ? `${m.better}가 조금 더 데려왔지만 아직 우연일 수 있어요` : `${m.better}가 같은 돈으로 방문자를 더 데려왔어요`;
  }
}
