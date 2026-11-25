import { useEffect, useState } from "react";
import { simulate, type Result, type Simulation } from "../api";
import { armName, Lead } from "../steps/shared";
import { AlertMark, band, Card, HowCalculated, won } from "../ui";

/** AN-05 예상 범위 (v4.2): 예산(세트당 총액)과 기간(4일/7일)을 고르면 '보통 ○명 (적게 ○명 ~ 많이 ○명)'.
 *  손님 수 범위는 총액으로 계산하고, 기간은 하루 금액을 바꾼다: 하루에 써 본 적 없는 금액이면 '가설',
 *  메타 하루 최소보다 적으면 ▲ (광고가 안 나갈 수 있어요).
 *  10번 중 8번은 이 안에 들어요(10~90%). 써 본 적 없는 금액은 점선 + '가설'. 보통 값은 진한 보라 점(주황은 주의 색). */
export function Simulator({ r }: { r: Result }) {
  const arms = r.summary.arms;
  const bi = r.verdict?.badge.better === "A" || arms.length < 2 ? 0 : 1;
  const arm = arms[bi];
  const start = r.matrix.change?.per_set ?? 5000;
  const [budget, setBudget] = useState(start);
  const [total, setTotal] = useState(100000);
  const [days, setDays] = useState(r.check.read.days === 7 ? 7 : 4);
  const [sims, setSims] = useState<Simulation[]>([]);
  const [error, setError] = useState<string | null>(null);
  const budgets = [budget, budget * 2, budget * 4];
  const spent = arm?.spend ?? 0;
  const c = r.matrix.change;

  useEffect(() => {
    if (!arm) return;
    const t = setTimeout(() => {
      Promise.all([budget, budget * 2, budget * 4].map((b) => simulate(r.code, arm.name, b, total, days)))
        .then((s) => { setSims(s); setError(null); }, (e: Error) => setError(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [r.code, arm, budget, total, days]);

  if (!arm) return null;
  const first = sims[0];
  const max = Math.max(...sims.map((s) => s.visits.hi), 1);
  const nt = first?.next_test;
  const who = armName(arm.name, bi);
  return (
    <>
      <Lead sub={`지금 세팅(${who}) 실측으로 계산${c?.tested === false && c.what ? ` · ${c.what} 효과는 아직 재 본 적 없어요` : ""}`}>
        {first ? `지금 세팅으로 세트당 총 ${won(budget)}을 ${days}일 동안 쓰면 ${band(first.visits)} 와요` : "계산하는 중…"}
      </Lead>
      <Card title="예상 손님 수" summary="10번 중 8번은 이 안에 들어요">
        <label htmlFor="budget" className="flex flex-wrap items-baseline justify-between gap-2 text-body">
          <span>예산 <span className="text-soft">(세트당 총액)</span></span><b className="tabular-nums">{won(budget)}</b>
        </label>
        <input id="budget" type="range" min={5000} max={100000} step={5000} value={budget} aria-label="예산"
          onChange={(e) => setBudget(Number(e.target.value))} className="w-full accent-action" />
        <div className="flex flex-wrap items-center gap-2">
          <div role="radiogroup" aria-label="기간" className="flex gap-2">
            {[4, 7].map((d) => (
              <label key={d} className={`cursor-pointer rounded-badge border px-3 py-1 text-body has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent ${days === d ? "border-accent bg-accent text-on-accent font-semibold" : "border-line bg-surface"}`}>
                <input type="radio" name="days" className="sr-only" checked={days === d} onChange={() => setDays(d)} />{d}일
              </label>
            ))}
          </div>
          <span className="text-body text-soft">하루 약 {won(Math.round(budget / days / 10) * 10)}</span>
        </div>
        {first?.below_daily_min && (
          <p role="status" className="flex items-start gap-2 rounded-button bg-warn-bg px-3 py-2 text-body text-warn">
            <AlertMark level="warn" />
            <span>하루 {won(Math.round(budget / days / 10) * 10)}은 메타 하루 최소(약 {won(first.daily_min)})보다 적어요 → 광고가 안 나갈 수 있어요. 기간을 줄이거나 총예산을 늘려 주세요.</span>
          </p>
        )}
        <ul className="flex flex-col gap-3" aria-live="polite">
          {budgets.map((b, i) => {
            const s = sims[i];
            const tried = s?.tried ?? b <= spent;   // 서버가 총액·하루 금액(기간)을 같이 봐요
            const at = (x: number) => `${(x / max) * 100}%`;
            return (
              <li key={b} className="flex flex-col gap-1">
                <p className="flex flex-wrap items-center gap-2 text-body">
                  <b className="tabular-nums">{won(b)}</b>
                  <span className="text-soft">{s ? band(s.visits) : "계산하는 중…"}</span>
                  {!tried && <span className="rounded-badge border border-dashed border-ink px-2 text-caption font-semibold">가설</span>}
                </p>
                {s && (
                  <div className="relative h-4" aria-hidden="true">
                    <div className={`absolute top-1/2 -translate-y-1/2 ${tried ? "h-1.5 rounded-badge bg-series-b" : "border-t-2 border-dashed border-series-b"}`}
                      style={{ left: at(s.visits.lo), width: `calc(${at(s.visits.hi)} - ${at(s.visits.lo)})` }} />
                    <span className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-badge bg-accent-ink" style={{ left: at(s.visits.median) }} />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
        <p className="text-caption text-soft">실선 = 써 본 금액 · 점선 = 써 본 적 없는 금액 · 진한 보라 점 = 보통 값</p>
        {!first?.tried && first && <p className="text-caption text-soft">
          {first.daily_tried === false
            ? `하루 ${won(first.daily)}은 써 본 적 없어서 가설이에요 (하루 최대 ${won(first.daily_max)}까지 써 봤어요).`
            : `이 금액은 써 본 적 없어서 범위가 넓어요 (세트당 ${won(spent)}까지만 써 봤어요).`}
        </p>}
        <p className="text-caption text-soft">손님 수 범위는 세트당 총액으로 계산해요. 기간을 바꾸면 하루 금액과 '가설' 여부가 바뀌어요.</p>
        {error && <p role="alert" className="text-body text-warn">{error}</p>}
      </Card>
      {nt && (
        <Card title="다음 테스트에 쓸 돈 (Test & Roll)"
          summary={start >= nt.per_set_lo && start <= nt.per_set_hi ? `이번처럼 세트당 총 ${won(start)}이면 적당해요`
            : `전체 예산이 ${won(nt.total)}이면 세트당 총 ${won(nt.per_set_lo)}~${won(nt.per_set_hi)}이 적당해요`}>
          <label className="flex flex-wrap items-center gap-2 text-body">이번 달 전체 광고 예산
            <input type="number" min={10000} step={10000} value={total} onChange={(e) => setTotal(Number(e.target.value) || 0)}
              className="w-32 rounded-button border border-field-line bg-surface px-2 py-1 tabular-nums" />원
          </label>
          <p className="text-body">전체 예산의 약 {Math.round(nt.share_lo * 100)}~{Math.round(nt.share_hi * 100)}% · {won(nt.total)}이면 세트당 {won(nt.per_set_lo)}~{won(nt.per_set_hi)}. 나머지는 이긴 쪽에 써요.</p>
        </Card>
      )}
      <HowCalculated easy="실측으로 맞춘 범위에서 광고비·누르는 정도·페이지 도착을 무작위로 뽑아 수만 번 가상으로 돌려 보고, 가운데 80%를 보여 드려요.">
        <p>예산 ÷ 광고 1,000번 보여주는 데 드는 돈 (CPM, 범위로 뽑음) → 보여진 횟수 × 누른 비율 (CTR) → 클릭 × 도착 비율 → 손님. 골라 뽑지 않고 전체 분포를 써요.</p>
        <p>한계: {first?.limits ?? "예산을 크게 늘리면 단가가 오르거나 학습 기간이 생길 수 있지만 반영하지 않았어요."} 근거: Jin 외 (2017) 포화 구조</p>
        {nt && <p>Test & Roll (Feit & Berman 2019): 실측으로 맞춘 몫 {(nt.share_lo * 100).toFixed(1)}~{Math.round(nt.share_hi * 100)}%.</p>}
        {r.verdict?.min_budget.per_group && <p>고전적 표본 크기: 손님 1명당 비용이 20% 나은 걸 확실하게 고르려면 세트당 약 {won(r.verdict.min_budget.per_group)} (10번 중 8번).</p>}
      </HowCalculated>
    </>
  );
}
