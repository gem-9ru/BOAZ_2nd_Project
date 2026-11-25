import type { ReactNode } from "react";
import type { Result } from "../api";
import { Card, HowCalculated, md, TestTag, VerdictBadge, won } from "../ui";
import { CertaintyBadge } from "./Certainty";
import { armName, Lead, sameMoney } from "./shared";

/** AN-01 확인 + 결론 (v4.2): 첫 화면에 '테스트할 칸 1개'. 돌려 본 적 없는 선택지는 예상하지 않고
 *  '두 세트로 직접 비교'를 제안(테스트 제안 태그, 판정 배지 없음). 판정 배지는 실측이 있는 카드(유지)에만. */
export function AN01({ r, onApply, onOpenSetting }: { r: Result; onApply: () => void; onOpenSetting?: (fieldId: string) => void }) {
  const m = r.matrix;
  const c = m.change ?? r.next.change;
  const read = r.check.read;
  const keep = m.keep[0];
  const watch = m.watch[0];
  const dont = m.dont[0];
  const same = sameMoney(r);
  const badge = r.verdict?.badge;
  const arms = r.summary.arms;
  const spend = arms.reduce((x, a) => x + a.spend, 0);
  const imps = arms.reduce((x, a) => x + a.impressions, 0);
  const clicks = arms.reduce((x, a) => x + a.link_clicks, 0);
  const off = r.alerts.filter((a) => a.kind === "no_delivery").length;
  const period = r.check.period;
  const untested = c.tested === false || !!c.tag;
  return (
    <>
      <Lead>나머지 칸은 그대로 둬야 무엇 덕분인지 알 수 있어요</Lead>
      <section aria-label="테스트할 칸" className="flex flex-col gap-3 rounded-card border-2 border-accent bg-accent-soft p-card">
        <p className="text-caption font-semibold text-accent-ink">{c.path ?? c.label}</p>
        <p className="flex flex-wrap items-center gap-2 text-title font-bold leading-snug">
          {c.new}
          {untested ? <TestTag text={c.tag ?? "테스트 제안"} /> : c.certainty && <CertaintyBadge level={c.certainty.level} better={badge?.better} />}
        </p>
        {c.test && <p className="text-body">{c.test} {c.reason}</p>}
        {!c.test && <p className="text-body">{c.reason ?? c.note}</p>}
        {c.now && <p className="text-body text-soft">지금 값: {c.now}</p>}
        {c.unknown && <p className="text-body text-soft">{c.unknown}</p>}
        <div><button type="button" onClick={onApply} className="h-button rounded-button bg-button px-5 text-body font-semibold text-button-fg hover:bg-button-hover">이 테스트 바로 준비 →</button></div>
      </section>
      <ul className="grid gap-3 sm:grid-cols-3" aria-label="나머지 칸">
        <Mini tag="유지" field={keep?.field_id} onOpen={onOpenSetting} title={keep ? `${keep.path.split(" › ").pop()} = ${keep.value}` : "바꿀 이유가 없는 칸"}>
          {keep && same && badge
            ? <><span>같은 돈으로 손님 A {same.counts[0]}명 · B {same.counts[1]}명</span> <VerdictBadge word={badge.word} small /></>
            : keep ? keep.reason : "이번 결과로는 없어요"}
        </Mini>
        <Mini tag="지켜보기" field={watch?.field_id} onOpen={onOpenSetting} title={watch ? watch.title ?? watch.path.split(" › ").pop()! : "없어요"}>{watch?.text ?? "이번엔 없어요"}</Mini>
        <Mini tag="하지 말기" title={dont ? dont.split(" — ")[0]! : "없어요"}>{dont?.split(" — ")[1] ?? ""}</Mini>
      </ul>
      <p className="flex flex-wrap items-center gap-2 text-caption text-soft">
        <span aria-hidden="true" className="font-bold text-ok">✓</span>
        파일 확인 · 기간 {period ? `${md(period.first)}~${md(period.last).split("/").pop()} ` : ""}({read.days}일) · 광고 세트 {read.adsets}개 · 광고비 {won(spend)} · 보여진 횟수 {imps.toLocaleString()}번 · 클릭 {clicks.toLocaleString()}번
        {off > 0 && <> · 안 보여진 날 {off}일 <span aria-label="주의" title="주의: 광고가 안 나간 날이 있어요" className="font-bold text-warn">▲</span></>}
        {!r.check.totals.every((t) => t.match) && " · 합계가 안 맞아요"}
      </p>
      <HowCalculated title="왜 이 칸인가요?">
        {(c.rule?.row ?? c.row) === "-"
          ? <p>위에서부터 막힌 단계도, 돈이 몰린 자리도 없어서 문구 하나만 바꿔 비교하는 걸 제안해요.</p>
          : <p>진단 규칙 {c.rule?.row ?? c.row ?? "–"}번: {m.rows.find((x) => x.row === (c.rule?.row ?? c.row))?.signal ?? c.reason}</p>}
        <p>위에서부터(게재 → 보이는 값 → 누르는 정도 → 페이지 도착 → 행동) 처음 막힌 단계의 칸을 고르고, 막힌 곳이 없으면 돈이 몰린 자리에 맞는 소재를 제안해요.</p>
        {c.rule && <p>근거: {c.rule.why}{c.grade ? ` (근거 ${c.grade})` : ""} · 자세한 확실도는 ⑥ 보내기의 근거 탭에 있어요</p>}
        {c.meta_says && <p>메타 신호: {c.meta_says}</p>}
        {badge && <p>비교한 세트: {arms.map((a, i) => `${armName(a.name, i)} (${a.name})`).join(" · ")}</p>}
      </HowCalculated>
    </>
  );
}

/** 유지 · 지켜보기 · 하지 말기 작은 카드. 칸이 있는 카드는 누르면 AN-03 내 세팅 카드의 그 행으로 간다. */
function Mini({ tag, title, children, field, onOpen }: { tag: string; title: string; children: ReactNode; field?: string; onOpen?: (fieldId: string) => void }) {
  const body = (
    <>
      <span className="text-caption font-semibold text-soft">{tag}</span>
      <h3 className="text-body font-bold">{title}</h3>
      <span className="flex flex-wrap items-center gap-1.5 text-caption">{children}</span>
      {field && onOpen && <span className="text-caption text-accent-ink">내 세팅 카드에서 보기 →</span>}
    </>
  );
  return (
    <li className="flex">
      {field && onOpen ? (
        <button type="button" onClick={() => onOpen(field)} className="flex w-full flex-col items-start gap-1 rounded-button border border-line bg-surface px-4 py-3 text-left hover:border-accent">{body}</button>
      ) : <div className="flex w-full flex-col gap-1 rounded-button border border-line bg-surface px-4 py-3">{body}</div>}
    </li>
  );
}
