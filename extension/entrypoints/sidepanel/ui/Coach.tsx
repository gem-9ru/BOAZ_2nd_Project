import type { ReactNode } from "react";

/** 코치가 하는 말 한 덩어리: 작은 캐릭터 + 글. 말풍선 상자 없이 글만 둔다. */
export function Coach({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-3 items-start">
      <span aria-hidden className="mt-0.5 size-7 shrink-0 rounded-full bg-accent grid place-items-center">
        <span className="flex gap-1">
          <i className="block size-1.5 rounded-full bg-ink" />
          <i className="block size-1.5 rounded-full bg-ink" />
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
      className="w-full rounded-xl bg-ink text-cream py-3 text-body font-semibold disabled:opacity-(--state-disabled-opacity) focus-visible:outline-2 focus-visible:outline-accent"
    >
      {props.busy ? "잠시만요…" : props.children}
    </button>
  );
}

/** 오류 한 줄 + 다시 시도 (칸 바로 아래에 둔다). */
export function ErrorLine({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="text-caption text-accent-ink flex items-center gap-2 flex-wrap">
      <span>{message}</span>
      {onRetry && (
        <button type="button" onClick={onRetry} className="underline font-semibold">
          다시 시도
        </button>
      )}
    </div>
  );
}
