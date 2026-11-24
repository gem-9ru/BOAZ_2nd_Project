import type { Metric, Result } from "../api";
import { Card, HowCalculated, pct, VerdictBadge } from "../ui";
import { sentence } from "./sentence";

/** 6 얼마나 믿을 수 있나: 지표별 확률 막대(70·90% 기준선) + 범위 점·선 + 말할 수 있는 것 3칸. */
export function Trust({ r }: { r: Result }) {
  const v = r.verdict;
  if (!v) return null;
  const sure = v.metrics.filter((m) => m.word === "확실해요");
  const dir = v.metrics.filter((m) => m.word.endsWith("쪽이에요"));
  const unknown = v.metrics.filter((m) => m.word === "아직 몰라요");
  const clicks = r.summary.arms.map((a) => a.link_clicks);
  return (
    <Card id="trust" title="지표별로 B가 나을 확률">
      <p className="text-lead">우연일 수 있는 만큼을 빼고 보면, 지금 말할 수 있는 건 이 정도예요.</p>
      <ul className="flex flex-col gap-4">
        {v.metrics.map((m) => <MetricRow key={m.key} m={m} />)}
      </ul>
      <div className="grid gap-3 sm:grid-cols-3">
        <Column title="확실히 말할 수 있어요" items={sure.map((m) => sentence(m, r))} />
        <Column title="방향만 말할 수 있어요" items={dir.map((m) => `${sentence(m, r)} (${pct(Math.max(m.prob_b_better, 1 - m.prob_b_better))})`)} />
        <Column title="아직 말할 수 없어요" items={[...unknown.map((m) => `${m.label} 차이`), "어느 쪽이 매출에 더 좋은지 (주문 숫자가 없어요)"]} />
      </div>
      {Math.min(...clicks) < 30 && <p className="text-body text-soft">링크 클릭이 {Math.min(...clicks)}번뿐인 세트가 있어 확실하다고 하기엔 부족해요. 더 모으면 범위가 좁아져요.</p>}
      <HowCalculated easy="두 세트의 가능한 범위가 안 겹치면 '확실해요', 겹치면 확률로만 말해요.">
        <p>판정: 나을 확률 90% 이상이거나 95% 범위가 안 겹치면 확실해요 · 70~90% ○ 쪽이에요 · 70% 미만 아직 몰라요 (희수 판정 규칙 + 다정 '말할 수 있음 / 방향만 / 말할 수 없음')</p>
        <p>모형: 비율은 베타 분포, 돈 대비 횟수는 감마 분포. 20만 번 뽑아 비교 (다정 M1). 근거: Lewis & Rao (2015) — 광고 효과는 큰 실험 없이 구분하기 어렵다</p>
      </HowCalculated>
    </Card>
  );
}

function MetricRow({ m }: { m: Metric }) {
  const p = m.prob_b_better;
  const lo = Math.min(m.a_interval[0], m.b_interval[0]), hi = Math.max(m.a_interval[1], m.b_interval[1]);
  const at = (x: number) => `${((x - lo) / (hi - lo || 1)) * 100}%`;
  const fmt = (x: number) => (m.key === "ctr" ? `${(x * 100).toFixed(2)}%` : m.key === "visits_per_1000won" ? `${x.toFixed(1)}명` : `₩${Math.round(x).toLocaleString()}`);
  return (
    <li className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2 text-body"><b>{m.label}</b><VerdictBadge word={m.word} /><span className="text-soft">B가 나을 확률 {pct(p)}</span></div>
      <div className="relative h-3 rounded bg-sunk" aria-hidden="true">
        <div className="absolute inset-y-0 left-0 rounded bg-series-b" style={{ width: `${p * 100}%` }} />
        <div className="absolute -inset-y-1 w-px bg-ink" style={{ left: "70%" }} />
        <div className="absolute -inset-y-1 w-px bg-ink" style={{ left: "90%" }} />
      </div>
      <div className="grid grid-cols-[2rem_1fr] gap-x-2 gap-y-1 text-caption text-soft">
        {(["A", "B"] as const).map((k) => {
          const iv = k === "A" ? m.a_interval : m.b_interval;
          return [
            <span key={`${k}l`}>{k}</span>,
            <div key={`${k}b`} className="relative h-4" title={`${fmt(iv[0])} ~ ${fmt(iv[1])}`}>
              <div className="absolute top-1/2 h-0.5 -translate-y-1/2" style={{ left: at(iv[0]), width: `calc(${at(iv[1])} - ${at(iv[0])})`, background: k === "A" ? "var(--tone-series-a)" : "var(--tone-series-b)" }} />
              <span className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 size-2.5 rounded-badge" style={{ left: at((iv[0] + iv[1]) / 2), background: k === "A" ? "var(--tone-series-a)" : "var(--tone-series-b)" }} />
            </div>,
          ];
        })}
      </div>
      <p className="text-caption text-soft">95% 범위 A {fmt(m.a_interval[0])}~{fmt(m.a_interval[1])} · B {fmt(m.b_interval[0])}~{fmt(m.b_interval[1])} {m.overlap ? "(겹침)" : "(안 겹침)"}</p>
    </li>
  );
}

function Column({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="rounded-button bg-bg px-4 py-3">
      <h3 className="text-body font-bold mb-2">{title}</h3>
      {items.length ? <ul className="flex flex-col gap-1 text-caption">{items.map((t) => <li key={t}>{t}</li>)}</ul> : <p className="text-caption text-soft">없어요</p>}
    </div>
  );
}
