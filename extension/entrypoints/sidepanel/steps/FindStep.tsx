import { useEffect, useRef, useState } from "react";
import { research as fetchResearch, type Research, type Segment } from "../../../lib/api";
import type { FlowEvent, FlowState, Target } from "../../../lib/flow";
import { compact, onlyLastWord, times } from "../../../lib/format";
import { ageGroupToRange, ageSpan, genderFrom } from "../../../lib/settings";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";
import AgeFigure from "./find/AgeFigure";
import CategoryPick, { CategoryAsk } from "./find/CategoryPick";
import ProductStats from "./find/ProductStats";
import SegmentCards from "./find/SegmentCards";
import TargetPick, { targetLine, toTarget } from "./find/TargetPick";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

const EXAMPLE = "수제 쿠키";
const RECENT_KEY = "ad-coach.recent-products";   // 최근 찾은 상품 (이 브라우저에만, 편의용)

function readRecent(): string[] {
  try { return JSON.parse(localStorage.getItem(RECENT_KEY) ?? "[]").filter((x: unknown) => typeof x === "string").slice(0, 5); }
  catch { return []; }
}
function saveRecent(word: string): string[] {
  const next = [word, ...readRecent().filter((x) => x !== word)].slice(0, 5);
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(next)); } catch { /* 저장이 막혀도 화면은 그대로 */ }
  return next;
}

