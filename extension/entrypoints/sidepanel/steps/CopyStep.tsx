import { useState } from "react";
import { copies as fetchCopies, type Copy } from "../../../lib/api";
import { compact } from "../../../lib/format";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

const GROUPS = ["포장", "맛·재료", "배송", "양"];
const OTHER = "그 밖";   // 맨 끝. 브랜드·가게 이름은 서버가 Claude로 걸러서 보낸다 (못 거른 것에 대비해 한 줄 안내)

/** ② 문구: 좋은 점 한두 마디 → 문구 3안 → 하나 고르기. */
export default function CopyStep({ state, dispatch }: Props) {
  const [strengths, setStrengths] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [list, setList] = useState<Copy[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mods = state.research?.modifiers ?? [];
  const hasMods = mods.length > 0;
  const seg = state.segment;
  const peak = seg?.trend?.seasonal ? seg.trend.peak_month : null;   // 시즌일 때만 "N월에 많음"
  const others = mods.filter((m) => m.group === OTHER);
  const typed = strengths.split(/[,\n]/).map((x) => x.trim()).filter(Boolean);
  const all = [...picked, ...typed];
  const blocked = hasMods && all.length === 0;
  const toggle = (w: string) => setPicked((p) => (p.includes(w) ? p.filter((x) => x !== w) : [...p, w]));

  const chips = (items: typeof mods) => (
    <div className="flex flex-wrap gap-2">
      {items.map((m) => {
        const on = picked.includes(m.word);
        return (
          <button key={m.word} type="button" aria-pressed={on} onClick={() => toggle(m.word)}
            className={`inline-flex items-center gap-1.5 rounded-badge border px-3 py-1.5 text-caption transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
              on ? "border-accent bg-accent-soft text-ink" : "border-line bg-paper text-soft"}`}>
            <span>{on ? "✓ " : ""}{m.word}</span>
            <span className="text-small text-soft">월 {compact(m.total_qc)}</span>
          </button>
        );
      })}
    </div>
  );

  async function write() {
    setBusy(true);
    setError(null);
    try {
      const r = await fetchCopies({
        product: state.product ?? "", strengths: all, keywords: state.keywords, avoid: state.research?.negatives ?? [],
        ...(seg ? { segment: { intent: seg.intent, label: seg.label, ...(peak ? { peak_month: peak } : {}) } } : {}),
      });
      setList(r.copies);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <Coach>
        {hasMods
          ? `손님이 '${state.product ?? ""}' 찾을 때 함께 쓰는 말이에요. 사장님 상품에 해당하는 것을 눌러 주세요. 문구에 그대로 넣을게요.`
          : "상품의 좋은 점을 한두 마디로 알려 주세요. 찾은 키워드와 섞어 광고 문구 3개를 써 드릴게요."}
      </Coach>
      {seg && (
        <p className="flex flex-wrap items-center gap-1.5 text-caption">
          <span>고른 손님: {seg.label}{peak ? ` · ${peak}월에 많음` : ""}</span>
          <button type="button" onClick={() => dispatch({ type: "editFind" })}
            className="text-caption font-semibold underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">바꾸기</button>
        </p>
      )}
      {hasMods && GROUPS.map((g) => {
        const items = mods.filter((m) => m.group === g);
        if (items.length === 0) return null;
        return (
          <div key={g} className="flex flex-col gap-2">
            <span className="text-caption font-semibold text-soft">{g}</span>
            {chips(items)}
          </div>
        );
      })}
      {hasMods && others.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-caption font-semibold text-soft">{OTHER}</span>
          {chips(others)}
          <p className="text-small text-soft">다른 가게·브랜드 이름이 보이면 고르지 마세요. 문구에 그대로 들어가요.</p>
        </div>
      )}
      <div className="flex flex-col gap-2">
        <label htmlFor="strengths" className="text-caption text-soft">{hasMods ? "직접 적기" : "상품의 좋은 점"}</label>
        <input
          id="strengths"
          value={strengths}
          onChange={(e) => setStrengths(e.target.value)}
          placeholder={hasMods ? "예: 버터 듬뿍" : "예: 버터 듬뿍, 당일 구움"}
          className="rounded-button border border-field-line bg-paper px-3 py-2.5 text-body"
        />
        {error && <ErrorLine message={error} onRetry={write} />}
      </div>
      {!list && <PrimaryButton onClick={write} busy={busy} disabled={blocked}>문구 써 주세요</PrimaryButton>}
      {!list && blocked && <p className="text-small text-soft">▲ 하나 이상 고르거나 적어 주세요</p>}
      {list && (
        <ol className="flex flex-col gap-3">
          {list.map((c, i) => (
            <li key={i} className="border-l-4 border-accent pl-3 flex flex-col gap-1">
              <strong className="text-body">{c.headline}</strong>
              <p className="text-body text-soft">{c.primary_text}</p>
              {c.basis && c.basis.length > 0 && <p className="text-small text-soft">근거: {c.basis.join(" · ")}</p>}
              <button type="button" onClick={() => dispatch({ type: "pickCopy", copy: c, ...(hasMods ? { strengths: all } : {}) })} className="self-start text-caption font-semibold underline">
                이 문구로 할게요 ({i + 1}안)
              </button>
            </li>
          ))}
        </ol>
      )}
      {list && (
        <button type="button" onClick={write} disabled={busy || blocked} className="self-start text-caption text-soft underline disabled:opacity-(--state-disabled-opacity)">
          {busy ? "다시 쓰는 중…" : "다른 문구로 다시 써 주세요"}
        </button>
      )}
      <p className="text-caption text-soft">사실이 아닌 말(최저가, 1위 등)은 넣지 않아요.</p>
    </section>
  );
}
