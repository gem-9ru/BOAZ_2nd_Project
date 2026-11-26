import type { ReactNode } from "react";
import type { Result } from "../api";
import { Fold, Folds, josa, md, pct, people, TestTag, VerdictBadge, won, wordOf } from "../ui";
import { FunnelDetail, funnelPreview } from "./AN02";
import { SettingsDetail, settingPreview } from "./AN03";
import { AdCost, CostPerCustomer, Method, Places, PlacesLead, short } from "./AN04";
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
      <Reason n={1} first tag={<TestTag text={c.tag ?? "테스트 제안"} />} sub={c.field_id === "meta.ad.media" && c.now ? `그런데 소재는 ${c.now}${batchim(c.now) ? "이었어요" : "였어요"} → 이번에 테스트할 칸` : "→ 이번에 테스트할 칸"}>
        {firstSentence(c.reason ?? c.note)}
      </Reason>
      {keep && keepValue && (
        <Reason n={2} tag={keepBadge && <VerdictBadge word={keepBadge} small />}
          sub={keep.field_id === "meta.adset.placements" && meta
            ? "메타는 '자동'을 권했지만, 우리가 돌려 본 2번 모두 수동이 쌌어요 (희수 실험은 36%)"
            : "지금처럼 그대로 두세요"}>
          {keep.title ?? `${josa(keep.path.split(" › ").pop()!, "은는")} ${josa(keepValue, "이가")} ${keepWord!.replace("싸요", "쌌어요")}`}
        </Reason>
      )}
      {v && same && m && (
        <Reason n={keep ? 3 : 2} tag={<VerdictBadge word={v.badge.word} small />}
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
        {cpm && (
          <Fold label="광고비 범위" preview={`A ${won(cpm.a_interval[0])}~${won(cpm.a_interval[1])} · B ${won(cpm.b_interval[0])}~${won(cpm.b_interval[1])}`}>
            <AdCost r={r} />
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
function Reason({ n, children, sub, tag, first }: { n: number; children: ReactNode; sub: string; tag?: ReactNode; first?: boolean }) {
  return (
    <section className={`flex items-center gap-4 rounded-card bg-surface px-5 py-4 shadow-card ${first ? "border-2 border-accent" : "border border-line"}`}>
      <span aria-hidden="true" className={`grid size-10 shrink-0 place-items-center rounded-button text-lead font-extrabold ${first ? "bg-accent text-on-accent" : "bg-accent-soft text-accent"}`}>{n}</span>
      <p className="flex-1 text-body font-bold leading-snug">{children}<span className="mt-1 block text-label font-medium text-soft">{sub}</span></p>
      {tag}
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
