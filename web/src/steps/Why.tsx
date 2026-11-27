import type { ReactNode } from "react";
import type { Metric, Result } from "../api";
import { Fold, Folds, josa, md, pct, people, TestTag, VerdictBadge, won, wordOf } from "../ui";
import { FunnelDetail, funnelPreview } from "./WhyFunnel";
import { SettingsDetail, settingPreview } from "./WhySettings";
import { CostPerCustomer, Method, Places, PlacesLead, short } from "./WhyCompare";
import { armName } from "./shared";
import { sameMoney } from "./shared";

/** ② 왜 그런지 (축소안 v5 · 기존 AN-02 + AN-03 + AN-04 합침): 한 줄 답 → 이유 3줄(판정 배지로 끝나는 문장) → 접기 6줄.
 *  지표 이름(CPM·CTR) 없이 사장님 말로. 기존 화면 내용은 지우지 않고 접기 안으로. */
export function Why({ r }: { r: Result }) {
  const c = r.matrix.change ?? r.next.change;
  const keep = r.matrix.keep[0];
  const v = r.verdict;
  const arms = r.summary.arms.slice(0, 2);
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

  const [keepWord, keepBadge] = (keep?.reason ?? "").split(" · ");
  const keepValue = keep?.value.split(",")[0]!.trim();
  const costs = arms.map((a) => (a.landing_page_views ? a.spend / a.landing_page_views : null));
  const m = v?.metrics.find((x) => x.key === v.badge.metric);

  return (
    <>
      <div className="flex flex-col gap-3">
      <Reason n={1} first graph={top && (c.rule?.row ?? c.row) === "5" && (
          <Bars label="노출 위치별로 나간 돈" rows={[
            { name: short(top.label), value: top.share, text: pct(top.share), on: true },
            { name: "나머지 자리", value: 1 - top.share, text: pct(1 - top.share) },
          ]} />
        )} tag={<TestTag text={c.tag ?? "테스트 제안"} />} sub={c.field_id === "meta.ad.media" && c.now ? `그런데 소재는 ${c.now}${batchim(c.now) ? "이었어요" : "였어요"} → 이번에 테스트할 칸` : "→ 이번에 테스트할 칸"}>
        {firstSentence(c.reason ?? c.note)}
      </Reason>
      {keep && keepValue && (
        <Reason n={2} graph={cpm && <Ranges m={cpm} names={arms.map((a, i) => armName(a.name, i))} />} tag={keepBadge && <VerdictBadge word={keepBadge} small />}
          sub={keep.field_id === "meta.adset.placements" && meta
            ? "메타는 '자동'을 권했지만, 우리가 돌려 본 2번 모두 수동이 쌌어요 (희수 실험은 36%)"
            : "지금처럼 그대로 두세요"}>
          {keep.title ?? `${josa(keep.path.split(" › ").pop()!, "은는")} ${josa(keepValue, "이가")} ${keepWord!.replace("싸요", "쌌어요")}`}
        </Reason>
      )}
      {v && same && m && (
        <Reason n={keep ? 3 : 2} graph={<>
            <Bars label="방문 1명당 비용 (짧을수록 좋아요)" rows={arms.map((a, i) => ({ name: `방문 1명당 ${"AB"[i]}`, value: (costs[i] ?? 0) / Math.max(...costs.map((x) => x ?? 0), 1), text: won(costs[i]), on: "AB"[i] === v.badge.better }))} />
            {days.length > 1 && <p className="mt-1.5 text-caption font-medium text-soft">날짜가 쌓일수록 {days.map((d) => pct(of(d.prob))).join(" → ")}로 {side} 쪽으로 {of(days[days.length - 1]!.prob) >= of(days[0]!.prob) ? "굳어지는 중" : "오락가락하는 중"}</p>}
          </>} tag={<VerdictBadge word={v.badge.word} small />}
          sub={`방문 1명당 A ${won(costs[0])} · B ${won(costs[1])} · ${v.badge.better}가 나을 확률 ${pct(v.badge.better === "B" ? m.prob_b_better : 1 - m.prob_b_better)}`}>
          같은 돈({won(same.base)})으로 방문자 A {same.counts[0]}명 · B {same.counts[1]}명
        </Reason>
      )}
      </div>
      {act?.status === "skip" && <p className="-mt-1 pl-1 text-label text-soft">들어온 뒤 행동{label && few?.actions != null ? `(${label} ${few.actions}건)` : ""}은 아직 몰라요</p>}

      <Folds title="궁금하면 열어 보세요">
        <Fold label="어디서 막혔나 · 단계별 신호" preview={funnelPreview(r)}><FunnelDetail r={r} /></Fold>
        {days.length > 0 && (
          <Fold label="날짜별로 확률이 어떻게 굳어졌나" preview={days.map((d) => `${md(d.date)} ${pct(of(d.prob))}`).join(" → ")}>
            <div className="flex flex-wrap items-end gap-4">
              <div className="relative flex h-40 items-end gap-5 px-1" role="img" aria-label={days.map((d) => `${md(d.date)} ${pct(of(d.prob))} ${d.word ?? wordOf(d.prob)}`).join(", ")}>
                {/* 점선 = 70% (방향이 보이는 선). 막대 높이 = 그날까지의 확률 (위 글자칸 2.5rem 빼고) */}
                <span aria-hidden="true" className="absolute inset-x-0 border-t-2 border-dashed border-belly-strong" style={{ bottom: `calc(2.75rem + (100% - 2.75rem) * 0.7)` }} />
                {days.map((d, i) => (
                  <div key={d.date} aria-hidden="true" className="flex h-full w-30 flex-col items-center justify-end whitespace-nowrap text-caption">
                    <i className={`block w-11 rounded-t-button rounded-b-mark ${i === days.length - 1 ? "bg-accent" : "bg-accent-line"}`} style={{ height: `calc((100% - 2.75rem) * ${of(d.prob)})` }} />
                    <span className="flex h-11 flex-col items-center justify-start pt-1.5 leading-tight"><b className="text-label">{pct(of(d.prob))}</b>{md(d.date)} · {d.word ?? wordOf(d.prob)}</span>
                  </div>
                ))}
              </div>
              <p className="min-w-40 flex-1 self-center text-label text-soft">점선 = 70% (방향이 보이는 선) · {side}가 나을 확률{of(days[0]!.prob) < 0.5 && days.length > 1 ? <><br />하루치만 보고 골랐다면 반대쪽을 골랐을 거예요</> : ""}</p>
            </div>
          </Fold>
        )}
        {top && (
          <Fold label="노출 위치별 클릭" preview={`${short(top.label)} 1,000번 보이면 ${people(top.ctr_adjusted, 1000, "번")}`}>
            <PlacesLead r={r} /><Places r={r} />
          </Fold>
        )}
        <Fold label="내 세팅 칸별 상태" preview={settingPreview(r)}><SettingsDetail r={r} /></Fold>
        <Fold label="계산 방법 · 근거" preview="베이지안 · 논문 · 한계">
          {v && <CostPerCustomer r={r} />}
          <Method r={r} />
        </Fold>
      </Folds>
    </>
  );
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

/** 광고비 범위 (CPM 95%): 두 세트 범위를 한 눈금 위에. 안 겹치면 '확실해요'. */
function Ranges({ m, names }: { m: Metric; names: string[] }) {
  const ivs = [m.a_interval, m.b_interval];
  const lo = Math.min(...ivs.map((x) => x[0])) * 0.97, hi = Math.max(...ivs.map((x) => x[1])) * 1.03;
  const at = (x: number) => ((x - lo) / (hi - lo || 1)) * 100;
  return (
    <figure className="mt-3 flex flex-col gap-1.5" aria-label={`광고 1,000번 보여주는 데 드는 돈 범위: ${ivs.map((x, i) => `${names[i]} ${won(x[0])}~${won(x[1])}`).join(", ")}`}>
      <figcaption className="mt-1 text-caption text-soft">광고 1,000번 보여주는 데 드는 돈 · {m.overlap ? "두 범위가 겹쳐요" : "두 범위가 안 겹쳐요"}</figcaption>
      {ivs.map((x, i) => {
        const on = "AB"[i] === m.better;
        return (
          <div key={i} aria-hidden="true" className="grid grid-cols-[minmax(0,7rem)_minmax(3rem,1fr)_auto] items-center gap-2 text-caption">
            <span className={on ? "font-bold text-ink" : "text-soft"}>{names[i]}</span>
            <span className="relative h-2.5 rounded-badge bg-sunk"><i className={`absolute inset-y-0 block rounded-badge ${on ? "bg-accent" : "bg-series-soft"}`} style={{ left: `${at(x[0])}%`, width: `${at(x[1]) - at(x[0])}%` }} /></span>
            <b className={`whitespace-nowrap text-right tabular-nums ${on ? "text-accent" : "text-soft"}`}>{won(x[0])}~{won(x[1])}</b>
          </div>
        );
      })}
    </figure>
  );
}
