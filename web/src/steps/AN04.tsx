import { useState } from "react";
import type { Result } from "../api";
import { Trust } from "../blocks/Trust";
import { Card, pct } from "../ui";

/** AN-04 ★ 세팅 값별 비교 (시연 메인): 지표별 확률 · 날짜별 누적 · 노출 위치 탭(보정한 클릭률 기본). */
export function AN04({ r }: { r: Result }) {
  const [tab, setTab] = useState<"metrics" | "days" | "places">("metrics");
  const alerts = r.alerts.filter((a) => a.screen === "AN-04");
  const tabs = [["metrics", "지표별"], ["days", "날짜별"], ["places", "노출 위치별"]] as const;
  return (
    <>
      <div role="tablist" aria-label="비교 보기" className="flex gap-2">
        {tabs.map(([id, t]) => (
          <button key={id} role="tab" type="button" aria-selected={tab === id} onClick={() => setTab(id)}
            className={`rounded-badge border px-4 py-1.5 text-body ${tab === id ? "border-accent bg-accent text-on-action font-semibold" : "border-line bg-surface"}`}>{t}</button>
        ))}
      </div>
      {alerts.map((a) => <p key={a.kind} className="rounded-button bg-warn-bg px-4 py-3 text-body text-warn">▲ {a.text}</p>)}
      {tab === "metrics" && (r.verdict ? <Trust r={r} /> : <Card title="비교할 세트가 하나예요"><p className="text-body">세트가 두 개 이상이어야 값을 비교할 수 있어요.</p></Card>)}
      {tab === "days" && (
        <Card title="하루씩 더했을 때 B가 나을 확률">
          <ol className="flex flex-wrap gap-3">
            {r.replay.map((d) => (
              <li key={d.date} className="flex min-w-24 flex-col items-center rounded-button bg-bg px-4 py-3">
                <span className="text-caption text-soft">{d.date.slice(5).replace("-", "/")}까지</span>
                <b className="text-number tabular-nums">{pct(d.prob)}</b>
              </li>
            ))}
          </ol>
          <p className="text-caption text-soft">날짜가 쌓일수록 한쪽으로 모이면 우연이 아닐 가능성이 커요 (Scott 2010).</p>
        </Card>
      )}
      {tab === "places" && (
        <Card title="노출 위치별 클릭률 (보정값)">
          <div className="overflow-x-auto">
            <table className="w-full text-body">
              <thead><tr className="text-left text-caption text-soft"><th className="py-2 pr-3">노출 위치</th><th className="pr-3">지출 비중</th><th className="pr-3">노출</th><th className="pr-3">보정한 클릭률</th><th>원래 클릭률</th></tr></thead>
              <tbody>
                {r.placements.map((p) => (
                  <tr key={p.placement} className={`border-t border-line ${p.reference_only ? "text-soft" : ""}`}>
                    <td className="py-2 pr-3">{p.label}{p.reference_only && <span className="ml-2 rounded-badge bg-hold-bg px-2 text-caption">참고만</span>}</td>
                    <td className="pr-3 tabular-nums">{pct(p.share)}</td>
                    <td className="pr-3 tabular-nums">{p.impressions.toLocaleString()}</td>
                    <td className="pr-3 font-semibold tabular-nums">{pct(p.ctr_adjusted, 1)}</td>
                    <td className="tabular-nums">{pct(p.ctr, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-caption text-soft">노출이 100보다 적은 칸은 전체 평균 쪽으로 당겨 보정했어요 (Efron & Morris 1975). 판정에는 쓰지 않아요.</p>
          <p className="rounded-button bg-info-bg px-4 py-3 text-body">● 평균만 보고 바로 끄지 마세요. 메타는 다음 1건의 비용으로 돈을 나눠서, 평균이 나쁜 자리를 끄면 전체 비용이 오를 수 있어요 (Breakdown effect). 끄고 싶으면 다음 5,000원 테스트로 확인해요.</p>
        </Card>
      )}
    </>
  );
}
