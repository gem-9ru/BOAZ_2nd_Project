import type { Metric } from "../api";
import { betterProb, probText, seriesBg, VerdictBadge, won } from "../ui";

/** 지표 하나의 'B가 나을 확률' 막대 (70·90% 점선) + 두 세트 범위. AN-04의 🔎 안에서 CPC·CTR에 쓴다 (v4.2). */
export function MetricRow({ m }: { m: Metric }) {
  const p = m.prob_b_better;
  const lo = Math.min(m.a_interval[0], m.b_interval[0]), hi = Math.max(m.a_interval[1], m.b_interval[1]);
  const at = (x: number) => `${((x - lo) / (hi - lo || 1)) * 100}%`;
  const fmt = (x: number) => (m.key === "ctr" ? `${(x * 100).toFixed(2)}%` : m.key === "visits_per_1000won" ? `${x.toFixed(1)}명` : won(x));
  // 추천 쪽 = 바이올렛, 나머지 = 회색 (v4.2)
  const tone = (k: "A" | "B") => seriesBg(k === m.better);
  return (
    <li className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2 text-body"><b>{m.label}</b><VerdictBadge word={m.word} small /><span className="text-soft">{m.better}가 나을 확률 {probText(betterProb(m.better, p))}</span></div>
      <ProbBar p={betterProb(m.better, p)} />
      <div className="grid grid-cols-[2rem_1fr] gap-x-2 gap-y-1 text-caption text-soft">
        {(["A", "B"] as const).map((k) => {
          const iv = k === "A" ? m.a_interval : m.b_interval;
          return [
            <span key={`${k}l`}>{k}</span>,
            <div key={`${k}b`} className="relative h-4" title={`${fmt(iv[0])} ~ ${fmt(iv[1])}`}>
              <div className={`absolute top-1/2 h-0.5 -translate-y-1/2 ${tone(k)}`} style={{ left: at(iv[0]), width: `calc(${at(iv[1])} - ${at(iv[0])})` }} />
              <span className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 size-2.5 rounded-badge ${tone(k)}`} style={{ left: at((iv[0] + iv[1]) / 2) }} />
            </div>,
          ];
        })}
      </div>
      <p className="text-caption text-soft">95% 범위 A {fmt(m.a_interval[0])}~{fmt(m.a_interval[1])} · B {fmt(m.b_interval[0])}~{fmt(m.b_interval[1])} {m.overlap ? "(겹침)" : "(안 겹침)"}</p>
    </li>
  );
}

/** 확률 막대: 점선 70% = '○ 쪽이에요', 90% = '확실해요'. */
export function ProbBar({ p }: { p: number }) {
  return (
    <div aria-hidden="true" className="flex flex-col gap-1">
      <div className="relative h-3 rounded-badge bg-sunk">
        <div className="absolute inset-y-0 left-0 rounded-badge bg-series-b" style={{ width: `${p * 100}%` }} />
        <div className="absolute -inset-y-1 border-l-2 border-dashed border-belly-strong" style={{ left: "70%" }} />
        <div className="absolute -inset-y-1 border-l-2 border-dashed border-belly-strong" style={{ left: "90%" }} />
      </div>
      {/* 점선 바로 아래에 기준 숫자 (설명 문장까지 내려가지 않아도 읽히게) */}
      <div className="relative h-4 text-small text-soft tabular-nums">
        <span className="absolute -translate-x-1/2" style={{ left: "70%" }}>70%</span>
        <span className="absolute -translate-x-1/2" style={{ left: "90%" }}>90%</span>
      </div>
    </div>
  );
}
