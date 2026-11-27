import { useEffect, useRef, useState } from "react";
import { analyzeFile, example, receivedSettings, type ExampleName, type Result } from "./api";
import type { Settings } from "./blocks/MySettings";
import { Start } from "./blocks/Start";
import { Conclusion, oneLine } from "./steps/Conclusion";
import { Prep, prepLine } from "./steps/Prep";
import { answer, Why } from "./steps/Why";
import { AlertLine, SCREEN_ORDER, STEPS } from "./steps/shared";
import { AlertMark, Button, Card, Ghost, Title, Toast } from "./ui";
import { Mungchi } from "./ui/Mungchi";

/** 분석 페이지 (축소안 v5): 업로드 → ① 결론 → ② 왜 그런지 → ③ 준비하기. 한 열로 읽고, 화면마다 진한 버튼은 하나.
 *  (v4.2의 7단계를 3단계로 줄임: 예전 AN-02·03·04 → ②, AN-05·06 → ③, 지운 화면 내용은 접기 줄로) 이 페이지는 크롬 탭에 펼쳐 두고, 오른쪽 광고 어시스턴트는
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
  /** 단계 이동: 브라우저 기록에 한 칸 쌓아서 [뒤로]가 앞 단계로 오게 한다 (아래 popstate). */
  function go(i: number) {
    if (i !== step) window.history.pushState(null, "", window.location.href);   // 새 칸 → 아래 효과가 이 칸의 # 를 새 단계로 바꾼다
    setStep(i); setReached((r) => Math.max(r, i)); window.scrollTo({ top: 0 });
  }
  // 브라우저 [뒤로]·[앞으로]: 주소 #의 step으로 단계를 맞춘다 (결과는 메모리에만 있어서 페이지를 떠나면 사라지므로)
  useEffect(() => {
    const onPop = () => {
      const id = new URLSearchParams(window.location.hash.slice(1)).get("step");
      const i = STEPS.findIndex((x) => x.id === id);
      if (i >= 0) setStep(i);
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);
  // 결과가 있는 동안 페이지를 떠나려 하면 브라우저가 한 번 묻는다 (결과는 다시 볼 수 없어요)
  useEffect(() => {
    if (!result) return;
    const ask = (e: BeforeUnloadEvent) => { e.preventDefault(); };
    window.addEventListener("beforeunload", ask);
    return () => window.removeEventListener("beforeunload", ask);
  }, [result]);
  function showToast(t: string) { setToast(t); setTimeout(() => setToast(null), 3500); }
  // 옆의 광고 어시스턴트(확장 프로그램)가 읽는 자리: 주소 # 뒤 (서버로 가지 않음)
  useEffect(() => {
    const q = new URLSearchParams(settingsKey ? { s: settingsKey } : {});
    if (result) { q.set("code", result.code); q.set("step", (STEPS[step] ?? STEPS[0]).id); }
    const next = `#${q.toString()}`;
    if (window.location.hash !== next) window.history.replaceState(null, "", next === "#" ? window.location.pathname : next);
  }, [result, step, settingsKey]);
  /** ③ [확장 프로그램으로 보내기]: 옆 패널이 주소의 send를 보고 테스트안을 받는다. 고른 세트당 예산도 같이 (budget). */
  function sendToExtension(budget?: number) {
    const q = new URLSearchParams(window.location.hash.slice(1));
    q.set("send", String(Date.now()));
    if (budget) q.set("budget", String(budget));
    window.history.replaceState(null, "", `#${q.toString()}`);
  }

  if (!result) {
    return (
      <div className="flex flex-col gap-4 pb-10">
        <AppHeader file={null} step={-1} />
        <main className="mx-auto flex w-full max-w-3xl flex-col gap-group px-4">
          <Start onFile={(f) => { setFileName(f.name); void check(f); }}
            checked={checked && { name: checked.file.name, rows: checked.result.check.read.placement_rows || checked.result.check.read.daily_rows,
              blocks: checked.result.alerts.filter((a) => a.level === "block") }}
            onStart={startAnalysis}
            onExample={(name: ExampleName = "ovenlog") => { setFileName(EXAMPLE_FILE[name]); void load(() => example(received !== null ? settingsKey : null, name)); }}
            busy={busy} error={error} received={received} settings={settings} onSettings={setSettings} />
        </main>
        <Toast text={toast} />
      </div>
    );
  }

  const s = STEPS[step] ?? STEPS[0];
  return (
    <div className="flex flex-col gap-4 pb-10">
      <AppHeader file={fileName} step={step} reached={reached} blocked={result.blocked} onGo={go} onLeave={leave} />
      <main className="mx-auto flex w-full max-w-3xl min-w-0 flex-col gap-4 px-4 pt-2">
        <AlertBar r={result} step={s.id} />
        <p role="status" className="sr-only">결과를 다 계산했어요</p>
        <div className="flex items-end gap-4">
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <h1 ref={title} tabIndex={-1} aria-label={step === 0 && result.blocked ? undefined : s.title} className="text-hero-sm font-extrabold leading-tight tracking-tight focus:outline-none">
              {step === 0 && result.blocked ? "이 파일로는 아직 결론을 낼 수 없어요" : <Title parts={s.parts} />}
            </h1>
            {!(step === 0 && result.blocked) && <p className="text-lead font-medium text-soft">{[oneLine(result.matrix.change ?? result.next.change), answer(result), prepLine(result)][step]}</p>}
          </div>
          {step === 1 && <Mungchi pose="idle" className="w-24 shrink-0 max-sm:hidden" />}
        </div>
        {step === 0 && result.blocked && (
          <Card title="이것부터 고쳐 주세요" summary="이 파일 숫자로는 비교가 틀릴 수 있어서 결론과 다음 테스트안을 보여 드리지 않아요.">
            <ul className="flex flex-col gap-2">{result.alerts.filter((a) => a.level === "block").map((a) => <AlertLine key={a.kind + a.text} a={a} />)}</ul>
          </Card>
        )}
        {step === 0 && !result.blocked && <Conclusion r={result} onPrep={() => go(2)} />}
        {step === 1 && <Why r={result} />}
        {step === 2 && <Prep r={result} onCopied={showToast} onSend={sendToExtension} onReload={() => setResult(null)} />}
        <nav aria-label="이전 다음" className="flex flex-wrap items-center justify-between gap-3 pt-2 print:hidden">
          {/* 화면마다 진한 버튼은 하나: ①은 [이 테스트 준비하기], ②는 [준비하기 ▶], ③은 [확장 프로그램으로 보내기] */}
          {step === 0 && <><span className="text-body text-soft">{result.blocked ? "" : "여기서 바로 준비해도 돼요"}</span>
            <Ghost onClick={() => go(1)} disabled={result.blocked}>왜 그런지 보기 ▶</Ghost></>}
          {step === 1 && <><Ghost onClick={() => go(0)}>◀ 결론</Ghost><Button onClick={() => go(2)}>준비하기 ▶</Button></>}
          {step === 2 && <><Ghost onClick={() => go(1)}>◀ 왜 그런지</Ghost>
            <button type="button" onClick={() => go(0)} className="inline-flex min-h-11 items-center px-2 text-body text-soft underline hover:text-ink">처음으로</button></>}
        </nav>
        {result.blocked && <p className="text-body text-block-ink">■ 차단 알림을 먼저 해결해야 다음 화면으로 갈 수 있어요.</p>}
      </main>
      <Toast text={toast} />
    </div>
  );
}

/** 맨 위 머리줄 (축소안 v5): ✦ 광고 어시스턴트 · 파일 이름(업로드 전엔 '새 분석') · ① 결론 — ② 왜 그런지 — ③ 준비하기.
 *  지난 단계·지금 단계는 누를 수 있고, ③은 차단이 없으면 바로 갈 수 있다. step = -1: 업로드 화면 */
function AppHeader({ file, step, reached = -1, blocked = false, onGo, onLeave }: {
  file: string | null; step: number; reached?: number; blocked?: boolean; onGo?: (i: number) => void; onLeave?: () => void;
}) {
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-page-wide flex-wrap items-center gap-x-3 gap-y-2 px-4 py-3">
        <p className="flex items-center gap-2 text-lead font-extrabold">
          <span aria-hidden="true" className="grid size-9 shrink-0 place-items-start justify-center overflow-hidden rounded-badge bg-belly"><Mungchi pose="idle" className="mt-1 w-8" /></span>
          광고 어시스턴트
        </p>
        <span className="min-w-0 truncate rounded-badge bg-sunk px-3 py-1.5 text-caption text-soft">{file ? `분석 · ${file}` : "새 분석"}</span>
        <nav aria-label="단계" className="ml-auto print:hidden max-sm:w-full max-sm:overflow-x-auto">
          <ol className="flex items-center gap-1 rounded-badge bg-sunk p-1">
            {STEPS.map((x, i) => {
              const can = step >= 0 && (i <= reached || (i === STEPS.length - 1 && !blocked));   // 차단이면 ③으로 건너뛰지 않음
              const past = step >= 0 && i < step;
              return (
                <li key={x.id}>
                  <button type="button" disabled={!can} onClick={() => onGo?.(i)} aria-current={i === step ? "step" : undefined} aria-label={`${"①②③"[i]} ${x.short}`}
                    className={`inline-flex min-h-9 items-center whitespace-nowrap rounded-badge px-4 text-label font-semibold ${i === step ? "bg-accent text-on-accent shadow-press-sm" : past ? "text-accent" : "text-soft"} disabled:cursor-default`}>
                    {past ? `✓ ${x.short}` : `${"①②③"[i]} ${x.short}`}
                  </button>
                </li>
              );
            })}
          </ol>
        </nav>
        {/* 결과를 지우는 일이라 한 번 묻는다. 자주 쓰는 버튼이 아니라 작은 글자 버튼으로 */}
        {onLeave && <button type="button" onClick={onLeave} className="print:hidden inline-flex min-h-9 items-center text-caption text-soft underline hover:text-ink">다른 파일 올리기</button>}
      </div>
    </header>
  );
}

