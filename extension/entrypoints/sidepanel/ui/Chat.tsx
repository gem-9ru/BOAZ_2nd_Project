import { useEffect, useRef, useState } from "react";
import { askAssistant } from "../../../lib/api";

interface Bubble { from: "assistant" | "me"; text: string }

/** 광고 어시스턴트 말풍선 (EX-03): 첫 말 + 추천 질문 2개, 질문하면 분석 결과(테스트안 JSON)로만 설명한다.
 *  말 규칙은 분석 페이지와 같다 (서버 assistant.SYSTEM, v4.2 AN-TXT): 판정 3단어 · JSON 숫자만 · 사장님 말 먼저. */
export function Chat({ code, step }: { code: string; step: string }) {
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    askAssistant(code, step).then((o) => {
      setBubbles([{ from: "assistant", text: o.message }]);
      setSuggestions(o.suggestions ?? []);
    }, () => setBubbles([{ from: "assistant", text: "지금은 어시스턴트에 연결하지 못했어요. 바꿀 칸 안내는 그대로 쓸 수 있어요." }]));
  }, [code, step]);

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
    <section aria-label="광고 어시스턴트" className="flex flex-col gap-2 rounded-card bg-accent-soft p-3">
      <div className="flex flex-col gap-2" aria-live="polite">
        {bubbles.map((b, i) => (
          <p key={i} className={b.from === "me" ? "self-end max-w-[85%] rounded-button bg-accent px-3 py-2 text-caption text-on-accent" : "max-w-[95%] rounded-button bg-paper px-3 py-2 text-caption"}>{b.text}</p>
        ))}
        {busy && <p role="status" className="text-caption text-soft">생각하는 중…</p>}
      </div>
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {suggestions.map((s) => (
            <button key={s} type="button" onClick={() => void ask(s)} className="rounded-badge border border-accent bg-paper px-2.5 py-1 text-caption text-accent-ink">{s}</button>
          ))}
        </div>
      )}
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); void ask(text); }}>
        <label htmlFor="ex-ask" className="sr-only">어시스턴트에게 묻기</label>
        <input id="ex-ask" value={text} onChange={(e) => setText(e.target.value)} placeholder="궁금한 걸 물어보세요 (예: CPM이 뭐예요?)"
          className="min-w-0 flex-1 rounded-button border border-field-line bg-paper px-3 py-2 text-caption" />
        <button type="submit" disabled={!text.trim() || busy} className="rounded-button bg-accent px-3 text-caption font-semibold text-on-accent disabled:opacity-(--state-disabled-opacity)">묻기</button>
      </form>
    </section>
  );
}
