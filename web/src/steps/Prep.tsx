import { useEffect, useState } from "react";
import { simulate, type Result } from "../api";
import { Simulator } from "../blocks/Simulator";
import { BigButton, Fold, Folds, Ghost, md, TestTag } from "../ui";
import { Mungchi } from "../ui/Mungchi";
import type { Result as R } from "../api";
import { AN05 } from "./AN05";
import { Evidence } from "./AN06";
import { oneLine } from "./Conclusion";

/** ③ 준비하기 (축소안 v5 · 기존 AN-05 + AN-06 합침): 지금 세트 vs 새 세트 → 예산(결정용 질문) → 체크리스트 → 보내기.
 *  예산은 '이 예산이면 판단할 수 있을까?' 한 줄로 답하고, 방문자 수·Test & Roll·예측 검증은 접기. 이 페이지는 결제·게시를 하지 않는다. */
export function Prep({ r, onCopied, onSend, onReload }: { r: Result; onCopied: (msg: string) => void; onSend?: () => void; onReload?: () => void }) {
  const c = r.matrix.change ?? r.next.change;
  const keep = r.matrix.keep[0];
  const checklist = c.checklist ?? r.alerts.filter((a) => a.level === "warn").map((a) => a.todo);
  const days = c.days ?? r.check.read.days;
  const start = c.per_set ?? 5000;
  const options = [...new Set([5000, start, 10000])].sort((a, b) => a - b);
  const [budget, setBudget] = useState(start);
  const chance = useJudge(r, options, days);
  const bt = r.backtest;

  // 옆 광고 어시스턴트(확장 프로그램 패널)로 보낸다. 패널이 안 열려 있을 때를 위해 코드도 복사해 둔다.
  function send() {
    onSend?.();
    const done = `오른쪽 광고 어시스턴트로 보냈어요. 패널이 안 열려 있으면 확장 프로그램 ③ 분석에 코드 ${r.code}를 넣어 주세요`;
    navigator.clipboard.writeText(r.code).then(() => onCopied(`${done} (코드 복사됨)`), () => onCopied(done));
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
        <h2 id="budget-title" className="text-body font-extrabold"><span aria-hidden="true">💰 </span>예산 · 세트당 총액 ({days}일)</h2>
        <div role="radiogroup" aria-label="세트당 총액" className="flex flex-wrap gap-2">
          {options.map((b) => (
            <label key={b} className={`cursor-pointer rounded-badge border-2 px-4.5 py-2 text-label font-bold has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent ${budget === b ? "border-accent bg-accent text-on-accent shadow-press" : "border-line bg-surface text-soft"}`}>
              <input type="radio" name="budget" className="sr-only" checked={budget === b} onChange={() => setBudget(b)} />{plain(b)}
            </label>
          ))}
        </div>
        <p className="pt-2 text-lead font-bold" aria-live="polite">이 예산이면 {days}일 뒤 결과를 판단할 수 있을 가능성 <span className="text-number font-extrabold text-accent">{chanceText(chance[budget])}</span></p>
        <div aria-hidden="true" className="h-4 overflow-hidden rounded-badge bg-sunk">
          <i className="block h-full rounded-badge bg-linear-90 from-accent-line to-accent transition-[width] duration-(--motion-expand)" style={{ width: `${Math.round((chance[budget] ?? 0) * 100)}%` }} />
        </div>
        {/* 30번: 서버 rules.yaml min_clicks (클릭이 이보다 적으면 판정 최대 '○ 쪽이에요') — 체크리스트 문구와 같은 기준. 새 세트도 지금 세트처럼 반응한다고 가정 */}
        <p className="flex flex-wrap justify-between gap-x-4 text-caption text-soft">
          <span>{options.filter((b) => b !== budget).map((b) => `${plain(b)} ${chanceText(chance[b])}`).join(" · ")}</span>
          <span>= 두 세트 합쳐 클릭 30번 넘게 모일 가능성 (성공 확률 아님)</span>
        </p>
        <Folds label="예산 더 보기">
          <Fold label="예상 방문자 수 보기"><Simulator r={r} onReload={onReload} part="visits" /></Fold>
          <Fold label="전체 예산으로 정하기" preview="Test & Roll: 전체의 약 8~20%"><Simulator r={r} onReload={onReload} part="roll" /></Fold>
          {btLine && <Fold label="예측이 맞았나?" preview={btLine}><AN05 r={r} /></Fold>}
        </Folds>
        <p className="mt-2 flex items-start gap-2 rounded-button border-2 border-info/30 bg-info-bg px-4 py-2.5 text-label">
          <span aria-hidden="true" className="font-bold text-info">i</span>
          <span>여기서는 금액을 <b>제안만</b> 해요. 예산은 광고 관리자에서 사장님이 직접 넣고, 이 페이지는 결제·게시를 하지 않아요.</span>
        </p>
      </section>

      <section aria-labelledby="check-title" className="flex flex-col gap-1 rounded-card border border-line bg-surface p-card shadow-card">
        <h2 id="check-title" className="text-body font-extrabold"><span aria-hidden="true">📝 </span>체크리스트 {checklist.length}개</h2>
        <ul className="flex flex-col">
          {checklist.map((t) => (
            <li key={t}><label className="flex min-h-11 cursor-pointer items-center gap-3 text-body"><input type="checkbox" className="size-5 shrink-0 accent-action" />{t}</label></li>
          ))}
        </ul>
      </section>

      <div className="flex flex-wrap items-center gap-3.5 print:hidden">
        <BigButton onClick={send}>확장 프로그램으로 보내기 →</BigButton>
        <Ghost onClick={download}>계획 파일 내려받기</Ghost>
        <Mungchi pose="run" className="ml-auto w-20 max-sm:hidden" />
      </div>

      <Folds label="근거와 결과 PDF">
        <Fold label="근거 · 메타 공식 신호 · 우리 실측 2건 · 논문 · 가상 케이스 · 한계" preview="세트 복제 시 겹쳐 보일 수 있음 등"><Evidence r={r} /></Fold>
        <button type="button" onClick={() => window.print()} className="flex w-full border-t border-line px-4 py-2.5 text-left text-body print:hidden">
          <span aria-hidden="true" className="inline-block w-4 text-soft">▸</span>결과 PDF 받기
        </button>
      </Folds>
    </>
  );
}

