import { useEffect, useState } from "react";
import { bannedIn, isHealth } from "../../../lib/copyRules";
import { copies as fetchCopies, type Copy } from "../../../lib/api";
import { compact } from "../../../lib/format";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";
import FeedPreview, { HEAD_REC, PREVIEW_LABEL, TEXT_REC_MIN, type PreviewKind } from "./copy/FeedPreview";
import { targetLine } from "./find/TargetPick";

const TONES = ["친근하게", "깔끔하게", "감성적으로"] as const;
const PICK_GOOD = 3;   // 칩은 1~3개가 알맞다 (많으면 문구가 길고 흐려짐)

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

const OTHER = "그 밖";   // 맨 끝. 묶음 이름은 서버가 상품에 맞게(재질·기능…) 붙이고 브랜드·가게 이름은 거른다
/** 메타 글자 수 기준 (server/engine/copywriter.py와 같게) */
export const HEADLINE_MAX = 40;
export const TEXT_MAX = 150;   // 메타 권장 기본 문구 50~150자 (copy/FeedPreview.tsx 출처 참고)
type Choice = number | "own" | null;

/** 문구 화면에서 한 일을 상품·손님 무리별로 기억 (① 찾기에 갔다 와도 그대로). 패널이 열려 있는 동안만. 사진은 기억하지 않음. */
interface Saved {
  strengths: string; added: string[]; tone: (typeof TONES)[number]; picked: string[];
  rounds: Copy[][]; sources: string[]; choice: Choice; draft: { headline: string; text: string }; view: PreviewKind;
}
const MEMO = new Map<string, Saved>();
export function forgetCopyWork(): void { MEMO.clear(); }

