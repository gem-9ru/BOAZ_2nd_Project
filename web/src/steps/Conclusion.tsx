import type { Change, Result } from "../api";
import { AlertMark, BigButton, josa, spaced, TestTag, VerdictBadge } from "../ui";
import { Mungchi } from "../ui/Mungchi";
import { SIGNAL_WORD } from "./shared";

/** ① 결론 (최종안 · 기존 AN-01): 결론 카드 1장(주 버튼 + '왜 이 칸인지 보기' 글자 링크) + 요약 2장. 접기 없음.
 *  결론은 돌려 본 적 없는 선택지라 판정 배지 대신 '테스트 제안' 태그. 숫자는 이유 한 줄 속 하나만.
 *  '그대로 두세요' 근거는 아직 확정이 아닌 79%(방문자) 대신 확실한 광고비 범위 (다정 절충안). */
export function Conclusion({ r, onPrep, onWhy }: { r: Result; onPrep: () => void; onWhy: () => void }) {
  const m = r.matrix;
  const c = m.change ?? r.next.change;
  const keep = m.keep[0];
  const watch = [...m.watch].sort((a, b) => Number(b.field_id.endsWith("end_date")) - Number(a.field_id.endsWith("end_date")));   // 시작 날짜 → 예산 순
  const arms = r.summary.arms;
  const [keepWord, keepBadge] = (keep?.reason ?? "").split(" · ");
  const one = arms.length === 1;   // ①b 세트가 1개: 비교 대신 기준값
  const base = [...(r.baseline ?? [])].sort((x, y) => ORDER.indexOf(x.key) - ORDER.indexOf(y.key)).slice(0, 2);
  return (
    <>
      <section aria-label="테스트할 칸" className="relative flex flex-col items-start gap-2 rounded-card border-2 border-accent bg-surface p-card shadow-hero sm:pr-56">
        <span aria-hidden="true" className="absolute top-4 right-36 rounded-button rounded-br-mark bg-accent-soft px-3 py-1.5 text-caption font-bold text-accent max-sm:hidden">여기예요!</span>
        <Mungchi pose="point" className="absolute right-5 bottom-3 w-40 max-sm:hidden" />
        <p className="flex flex-wrap items-center gap-2"><span className="rounded-badge bg-accent-faint px-2.5 py-1 text-caption font-bold text-accent">{spaced(c.path ?? c.label)}</span> <TestTag text={c.tag ?? "테스트 제안"} /></p>
        <p className="text-headline font-extrabold leading-snug">{lineBreak(c.new.replace(/만들어 보세요$/, "만들어 같이 돌려 보세요"))}</p>
        <p className="text-body leading-relaxed">{boldPct(c.reason ?? c.note)}</p>
        {one ? <p className="text-label text-soft">세트가 1개라 비교할 대상이 없었어요. 이번에 두 세트로 돌리면 처음으로 '어느 쪽이 나은지'를 알 수 있어요.</p>
          : c.unknown && <p className="text-label text-soft">{c.unknown}</p>}
        <div className="flex flex-wrap items-center gap-4 pt-3">
          <BigButton onClick={onPrep}>이 테스트 준비하기 →</BigButton>
          <button type="button" onClick={onWhy} className="min-h-11 text-label font-semibold text-accent-ink underline">왜 이 칸인지 보기</button>
        </div>
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
          <Tag tone="keep">✓ 그대로 두세요</Tag>
          {keep ? <>
            <b className="mt-1.5 text-body">{keep.title ?? `${keep.path.split(" › ").pop()} = ${keep.value.split(",")[0]!.trim()}`}</b>
            <span className="flex flex-wrap items-center gap-1.5">{keepBadge === "확실해요" ? "광고비가 확실히 쌌어요" : (keepWord ?? "").replace("광고비 ", "광고비가 ").replace("싸요", "쌌어요")}{keepBadge && <VerdictBadge word={keepBadge} small />}</span>
          </> : <span className="text-soft">이번 결과로는 없어요</span>}
        </li>
        <li className="flex flex-col items-start gap-1 rounded-card border border-line bg-surface px-5 py-4 text-label shadow-card">
          {/* 시안 ①: 문제보다 할 일을 먼저 ('다음엔 이렇게' + 체크리스트 첫 줄), 이유는 그 아래 */}
          <Tag tone="watch">다음엔 이렇게</Tag>
          {c.checklist?.length ? <>
            {/* 체크리스트 첫 줄의 마지막 할 일 ('두 세트를 같은 날 같이 시작, 시작은 하루 여유 있게' → '시작은 하루 여유 있게') */}
            <b className="mt-1.5 text-body">{c.checklist[0]!.split(", ").pop()}</b>
            {watch.length > 0 && <span>{watch.map((w) => w.short ?? w.text).join(", ")}</span>}
          </> : watch.length ? <>
            <b className="mt-1.5 text-body">{watch.map((w) => w.title ?? w.path.split(" › ").pop()).join(" · ")} 다시 보기</b>
            <span>{watch.map((w) => w.short ?? w.text).join(" · ")}</span>
          </> : <span className="text-soft">이번엔 없어요</span>}
        </li>
      </ul>}
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


/** 결론 카드 제목: '…세트를' 뒤에서 줄을 바꾼다 (최종안(1)). 휴대폰은 저절로 줄바꿈 */
function lineBreak(s: string) {
  const i = s.indexOf("세트를 ");
  return i < 0 ? s : <>{s.slice(0, i + 4)}<br className="max-sm:hidden" />{s.slice(i + 4)}</>;
}

/** 칸 상태 태그 (그대로 = 초록, 다시 보기 = 주황). 판정 배지와 다른 모양(작은 알약). */
export function Tag({ tone, children }: { tone: "keep" | "watch"; children: string }) {
  return <span className={`inline-flex rounded-badge px-2.5 py-1 text-caption font-bold ${tone === "keep" ? "bg-ok-bg text-ink" : "bg-sunk text-soft"}`}>{children}</span>;
}

/** '돈의 72%가 …' → 72%만 굵게 (결론 카드의 숫자는 하나) */
function boldPct(s: string) {
  return s.split(/(\d+%)/).map((x, i) => (i % 2 ? <b key={i}>{x}</b> : x));
}
