import { useEffect, useState } from "react";
import { analysisPageUrl, plan as fetchPlan } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";

/** 4자리로 맞춘다: 공백을 빼고 대문자로 (분석 페이지는 헷갈리는 O·0·I·1을 쓰지 않는다). */
export function tidyCode(raw: string): string {
  return raw.replace(/\s+/g, "").toUpperCase();
}

/** CodeStep 체크 칸 번호: 0 파일 받기 ✓ · 1 분석 페이지 열기 ✓ · 9 내보내기 안내를 시작함(화면에 안 보임) */
const EXPORTING = 9;

/** ③ 분석: 결과 파일은 분석 페이지에서 올리고, 거기서 받은 코드 4자리를 여기에 넣는다. */
export default function CodeStep({ state, dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
  // 이번 광고의 세팅값 (비어 있는 칸은 빼고) → 분석 페이지 '내 세팅 카드'
  const settings = Object.fromEntries(state.settings.filter((x) => x.value).map((x) => [x.fieldId, x.value]));
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lost, setLost] = useState(false);   // 세팅값을 분석 페이지로 넘기지 못함 (서버가 잠깐 안 됨)

  async function load() {
    const c = tidyCode(code);
    if (c.length !== 4) {
      setError("코드는 4자리예요. 분석 페이지 ③ 준비하기에서 [확장 프로그램으로 보내기]를 누르면 나오는 글자 4개예요.");
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
  const endIso = pick("meta.adset.end_date")?.slice(0, 10);
  const end = endIso && /^\d{4}-\d{2}-\d{2}$/.test(endIso) ? `${Number(endIso.slice(5, 7))}월 ${Number(endIso.slice(8))}일` : endIso;   // 다른 화면처럼 '11월 20일'
  const budget = pick("meta.adset.lifetime_budget");
  const startIso = pick("meta.adset.start_date")?.slice(0, 10);
  const md = (iso?: string) => (iso && /^\d{4}-\d{2}-\d{2}$/.test(iso) ? `${Number(iso.slice(5, 7))}/${Number(iso.slice(8))}` : null);
  const ended = Boolean(endIso) && new Date(`${endIso}T23:59:59`) < new Date();
  const period = md(startIso) && md(endIso) ? ` (${md(startIso)}~${md(endIso)})` : "";
  // EX-02 ③ 받은 단계는 ✓ (체크 저장소를 같이 쓴다: 분석 탭에 다녀와도 남는다)
  const doneKey = `upload:${endIso ?? ""}`;
  const done = state.checks?.[doneKey] ?? [];
  const mark = (i: number) => { if (!done.includes(i)) dispatch({ type: "toggleCheck", key: doneKey, index: i }); };
  // 1번 ✓는 '받았을 때': [짚어 주기]를 누르면 시작만 적어 두고(EXPORTING), 내보내기 안내를 닫고 이 화면으로 돌아오면
  // ('← 파일을 받았어요 · 돌아가기') ✓. 이 화면은 안내가 떠 있는 동안 안 보이니, 다시 그려질 때가 곧 안내가 닫힌 때다.
  useEffect(() => { if (done.includes(EXPORTING)) mark(0); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  const Num = ({ i }: { i: number }) => done.includes(i)
    ? <span className="font-bold text-adopt">✓<span className="sr-only"> 했어요</span></span>
    : <span className="font-bold text-accent-ink">{i + 1}</span>;
  return (
    <section className="flex flex-col gap-4">
      <Coach>{ended ? `광고가 끝났어요${period}. ` : ""}결과 파일을 받아서 다음에 바꿀 칸 1개를 찾아볼까요?</Coach>
      <ol className="flex flex-col gap-3 text-body">
        <li className="flex gap-2"><Num i={0} />
          <span>광고 관리자에서 결과 파일 받기
            <span className="block text-label text-soft">[내보내기]에서 <b>일 · 노출 위치</b>를 꼭 골라요. 광고가 끝난 뒤 받아야 기간 합계가 맞아요.</span>
            <button type="button" onClick={() => { mark(EXPORTING); dispatch({ type: "startExport" }); }} className="flex min-h-11 items-center text-label font-semibold text-accent-ink underline">내보내기 버튼 짚어 주기</button>
          </span></li>
        <li className="flex gap-2"><Num i={1} />
          <span>분석 페이지에 파일 올리기
            <span className="block text-label text-soft">끝까지 보고 [확장 프로그램으로 보내기]를 누르면 바꿀 칸이 이 패널로 와요.</span>
          </span></li>
      </ol>
      {(summary || media) && (
        <section aria-label="이번 광고 세팅" className="flex flex-col gap-1 rounded-card border border-line bg-paper px-3 py-2 text-label">
          <p className="font-semibold">이번 광고 세팅{Object.keys(settings).length > 0 ? ` · ${Object.keys(settings).length}칸은 분석 페이지로 자동으로 넘어가요` : ""}</p>
          {summary && <p>{summary}</p>}
          {media && <p>소재: {media}</p>}
          {end && <p>종료 날짜: {end}{budget ? ` · 세트당 총 ${budget}` : " · 예산은 광고 관리자에 넣은 값 그대로예요"}</p>}
        </section>
      )}
      <PrimaryButton onClick={async () => {
        mark(1);
        const url = await analysisPageUrl(settings);
        setLost(Object.keys(settings).length > 0 && !url.includes("#s="));   // 맡기기 실패 → 열쇠 없이 열림
        await browser.tabs.create({ url });
      }}>분석 페이지 열기 (새 창)</PrimaryButton>
      {lost && <ErrorLine message="이번 세팅값을 넘기지 못했어요. 분석 페이지에서 '내 광고 설정 5개만 직접 입력하기'로 넣어 주세요." />}
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
