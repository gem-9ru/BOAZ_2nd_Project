// 공통 부품. 색은 토큰 이름(bg-surface, text-soft …)으로만 쓴다. 이름은 UX_설계원칙.md의 부품 이름을 따른다.
import { useState, type ReactNode } from "react";

/** 카드: 블록 하나. 번호는 화면 순서(0~7)라 실제 순서가 있는 곳에만 붙인다. */
export function Card({ id, step, title, children }: { id?: string; step?: number; title: string; children: ReactNode }) {
  return (
    <section id={id} aria-labelledby={id ? `${id}-title` : undefined}
      className="bg-card border border-card-border rounded-card p-card flex flex-col gap-stack min-w-0 scroll-mt-4">
      <h2 id={id ? `${id}-title` : undefined} className="text-title font-bold flex items-baseline gap-2">
        {step !== undefined && <span className="text-caption font-semibold text-soft tabular-nums">{step}</span>}
        {title}
      </h2>
      {children}
    </section>
  );
}

/** 주 버튼 / 보조 버튼 / 로딩 버튼 (누른 버튼에 '…중'을 띄워 같은 자리에서 기다리게 한다). */
export function Button({ children, onClick, kind = "primary", busy, disabled, type = "button" }: {
  children: ReactNode; onClick?: () => void; kind?: "primary" | "secondary"; busy?: boolean; disabled?: boolean; type?: "button" | "submit";
}) {
  const look = kind === "primary"
    ? "bg-button text-button-fg hover:bg-button-hover"
    : "border border-ink text-ink hover:bg-sunk";
  return (
    <button type={type} onClick={onClick} disabled={disabled || busy} aria-busy={busy || undefined}
      className={`h-button px-5 rounded-button text-body font-semibold disabled:opacity-50 ${look}`}>
      {busy ? "계산하는 중…" : children}
    </button>
  );
}

export type Word = "확실해요" | "A 쪽이에요" | "B 쪽이에요" | "아직 몰라요";

/** 판정 배지: 사이트 전체에서 문구 3개만. 색만으로 말하지 않게 모양(●◐○)도 같이. */
export function VerdictBadge({ word }: { word: Word }) {
  const look = word === "확실해요" ? { cls: "bg-adopt-bg text-adopt", mark: "●" }
    : word === "아직 몰라요" ? { cls: "bg-hold-bg text-hold", mark: "○" } : { cls: "bg-likely-bg text-likely", mark: "◐" };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-badge px-3 py-1 text-body font-bold whitespace-nowrap ${look.cls}`}>
      <span aria-hidden="true">{look.mark}</span>{word}
    </span>
  );
}

/** 근거 등급: A 실측 · B 매체 추산 · D 우리 가정. */
export function Grade({ g }: { g: "A" | "B" | "D" }) {
  const label = { A: "실측", B: "매체 추산", D: "가정" }[g];
  return <span className="inline-block shrink-0 rounded-badge border border-line px-2 py-0.5 text-caption text-soft whitespace-nowrap">근거 {g} · {label}</span>;
}

/** 접기: 기본은 사장님용, 펼치면 모형·근거. 첫 줄은 항상 '쉽게 말하면'. */
export function HowCalculated({ easy, children }: { easy: string; children: ReactNode }) {
  return (
    <details className="rounded-button bg-details px-4 py-3 group">
      <summary className="cursor-pointer text-body font-semibold text-details-fg">이 숫자는 어떻게 나왔나요?</summary>
      <div className="mt-3 flex flex-col gap-2 text-body text-soft">
        <p><b className="text-ink">쉽게 말하면:</b> {easy}</p>
        {children}
      </div>
    </details>
  );
}

/** 배너: 계속 알고 있어야 하는 경고 (게재 이상). 사용자가 닫을 수 있다. */
export function Banner({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(true);
  if (!open) return null;
  return (
    <div role="status" className="flex items-start gap-3 rounded-button bg-banner text-banner-fg px-4 py-3 text-body">
      <span aria-hidden="true">⚠</span>
      <div className="flex-1">{children}</div>
      <button type="button" onClick={() => setOpen(false)} aria-label="경고 닫기" className="text-caption underline">닫기</button>
    </div>
  );
}

/** 토스트: 복사처럼 이미 끝난 일을 슬쩍 알린다 (버튼 없음). */
export function Toast({ text }: { text: string | null }) {
  return (
    <div aria-live="polite" className="fixed bottom-6 left-1/2 -translate-x-1/2">
      {text && <p className="rounded-button bg-action text-on-action px-4 py-2 text-body shadow-lg">{text}</p>}
    </div>
  );
}

export function won(x: number | null | undefined): string {
  return x == null ? "–" : `₩${Math.round(x).toLocaleString()}`;
}
export function pct(x: number | null | undefined, digits = 0): string {
  return x == null ? "–" : `${(x * 100).toFixed(digits)}%`;
}
