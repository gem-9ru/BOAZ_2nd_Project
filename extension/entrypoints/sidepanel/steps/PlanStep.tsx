import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, PrimaryButton } from "../ui/Coach";

/** ③ 다음에 할 일: 분석 페이지 결론 3줄 + 바꿀 칸 하나 → 캐릭터가 그 칸을 짚는다. */
export default function PlanStep({ state, dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
  const p = state.plan;
  if (!p) return null;
  return (
    <section className="flex flex-col gap-4">
      <Coach>분석 페이지에서 받은 결과예요. 바꿀 칸은 하나예요.</Coach>
      {p.badge && (
        <p className="flex items-center gap-2 text-body">
          <span className="rounded-full bg-paper border border-ink px-3 py-1 font-bold">{p.badge.word}</span>
          <span className="text-soft">1,000원당 방문 기준 {Math.round(p.badge.prob * 100)}%</span>
        </p>
      )}
      <ul className="flex flex-col gap-1 text-label border-l-4 border-accent pl-3">
        {p.summary.map((l) => <li key={l}>{l}</li>)}
      </ul>
      <div className="rounded-xl border-2 border-ink bg-paper px-4 py-3">
        <p className="text-caption font-semibold text-accent-ink">{p.action}</p>
        <p className="text-body"><b>{p.change.label}</b> → {p.change.new}</p>
        <p className="text-caption text-soft">{p.change.note}</p>
      </div>
      <PrimaryButton onClick={() => dispatch({ type: "startFix" })}>바꾸러 가기</PrimaryButton>
      <button type="button" onClick={() => dispatch({ type: "startUpload" })} className="self-start text-caption text-soft underline">
        다른 코드 넣기
      </button>
    </section>
  );
}
