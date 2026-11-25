import { useState } from "react";
import { analysisPageUrl, plan as fetchPlan } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";

/** 4자리로 맞춘다: 공백을 빼고 대문자로 (분석 페이지는 헷갈리는 O·0·I·1을 쓰지 않는다). */
export function tidyCode(raw: string): string {
  return raw.replace(/\s+/g, "").toUpperCase();
}

/** ③ 분석: 결과 파일은 분석 페이지에서 올리고, 거기서 받은 코드 4자리를 여기에 넣는다. */
export default function CodeStep({ state, dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
  // 이번 광고의 세팅값 (비어 있는 칸은 빼고) → 분석 페이지 '내 세팅 카드'
  const settings = Object.fromEntries(state.settings.filter((x) => x.value).map((x) => [x.fieldId, x.value]));
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const c = tidyCode(code);
    if (c.length !== 4) {
      setError("코드는 4자리예요. 분석 페이지 '다음에 할 일'에 있는 글자 4개를 넣어 주세요.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      dispatch({ type: "planLoaded", plan: await fetchPlan(c) });
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col gap-4">
      <Coach>광고가 끝났으면 결과 파일을 받아서 다음에 바꿀 칸을 찾아볼까요? 분석 기준은 꼭 <b>일 · 노출 위치</b>로 골라 주세요. 광고가 끝난 뒤 받아야 기간 합계가 맞아요.</Coach>
      <ol className="flex flex-col gap-2 text-body">
        <li className="flex gap-2"><span className="font-bold text-accent-ink">1</span>
          <span>광고 관리자 보고서에서 [내보내기] → 분석 기준 '일 · 노출 위치'
            <button type="button" onClick={() => dispatch({ type: "startExport" })} className="ml-1 text-caption font-semibold text-accent-ink underline">내보내기 버튼 짚어 주기</button>
          </span></li>
        <li className="flex gap-2"><span className="font-bold text-accent-ink">2</span>
          <span>분석 페이지에 받은 파일을 올리기
            {Object.keys(settings).length > 0 && <span className="block text-caption text-soft">이번 세팅값({Object.keys(settings).length}칸)은 자동으로 함께 넘어가요</span>}
            <button type="button" onClick={async () => { await browser.tabs.create({ url: await analysisPageUrl(settings) }); }}
              className="mt-2 block rounded-button border border-accent bg-paper px-4 py-2 font-semibold text-accent-ink">분석 페이지 열기 (새 창)</button>
          </span></li>
        <li className="flex gap-2"><span className="font-bold text-accent-ink">3</span><span>다 계산하면 나오는 코드 4자리를 아래에 넣기</span></li>
      </ol>
      <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); void load(); }}>
        <label htmlFor="plan-code" className="text-caption text-soft">분석 페이지의 코드 4자리</label>
        <input id="plan-code" value={code} onChange={(e) => setCode(e.target.value)} maxLength={8}
          autoComplete="off" autoCapitalize="characters" spellCheck={false} placeholder="예: 75R7"
          aria-invalid={error ? true : undefined} aria-describedby={error ? "plan-code-error" : undefined}
          className="rounded-button border border-line bg-paper px-3 py-2.5 text-title font-bold tracking-[0.3em] uppercase" />
        {error && <div id="plan-code-error"><ErrorLine message={error} /></div>}
        <PrimaryButton type="submit" busy={busy}>가져오기</PrimaryButton>
      </form>
    </section>
  );
}
