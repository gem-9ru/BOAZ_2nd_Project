import { useEffect, useRef, useState } from "react";
import { askAssistant, plan as fetchPlan, type AssistantAlert } from "../../../lib/api";
import { ANALYSIS_STEPS, type AnalysisTab } from "../../../lib/analysisTab";
import type { FlowEvent } from "../../../lib/flow";
import { AskForm, bubbleClass, useAsk, type Bubble } from "../ui/Chat";
import { Coach } from "../ui/Coach";

const SHAPE: Record<AssistantAlert["level"], { mark: string; name: string; box: string }> = {
  block: { mark: "■", name: "차단", box: "bg-block-bg text-block-ink" },
  warn: { mark: "▲", name: "주의", box: "bg-warn-bg text-warn" },
  info: { mark: "●", name: "참고", box: "bg-info-bg text-ink" },
};

/** 분석 페이지 옆 광고 어시스턴트 (v4.2 AN-COM ④): 분석 페이지를 크롬 탭에 펼쳐 두면, 이 사이드 패널이 그 단계에 맞춰
 *  알림 말풍선을 먼저, 그다음 이 단계 요약 + 추천 질문 2개를 보여 준다. 질문하면 그 단계 결과(JSON)로만 설명한다.
 *  같은 알림은 처음 나오는 단계에서만 (서버가 단계별로 준다). AN-06 [확장 프로그램으로 보내기]를 누르면 테스트안을 받아 EX-03으로 이어진다. */
export default function AnalysisAssistant({ tab, dispatch }: { tab: AnalysisTab; dispatch: (ev: FlowEvent) => void }) {
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);   // 단계 첫 말을 기다리는 중
  const seen = useRef(new Set<string>());
  const sent = useRef<string | null>(null);
  const end = useRef<HTMLDivElement>(null);
  const { code, step } = tab;
  const { busy, ask } = useAsk(code, step, (b) => setBubbles((all) => [...all, b]));

  // 다른 결과(코드)로 바뀌면 대화를 새로 시작
  useEffect(() => { seen.current = new Set(); setBubbles([]); setSuggestions([]); }, [code]);

  useEffect(() => {
    if (!code || !step || seen.current.has(step)) return;
    seen.current.add(step);
    setLoading(true);
    askAssistant(code, step).finally(() => setLoading(false)).then((o) => {
      setBubbles((b) => [...b, ...(o.alerts ?? []).map((a) => ({ from: "assistant" as const, text: `${a.text} ${a.todo}`, alert: a })), { from: "assistant", text: o.message }]);
      setSuggestions(o.suggestions ?? []);
    }, () => setBubbles((b) => [...b, { from: "assistant", text: "지금은 어시스턴트에 연결하지 못했어요. 분석 페이지의 내용은 그대로 보실 수 있어요." }]));
  }, [code, step]);

  // AN-06 [확장 프로그램으로 보내기] → 테스트안을 받아 둔다 (탭을 떠나면 EX-03 화면, [다음 테스트 세팅]을 눌러야 뭉치가 짚는다)
  useEffect(() => {
    if (!code || !tab.send || sent.current === tab.send) return;
    sent.current = tab.send;
    fetchPlan(code).then((got) => {
      // 사장님이 ③에서 고른 예산이 있으면 그 금액으로 (서버 계획은 기본값 per_set)
      const p = tab.budget ? { ...got, change: { ...got.change, per_set: tab.budget } } : got;
      dispatch({ type: "planLoaded", plan: p });
      setBubbles((b) => [...b, { from: "assistant", text: `테스트안을 받았어요 (${p.change.path ?? p.change.label}). 이 탭을 떠나면 이 패널에 [다음 테스트 세팅]이 보여요. 누르면 광고 관리자에서 그 칸을 짚어 드려요. 게시는 사장님이 직접 해요.` }]);
    }, (e: Error) => setBubbles((b) => [...b, { from: "assistant", text: e.message }]));
  }, [code, tab.send, tab.budget, dispatch]);

  useEffect(() => { end.current?.scrollIntoView?.({ block: "end" }); }, [bubbles]);

  if (!code) {
    // AN-00 업로드: 아직 결과가 없으면 정해진 안내만
    return (
      <section aria-label="분석 페이지 어시스턴트" className="flex flex-col gap-3">
        <p className="text-caption font-semibold text-accent-ink">분석 페이지 · 업로드</p>
        <Coach>안녕하세요! 돌려 본 광고 결과를 올려 주시면 다음에 바꿔 볼 칸 1개를 같이 찾아볼게요.</Coach>
        <Coach>내보내기 할 때 분석 기준에서 <b>일</b>과 <b>노출 위치</b>를 꼭 골라 주세요.</Coach>
        <details className="rounded-button bg-paper px-3 py-2 text-caption">
          <summary className="cursor-pointer font-semibold text-accent-ink">CSV는 어디서 받아요?</summary>
          <p className="mt-1">광고 관리자 › 보고서 › 내보내기에서 분석 기준을 '일 · 노출 위치'로 고른 뒤 CSV로 받아요. 광고가 끝난 뒤 받아야 기간 합계가 맞아요.</p>
        </details>
        <details className="rounded-button bg-paper px-3 py-2 text-caption">
          <summary className="cursor-pointer font-semibold text-accent-ink">광고 설정은 왜 필요해요?</summary>
          <p className="mt-1">내 광고 설정이 있어야 '내 세팅 카드'에서 칸마다 바꿀지·둘지를 알려 드려요. 확장 프로그램 ② 세팅에서 만든 값은 자동으로 넘어가요.</p>
        </details>
      </section>
    );
  }

  return (
    <section aria-label="분석 페이지 어시스턴트" className="flex flex-col gap-2 rounded-card bg-accent-soft p-3">
      <p className="text-caption font-semibold text-accent-ink">분석 페이지 · {step ? ANALYSIS_STEPS[step] : ""}</p>
      <div className="flex flex-col gap-2" aria-live="polite">
        {bubbles.map((b, i) => b.alert ? (
          <p key={i} className={`flex gap-2 rounded-button px-3 py-2 text-body ${SHAPE[b.alert.level].box}`}>
            <span aria-hidden="true" className="font-bold">{SHAPE[b.alert.level].mark}</span>
            <span><span className="sr-only">{SHAPE[b.alert.level].name} </span>{b.text}</span>
          </p>
        ) : (
          <p key={i} className={bubbleClass(b.from)}>{b.text}</p>
        ))}
        {loading && <p role="status" className="text-caption text-soft">이 단계 설명을 불러오는 중…</p>}
        {busy && <p role="status" className="text-caption text-soft">생각하는 중…</p>}
        <div ref={end} />
      </div>
      <AskForm id="an-ask" label="광고 어시스턴트에게 묻기" suggestions={suggestions} busy={busy} onAsk={(q) => void ask(q)} />
    </section>
  );
}
