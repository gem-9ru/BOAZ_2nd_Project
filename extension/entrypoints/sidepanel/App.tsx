import { useEffect, useReducer, useRef, useState } from "react";
import { fields as fetchFields, type Field, type PresetField } from "../../lib/api";
import { initialState, reduce, type FlowEvent, type FlowState, type Step } from "../../lib/flow";
import { useAnalysisTab } from "../../lib/analysisTab";
import { loadState, saveState, STATE_KEY } from "../../lib/storage";
import AnalysisAssistant from "./steps/AnalysisAssistant";
import { forgetCopyWork } from "./steps/CopyStep";
import CopyStep from "./steps/CopyStep";
import FindStep from "./steps/FindStep";
import GuideStep from "./steps/GuideStep";
import WaitStep from "./steps/WaitStep";
import QuestionStep from "./steps/QuestionStep";
import CodeStep from "./steps/CodeStep";
import PlanStep from "./steps/PlanStep";
import PrepStep from "./steps/PrepStep";
import { ErrorLine } from "./ui/Coach";
import { HomeSeat } from "./ui/HomeSeat";

const STAGES: { label: string; steps: Step[] }[] = [
  { label: "찾기", steps: ["prep", "find"] },
  { label: "세팅", steps: ["copy", "questions", "guide", "wait"] },
  { label: "분석", steps: ["upload", "plan"] },
];

type Action = FlowEvent | { type: "__load"; state: FlowState };

function appReduce(s: FlowState, a: Action): FlowState {
  return a.type === "__load" ? a.state : reduce(s, a);
}

