import { useEffect, useRef, useState } from "react";
import { analyzeFile, example, type Result } from "./api";
import { DataCheck } from "./blocks/DataCheck";
import { NextStep } from "./blocks/NextStep";
import { Alerts } from "./blocks/Alerts";
import { Conclusion } from "./blocks/Conclusion";
import { Funnel } from "./blocks/Funnel";
import { KeyNumbers } from "./blocks/KeyNumbers";
import { Trust } from "./blocks/Trust";
import { Simulator } from "./blocks/Simulator";
import { Start } from "./blocks/Start";
import { Button, Toast } from "./ui";

/** 분석 페이지 결과 리포트: 결론 먼저 → 근거 → 얼마나 믿나 → 왜 → 앞으로 → 다음 행동. 사장님은 위 3블록만 봐도 된다. */
export default function App() {
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => { if (result) title.current?.focus(); }, [result]);   // 결과가 나오면 제목으로 초점을 옮겨 알린다

  async function load(get: () => Promise<Result>) {
    setBusy(true);
    setError(null);
    try { setResult(await get()); window.scrollTo({ top: 0 }); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  function showToast(t: string) { setToast(t); setTimeout(() => setToast(null), 2000); }

  return (
    <main className="mx-auto max-w-[960px] px-4 py-section flex flex-col gap-group">
      {!result ? (
        <Start onFile={(f) => load(() => analyzeFile(f))} onExample={() => load(example)} busy={busy} error={error} />
      ) : (
        <>
          <header className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-caption font-semibold text-accent-ink">Ad assistant · 결과 분석</p>
              <h1 ref={title} tabIndex={-1} className="text-hero-sm sm:text-hero font-bold leading-tight focus:outline-none">이번 광고에서 알게 된 것</h1>
              <p role="status" className="sr-only">결과를 다 계산했어요</p>
              <a href="#conclusion" className="sr-only focus:not-sr-only focus:inline-block mt-2 rounded-button bg-button text-button-fg px-4 py-2 text-body">결론으로 바로 가기</a>
            </div>
            <Button kind="secondary" onClick={() => setResult(null)}>다른 파일 올리기</Button>
          </header>
          <nav aria-label="결과 순서" className="flex flex-wrap gap-2 text-caption">
            {[["check", "데이터 점검"], ["conclusion", "결론"], ["numbers", "핵심 숫자"], ["funnel", "퍼널"], ["trust", "믿을 수 있나"], ["simulator", "예산"], ["next", "다음에 할 일"]].map(([id, t]) => (
              <a key={id} href={`#${id}`} className="rounded-badge border border-line bg-surface px-3 py-1 text-soft hover:text-ink">{t}</a>
            ))}
          </nav>
          <DataCheck c={result.check} />
          <Alerts c={result.check} />
          <Conclusion r={result} />
          <KeyNumbers r={result} />
          <Funnel r={result} />
          <Trust r={result} />
          <Simulator r={result} />
          <NextStep r={result} onCopied={showToast} />
        </>
      )}
      <Toast text={toast} />
    </main>
  );
}
