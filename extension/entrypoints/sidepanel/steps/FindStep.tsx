import { useState } from "react";
import { research as fetchResearch, type Research } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { GENDER_LABEL, ageGroupToRange, genderFrom } from "../../../lib/settings";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";

const AGE_ORDER = ["10", "20", "30", "40", "50", "60"];

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

/** ① 찾기: 상품 → 네이버로 누가·어떤 말로 찾는지 → 타겟 확인. */
export default function FindStep({ state, dispatch }: Props) {
  const [product, setProduct] = useState(state.product ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const r = state.research;

  async function search() {
    setBusy(true);
    setError(null);
    try {
      dispatch({ type: "researched", research: await fetchResearch(product.trim()), product: product.trim() });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <Coach>어떤 상품을 파세요? 네이버에서 누가, 어떤 말로 찾는지 알아볼게요.</Coach>
      <div className="flex flex-col gap-2">
        <label htmlFor="product" className="text-caption text-soft">파는 상품</label>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (product.trim() && !busy) search();
          }}
        >
          <input
            id="product"
            value={product}
            onChange={(e) => setProduct(e.target.value)}
            placeholder="예: 수제 쿠키"
            className="flex-1 rounded-xl border border-line bg-paper px-3 py-2.5 text-body focus-visible:outline-2 focus-visible:outline-accent"
          />
          <button
            type="submit"
            disabled={!product.trim() || busy}
            className="rounded-xl border border-ink px-4 text-body font-semibold disabled:opacity-(--state-disabled-opacity)"
          >
            {busy ? "찾는 중…" : "찾아보기"}
          </button>
        </form>
        {error && <ErrorLine message={error} onRetry={search} />}
      </div>

      {r && r.notice && <NoData notice={r.notice} product={state.product ?? product.trim()} dispatch={dispatch} />}
      {r && !r.notice && <Result research={r} dropped={state.dropped ?? []} dispatch={dispatch} />}
    </section>
  );
}

function Result({ research: r, dropped, dispatch }: {
  research: Research;
  dropped: string[];
  dispatch: (ev: FlowEvent) => void;
}) {
  const aud = r.audience;
  const gender = aud ? genderFrom(aud.female) : "all";
  const top = aud?.top_age ?? "30";
  const who = `${top}대 ${gender === "all" ? "" : GENDER_LABEL[gender]}`.trim();
  const ages = aud ? AGE_ORDER.filter((a) => a in aud.ages) : [];
  const max = aud ? Math.max(...ages.map((a) => aud.ages[a] ?? 0)) : 1;
  const kept = r.keywords.map((k) => k.keyword).filter((k) => !dropped.includes(k));

  function confirm() {
    dispatch({ type: "confirmTarget", target: { ...ageGroupToRange(top), gender }, keywords: kept });
  }

  return (
    <div className="flex flex-col gap-5">
      {aud && (
        <figure className="flex flex-col gap-3">
          <figcaption className="flex flex-col">
            <span className="text-caption text-soft">가장 눈에 띄게 찾는 사람</span>
            <strong className="text-[22px] font-bold">{who}</strong>
          </figcaption>
          <div className="flex items-end gap-2 h-24" aria-label="연령대별 검색 비중">
            {ages.map((a) => (
              <div key={a} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={a === top ? "w-full rounded-t-md bg-accent" : "w-full rounded-t-md bg-line"}
                  style={{ height: `${Math.round(((aud.ages[a] ?? 0) / max) * 80)}px` }}
                />
                <span className={a === top ? "text-caption font-semibold" : "text-caption text-soft"}>{a}대</span>
              </div>
            ))}
          </div>
          <p className="text-caption text-soft">{r.headline}</p>
        </figure>
      )}

      <div className="flex flex-col gap-2">
        <span className="text-caption text-soft">이 사람들이 쓰는 말 (빼고 싶은 건 누르세요)</span>
        <div className="flex flex-wrap gap-2">
          {r.keywords.map((k) => {
            const off = dropped.includes(k.keyword);
            return (
              <button
                key={k.keyword}
                type="button"
                aria-pressed={!off}
                onClick={() => dispatch({ type: "toggleKeyword", keyword: k.keyword })}
                className={`rounded-full border px-3 py-1 text-caption ${off ? "border-line text-soft line-through" : "border-ink bg-paper"}`}
              >
                {k.keyword} · 월 {k.total_qc.toLocaleString()}회
              </button>
            );
          })}
        </div>
      </div>

      {r.negatives && r.negatives.length > 0 && (
        <details className="text-caption text-soft">
          <summary className="cursor-pointer">광고에서 뺄 말 {r.negatives.length}개 (만들기·매장·관련 낮은 말)</summary>
          <p className="mt-2">이런 말로 찾는 사람은 사지 않을 가능성이 커서 문구에 넣지 않아요.</p>
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {r.negatives.map((w) => <li key={w} className="rounded-full border border-line px-2 py-0.5">{w}</li>)}
          </ul>
        </details>
      )}
      <p className="text-caption text-soft">
        {r.sources?.length
          ? `출처: 네이버 검색광고·데이터랩 — ${r.sources.map((x) => `${x.label} ${x.today ? "오늘 조회" : `${dayLabel(x.fetched)} 저장본`}`).join(" · ")}`
          : `출처: 네이버 검색광고 · 데이터랩 · 조회일 ${r.fetched}${r.source === "cache" ? " (저장된 자료)" : ""}`}
      </p>
      <PrimaryButton onClick={confirm} disabled={kept.length === 0}>이 사람들로 할게요</PrimaryButton>
    </div>
  );
}

