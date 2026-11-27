import { useEffect, useRef, useState } from "react";
import { simulateGrid, type GridRow, type Result } from "../api";
import { Simulator } from "../blocks/Simulator";
import { AlertMark, BigButton, Fold, Folds, Ghost, md, spaced, Sub, TestTag, won } from "../ui";
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
export function Prep({ r, onCopied, onSend, onReload, onBack }: { r: Result; onCopied: (msg: string) => void; onSend?: (budget: number, days: number) => void; onReload?: () => void; onBack?: () => void }) {
  const c = r.matrix.change ?? r.next.change;
  const keep = r.matrix.keep[0];
  const checklist = c.checklist ?? r.alerts.filter((a) => a.level === "warn").map((a) => a.todo);
  const [days, setDays] = useState(c.days ?? (r.check.read.days === 7 ? 7 : 4));
  const perSet = c.per_set ?? 6000;
  const [budget, setBudget] = useState(perSet);
  const [touched, setTouched] = useState(false);   // 사장님이 슬라이더를 움직였는지 (안 움직였으면 추천 금액을 따라간다)
  const { grid, error, mid, manyFrom } = useGrid(r, days);
  const armsAll = r.summary.arms;
  const bi = r.verdict?.badge.better === "A" || armsAll.length < 2 ? 0 : 1;
  const who = armsAll[bi] ? armName(armsAll[bi]!.name, bi) : "지금 세트";
  const rows = grid ?? [];
  const lo = rows[0]?.budget ?? 3000, hi = rows[rows.length - 1]?.budget ?? 100000;
  // 눈금 자리: 3만 원까지 왼쪽 절반, 그 위 10만 원까지 오른쪽 절반 (최종안(1) — 작은 금액을 자세히)
  const at = (b: number) => (b <= mid ? ((b - lo) / (mid - lo || 1)) * 50 : 50 + ((b - mid) / (hi - mid || 1)) * 50);
  const row = rows.find((x) => x.budget === budget);
  const idx = Math.max(0, rows.findIndex((x) => x.budget === budget));
  const lowEnd = Math.max(lo, ...rows.filter((x) => x.below_daily_min).map((x) => x.budget));   // 빗금: 하루 금액이 메타 최소보다 적은 금액까지
  const tested = Math.max(lo, ...rows.filter((x) => x.daily_tried).map((x) => x.budget));       // 써 본 범위 (하루 최대 × 기간)
  // 추천 = 서버 금액(per_set) 이상이면서 고른 기간에 하루 최소를 넘는 가장 작은 칸 (7일이면 더 커진다). 범위 밖이면 끝 칸
  const start = rows.find((x) => x.budget >= perSet && !x.below_daily_min)?.budget ?? rows[rows.length - 1]?.budget ?? perSet;
  // 결과표가 오거나 기간이 바뀌면: 안 움직였으면 추천으로, 움직였는데 표에 없는 금액이면 가장 가까운 칸으로
  useEffect(() => {
    if (!rows.length) return;
    if (!touched) setBudget(start);
    else if (!rows.some((x) => x.budget === budget)) setBudget(rows.reduce((a, x) => (Math.abs(x.budget - budget) < Math.abs(a.budget - budget) ? x : a)).budget);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [grid, start]);
  const pick = (i: number) => { const x = rows[Math.min(rows.length - 1, Math.max(0, i))]; if (x) { setBudget(x.budget); setTouched(true); } };
  const nearest = (pos: number) => rows.reduce((best, x, i) => (Math.abs(at(x.budget) - pos) < Math.abs(at(rows[best]!.budget) - pos) ? i : best), 0);
  const bt = r.backtest;

  // 옆 광고 어시스턴트(확장 프로그램 패널)로 보낸다. 패널이 안 열려 있을 때를 위해 코드도 복사해 둔다.
  // 보낸 결과는 버튼 아래에 남긴다 (코드는 패널이 안 열려 있을 때 꼭 필요해서 잠깐 뜨는 알림에만 두지 않음)
  const [sent, setSent] = useState<{ budget: number; copied: boolean } | null>(null);
  function send() {
    onSend?.(budget, days);
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
          <b className="text-lead font-extrabold">{c.now ? c.now.replace(/(\d)장/g, "$1") : "지금 그대로"}</b>
          <span className="text-caption text-soft">{keep ? `${keep.title ?? `${keep.path.split(" › ").pop()} ${keep.value.split(/[(,]/)[0]!.trim()}`} · ` : ""}나머지 그대로</span>
        </section>
        <section aria-label="새 세트" className="flex flex-col gap-1 rounded-card border-2 border-accent bg-linear-160 from-surface to-accent-faint px-5 py-4 text-label shadow-card">
          <span className="text-caption text-soft">새 세트 · 복제해서 이 칸만</span>
          <span className="flex flex-wrap items-center gap-2"><b className="text-lead font-extrabold">{c.new_short ?? c.new}</b> <TestTag text={c.tag ?? "테스트 제안"} /></span>
          <span className="text-caption text-soft">{spaced(c.path ?? c.label)}</span>
        </section>
      </div>

      <section aria-labelledby="budget-title" className="flex flex-col gap-2 rounded-card border border-line bg-surface p-card shadow-card">
        <h2 id="budget-title" className="text-body font-extrabold"><span aria-hidden="true">💰 </span>세트당 얼마로 돌릴까요?</h2>
        {error && !grid && <p role="alert" className="text-body text-block-ink">{error} {onReload && <button type="button" onClick={onReload} className="underline">파일 다시 올리기</button>}</p>}
        {grid && (
          <div className="relative mt-11 mb-6">
            {/* 길: 써 본 범위(실선) · 그 위는 가설(점선) · 빗금 = 하루 금액이 메타 최소보다 적은 금액 · 보라 = 지금 금액까지 · 추천 눈금 */}
            <span aria-hidden="true" className="absolute top-1/2 left-0 h-3 -translate-y-1/2 rounded-l-badge bg-line" style={{ width: `${at(tested)}%` }} />
            <span aria-hidden="true" className="rail-guess absolute top-1/2 right-0 h-3 -translate-y-1/2 rounded-r-badge" style={{ left: `${at(tested)}%` }} />
            <span aria-hidden="true" className="absolute top-1/2 left-0 h-3 -translate-y-1/2 rounded-badge bg-linear-90 from-accent-line to-accent" style={{ width: `${at(budget)}%` }} />
            <span aria-hidden="true" className="hatch-warn absolute top-1/2 left-0 h-3 -translate-y-1/2 rounded-l-badge opacity-90" style={{ width: `${at(lowEnd)}%` }} />
            {tested < hi && <>
              <span aria-hidden="true" className="absolute top-0 h-full border-l-2 border-belly-strong" style={{ left: `${at(tested)}%` }} />
              <span aria-hidden="true" className="absolute -top-6 ml-1.5 whitespace-nowrap text-small font-bold text-belly-ink max-sm:hidden" style={{ left: `${at(tested)}%` }}>
                ← 써 본 범위 · 여기부터 <span className="rounded-badge border-[1.5px] border-dashed border-disabled-line bg-hold-bg px-1.5 text-hold">가설</span> →
              </span>
            </>}
            <span aria-hidden="true" className="absolute -bottom-6 -translate-x-1/2 rounded-badge bg-belly px-2 text-small font-bold text-belly-ink" style={{ left: `${at(start)}%` }}>추천</span>
            <span aria-hidden="true" className={`absolute -top-11 whitespace-nowrap rounded-button bg-accent px-2.5 py-0.5 text-label font-extrabold text-on-accent ${edge(at(budget))}`} style={{ left: `${at(budget)}%` }}>{plain(budget)}</span>
            {/* 길이 두 구간이라 위치(0~1000)로 움직이고 가장 가까운 금액에 붙는다. 화살표 키는 한 칸씩 */}
            <input type="range" className="budget-range relative" min={0} max={1000} step={1} value={Math.round(at(budget) * 10)}
              onChange={(e) => {
                // 화면 낭독기는 0.1칸씩 올리고 내려서, 같은 금액에 다시 붙으면 그 방향으로 한 칸 옮긴다
                const pos = Number(e.target.value) / 10, i = nearest(pos);
                pick(i === idx && Math.abs(pos - at(budget)) > 0.05 ? idx + Math.sign(pos - at(budget)) : i);
              }}
              onKeyDown={(e) => {
                const move = { ArrowRight: 1, ArrowUp: 1, ArrowLeft: -1, ArrowDown: -1, PageUp: 5, PageDown: -5 }[e.key];
                if (move !== undefined) { e.preventDefault(); pick(idx + move); }
                else if (e.key === "Home") { e.preventDefault(); pick(0); }
                else if (e.key === "End") { e.preventDefault(); pick(rows.length - 1); }
              }}
              aria-label="세트당 총액" aria-valuemin={lo} aria-valuemax={hi} aria-valuenow={budget} aria-valuetext={`${plain(budget)}${budget === start ? " (추천)" : ""}`} />
          </div>
        )}
        {grid && <p aria-hidden="true" className="relative h-5 text-caption text-soft">
          {[[lo, "3천"], [10000, "1만"], [20000, "2만"], [mid, "3만"], [50000, "5만"], [hi, "10만 원"]].map(([b, t], i, all) => (
            <span key={b} className={`absolute whitespace-nowrap ${i === 0 ? "" : i === all.length - 1 ? "-translate-x-full" : "-translate-x-1/2"}`} style={{ left: `${at(Number(b))}%` }}>{t}</span>
          ))}
        </p>}
        {grid && <p className="text-caption text-soft">{(mid / 10000).toLocaleString()}만 원까지는 1,000원씩, 그 위는 5,000원씩 움직여요</p>}
        <div className="flex flex-wrap items-center gap-2 pt-2">
          <div role="radiogroup" aria-label="기간" className="flex gap-1.5">
            {[4, 7].map((d) => (
              <label key={d} className={`cursor-pointer rounded-badge border-2 px-3.5 py-1 text-label font-bold has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent ${days === d ? "border-accent bg-accent text-on-accent shadow-press-sm" : "border-line bg-surface text-soft"}`}>
                <input type="radio" name="days" className="sr-only" checked={days === d} onChange={() => setDays(d)} />{d}일
              </label>
            ))}
          </div>
          <span className="text-label text-soft">하루 약 {won(Math.round(budget / days / 10) * 10)}</span>
        </div>
        {!grid && !error && <p role="status" className="text-body text-soft">계산하는 중…</p>}
        {row && (
          <div aria-live="polite" className="flex flex-col gap-2 pt-1">
            <p className="flex flex-wrap items-baseline gap-x-2 text-lead"><b className="text-number font-extrabold text-accent">방문자 보통 {Math.round(row.visits.median)}명</b>
              <span className="text-soft">(적게 {Math.round(row.visits.lo)}명 ~ 많이 {Math.round(row.visits.hi)}명)</span>
              {!row.daily_tried && <span className="rounded-badge border-[1.5px] border-dashed border-disabled-line bg-hold-bg px-2 text-caption font-bold text-hold">가설</span>}</p>
            <p className="text-caption text-soft">지금 세팅({who})으로 계산 · 10번 중 8번은 이 안에 들어요{c.what ? ` · ${c.what} 효과는 아직 재 본 적 없어요` : ""}</p>
            {row.below_daily_min && (
              <p role="status" className="flex items-start gap-2 rounded-soft border-[1.5px] border-warn-line bg-warn-bg px-4 py-2.5 text-label text-warn">
                <AlertMark level="warn" />
                <span>하루 {won(Math.round(budget / days / 10) * 10)}은 메타 하루 최소(약 {won(row.daily_min)})보다 적어요 → 광고가 안 나갈 수 있어요. 기간을 줄이거나 총예산을 늘려 주세요.</span>
              </p>
            )}
            {budget > manyFrom && (
              <p className="flex items-start gap-2 text-label font-bold">
                <AlertMark level="info" /><span>금액이 커지면 같은 사람에게 여러 번 보여서, 방문자가 금액만큼 늘지 않을 수 있어요</span>
              </p>
            )}
          </div>
        )}
        <Folds label="이 숫자는 어떻게 나왔나요?">
          <Fold label={<><span aria-hidden="true">🔎 </span>이 숫자는 어떻게 나왔나요?</>} preview="금액 2배·4배 비교 · 실선/점선 뜻 · 계산 방법">
            <Simulator r={r} onReload={onReload} part="compare" budget={budget} days={days} grid={grid} />
          </Fold>
        </Folds>
        <p className="mt-2 flex items-start gap-2 rounded-soft border-[1.5px] border-info-line bg-info-bg px-4 py-2.5 text-label text-info-ink">
          <span aria-hidden="true" className="font-bold text-info">i</span>
          <span>금액은 <b>제안만</b> 해요. 예산은 광고 관리자에서 직접 넣고, 이 페이지는 결제·게시를 하지 않아요.</span>
        </p>
      </section>

      <section aria-labelledby="check-title" className="flex flex-col gap-1 rounded-card border border-line bg-surface p-card shadow-card">
        <h2 id="check-title" className="text-body font-extrabold"><span aria-hidden="true">📝 </span>돌리기 전에 {checklist.length}가지만</h2>
        <ul className="flex flex-col">
          {checklist.map((t) => (
            <li key={t}><label className="flex min-h-11 cursor-pointer items-center gap-3 text-body"><input type="checkbox" className="size-5 shrink-0 accent-action" /><span>{boldOnce(spaced(t.replace(/^\d+일 동안/, `${days}일 동안`)))}</span></label></li>
          ))}
        </ul>
      </section>

      {/* 최종안: 접기는 '더 자세히' 1개 */}
      <Folds label="더 자세히">
        <Fold label="더 자세히" preview="전체 예산으로 정하기 (Test & Roll) · 예측이 맞았나 · 근거">
          <Sub title="전체 예산으로 정하기" note="Test & Roll: 전체의 약 8~20%"><Simulator r={r} onReload={onReload} part="roll" budget={budget} days={days} /></Sub>
          {btLine && <Sub title="예측이 맞았나?" note={btLine}><Backtest r={r} /></Sub>}
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

/** 금액 말풍선이 양 끝에서 카드 밖으로 나가지 않게: 왼쪽 끝은 왼쪽 맞춤, 오른쪽 끝은 오른쪽 맞춤 */
const edge = (pos: number) => (pos < 6 ? "-translate-x-[0.75rem]" : pos > 94 ? "-translate-x-[calc(100%-0.75rem)]" : "-translate-x-1/2");

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

/** 슬라이더 결과표를 기간마다 한 번 받아 둔다 (움직일 때마다 서버에 묻지 않음, 4일↔7일은 기억). 새 세트도 지금 이긴 세트처럼 반응한다고 가정. */
function useGrid(r: Result, days: number) {
  const [got, setGot] = useState<Record<number, { rows: GridRow[]; mid: number; many_from: number }>>({});
  const [error, setError] = useState<string | null>(null);
  const arms = r.summary.arms;
  const arm = arms[r.verdict?.badge.better === "A" || arms.length < 2 ? 0 : 1];
  useEffect(() => {
    if (!arm || got[days]) return;
    let live = true;
    setError(null);
    simulateGrid(r.code, arm.name, days).then((g) => { if (live) setGot((x) => ({ ...x, [days]: g })); }, (e: Error) => { if (live) setError(e.message); });
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [r.code, arm?.name, days]);
  // 새 기간의 표가 오는 동안은 앞 기간의 표를 그대로 둔다 (슬라이더가 사라졌다 나타나며 깜빡이지 않게)
  const last = useRef<{ rows: GridRow[]; mid: number; many_from: number } | undefined>(undefined);
  if (got[days]) last.current = got[days];
  const g = got[days] ?? last.current;
  return { grid: g?.rows ?? null, error, mid: g?.mid ?? 30000, manyFrom: g?.many_from ?? 50000 };
}
