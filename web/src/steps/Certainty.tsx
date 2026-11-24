/** 제안의 확실도: 확실 = 메인 진하게 · 유력 = 메인 연하게 · 보류 = 회색. 색만으로 말하지 않게 모양(●◐○)도. */
export function CertaintyBadge({ level }: { level: "채택" | "유력" | "보류" }) {
  const look = level === "채택" ? { cls: "bg-adopt text-on-accent", mark: "●", label: "확실" }
    : level === "유력" ? { cls: "bg-likely-bg text-likely ring-1 ring-inset ring-likely", mark: "◐", label: "유력" }
    : { cls: "bg-hold-bg text-hold", mark: "○", label: "보류" };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-badge px-3 py-1 text-body font-bold ${look.cls}`}>
      <span aria-hidden="true">{look.mark}</span>{look.label}
    </span>
  );
}
