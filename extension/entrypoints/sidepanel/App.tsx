import { useEffect, useReducer, useRef, useState } from "react";
import { fields as fetchFields, type Field, type PresetField } from "../../lib/api";
import { initialState, reduce, type FlowEvent, type FlowState, type Step } from "../../lib/flow";
import { loadState, saveState } from "../../lib/storage";
import CopyStep from "./steps/CopyStep";
import FindStep from "./steps/FindStep";
import GuideStep from "./steps/GuideStep";
import WaitStep from "./steps/WaitStep";
import QuestionStep from "./steps/QuestionStep";
import ResultStep from "./steps/ResultStep";
import UploadStep from "./steps/UploadStep";
import { ErrorLine } from "./ui/Coach";

const STAGES: { label: string; steps: Step[] }[] = [
  { label: "찾기", steps: ["find"] },
  { label: "세팅", steps: ["copy", "questions", "guide", "wait"] },
  { label: "분석", steps: ["upload", "result", "fix"] },
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
      const next = changes["coach.v3.state"]?.newValue as FlowState | undefined;
      if (next && JSON.stringify(next) !== JSON.stringify(latest.current)) dispatch({ type: "__load", state: next });
    };
    browser.storage.onChanged.addListener(onChanged);
    return () => browser.storage.onChanged.removeListener(onChanged);
  }, []);

  const [spec, setSpec] = useState<{ fields: Field[]; defaults: PresetField[] } | null>(null);
  const [specError, setSpecError] = useState<string | null>(null);
  const loadSpec = () => fetchFields().then(setSpec, (e: Error) => setSpecError(e.message));
  useEffect(() => {
    if (state.step === "questions" && !spec) void loadSpec();
  }, [state.step]);

  const current = STAGES.findIndex((st) => st.steps.includes(state.step));

  return (
    <main className="min-h-screen p-4 flex flex-col gap-6">
      <header className="flex items-center justify-between">
        <h1 className="text-[17px] font-bold">광고 코치</h1>
        <ol className="flex gap-3 text-[13px]" aria-label="진행 단계">
          {STAGES.map((st, i) => (
            <li
              key={st.label}
              aria-current={i === current ? "step" : undefined}
              className={i === current ? "font-semibold text-ink" : i < current ? "text-soft" : "text-line"}
            >
              {"①②③"[i]} {st.label}
            </li>
          ))}
        </ol>
        {state.step !== "find" && (
          <button type="button" onClick={() => { if (window.confirm("처음부터 다시 할까요? 지금까지 답한 내용이 지워져요.")) dispatch({ type: "reset" }); }} className="text-[12px] text-soft underline">
            처음부터
          </button>
        )}
      </header>
      {state.guide && <GuideStep state={state} dispatch={dispatch} />}
      {!state.guide && state.step === "wait" && <WaitStep state={state} dispatch={dispatch} />}
      {state.step === "find" && <FindStep state={state} dispatch={dispatch} />}
      {!state.guide && state.step === "upload" && <UploadStep state={state} dispatch={dispatch} />}
      {state.step === "result" && <ResultStep state={state} dispatch={dispatch} />}
      {state.step === "copy" && <CopyStep state={state} dispatch={dispatch} />}
      {state.step === "questions" && spec && (
        <QuestionStep state={state} dispatch={dispatch} fields={spec.fields} defaults={spec.defaults} />
      )}
      {state.step === "questions" && !spec && !specError && (
        <p role="status" className="text-[13px] text-soft">질문을 불러오는 중이에요…</p>
      )}
      {state.step === "questions" && specError && <ErrorLine message={specError} onRetry={() => { setSpecError(null); void loadSpec(); }} />}
    </main>
  );
}
