import { useEffect, useRef, useState } from "react";
import { analyzeFile, example, receivedSettings, type ExampleName, type Result } from "./api";
import type { Settings } from "./blocks/MySettings";
import { Start } from "./blocks/Start";
import { AN01 } from "./steps/AN01";
import { AN02 } from "./steps/AN02";
import { AN03 } from "./steps/AN03";
import { AN04 } from "./steps/AN04";
import { AN05 } from "./steps/AN05";
import { AN06 } from "./steps/AN06";
import { AlertLine, STEPS } from "./steps/shared";
import { AlertMark, Button, Card, Toast } from "./ui";

/** 분석 페이지 (v4.2): [다음]으로 넘기는 7단계. 이 페이지는 크롬 탭에 펼쳐 두고, 오른쪽 광고 어시스턴트는
 *  크롬 확장 프로그램 사이드 패널이 맡는다 (페이지 안에 따로 띄우지 않음). 페이지는 주소 # 뒤에 코드·단계를 적어
 *  패널이 이 단계에 맞춰 설명하게 한다 (#s=세팅값키&code=AB12&step=AN-02).
 *  경고 먼저(알림 바 맨 위) → 결론(AN-01) → 이유는 다음 화면에서 하나씩. 건너뛰기는 [이 테스트 바로 준비]와 단계 ⑥만. */
