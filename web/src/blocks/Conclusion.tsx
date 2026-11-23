import type { Metric, Result } from "../api";
import { Card, pct, VerdictBadge } from "../ui";

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

/** 3 한 줄 결론: 대표 지표(1,000원당 방문) 하나로 말하고, 그와 별개로 확실한 사실이 있으면 한 줄 더. */
export function Conclusion({ r }: { r: Result }) {
  const v = r.verdict;
  if (!v) {
    return (
      <Card id="conclusion" step={3} title="한 줄 결론">
        <p className="text-lead font-semibold">{r.diagnosis.finding.title}</p>
        <p className="text-body text-soft">{r.diagnosis.finding.message} 비교할 세트가 하나라 무엇이 더 나은지는 아직 몰라요.</p>
      </Card>
    );
  }
  const main = v.metrics.find((m) => m.key === v.badge.metric)!;
  const sure = v.metrics.find((m) => m.key !== main.key && m.word === "확실해요");
  const say = { "확실해요": `${v.badge.better}가 더 나았어요.`, "아직 몰라요": "이번 데이터로는 차이를 알 수 없어요." }[v.badge.word as string]
    ?? `${v.badge.better}가 나았을 가능성이 높아요. 한 번 더 확인하면 좋아요.`;
  return (
    <Card id="conclusion" step={3} title="한 줄 결론">
      <p className="text-lead leading-relaxed"><b>{sentence(main, r)}</b></p>
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-body text-soft">1,000원당 방문</span>
        <VerdictBadge word={v.badge.word} />
        <span className="text-number font-bold tabular-nums">{pct(v.badge.prob)}</span>
        <span className="text-body text-soft">{say}</span>
      </div>
      {sure && (
        <p className="flex flex-wrap items-center gap-3 text-body">
          <span>{sentence(sure, r)}</span><VerdictBadge word="확실해요" />
        </p>
      )}
    </Card>
  );
}
