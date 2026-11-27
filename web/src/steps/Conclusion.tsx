import type { Change, Result } from "../api";
import { AlertMark, BigButton, Fold, Folds, GRADE_LABEL, josa, md, TestTag, VerdictBadge, won } from "../ui";
import { Mungchi } from "../ui/Mungchi";
import { armName, SIGNAL_WORD } from "./shared";

/** ① 결론 (축소안 v5 · 기존 AN-01): 결론 카드 1장 + 주 버튼 [이 테스트 준비하기 →] + 나머지 칸 요약 2개 + 접기 2줄.
 *  결론은 돌려 본 적 없는 선택지라 판정 배지 대신 '테스트 제안' 태그. 숫자는 이유 한 줄 속 하나만. */
export function Conclusion({ r, onPrep }: { r: Result; onPrep: () => void }) {
  const m = r.matrix;
  const c = m.change ?? r.next.change;
  const keep = m.keep[0];
  const watch = [...m.watch].sort((a, b) => Number(b.field_id.endsWith("end_date")) - Number(a.field_id.endsWith("end_date")));   // 시작 날짜 → 예산 순
  const read = r.check.read;
  const arms = r.summary.arms;
  const spend = arms.reduce((x, a) => x + a.spend, 0);
  const clicks = arms.reduce((x, a) => x + a.link_clicks, 0);
  const imps = arms.reduce((x, a) => x + a.impressions, 0);
  const off = r.alerts.filter((a) => a.kind === "no_delivery").length;
  const period = r.check.period;
  const days = period ? `${md(period.first)}~${md(period.last).split("/").pop()}` : `${read.days}일`;
  const [keepWord, keepBadge] = (keep?.reason ?? "").split(" · ");
  const row = c.rule?.row ?? c.row;
  const one = arms.length === 1;   // ①b 세트가 1개: 비교 대신 기준값
  const base = [...(r.baseline ?? [])].sort((x, y) => ORDER.indexOf(x.key) - ORDER.indexOf(y.key)).slice(0, 2);
  return (
    <>
      <section aria-label="테스트할 칸" className="relative flex flex-col items-start gap-2 rounded-card border-2 border-accent bg-surface p-card shadow-hero sm:pr-56">
        <span aria-hidden="true" className="absolute top-4 right-36 rounded-button rounded-br-mark bg-accent-soft px-3 py-1.5 text-caption font-bold text-accent max-sm:hidden">여기예요!</span>
        <Mungchi pose="point" className="absolute right-5 bottom-3 w-40 max-sm:hidden" />
        <p className="rounded-badge bg-accent-faint px-2.5 py-1 text-caption font-bold text-accent">{c.path ?? c.label}</p>
        <p className="flex flex-wrap items-center gap-2 text-headline font-extrabold leading-snug">{headline(c)} <TestTag text={c.tag ?? "테스트 제안"} /></p>
        <p className="text-body leading-relaxed">{boldPct(c.reason ?? c.note)}</p>
        {one ? <p className="text-label text-soft">세트가 1개라 비교할 대상이 없었어요. 이번에 두 세트로 돌리면 처음으로 '어느 쪽이 나은지'를 알 수 있어요.</p>
          : c.unknown && <p className="text-label text-soft">{c.unknown}</p>}
        <div className="pt-3"><BigButton onClick={onPrep}>이 테스트 준비하기 →</BigButton></div>
      </section>
      {one && base.length > 0 && <>
        <ul className="grid gap-3.5 sm:grid-cols-2" aria-label="기준값과 비교">
          {base.map((b) => (
            <li key={b.key} className="flex flex-col items-start gap-1 rounded-card border border-line bg-surface px-5 py-4 text-label shadow-card">
              <b className={`text-title font-extrabold ${b.signal === "ok" ? "text-ok-ink" : b.signal === "low" ? "text-accent-ink" : "text-hold"}`}>{SIGNAL_WORD[b.signal]}</b>
              <b className="mt-1 text-body">{b.label}</b>
              <span>{b.text} · 기준 {b.standard}</span>
              {b.why && <span className="text-caption text-soft">{b.why}</span>}
            </li>
          ))}
        </ul>
        <p className="flex items-start gap-2 rounded-soft border-[1.5px] border-info-line bg-info-bg px-4 py-2.5 text-label text-info-ink">
          <AlertMark level="info" />
          <span>세트가 1개일 때는 <b>'확실해요 / ○ 쪽이에요'가 나오지 않아요.</b> 대신 기준값과 비교해 ✓ 괜찮아요 / ↓ 기준보다 낮아요 / – 아직 몰라요로만 보여 줘요. 클릭이 30번이 안 되면 숫자가 좋아 보여도 '– 아직 몰라요'예요.</span>
        </p>
      </>}
      {!(one && base.length > 0) && <ul className="grid gap-3.5 sm:grid-cols-2" aria-label="나머지 칸">
        <li className="flex flex-col items-start gap-1 rounded-card border border-line bg-surface px-5 py-4 text-label shadow-card">
          <Tag tone="keep">✓ 그대로</Tag>
          {keep ? <>
            <b className="mt-1.5 text-body">{keep.title ?? `${keep.path.split(" › ").pop()} = ${keep.value.split(/[(,]/)[0]!.trim()}`}</b>
            <span className="flex flex-wrap items-center gap-1.5">{(keepWord ?? "").replace("광고비 ", "광고비가 ").replace("싸요", "쌌어요")}{keepBadge && <VerdictBadge word={keepBadge} small />}</span>
          </> : <span className="text-soft">이번 결과로는 없어요</span>}
        </li>
        <li className="flex flex-col items-start gap-1 rounded-card border border-line bg-surface px-5 py-4 text-label shadow-card">
          {/* 시안 ①: 문제보다 할 일을 먼저 ('다음엔 이렇게' + 체크리스트 첫 줄), 이유는 그 아래 */}
          <Tag tone="watch">→ 다음엔 이렇게</Tag>
          {c.checklist?.length ? <>
            <b className="mt-1.5 text-body">{c.checklist[0]}</b>
            {watch.length > 0 && <span>{watch.map((w) => w.short ?? w.text).join(" · ")}</span>}
            <span className="text-caption text-soft">→ ③ 준비하기 체크리스트에 {c.checklist.length}가지로 넣었어요</span>
          </> : watch.length ? <>
            <b className="mt-1.5 text-body">{watch.map((w) => w.title ?? w.path.split(" › ").pop()).join(" · ")} 다시 보기</b>
            <span>{watch.map((w) => w.short ?? w.text).join(" · ")}</span>
          </> : <span className="text-soft">이번엔 없어요</span>}
        </li>
      </ul>}
      <Folds label="궁금하면 열어 보세요">
        <Fold label="파일 확인 결과" preview={`${days} · 광고비 ${won(spend)} · 클릭 ${clicks.toLocaleString()}번`}>
          <p><span aria-hidden="true" className="font-bold text-ok">✓ </span>기간 {days} ({read.days}일) · 광고 세트 {read.adsets}개 · 광고비 {won(spend)} · 보여진 횟수 {imps.toLocaleString()}번 · 클릭 {clicks.toLocaleString()}번{off > 0 && ` · 안 보여진 날 ${off}일`}</p>
          <p className="text-soft">{r.check.totals.every((t) => t.match) ? "일자별 합계와 노출 위치별 합계가 맞아요." : "일자별 합계와 노출 위치별 합계가 안 맞아요."}</p>
        </Fold>
        <Fold label={one ? "자주 묻는 질문 · 왜 두 세트로 돌려야 해요?" : "자주 묻는 질문 · 왜 이 칸이에요?"} preview="펼치면 답">
          {one && <div className="flex flex-col gap-1">
            <p className="font-semibold">왜 두 세트로 돌려야 해요?</p>
            <p className="text-soft">세트가 하나면 숫자가 좋은지 나쁜지를 기준값으로만 짐작할 수 있어요. 같은 날 같이 돌린 두 세트를 비교해야 '바꾼 칸 덕분인지'를 알 수 있어요. 그래서 지금 세트는 그대로 두고, 이 칸만 바꾼 세트를 하나 더 만들어요.</p>
          </div>}
          <div className="flex flex-col gap-1">
            <p className="font-semibold">왜 이 칸이에요?</p>
            <p className="text-soft">{row === "-" ? "위에서부터 막힌 단계도, 돈이 몰린 자리도 없어서 문구 하나만 바꿔 비교하는 걸 제안해요."
              : `${m.rows.find((x) => x.row === row)?.signal ?? c.reason}. 위에서부터(게재 → 보이는 값 → 누르는 정도 → 페이지 도착 → 행동) 처음 막힌 단계의 칸을 고르고, 막힌 곳이 없으면 돈이 몰린 자리에 맞는 소재를 제안해요.`}</p>
            {c.meta_says && <p className="text-soft">{c.meta_says}</p>}
            {c.rule && <p className="text-soft">근거: {c.rule.why}{c.grade && GRADE_LABEL[c.grade] ? ` (${GRADE_LABEL[c.grade]})` : ""}</p>}
            {r.verdict && <p className="text-soft">비교한 세트: {arms.map((a, i) => `${armName(a.name, i)} (${a.name})`).join(" · ")}</p>}
          </div>
          <div className="flex flex-col gap-1">
            <p className="font-semibold">테스트는 어떻게 해요?</p>
            <p className="text-soft">{c.test ?? "지금 세트와 같이 돌려서 직접 비교해요."} 나머지 칸은 그대로 둬야 무엇 덕분인지 알 수 있어요. 예산과 체크리스트는 ③ 준비하기에서 정해요.</p>
          </div>
        </Fold>
      </Folds>
    </>
  );
}

