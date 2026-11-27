import type { ReactNode } from "react";
import type { Alert, Result } from "../api";
import { AlertMark } from "../ui";

/** 3단계 (축소안 v5): 결론 → 왜 그런지 → 준비하기. 제목은 사장님 질문.
 *  id는 옆 확장 프로그램 패널이 읽는 단계 이름이라 예전 이름을 그대로 쓴다 (② = AN-02~04, ③ = AN-05~06을 합친 화면). */
export const STEPS = [
  { id: "AN-01", short: "결론", title: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요", parts: ["다음엔 ", "이 칸 1개만", " 바꿔서 테스트해 보세요"] },
  { id: "AN-02", short: "왜 그런지", title: "왜 이 칸이에요?", parts: ["왜 ", "이 칸", "이에요?"] },
  { id: "AN-06", short: "준비하기", title: "이 테스트를 준비해요", parts: ["이 테스트를 ", "준비해요", ""] },
] as const;
/** 알림의 screen·shown_from 순서 비교용 (예전 단계 이름 전부) */
export const SCREEN_ORDER = ["AN-00", "AN-01", "AN-02", "AN-03", "AN-04", "AN-05", "AN-06"];

/** 단계 제목 바로 아래 한 줄 요약(질문의 답, 필수) + 보조 설명 한 줄. */
export function Lead({ children, sub, badge }: { children: ReactNode; sub?: ReactNode; badge?: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <p className="flex flex-wrap items-center gap-2 text-lead font-semibold">{children}{badge}</p>
      {sub && <p className="text-body text-soft">{sub}</p>}
    </div>
  );
}

/** 세트 이름 → 'A 자동' · 'B 수동' (노출 위치를 비교한 이름이 아니면 글자만). */
export function armName(name: string, i: number): string {
  const l = "AB"[i] ?? String(i + 1);
  if (name.includes("자동")) return `${l} 자동`;
  if (/수동|피드만|AN ?제외|릴스만/.test(name)) return `${l} 수동`;
  return l;
}

/** 같은 돈으로 온 방문자 수: 두 세트 중 적게 쓴 돈 기준 (지출이 달라도 공정하게). */
export function sameMoney(r: Result): { base: number; counts: number[] } | null {
  const arms = r.summary.arms.slice(0, 2);
  if (arms.length < 2) return null;
  const base = Math.min(...arms.map((a) => a.spend));
  return { base, counts: arms.map((a) => Math.round(((a.visits_per_1000won ?? 0) * base) / 1000)) };
}

/** 신호 (축소안 v5): ✓ 괜찮음 · ↓ 비교 대상이나 기준보다 낮음 · – 아직 몰라요(회색). ▲는 주의 알림 전용이라 신호에 안 씀. */
export type SignalKind = "ok" | "worse" | "low" | "unknown";
export function Signal({ kind }: { kind: SignalKind }) {
  if (kind === "ok") return <AlertMark level="ok" />;
  if (kind === "low" || kind === "worse") return <span aria-label="낮아요" className="inline-grid size-4 place-items-center font-bold text-accent-ink">↓</span>;
  return <span aria-label="아직 몰라요" className="inline-grid size-4 place-items-center text-caption text-hold">–</span>;
}

/** 기준값 비교 신호 글자 (①b): ✓ 괜찮아요 · ↓ 기준보다 낮아요 · – 아직 몰라요. 판정 배지(확실해요·○ 쪽이에요)와 다른 모양 */
export const SIGNAL_WORD = { ok: "✓ 괜찮아요", low: "↓ 기준보다 낮아요", unknown: "– 아직 몰라요" } as const;
export function SignalTag({ signal }: { signal: keyof typeof SIGNAL_WORD }) {
  const look = signal === "ok" ? "bg-ok-bg text-ok-ink" : signal === "low" ? "bg-accent-soft text-accent-ink" : "bg-hold-bg text-hold";
  return <span className={`inline-flex whitespace-nowrap rounded-badge px-2.5 py-1 text-caption font-bold ${look}`}>{SIGNAL_WORD[signal]}</span>;
}

export function AlertLine({ a }: { a: Alert }) {
  return (
    <li className="flex items-start gap-2 text-body">
      <span className="mt-1"><AlertMark level={a.level} /></span>
      <span><b>{a.text}</b> <span className="text-soft">{a.todo}</span></span>
    </li>
  );
}