export default function App() {
  const [result, setResult] = useState<Result | null>(null);
  const [step, setStep] = useState(0);
  const [reached, setReached] = useState(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [focusField, setFocusField] = useState<string | null>(null);   // AN-01 작은 카드 → AN-03 그 행
  // 확장 프로그램이 넘긴 세팅값 키: 주소 뒤 #s=… (# 뒤는 서버로 가지 않음, 값 자체는 서버에만 있음)
  const [settingsKey] = useState(() => new URLSearchParams(window.location.hash.slice(1)).get("s"));
  const [received, setReceived] = useState<number | null>(null);
  const [settings, setSettings] = useState<Settings>({});
  useEffect(() => {
    if (settingsKey) receivedSettings(settingsKey).then((r) => setReceived(r.count), () => setReceived(null));
  }, [settingsKey]);
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => { if (result) title.current?.focus(); }, [result, step]);   // 단계가 바뀌면 제목으로 초점

  // 화면설계서 v4.2 AN-00: 파일을 올리면 그 자리에서 검사(✓ 파일 · N줄 / 차단 알림) → [분석 시작]으로 결과
  const [checked, setChecked] = useState<{ file: File; result: Result; given: string } | null>(null);
  const given = () => (received !== null ? `key:${settingsKey}` : JSON.stringify(settings));
  async function check(f: File) {
    setBusy(true); setError(null); setChecked(null);
    try { setChecked({ file: f, result: await analyzeFile(f, received !== null ? { settingsKey } : { settings }), given: given() }); }
    catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  function startAnalysis() {
    if (!checked) return;
    // 올린 뒤 세팅을 바꿨으면 그 세팅으로 다시 계산, 아니면 검사 때 계산한 결과를 그대로
    if (checked.given !== given()) void load(() => analyzeFile(checked.file, received !== null ? { settingsKey } : { settings }));
    else { setResult(checked.result); setStep(0); setReached(0); window.scrollTo({ top: 0 }); }
  }
  /** 결과를 닫고 업로드 화면으로 (결과가 사라져서 한 번 묻는다). */
  function leave() {
    if (window.confirm("지금 결과를 닫고 다른 파일을 올릴까요? 지금 결과는 다시 볼 수 없어요.")) { setResult(null); setChecked(null); }
  }

  async function load(get: () => Promise<Result>) {
    setBusy(true);
    setError(null);
    try { setResult(await get()); setStep(0); setReached(0); window.scrollTo({ top: 0 }); } catch (e) { setError((e as Error).message); } finally { setBusy(false); }
  }
  function go(i: number) { setStep(i); setReached((r) => Math.max(r, i)); window.scrollTo({ top: 0 }); }
  function showToast(t: string) { setToast(t); setTimeout(() => setToast(null), 3500); }
  // 옆의 광고 어시스턴트(확장 프로그램)가 읽는 자리: 주소 # 뒤 (서버로 가지 않음)
  useEffect(() => {
    const q = new URLSearchParams(settingsKey ? { s: settingsKey } : {});
    if (result) { q.set("code", result.code); q.set("step", (STEPS[step] ?? STEPS[0]).id); }
    const next = `#${q.toString()}`;
    if (window.location.hash !== next) window.history.replaceState(null, "", next === "#" ? window.location.pathname : next);
  }, [result, step, settingsKey]);
  /** AN-06 [확장 프로그램으로 보내기]: 옆 패널이 주소의 send를 보고 테스트안을 받는다. */
  function sendToExtension() {
    const q = new URLSearchParams(window.location.hash.slice(1));
    q.set("send", String(Date.now()));
    window.history.replaceState(null, "", `#${q.toString()}`);
  }

  if (!result) {
    return (
      <main className="mx-auto max-w-page px-4 py-section flex flex-col gap-group">
        <Start onFile={(f) => { setFileName(f.name); void check(f); }}
          checked={checked && { name: checked.file.name, rows: checked.result.check.read.placement_rows || checked.result.check.read.daily_rows,
            blocks: checked.result.alerts.filter((a) => a.level === "block") }}
          onStart={startAnalysis}
          onExample={(name: ExampleName = "ovenlog") => { setFileName(EXAMPLE_FILE[name]); void load(() => example(received !== null ? settingsKey : null, name)); }}
          busy={busy} error={error} received={received} settings={settings} onSettings={setSettings} />
        <Toast text={toast} />
      </main>
    );
  }

  const s = STEPS[step] ?? STEPS[0];
  const last = step === STEPS.length - 1;
  return (
    <div className="mx-auto max-w-page-wide px-4 py-6 flex flex-col gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-lead font-bold"><span aria-hidden="true" className="text-accent">✦</span> 광고 어시스턴트 <span className="text-body font-normal text-soft break-all">분석{fileName ? ` · ${fileName}` : ""}</span></p>
          <p className="text-caption text-soft max-sm:hidden">궁금한 건 크롬 오른쪽 광고 어시스턴트(확장 프로그램 패널)에 물어보세요. 이 단계에 맞춰 설명해 드려요.</p>
        </div>
        <nav aria-label="단계" className="print:hidden max-sm:w-full max-sm:min-w-0">
          <ol className="flex flex-wrap gap-1.5 max-sm:-mx-4 max-sm:flex-nowrap max-sm:overflow-x-auto max-sm:px-4">
            {/* 화면설계서 v4.2 스테퍼: 업로드 — ① … ⑥ */}
            <li><button type="button" onClick={leave} className="inline-flex min-h-8 items-center whitespace-nowrap rounded-badge bg-accent-soft px-3 text-caption text-accent-ink">업로드</button></li>
            {STEPS.map((x, i) => {
              const can = i <= reached || (i === STEPS.length - 1 && !result.blocked);   // 차단이면 ⑥으로 건너뛰지 않음
              return (
                <li key={x.id}>
                  <button type="button" disabled={!can} onClick={() => go(i)} aria-current={i === step ? "step" : undefined}
                    className={`inline-flex min-h-8 items-center whitespace-nowrap rounded-badge px-3 text-caption ${i === step ? "bg-accent text-on-action font-bold" : i <= reached ? "bg-accent-soft text-accent-ink" : can ? "bg-surface border border-line text-ink" : "text-soft opacity-(--state-disabled-opacity)"}`}>
                    {"①②③④⑤⑥"[i]} {x.short}
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>
        {/* 결과를 지우는 일이라 한 번 묻는다. 자주 쓰는 버튼이 아니라 작은 글자 버튼으로 */}
        <button type="button" onClick={leave}
          className="print:hidden inline-flex min-h-11 items-center px-2 text-body text-soft underline hover:text-ink">다른 파일 올리기</button>
      </header>

      <AlertBar r={result} step={s.id} />

      <div>
        <main className="flex min-w-0 flex-col gap-4">
          <p role="status" className="sr-only">결과를 다 계산했어요</p>
          <h1 ref={title} tabIndex={-1} className="text-hero-sm font-bold leading-tight focus:outline-none">{step === 0 && result.blocked ? "이 파일로는 아직 결론을 낼 수 없어요" : s.title}</h1>
          {step === 0 && result.blocked && (
            <Card title="이것부터 고쳐 주세요" summary="이 파일 숫자로는 비교가 틀릴 수 있어서 결론과 다음 테스트안을 보여 드리지 않아요.">
              <ul className="flex flex-col gap-2">{result.alerts.filter((a) => a.level === "block").map((a) => <AlertLine key={a.kind + a.text} a={a} />)}</ul>
            </Card>
          )}
          {step === 0 && !result.blocked && <AN01 r={result} onApply={() => go(5)} onOpenSetting={(id) => { setFocusField(id); go(2); }} />}
          {step === 1 && <AN02 r={result} />}
          {step === 2 && <AN03 r={result} focus={focusField} />}
          {step === 3 && <AN04 r={result} />}
          {step === 4 && <AN05 r={result} onReload={() => setResult(null)} />}
          {step === 5 && <AN06 r={result} onCopied={showToast} onSend={sendToExtension} />}
          <nav aria-label="이전 다음" className="flex items-center justify-between gap-3 pt-2 print:hidden">
            {step > 0 ? <Button kind="secondary" onClick={() => go(step - 1)}>◀ {STEPS[step - 1]!.short}</Button> : <Button kind="secondary" onClick={leave}>◀ 업로드</Button>}
            {/* ①에는 [이 테스트 바로 준비]가 주 버튼이라 [다음]은 보조 (한 화면에 주 버튼 하나) */}
            {!last && <Button kind={step === 0 && !result.blocked ? "secondary" : "primary"} onClick={() => go(step + 1)} disabled={result.blocked}>{s.next} ▶</Button>}
            {last && <Button kind="secondary" onClick={() => go(0)}>처음으로 ▶</Button>}
          </nav>
          {result.blocked && <p className="text-body text-block-ink">■ 차단 알림을 먼저 해결해야 다음 화면으로 갈 수 있어요.</p>}
        </main>
      </div>
      <Toast text={toast} />
    </div>
  );
}

const EXAMPLE_FILE: Record<ExampleName, string> = { ovenlog: "오븐로그_메타AB_20261117-20261120.csv", heesu: "희수_메타AB_20261117-20261120.csv" };
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
        <button type="button" onClick={() => setAll((x) => !x)} aria-expanded={all} className="inline-flex min-h-8 items-center px-2 text-caption underline">{all ? "접기" : "모두 보기"}</button>
      </div>
      {all && <ul className="mt-3 flex flex-col gap-2">{list.map((a) => <AlertLine key={a.kind + a.text} a={a} />)}</ul>}
    </section>
  );
}
