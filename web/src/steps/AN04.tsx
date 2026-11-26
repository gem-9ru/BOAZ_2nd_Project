import { useState } from "react";
import type { Placement, Result } from "../api";
import { sentence } from "../blocks/sentence";
import { MetricRow, ProbBar } from "../blocks/Trust";
import { band, Card, HowCalculated, md, pct, people, betterProb, ReferenceBadge, Tabs, VerdictBadge, won, wordOf } from "../ui";
import { armName, Lead, sameMoney } from "./shared";

/** AN-04 ★ 세팅 값별 비교 (v4.2): 맨 앞에 '손님 1명당 비용' (사장님이 궁금한 숫자) + B가 나을 확률,
 *  광고비 범위(CPM)는 기본 화면에 사장님 말로, CPC·CTR 막대는 🔎 안. 색은 추천 쪽 = 바이올렛, 나머지 = 회색. */
export function AN04({ r }: { r: Result }) {
  const [tab, setTab] = useState<"ab" | "places" | "days">("ab");
  const v = r.verdict;
  const arms = r.summary.arms.slice(0, 2);
  const title = arms.length === 2 ? `${armName(arms[0]!.name, 0)} vs ${armName(arms[1]!.name, 1)}` : "세트 비교";
  const tabs = [["ab", title], ["places", "노출 위치별"], ["days", "날짜별"]] as const;
  return (
    <>
      {tab !== "places" && v && (
        <Lead badge={<VerdictBadge word={v.badge.word} />}>
          {v.badge.word === "아직 몰라요" ? "어느 쪽이 손님을 더 데려왔는지는 아직 몰라요" : `${paren(armName(v.badge.better === "B" ? arms[1]!.name : arms[0]!.name, v.badge.better === "B" ? 1 : 0))}가 같은 돈으로 손님을 더 데려왔어요`}
        </Lead>
      )}
      {tab === "places" && <PlacesLead r={r} />}
      <Tabs big label="비교 기준" value={tab} onChange={setTab} items={tabs.map(([id, t]) => ({ id, label: t }))} />
      {!v && tab !== "places" && <><Lead>비교할 세트가 하나라 값 비교는 없어요</Lead>
        <Card title="비교할 세트가 하나예요" summary="세트가 두 개 이상이어야 값을 비교할 수 있어요. 다음엔 칸 1개만 다르게 두 세트를 같은 날 같이 돌려 보세요" /></>}
      {v && tab === "ab" && <><CostPerCustomer r={r} /><AdCost r={r} /><Days r={r} /></>}
      {v && tab === "days" && <Days r={r} />}
      {tab === "places" && <Places r={r} />}
      {v && tab !== "places" && (
        <HowCalculated easy="두 세트의 가능한 범위가 안 겹치면 '확실해요', 겹치면 확률로만 말해요. 판정: 90% 이상 확실해요 · 70~90% ○ 쪽이에요 · 70% 미만 아직 몰라요.">
          <ul className="flex flex-col gap-4">
            {v.metrics.filter((m) => m.key === "cpc" || m.key === "ctr").map((m) => <MetricRow key={m.key} m={m} />)}
          </ul>
          {v.badge.capped && <p>판정을 낮춘 이유: {v.badge.capped.join(" · ")}</p>}
          <p>계산 방법: 비율은 베타-이항, 돈 대비 횟수는 감마-포아송 분포에서 반복 시뮬레이션으로 뽑아 비교해요. 근거: Lewis & Rao (2015), Scott (2010)</p>
        </HowCalculated>
      )}
    </>
  );
}

const paren = (s: string) => (s.includes(" ") ? `${s.replace(" ", "(")})` : s);   // 'B 수동' → 'B(수동)'

/** 손님 1명당 비용 (핵심 카드): 손님 1명당 비용 · 같은 돈으로 온 손님 수 · B가 나을 확률. */
function CostPerCustomer({ r }: { r: Result }) {
  const v = r.verdict!;
  const arms = r.summary.arms.slice(0, 2);
  const same = sameMoney(r);
  const m = v.metrics.find((x) => x.key === v.badge.metric)!;
  const costs = arms.map((a) => (a.landing_page_views ? a.spend / a.landing_page_views : null));
  const max = Math.max(...costs.map((c) => c ?? 0)) || 1;
  const better = v.badge.better === "B" ? 1 : 0;
  return (
    <Card title="손님 1명당 비용" summary={sentence(m, r)}>
      <ul className="flex flex-col gap-2">
        {arms.map((a, i) => (
          <li key={a.name} className="grid grid-cols-[6rem_1fr_5rem] items-center gap-3 text-body">
            <span className="font-semibold">{armName(a.name, i)}</span>
            <span className="h-3 rounded-badge bg-sunk" aria-hidden="true">
              <span className={`block h-3 rounded-badge ${i === better ? "bg-series-b" : "bg-series-a"}`} style={{ width: `${((costs[i] ?? 0) / max) * 100}%` }} />
            </span>
            <b className="text-right tabular-nums">{won(costs[i])}</b>
          </li>
        ))}
      </ul>
      {same && <p className="text-body">같은 돈({won(same.base)})으로 온 손님 <b>A {same.counts[0]}명 · B {same.counts[1]}명</b></p>}
      {/* 이긴 쪽 기준으로 말한다 (A가 이기면 'A가 나을 확률 95%') */}
      <p className="flex flex-wrap items-center gap-2 text-body">{v.badge.better}가 나을 확률 <b className="tabular-nums">{pct(betterProb(v.badge.better, m.prob_b_better))}</b> <VerdictBadge word={v.badge.word} small /></p>
      <ProbBar p={betterProb(v.badge.better, m.prob_b_better)} />
      <p className="text-caption text-soft">점선: 70% 넘으면 '○ 쪽이에요' · 90% 넘으면 '확실해요'{v.badge.capped ? " · 클릭이 적거나 돈이 한쪽에 몰리면 한 단계 낮춰 보여 드려요" : ""}</p>
    </Card>
  );
}

