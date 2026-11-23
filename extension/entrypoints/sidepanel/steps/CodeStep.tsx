import { useState } from "react";
import { ANALYSIS_PAGE, plan as fetchPlan } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";

/** 4자리로 맞춘다: 공백을 빼고 대문자로 (분석 페이지는 헷갈리는 O·0·I·1을 쓰지 않는다). */
export function tidyCode(raw: string): string {
  return raw.replace(/\s+/g, "").toUpperCase();
}

/** ③ 분석: 결과 파일은 분석 페이지에서 올리고, 거기서 받은 코드 4자리를 여기에 넣는다. */
export default function CodeStep({ dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
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
      <Coach>광고가 끝났으면 분석 페이지에 결과 파일을 올려 주세요. 다 계산하면 코드 4자리가 나와요.</Coach>
      <button type="button" onClick={() => void browser.tabs.create({ url: ANALYSIS_PAGE })}
        className="self-start rounded-xl border border-ink px-4 py-2.5 text-[15px] font-semibold">
        분석 페이지 열기
      </button>
      <form className="flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); void load(); }}>
        <label htmlFor="plan-code" className="text-[13px] text-soft">분석 페이지의 코드 4자리</label>
        <input id="plan-code" value={code} onChange={(e) => setCode(e.target.value)} maxLength={8}
          autoComplete="off" autoCapitalize="characters" spellCheck={false} placeholder="예: 75R7"
          aria-invalid={error ? true : undefined} aria-describedby={error ? "plan-code-error" : undefined}
          className="rounded-xl border border-line bg-paper px-3 py-2.5 text-[20px] font-bold tracking-[0.3em] uppercase" />
        {error && <div id="plan-code-error"><ErrorLine message={error} /></div>}
        <PrimaryButton type="submit" busy={busy}>가져오기</PrimaryButton>
      </form>
    </section>
  );
}
