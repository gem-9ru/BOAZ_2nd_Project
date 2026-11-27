import type { ReactNode } from "react";
import type { Result } from "../api";
import { Fold, Folds, josa, pct, people, Sub, TestTag, VerdictBadge, won } from "../ui";
import { FunnelDetail, funnelPreview } from "./WhyFunnel";
import { SettingsDetail, settingPreview } from "./WhySettings";
import { CostPerCustomer, Method, Places, PlacesLead, short } from "./WhyCompare";
import { armName, SignalTag } from "./shared";
import { sameMoney } from "./shared";

/** ② 왜 그런지 (최종안 · 기존 AN-02 + AN-03 + AN-04 합침): 이유 3장, 장마다 문장 1줄 + 근거 그래프 1개 + 판정 배지 → '더 자세히' 접기 1개.
 *  ① 릴스로 간 돈 ② 방문 1명당 비용(○ 쪽이에요, 날짜별로 굳어지는 한 줄) ③ 광고비 범위(안 겹치면 확실해요) + 메타 권장과 다른 실측 한 줄.
 *  지표 이름(CPM·CTR) 없이 사장님 말로. 기존 화면 내용은 지우지 않고 '더 자세히' 안으로. */
export function Why({ r }: { r: Result }) {
  const c = r.matrix.change ?? r.next.change;
  const keep = r.matrix.keep[0];
  const v = r.verdict;
  const arms = r.summary.arms.slice(0, 2);
  const names = arms.map((a, i) => armName(a.name, i));
  const same = sameMoney(r);
  const cpm = v?.metrics.find((m) => m.key === "cpm");
  const top = r.placements[0];
  const meta = r.alerts.find((a) => a.kind === "meta_vs_measured");
  const act = r.matrix.rows.find((x) => x.row === "4");
  const few = r.alerts.find((a) => a.kind === "small_sample") as { actions?: number } | undefined;
  const label = (r.summary as { action_label?: string | null }).action_label;
  const days = r.replay;
  const side = days.length && days[days.length - 1]!.prob < 0.5 ? "A" : "B";
  const of = (p: number) => (side === "B" ? p : 1 - p);
  const costs = arms.map((a) => (a.landing_page_views ? a.spend / a.landing_page_views : null));
  const m = v?.metrics.find((x) => x.key === v.badge.metric);
  const win = v ? names["AB".indexOf(v.badge.better)] ?? v.badge.better : "";
  const cheap = cpm ? names["AB".indexOf(cpm.better)] ?? cpm.better : "";
  const placementKeep = keep?.field_id === "meta.adset.placements";

  return (
    <>
      <div className="flex flex-col gap-3">
      <Reason n={1} first graph={top && (c.rule?.row ?? c.row) === "5" && (
          <Bars label="노출 위치별로 나간 돈" rows={[
            { name: short(top.label), value: top.share, text: pct(top.share), on: true },
            { name: "나머지 자리", value: 1 - top.share, text: pct(1 - top.share) },
          ]} />
        )} tag={<TestTag text={c.tag ?? "테스트 제안"} />} sub={c.field_id === "meta.ad.media" && c.now ? `소재는 ${c.now}${batchim(c.now) ? "이었어요" : "였어요"} → 이번에 테스트할 칸` : "→ 이번에 테스트할 칸"}>
        {reasonOne(r)}
      </Reason>
      {/* ①b 세트 1개: 이유 2·3은 A/B 비교 대신 '기준 대비' 문장 (같은 틀, 배지 대신 ✓ / ↓ / – 신호) */}
      {r.summary.arms.length === 1 && (r.baseline ?? []).map((b, i) => (
        <Reason key={b.key} n={i + 2} tag={<SignalTag signal={b.signal} />}
          sub={`기준 ${b.standard}${b.why ? ` · ${b.why}` : ""}`}
          graph={b.key === "visit_rate" && <Bars label={`${b.label} (기준 ${b.standard})`} rows={[{ name: "내 세트", value: b.value, text: b.text.split(" (")[0]!, on: b.signal === "ok" }]} />}>
          {b.label}: {b.text}
        </Reason>
      ))}
      {v && same && m && (
        <Reason n={2} graph={<>
            <Bars label="방문 1명당 비용 (짧을수록 좋아요)" rows={arms.map((_, i) => ({ name: `방문 1명당 ${"AB"[i]}`, value: (costs[i] ?? 0) / Math.max(...costs.map((x) => x ?? 0), 1), text: won(costs[i]), on: "AB"[i] === v.badge.better }))} />
            <p className="mt-1.5 text-caption font-medium text-soft">{v.badge.better}가 나을 확률 <b className="text-ink">{pct(v.badge.better === "B" ? m.prob_b_better : 1 - m.prob_b_better)}</b>
              {days.length > 1 && ` · 날짜가 쌓일수록 ${days.map((d) => pct(of(d.prob))).join(" → ")}로 ${side} 쪽으로 ${of(days[days.length - 1]!.prob) >= of(days[0]!.prob) ? "굳어지는 중" : "오락가락하는 중"}`}</p>
          </>} tag={<VerdictBadge word={v.badge.word} small />}
          sub={`세트당 ${won(same.base)}으로 방문자 A ${same.counts[0]}명 · B ${same.counts[1]}명`}>
          {v.badge.word === "아직 몰라요" ? "같은 돈으로 온 방문자는 아직 비슷해요" : `같은 돈으로 방문자를 ${paren(win)}가 더 데려왔어요`}
        </Reason>
      )}
      {cpm && arms.length === 2 && (
        <Reason n={3} graph={<>
            <Bars label="광고 1,000번 보여 주는 데 드는 돈 (짧을수록 좋아요)" rows={arms.map((a, i) => ({ name: names[i]!, value: (a.cpm ?? 0) / Math.max(...arms.map((x) => x.cpm ?? 0), 1), text: won(a.cpm), on: "AB"[i] === cpm.better }))} />
            <p className="mt-1.5 text-caption font-medium text-soft">{arms.map((_, i) => { const iv = i ? cpm.b_interval : cpm.a_interval; return `${"AB"[i]} 적게 ${won(iv[0])} ~ 많이 ${won(iv[1])}`; }).join(" · ")}</p>
            {placementKeep && meta && <p className="mt-2 rounded-button bg-belly px-3 py-2 text-caption text-belly-ink"><span aria-hidden="true">💡 </span>메타는 '자동'을 권했지만, 우리가 돌려 본 2번 모두 수동이 쌌어요 (베이커리 실험 1은 36%) → 노출 위치는 지금처럼 그대로</p>}
          </>} tag={<VerdictBadge word={cpm.word} small />}
          sub={`광고 1,000번 보여 주는 데 드는 돈 · ${cpm.overlap ? "두 범위가 겹쳐요" : "두 범위가 안 겹쳐요"}`}>
          {cpm.word === "확실해요" ? `광고비 자체는 확실히 ${cheap.split(" ")[0]}가 쌌어요` : "광고비 차이는 아직 몰라요"}
        </Reason>
      )}
      </div>
      {act?.status === "skip" && <p className="-mt-1 pl-1 text-label text-soft">들어온 뒤 행동{label && few?.actions != null ? `(${label} ${few.actions}건)` : ""}은 아직 몰라요</p>}

      {/* 최종안: 접기는 '더 자세히' 1개. 열면 단계별 신호 · 노출 위치별 클릭 · 내 세팅 칸별 상태 · 계산 방법 */}
      <Folds label="더 자세히">
        <Fold label="더 자세히" preview="단계별 신호 · 노출 위치별 클릭 · 내 세팅 칸별 상태 · 계산 방법">
          <Sub title="어디서 막혔나 · 단계별 신호" note={funnelPreview(r)}><FunnelDetail r={r} /></Sub>
          {top && <Sub title="노출 위치별 클릭" note={`${short(top.label)} 1,000번 보이면 ${people(top.ctr_adjusted, 1000, "번")}`}><PlacesLead r={r} /><Places r={r} /></Sub>}
          <Sub title="내 세팅 칸별 상태" note={settingPreview(r)}><SettingsDetail r={r} /></Sub>
          <Sub title="계산 방법 · 근거" note="베이지안 · 논문 · 한계">{v && <CostPerCustomer r={r} />}<Method r={r} /></Sub>
        </Fold>
      </Folds>
    </>
  );
}


