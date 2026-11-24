import { useEffect, useRef, useState } from "react";
import { askAssistant, type Alert } from "../api";
import { AlertMark } from "../ui";

interface Bubble { from: "assistant" | "me"; text: string; alert?: Alert }

/** 오른쪽 광고 어시스턴트 (폭 320px 고정, 접기 가능). 단계에 들어오면 첫 말풍선 + 추천 질문 2개.
 *  숫자·결론은 코드가 정하고, 어시스턴트는 그 단계 결과로 설명만 한다. 같은 알림은 처음 화면에서만 말풍선으로. */
export function Assistant({ code, step, open, onToggle }: { code: string; step: string; open: boolean; onToggle: () => void }) {
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const seen = useRef(new Set<string>());
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (seen.current.has(step)) return;
    seen.current.add(step);
    askAssistant(code, step).then((o) => {
      setBubbles((b) => [...b, { from: "assistant", text: o.message }, ...(o.alerts ?? []).map((a) => ({ from: "assistant" as const, text: `${a.text} ${a.todo}`, alert: a }))]);
      setSuggestions(o.suggestions ?? []);
    }, () => setBubbles((b) => [...b, { from: "assistant", text: "지금은 어시스턴트에 연결하지 못했어요. 화면의 내용은 그대로 보실 수 있어요." }]));
  }, [code, step]);
  useEffect(() => { end.current?.scrollIntoView?.({ block: "end" }); }, [bubbles]);

  async function ask(q: string) {
    if (!q.trim() || busy) return;
    setBubbles((b) => [...b, { from: "me", text: q }]);
    setText("");
    setBusy(true);
    try {
      const a = await askAssistant(code, step, q);
      setBubbles((b) => [...b, { from: "assistant", text: a.message }]);
    } catch (e) {
      setBubbles((b) => [...b, { from: "assistant", text: (e as Error).message }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside aria-label="광고 어시스턴트" className={`flex flex-col rounded-card border border-card-border bg-accent-soft ${open ? "" : "hidden lg:flex"}`}>
      <header className="flex items-center justify-between border-b border-line px-4 py-3">
        <p className="text-body font-bold"><span aria-hidden="true" className="text-accent">✦</span> 광고 어시스턴트</p>
        <button type="button" onClick={onToggle} className="text-caption text-soft underline">접기</button>
      </header>
      <div className="flex max-h-[60vh] min-h-48 flex-col gap-2 overflow-y-auto px-4 py-3" aria-live="polite">
        {bubbles.map((b, i) => (
          <div key={i} className={b.from === "me" ? "self-end max-w-[85%] rounded-button bg-accent px-3 py-2 text-body text-on-action"
            : b.alert ? "flex gap-2 rounded-button bg-warn-bg px-3 py-2 text-body" : "max-w-[95%] rounded-button bg-surface px-3 py-2 text-body"}>
            {b.alert && <span className="mt-0.5"><AlertMark level={b.alert.level} /></span>}
            <span>{b.text}</span>
          </div>
        ))}
        {busy && <p role="status" className="text-caption text-soft">생각하는 중…</p>}
        <div ref={end} />
      </div>
      <div className="flex flex-wrap gap-2 px-4 pb-2">
        {suggestions.map((s) => (
          <button key={s} type="button" onClick={() => ask(s)} className="rounded-badge border border-accent bg-surface px-3 py-1 text-caption text-accent-ink">{s}</button>
        ))}
      </div>
      <form className="flex gap-2 border-t border-line p-3" onSubmit={(e) => { e.preventDefault(); void ask(text); }}>
        <label htmlFor="ask" className="sr-only">어시스턴트에게 묻기</label>
        <input id="ask" value={text} onChange={(e) => setText(e.target.value)} placeholder="궁금한 걸 물어보세요"
          className="min-w-0 flex-1 rounded-button border border-line bg-surface px-3 py-2 text-body" />
        <button type="submit" disabled={!text.trim() || busy} className="rounded-button bg-button px-3 text-body font-semibold text-button-fg disabled:opacity-(--state-disabled-opacity)">묻기</button>
      </form>
    </aside>
  );
}