/** 한 줄 답: '지금 세트는 그대로 두고, 세로 소재를 넣은 세트 하나만 더 만들면 돼요' */
export function prepLine(r: R) {
  return oneLine(r.matrix.change ?? r.next.change, "지금 세트는 그대로 두고, ").replace("세트를 하나 더 만들어, 지금 세트와 같이 돌려 보면 돼요", "세트 하나만 더 만들면 돼요");
}

/** 예산 칩은 '10,000원' (나란한 칩끼리 같은 모양으로, 축소안 v5) */
const plain = (b: number) => `${b.toLocaleString()}원`;

/** '약 90%' (10% 단위) · 99.5% 넘으면 '거의 확실' · 계산 전엔 '…' */
function chanceText(p: number | undefined) {
  return p == null ? "…" : p >= 0.995 ? "거의 확실" : `약 ${Math.round(p * 10) * 10}%`;
}

/** 예산 칩마다 서버 /simulate의 judge(두 세트 합쳐 클릭 30번 넘을 가능성)를 받아 둔다. 새 세트도 지금 이긴 세트처럼 반응한다고 가정. */
function useJudge(r: Result, budgets: number[], days: number) {
  const [out, setOut] = useState<Record<number, number>>({});
  const arms = r.summary.arms;
  const arm = arms[r.verdict?.badge.better === "A" || arms.length < 2 ? 0 : 1];
  const key = budgets.join(",");
  useEffect(() => {
    if (!arm) return;
    let live = true;
    Promise.all(budgets.map((b) => simulate(r.code, arm.name, b, 100000, days).then((s) => [b, s.judge ?? null] as const)))
      .then((xs) => { if (live) setOut(Object.fromEntries(xs.filter((x): x is readonly [number, number] => x[1] != null))); }, () => {});
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [r.code, arm?.name, key, days]);
  return out;
}