/** 광고비 범위 (CPM 95%): 기본 화면에 두되 문구는 사장님 말로. 겹치지 않으면 '확실해요'. */
function AdCost({ r }: { r: Result }) {
  const m = r.verdict!.metrics.find((x) => x.key === "cpm");
  if (!m) return null;
  const arms = r.summary.arms.slice(0, 2);
  const lo = Math.min(m.a_interval[0], m.b_interval[0]) * 0.97, hi = Math.max(m.a_interval[1], m.b_interval[1]) * 1.03;
  const at = (x: number) => `${((x - lo) / (hi - lo || 1)) * 100}%`;
  const sure = m.word === "확실해요";
  return (
    <Card title={sure ? `광고비는 확실히 ${m.better}가 쌌어요` : "광고비 차이는 아직 몰라요"} badge={<VerdictBadge word={m.word} small />}
      summary="광고 1,000번 보여주는 데 드는 돈 (CPM) · 가능한 범위">
      <ul className="flex flex-col gap-3">
        {arms.map((a, i) => {
          const iv = i === 0 ? m.a_interval : m.b_interval;
          const mid = a.cpm ?? (iv[0] + iv[1]) / 2;
          const rec = "AB"[i] === m.better;
          return (
            <li key={a.name} className="flex flex-col gap-1">
              <p className="text-body"><b>{armName(a.name, i)}</b> <span className="text-soft">{band({ median: mid, lo: iv[0], hi: iv[1] }, "", won)}</span></p>
              <div className="relative h-4" aria-hidden="true">
                <div className={`absolute top-1/2 h-1.5 -translate-y-1/2 rounded-badge ${rec ? "bg-series-b" : "bg-series-a"}`} style={{ left: at(iv[0]), width: `calc(${at(iv[1])} - ${at(iv[0])})` }} />
                <span className="absolute top-1/2 size-3 -translate-x-1/2 -translate-y-1/2 rounded-badge bg-accent-ink" style={{ left: at(mid) }} />
              </div>
            </li>
          );
        })}
      </ul>
      <p className="flex justify-between text-caption text-soft"><span>{m.overlap ? "두 범위가 겹쳐요 → 아직 몰라요" : "두 범위가 안 겹쳐요 → 확실해요"}</span><span>← 쌈 · 비쌈 →</span></p>
    </Card>
  );
}

/** 날짜별 누적 확률: 결과가 굳어지는 중인지 오락가락하는지. 근거 없는 예측('하루 더 돌리면 90%')은 쓰지 않는다. */
function Days({ r }: { r: Result }) {
  const days = r.replay;
  if (!days.length) return null;
  const last = days[days.length - 1]!;
  const lastWord = last.word ?? wordOf(last.prob);
  // 마지막 날 이긴 쪽 기준 확률로 보여 준다 (B가 이기면 B가 나을 확률, A가 이기면 A가 나을 확률)
  const side = last.prob >= 0.5 ? "B" : "A";
  const of = (p: number) => (side === "B" ? p : 1 - p);
  const steady = days.length >= 2 && days.every((d, i) => i === 0 || of(d.prob) >= of(days[i - 1]!.prob) - 0.03);
  return (
    <Card title={steady ? `하루씩 쌓일수록 ${side} 쪽으로 굳어지고 있어요` : "하루씩 더해 보면 아직 오락가락해요"}
      summary={`손님 1명당 비용 기준 · ${side}가 나을 확률${lastWord === "확실해요" ? "" : " · 더 돌리면 '확실해요'까지 갈 수도 있지만 아직 장담은 못 해요"}`}>
      <ol className="flex flex-wrap items-center gap-2">
        {days.map((d, i) => (
          <li key={d.date} className="flex items-center gap-2">
            {i > 0 && <span aria-hidden="true" className="text-soft">→</span>}
            <span className="flex flex-col items-center gap-1 rounded-button bg-bg px-3 py-2">
              <span className="text-caption text-soft">{md(d.date)}</span>
              <b className="text-lead tabular-nums">{pct(of(d.prob))}</b>
              <VerdictBadge word={d.word ?? wordOf(d.prob)} small />
            </span>
          </li>
        ))}
      </ol>
      {lastWord !== "확실해요" && <p className="text-caption text-soft">날짜가 쌓일수록 한쪽으로 모이면 우연이 아닐 가능성이 커요 (Scott 2010).</p>}
    </Card>
  );
}

