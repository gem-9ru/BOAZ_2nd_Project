import type { Change } from "../../../lib/api";
import type { FlowEvent, FlowState, Plan } from "../../../lib/flow";
import { isoDate, META_DAILY_MIN, minBudget, scheduleDays } from "../../../lib/settings";
import { Chat } from "../ui/Chat";
import { Coach, PrimaryButton } from "../ui/Coach";

/** v4.2 테스트안: 서버가 보내는 필드 (lib/api Change에 더해 오는 것) */
type TestPlan = Change & { tag?: string; new_short?: string; reason?: string; tested?: boolean; what?: string; per_set?: number };

const won = (n: number) => `${n.toLocaleString()}원`;
const day = (iso: string) => { const [, m, d] = iso.split("-").map(Number); return `${m}월 ${d}일`; };

/** 다음 테스트의 돈·기간: 내일 시작(하루 여유), 지난번과 같은 길이, 세트당 금액은 분석 페이지 권장(예산 칸을 바꾸는 테스트면 '더 모아야 할 금액').
 *  메타 최소(하루 약 1,336원 × 일수)보다 적으면 올린다 — 안 그러면 광고가 안 나간다. 권장 금액이 없으면 지난 금액 그대로. */
export function nextMoney(p: Plan, settings: FlowState["settings"], today = new Date()) {
  const c = p.change as TestPlan;
  const val = (id: string) => settings.find((x) => x.fieldId === id)?.value;
  const lastStart = val("meta.adset.start_date")?.slice(0, 10);
  const lastEnd = val("meta.adset.end_date")?.slice(0, 10);
  const last = lastStart && lastEnd ? scheduleDays({ start: lastStart, end: lastEnd }) : NaN;
  const days = last > 0 ? last : 7;
  const at = (n: number) => isoDate(new Date(today.getFullYear(), today.getMonth(), today.getDate() + n));
  const want = /budget/.test(c.field_id) ? p.watch?.find((w) => w.field_id === c.field_id)?.need_per_set : c.per_set;
  const amount = want ? Math.max(want, minBudget(days)) : null;
  return { startDate: at(1), endDate: at(days), days, want, amount, budget: amount ? won(amount) : val("meta.adset.lifetime_budget") || undefined };
}

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
 *  다음 테스트 돈·기간을 먼저 밝히고, 체크리스트 4개, 챗봇은 추천 질문만(카드와 같은 첫 말은 빼고), [다음 테스트 세팅]으로 ② 세팅에 간다.
 *  원래 세트를 고치는 [그 칸으로 이동]은 비교를 깨서 뺐다. */
export default function PlanStep({ state, dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
  const p = state.plan;
  if (!p) return null;
  const c = p.change as TestPlan;
  const m = nextMoney(p, state.settings);
  const better = p.badge?.word?.startsWith("A") ? "A" : "B";
  const word = !c.tag && c.certainty ? ownerWord(c.certainty.level, c.certainty.label, better) : null;
  const look = word ? (word.endsWith("쪽이에요") ? LOOK.쪽이에요 : LOOK[word as "확실해요" | "아직 몰라요"] ?? LOOK["아직 몰라요"]) : null;
  return (
    <section className="flex flex-col gap-4">
      <section aria-label="바꿀 칸" className="sticky top-0 z-10 flex flex-col gap-2 rounded-card border-2 border-accent bg-paper px-4 py-3 shadow-raised">
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
        {c.reason ?? c.note} 지난 세트는 그대로 두고, 복제한 세트에서 이 칸만 바꾸세요.
      </Coach>
      <section aria-label="다음 테스트 돈·기간" className="flex flex-col gap-1 rounded-card border border-line bg-paper px-3 py-2 text-caption">
        <p className="font-semibold">다음 테스트 돈·기간</p>
        <p className="text-body font-bold">
          {m.amount ? `두 세트 × 세트당 ${won(m.amount)} = 합계 ${won(m.amount * 2)}` : m.budget ? `두 세트 × 세트당 ${m.budget}` : "세트당 금액은 ② 세팅에서 정해요"}
        </p>
        {m.want && m.amount! > m.want && (
          <p className="text-soft">분석 페이지 권장은 세트당 {won(m.want)}인데, {m.days}일이면 메타 최소(하루 약 {won(META_DAILY_MIN)} × {m.days}일)보다 적어서 올렸어요.</p>
        )}
        <p>{day(m.startDate)} ~ {day(m.endDate)} ({m.days}일) · 내일 시작, 지난번과 같은 길이</p>
        <p>지난 광고는 끝났어요. 지난 세트를 복제해 두 세트를 새로 같이 돌려요: 하나는 지난번 그대로, 하나는 이 칸만 바꿔서. 두 세트 모두 이 금액·날짜로 맞춰야 정한 돈만 나가요.</p>
      </section>
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
      <Chat code={p.code} step="EX-03" greet={false} />
      <PrimaryButton onClick={() => dispatch({ type: "startNextTest", fieldId: c.field_id, label: c.label, value: c.what ?? c.new_short ?? c.new,
        startDate: m.startDate, endDate: m.endDate, budget: m.budget })}>
        다음 테스트 세팅 ▶
      </PrimaryButton>
      <p className="-mt-2 text-caption text-soft">② 세팅 목록으로 가요. 뭉치가 바꿀 칸 · 금액 · 날짜 · 게시 전 돈 확인만 짚어요. 게시는 직접 해 주세요.</p>
      <button type="button" onClick={() => dispatch({ type: "startUpload" })} className="self-start text-caption text-soft underline">
        다른 코드 넣기
      </button>
    </section>
  );
}
