import { useEffect, useState } from "react";
import { simulateGrid, type GridRow, type Result } from "../api";
import { Simulator } from "../blocks/Simulator";
import { AlertMark, BigButton, Fold, Folds, Ghost, md, Sub, TestTag, won } from "../ui";
import { armName } from "./shared";
import { Mungchi } from "../ui/Mungchi";
import type { Result as R } from "../api";
import { Backtest } from "./PrepBacktest";
import { Evidence } from "./PrepEvidence";
import { oneLine } from "./Conclusion";

/** ③ 준비하기 (최종안 · 기존 AN-05 + AN-06 합침): 지금 세트 vs 새 세트 → 예산 슬라이더(결과 한 줄) → 체크리스트 → 보내기.
 *  예산은 칩 대신 슬라이더 1개 (최종안 A: '왜 하필 이 금액?'이 안 나오게). 3,000~30,000원 1,000원 단위 결과표를 서버가 한 번에 계산해 두고,
 *  움직일 때마다 '방문자 보통 ○명 (적게 ~ 많이)' 한 줄만 바뀐다. 처음 위치는 추천 금액(서버 per_set, 하루 최소를 넘는 가장 작은 금액).
 *  이 페이지는 결제·게시를 하지 않는다. */
export function Prep({ r, onCopied, onSend, onReload, onBack }: { r: Result; onCopied: (msg: string) => void; onSend?: (budget: number) => void; onReload?: () => void; onBack?: () => void }) {
  const c = r.matrix.change ?? r.next.change;
  const keep = r.matrix.keep[0];
  const checklist = c.checklist ?? r.alerts.filter((a) => a.level === "warn").map((a) => a.todo);
  const days = c.days ?? r.check.read.days;
  const start = c.per_set ?? 6000;
  const [budget, setBudget] = useState(start);
  const { grid, error } = useGrid(r, days);
  const armsAll = r.summary.arms;
  const bi = r.verdict?.badge.better === "A" || armsAll.length < 2 ? 0 : 1;
  const who = armsAll[bi] ? armName(armsAll[bi]!.name, bi) : "지금 세트";
  const rows = grid ?? [];
  const lo = rows[0]?.budget ?? 3000, hi = rows[rows.length - 1]?.budget ?? 30000;
  const at = (b: number) => ((b - lo) / (hi - lo || 1)) * 100;
  const row = rows.find((x) => x.budget === budget);
  const hardEnd = Math.max(lo, ...rows.filter((x) => x.hard || x.below_daily_min).map((x) => x.budget));   // 빗금: 판단하기 어려운 금액까지
  const bt = r.backtest;

  // 옆 광고 어시스턴트(확장 프로그램 패널)로 보낸다. 패널이 안 열려 있을 때를 위해 코드도 복사해 둔다.
  // 보낸 결과는 버튼 아래에 남긴다 (코드는 패널이 안 열려 있을 때 꼭 필요해서 잠깐 뜨는 알림에만 두지 않음)
  const [sent, setSent] = useState<{ budget: number; copied: boolean } | null>(null);
  function send() {
    onSend?.(budget);
    navigator.clipboard.writeText(r.code).then(() => setSent({ budget, copied: true }), () => setSent({ budget, copied: false }));
    onCopied("오른쪽 광고 어시스턴트로 보냈어요");
  }
  function download() {
    const blob = new Blob([JSON.stringify({ code: r.code, change: c, budget_per_set: budget, keep: r.matrix.keep, dont: r.matrix.dont, checklist }, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `광고어시스턴트_계획_${r.code}.json` });
    a.click();
    URL.revokeObjectURL(a.href);
  }
  const btLine = bt.ok && bt.arms ? `${bt.train_days?.length ? `${md(bt.train_days[0])}~${md(bt.train_days[bt.train_days.length - 1]).split("/").pop()}` : ""}로 ${md(bt.test_day)} 예측 → ${bt.arms.every((a) => a.visits.inside && a.link_clicks.inside) ? "A·B 실제값 모두 범위 안" : "범위를 벗어난 세트가 있어요"}` : null;

  return (
    <>
      <div className="grid gap-3.5 sm:grid-cols-2">
        <section aria-label="지금 세트" className="flex flex-col gap-1 rounded-card border border-line bg-surface px-5 py-4 text-label shadow-card">
          <span className="text-caption text-soft">지금 세트 · 그대로</span>
          <b className="text-lead font-extrabold">{c.now ?? "지금 그대로"}</b>
          <span className="text-caption text-soft">{keep ? `${keep.path.split(" › ").pop()} ${keep.value.split(/[(,]/)[0]!.trim()} · ` : ""}나머지 그대로</span>
        </section>
        <section aria-label="새 세트" className="flex flex-col gap-1 rounded-card border-2 border-accent bg-linear-160 from-surface to-accent-faint px-5 py-4 text-label shadow-card">
          <span className="text-caption text-soft">새 세트 · 복제해서 이 칸만</span>
          <span className="flex flex-wrap items-center gap-2"><b className="text-lead font-extrabold">{c.new_short ?? c.new}</b> <TestTag text={c.tag ?? "테스트 제안"} /></span>
          <span className="text-caption text-soft">{c.path ?? c.label}</span>
        </section>
      </div>

      <section aria-labelledby="budget-title" className="flex flex-col gap-2 rounded-card border border-line bg-surface p-card shadow-card">
        <h2 id="budget-title" className="text-body font-extrabold"><span aria-hidden="true">💰 </span>세트당 얼마로 돌릴까요? <span className="font-semibold text-soft">· {days}일 기준</span></h2>
        {error && !grid && <p role="alert" className="text-body text-block-ink">{error} {onReload && <button type="button" onClick={onReload} className="underline">파일 다시 올리기</button>}</p>}
        {grid && (
          <div className="relative mt-7 mb-6">
            {/* 길: 빗금 = 판단하기 어려운 금액 · 보라 = 지금 금액까지 · 추천 눈금 */}
            <span aria-hidden="true" className="absolute inset-x-0 top-1/2 h-2.5 -translate-y-1/2 rounded-badge bg-sunk" />
            <span aria-hidden="true" className="absolute top-1/2 left-0 h-2.5 -translate-y-1/2 rounded-badge bg-linear-90 from-accent-line to-accent opacity-90" style={{ width: `${at(budget)}%` }} />
            <span aria-hidden="true" className="hatch-warn absolute top-1/2 left-0 h-2.5 -translate-y-1/2 rounded-l-badge" style={{ width: `${at(hardEnd)}%` }} />
            <span aria-hidden="true" className="absolute -bottom-6 -translate-x-1/2 rounded-badge bg-belly px-2 text-small font-bold text-belly-ink" style={{ left: `${at(start)}%` }}>추천</span>
            <span aria-hidden="true" className="absolute -top-7 -translate-x-1/2 whitespace-nowrap rounded-button bg-accent px-2.5 py-0.5 text-caption font-bold text-on-accent" style={{ left: `${at(budget)}%` }}>{plain(budget)}</span>
            <input type="range" className="budget-range relative" min={lo} max={hi} step={1000} value={budget} onChange={(e) => setBudget(Number(e.target.value))}
              aria-label="세트당 총액" aria-valuetext={`${plain(budget)}${budget === start ? " (추천)" : ""}`} />
          </div>
        )}
        {/* 눈금 글자는 실제 금액 자리에 (양 끝은 안쪽으로 붙여 잘리지 않게) */}
        {grid && <p aria-hidden="true" className="relative h-5 text-caption text-soft">
          {[lo, 10000, 20000, hi].map((b, i, all) => (
            <span key={b} className={`absolute whitespace-nowrap ${i === 0 ? "" : i === all.length - 1 ? "-translate-x-full" : "-translate-x-1/2"}`} style={{ left: `${at(b)}%` }}>{plain(b)}</span>
          ))}
        </p>}
        {!grid && !error && <p role="status" className="text-body text-soft">계산하는 중…</p>}
        {row && (
          <div aria-live="polite" className="flex flex-col gap-2 pt-1">
            <p className="text-lead"><b className="text-number font-extrabold text-accent">방문자 보통 {Math.round(row.visits.median)}명</b> <span className="text-soft">(적게 {Math.round(row.visits.lo)}명 ~ 많이 {Math.round(row.visits.hi)}명)</span></p>
            {row.hard ? (
              <p role="status" className="flex items-start gap-2 rounded-soft border-[1.5px] border-warn-line bg-warn-bg px-4 py-2.5 text-label text-warn">
                <AlertMark level="warn" /><span>이 금액이면 결과를 판단하기 어려워요 · 클릭 30번이 모이기 어려워요</span>
              </p>
            ) : <p className="text-label text-soft">{row.judge >= 0.995 ? "넉넉해요 · 결과를 판단하기에 충분할 가능성이 커요" : "최소한은 돼요 · 확실히 알려면 조금 더 필요할 수 있어요"}</p>}
            {row.below_daily_min && (
              <p role="status" className="flex items-start gap-2 rounded-soft border-[1.5px] border-warn-line bg-warn-bg px-4 py-2.5 text-label text-warn">
                <AlertMark level="warn" />
                <span>하루 {won(Math.round(budget / days / 10) * 10)}은 메타 하루 최소(약 {won(row.daily_min)})보다 적어요 → 광고가 안 나갈 수 있어요. {plain(start)} 이상으로 해 주세요.</span>
              </p>
            )}
            <p className="text-caption text-soft">지금 세팅({who}) 기준 · 10번 중 8번은 이 범위 안{c.what ? ` · ${c.what} 효과는 이 숫자에 없어요` : ""}</p>
          </div>
        )}
        <p className="mt-2 flex items-start gap-2 rounded-soft border-[1.5px] border-info-line bg-info-bg px-4 py-2.5 text-label text-info-ink">
          <span aria-hidden="true" className="font-bold text-info">i</span>
          <span>금액은 <b>제안만</b> 해요. 예산은 광고 관리자에서 직접 넣고, 이 페이지는 결제·게시를 하지 않아요.</span>
        </p>
      </section>

      <section aria-labelledby="check-title" className="flex flex-col gap-1 rounded-card border border-line bg-surface p-card shadow-card">
        <h2 id="check-title" className="text-body font-extrabold"><span aria-hidden="true">📝 </span>돌리기 전에 {checklist.length}가지만</h2>
        <ul className="flex flex-col">
          {checklist.map((t) => (
            <li key={t}><label className="flex min-h-11 cursor-pointer items-center gap-3 text-body"><input type="checkbox" className="size-5 shrink-0 accent-action" /><span>{boldOnce(t)}</span></label></li>
          ))}
        </ul>
      </section>

      {/* 최종안: 접기는 '더 자세히' 1개 */}
      <Folds label="더 자세히">
        <Fold label="더 자세히" preview="전체 예산으로 정하기 · 예측이 맞았나 · 클릭 30번 기준 · 근거">
          <Sub title="전체 예산으로 정하기" note="Test & Roll: 전체의 약 8~20%"><Simulator r={r} onReload={onReload} part="roll" /></Sub>
          {btLine && <Sub title="예측이 맞았나?" note={btLine}><Backtest r={r} /></Sub>}
          <Sub title="클릭 30번 기준" note={row ? `지금 금액이면 약 ${Math.round(row.judge * 100)}%` : ""}>
            <p className="text-soft">두 세트 합쳐 링크 클릭이 30번은 모여야 어느 쪽이 나은지 말할 수 있어요. 그보다 적으면 결과가 좋아 보여도 '○ 쪽이에요'까지만 말해요.
              슬라이더는 금액마다 '두 세트 합쳐 클릭 30번이 모일 가능성'을 계산해서, 80%보다 낮으면 빗금으로 표시해요. 테스트가 '성공'할 확률은 아니에요. (새 세트도 지금 세트처럼 반응한다고 가정)</p>
          </Sub>
          <Sub title="근거" note="메타 공식 신호 · 우리 실측 2건 · 논문 · 가상 케이스 · 한계"><Evidence r={r} /></Sub>
        </Fold>
      </Folds>

      <div className="flex flex-wrap items-center gap-3.5 print:hidden">
        {onBack && <Ghost onClick={onBack}>◀ 왜 그런지</Ghost>}
        <span className="text-label text-soft">
          <button type="button" onClick={download} className="min-h-11 underline hover:text-ink">계획 파일</button> · <button type="button" onClick={() => window.print()} className="min-h-11 underline hover:text-ink">PDF 받기</button>
        </span>
        <span className="ml-auto flex items-center gap-3.5">
          <BigButton onClick={send}>확장 프로그램으로 보내기 →</BigButton>
          <Mungchi pose="run" className="w-20 max-sm:hidden" />
        </span>
      </div>
      {sent && (
        <p role="status" className="-mt-2 flex flex-wrap items-center gap-2 rounded-soft border-[1.5px] border-ok-line bg-ok-bg px-4 py-2.5 text-label text-ok-ink">
          <AlertMark level="ok" />
          <span>보냈어요 · 세트당 {plain(sent.budget)} · 코드 <b className="tracking-widest tabular-nums">{r.code}</b>{sent.copied ? " (복사됨)" : ""}</span>
          <span className="text-soft">패널이 안 열려 있으면 확장 프로그램 ③ 분석에 이 코드를 넣어 주세요</span>
        </p>
      )}
    </>
  );
}

/** 체크리스트의 '딱 하루만'은 굵게 (최종안: '될 때까지 늘린 것 아니냐'는 질문을 막는 규칙이라 눈에 띄게) */
function boldOnce(t: string) {
  const i = t.indexOf("딱 하루만");
  return i < 0 ? t : <>{t.slice(0, i)}<b>딱 하루만</b>{t.slice(i + 5)}</>;
}

/** 한 줄 답: '지금 세트는 그대로 두고, 세로 소재를 넣은 세트 하나만 더 만들면 돼요' */
export function prepLine(r: R) {
  return oneLine(r.matrix.change ?? r.next.change, "지금 세트는 그대로 두고, ").replace("세트를 하나 더 만들어, 지금 세트와 같이 돌려 보면 돼요", "세트 하나만 더 만들면 돼요");
}

/** 금액 글자는 '10,000원' (슬라이더 눈금끼리 같은 모양으로) */
const plain = (b: number) => `${b.toLocaleString()}원`;

/** 슬라이더 결과표를 한 번 받아 둔다 (움직일 때마다 서버에 묻지 않음). 새 세트도 지금 이긴 세트처럼 반응한다고 가정. */
function useGrid(r: Result, days: number) {
  const [grid, setGrid] = useState<GridRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const arms = r.summary.arms;
  const arm = arms[r.verdict?.badge.better === "A" || arms.length < 2 ? 0 : 1];
  useEffect(() => {
    if (!arm) return;
    let live = true;
    simulateGrid(r.code, arm.name, days).then((g) => { if (live) setGrid(g.rows); }, (e: Error) => { if (live) setError(e.message); });
    return () => { live = false; };
  }, [r.code, arm?.name, days]);
  return { grid, error };
}
