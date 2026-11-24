import type { ReactNode } from "react";

/** 코치가 하는 말 한 덩어리: 작은 캐릭터 + 글. 말풍선 상자 없이 글만 둔다. */
export function Coach({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-3 items-start">
      <span aria-hidden className="mt-0.5 size-7 shrink-0 rounded-badge bg-accent grid place-items-center">
        <span className="flex gap-1">
          <i className="block size-1.5 rounded-badge bg-on-accent" />
          <i className="block size-1.5 rounded-badge bg-on-accent" />
        </span>
      </span>
      <div className="text-body leading-relaxed">{children}</div>
    </div>
  );
}

/** 화면 맨 아래 큰 버튼 하나. */
export function PrimaryButton(props: { children: ReactNode; onClick?: () => void; disabled?: boolean; busy?: boolean; type?: "button" | "submit" }) {
  return (
    <button
      type={props.type ?? "button"}
      onClick={props.onClick}
      disabled={props.disabled || props.busy}
      className="w-full rounded-button bg-accent text-on-accent py-3 text-body font-semibold transition-colors hover:bg-accent-ink active:bg-accent-ink disabled:opacity-(--state-disabled-opacity) disabled:hover:bg-accent focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
    >
      {props.busy ? "잠시만요…" : props.children}
    </button>
  );
}

/** 오류 한 줄 + 다시 시도 (칸 바로 아래에 둔다). */
export function ErrorLine({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="text-caption text-block-ink flex items-center gap-2 flex-wrap">
      <span aria-hidden className="inline-grid size-3.5 place-items-center rounded-mark bg-block text-mark font-bold text-on-accent">✕</span>
      <span>{message}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="underline font-semibold">
          다시 시도
        </button>
      )}
    </div>
  );
}

/** ▲ 주의 한 줄: 막지는 않지만 알고 넘어가야 하는 것 (v4 알림 모양: ▲ = 주의). */
export function WarnLine({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="status" className="flex flex-wrap items-center gap-2 rounded-button bg-warn-bg px-3 py-2 text-caption text-warn">
      <span aria-hidden="true" className="font-bold">▲</span>
      <span className="sr-only">주의</span>
      <span>{message}</span>
      {onRetry && <button type="button" onClick={onRetry} className="font-semibold underline">다시 시도</button>}
    </div>
  );
}
