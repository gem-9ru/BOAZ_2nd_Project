import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Chat } from "../ui/Chat";
import { Coach, PrimaryButton } from "../ui/Coach";

// 확실도 토큰 (design-system): 확실 adopt · 유력 likely · 보류 hold
const CERT = { 채택: { mark: "●", cls: "bg-adopt text-on-accent" }, 유력: { mark: "◐", cls: "bg-likely-bg text-likely ring-1 ring-inset ring-likely" }, 보류: { mark: "○", cls: "bg-hold-bg text-hold" } } as const;

/** EX-03 바꿀 칸 받기: 분석 페이지가 보낸 변경안을 맨 위에 고정, 챗봇이 이어서 설명, [바꾸러 가기]로 그 칸만 짚는다. */
export default function PlanStep({ state, dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
  const p = state.plan;
  if (!p) return null;
  const c = p.change;
  const cert = c.certainty ? CERT[c.certainty.level] : null;
  return (
    <section className="flex flex-col gap-4">
      <section aria-label="바꿀 칸" className="sticky top-0 z-10 flex flex-col gap-2 rounded-card border-2 border-accent bg-paper px-4 py-3 shadow-sm">
        <p className="text-caption font-semibold text-accent-ink">{c.path ?? c.label}</p>
        <p className="text-body font-bold">{c.now ? `${c.now} → ` : ""}{c.new}</p>
        {cert && c.certainty && (
          <span className={`self-start inline-flex items-center gap-1 rounded-badge px-2.5 py-0.5 text-caption font-bold ${cert.cls}`}>
            <span aria-hidden="true">{cert.mark}</span>{c.certainty.label}
          </span>
        )}
        <p className="text-caption text-soft">{c.note}</p>
      </section>
      <Coach>분석 페이지에서 받은 변경안이에요. 광고 관리자에서 이 칸만 바꾸고, 나머지는 그대로 두세요.</Coach>
      {(p.keep?.length ?? 0) > 0 && (
        <ul className="flex flex-col gap-1.5 text-caption">
          {p.keep!.map((k) => (
            <li key={k.field_id} className="flex gap-2"><span className="shrink-0 rounded-badge bg-sunk px-2 py-0.5 font-semibold">유지</span><span>{k.path}: {k.value}</span></li>
          ))}
        </ul>
      )}
      {(c.checklist?.length ?? 0) > 0 && (
        <div className="flex flex-col gap-1.5">
          <p className="text-caption font-semibold text-soft">다음 테스트 전에 확인할 것</p>
          <ul className="flex flex-col gap-1 text-caption">
            {c.checklist!.map((t) => <li key={t}><label className="flex items-start gap-2"><input type="checkbox" className="mt-0.5 accent-accent" />{t}</label></li>)}
          </ul>
        </div>
      )}
      <Chat code={p.code} step="EX-03" />
      <PrimaryButton onClick={() => dispatch({ type: "startFix" })}>바꾸러 가기</PrimaryButton>
      <button type="button" onClick={() => dispatch({ type: "startUpload" })} className="self-start text-caption text-soft underline">
        다른 코드 넣기
      </button>
    </section>
  );
}