/** ② 문구: 좋은 점 고르기 → 문구 3안(피드 모양 미리 보기) → 하나 고르거나 직접 쓰기 → 고쳐서 정하기. */
export default function CopyStep({ state, dispatch }: Props) {
  const memoKey = `${state.product ?? ""}|${state.segment?.intent ?? ""}`;
  const saved = MEMO.get(memoKey);
  const [strengths, setStrengths] = useState(saved?.strengths ?? "");
  const [added, setAdded] = useState<string[]>(saved?.added ?? []);   // 직접 적어 엔터로 붙인 말 (칩)
  const [tone, setTone] = useState<(typeof TONES)[number]>(saved?.tone ?? "친근하게");
  const [toneOpen, setToneOpen] = useState(false);   // 말투는 접어 두고 [바꾸기]로 연다
  const [picked, setPicked] = useState<string[]>(saved?.picked ?? []);
  const [rounds, setRounds] = useState<Copy[][]>(saved?.rounds ?? []);   // 써 달라고 할 때마다 한 묶음씩 쌓는다 (앞 문구도 남겨 비교)
  const [sources, setSources] = useState<string[]>(saved?.sources ?? []);   // 묶음마다 claude | template
  const [view, setView] = useState<PreviewKind>(saved?.view ?? "ig");
  const list: Copy[] | null = rounds.length ? rounds.flat() : null;   // 번호(1안·2안…)는 쓴 순서대로
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [choice, setChoice] = useState<Choice>(saved?.choice ?? null);
  const [draft, setDraft] = useState(saved?.draft ?? { headline: "", text: "" });
  useEffect(() => {
    MEMO.set(memoKey, { strengths, added, tone, picked, rounds, sources, choice, draft, view });
  }, [memoKey, strengths, added, tone, picked, rounds, sources, choice, draft, view]);
  const lastKey = `ad-coach.last-copy.${state.product ?? ""}`;   // 지난번 고른 문구 (이 브라우저에만, 다음 달에 다시 쓰기용)
  const [last] = useState<{ headline: string; primary_text: string; day: string } | null>(() => {
    try { const v = JSON.parse(localStorage.getItem(lastKey) ?? "null"); return v && typeof v.headline === "string" ? v : null; }
    catch { return null; }
  });
  const [photo, setPhoto] = useState<string | null>(null);   // 미리 보기에만 쓰는 내 사진 (패널 안에서만, 올리지 않음)
  useEffect(() => () => { if (photo) URL.revokeObjectURL(photo); }, [photo]);
  const shop = (state.answers?.["meta.pre.ig_account"] ?? "").replace(/^@/, "").trim() || "내 가게";

  function choose(c: Choice) {
    setChoice(c);
    const from = typeof c === "number" ? list?.[c] : undefined;
    setDraft(from ? { headline: from.headline, text: from.primary_text } : { headline: "", text: "" });
  }
  const headOk = draft.headline.trim().length > 0 && draft.headline.length <= HEADLINE_MAX;
  const textOk = draft.text.trim().length > 0 && draft.text.length <= TEXT_MAX;
  const banned = bannedIn(`${draft.headline} ${draft.text}`);
  function confirm() {
    const from = typeof choice === "number" ? list?.[choice] : undefined;
    const same = !!from && from.headline === draft.headline && from.primary_text === draft.text;
    const copy = same ? from! : { headline: draft.headline.trim(), primary_text: draft.text.trim() };   // 고쳤으면 근거 줄은 뺀다
    try {
      const d = new Date();
      localStorage.setItem(lastKey, JSON.stringify({ headline: copy.headline, primary_text: copy.primary_text, day: `${d.getMonth() + 1}/${d.getDate()}` }));
    } catch { /* 저장이 막혀도 그대로 진행 */ }
    dispatch({ type: "pickCopy", copy, ...(all.length ? { strengths: all } : {}) });   // 칩이 없어도 직접 적은 좋은 점은 넘긴다
  }

  const mods = state.research?.modifiers ?? [];
  const hasMods = mods.length > 0;
  const seg = state.segment;
  const peak = seg?.trend?.seasonal ? seg.trend.peak_month : null;   // 시즌일 때만 "N월에 많음"
  const others = mods.filter((m) => m.group === OTHER);
  const groups = [...new Set(mods.map((m) => m.group))].filter((g) => g !== OTHER);   // 많이 찾는 순(서버 순서)대로 처음 나온 묶음부터
  const typed = strengths.split(/[,\n]/).map((x) => x.trim()).filter(Boolean);   // 아직 엔터를 안 친 말도 넣는다
  const all = [...new Set([...picked, ...added, ...typed])];
  function addTyped() {
    if (!typed.length) return;
    setAdded((a) => [...new Set([...a, ...typed])]);
    setStrengths("");
  }
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
            <span>{on ? "✓ " : ""}{m.word}{isHealth(m.word) && <span aria-label="효능 표현 주의" className="ml-0.5 text-warn">▲</span>}</span>
            <span className="text-small text-soft">{compact(m.total_qc)}번</span>
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
        tone,
      });
      setRounds((rs) => [...rs, r.copies]);   // 뒤에 붙이니 이미 고른 문구 번호는 그대로
      setSources((ss) => [...ss, r.source]);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  /** 문구 한 장: 라디오 + 피드 미리 보기 + 근거, 고르면 고쳐 쓰기 칸. */
  function card(c: Copy, i: number) {
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
        {on
          ? <Preview name={shop} draft={draft} photo={photo} setPhoto={setPhoto} view={view} setView={setView} />
          : <p className="line-clamp-2 text-caption text-soft">{c.primary_text}</p>}
        {c.basis && c.basis.length > 0 && <p className="text-caption text-soft">이 문구에 쓴 말: {c.basis.join(" · ")}</p>}
        {on && <Editor draft={draft} setDraft={setDraft} banned={banned} product={state.product ?? ""} original={{ headline: c.headline, text: c.primary_text }} />}
      </div>
    );
  }

  return (
    <section className="flex flex-col gap-5">
      <Coach>
        {hasMods
          ? `손님이 '${state.product ?? ""}' 찾을 때 함께 쓰는 말이에요. 사장님 상품에 해당하는 것을 눌러 주세요. 문구에 그대로 넣을게요.`
          : "상품의 좋은 점을 한두 마디로 알려 주세요. 찾은 키워드와 섞어 광고 문구 3개를 써 드릴게요."}
      </Coach>
      {(seg || state.target) && (
        <div className="flex items-start justify-between gap-3 rounded-card border border-line bg-paper px-4 py-3">
          <span className="flex flex-col gap-0.5">
            <span className="text-caption text-soft">이 손님에게 쓰는 문구예요</span>
            {seg && <span className="text-body font-semibold">{seg.label}{peak ? ` · ${peak}월에 많음` : ""}</span>}
            {state.target && <span className="text-caption">{targetLine(state.target)}</span>}
          </span>
          <button type="button" onClick={() => dispatch({ type: "editFind" })}
            className="shrink-0 rounded-button border border-line bg-paper min-h-11 px-3 py-1 text-caption font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">바꾸기</button>
        </div>
      )}
      {hasMods && <p className="-mt-2 text-small text-soft">1~3개 고르면 좋아요. 칩 옆 숫자는 한 달에 그 말로 네이버에서 찾는 횟수예요 (많이 찾는 순서).</p>}
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
          onKeyDown={(e) => { if (e.key === "Enter" && !e.nativeEvent.isComposing) { e.preventDefault(); addTyped(); } }}
          aria-describedby="strengths-help"
          placeholder={hasMods ? "예: 버터 듬뿍 (적고 엔터)" : "예: 버터 듬뿍 (적고 엔터)"}
          className="rounded-button border border-field-line bg-paper px-3 py-2.5 text-body"
        />
        <p id="strengths-help" className="text-caption text-soft">적고 엔터를 누르면 칩으로 붙어요. 쉼표로 여러 개 적어도 돼요.</p>
        {added.length > 0 && (
          <ul aria-label="직접 적은 말" className="flex flex-wrap gap-2">
            {added.map((w) => (
              <li key={w} className="inline-flex items-center gap-1 rounded-badge border border-accent bg-accent-soft px-3 py-1.5 text-caption">
                ✓ {w}
                <button type="button" aria-label={`${w} 빼기`} onClick={() => setAdded((a) => a.filter((x) => x !== w))}
                  className="-my-3 -mr-3 grid size-11 place-items-center rounded-badge text-soft hover:bg-paper focus-visible:outline-2 focus-visible:outline-accent">×</button>
              </li>
            ))}
          </ul>
        )}
        {error && !list && <ErrorLine message={error} onRetry={write} />}
      </div>
      {!list && choice === null && last && (
        <div className="flex flex-col gap-2 rounded-card border border-dashed border-line px-4 py-3">
          <span className="text-caption font-semibold text-soft">지난번 고른 문구 ({last.day})</span>
          <strong className="text-body">{last.headline}</strong>
          <p className="line-clamp-2 text-caption text-soft">{last.primary_text}</p>
          <button type="button" onClick={() => { setChoice("own"); setDraft({ headline: last.headline, text: last.primary_text }); }}
            className="min-h-11 self-start rounded-button border border-accent bg-paper px-3 py-1 text-caption font-semibold text-accent-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
            이 문구로 다시 쓰기
          </button>
        </div>
      )}
      {!list && choice !== "own" && (
        <div className="flex flex-col gap-2">
          {!toneOpen ? (
            <p className="flex items-center gap-2 text-caption">
              <span><span className="text-soft">문구 말투</span> <span className="font-semibold">{tone}</span></span>
              <button type="button" onClick={() => setToneOpen(true)}
                className="min-h-11 rounded-button border border-line bg-paper px-3 py-1 text-caption font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">말투 바꾸기</button>
            </p>
          ) : (
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-caption font-semibold text-soft">문구 말투</legend>
            <div className="flex flex-wrap gap-2">
              {TONES.map((t) => (
                <label key={t} className={`cursor-pointer rounded-badge border px-3 py-1.5 text-label has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${
                  tone === t ? "border-accent bg-accent font-semibold text-on-accent" : "border-line"}`}>
                  <input type="radio" name="tone" value={t} checked={tone === t} onChange={() => { setTone(t); setToneOpen(false); }} className="sr-only" />
                  {t}
                </label>
              ))}
            </div>
          </fieldset>
          )}
          {all.some(isHealth) && (
            <p role="note" className="text-caption text-warn">
              ▲ {all.filter(isHealth).map((w) => `'${w}'`).join(", ")} 같은 효능 말은 '낫는다·좋아진다'고 쓰면 광고 심의에 걸릴 수 있어요. 문구에는 '○○이 고민인 분께'처럼만 쓸게요.
            </p>
          )}
          {all.length > 0 && (
            <p className="text-caption text-soft">
              <span className="text-ink">{all.join(" · ")}</span>{euro(all[all.length - 1]!)}, {tone} 써요 (좋은 점 {all.length}개){all.length > PICK_GOOD ? " · 많이 고르면 문구가 길고 흐려질 수 있어요" : ""}
            </p>
          )}
          <PrimaryButton onClick={write} busy={busy} disabled={blocked}>문구 써 주세요</PrimaryButton>
          {blocked && <p className="text-caption text-warn">▲ 하나 이상 고르거나 적어 주세요</p>}
          <button type="button" onClick={() => choose("own")}
            className="inline-flex min-h-11 items-center self-start text-caption text-soft underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
            문구를 직접 쓸게요
          </button>
        </div>
      )}
      {busy && <WritingSkeleton />}
      {list && (
        <div role="radiogroup" aria-label="광고 문구 고르기" className="flex flex-col gap-3">
          {[...rounds.keys()].reverse().map((ri) => {
            const start = rounds.slice(0, ri).reduce((n, r) => n + r.length, 0);
            const cards = rounds[ri]!.map((c, k) => card(c, start + k));
            const fallback = sources[ri] === "template" && ri === rounds.length - 1 && (
              <p role="status" className="rounded-button bg-warn-bg px-3 py-2 text-caption text-warn">
                ▲ 이번엔 Claude가 문구를 쓰지 못해 기본 문장 틀로 썼어요. [다른 문구로 다시 써 주세요]를 누르면 나아질 수 있어요.
              </p>
            );
            if (rounds.length === 1) return <div key={ri} className="flex flex-col gap-3">{fallback}{cards}</div>;
            const newest = ri === rounds.length - 1;
            const hasChoice = typeof choice === "number" && choice >= start && choice < start + rounds[ri]!.length;
            return newest ? (
              <div key={ri} className="flex flex-col gap-3">
                <span className="text-caption font-semibold text-soft">새로 쓴 문구</span>
                {fallback}
                {cards}
              </div>
            ) : (
              <details key={ri} open={hasChoice} className="group flex flex-col gap-3">
                <summary className="flex cursor-pointer list-none items-center justify-between text-caption font-semibold text-soft [&::-webkit-details-marker]:hidden">
                  <span>앞에서 쓴 문구 ({start + 1}~{start + rounds[ri]!.length}안)</span>
                  <span aria-hidden className="transition-transform group-open:rotate-180">▾</span>
                </summary>
                <div className="mt-3 flex flex-col gap-3">{cards}</div>
              </details>
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
                <Preview name={shop} draft={draft} photo={photo} setPhoto={setPhoto} view={view} setView={setView} />
                <Editor draft={draft} setDraft={setDraft} banned={banned} product={state.product ?? ""} />
              </>
            )}
          </div>
        </div>
      )}
      {!list && choice === "own" && (
        <div className="flex flex-col gap-2 rounded-card border border-accent bg-accent-soft p-3">
          <strong className="text-body">직접 쓰기</strong>
          <Preview name={shop} draft={draft} photo={photo} setPhoto={setPhoto} view={view} setView={setView} />
          <Editor draft={draft} setDraft={setDraft} banned={banned} product={state.product ?? ""} />
          <button type="button" onClick={() => setChoice(null)} className="inline-flex min-h-11 items-center self-start text-caption text-soft underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">← 문구를 써 달라고 할게요</button>
        </div>
      )}
      {choice !== null && (
        <div className="flex flex-col gap-2">
          <PrimaryButton onClick={confirm} disabled={!headOk || !textOk || banned.length > 0}>이 문구로 할게요</PrimaryButton>
          <p className="text-small text-soft">다음: 광고 설정 질문 몇 개에 답하면, 광고 관리자에 넣을 값을 만들어 드려요.</p>
          {(!headOk || !textOk) && <p className="text-caption text-warn">▲ 제목은 1~{HEADLINE_MAX}자, 본문은 1~{TEXT_MAX}자로 적어 주세요</p>}
        </div>
      )}
      {list && (
        <button type="button" onClick={write} disabled={busy || blocked} className="inline-flex min-h-11 items-center self-start text-caption text-soft underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:opacity-(--state-disabled-opacity)">
          {busy ? "다시 쓰는 중…" : "다른 문구로 다시 써 주세요"}
        </button>
      )}
      {list && error && <ErrorLine message={error} onRetry={write} />}
      <p className="text-caption text-soft">사실이 아닌 말(최저가, 1위 등)은 넣지 않아요.</p>
    </section>
  );
}

/** 고른 문구 고치기: 제목·본문 + 글자 수 (메타 기준을 넘으면 경고색). */
/** '로/으로': 받침이 있으면(ㄹ 받침 빼고) '으로' */
function euro(word: string): string {
  const c = word.charCodeAt(word.length - 1) - 0xac00;
  if (c < 0 || c > 11171) return "(으)로";
  const jong = c % 28;
  return jong === 0 || jong === 8 ? "로" : "으로";
}

function Editor({ draft, setDraft, banned, original, product }: {
  draft: { headline: string; text: string }; setDraft: (d: { headline: string; text: string }) => void; banned: string[];
  product: string;
  /** 받은 문구 그대로 (직접 쓰기엔 없음): 고쳤으면 [원래 문구로] */
  original?: { headline: string; text: string };
}) {
  const [copied, setCopied] = useState<"" | "ok" | "fail">("");
  const edited = !!original && (original.headline !== draft.headline || original.text !== draft.text);
  // 상품 이름(또는 그 끝 낱말, 2글자 이상)이 제목·본문 어디에도 없으면 알려 준다 (막지는 않음)
  const flat = `${draft.headline}${draft.text}`.replace(/\s/g, "");
  const names = [product.replace(/\s/g, ""), ...product.split(/\s+/).filter((w) => w.length >= 2)].filter(Boolean);
  const noName = !!product && flat.length > 0 && !names.some((n) => flat.includes(n));
  async function copy() {
    try {
      await navigator.clipboard.writeText(`${draft.headline}\n${draft.text}`);
      setCopied("ok");
    } catch {
      setCopied("fail");
    }
    setTimeout(() => setCopied(""), 2000);
  }
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
      {draft.headline.length > HEAD_REC && draft.headline.length <= HEADLINE_MAX && (
        <p className="text-caption text-soft">메타 권장 제목 길이는 {HEAD_REC}자예요 (지금 {draft.headline.length}자). 줄여도 되면 중요한 말을 앞에 두세요.</p>
      )}
      {draft.text.trim() && draft.text.length < TEXT_REC_MIN && (
        <p className="text-caption text-soft">메타 권장 본문 길이는 {TEXT_REC_MIN}~{TEXT_MAX}자예요 (지금 {draft.text.length}자).</p>
      )}
      {noName && <p className="text-caption text-warn">▲ 문구에 상품 이름('{product}')이 없어요. 무엇을 파는지 알 수 있게 넣어 주세요.</p>}
      <div className="flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => void copy()} disabled={!draft.headline.trim() && !draft.text.trim()}
          className="rounded-button border border-line bg-paper min-h-11 px-3 py-1 text-caption font-semibold disabled:opacity-(--state-disabled-opacity) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          복사
        </button>
        {edited && (
          <button type="button" onClick={() => setDraft(original!)} className="inline-flex min-h-11 items-center text-caption text-soft underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">원래 문구로</button>
        )}
        {copied && <span role="status" className="text-small text-soft">{copied === "ok" ? "제목과 본문을 복사했어요." : "복사하지 못했어요. 직접 골라 복사해 주세요."}</span>}
      </div>
      {banned.length > 0
        ? <p role="alert" className="text-caption text-warn">▲ {banned.map((b) => `'${b}'`).join(", ")} 같은 말은 근거를 댈 수 없는 말이라 광고에 쓸 수 없어요. 빼거나 바꿔 주세요.</p>
        : <p className="text-small text-soft">사실이 아닌 말(최저가, 1위 등)은 쓰지 마세요.</p>}
    </div>
  );
}

