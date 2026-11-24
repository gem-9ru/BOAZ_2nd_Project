import { useEffect, useRef, useState } from "react";
import { analyzeFile, example, receivedSettings, type Result } from "./api";
import type { Settings } from "./blocks/MySettings";
import { Assistant } from "./assistant/Assistant";
import { Start } from "./blocks/Start";
import { AN01 } from "./steps/AN01";
import { AN02 } from "./steps/AN02";
import { AN03 } from "./steps/AN03";
import { AN04 } from "./steps/AN04";
import { AN05 } from "./steps/AN05";
import { AN06 } from "./steps/AN06";
import { AlertLine, STEPS } from "./steps/shared";
import { AlertMark, Button, Toast } from "./ui";

/** 분석 페이지 (v4): [다음]으로 넘기는 7단계. 왼쪽 = 단계별 분석, 오른쪽 = 광고 어시스턴트 고정.
 *  결론(AN-01)을 먼저, 이유는 다음 화면에서 하나씩. 건너뛰기는 [바로 적용]과 단계 ⑥만. */
export default function App() {
  const [result, setResult] = useState<Result | null>(null);
  const [step, setStep] = useState(0);
  const [reached, setReached] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [panel, setPanel] = useState(false);
  // 확장 프로그램이 넘긴 세팅값 키: 주소 뒤 #s=… (# 뒤는 서버로 가지 않음, 값 자체는 서버에만 있음)
  const [settingsKey] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get("s"));
  const [received, setReceived] = useState<number | null>(null);
  const [settings, setSettings] = useState<Settings>({});
  useEffect(() => {
    if (settingsKey) receivedSettings(settingsKey).then((r) => setReceived(r.count), () => setReceived(null));
  }, [settingsKey]);
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => { if (result) title.current?.focus(); }, [result, step]);   // 단계가 바뀌면 제목으로 초점

  async function load(get: () => Promise<Result>) {
    setBusy(true);
    setError(null);
    try { setResult(await get()); setStep(0); setReached(0); window.scrollTo({ top: 0 }); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  function go(i: number) { setStep(i); setReached((r) => Math.max(r, i)); window.scrollTo({ top: 0 }); }
  function showToast(t: string) { setToast(t); setTimeout(() => setToast(null), 2500); }

  if (!result) {
    return (
      <main className="mx-auto max-w-[960px] px-4 py-section flex flex-col gap-group">
        <Start onFile={(f) => load(() => analyzeFile(f, received !== null ? { settingsKey } : { settings }))} onExample={() => load(() => example(received !== null ? settingsKey : null))}
          busy={busy} error={error} received={received} settings={settings} onSettings={setSettings} />
        <Toast text={toast} />
      </main>
    );
  }

  const s = STEPS[step] ?? STEPS[0];
  const last = step === STEPS.length - 1;
  return (
    <div className="mx-auto max-w-[1280px] px-4 py-6 flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-lead font-bold"><span aria-hidden="true" className="text-accent">✦</span> 광고 어시스턴트 <span className="text-body font-normal text-soft">결과 분석</span></p>
        <nav aria-label="단계">
          <ol className="flex flex-wrap gap-1.5">
            {STEPS.map((x, i) => {
              const can = i <= reached || i === STEPS.length - 1;
              return (
                <li key={x.id}>
                  <button type="button" disabled={!can} onClick={() => go(i)} aria-current={i === step ? "step" : undefined}
                    className={`rounded-badge px-3 py-1 text-caption ${i === step ? "bg-accent text-on-action font-bold" : can ? "bg-surface border border-line text-ink" : "text-soft opacity-(--state-disabled-opacity)"}`}>
                    {"①②③④⑤⑥"[i]} {x.short}
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>
        <Button kind="secondary" onClick={() => setResult(null)}>다른 파일 올리기</Button>
      </header>

      <AlertBar r={result} />

      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
        <main className="flex min-w-0 flex-col gap-4">
          <p role="status" className="sr-only">결과를 다 계산했어요</p>
          <h1 ref={title} tabIndex={-1} className="text-hero-sm font-bold leading-tight focus:outline-none">{s.title}</h1>
          {step === 0 && <AN01 r={result} onApply={() => go(5)} />}
          {step === 1 && <AN02 r={result} />}
          {step === 2 && <AN03 r={result} />}
          {step === 3 && <AN04 r={result} />}
          {step === 4 && <AN05 r={result} />}
          {step === 5 && <AN06 r={result} onCopied={showToast} />}
          <nav aria-label="이전 다음" className="flex items-center justify-between gap-3 pt-2">
            {step > 0 ? <Button kind="secondary" onClick={() => go(step - 1)}>이전</Button> : <span />}
            {!last && <Button onClick={() => go(step + 1)} disabled={result.blocked}>{s.next}</Button>}
          </nav>
          {result.blocked && <p className="text-body text-block-ink">■ 차단 알림을 먼저 해결해야 다음 화면으로 갈 수 있어요.</p>}
        </main>
        <div className={panel ? "fixed inset-x-0 bottom-0 z-20 max-h-[85vh] overflow-y-auto p-2 shadow-2xl lg:static lg:z-auto lg:p-0 lg:shadow-none lg:sticky lg:top-4" : "lg:sticky lg:top-4"}>
          <Assistant code={result.code} step={s.id} open={panel} onToggle={() => setPanel((p) => !p)} />
        </div>
      </div>
      {!panel && (
        <button type="button" onClick={() => setPanel(true)} className="fixed bottom-4 right-4 rounded-badge bg-accent px-4 py-3 text-body font-bold text-on-action shadow-lg lg:hidden">✦ 어시스턴트</button>
      )}
      <Toast text={toast} />
    </div>
  );
}

/** 맨 위 알림 바: 가장 심각한 알림 1개 + 등급별 개수 + [모두 보기]. */
function AlertBar({ r }: { r: Result }) {
  const [all, setAll] = useState(false);
  if (!r.alerts.length) return null;
  const top = r.alerts[0]!;
  const count = (l: string) => r.alerts.filter((a) => a.level === l).length;
  const box = top.level === "block" ? "bg-block-bg" : top.level === "warn" ? "bg-warn-bg" : "bg-info-bg";
  return (
    <section aria-label="알림" className={`rounded-button px-4 py-3 ${box}`}>
      <div className="flex flex-wrap items-center gap-3 text-body">
        <AlertMark level={top.level} />
        <b className="flex-1 min-w-48">{top.text}</b>
        <span className="text-caption text-soft">■ {count("block")} · ▲ {count("warn")} · ● {count("info")}</span>
        <button type="button" onClick={() => setAll((x) => !x)} aria-expanded={all} className="text-caption underline">{all ? "접기" : "모두 보기"}</button>
      </div>
      {all && <ul className="mt-3 flex flex-col gap-2">{r.alerts.map((a) => <AlertLine key={a.kind + a.text} a={a} />)}</ul>}
    </section>
  );
}