const EXAMPLE_FILE: Record<ExampleName, string> = { ovenlog: "오븐로그_메타AB_20261117-20261120.csv", heesu: "모닝빈_메타AB_20261117-20261120.csv" };
const ORDER = SCREEN_ORDER;
const NAME = { block: "차단", warn: "주의", info: "참고" } as const;

/** 맨 위 알림 바 (v4.2 규칙 그대로, 축소안 v5): 경고는 결론보다 먼저. 가장 심각한 알림 1개 한 줄 + 등급별 개수 + [모두 보기 ▾].
 *  ③ 준비하기(AN-06)에선 남은 주의를 체크리스트로 옮겼다고 알려 준다. 고정 안내(Breakdown)는 여기 넣지 않는다. */
function AlertBar({ r, step }: { r: Result; step: string }) {
  const [all, setAll] = useState(false);
  const at = ORDER.indexOf(step);
  const list = r.alerts.filter((a) => !a.shown_from || at >= ORDER.indexOf(a.shown_from));
  if (!list.length) return null;
  const count = (l: keyof typeof NAME) => list.filter((a) => a.level === l).length;
  const counts = (["block", "warn", "info"] as const).filter((l) => count(l) > 0).map((l) => `${NAME[l]} ${count(l)}`).join(" · ");
  if (step === "AN-06" && !count("block")) {
    return (
      <section aria-label="알림" className="flex flex-wrap items-center gap-3 rounded-soft border-[1.5px] border-ok-line bg-ok-bg px-4 py-2.5 text-label text-ok-ink">
        <AlertMark level="ok" />
        <b className="flex-1 min-w-48">차단 알림 없음{count("warn") ? ` · 주의 ${count("warn")}건은 아래 체크리스트에 넣었어요` : ""}</b>
      </section>
    );
  }
  // 가장 심각한 1개: 차단 → 주의 → 참고 (같은 등급이면 앞 단계 것). 짧은 글(later)이 있으면 그것.
  const top = list.find((a) => a.level === "block") ?? list.find((a) => a.level === "warn") ?? list[0]!;
  const text = top.later ?? top.text;
  // 상자 = 연한 바탕 + 같은 계열 1.5px 테두리 + 진한 글자 (디자인 시스템 '알림 상자', 꾸미기안_뭉치 .alert)
  const box = top.level === "block" ? "bg-block-bg border-block-line text-block-ink" : top.level === "warn" ? "bg-warn-bg border-warn-line text-warn" : "bg-info-bg border-info-line text-info-ink";
  return (
    <section aria-label="알림" className={`rounded-soft border-[1.5px] px-4 py-2.5 ${box}`}>
      <div className="flex flex-wrap items-center gap-3 text-label">
        <AlertMark level={top.level} />
        <b className="flex-1 min-w-48"><span className="font-normal">{NAME[top.level]} · </span>{text}</b>
        <span className="text-caption text-soft">{counts}</span>
        <button type="button" onClick={() => setAll((x) => !x)} aria-expanded={all} className="inline-flex min-h-8 items-center px-2 text-caption underline">{all ? "접기 ▴" : "모두 보기 ▾"}</button>
      </div>
      {all && <ul className="mt-3 flex flex-col gap-2">{list.map((a) => <AlertLine key={a.kind + a.text} a={a} />)}</ul>}
    </section>
  );
}
