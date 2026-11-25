import type { Level } from "../api";
import { VerdictBadge } from "../ui";

/** 개발 판정(채택·유력·보류) → 사장님 화면 배지 3단어 (v4.2). 근거 탭·개발 문서만 확실/유력/보류를 쓴다. */
export function CertaintyBadge({ level, better = "B" }: { level: Level; better?: string }) {
  const word = level === "채택" ? "확실해요" : level === "유력" ? `${better} 쪽이에요` : "아직 몰라요";
  return <VerdictBadge word={word} />;
}

/** 근거 탭용 이름 (확실 / 유력 / 보류 그대로). */
export const DEV_LABEL: Record<Level, string> = { 채택: "확실", 유력: "유력", 보류: "보류" };