export default function App() {
  const [state, dispatch] = useReducer(appReduce, undefined, initialState);
  const loaded = useRef(false);

  useEffect(() => {
    loadState().then((s) => {
      loaded.current = true;
      dispatch({ type: "__load", state: s });
    });
  }, []);
  useEffect(() => {
    if (loaded.current) void saveState(state);
  }, [state]);
  // 패널이 닫혀 있던 동안 배경 스크립트가 쓴 진행(캐릭터 단계)을 따라간다.
  const latest = useRef(state);
  latest.current = state;
  useEffect(() => {
    const onChanged = (changes: Record<string, { newValue?: unknown }>) => {
      const next = changes[STATE_KEY]?.newValue as FlowState | undefined;
      // 더 옛 차례(rev)의 쓰기가 늦게 도착하면 무시: [처음부터] 직후 배경의 옛 진행이 지운 상태를 되살리지 않게 (재검토 B12)
      if (next && (next.rev ?? 0) < (latest.current.rev ?? 0)) return;
      if (next && JSON.stringify(next) !== JSON.stringify(latest.current)) dispatch({ type: "__load", state: next });
    };
    browser.storage.onChanged.addListener(onChanged);
    return () => browser.storage.onChanged.removeListener(onChanged);
  }, []);

  const [spec, setSpec] = useState<{ fields: Field[]; defaults: PresetField[] } | null>(null);
  const [specError, setSpecError] = useState<string | null>(null);
  const loadSpec = () => fetchFields().then(setSpec, (e: Error) => setSpecError(e.message));
  useEffect(() => {
    if ((state.step === "questions" || state.step === "prep") && !spec) void loadSpec();
  }, [state.step]);

  // 분석 페이지 탭을 보고 있으면 이 패널은 그 페이지 옆 광고 어시스턴트가 된다 (v4.2 AN-COM ④)
  const analysis = useAnalysisTab();
  // 광고가 끝났으면(종료일 다음 날부터) 기다리기 화면도 ③ 분석 차례로 + ③에 점 (설계서 EX-02 ①, 화면 검토 24)
  const end = state.endDate?.slice(0, 10);
  const ended = state.step === "wait" && Boolean(end) && new Date(`${end}T23:59:59`) < new Date();
  // 분석 탭을 보고 있어도 아직 광고를 안 켰으면(찾기·세팅) 그 단계 그대로 (재검토 B11)
  const late = ["wait", "upload", "plan"].includes(state.step);
  const current = (analysis && late) || ended ? 2 : STAGES.findIndex((st) => st.steps.includes(state.step));

  return (
    <main className="min-h-screen flex flex-col gap-6 pb-4">
      {/* 꾸미기안_뭉치: 보라 머리(아래만 둥글게) · 뭉치 얼굴(집) · 이름과 한 줄 소개 · 알약 모양 단계 */}
      <header className="relative isolate overflow-hidden rounded-b-sheet bg-linear-135 from-accent to-accent-ink px-4 pt-4 pb-3.5 text-on-accent">
        {/* 꾸미기안 .top: 오른쪽 위·아래 옅은 흰 동그라미 무늬 (장식) */}
        <span aria-hidden="true" className="absolute top-[-10%] left-[88%] -z-10 size-30 -translate-x-1/2 -translate-y-1/2 rounded-badge bg-on-accent/20" />
        <span aria-hidden="true" className="absolute top-[120%] left-[70%] -z-10 size-35 -translate-x-1/2 -translate-y-1/2 rounded-badge bg-on-accent/10" />
        <div className="flex items-center gap-2.5">
          <HomeSeat away={Boolean(state.guide?.away)} />
          <div className="min-w-0">
            <h1 className="text-title font-extrabold tracking-tight">Ad Assistant</h1>
            <p className="text-small">메타 광고, 한 칸씩 같이 채워요</p>
          </div>
          {state.step !== "find" && state.step !== "prep" && (
            <button type="button" onClick={() => { if (window.confirm("처음부터 다시 할까요? 지금까지 답한 내용이 지워져요.")) { forgetCopyWork(); dispatch({ type: "reset" }); } }}
              title="지금까지 답한 내용이 모두 지워져요"
              className="ml-auto min-h-11 shrink-0 rounded-badge bg-on-accent/15 px-3 text-small font-semibold">
              ↺ 처음부터
            </button>
          )}
        </div>
        {/* 진행 표시: 누르는 탭처럼 보이지 않게 알약 대신 밑줄 막대 (처음 쓰는 사람 따라가기 5, 2026-11-27) */}
        <ol className="mt-4 flex gap-1.5 text-caption" aria-label="진행 단계">
          {STAGES.map((st, i) => (
            <li
              key={st.label}
              aria-current={i === current ? "step" : undefined}
              className={`flex-1 border-b-[3px] pb-1.5 text-center ${i === current ? "border-on-accent font-bold" : i < current ? "border-on-accent/60 font-semibold" : "border-on-accent/25 font-medium"}`}
            >
              {/* 준비물을 묻는 동안은 '준비' (찾기 탭에서 준비물을 묻는 것처럼 보였음, 따라가기 8) */}
              {i < current ? `✓ ${st.label}` : `${"①②③"[i]} ${i === 0 && state.step === "prep" ? "준비" : st.label}`}
              {i === 2 && ended && <><span aria-hidden="true" className="ml-1 text-warn-mark">●</span><span className="sr-only"> 결과를 볼 때예요</span></>}
            </li>
          ))}
        </ol>
      </header>
      <div className="flex flex-col gap-6 px-4">
      {analysis && <AnalysisAssistant tab={analysis} dispatch={dispatch} handled={state.planSent} plan={state.plan} flowStep={state.step} />}
      {!analysis && <>
      {state.guide && state.step !== "prep" && <GuideStep state={state} dispatch={dispatch} />}
      {!state.guide && state.step === "wait" && <WaitStep state={state} dispatch={dispatch} />}
      {state.step === "find" && <FindStep state={state} dispatch={dispatch} />}
      {!state.guide && state.step === "upload" && <CodeStep state={state} dispatch={dispatch} />}
      {state.step === "plan" && <PlanStep state={state} dispatch={dispatch} />}
      {state.step === "copy" && <CopyStep state={state} dispatch={dispatch} />}
      {state.step === "questions" && spec && (
        <QuestionStep state={state} dispatch={dispatch} fields={spec.fields} defaults={spec.defaults} />
      )}
      {state.step === "prep" && spec && <PrepStep state={state} dispatch={dispatch} fields={spec.fields} />}
      {(state.step === "questions" || state.step === "prep") && !spec && !specError && (
        <p role="status" className="text-caption text-soft">질문을 불러오는 중이에요…</p>
      )}
      {(state.step === "questions" || state.step === "prep") && specError && <ErrorLine message={specError} onRetry={() => { setSpecError(null); void loadSpec(); }} />}
      </>}
      </div>
    </main>
  );
}
