import { useEffect, useRef, useState, type ReactNode } from "react";
import { askAssistant, BadInput, plan as fetchPlan, type AssistantAlert } from "../../../lib/api";
import { ANALYSIS_STEPS, type AnalysisTab } from "../../../lib/analysisTab";
import type { FlowEvent, Plan, Step } from "../../../lib/flow";
import { ADS_MANAGER_URL } from "../../../lib/guideList";
import { AskForm, bubbleClass, useAsk, type Bubble } from "../ui/Chat";
import { Coach, ErrorLine, PrimaryButton, SECONDARY_BUTTON } from "../ui/Coach";
import { isLoginPage } from "./GuideStep";
import { nextMoney } from "./PlanStep";

const SHAPE: Record<AssistantAlert["level"], { mark: string; name: string; box: string }> = {
  block: { mark: "■", name: "차단", box: "border-[1.5px] border-block-line bg-block-bg text-block-ink" },
  warn: { mark: "▲", name: "주의", box: "border-[1.5px] border-warn-line bg-warn-bg text-warn" },
  info: { mark: "●", name: "참고", box: "border-[1.5px] border-info-line bg-info-bg text-info-ink" },
};

const ADS = /^https:\/\/(adsmanager|business)\.facebook\.com\//;

/** 광고 관리자 탭을 앞으로 (없으면 지금 창에 새로 연다). 그 탭에서는 패널이 ③ 결과 화면·뭉치 안내로 바뀐다.
 *  사이드 패널은 창마다 따로라서 지금 창의 탭을 먼저 찾는다 (다른 창으로 넘어가면 이 패널은 분석 화면 그대로). */
async function goAds() {
  // 로그인이 풀려 로그인 화면이 된 광고 관리자 탭도 그 탭으로 친다 (새 탭을 또 열지 않게, GuideStep과 같은 기준)
  const find = async (q: { currentWindow?: boolean }) => (await browser.tabs.query(q).catch(() => [])).find((x) => ADS.test(x.url ?? "") || isLoginPage(x.url));
  const t = (await find({ currentWindow: true })) ?? (await find({}));
  if (t?.id == null) { await browser.tabs.create({ url: ADS_MANAGER_URL }); return; }
  await browser.tabs.update(t.id, { active: true });
  if (t.windowId != null) await browser.windows?.update?.(t.windowId, { focused: true });
}

/** 지금 왼쪽 분석 페이지에서 누를 것 한 줄 (웹 화면의 실제 버튼 이름) */
function todoFor(step: string | null, blocked: boolean, offline: boolean): string {
  if (blocked) return "왼쪽 ■ 차단 알림부터 고쳐 주세요. 고치기 전에는 다음 화면으로 못 가요.";
  if (step === "AN-01" && offline) return "왼쪽 결론 화면의 안내를 따라 주세요.";   // 알림을 못 받아 차단인지 모름 → 없을 수 있는 버튼 이름은 빼고
  if (step === "AN-01") return "왼쪽 결론 카드의 [이 테스트 준비하기 →]를 눌러요.";
  if (step === "AN-05" || step === "AN-06") return "왼쪽에서 세트당 예산·기간을 고르고 [확장 프로그램으로 보내기 →]를 눌러요.";
  return "왼쪽 아래 [준비하기 ▶]를 눌러요.";
}

/** 분석 페이지 옆 광고 어시스턴트 (v4.2 AN-COM ④): 분석 페이지를 크롬 탭에 펼쳐 두면, 이 사이드 패널이 그 단계에 맞춰
 *  알림 말풍선을 먼저, 그다음 이 단계 요약 + 추천 질문 2개를 보여 준다. 질문하면 그 단계 결과(JSON)로만 설명한다.
 *  같은 알림은 처음 나오는 단계에서만 (서버가 단계별로 준다). AN-06 [확장 프로그램으로 보내기]를 누르면 테스트안을 받아 EX-03으로 이어진다. */
