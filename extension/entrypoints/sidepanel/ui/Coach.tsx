import type { ReactNode } from "react";
import wave from "../../../assets/mungchi/wave.png";

/** 광고 어시스턴트가 하는 말 한 덩어리: 손 흔드는 뭉치 + 흰 말풍선 (꾸미기안_뭉치 .say). 그림은 장식이라 읽지 않는다. */
export function Coach({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-end gap-2.5">
      <img src={wave} alt="" aria-hidden="true" draggable={false} className="w-14 shrink-0 select-none" />
      <div className="rounded-card rounded-bl-mark border-2 border-line bg-paper px-3.5 py-3 text-label leading-relaxed">{children}</div>
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
      className="w-full min-h-12 rounded-button bg-accent text-on-accent py-3 text-body font-bold shadow-press transition-colors hover:bg-accent-ink active:translate-y-0.5 active:shadow-none disabled:cursor-default disabled:border-disabled-line disabled:bg-disabled-bg disabled:text-disabled-fg disabled:shadow-none disabled:shadow-none disabled:hover:bg-disabled-bg focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
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

/** ▲ 주의 한 줄: 막지는 않지만 알고 넘어가야 하는 것 (v4 알림 모양: ▲ = 주의 전용).
 *  v4.2: 이유 → 할 일 → [다시 시도] 순서. */
export function WarnLine({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="status" className="flex flex-wrap items-center gap-2 rounded-soft border-[1.5px] border-warn-line bg-warn-bg px-3 py-2 text-caption text-warn">
      <span aria-hidden="true" className="font-bold">▲</span>
      <span className="sr-only">주의</span>
      <span>{message}</span>
      {onRetry && <button type="button" onClick={onRetry} className="font-semibold underline">다시 시도</button>}
    </div>
  );
}
