import { useEffect, useRef, useState } from "react";
import { research as fetchResearch, type Research, type Segment } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { compact } from "../../../lib/format";
import { ageGroupToRange, genderFrom } from "../../../lib/settings";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";
import AgeFigure from "./find/AgeFigure";
import CategoryPick, { CategoryAsk } from "./find/CategoryPick";
import ProductStats from "./find/ProductStats";
import SegmentCards from "./find/SegmentCards";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

const EXAMPLE = "수제 쿠키";

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

  function search(word = product) {
    const q = word.trim();
    if (!q) return;
    void run(async () => {
      dispatch({ type: "researched", research: await fetchResearch(q), product: q });
    }, () => search(q));
  }

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
      <Coach>어떤 상품을 파세요? 네이버에서 손님이 어떤 말로, 언제, 누가 찾는지 알아볼게요.</Coach>
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
      </div>

      {busy && <ResultSkeleton />}
      {!busy && stale && (
        <p className="rounded-button bg-sunk px-3 py-2 text-caption text-soft">
          아래는 '{state.product}' 결과예요. 찾아보기를 누르면 새 상품으로 바뀌어요.
        </p>
      )}
      {!busy && r && (
        <div className={stale ? "opacity-50 transition-opacity" : "transition-opacity"}>
          {r.notice
            ? <NoData notice={r.notice} product={state.product ?? product.trim()} dispatch={dispatch} />
            : Array.isArray(r.segments)
              ? <SegmentResult research={r} segments={r.segments} state={state} dispatch={dispatch}
                  onPickCategory={pickCategory} onResearch={() => rerun()} />
              : <Result research={r} dropped={state.dropped ?? []} dispatch={dispatch} />}
        </div>
      )}
    </section>
  );
}

/** 결과 자리 스켈레톤: 결과 카드와 같은 모양. */
function ResultSkeleton() {
  return (
    <div className="flex flex-col gap-4 rounded-card border border-line bg-paper p-4">
      <p role="status" className="text-caption text-soft">네이버에서 찾는 중이에요…</p>
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
function KeywordChips({ research: r, dropped, kept, title, hint, dispatch }: {
  research: Research; dropped: string[]; kept: string[]; title: string; hint: string;
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
              <span className="text-small text-soft tabular-nums">월 {compact(k.total_qc)}회</span>
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
      <p className="mt-2">이런 말로 찾는 사람은 사지 않을 가능성이 커서 문구에 넣지 않아요.</p>
      <ul className="mt-2 flex flex-wrap gap-1.5">
        {words.map((w) => <li key={w} className="rounded-badge bg-sunk px-2 py-0.5 line-through decoration-soft">{w}</li>)}
      </ul>
    </details>
  );
}

function SourceLine({ research: r }: { research: Research }) {
  return (
    <p className="text-small leading-relaxed text-soft">
      {r.sources?.length
        ? `출처: 네이버 검색광고·데이터랩 — ${r.sources.map((x) => `${x.label} ${x.today ? "오늘 조회" : `${dayLabel(x.fetched)} 저장본`}`).join(" · ")}`
        : `출처: 네이버 검색광고 · 데이터랩 · 조회일 ${r.fetched}${r.source === "cache" ? " (저장된 자료)" : ""}`}
    </p>
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
    dispatch({ type: "confirmTarget", target: { ...ageGroupToRange(top), gender }, keywords: kept });
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
function SegmentResult({ research: r, segments, state, dispatch, onPickCategory, onResearch }: {
  research: Research;
  segments: Segment[];
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
  onPickCategory: (code: string) => void;
  onResearch: () => void;
}) {
  const dropped = state.dropped ?? [];
  const kept = r.keywords.map((k) => k.keyword).filter((k) => !dropped.includes(k));
  const selected = segments.find((s) => s.intent === state.segment?.intent);
  const [age, setAge] = useState("");
  const [gender, setGender] = useState<"" | "all" | "female" | "male">("");
  const product = state.product ?? "";

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

  function confirm() {
    if (!selected) return;
    const target = selected.audience
      ? { ...ageGroupToRange(selected.audience.top_age), gender: genderFrom(selected.audience.female) }
      : { ...ageGroupToRange(age), gender: gender as "all" | "female" | "male" };
    dispatch({ type: "confirmTarget", target, keywords: kept, segment: selected });
  }

  const detail = selected?.audience
    ? <AgeFigure audience={selected.audience} />
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
        <CategoryPick product={product} category={r.category} categories={r.categories} onPick={onPickCategory} />
      )}
      {r.product_stats && <ProductStats stats={r.product_stats} hasCategory={!!r.category} />}
      <KeywordChips research={r} dropped={dropped} kept={kept} dispatch={dispatch}
        title="손님은 이렇게도 불러요" hint="사장님 상품에 맞지 않는 말은 눌러서 빼 주세요." />
      <Negatives words={r.negatives} />

      {!r.category ? (
        <div className="flex flex-col gap-2.5">
          <span className="text-caption font-semibold text-soft">손님 무리</span>
          <p className="text-caption">분야를 골라 주시면 손님을 찾아볼게요</p>
          <CategoryAsk categories={r.categories} candidates={r.category_candidates} onPick={onPickCategory} />
        </div>
      ) : segments.length === 0 ? (
        <NoData notice="이 말로 찾는 손님 자료를 찾지 못했어요." product={product} keywords={kept} dispatch={dispatch} />
      ) : (
        <>
          <SegmentCards segments={segments} selected={selected} dropped={dropped}
            onPick={(segment) => dispatch({ type: "pickSegment", segment })} onResearch={onResearch}
            selectedDetail={detail} />
          <div className="flex flex-col gap-2">
            {kept.length === 0 && <p className="text-caption text-warn">▲ 검색어를 하나 이상 남겨 주세요.</p>}
            {!selected && <p className="text-caption text-warn">▲ 광고를 보여 줄 손님을 하나 골라 주세요.</p>}
            {manualMissing && <p className="text-caption text-warn">▲ 보여 줄 나이와 성별을 골라 주세요.</p>}
            <PrimaryButton onClick={confirm} disabled={!ready}>이 손님들로 할게요</PrimaryButton>
          </div>
        </>
      )}
      <SourceLine research={r} />
    </div>
  );
}

const MANUAL_AGES = ["20", "30", "40", "50", "60"];
const MANUAL_GENDERS: { id: "all" | "female" | "male"; label: string }[] = [
  { id: "all", label: "모두" }, { id: "female", label: "여성" }, { id: "male", label: "남성" },
];

/** 네이버 자료가 없을 때: 다른 말로 다시 찾거나, 사장님이 직접 정하고 넘어간다 (막다른 길을 만들지 않는다). */
function NoData({ notice, product, keywords = [], dispatch }: {
  notice: string; product: string; keywords?: string[]; dispatch: (ev: FlowEvent) => void;
}) {
  const [manual, setManual] = useState(false);
  const [age, setAge] = useState("30");
  const [gender, setGender] = useState<"all" | "female" | "male">("all");

  return (
    <div className="flex flex-col gap-4">
      <Coach>{notice} 아니면 누구에게 보여 줄지 직접 정하고 넘어가도 돼요.</Coach>
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