const MANUAL_AGES = ["20", "30", "40", "50", "60"];
const MANUAL_GENDERS: { id: "all" | "female" | "male"; label: string }[] = [
  { id: "all", label: "모두" }, { id: "female", label: "여성" }, { id: "male", label: "남성" },
];

/** 네이버 자료가 없을 때: 다른 말로 다시 찾거나, 사장님이 직접 정하고 넘어간다 (막다른 길을 만들지 않는다). */
function NoData({ notice, product, dispatch }: { notice: string; product: string; dispatch: (ev: FlowEvent) => void }) {
  const [manual, setManual] = useState(false);
  const [age, setAge] = useState("30");
  const [gender, setGender] = useState<"all" | "female" | "male">("all");

  return (
    <div className="flex flex-col gap-4">
      <Coach>{notice} 아니면 누구에게 보여 줄지 직접 정하고 넘어가도 돼요.</Coach>
      {!manual ? (
        <button type="button" onClick={() => setManual(true)} className="self-start text-body font-semibold underline">
          직접 정하고 계속할게요
        </button>
      ) : (
        <>
          <Choice legend="보여 줄 나이" name="manual-age"
            options={MANUAL_AGES.map((a) => ({ id: a, label: `${a}대` }))} value={age} onChange={setAge} />
          <Choice legend="성별" name="manual-gender"
            options={MANUAL_GENDERS} value={gender} onChange={(v) => setGender(v as typeof gender)} />
          <p className="text-caption text-soft">검색어 자료가 없어서 광고 문구에는 '{product}'를 넣을게요.</p>
          <PrimaryButton onClick={() => dispatch({ type: "confirmTarget", target: { ...ageGroupToRange(age), gender }, keywords: [product] })}>
            이 사람들로 할게요
          </PrimaryButton>
        </>
      )}
    </div>
  );
}

function Choice({ legend, name, options, value, onChange }: {
  legend: string; name: string; options: { id: string; label: string }[]; value: string; onChange: (v: string) => void;
}) {
  return (
    <fieldset className="flex flex-col gap-2">
      <legend className="text-caption text-soft mb-2">{legend}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <label key={o.id}
            className={`rounded-full border px-3 py-1.5 text-label cursor-pointer has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${value === o.id ? "border-ink bg-ink text-paper font-semibold" : "border-line"}`}>
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
