import type { Result } from "../api";
import { Card, HowCalculated, pct } from "../ui";

/** 5 퍼널: 본 사람 → 누른 사람 → 들어온 사람. 세트별 막대 + 단계 사이 비율(범위). */
export function Funnel({ r }: { r: Result }) {
  const f = r.funnel;
  return (
    <Card id="funnel" title="단계별로 몇 명이 남았나" summary="보여진 횟수 → 클릭 → 손님(페이지 방문)">
      {f.hint && <p className="text-lead font-semibold">{f.hint}</p>}
      <div className="grid gap-group sm:grid-cols-2">
        {f.arms.map((arm, i) => {
          const top = arm.stages[0]?.count || 1;
          return (
            <div key={arm.name} className="flex flex-col gap-3">
              <p className="text-body font-semibold">
                <span className="inline-block size-2.5 rounded-badge mr-1.5" style={{ background: i ? "var(--tone-series-b)" : "var(--tone-series-a)" }} />
                {"AB"[i]} · {arm.name}
              </p>
              {arm.stages.map((s) => (
                <div key={s.key} className="flex flex-col gap-1">
                  <div className="flex justify-between text-body"><span className="text-soft">{s.label}</span><b className="tabular-nums">{s.count.toLocaleString()}</b></div>
                  <div className="h-2 rounded bg-sunk" aria-hidden="true">
                    <div className="h-2 rounded" style={{ width: `${Math.max((s.count / top) * 100, s.count ? 1 : 0)}%`, background: i ? "var(--tone-series-b)" : "var(--tone-series-a)" }} />
                  </div>
                  {s.per100 && (
                    <p className="text-caption text-soft">
                      {s.per100} · {pct(s.rate, 1)} (적게 {pct(s.range?.[0])} ~ 많이 {pct(s.range?.[1])})
                      {s.unknown && <span className="ml-1 rounded-badge bg-hold-bg text-hold px-2">아직 몰라요</span>}
                    </p>
                  )}
                </div>
              ))}
            </div>
          );
        })}
      </div>
      <HowCalculated easy="앞 단계 사람 중 몇 명이 다음 단계로 갔는지예요. 사람이 적으면 우연일 수 있어서 가능한 범위를 같이 적었어요.">
        <p>범위는 베타 분포 95% 구간이에요. 앞 단계가 10건보다 적으면 '아직 몰라요'로 표시해요. 픽셀 이벤트가 파일에 있으면 단계가 더 붙어요 (다음 버전).</p>
      </HowCalculated>
    </Card>
  );
}