function PlacesLead({ r }: { r: Result }) {
  const top = r.placements[0];
  if (!top) return <Lead>노출 위치별 자료가 없어요</Lead>;
  return <Lead>누르는 정도는 보정해서 보면 자리마다 비슷하고, 돈은 {short(top.label)}에 {Math.floor(top.share * 10) * 10}% 넘게 몰렸어요</Lead>;
}

const short = (label: string) => label.replace("인스타그램", "인스타").replace("페이스북", "페북");

/** 노출 위치별 탭: 세트 × 노출 위치. 기본 열 = 보정한 값(1,000명 중 ○명), 실제 그대로는 옆에 작게.
 *  노출 100 미만 칸은 파랑 ● 참고만 배지 + 숫자 연하게 (ALT-22). 표 아래 고정 안내(알림 아님): 평균만 보고 끄지 말기. */
function Places({ r }: { r: Result }) {
  const rows: Placement[] = r.placements_by_set?.length ? r.placements_by_set : r.placements;
  const arms = r.summary.arms;
  const setName = (n?: string) => { const i = arms.findIndex((a) => a.name === n); return i >= 0 ? armName(n!, i) : "전체"; };
  const total = r.placements.reduce((x, p) => x + p.impressions, 0);
  const clicks = r.placements.reduce((x, p) => x + p.link_clicks, 0);
  const tops = arms.slice(0, 2).map((a, i) => {
    const mine = (r.placements_by_set ?? []).filter((p) => p.adset === a.name);
    const t = mine[0];
    return t ? `${"AB"[i]}는 100원 중 ${Math.round(t.share * 100)}원` : null;
  }).filter(Boolean);
  const an = (r.placements_by_set ?? r.placements).filter((p) => /Audience Network/i.test(p.placement)).reduce((x, p) => x + p.spend, 0);
  const top = r.placements[0];
  return (
    <>
      <Card title="어떤 노출 위치에서 잘 눌렸나요?" summary="1,000명이 보면 몇 명이 눌렀는지예요. 보여진 횟수가 적은 칸은 우연히 튀기 쉬워서 보정한 값을 먼저 보여 드려요">
        <div className="overflow-x-auto">
          <table className="w-full text-body">
            <thead><tr className="text-left text-caption text-soft">
              <th className="py-2 pr-3">세트</th><th className="pr-3">노출 위치</th><th className="pr-3 text-right">보여진 횟수</th>
              <th className="pr-3 text-right">1,000명 중 누른 사람 (보정)</th><th className="text-right">실제 그대로</th>
            </tr></thead>
            <tbody>
              {rows.map((p) => (
                <tr key={(p.adset ?? "") + p.placement} className="border-t border-line">
                  <td className="py-2 pr-3 whitespace-nowrap">{setName(p.adset)}</td>
                  <td className="pr-3">{short(p.label)}</td>
                  <td className={`pr-3 text-right tabular-nums ${p.reference_only ? "text-soft" : ""}`}>{p.impressions.toLocaleString()}</td>
                  <td className={`pr-3 text-right tabular-nums ${p.reference_only ? "text-soft" : "font-semibold"}`}>
                    {people(p.ctr_adjusted)}{p.reference_only && <ReferenceBadge />}
                  </td>
                  <td className="text-right text-caption text-soft tabular-nums">{p.ctr == null ? "–" : `${Math.round(p.ctr * 1000)}명`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="rounded-button border border-line px-4 py-3 text-body">평균이 나쁜 자리를 바로 끄지 마세요. 메타는 '다음 손님 1명에 드는 돈'을 보고 돈을 나눠요.</p>
      </Card>
      {top && (
        <Card title="돈이 몰린 곳" summary={tops.length ? `${tops.join(", ")}이 ${short(top.label)}에서 나갔어요` : `100원 중 ${Math.round(top.share * 100)}원이 ${short(top.label)}에서 나갔어요`}>
          <p className="text-body text-soft">Audience Network는 {won(an)}{tops.length > 1 ? " (두 세트 모두)" : ""}</p>
        </Card>
      )}
      <HowCalculated title="보정이 뭔가요?" easy={`보여진 횟수가 적은 칸은 우연히 튀기 쉬워서, 전체 평균(1,000명 중 ${total ? Math.round((clicks / total) * 1000) : "–"}명) 쪽으로 당겨서 보여줘요.`}>
        <p>경험적 베이즈 축소 추정 (Efron & Morris 1975): (클릭 + 평균 클릭률 × 강도) ÷ (노출 + 강도). 강도는 칸 사이 실제 차이에서 추정해요.</p>
        <p>보여진 횟수 100 미만 칸은 '참고만'으로 표시하고, 판정(90/70%)에는 넣지 않아요. 평균이 나쁜 자리를 끄지 말라는 안내는 Breakdown effect 때문이에요.</p>
      </HowCalculated>
    </>
  );
}

