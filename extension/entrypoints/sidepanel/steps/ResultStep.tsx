import type { FlowEvent, FlowState } from "../../../lib/flow";
import { pct, pctRange } from "../../../lib/format";
import { Coach, PrimaryButton } from "../ui/Coach";
import { GradeBadge } from "../ui/GradeBadge";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

/** ③ 결과: 무엇이 문제였나 → 이 칸을 이렇게 → 바꾸면 이 범위. 다음 할 일 하나(바꾸러 가기)로 끝낸다. */
export default function ResultStep({ state, dispatch }: Props) {
  const r = state.result;
  if (!r) return null;
  const e = r.expect;

  return (
    <section className="flex flex-col gap-4">
      <Coach>결과를 읽었어요. 세 가지만 보시면 돼요.</Coach>

      <article className="rounded-2xl bg-paper border border-line p-4 flex flex-col gap-1">
        <p className="text-[13px] text-soft">무엇이 문제였나</p>
        <h2 className="text-[17px] font-bold">{r.finding.title}</h2>
        <p className="text-[15px]">{r.finding.message}</p>
        {r.status === "hold" && r.ab && (
          <p className="text-[15px] mt-1">
            지금까지로는 {r.ab.b}이 나을 확률 약 {Math.round(r.ab.prob_b_better * 100)}%예요. 단정하기엔 아직 이릅니다.
          </p>
        )}
      </article>

      {r.changes.length > 0 && (
        <article className="rounded-2xl bg-paper border border-line p-4 flex flex-col gap-2">
          <p className="text-[13px] text-soft">이 칸을 이렇게 바꾸세요</p>
          <ul className="flex flex-col gap-2">
            {r.changes.map((c) => (
              <li key={c.field_id} className="text-[15px]">
                <strong>{c.label}</strong> → {c.new}
                <span className="block text-[13px] text-soft">{c.note}</span>
              </li>
            ))}
          </ul>
        </article>
      )}

      {e && (
        <article className="rounded-2xl bg-ink text-cream p-4 flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <p className="text-[13px] text-line">{r.status === "hold" ? "기간을 늘리면 이만큼 좁혀져요" : "바꾸면 이 범위"}</p>
            <GradeBadge grade={e.grade} />
          </div>
          <p className="text-[15px]">
            {e.label} 지금 <span className="whitespace-nowrap">{pctRange(e.current)}</span>
          </p>
          <p className="text-[17px] font-bold text-accent">
            → <span className="whitespace-nowrap">{pctRange(e.expected)}</span>
          </p>
          {e.prob_better !== null && r.status !== "hold" && <p className="text-[13px]">좋아질 확률 약 {pct(e.prob_better, 0)}</p>}
        </article>
      )}

      <button
        type="button"
        onClick={() => void browser.tabs.create({ url: browser.runtime.getURL("/report.html" as never) })}
        className="text-left text-[15px] underline"
      >
        보고서 크게 보기
      </button>
      {r.changes.length > 0 ? (
        <PrimaryButton onClick={() => dispatch({ type: "startFix" })}>바꾸러 가기</PrimaryButton>
      ) : (
        <PrimaryButton onClick={() => dispatch({ type: "guideDone" })}>이대로 계속 돌릴게요</PrimaryButton>
      )}
    </section>
  );
}
