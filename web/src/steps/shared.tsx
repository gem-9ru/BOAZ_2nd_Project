import type { Alert, MatrixRow } from "../api";
import { AlertMark, type Level } from "../ui";

export const STEPS = [
  { id: "AN-01", short: "결론", title: "그래서 뭘 바꾸면 돼요?", next: "왜 그 칸인지 보기" },
  { id: "AN-02", short: "막힌 곳", title: "어디서 막혔나요?", next: "내 세팅 카드 보기" },
  { id: "AN-03", short: "내 세팅", title: "내 다른 설정은 괜찮아요?", next: "값 비교 보기" },
  { id: "AN-04", short: "값 비교", title: "어떤 값이 더 나았어요?", next: "바꾸면 얼마나 좋아지나 보기" },
  { id: "AN-05", short: "바꾸면", title: "이 칸을 바꾸면 얼마나 좋아져요?", next: "적용하러 가기" },
  { id: "AN-06", short: "보내기", title: "이제 어떻게 적용해요?", next: "" },
] as const;

/** 매트릭스 줄 상태 → 신호등 모양 (✓ 괜찮음 · ▲ 비교보다 나쁨/지켜보기 · ■ 기준 미달 · – 해당 없음). */
export function rowLevel(r: MatrixRow): Level | "none" {
  if (r.status === "blocked") return "block";
  if (r.status === "watch" || r.status === "found" || (r.row === "1" && r.detail)) return "warn";
  if (r.status === "skip") return "none";
  return "ok";
}

export function Signal({ level }: { level: Level | "none" }) {
  return level === "none"
    ? <span aria-label="해당 없음" className="inline-grid size-4 place-items-center text-caption text-soft">–</span>
    : <AlertMark level={level} />;
}

export function AlertLine({ a }: { a: Alert }) {
  return (
    <li className="flex items-start gap-2 text-body">
      <span className="mt-1"><AlertMark level={a.level} /></span>
      <span><b>{a.text}</b> <span className="text-soft">{a.todo}</span></span>
    </li>
  );
}
