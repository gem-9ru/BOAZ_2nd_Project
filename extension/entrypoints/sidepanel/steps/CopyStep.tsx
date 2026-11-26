import { useState } from "react";
import { copies as fetchCopies, type Copy } from "../../../lib/api";
import { compact } from "../../../lib/format";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";
import FeedPreview from "./copy/FeedPreview";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

const OTHER = "그 밖";   // 맨 끝. 묶음 이름은 서버가 상품에 맞게(재질·기능…) 붙이고 브랜드·가게 이름은 거른다
/** 메타 글자 수 기준 (server/engine/copywriter.py와 같게) */
export const HEADLINE_MAX = 40;
export const TEXT_MAX = 125;
type Choice = number | "own" | null;

/** ② 문구: 좋은 점 고르기 → 문구 3안(피드 모양 미리 보기) → 하나 고르거나 직접 쓰기 → 고쳐서 정하기. */
export default function CopyStep({ state, dispatch }: Props) {
  const [strengths, setStrengths] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [list, setList] = useState<Copy[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [choice, setChoice] = useState<Choice>(null);
  const [draft, setDraft] = useState({ headline: "", text: "" });
  const shop = (state.answers?.["meta.pre.ig_account"] ?? "").replace(/^@/, "").trim() || "내 가게";

  function choose(c: Choice) {
    setChoice(c);
    const from = typeof c === "number" ? list?.[c] : undefined;
    setDraft(from ? { headline: from.headline, text: from.primary_text } : { headline: "", text: "" });
  }
  const headOk = draft.headline.trim().length > 0 && draft.headline.length <= HEADLINE_MAX;
  const textOk = draft.text.trim().length > 0 && draft.text.length <= TEXT_MAX;
  function confirm() {
    const from = typeof choice === "number" ? list?.[choice] : undefined;
    const same = !!from && from.headline === draft.headline && from.primary_text === draft.text;
    const copy = same ? from! : { headline: draft.headline.trim(), primary_text: draft.text.trim() };   // 고쳤으면 근거 줄은 뺀다
    dispatch({ type: "pickCopy", copy, ...(hasMods && all.length ? { strengths: all } : {}) });
  }

  const mods = state.research?.modifiers ?? [];
  const hasMods = mods.length > 0;
  const seg = state.segment;
  const peak = seg?.trend?.seasonal ? seg.trend.peak_month : null;   // 시즌일 때만 "N월에 많음"
  const others = mods.filter((m) => m.group === OTHER);
  const groups = [...new Set(mods.map((m) => m.group))].filter((g) => g !== OTHER);   // 많이 찾는 순(서버 순서)대로 처음 나온 묶음부터
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
      setChoice(null);
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
      {hasMods && groups.map((g) => {
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
      {!list && choice !== "own" && (
        <div className="flex flex-col gap-2">
          <PrimaryButton onClick={write} busy={busy} disabled={blocked}>문구 써 주세요</PrimaryButton>
          {blocked && <p className="text-small text-soft">▲ 하나 이상 고르거나 적어 주세요</p>}
          <button type="button" onClick={() => choose("own")}
            className="self-start text-caption text-soft underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
            문구를 직접 쓸게요
          </button>
        </div>
      )}
      {list && (
        <div role="radiogroup" aria-label="광고 문구 고르기" className="flex flex-col gap-3">
          {list.map((c, i) => {
            const on = choice === i;
            return (
              <div key={i} className={`flex flex-col gap-2 rounded-card border p-3 transition-colors ${on ? "border-accent bg-accent-soft" : "border-line bg-paper"}`}>
                <label className="flex cursor-pointer items-center gap-2 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-4 has-[:focus-visible]:outline-accent">
                  <input type="radio" name="copy" checked={on} onChange={() => choose(i)} className="sr-only" aria-label={`${i + 1}안: ${c.headline}`} />
                  <span aria-hidden className={`grid size-4 shrink-0 place-items-center rounded-badge border ${on ? "border-accent bg-accent" : "border-line"}`}>
                    {on && <i className="block size-1.5 rounded-badge bg-on-accent" />}
                  </span>
                  <strong className="text-body">{i + 1}안 · {c.headline}</strong>
                </label>
                <FeedPreview name={shop} headline={on ? draft.headline : c.headline} text={on ? draft.text : c.primary_text} />
                {!on && <p className="text-caption text-soft">{c.primary_text}</p>}
                {c.basis && c.basis.length > 0 && <p className="text-small text-soft">근거: {c.basis.join(" · ")}</p>}
                {on && <Editor draft={draft} setDraft={setDraft} />}
              </div>
            );
          })}
          <div className={`flex flex-col gap-2 rounded-card border p-3 ${choice === "own" ? "border-accent bg-accent-soft" : "border-dashed border-line bg-paper"}`}>
            <label className="flex cursor-pointer items-center gap-2 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-4 has-[:focus-visible]:outline-accent">
              <input type="radio" name="copy" checked={choice === "own"} onChange={() => choose("own")} className="sr-only" aria-label="직접 쓰기" />
              <span aria-hidden className={`grid size-4 shrink-0 place-items-center rounded-badge border ${choice === "own" ? "border-accent bg-accent" : "border-line"}`}>
                {choice === "own" && <i className="block size-1.5 rounded-badge bg-on-accent" />}
              </span>
              <strong className="text-body">직접 쓰기</strong>
            </label>
            {choice === "own" && (
              <>
                <FeedPreview name={shop} headline={draft.headline} text={draft.text} />
                <Editor draft={draft} setDraft={setDraft} />
              </>
            )}
          </div>
        </div>
      )}
      {!list && choice === "own" && (
        <div className="flex flex-col gap-2 rounded-card border border-accent bg-accent-soft p-3">
          <strong className="text-body">직접 쓰기</strong>
          <FeedPreview name={shop} headline={draft.headline} text={draft.text} />
          <Editor draft={draft} setDraft={setDraft} />
          <button type="button" onClick={() => setChoice(null)} className="self-start text-caption text-soft underline">← 문구를 써 달라고 할게요</button>
        </div>
      )}
      {choice !== null && (
        <div className="flex flex-col gap-2">
          <PrimaryButton onClick={confirm} disabled={!headOk || !textOk}>이 문구로 할게요</PrimaryButton>
          {(!headOk || !textOk) && <p className="text-small text-soft">▲ 제목은 1~{HEADLINE_MAX}자, 본문은 1~{TEXT_MAX}자로 적어 주세요</p>}
        </div>
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

/** 고른 문구 고치기: 제목·본문 + 글자 수 (메타 기준을 넘으면 경고색). */
function Editor({ draft, setDraft }: { draft: { headline: string; text: string }; setDraft: (d: { headline: string; text: string }) => void }) {
  const count = (n: number, max: number) => (
    <span className={`text-small tabular-nums ${n > max ? "font-semibold text-warn" : "text-soft"}`}>{n}/{max}자</span>
  );
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor="copy-headline" className="text-caption text-soft">제목 (고쳐도 돼요)</label>
        {count(draft.headline.length, HEADLINE_MAX)}
      </div>
      <input id="copy-headline" value={draft.headline} onChange={(e) => setDraft({ ...draft, headline: e.target.value })}
        aria-invalid={draft.headline.length > HEADLINE_MAX || undefined}
        className="rounded-button border border-field-line bg-paper px-3 py-2 text-body" />
      <div className="flex items-baseline justify-between gap-2">
        <label htmlFor="copy-text" className="text-caption text-soft">본문 (고쳐도 돼요)</label>
        {count(draft.text.length, TEXT_MAX)}
      </div>
      <textarea id="copy-text" rows={4} value={draft.text} onChange={(e) => setDraft({ ...draft, text: e.target.value })}
        aria-invalid={draft.text.length > TEXT_MAX || undefined}
        className="rounded-button border border-field-line bg-paper px-3 py-2 text-body" />
      <p className="text-small text-soft">사실이 아닌 말(최저가, 1위 등)은 쓰지 마세요.</p>
    </div>
  );
}
