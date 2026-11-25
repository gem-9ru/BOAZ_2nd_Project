import type { ReactNode } from "react";
import type { Alert, Result } from "../api";
import { AlertMark } from "../ui";

/** 7단계 (설계서 v4.2): 제목은 사장님 질문, [다음] 버튼 문구는 다음 화면 내용. */
export const STEPS = [
  { id: "AN-01", short: "확인·결론", title: "다음엔 이 칸 1개만 바꿔서 테스트해 보세요", next: "왜 그런지 보기" },
  { id: "AN-02", short: "막힌 곳", title: "어디서 막혔나요?", next: "내 세팅 보기" },
  { id: "AN-03", short: "세팅 카드", title: "내 다른 설정은 괜찮나요?", next: "값 비교 보기" },
  { id: "AN-04", short: "값 비교", title: "어떤 값이 더 나았나요?", next: "바꾸면 어떻게 돼요?" },
  { id: "AN-05", short: "바꾸면", title: "예산을 바꾸면 손님이 몇 명 올까요?", next: "보내기" },
  { id: "AN-06", short: "보내기", title: "이 테스트를 광고 관리자에 준비해요", next: "" },
] as const;

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

/** 같은 돈으로 온 손님 수: 두 세트 중 적게 쓴 돈 기준 (지출이 달라도 공정하게). */
export function sameMoney(r: Result): { base: number; counts: number[] } | null {
  const arms = r.summary.arms.slice(0, 2);
  if (arms.length < 2) return null;
  const base = Math.min(...arms.map((a) => a.spend));
  return { base, counts: arms.map((a) => Math.round(((a.visits_per_1000won ?? 0) * base) / 1000)) };
}

/** 신호 (v4.2): ✓ 괜찮음 · ↓ 비교 대상보다 나쁨 · ▲ 기준 미달(주의) · – 아직 몰라요(회색). ▲는 주의 전용. */
export type SignalKind = "ok" | "worse" | "low" | "unknown";
export function Signal({ kind }: { kind: SignalKind }) {
  if (kind === "ok") return <AlertMark level="ok" />;
  if (kind === "low") return <AlertMark level="warn" />;
  if (kind === "worse") return <span aria-label="비교 대상보다 나쁨" className="inline-grid size-4 place-items-center font-bold text-accent-ink">↓</span>;
  return <span aria-label="아직 몰라요" className="inline-grid size-4 place-items-center text-caption text-hold">–</span>;
}

export function AlertLine({ a }: { a: Alert }) {
  return (
    <li className="flex items-start gap-2 text-body">
      <span className="mt-1"><AlertMark level={a.level} /></span>
      <span><b>{a.text}</b> <span className="text-soft">{a.todo}</span></span>
    </li>
  );
}