const paren = (s: string) => (s.includes(" ") ? `${s.replace(" ", "(")})` : s);   // 'B 수동' → 'B(수동)'

/** 이유 1 (최종안): '돈이 인스타 릴스로 갔는데, 세로 소재가 없었어요' (설정을 받았을 때) · 아니면 서버 이유의 첫 문장 */
function reasonOne(r: Result): string {
  const c = r.matrix.change ?? r.next.change;
  const top = r.placements[0];
  if ((c.rule?.row ?? c.row) === "5" && top && (c.reason ?? "").includes("없었어요")) return `돈이 ${short(top.label)}로 갔는데, ${josa(c.what ?? "맞는 소재", "이가")} 없었어요`;
  return firstSentence(c.reason ?? c.note);
}

/** 이유 한 줄: 번호 · 굵은 문장 + 작은 설명 · 끝에 판정 배지(또는 테스트 제안 태그). */
/** 문장 → 작은 설명 → 근거 그래프 순서 (시안 '문장 1줄 + 근거 그래프 1개 + 판정 배지') */
function Reason({ n, children, sub, tag, first, graph }: { n: number; children: ReactNode; sub: string; tag?: ReactNode; first?: boolean; graph?: ReactNode }) {
  return (
    // 휴대폰: 번호 · 문장만 한 줄, 배지는 문장 아래, 그래프는 카드 너비 전체 (좁은 칸에 갇히지 않게)
    <section className={`grid grid-cols-[auto_1fr] items-start gap-x-4 gap-y-2 rounded-card bg-surface px-5 py-4 shadow-card sm:grid-cols-[auto_1fr_auto] ${first ? "border-2 border-accent" : "border border-line"}`}>
      <span aria-hidden="true" className={`grid size-10 shrink-0 place-items-center rounded-button text-lead font-extrabold ${first ? "bg-accent text-on-accent" : "bg-accent-soft text-accent"}`}>{n}</span>
      <p className="min-w-0 text-body font-bold leading-snug">{children}<span className="mt-1 block text-label font-medium text-soft">{sub}</span></p>
      {tag && <span className="col-start-2 justify-self-start sm:col-start-3 sm:row-start-1">{tag}</span>}
      {graph && <div className="col-span-2 min-w-0 sm:col-span-1 sm:col-start-2">{graph}</div>}
    </section>
  );
}