/** ① 찾기: 상품 → 네이버로 누가·어떤 말로 찾는지 → 타겟 확인. */
export default function FindStep({ state, dispatch }: Props) {
  const [product, setProduct] = useState(state.product ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const r = state.research;
  const stale = !!r && !!state.product && product.trim() !== "" && product.trim() !== state.product;

  const retry = useRef<() => void>(() => {});

  async function run(go: () => Promise<void>, again: () => void) {
    retry.current = again;
    setBusy(true);
    setError(null);
    try {
      await go();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const [recent, setRecent] = useState<string[]>(readRecent);

  function search(word = product) {
    const q = word.trim();
    if (!q) return;
    void run(async () => {
      dispatch({ type: "researched", research: await fetchResearch(q), product: q });
      setRecent(saveRecent(q));
    }, () => search(q));
  }
  const tryWord = (w: string) => { setProduct(w); search(w); };

  // 다시 시도는 누른 그때의 상태(사장님이 그 사이 켜고 끈 말)를 읽어야 해서 ref로 둔다.
  const latest = useRef(state);
  latest.current = state;

  /** 같은 상품을 다시 찾기(분야 바꾸기·이 말로 다시 찾기): 켜 둔 말만 보내고, 사장님이 뺀 말은 그대로 둔다.
   *  category를 주면(분야 바꾸기) 성공한 뒤에만 pickCategory를 보낸다: 실패하면 지금 분야·고른 무리를 그대로 둔다. */
  function rerun(pick?: string) {
    const s = latest.current;
    const p = s.product;
    const cur = s.research;
    if (!p || !cur) return;
    const dropped = s.dropped ?? [];
    const kept = cur.keywords.map((k) => k.keyword).filter((k) => !dropped.includes(k));
    void run(async () => {
      const next = await fetchResearch(p, { category: pick ?? s.category, keywords: kept });
      if (pick) dispatch({ type: "pickCategory", category: pick });
      dispatch({ type: "researched", research: next, product: p, dropped });
    }, () => rerun(pick));
  }

  function pickCategory(code: string) {
    if (code === r?.category?.code) return;
    rerun(code);
  }

  return (
    <section className="flex flex-col gap-5">
      <Coach>어떤 상품을 파세요? 네이버에서 손님이 어떤 말로, 언제 찾고, 누가 쇼핑에서 클릭하는지 알아볼게요.</Coach>
      <div className="flex flex-col gap-2">
        <label htmlFor="product" className="text-caption font-semibold text-soft">파는 상품</label>
        <form
          className="flex items-center gap-1 rounded-card border border-field-line bg-paper p-1.5 transition-colors focus-within:border-ink has-[input:focus-visible]:outline-2 has-[input:focus-visible]:outline-offset-2 has-[input:focus-visible]:outline-accent"
          onSubmit={(e) => {
            e.preventDefault();
            if (!busy) search();
          }}
        >
          <input
            id="product"
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            placeholder="예: 수제 쿠키"
            autoComplete="off"
            className="min-w-0 flex-1 bg-transparent px-2.5 py-2 text-body placeholder:text-soft focus:outline-none"
          />
          <button
            type="submit"
            disabled={!product.trim() || busy}
            className="shrink-0 rounded-button bg-accent px-4 py-2 text-label font-semibold text-on-accent transition-colors hover:bg-accent-ink disabled:opacity-(--state-disabled-opacity) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
          >
            {busy ? "찾는 중…" : "찾아보기"}
          </button>
        </form>
        {error && <ErrorLine message={error} onRetry={() => retry.current()} />}
        {!r && !busy && !error && (
          <button
            type="button"
            onClick={() => { setProduct(EXAMPLE); search(EXAMPLE); }}
            className="self-start rounded-badge bg-accent-soft px-3 py-1.5 text-caption font-semibold text-accent-ink hover:ring-1 hover:ring-accent focus-visible:outline-2 focus-visible:outline-accent"
          >
            {EXAMPLE}로 먼저 보기
          </button>
        )}
        {!busy && recent.filter((w) => w !== product.trim()).length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-small text-soft">최근에 찾은 상품</span>
            {recent.filter((w) => w !== product.trim()).slice(0, 3).map((w) => (
              <button key={w} type="button" onClick={() => tryWord(w)}
                className="min-h-11 rounded-badge border border-line bg-paper px-3 py-1 text-caption focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
                {w}
              </button>
            ))}
          </div>
        )}
      </div>

      {!r && !busy && !error && (
        <div className="flex flex-col gap-2 rounded-card border border-dashed border-line px-4 py-3">
          <span className="text-caption font-semibold text-soft">찾아보면 이렇게 알려 드려요</span>
          <ul className="flex flex-col gap-1 text-caption text-soft">
            <li>· 한 달에 몇 번 찾는지</li>
            <li>· 누가 쇼핑에서 클릭하는지 (나이·성별)</li>
            <li>· 언제 많이 찾는지 (달별)</li>
            <li>· 손님이 어떤 말로 찾는지, 어떤 손님 무리가 있는지</li>
          </ul>
          <span className="text-small text-soft">네이버 검색광고·데이터랩 자료로 보여 드려요.</span>
        </div>
      )}
      {busy && <ResultSkeleton />}
      {!busy && stale && (
        <p className="rounded-button bg-sunk px-3 py-2 text-caption text-soft">
          아래는 '{state.product}' 결과예요. 찾아보기를 누르면 새 상품으로 바뀌어요.
        </p>
      )}
      {!busy && r && (
        <div className={stale ? "opacity-50 transition-opacity" : "transition-opacity"}>
          {r.notice
            ? <NoData notice={r.notice} product={state.product ?? product.trim()} dispatch={dispatch}
                suggestions={r.suggestions} onTry={tryWord} />
            : Array.isArray(r.segments)
              ? <SegmentResult research={r} segments={r.segments} state={state} dispatch={dispatch}
                  onPickCategory={pickCategory} onResearch={() => rerun()} onTry={tryWord} />
              : <Result research={r} dropped={state.dropped ?? []} dispatch={dispatch} />}
        </div>
      )}
    </section>
  );
}

/** 결과 자리 스켈레톤: 결과 카드와 같은 모양. */
const SEARCH_STEPS = ["네이버에서 검색 수를 보는 중이에요…", "누가 클릭하는지 보는 중이에요…", "손님을 무리로 나누는 중이에요…", "좋은 점 낱말을 고르는 중이에요…"];

function ResultSkeleton() {
  // 실제 진행을 받지 않으니 시간으로만 넘긴다 (마지막 단계에서 멈춤)
  const [stepAt, setStepAt] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setStepAt((i) => Math.min(i + 1, SEARCH_STEPS.length - 1)), 1200);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="flex flex-col gap-4 rounded-card border border-line bg-paper p-4">
      <p role="status" className="text-caption text-soft">{SEARCH_STEPS[stepAt]}</p>
      <div aria-hidden className="skeleton flex flex-col gap-4">
        <div className="h-7 w-32 rounded-button bg-sunk" />
        <div className="flex h-24 items-end gap-2">
          {[30, 70, 90, 55, 35, 20].map((h, i) => (
            <div key={i} className="flex-1 rounded-t-md bg-sunk" style={{ height: `${h}%` }} />
          ))}
        </div>
        <div className="flex gap-2">
          {[72, 56, 88].map((w) => <div key={w} className="h-7 rounded-badge bg-sunk" style={{ width: w }} />)}
        </div>
      </div>
    </div>
  );
}

