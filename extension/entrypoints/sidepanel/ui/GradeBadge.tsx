import { GRADE_LABEL } from "../../../lib/format";

/** 숫자의 근거 등급. 색만으로 말하지 않고 글자로 적는다. */
export function GradeBadge({ grade }: { grade: "checked" | "hypothesis" }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-[12px] font-semibold ${grade === "checked" ? "bg-ink text-cream" : "border border-soft text-soft"}`}>
      {GRADE_LABEL[grade]}
    </span>
  );
}
