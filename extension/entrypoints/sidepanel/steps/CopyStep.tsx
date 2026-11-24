import { useState } from "react";
import { copies as fetchCopies, type Copy } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

/** ② 문구: 좋은 점 한두 마디 → 문구 3안 → 하나 고르기. */
export default function CopyStep({ state, dispatch }: Props) {
  const [strengths, setStrengths] = useState("");
  const [list, setList] = useState<Copy[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function write() {
    setBusy(true);
    setError(null);
    try {
      const pieces = strengths.split(/[,\n]/).map((s) => s.trim()).filter(Boolean);
      const r = await fetchCopies({ product: state.product ?? "", strengths: pieces, keywords: state.keywords, avoid: state.research?.negatives ?? [] });
      setList(r.copies);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <Coach>상품의 좋은 점을 한두 마디로 알려 주세요. 찾은 키워드와 섞어 광고 문구 3개를 써 드릴게요.</Coach>
      <div className="flex flex-col gap-2">
        <label htmlFor="strengths" className="text-caption text-soft">상품의 좋은 점</label>
        <input
          id="strengths"
          value={strengths}
          onChange={(e) => setStrengths(e.target.value)}
          placeholder="예: 버터 듬뿍, 당일 구움"
          className="rounded-xl border border-line bg-paper px-3 py-2.5 text-body"
        />
        {error && <ErrorLine message={error} onRetry={write} />}
      </div>
      {!list && <PrimaryButton onClick={write} busy={busy}>문구 써 주세요</PrimaryButton>}
      {list && (
        <ol className="flex flex-col gap-3">
          {list.map((c, i) => (
            <li key={i} className="border-l-4 border-accent pl-3 flex flex-col gap-1">
              <strong className="text-body">{c.headline}</strong>
              <p className="text-body text-soft">{c.primary_text}</p>
              <button type="button" onClick={() => dispatch({ type: "pickCopy", copy: c })} className="self-start text-caption font-semibold underline">
                이 문구로 할게요 ({i + 1}안)
              </button>
            </li>
          ))}
        </ol>
      )}
      {list && (
        <button type="button" onClick={write} disabled={busy} className="self-start text-caption text-soft underline disabled:opacity-(--state-disabled-opacity)">
          {busy ? "다시 쓰는 중…" : "다른 문구로 다시 써 주세요"}
        </button>
      )}
      <p className="text-caption text-soft">사실이 아닌 말(최저가, 1위 등)은 넣지 않아요.</p>
    </section>
  );
}
