import { useEffect, useRef, useState } from "react";
import { askAssistant, type AssistantAlert } from "../../../lib/api";

export interface Bubble { from: "assistant" | "me"; text: string; alert?: AssistantAlert }

/** 사장님 말풍선(오른쪽)·어시스턴트 말풍선(왼쪽) 모양 */
export function bubbleClass(from: Bubble["from"]): string {
  return from === "me" ? "self-end max-w-[85%] rounded-button bg-accent px-3 py-2 text-body text-on-accent" : "max-w-[95%] rounded-button bg-paper px-3 py-2 text-body";
}

/** 질문 보내기: 내 말풍선 → 생각하는 중 → 답(또는 오류) 말풍선. 확장 EX-03과 분석 페이지 옆 어시스턴트가 같이 쓴다. */
export function useAsk(code: string | null | undefined, step: string | null | undefined, add: (b: Bubble) => void) {
  const [busy, setBusy] = useState(false);
  async function ask(q: string) {
    if (!q.trim() || busy || !code || !step) return;
    add({ from: "me", text: q });
    setBusy(true);
    try {
      add({ from: "assistant", text: (await askAssistant(code, step, q)).message });
    } catch (e) {
      add({ from: "assistant", text: (e as Error).message });
    } finally {
      setBusy(false);
    }
  }
  return { busy, ask };
}

/** 추천 질문 칩 + 묻기 칸 */
export function AskForm({ id, label, suggestions, busy, onAsk }: { id: string; label: string; suggestions: string[]; busy: boolean; onAsk: (q: string) => void }) {
  const [text, setText] = useState("");
  const send = (q: string) => { onAsk(q); setText(""); };
  return (
    <>
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <button key={s} type="button" onClick={() => send(s)} className="min-h-11 rounded-badge border border-accent bg-paper px-3 text-label text-accent-ink">{s}</button>
          ))}
        </div>
      )}
      <label htmlFor={id} className="text-caption font-semibold text-soft">{label}</label>
      <form className="-mt-1 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (text.trim() && !busy) send(text); }}>
        <input id={id} value={text} onChange={(e) => setText(e.target.value)} placeholder="예: CPM이 뭐예요?"
          className="min-h-11 min-w-0 flex-1 rounded-button border border-field-line bg-paper px-3 text-body" />
        <button type="submit" disabled={!text.trim() || busy} className="min-h-11 rounded-button bg-accent px-4 text-label font-semibold text-on-accent disabled:cursor-default disabled:border-disabled-line disabled:bg-disabled-bg disabled:text-disabled-fg disabled:shadow-none">묻기</button>
      </form>
    </>
  );
}

/** 광고 어시스턴트 말풍선 (EX-03): 첫 말 + 추천 질문 2개, 질문하면 분석 결과(테스트안 JSON)로만 설명한다.
 *  말 규칙은 분석 페이지와 같다 (서버 assistant.SYSTEM, v4.2 AN-TXT): 판정 3단어 · JSON 숫자만 · 사장님 말 먼저. */
/** greet=false: 첫 말은 빼고 추천 질문만 (같은 설명이 바로 위 카드에 이미 있을 때) */
export function Chat({ code, step, greet = true }: { code: string; step: string; greet?: boolean }) {
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const started = useRef(false);
  const { busy, ask } = useAsk(code, step, (b) => setBubbles((all) => [...all, b]));

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    askAssistant(code, step).then((o) => {
      if (greet) setBubbles([{ from: "assistant", text: o.message }]);
      setSuggestions(o.suggestions ?? []);
    }, () => setBubbles([{ from: "assistant", text: "지금은 어시스턴트에 연결하지 못했어요. 바꿀 칸 안내는 그대로 쓸 수 있어요." }]));
  }, [code, step, greet]);

  return (
    <section aria-label="광고 어시스턴트" className="flex flex-col gap-2 rounded-card bg-accent-soft p-3">
      <div className="flex flex-col gap-2" aria-live="polite">
        {bubbles.map((b, i) => <p key={i} className={bubbleClass(b.from)}>{b.text}</p>)}
        {busy && <p role="status" className="text-caption text-soft">생각하는 중…</p>}
      </div>
      <AskForm id="ex-ask" label="어시스턴트에게 묻기" suggestions={suggestions} busy={busy} onAsk={(q) => void ask(q)} />
    </section>
  );
}
