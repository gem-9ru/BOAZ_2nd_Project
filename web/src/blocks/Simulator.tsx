import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { simulate, type Result, type Simulation } from "../api";
import { Card, Grade, HowCalculated, won } from "../ui";

/** 9 예산 시뮬레이터 (3 시뮬레이션): 예산을 움직이면 바로 다시 계산 (즉시 반영 → 슬라이더·세그먼트). */
export function Simulator({ r }: { r: Result }) {
  const arms = r.summary.arms;
  const better = r.verdict?.badge.better === "A" ? arms[0] : arms[1] ?? arms[0];
  const [arm, setArm] = useState(better?.name ?? "");
  const [budget, setBudget] = useState(5000);
  const [total, setTotal] = useState(100000);
  const [sim, setSim] = useState<Simulation | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      simulate(r.code, arm, budget, total).then((s) => { setSim(s); setError(null); }, (e: Error) => setError(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [r.code, arm, budget, total]);

  const band = (b: { median: number; lo: number; hi: number }) => `약 ${Math.round(b.median).toLocaleString()} (${Math.round(b.lo)}~${Math.round(b.hi)})`;
  return (
    <Card id="simulator" title="예산을 바꿔 보기">
      <div role="radiogroup" aria-label="세팅" className="flex gap-2">
        {arms.map((a, i) => (
          <label key={a.name} className={`cursor-pointer rounded-badge border px-3 py-1.5 text-body focus-within:outline-2 focus-within:outline-focus focus-within:outline-offset-2 ${arm === a.name ? "border-ink bg-ink text-on-action font-semibold" : "border-line"}`}>
            <input type="radio" name="arm" className="sr-only" checked={arm === a.name} onChange={() => setArm(a.name)} />
            {"AB"[i]} · {a.name}
          </label>
        ))}
      </div>
      <label htmlFor="budget" className="text-body text-soft">예산</label>
      <input id="budget" type="range" min={5000} max={100000} step={5000} value={budget}
        onChange={(e) => setBudget(Number(e.target.value))} className="w-full accent-action" />
      <p className="text-lead" aria-live="polite">
        <b className="tabular-nums">{won(budget)}</b>이면
        {sim ? <> 링크 클릭 <b className="tabular-nums">{band(sim.link_clicks)}</b>회 · 가게 도착 <b className="tabular-nums">{band(sim.visits)}</b>명</> : " 계산하는 중…"}
      </p>
      <div className="flex gap-2 items-center"><Grade g="A" /><span className="text-caption text-soft">내 실측 범위로 충분히 많이(20만 번) 가상 집행 · 가운데 80% · 실제 결과가 아닌 예상치예요</span></div>
      {sim && sim.tried === false && (
        <p className="rounded-button border-2 border-dashed border-line px-4 py-2 text-body text-soft"><b>가설</b> · 세트마다 실제로 쓴 금액보다 커요. 써 본 적 없는 금액이라 참고로만 봐 주세요.</p>
      )}
      {sim?.next_test && (
        <div className="flex flex-col gap-2 rounded-button bg-accent-soft px-4 py-3 text-body">
          <label className="flex flex-wrap items-center gap-2">이번 달 전체 광고 예산
            <input type="number" min={10000} step={10000} value={total} onChange={(e) => setTotal(Number(e.target.value) || 0)}
              className="w-32 rounded-button border border-line bg-surface px-2 py-1 tabular-nums" />원
          </label>
          <p>다음 테스트는 <b>세트당 {won(sim.next_test.per_set_lo)}~{won(sim.next_test.per_set_hi)}</b>이면 돼요. 전체의 약 {Math.round(sim.next_test.share_lo * 100)}~{Math.round(sim.next_test.share_hi * 100)}%만 테스트에 쓰고, 나머지는 이긴 쪽에 써요 (Test & Roll).</p>
        </div>
      )}
      {error && <p role="alert" className="text-body text-warn">{error}</p>}
      {sim && (
        <div className="h-48" aria-label="링크 클릭 수 분포">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sim.histogram.map((h) => ({ x: Math.round((h.lo + h.hi) / 2), n: h.count }))} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <XAxis dataKey="x" stroke="var(--tone-ink-soft)" tickLine={false} fontSize={12} />
              <YAxis hide />
              <Tooltip formatter={(n: number) => [`${n.toLocaleString()}번`, "가상 집행"]} labelFormatter={(x) => `링크 클릭 약 ${x}회`} />
              <Bar dataKey="n" fill="var(--tone-series-b)" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
      <HowCalculated easy="내 실측에서 나온 범위 안에서 노출 단가·클릭률·도착률을 무작위로 뽑아 20만 번 가상으로 집행해 보고, 가운데 80%를 보여 드려요.">
        <p>노출 = 예산 ÷ CPM × 1,000 → 클릭 = 노출 × 클릭률 → 도착 = 클릭 × 클릭→도착 비율 (희수 8장 ③)</p>
        <p>한계: {sim?.limits ?? "예산을 크게 늘리면 단가가 오르거나 학습 기간이 생길 수 있지만 반영하지 않았어요."} 근거: Jin 외 (2017) 포화 구조</p>
      </HowCalculated>
    </Card>
  );
}