const ORDER = ["visit_rate", "frequency", "ctr"];   // ①b 요약 카드 순서 (와이어: 도착 → 본 횟수)

/** 결론 한 줄 답: '세로 소재를 넣은 세트를 하나 더 만들어, 지금 세트와 같이 돌려 보면 돼요' */
export function oneLine(c: Change, lead = "") {
  const what = c.what ?? c.label;
  return /소재$|문구$/.test(what) ? `${lead}${josa(what, "을를")} 넣은 세트를 하나 더 만들어, 지금 세트와 같이 돌려 보면 돼요`
    : `${lead}${c.label} 칸만 바꾼 세트를 하나 더 만들어, 지금 세트와 같이 돌려 보면 돼요`;
}

/** 결론 카드 큰 글자: '+ 세로(9:16) 1개' → '세로(9:16) 소재 세트 하나 더'. '+ ○ 1개' 모양이 아니면 서버 문장 그대로. */
function headline(c: Change) {
  const s = c.new_short ?? "";
  if (!/^\+ .+ 1개$/.test(s)) return c.new;
  const core = s.slice(2, -3);
  return /소재$|문구$/.test(core) ? `${core} 세트 하나 더` : /소재$/.test(c.what ?? "") ? `${core} 소재 세트 하나 더` : c.new;
}

/** 칸 상태 태그 (그대로 = 초록, 다시 보기 = 주황). 판정 배지와 다른 모양(작은 알약). */
export function Tag({ tone, children }: { tone: "keep" | "watch"; children: string }) {
  return <span className={`inline-flex rounded-badge px-2.5 py-1 text-caption font-bold ${tone === "keep" ? "bg-ok-bg text-ink" : "bg-sunk text-soft"}`}>{children}</span>;
}

/** '돈의 72%가 …' → 72%만 굵게 (결론 카드의 숫자는 하나) */
function boldPct(s: string) {
  return s.split(/(\d+%)/).map((x, i) => (i % 2 ? <b key={i}>{x}</b> : x));
}
