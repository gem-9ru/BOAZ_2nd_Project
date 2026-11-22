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
        <label htmlFor="product" className="text-[13px] text-soft">파는 상품</label>
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
            className="flex-1 rounded-xl border border-line bg-paper px-3 py-2.5 text-[15px] focus-visible:outline-2 focus-visible:outline-accent"
          />
          <button
            type="submit"
            disabled={!product.trim() || busy}
            className="rounded-xl border border-ink px-4 text-[15px] font-semibold disabled:opacity-40"
          >
            {busy ? "찾는 중…" : "찾아보기"}
          </button>
        </form>
        {error && <ErrorLine message={error} onRetry={search} />}
      </div>

      {r && r.notice && <Coach>{r.notice}</Coach>}
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
            <span className="text-[13px] text-soft">가장 눈에 띄게 찾는 사람</span>
            <strong className="text-[22px] font-bold">{who}</strong>
          </figcaption>
          <div className="flex items-end gap-2 h-24" aria-label="연령대별 검색 비중">
            {ages.map((a) => (
              <div key={a} className="flex-1 flex flex-col items-center gap-1">
                <div
                  className={a === top ? "w-full rounded-t-md bg-accent" : "w-full rounded-t-md bg-line"}
                  style={{ height: `${Math.round(((aud.ages[a] ?? 0) / max) * 80)}px` }}
                />
                <span className={a === top ? "text-[13px] font-semibold" : "text-[13px] text-soft"}>{a}대</span>
              </div>
            ))}
          </div>
          <p className="text-[13px] text-soft">{r.headline}</p>
        </figure>
      )}

      <div className="flex flex-col gap-2">
        <span className="text-[13px] text-soft">이 사람들이 쓰는 말 (빼고 싶은 건 누르세요)</span>
        <div className="flex flex-wrap gap-2">
          {r.keywords.map((k) => {
            const off = dropped.includes(k.keyword);
            return (
              <button
                key={k.keyword}
                type="button"
                aria-pressed={!off}
                onClick={() => dispatch({ type: "toggleKeyword", keyword: k.keyword })}
                className={`rounded-full border px-3 py-1 text-[13px] ${off ? "border-line text-soft line-through" : "border-ink bg-paper"}`}
              >
                {k.keyword} · 월 {k.total_qc.toLocaleString()}회
              </button>
            );
          })}
        </div>
      </div>

      <p className="text-[13px] text-soft">
        출처: 네이버 검색광고 · 데이터랩 · 조회일 {r.fetched}
        {r.source === "cache" ? " (저장된 자료)" : ""}
      </p>
      <PrimaryButton onClick={confirm} disabled={kept.length === 0}>이 사람들로 할게요</PrimaryButton>
    </div>
  );
}
