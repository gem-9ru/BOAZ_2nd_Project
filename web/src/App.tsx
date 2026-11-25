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

/** 분석 페이지 (v4.2): [다음]으로 넘기는 7단계. 왼쪽 = 단계별 분석, 오른쪽 = 광고 어시스턴트 고정.
 *  경고 먼저(알림 바 맨 위) → 결론(AN-01) → 이유는 다음 화면에서 하나씩. 건너뛰기는 [이 테스트 바로 준비]와 단계 ⑥만. */
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
        <p className="text-lead font-bold"><span aria-hidden="true" className="text-accent">✦</span> 광고 어시스턴트 <span className="text-body font-normal text-soft">분석</span></p>
        <nav aria-label="단계">
          <ol className="flex flex-wrap gap-1.5">
            {STEPS.map((x, i) => {
              const can = i <= reached || i === STEPS.length - 1;
              return (
                <li key={x.id}>
                  <button type="button" disabled={!can} onClick={() => go(i)} aria-current={i === step ? "step" : undefined}
                    className={`rounded-badge px-3 py-1 text-caption ${i === step ? "bg-accent text-on-action font-bold" : i <= reached ? "bg-accent-soft text-accent-ink" : can ? "bg-surface border border-line text-ink" : "text-soft opacity-(--state-disabled-opacity)"}`}>
                    {"①②③④⑤⑥"[i]} {x.short}
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>
        <Button kind="secondary" onClick={() => setResult(null)}>다른 파일 올리기</Button>
      </header>

      <AlertBar r={result} step={s.id} />

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
            {step > 0 ? <Button kind="secondary" onClick={() => go(step - 1)}>◀ {STEPS[step - 1]!.short}</Button> : <span />}
            {!last && <Button onClick={() => go(step + 1)} disabled={result.blocked}>{s.next} ▶</Button>}
            {last && <Button kind="secondary" onClick={() => go(0)}>처음으로 ▶</Button>}
          </nav>
          {result.blocked && <p className="text-body text-block-ink">■ 차단 알림을 먼저 해결해야 다음 화면으로 갈 수 있어요.</p>}
        </main>
        <div className={panel ? "fixed inset-x-0 bottom-0 z-20 max-h-[85vh] overflow-y-auto p-2 shadow-2xl lg:static lg:z-auto lg:p-0 lg:shadow-none lg:sticky lg:top-4" : "lg:sticky lg:top-4"}>
          <Assistant code={result.code} step={s.id} open={panel} onToggle={() => setPanel((p) => !p)} />
        </div>
      </div>
      {!panel && (
        <button type="button" onClick={() => setPanel(true)} className="fixed bottom-4 right-4 rounded-badge bg-accent px-4 py-3 text-body font-bold text-on-action shadow-lg lg:hidden">✦ 광고 어시스턴트</button>
      )}
      <Toast text={toast} />
    </div>
  );
}

const ORDER = STEPS.map((x) => x.id as string);
const NAME = { block: "차단", warn: "주의", info: "참고" } as const;

/** 맨 위 알림 바 (v4.2): 경고는 결론보다 먼저. 이 단계 알림이 있으면 그것, 없으면 가장 심각한 알림 1개 + 등급별 개수 + [모두 보기].
 *  보내기(AN-06)에선 남은 주의를 체크리스트로 옮겼다고 알려 준다. 고정 안내(Breakdown)는 여기 넣지 않는다. */
function AlertBar({ r, step }: { r: Result; step: string }) {
  const [all, setAll] = useState(false);
  const at = ORDER.indexOf(step);
  const list = r.alerts.filter((a) => !a.shown_from || at >= ORDER.indexOf(a.shown_from));
  if (!list.length) return null;
  const count = (l: keyof typeof NAME) => list.filter((a) => a.level === l).length;
  const counts = (["block", "warn", "info"] as const).filter((l) => count(l) > 0).map((l) => `${NAME[l]} ${count(l)}`).join(" · ");
  if (step === "AN-06" && !count("block")) {
    return (
      <section aria-label="알림" className="flex flex-wrap items-center gap-3 rounded-button bg-ok-bg px-4 py-3 text-body">
        <AlertMark level="ok" />
        <b className="flex-1 min-w-48">차단 알림 없음{count("warn") ? ` · 주의 ${count("warn")}건은 다음 테스트 체크리스트에 넣었어요` : ""}</b>
      </section>
    );
  }
  const here = list.find((a) => a.screen === step && a.level !== "info") ?? list.find((a) => a.screen === step);
  const top = list.find((a) => a.level === "block") ?? here ?? list[0]!;
  const text = top.kind === "no_delivery" && top.later && step !== top.screen ? top.later : top.text;
  const box = top.level === "block" ? "bg-block-bg" : top.level === "warn" ? "bg-warn-bg" : "bg-info-bg";
  return (
    <section aria-label="알림" className={`rounded-button px-4 py-3 ${box}`}>
      <div className="flex flex-wrap items-center gap-3 text-body">
        <AlertMark level={top.level} />
        <b className="flex-1 min-w-48"><span className="font-normal">{NAME[top.level]} · </span>{text}</b>
        <span className="text-caption text-soft">{counts}</span>
        <button type="button" onClick={() => setAll((x) => !x)} aria-expanded={all} className="text-caption underline">{all ? "접기" : "모두 보기"}</button>
      </div>
      {all && <ul className="mt-3 flex flex-col gap-2">{list.map((a) => <AlertLine key={a.kind + a.text} a={a} />)}</ul>}
    </section>
  );
}
