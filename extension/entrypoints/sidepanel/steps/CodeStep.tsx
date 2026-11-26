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
      setError("코드는 4자리예요. 분석 페이지 마지막 ⑥ 보내기에 있는 글자 4개를 넣어 주세요.");
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

  // EX-02 ④ 이번 광고 세팅 요약 (분석 페이지로 자동으로 넘어감)
  const pick = (id: string) => state.settings.find((x) => x.fieldId === id)?.value;
  const summary = [pick("meta.campaign.objective"), pick("meta.adset.age_gender"), pick("meta.adset.location")].filter(Boolean).join(" · ");
  const media = [pick("meta.ad.format"), pick("meta.ad.media")].filter(Boolean).join(" · ");
  const end = pick("meta.adset.end_date");
  const budget = pick("meta.adset.lifetime_budget");
  return (
    <section className="flex flex-col gap-4">
      <Coach>광고가 끝났으면 결과 파일을 받아 분석 페이지에 올려요. 다음에 바꿔 볼 칸 1개를 찾아 드려요. 광고가 끝난 뒤 받아야 기간 합계가 맞아요.</Coach>
      <ol className="flex flex-col gap-2 text-body">
        <li className="flex gap-2"><span className="font-bold text-accent-ink">1</span>
          <span>광고 관리자에서 결과 파일 받기: [내보내기]에서 <b>일 · 노출 위치</b>를 꼭 고르기
            <button type="button" onClick={() => dispatch({ type: "startExport" })} className="flex min-h-11 items-center text-label font-semibold text-accent-ink underline">내보내기 버튼 짚어 주기</button>
          </span></li>
        <li className="flex gap-2"><span className="font-bold text-accent-ink">2</span>
          <span>분석 페이지에 받은 파일을 올리기
            {Object.keys(settings).length > 0 && <span className="block text-caption text-soft">이번 세팅값({Object.keys(settings).length}칸)은 자동으로 함께 넘어가요</span>}
            <button type="button" onClick={async () => { await browser.tabs.create({ url: await analysisPageUrl(settings) }); }}
              className="mt-2 block min-h-12 w-full rounded-button bg-accent px-4 font-semibold text-on-accent hover:bg-accent-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">분석 페이지 열기 (새 창)</button>
          </span></li>
        <li className="flex gap-2"><span className="font-bold text-accent-ink">3</span><span>분석 페이지 마지막 ⑥ 보내기에서 [확장 프로그램으로 보내기]를 누르면 바꿀 칸이 여기로 와요. 안 오면 아래 '코드로 넣기'를 펼쳐 거기 있는 코드 4자리를 넣어 주세요.</span></li>
      </ol>
      {(summary || media) && (
        <section aria-label="이번 광고 세팅" className="flex flex-col gap-1 rounded-card border border-line bg-paper px-3 py-2 text-caption">
          <p className="font-semibold">이번 광고 세팅</p>
          {summary && <p>{summary}</p>}
          {media && <p>소재: {media}</p>}
          {end && <p>종료 날짜: {end}{budget ? ` · 세트당 총 ${budget}` : " · 예산은 광고 관리자에 넣은 값 그대로예요"}</p>}
          <p className="text-soft">광고가 끝난 뒤 받아야 기간 합계가 맞아요</p>
        </section>
      )}
      <details className="rounded-button bg-paper px-3 py-2">
        <summary className="flex min-h-11 cursor-pointer items-center text-label font-semibold text-accent-ink">보내기가 안 되면: 코드 4자리로 넣기</summary>
      <form className="mt-2 flex flex-col gap-2" onSubmit={(e) => { e.preventDefault(); void load(); }}>
        <label htmlFor="plan-code" className="text-caption text-soft">분석 페이지의 코드 4자리</label>
        <input id="plan-code" value={code} onChange={(e) => setCode(e.target.value)} maxLength={8}
          autoComplete="off" autoCapitalize="characters" spellCheck={false} placeholder="예: 75R7"
          aria-invalid={error ? true : undefined} aria-describedby={error ? "plan-code-error" : undefined}
          className="rounded-button border border-field-line bg-paper px-3 py-2.5 text-title font-bold tracking-[0.3em] uppercase" />
        {error && <div id="plan-code-error"><ErrorLine message={error} /></div>}
        <PrimaryButton type="submit" busy={busy}>가져오기</PrimaryButton>
      </form>
      </details>
    </section>
  );
}