export default function AnalysisAssistant({ tab, dispatch, handled, plan, flowStep }: { tab: AnalysisTab; dispatch: (ev: FlowEvent) => void;
  /** 이미 받은 보내기 (저장된 상태). 탭을 오가도 같은 보내기는 다시 받지 않는다 */
  handled?: string;
  /** 받아 둔 테스트안 (보내기를 받았으면 '받았어요' 카드에 쓴다) */
  plan?: Plan | null;
  /** 확장 흐름의 지금 단계: 내보내기 안내는 광고를 켠 뒤 결과를 받기 전(wait·upload)에만 */
  flowStep?: Step }) {
  const [bubbles, setBubbles] = useState<Bubble[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);   // 단계 첫 말을 기다리는 중
  const [sendError, setSendError] = useState<string | null>(null);
  const [gone, setGone] = useState(false);   // 서버가 결과를 못 찾음(다시 켜져 지워짐) → 다시 시도·코드 넣기로는 안 된다
  const [receiving, setReceiving] = useState(false);   // 보내기를 받아 오는 중
  const [offline, setOffline] = useState(false);   // 이 단계 설명·알림을 못 받음
  const [retry, setRetry] = useState(0);
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
      setOffline(false);
      setBubbles((b) => [...b, ...(o.alerts ?? []).map((a) => ({ from: "assistant" as const, text: `${a.text} ${a.todo}`, alert: a })), { from: "assistant", text: o.message }]);
      setSuggestions(o.suggestions ?? []);
    }, () => { setOffline(true); setBubbles((b) => [...b, { from: "assistant", text: "지금은 어시스턴트에 연결하지 못했어요. 분석 페이지의 내용은 그대로 보실 수 있어요." }]); });
  }, [code, step]);

  // AN-06 [확장 프로그램으로 보내기] → 테스트안을 받아 둔다. 받으면 아래 '받았어요' 카드의 버튼 하나로 광고 관리자(EX-03 결과 화면)에 간다
  useEffect(() => {
    if (!code || !tab.send || sent.current === tab.send || handled === tab.send) return;
    const mine = tab.send;
    sent.current = mine;
    setSendError(null);
    setReceiving(true);
    // 답이 오면 '지금 기다리는 보내기'인지 본다: 빨리 두 번 보내면 늦게 온 옛 답(옛 금액)이 새 답을 덮지 않게
    fetchPlan(code).finally(() => { if (sent.current === mine) setReceiving(false); }).then((got) => {
      if (sent.current !== mine) return;
      // 사장님이 ③에서 고른 예산·기간이 있으면 그 값으로 (서버 계획은 기본값 per_set·days)
      const p = { ...got, change: { ...got.change, ...(tab.budget ? { per_set: tab.budget, picked: true } : {}), ...(tab.days ? { days: tab.days } : {}) } };
      dispatch({ type: "planLoaded", plan: p, sent: mine });
    }, (e: Error) => { if (sent.current !== mine) return; sent.current = null; setGone(e instanceof BadInput); setSendError(e.message); });
  }, [code, tab.send, tab.budget, tab.days, dispatch, handled, retry]);

  useEffect(() => { end.current?.scrollIntoView?.({ block: "end" }); }, [bubbles]);

  if (!code) {
    // AN-00 업로드: 아직 결과가 없으면 정해진 안내만 (할 일 한 줄 + 파일이 없을 때 갈 곳)
    return (
      <section aria-label="분석 페이지 어시스턴트" className="flex flex-col gap-3">
        <p className="text-caption font-semibold text-accent-ink">분석 페이지 · 업로드</p>
        <Todo>왼쪽 분석 페이지에 결과 파일(CSV)을 올리고 [분석 시작 ▶]을 눌러요.</Todo>
        <Coach>올려 주시면 다음에 바꿔 볼 칸 1개를 같이 찾아볼게요. 내보내기 전에 표 위 '분석 데이터'에서 <b>일</b>과 <b>노출 위치</b>를 꼭 골라 주세요.</Coach>
        {(flowStep === "wait" || flowStep === "upload") && (   // 결과 화면(plan)에서는 안 띄움: 내보내기 안내와 PlanStep이 겹친다 (새 결과는 [다른 코드 넣기]로)
          <button type="button" onClick={() => { dispatch({ type: "startExport" }); void goAds(); }}
            className={SECONDARY_BUTTON}>파일이 아직 없으면: 광고 관리자에서 내보내기 짚어 주기</button>
        )}
        <details className="rounded-button bg-paper px-3 py-2 text-label">
          <summary className="flex min-h-11 cursor-pointer items-center font-semibold text-accent-ink">CSV는 어디서 받아요?</summary>
          <p className="mt-1">광고 관리자 › 광고 세트 탭 › 표 위 '분석 데이터'에서 '일 · 노출 위치'에 체크한 뒤 내보내기로 CSV를 받아요. 광고가 끝난 뒤 받아야 기간 합계가 맞아요.</p>
        </details>
        <details className="rounded-button bg-paper px-3 py-2 text-label">
          <summary className="flex min-h-11 cursor-pointer items-center font-semibold text-accent-ink">광고 설정은 왜 필요해요?</summary>
          <p className="mt-1">내 광고 설정이 있어야 '내 세팅 카드'에서 칸마다 바꿀지·둘지를 알려 드려요. 확장 프로그램 ② 세팅에서 만든 값은 자동으로 넘어가요.</p>
        </details>
      </section>
    );
  }

  const got = plan && tab.send && handled === tab.send ? plan : null;   // 이번 보내기를 받았음
  const blocked = bubbles.some((b) => b.alert?.level === "block");
  return (
    <section aria-label="분석 페이지 어시스턴트" className="flex flex-col gap-2 rounded-card bg-accent-soft p-3">
      <p className="text-caption font-semibold text-accent-ink">분석 페이지 · {step ? `${ANALYSIS_STEPS[step]} (3단계 중)` : ""}</p>
      {got ? (
        <section aria-label="받은 바꿀 칸" className="flex flex-col gap-2 rounded-card border-2 border-accent bg-paper px-4 py-3">
          <p className="text-label font-semibold text-accent-ink">✓ 바꿀 칸을 받았어요</p>
          <p className="text-caption text-soft">{got.change.path ?? got.change.label}</p>
          <p className="text-body font-bold">{got.change.now ? `${got.change.now} → ` : ""}{(got.change as { new_short?: string }).new_short ?? got.change.new}</p>
          {money(got) && <p className="text-label font-semibold">{money(got)}</p>}
          <p className="text-label">분석은 끝났어요. 이제 광고 관리자에서 다음 테스트를 준비해요. 게시는 사장님이 직접 해요.</p>
          <PrimaryButton onClick={() => void goAds()}>광고 관리자에서 다음 테스트 준비 ▶</PrimaryButton>
        </section>
      ) : sendError && gone ? (
        <div className="rounded-button bg-paper px-3 py-2">
          <ErrorLine message="분석 결과가 서버에서 지워졌어요 (서버를 다시 켜면 지워져요). 왼쪽 분석 페이지에서 파일을 다시 올리고 보내 주세요." />
        </div>
      ) : sendError ? (
        <div className="flex flex-col gap-1 rounded-button bg-paper px-3 py-2">
          <ErrorLine message={`바꿀 칸을 받지 못했어요. ${sendError}`} onRetry={() => setRetry((n) => n + 1)} />
          <p className="text-label">그래도 안 되면 광고 관리자 패널의 '보내기가 안 되면: 코드 6자리로 넣기'에 <b className="tracking-widest">{code}</b>를 넣어 주세요.</p>
        </div>
      ) : <Todo>{receiving ? "보낸 바꿀 칸을 받는 중이에요…" : todoFor(step, blocked, offline)}</Todo>}
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

/** 받은 금액·기간 한 줄: 다음 테스트 화면(PlanStep)과 같은 계산 (메타 하루 최소보다 적으면 올린 금액) */
function money(p: Plan): string {
  const days = (p.change as { days?: number }).days;
  const m = nextMoney(p, []);
  return [m.amount ? `세트당 ${m.amount.toLocaleString()}원` : "", days ? `${days}일` : ""].filter(Boolean).join(" · ");
}

/** 지금 할 일 한 줄 (패널 맨 위 고정) */
function Todo({ children }: { children: ReactNode }) {
  return (
    <p aria-live="polite" className="rounded-button border-2 border-accent bg-paper px-3 py-2 text-body font-semibold">
      <span className="mr-1.5 text-label text-accent-ink">할 일</span>{children}
    </p>
  );
}