/** 한 줄 답: '돈은 릴스로 갔는데 세로 소재가 없었고, 나머지 설정은 괜찮았어요' (결론 규칙 번호에 따라) */
export function answer(r: Result): string {
  const c = r.matrix.change ?? r.next.change;
  const row = c.rule?.row ?? c.row;
  const top = r.placements[0];
  if (row === "5" && top) {
    const spot = short(top.label).replace(/^(인스타|페북) /, "");
    return (c.reason ?? "").includes("없었어요") ? `돈은 ${spot}로 갔는데 ${josa(c.what ?? "맞는 소재", "이가")} 없었고, 나머지 설정은 괜찮았어요`
      : `돈은 ${spot}로 몰렸고, 나머지 설정은 괜찮았어요`;
  }
  if (row === "-") return "크게 막힌 곳이 없어서 문구 하나만 바꿔 비교해 봐요";
  const stage = r.matrix.rows.find((x) => x.row === row)?.stage;
  return stage ? `'${stage}' 단계에서 처음 막혔어요` : (c.reason ?? c.note);
}

/** '…나갔는데, 세로 소재가 없었어요.' → '…나갔어요' / '…나갔어요. 그 자리에 …' → '…나갔어요' */
function firstSentence(s: string): string {
  return s.split(". ")[0]!.replace(/\.$/, "").replace(/는데, .*$/, "어요");
}

function batchim(w: string): boolean {
  const c = w.trim().slice(-1).charCodeAt(0);
  return c >= 0xac00 && c <= 0xd7a3 && (c - 0xac00) % 28 !== 0;
}

/** 근거 막대 (가로): 이긴 쪽·주인공은 보라, 나머지는 옅은 회보라. 숫자는 막대 옆 글자로도 (색만으로 말하지 않음). */
function Bars({ label, rows }: { label: string; rows: { name: string; value: number; text: string; on?: boolean }[] }) {
  return (
    <figure className="mt-3 flex flex-col gap-1.5" aria-label={`${label}: ${rows.map((x) => `${x.name} ${x.text}`).join(", ")}`}>
      {rows.map((x) => (
        <div key={x.name} aria-hidden="true" className="grid grid-cols-[minmax(0,7rem)_minmax(3rem,1fr)_auto] items-center gap-2 text-caption">
          <span className={x.on ? "font-bold text-ink" : "text-soft"}>{x.name}</span>
          <span className="h-2.5 rounded-badge bg-sunk"><i className={`block h-full rounded-badge ${x.on ? "bg-accent" : "bg-series-soft"}`} style={{ width: `${Math.max(2, x.value * 100)}%` }} /></span>
          <b className={`text-right tabular-nums ${x.on ? "text-accent" : "text-soft"}`}>{x.text}</b>
        </div>
      ))}
    </figure>
  );
}

