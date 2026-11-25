import type { Change } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Chat } from "../ui/Chat";
import { Coach, PrimaryButton } from "../ui/Coach";

/** v4.2 테스트안: 서버가 보내는 필드 (lib/api Change에 더해 오는 것) */
type TestPlan = Change & { tag?: string; new_short?: string; reason?: string; tested?: boolean };

// 판정 배지 토큰 (design-system): 확실해요 adopt · ○ 쪽이에요 likely · 아직 몰라요 hold. 사장님 화면 문구는 3개만 (v4.2)
const LOOK = {
  확실해요: { mark: "●", cls: "bg-adopt text-on-accent" },
  쪽이에요: { mark: "◐", cls: "bg-adopt-bg text-adopt ring-1 ring-inset ring-likely" },
  "아직 몰라요": { mark: "○", cls: "bg-hold-bg text-hold" },
} as const;

/** 개발 판정(채택·유력·보류)이나 옛 라벨이 와도 사장님 말 3개로만 보여 준다. */
export function ownerWord(level: "채택" | "유력" | "보류", label: string | undefined, better = "B"): string {
  if (label && !["확실", "유력", "보류"].includes(label)) return label;
  return level === "채택" ? "확실해요" : level === "유력" ? `${better} 쪽이에요` : "아직 몰라요";
}

/** EX-03 바꿀 칸 받기 (v4.2): 분석 페이지가 보낸 테스트안을 맨 위에 고정 ('테스트 제안' 태그, AN-01과 같은 문구),
 *  챗봇이 이어서 설명, 다음 테스트 체크리스트 4개, [그 칸으로 이동]으로 그 칸만 짚는다. 원래 세트는 그대로 두고 복제본에서만. */
export default function PlanStep({ state, dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
  const p = state.plan;
  if (!p) return null;
  const c = p.change as TestPlan;
  const better = p.badge?.word?.startsWith("A") ? "A" : "B";
  const word = !c.tag && c.certainty ? ownerWord(c.certainty.level, c.certainty.label, better) : null;
  const look = word ? (word.endsWith("쪽이에요") ? LOOK.쪽이에요 : LOOK[word as "확실해요" | "아직 몰라요"] ?? LOOK["아직 몰라요"]) : null;
  return (
    <section className="flex flex-col gap-4">
      <section aria-label="바꿀 칸" className="sticky top-0 z-10 flex flex-col gap-2 rounded-card border-2 border-accent bg-paper px-4 py-3 shadow-sm">
        <p className="text-caption text-soft">분석 페이지에서 도착</p>
        <p className="text-caption font-semibold text-accent-ink">{c.path ?? c.label}</p>
        <p className="text-body font-bold">{c.now ? `${c.now} → ` : ""}{c.new_short ?? c.new}</p>
        {c.tag && <span className="self-start rounded-badge border border-dashed border-accent bg-paper px-2.5 py-0.5 text-caption font-bold text-accent-ink">{c.tag}</span>}
        {look && word && (
          <span className={`self-start inline-flex items-center gap-1 rounded-badge px-2.5 py-0.5 text-caption font-bold ${look.cls}`}>
            <span aria-hidden="true">{look.mark}</span>{word}
          </span>
        )}
      </section>
      <Coach>
        {c.reason ?? c.note} 지금 세트는 그대로 두고, 복제한 세트에서 이 칸만 바꾸세요. 두 세트를 같은 날 같이 돌려야 비교할 수 있어요.
      </Coach>
      {(p.keep?.length ?? 0) > 0 && (
        <ul className="flex flex-col gap-1.5 text-caption">
          {p.keep!.map((k) => (
            <li key={k.field_id} className="flex gap-2"><span className="shrink-0 rounded-badge bg-sunk px-2 py-0.5 font-semibold">유지</span><span>{k.path}: {k.value}</span></li>
          ))}
        </ul>
      )}
      {(c.checklist?.length ?? 0) > 0 && (
        <div className="flex flex-col gap-1.5">
          <p className="text-caption font-semibold text-soft">다음 테스트 체크리스트</p>
          <ul className="flex flex-col gap-1 text-caption">
            {c.checklist!.map((t) => <li key={t}><label className="flex items-start gap-2"><input type="checkbox" className="mt-0.5 accent-accent" />{t}</label></li>)}
          </ul>
        </div>
      )}
      <Chat code={p.code} step="EX-03" />
      <PrimaryButton onClick={() => dispatch({ type: "startFix" })}>그 칸으로 이동</PrimaryButton>
      <button type="button"
        onClick={() => dispatch({ type: "startNextTest", fieldId: c.field_id, label: c.label, value: c.new_short ?? c.new })}
        className="rounded-button border border-accent bg-paper py-2.5 text-body font-semibold text-accent-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
        다음 테스트 세팅 ▶
      </button>
      <p className="-mt-2 text-caption text-soft">② 세팅 목록으로 가요. 바꿀 칸 1개만 '지금', 나머지는 지난번 값 그대로예요. 게시는 직접 해 주세요.</p>
      <button type="button" onClick={() => dispatch({ type: "startUpload" })} className="self-start text-caption text-soft underline">
        다른 코드 넣기
      </button>
    </section>
  );
}
