import { useEffect, useReducer, useRef } from "react";
import { initialState, reduce, type FlowEvent, type FlowState, type Step } from "../../lib/flow";
import { loadState, saveState } from "../../lib/storage";
import FindStep from "./steps/FindStep";

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
      </header>
      {state.step === "find" && <FindStep state={state} dispatch={dispatch} />}
    </main>
  );
}