/** 2) 부르는 말: 켜고 끄는 칩. */
function KeywordChips({ research: r, dropped, kept, title, hint, dispatch, product = "" }: {
  research: Research; dropped: string[]; kept: string[]; title: string; hint: string; product?: string;
  dispatch: (ev: FlowEvent) => void;
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-caption font-semibold text-soft">{title}</span>
        <span className="text-small text-soft">{r.keywords.length}개 중 {kept.length}개 넣음</span>
      </div>
      <p className="-mt-1 text-small text-soft">{hint}</p>
      <div className="flex flex-wrap gap-2">
        {r.keywords.map((k) => {
          const off = dropped.includes(k.keyword);
          return (
            <button
              key={k.keyword}
              type="button"
              aria-pressed={!off}
              onClick={() => dispatch({ type: "toggleKeyword", keyword: k.keyword })}
              className={`inline-flex items-center gap-1.5 rounded-badge border px-3 py-1.5 text-caption transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent ${
                off ? "border-dashed border-line text-soft" : "border-accent bg-accent-soft text-ink"}`}
            >
              <span aria-hidden className={`grid size-4 place-items-center rounded-badge text-mark ${off ? "border border-line" : "bg-accent text-on-accent"}`}>
                {off ? "" : "✓"}
              </span>
              <span className={off ? "line-through" : "font-medium"}>{k.keyword}</span>
              <span className="text-small text-soft tabular-nums">한 달 {times(k.total_qc, k.under)}</span>
              {onlyLastWord(product, k.keyword) && (
                <span className="rounded-badge border border-line bg-paper px-1.5 text-small text-soft">'{onlyLastWord(product, k.keyword)}'만 같아요</span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function Negatives({ words }: { words?: string[] }) {
  if (!words || words.length === 0) return null;
  return (
    <details className="group rounded-button border border-line px-3 py-2.5 text-caption text-soft open:bg-paper">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 font-semibold [&::-webkit-details-marker]:hidden">
        <span>광고에서 뺄 말 {words.length}개 <span className="font-normal">(만들기·매장·관련 낮은 말)</span></span>
        <span aria-hidden className="transition-transform group-open:rotate-180">▾</span>
      </summary>
      <p className="mt-2">만들기·매장 찾기처럼 사려는 뜻과 다르거나 상품과 관련이 낮은 말이라, 문구에 넣지 않아요 (이 도구 기준).</p>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {words.map((w) => <li key={w} className="rounded-badge bg-sunk px-2 py-0.5 line-through decoration-soft">{w}</li>)}
      </ul>
    </details>
  );
}

function SourceLine({ research: r }: { research: Research }) {
  const day = r.sources?.find((x) => x.part === "product")?.fetched ?? r.fetched;
  const detail = r.sources?.length
    ? `네이버 검색광고·데이터랩 — ${r.sources.map((x) => `${x.label} ${x.today ? "오늘 조회" : `${dayLabel(x.fetched)} 저장본`}`).join(" · ")}`
    : `네이버 검색광고 · 데이터랩 · 조회일 ${r.fetched}${r.source === "cache" ? " (저장된 자료)" : ""}`;
  return (
    <details className="text-small leading-relaxed text-soft">
      <summary className="cursor-pointer list-none [&::-webkit-details-marker]:hidden">
        네이버 자료{day ? ` · ${dayLabel(day)} 기준` : ""} <span aria-hidden>🔎</span>
      </summary>
      <p className="mt-1">출처: {detail}</p>
    </details>
  );
}

/** 예전 저장본(segments 없음): 지금까지의 화면 그대로. */
function Result({ research: r, dropped, dispatch }: {
  research: Research;
  dropped: string[];
  dispatch: (ev: FlowEvent) => void;
}) {
  const aud = r.audience;
  const gender = aud ? genderFrom(aud.female) : "all";
  const top = aud?.top_age ?? "30";
  const kept = r.keywords.map((k) => k.keyword).filter((k) => !dropped.includes(k));

  function confirm() {
    const { ageMin, ageMax } = aud ? ageSpan(aud.ages) : ageGroupToRange(top);
    dispatch({ type: "confirmTarget", target: { ageMin, ageMax, gender }, keywords: kept });
  }

  return (
    <div className="flex flex-col gap-5">
      {aud && <AgeFigure audience={aud} headline={r.headline} />}
      <KeywordChips research={r} dropped={dropped} kept={kept} dispatch={dispatch}
        title="이 사람들이 쓰는 말" hint="빼고 싶은 말은 누르세요. 다시 누르면 돌아와요." />
      <Negatives words={r.negatives} />
      <div className="flex flex-col gap-2">
        {kept.length === 0 && <p className="text-caption text-warn">▲ 검색어를 하나 이상 남겨 주세요.</p>}
        <PrimaryButton onClick={confirm} disabled={kept.length === 0}>이 사람들로 할게요</PrimaryButton>
        <SourceLine research={r} />
      </div>
    </div>
  );
}

/** 새 ① 흐름: 1) 분야 → 2) 부르는 말 → 3) 손님 무리 → [이 손님들로 할게요]. */
function SegmentResult({ research: r, segments, state, dispatch, onPickCategory, onResearch, onTry }: {
  research: Research;
  segments: Segment[];
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
  onPickCategory: (code: string) => void;
  onResearch: () => void;
  onTry: (word: string) => void;
}) {
  const dropped = state.dropped ?? [];
  const kept = r.keywords.map((k) => k.keyword).filter((k) => !dropped.includes(k));
  const topWord = [...r.keywords].sort((x, y) => y.total_qc - x.total_qc)[0];
  const selected = segments.find((s) => s.intent === state.segment?.intent);
  const [age, setAge] = useState("");
  const [gender, setGender] = useState<"" | "all" | "female" | "male">("");
  const product = state.product ?? "";
  // 추천 타깃(많이 찾는 나이대 + 성별)과 사장님이 고친 값. 무리를 바꾸면 추천으로 돌아간다.
  const rec = selected?.audience
    ? (() => { const g = ageSpan(selected.audience.ages).groups; return { from: g[0]!, to: g[g.length - 1]!, gender: genderFrom(selected.audience.female) }; })()
    : null;
  // ②에 갔다 돌아왔을 때: 지난번에 정한 타깃이 추천과 다르면 그 값을 고친 값으로 다시 쓴다
  const [custom, setCustom] = useState<{ intent: string; from: string; to: string; gender: "all" | "female" | "male" } | null>(() => {
    const t = state.target;
    if (!t || !selected || !rec || state.segment?.intent !== selected.intent) return null;
    const g = (age: number) => String(Math.min(60, Math.max(10, Math.floor(age / 10) * 10)));
    const back = { from: g(t.ageMin), to: g(t.ageMax), gender: t.gender };
    return back.from === rec.from && back.to === rec.to && back.gender === rec.gender ? null : { intent: selected.intent, ...back };
  });
  const pick = rec ? (custom && custom.intent === selected?.intent ? custom : rec) : null;

  // 무리가 하나뿐이면 미리 골라 둔다 (이 결과마다 한 번)
  const preselected = useRef<Research | null>(null);
  useEffect(() => {
    if (segments.length === 1 && !selected && preselected.current !== r) {
      preselected.current = r;
      dispatch({ type: "pickSegment", segment: segments[0]! });
    }
  }, [r, segments, selected, dispatch]);

  const manual = !!selected && !selected.audience;
  const manualMissing = manual && (!age || !gender);
  const ready = !!selected && kept.length > 0 && !manualMissing;

  // 검색어 칩: 손님 무리 아래에 접어 둔다 (무리가 없을 때·뺀 말이 있을 때는 펼침)
  const words = (
    <details open={dropped.length > 0 || !r.category || segments.length === 0}
      className="group flex flex-col gap-3 rounded-card border border-line bg-paper p-4">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-2 [&::-webkit-details-marker]:hidden">
        <span className="flex flex-col gap-0.5">
          <span className="text-caption font-semibold text-soft">문구에 넣을 검색어</span>
          <span className="text-body">검색어 {kept.length}개를 넣어요{dropped.length ? ` (${dropped.length}개 뺌)` : ""}</span>
        </span>
        <span className="shrink-0 text-caption font-semibold text-soft">
          <span className="group-open:hidden">살펴보기 ▾</span><span className="hidden group-open:inline">접기 ▴</span>
        </span>
      </summary>
      <div className="mt-3 flex flex-col gap-4">
        <p className="text-small text-soft">이 말들은 ② 문구를 쓸 때 넣어요. 메타 광고는 검색어로 손님을 고르지 않아서, 손님은 위에서 고른 나이·성별로 정해요.</p>
        <KeywordChips research={r} dropped={dropped} kept={kept} dispatch={dispatch} product={state.product ?? ""}
          title="손님은 이렇게도 불러요" hint="사장님 상품에 맞지 않는 말은 눌러서 빼 주세요." />
        <Negatives words={r.negatives} />
      </div>
    </details>
  );

  const target = pick ? toTarget(pick.from, pick.to, pick.gender)
    : age && gender ? { ...ageGroupToRange(age), gender: gender as "all" | "female" | "male" } : null;

  function confirm() {
    if (!selected || !target) return;
    dispatch({ type: "confirmTarget", target, keywords: kept, segment: selected });
  }

  const detail = selected?.audience && pick && rec
    ? (
      <div className="flex flex-col gap-3">
        <AgeFigure audience={selected.audience} caption="쇼핑에서 많이 클릭한 사람 (추천)" split={r.category ? { keyword: selected.lead, category: r.category.code } : undefined} />
        <TargetPick from={pick.from} to={pick.to} gender={pick.gender} rec={rec} female={selected.audience.female}
          recShare={(() => { const g = ageSpan(selected.audience.ages).groups; return g.reduce((t, a) => t + (selected.audience!.ages[a] ?? 0), 0); })()}
          onChange={(v) => setCustom({ intent: selected.intent, ...v })} />
      </div>
    )
    : (
      <div className="flex flex-col gap-4 rounded-card border border-line bg-paper p-4">
        <Choice legend="보여 줄 나이" name="segment-age"
          options={MANUAL_AGES.map((a) => ({ id: a, label: `${a}대` }))} value={age} onChange={setAge} />
        <Choice legend="성별" name="segment-gender"
          options={MANUAL_GENDERS} value={gender} onChange={(v) => setGender(v as typeof gender)} />
      </div>
    );

  return (
    <div className="flex flex-col gap-5">
      {r.category && (
        <CategoryPick product={product} category={r.category} categories={r.categories} candidates={r.category_candidates} onPick={onPickCategory} />
      )}
      {r.product_stats && <ProductStats stats={r.product_stats} hasCategory={!!r.category} category={r.category?.code} />}
      {topWord && (!r.product_stats || (r.product_stats.total_qc * 10 < topWord.total_qc && topWord.keyword !== r.product_stats.keyword)) && (
        <p className="rounded-card border border-line bg-paper px-4 py-3 text-caption">
          '{product}' 이름 그대로는 {r.product_stats ? ((r.product_stats.under ?? 0) >= 2 ? "한 달 20번도 안 찾아요" : `한 달 ${times(r.product_stats.total_qc, r.product_stats.under)}만 찾아요`) : "찾는 사람이 적어요"}. 손님은 <span className="font-semibold">'{topWord.keyword}'</span>{euro(topWord.keyword)} 가장 많이 찾아요 (한 달 {times(topWord.total_qc, topWord.under)}).
        </p>
      )}
      {!r.category ? (
        <div className="flex flex-col gap-2.5">
          <span className="text-caption font-semibold text-soft">손님 무리</span>
          <p className="text-caption">분야를 골라 주시면 손님을 찾아볼게요</p>
          <CategoryAsk categories={r.categories} candidates={r.category_candidates} onPick={onPickCategory} />
          {words}
        </div>
      ) : segments.length === 0 ? (
        <>
          {words}
          <NoData notice="이 말로 찾는 손님 자료를 찾지 못했어요." product={product} keywords={kept} dispatch={dispatch}
            suggestions={kept.filter((k) => k !== product.replace(/\s/g, "")).slice(0, 3)} onTry={onTry} />
        </>
      ) : (
        <>
          {dropped.length > 0 && !segments.some((g) => dropped.includes(g.lead)) && (
            <div className="flex flex-wrap items-center justify-between gap-2 rounded-button bg-sunk px-3 py-2">
              <span className="text-caption">검색어 {dropped.length}개를 뺐어요. 남긴 말로 손님을 다시 볼 수 있어요.</span>
              <button type="button" onClick={onResearch}
                className="shrink-0 rounded-button border border-accent bg-paper min-h-11 px-3 py-1 text-caption font-semibold text-accent-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
                뺀 말을 빼고 손님 다시 보기
              </button>
            </div>
          )}
          <SegmentCards segments={segments} selected={selected} dropped={dropped} product={product}
            onPick={(segment) => dispatch({ type: "pickSegment", segment })} onResearch={onResearch}
            selectedDetail={detail} />
          {segments.length === 1 && (
            <p className="-mt-2 text-small text-soft">
              {segments[0]!.intent === "상품"
                ? "선물·시즌으로 찾는 말이 적어서, 상품 자체로 찾는 손님 한 무리로 봤어요."
                : "다른 목적으로 찾는 말이 적어서 이 한 무리로 봤어요."}
            </p>
          )}
          {words}
          <div className="flex flex-col gap-2">
            {kept.length === 0 && <p className="text-caption text-warn">▲ 검색어를 하나 이상 남겨 주세요.</p>}
            {!selected && <p className="text-caption text-warn">▲ 광고를 보여 줄 손님을 하나 골라 주세요.</p>}
            {manualMissing && <p className="text-caption text-warn">▲ 보여 줄 나이와 성별을 골라 주세요.</p>}
            {ready && target && (
              <p className="rounded-button bg-sunk px-3 py-2 text-caption">
                광고 관리자에는 <span className="font-semibold">{targetLine(target)}</span>{euro(targetLine(target))} 넣고, 검색어 {kept.length}개는 ② 문구에 써요.
              </p>
            )}
            <PrimaryButton onClick={confirm} disabled={!ready}>이 손님들로 할게요</PrimaryButton>
          </div>
        </>
      )}
      {segments.length > 0 && <CopySummary product={product} research={r} selected={selected} target={target} kept={kept} />}
      <SourceLine research={r} />
    </div>
  );
}

const MANUAL_AGES = ["20", "30", "40", "50", "60"];
const MANUAL_GENDERS: { id: "all" | "female" | "male"; label: string }[] = [
  { id: "all", label: "모두" }, { id: "female", label: "여성" }, { id: "male", label: "남성" },
];

/** 네이버 자료가 없을 때: 다른 말로 다시 찾거나, 사장님이 직접 정하고 넘어간다 (막다른 길을 만들지 않는다). */
function NoData({ notice, product, keywords = [], dispatch, suggestions = [], onTry }: {
  notice: string; product: string; keywords?: string[]; dispatch: (ev: FlowEvent) => void;
  suggestions?: string[]; onTry?: (word: string) => void;
}) {
  const [manual, setManual] = useState(false);
  const [age, setAge] = useState("30");
  const [gender, setGender] = useState<"all" | "female" | "male">("all");

  return (
    <div className="flex flex-col gap-4">
      <Coach>{notice} 아니면 누구에게 보여 줄지 직접 정하고 넘어가도 돼요.</Coach>
      {onTry && suggestions.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-caption font-semibold text-soft">이 말로 다시 찾아볼까요?</span>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((w) => (
              <button key={w} type="button" onClick={() => onTry(w)}
                className="rounded-badge border border-accent bg-paper px-3 py-1.5 text-caption font-semibold text-accent-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
                {w}
              </button>
            ))}
          </div>
        </div>
      )}
      {!manual ? (
        <button type="button" onClick={() => setManual(true)} className="self-start rounded-button border border-accent bg-paper text-accent-ink px-4 py-2 text-label font-semibold focus-visible:outline-2 focus-visible:outline-accent">
          직접 정하고 계속할게요
        </button>
      ) : (
        <div className="flex flex-col gap-4 rounded-card border border-line bg-paper p-4">
          <Choice legend="보여 줄 나이" name="manual-age"
            options={MANUAL_AGES.map((a) => ({ id: a, label: `${a}대` }))} value={age} onChange={setAge} />
          <Choice legend="성별" name="manual-gender"
            options={MANUAL_GENDERS} value={gender} onChange={(v) => setGender(v as typeof gender)} />
          {keywords.length === 0 && (
            <p className="text-caption text-soft">검색어 자료가 없어서 광고 문구에는 '{product}'를 넣을게요.</p>
          )}
          <PrimaryButton onClick={() => dispatch({ type: "confirmTarget", target: { ...ageGroupToRange(age), gender },
            keywords: keywords.length ? keywords : [product] })}>
            이 손님들로 할게요
          </PrimaryButton>
        </div>
      )}
    </div>
  );
}

function Choice({ legend, name, options, value, onChange }: {
  legend: string; name: string; options: { id: string; label: string }[]; value: string; onChange: (v: string) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-caption font-semibold text-soft mb-2">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <label key={o.id}
            className={`rounded-badge border px-3 py-1.5 text-label cursor-pointer has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${value === o.id ? "border-accent bg-accent text-on-accent font-semibold" : "border-line"}`}>
            <input type="radio" name={name} value={o.id} checked={value === o.id} onChange={() => onChange(o.id)} className="sr-only" />
            {o.label}
          </label>
        ))}
      </div>
    </fieldset>
  );
}

/** '2026-11-15' → '11월 15일' */
function dayLabel(iso: string): string {
  const [, m, d] = iso.split("-").map(Number);
  return m && d ? `${m}월 ${d}일` : iso;
}

/** '로/으로': 받침이 있으면(ㄹ 받침 빼고) '으로' */
function euro(word: string): string {
  const c = word.charCodeAt(word.length - 1) - 0xac00;
  if (c < 0 || c > 11171) return "(으)로";
  const jong = c % 28;
  return jong === 0 || jong === 8 ? "로" : "으로";
}

/** [결과 복사]: 찾은 결과를 짧은 글로 (메모·동료에게 보내기용). */
function CopySummary({ product, research: r, selected, target, kept }: {
  product: string; research: Research; selected?: Segment; target: Target | null; kept: string[];
}) {
  const [done, setDone] = useState<"" | "ok" | "fail">("");
  const st = r.product_stats;
  const lines = [
    `상품: ${product}${r.category ? ` (${r.category.name})` : ""}`,
    st ? `한 달에 찾는 횟수: ${st.under ? times(st.total_qc, st.under) : `${st.total_qc.toLocaleString()}번`}` : null,
    st?.trend?.peak_month ? `가장 많이 찾는 달: ${st.trend.peak_month}월` : null,
    selected ? `고른 손님: ${selected.label}${selected.line ? ` — ${selected.line}` : ""}` : null,
    target ? `광고 대상: ${targetLine(target)}` : null,
    kept.length ? `문구에 넣을 검색어: ${kept.join(", ")}` : null,
    `자료: 네이버 검색광고·데이터랩 (${r.fetched || "오늘"})`,
  ].filter(Boolean).join("\n");
  async function copy() {
    try { await navigator.clipboard.writeText(lines); setDone("ok"); } catch { setDone("fail"); }
    setTimeout(() => setDone(""), 2000);
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button type="button" onClick={() => void copy()}
        className="rounded-button border border-line bg-paper min-h-11 px-3 py-1 text-caption font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
        결과 복사
      </button>
      {done && <span role="status" className="text-small text-soft">{done === "ok" ? "찾은 결과를 복사했어요." : "복사하지 못했어요."}</span>}
    </div>
  );
}