/** 문구를 쓰는 동안(5초쯤): 문구 카드 3장 모양의 빈 틀. */
function WritingSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      <p role="status" className="text-caption text-soft">문구 3개를 쓰는 중이에요. 5초쯤 걸려요…</p>
      <div aria-hidden className="skeleton flex flex-col gap-3">
        {[0, 1, 2].map((k) => (
          <div key={k} className="flex flex-col gap-2 rounded-card border border-line bg-paper p-3">
            <div className="h-4 w-40 rounded-button bg-sunk" />
            <div className="h-24 w-full rounded-button bg-sunk" />
            <div className="h-3 w-full rounded-button bg-sunk" />
            <div className="h-3 w-3/4 rounded-button bg-sunk" />
          </div>
        ))}
      </div>
    </div>
  );
}

/** 고른 문구의 피드 미리 보기 + 내 사진 넣어 보기 (사진은 이 패널에서만 보이고 어디에도 올리지 않음). */
function Preview({ name, draft, photo, setPhoto, view, setView }: {
  name: string; draft: { headline: string; text: string }; photo: string | null; setPhoto: (u: string | null) => void;
  view: PreviewKind; setView: (v: PreviewKind) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div role="radiogroup" aria-label="미리 보기 자리" className="flex flex-wrap gap-1.5">
        {(Object.keys(PREVIEW_LABEL) as PreviewKind[]).map((k) => (
          <label key={k} className={`cursor-pointer inline-flex min-h-11 items-center rounded-badge border px-3 py-1 text-caption has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${
            view === k ? "border-accent bg-accent font-semibold text-on-accent" : "border-line bg-paper"}`}>
            <input type="radio" name="preview-kind" checked={view === k} onChange={() => setView(k)} className="sr-only" />
            {PREVIEW_LABEL[k]}
          </label>
        ))}
      </div>
      {view !== "fb" && <p className="text-caption text-soft">{view === "ig" ? "인스타 피드는 제목 40자, 본문 125자가 권장돼요 (메타 광고 가이드)." : "스토리에서는 제목이 안 보이고 본문도 한 줄만 보여요."}</p>}
      <FeedPreview name={name} headline={draft.headline} text={draft.text} photo={photo} kind={view} />
      <div className="flex items-center justify-between gap-2">
        <label className="inline-flex min-h-11 cursor-pointer items-center text-caption font-semibold text-accent-ink underline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent">
          {photo ? "사진 바꾸기" : "내 상품 사진 넣어 보기"}
          <input type="file" accept="image/*" className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) setPhoto(URL.createObjectURL(f)); }} />
        </label>
        <span className="text-small text-soft">미리 보기에만 써요 (올리지 않아요)</span>
      </div>
    </div>
  );
}
