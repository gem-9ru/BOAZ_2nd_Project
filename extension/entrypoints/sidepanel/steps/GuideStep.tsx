import { useState } from "react";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { groupOf, guideSignature, nextTestSteps, stepsFor, type GuideMsg, type GuideStepItem, shownDates } from "../../../lib/guide";
import { ADS_MANAGER_URL, GUIDE } from "../../../lib/guideList";
import { sendWithRetry } from "../../../lib/progress";
import { Coach, PrimaryButton, WarnLine } from "../ui/Coach";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

import { META_DAILY_MIN, minBudget, parseWon } from "../../../lib/settings";
export { META_DAILY_MIN };
const BUDGET = "meta.adset.lifetime_budget";
/** 게시 직전에 비어 있으면 안 되는 칸 */
const REQUIRED = ["meta.creative.copy.text", "meta.creative.copy.headline", "meta.ad.website_url"];
const won = (n: number) => `${Math.round(n).toLocaleString()}원`;

/** 종료 날짜까지 며칠 (오늘 포함). 날짜가 아니면 null. */
export function daysUntil(end: string | undefined, today: Date = new Date()): number | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})(?: \d{2}:\d{2})?$/.exec(end ?? "");   // 시각이 붙어 있어도 날짜로 셈
  if (!m) return null;
  const a = Date.UTC(today.getFullYear(), today.getMonth(), today.getDate());
  const b = Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  const d = Math.round((b - a) / 86400000) + 1;
  return d > 0 ? d : null;
}

/** 페이스북 로그인·본인 확인 화면: 처음 쓰는 사장님이 광고 관리자를 열면 메타가 먼저 이리로 보낸다 */
export const isLoginPage = (url?: string) =>
  /^https:\/\/([a-z]+\.)?facebook\.com\/(login|business\/loginpage|checkpoint|two_step_verification|recover)/.test(url ?? "");
const isAds = (url?: string) => /^https:\/\/(adsmanager|business)\.facebook\.com\//.test(url ?? "") && !isLoginPage(url);
const LOGIN_WAIT_MS = 15 * 60 * 1000;   // 로그인(본인 확인 포함)을 기다리는 가장 긴 시간

/** 탭이 광고 관리자 화면이 될 때까지 기다린다. 로그인 화면이면 onLogin을 한 번 부르고 계속 기다린다. 탭이 닫히거나 너무 오래면 false */
async function waitForAds(tab: { id?: number; url?: string; status?: string }, onLogin: () => void): Promise<boolean> {
  const end = Date.now() + LOGIN_WAIT_MS;
  let told = false;
  for (let first = true; Date.now() < end; first = false) {
    // 처음 한 번은 방금 찾은 탭 정보로도 본다 (탭을 다시 못 읽으면). 그 뒤 못 읽으면 탭이 닫힌 것
    const t = (await browser.tabs.get(tab.id!).catch(() => null)) ?? (first ? tab : null);
    if (!t) return false;
    if (isAds(t.url) && t.status !== "loading") return true;
    if (!told && isLoginPage(t.url)) { told = true; onLogin(); }
    await new Promise((r) => setTimeout(r, 1000));
  }
  return false;
}

/** 뭉치를 보낼 광고 관리자 탭: 지금 창에서 보고 있는 탭 → 다른 광고 관리자 탭 (반쯤 채운 초안을 떠나지 않게). */
async function findAdsTab() {
  const [active] = await browser.tabs.query({ active: true, currentWindow: true }).catch(() => []);
  if (active && isAds(active.url)) return active;
  if (active && isLoginPage(active.url)) return active;   // 아까 연 광고 관리자가 로그인 화면으로 넘어가 있음
  const all = (await browser.tabs.query({})).filter((t) => isAds(t.url) || isLoginPage(t.url));
  return all.find((t) => t.active) ?? all[0];
}

async function adsTab() {
  const found = await findAdsTab();
  if (!found) return browser.tabs.create({ url: ADS_MANAGER_URL });
  if (found.id && !found.active) await browser.tabs.update(found.id, { active: true });
  return found;
}

/** ② 안내 / ③ 바꾸기 / 결과 내보내기: 광고 관리자 탭에 캐릭터를 부른다. 진행은 배경 스크립트가 저장소에 쓰고 패널이 따라간다. */
export default function GuideStep({ state, dispatch }: Props) {
  const mode = state.guide?.mode ?? "create";
  // 바꿀 칸: 분석 페이지에서 코드로 받은 것 하나
  const changes = state.plan ? [state.plan.change] : [];
  // EX-03 [다음 테스트 세팅]: 목록은 ② 세팅 전체, 캐릭터는 바꿀 칸 + 게시 직전 확인만 짚는다 (index는 그 안에서)
  const next = mode === "create" && state.guide?.next ? nextTestSteps(GUIDE, state.settings, state.guide.next) : null;
  const shown = next ? next.all : stepsFor(mode, GUIDE, state.settings, changes);
  const steps = next ? next.send : shown;
  const index = state.guide?.index ?? 0;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [login, setLogin] = useState(false);   // 로그인 화면에서 사장님을 기다리는 중
  const away = Boolean(state.guide?.away);   // 뭉치가 광고 관리자에 나가 있음

  async function open() {
    if (busy || login) return;   // 기다리는 동안 다시 부르면 기다림이 두 번 돌고 뭉치를 두 번 부른다 (재검토 A3)
    setBusy(true);
    setError(null);
    const tab = await adsTab();
    // 처음 쓰는 사장님: 메타가 로그인 화면으로 보낸다 → 로그인은 사장님이 직접, 광고 관리자가 뜨면 이어서 부른다
    if (tab.id && !(await waitForAds(tab, () => { setLogin(true); setBusy(false); }))) {
      setLogin(false);
      setBusy(false);
      dispatch({ type: "guideClosed" });   // 뭉치가 못 나갔다 → 집으로 (화면 검토 10)
      setError(`광고 관리자 화면이 뜨지 않았어요 → 로그인한 뒤 '${away ? "뭉치 다시 부르기" : "광고 관리자 열기"}'를 다시 눌러 주세요.`);
      return;
    }
    setLogin(false);
    setBusy(true);
    // 광고 관리자가 뜬 뒤에야 '나가 있음' (로그인 기다리는 동안엔 [광고 관리자 열기]가 '기다리는 중'으로 남게, 재검토 A3)
    // sig: 이번에 보내는 안내 표시 — 예전 뭉치의 진행은 배경이 버린다 (재검토 B9)
    const sig = `${guideSignature(steps)}@${Date.now()}`;
    dispatch({ type: "guideOpened", sig });   // 뭉치가 집을 나선다
    // fromNest: 집에 있던 뭉치가 지금 막 둥지를 나섰을 때만 (이미 나가 있었거나 새로고침 뒤 다시 부를 땐 기다리지 않음)
    let fromNest = !away;
    const send = () => browser.tabs.sendMessage(tab.id!, { type: "guide:start", steps, startIndex: index, sig, ...(next ? { focus: true } : {}), ...(fromNest ? { fromNest: true } : {}) } satisfies GuideMsg);
    let ok = await sendWithRetry(send, 2, 800);
    if (!ok && tab.id) {
      // 확장을 다시 불러오기 전에 열린 탭은 뭉치 스크립트가 없다 → 새로고침해서 넣고 다시 부른다
      let reloaded = false;
      try { await browser.tabs.reload(tab.id); reloaded = true; } catch { /* 새로고침 못 함 → 아래 ▲ 안내 */ }
      fromNest = false;
      if (reloaded) ok = await sendWithRetry(send);
    }
    setBusy(false);
    if (!ok) setError("뭉치를 부르지 못했어요 → 광고 관리자 화면이 다 뜬 뒤 다시 시도해 주세요.");
  }

  // 목록에서 지난 칸을 누르면 뭉치를 그 칸으로 (설계서 EX-01 ②)
  async function goTo(i: number) {
    const tab = await findAdsTab();
    if (!tab?.id) { setError("광고 관리자 탭이 닫혔어요 → '뭉치 다시 부르기'를 눌러 주세요."); return; }
    await browser.tabs.sendMessage(tab.id, { type: "guide:goto", index: i } satisfies GuideMsg).catch(() => setError("뭉치를 부르지 못했어요 → 광고 관리자 화면이 다 뜬 뒤 다시 시도해 주세요."));
  }

  // [이전 칸] [다음 칸]: 광고 관리자 탭의 캐릭터를 움직인다 (진행은 배경 스크립트가 저장소에 쓴다).
  async function move(delta: 1 | -1) {
    // 게시 칸에서 [다음 칸]은 게시하지 않았는데 '끝남'으로 넘어간다 → 막는다 (감사 14)
    if (delta > 0 && steps[index]?.entry.publish) {
      setError("게시는 사장님이 직접 '동의하고 게시'를 누른 뒤, 뭉치 말풍선의 [게시했어요]를 눌러 주세요.");
      return;
    }
    const tab = await findAdsTab();
    if (!tab?.id) { setError("광고 관리자 탭이 닫혔어요 → '뭉치 다시 부르기'를 눌러 주세요."); return; }
    await browser.tabs.sendMessage(tab.id, { type: "guide:move", delta } satisfies GuideMsg).catch(() => setError("뭉치를 부르지 못했어요 → 광고 관리자 화면이 다 뜬 뒤 다시 시도해 주세요."));
  }

  const target = next?.send.find((s) => s.entry.id === state.guide?.next);   // 바꿀 칸 (앞에 복제·예산 공유 끄기 칸이 올 수 있음)
  const targetLabel = target ? state.settings.find((x) => x.fieldId === target.entry.id)?.label ?? target.entry.fallback.text : "";
  const val = (id: string) => state.settings.find((x) => x.fieldId === id)?.value ?? "";
  const money = shownDates(`${val("meta.adset.lifetime_budget")} · ${val("meta.adset.start_date")} ~ ${val("meta.adset.end_date")}`);
  const intro = {
    create: next
      ? `다음 테스트 세팅이에요. 지난 광고는 끝났으니 ① 지난 광고 세트를 복제해 새 세트 2개를 만들어요 (하나는 지난번 그대로, 하나는 바꿀 세트). ② 바꿀 세트에서 '${targetLabel}' 칸만 바꿔요. ③ 두 세트 모두 총예산 ${money} 로 맞춰요 (돈이 정한 만큼만 나가게). 그 밖의 칸은 지난번 값 그대로예요. 뭉치가 차례로 짚고, '그대로' 세트의 금액·날짜는 사장님이 직접 맞춰요. '동의하고 게시'는 마지막에 직접 눌러 주세요.`
      : "광고 관리자를 열면 뭉치가 칸마다 무엇을 넣을지 알려 드려요. '동의하고 게시' 버튼은 마지막에 직접 눌러 주세요.",
    edit: "바꿀 칸만 뭉치가 짚어 드려요. 광고 관리자에서 지난번 광고 세트나 광고를 열어 수정하세요.",
    export: "광고 관리자에서 결과를 내보내는 곳을 뭉치가 짚어 드려요.",
  }[mode];

  const total = steps.length;
  return (
    <section className="flex flex-col gap-5">
      <Coach>{intro}</Coach>
      {total > 0 && (
        <div className="flex flex-col gap-2">
          <div className="flex items-baseline justify-between text-caption font-bold">
            <span>지금 채우는 칸</span>
            <span className="tabular-nums font-semibold text-soft">{Math.min(index + 1, total)} / {total}</span>
          </div>
          {/* 진행 막대: 보라로 채우고 지금 자리에 뭉치 배 색 점 (꾸미기안_뭉치 .prog) */}
          <div role="progressbar" aria-label="세팅 진행" aria-valuemin={0} aria-valuemax={total} aria-valuenow={index}
            className="relative h-2.5 rounded-badge bg-sunk">
            <div className="h-full rounded-badge bg-linear-90 from-accent-line to-accent transition-[width]" style={{ width: `${(index / total) * 100}%` }} />
            <span aria-hidden="true" className="absolute top-1/2 size-4.5 -translate-x-1/2 -translate-y-1/2 rounded-badge border-3 border-paper bg-belly-strong shadow-raised transition-[left]" style={{ left: `${(index / total) * 100}%` }} />
          </div>
        </div>
      )}
      <ol className="flex flex-col gap-1">
        {shown.map((s, n) => {
          // 다음 테스트 세팅: 보내는 칸(바꿀 칸·게시 확인)만 순서대로, 나머지는 지난번 값으로 끝난 칸
          const i = next ? steps.indexOf(s) : n;
          const done = next ? i < 0 || i < index : i < index;
          const now = i >= 0 && i === index;
          const group = groupOf(s.entry.id);
          const newGroup = group && group !== groupOf(shown[n - 1]?.entry.id);
          const label = state.settings.find((x) => x.fieldId === s.entry.id)?.label ?? s.entry.fallback.text;
          const publish = Boolean(s.entry.publish);
          return (
            <li key={`${s.entry.id}${s.entry.mode}${n}`} aria-current={now ? "step" : undefined} className="flex flex-col">   {/* 다음 테스트는 돈 확인 칸이 두 번 들어간다 (화면 검토 26) */}
              {newGroup && <p aria-hidden="true" className="mt-2 mb-1 flex items-center gap-1.5 px-0.5 text-small font-bold text-soft after:h-px after:flex-1 after:bg-line">{group}</p>}
              <div className={`flex items-center gap-2.5 rounded-button text-caption ${now ? "border-2 border-accent bg-paper p-2.5 shadow-raised" : publish ? "mt-1 border-2 border-dashed border-warn-mark/60 bg-warn-bg px-2.5 py-1.5" : "px-2.5 py-1"}`}>
                {publish && !done
                  ? <span aria-hidden="true" className="inline-grid size-5.5 shrink-0 place-items-center pt-1 text-mark font-bold text-on-accent bg-warn-mark [clip-path:polygon(50%_0,100%_100%,0_100%)]">!</span>
                  : <span aria-hidden="true" className={`inline-grid size-5.5 shrink-0 place-items-center rounded-badge border-2 text-small font-bold ${done ? "border-ok bg-ok text-on-accent" : now ? "border-accent bg-accent text-on-accent" : "border-line bg-paper text-soft"}`}>{done ? "✓" : n + 1}</span>}
                <span className="flex min-w-0 flex-1 flex-col gap-1">
                  <span className="flex items-center gap-1.5">
                    {away && i >= 0 && i < index
                      ? <button type="button" onClick={() => void goTo(i)} className="min-h-11 text-left text-soft underline decoration-dotted" aria-label={`${label}: 뭉치를 이 칸으로 보내기`}>{label}<span className="sr-only"> (끝남)</span></button>
                      : <span className={publish ? "font-semibold text-warn" : now ? "font-bold text-ink" : done && i >= 0 ? "text-soft line-through" : "text-soft"}>{publish && !done ? `${n + 1} · ${label}` : label}{done && <span className="sr-only"> (끝남)</span>}</span>}
                    {now && !publish && <span className="rounded-badge bg-accent px-1.5 text-small font-bold text-on-accent">지금</span>}
                    {!done && isOwnerStep(steps.find((x) => x.entry.id === s.entry.id) ?? s) && <span className="rounded-badge border border-accent px-1.5 text-small text-accent-ink">직접</span>}
                    {s.value && <span className={`ml-auto max-w-48 truncate text-right font-semibold ${now ? "text-accent" : "text-ink"}`}>{shownDates(s.value)}</span>}
                  </span>
                  {mode === "create" && !done && <InlineNotice id={s.entry.id} publish={publish} state={state} />}
                </span>
              </div>
            </li>
          );
        })}
      </ol>
      {login && (
        <p role="status" className="rounded-soft border-[1.5px] border-info-line bg-info-bg px-3 py-2 text-caption text-info-ink">
          <span aria-hidden="true" className="font-bold text-info">● </span><span className="sr-only">참고 </span>
          광고 관리자 대신 페이스북 로그인 화면이 열렸어요. 그 탭에서 페이스북에 로그인해 주세요 (비밀번호는 사장님이 직접 넣어요). 로그인이 끝나 광고 관리자가 뜨면 뭉치가 이어서 시작해요.
        </p>
      )}
      {error && <WarnLine message={error} onRetry={open} />}
      {mode === "create" && (state.prepMissing?.length ?? 0) > 0 && (
        <div role="status" className="flex flex-col gap-2 rounded-soft border-[1.5px] border-warn-line bg-warn-bg px-3 py-2 text-caption text-warn">
          <span><span aria-hidden="true" className="font-bold">▲ </span><span className="sr-only">주의 </span>
            {state.prepMissing!.join(" · ")}이(가) 아직 없어요 → 없으면 광고를 낼 수 없어요. 준비한 뒤 광고 관리자를 열어 주세요.</span>
          <button type="button" onClick={() => dispatch({ type: "openPrep" })} className="self-start font-semibold underline">준비물 다시 보기</button>
        </div>
      )}
      {away && <p className="text-small text-soft">지난 칸 이름을 누르면 뭉치가 그 칸으로 가요.</p>}
      {/* 설계서 EX-01 ⑥: 뭉치가 광고 관리자에 나가 있으면 [이전 칸][다음 칸], 아니면 [광고 관리자 열기] 하나만.
          긴 칸 목록 아래로 밀려 안 보이지 않게 패널 아래에 붙여 둔다 */}
      <div className="sticky bottom-0 z-10 flex flex-col gap-2 bg-cream py-2">
        {!away ? <>
          {/* 로그인을 기다리는 동안은 다시 누르지 못하게: 기다림이 두 번 돌면 뭉치를 두 번 부르거나 늦게 오류가 뜬다 (화면 검토 10) */}
          <PrimaryButton onClick={open} busy={busy} disabled={login || (mode === "create" && (state.prepMissing?.length ?? 0) > 0)}>
            {login ? "로그인을 기다리는 중…" : <>광고 관리자 열기 <span aria-hidden="true" className="opacity-80">↗</span></>}
          </PrimaryButton>
          <p className="text-center text-small text-soft">어시스턴트는 결제·게시를 대신 누르지 않아요</p>
        </> : <div className="flex gap-2">
          <button type="button" onClick={() => void move(-1)} disabled={index === 0}
            className="min-h-11 flex-1 rounded-button border border-line bg-paper py-2 text-body focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-default disabled:border-disabled-line disabled:bg-disabled-bg disabled:text-disabled-fg disabled:shadow-none">이전 칸</button>
          <button type="button" onClick={() => void move(1)} disabled={index >= total}
            className="min-h-11 flex-1 rounded-button border border-accent bg-paper py-2 text-body font-semibold text-accent-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-default disabled:border-disabled-line disabled:bg-disabled-bg disabled:text-disabled-fg disabled:shadow-none">다음 칸</button>
        </div>}
      </div>
      {mode === "export" && (
        // 뭉치 없이 파일을 받았거나 뭉치를 닫았어도 다음 화면(분석 페이지 열기·코드 넣기)으로 갈 수 있게 (화면 검토 22)
        <button type="button" onClick={() => dispatch({ type: "closeExport" })} className="min-h-11 self-start text-label text-accent-ink underline">← 파일을 받았어요 · 돌아가기</button>
      )}
      {next && state.beforeNext && (
        // 다음 테스트를 누른 뒤 마음이 바뀌면: 지난 세팅·날짜·금액으로 되돌리고 결과 화면으로
        <button type="button" onClick={() => dispatch({ type: "backToPlan" })} className="min-h-11 self-start text-label text-accent-ink underline">← 결과 화면으로 돌아가기</button>
      )}
      {away && (
        // 탭을 닫았거나 뭉치가 안 보이면 다시 부른다
        <button type="button" onClick={open} disabled={busy || login} className="min-h-11 self-start text-label text-accent-ink underline disabled:text-disabled-fg disabled:no-underline">{login ? "로그인을 기다리는 중…" : "뭉치 다시 부르기"}</button>
      )}
      {index > 0 && (
        // 초안을 지웠거나 다시 만들 때: 1번 칸으로 (뭉치는 [광고 관리자 열기]로 다시 부른다)
        // 뭉치가 나가 있으면 뭉치에게도 1번 칸으로 가라고 알린다 (패널 번호만 바꾸면 다음 움직임에 되돌아감, 재검토 A7)
        <button type="button" onClick={() => { dispatch({ type: "guideProgress", index: 0 }); if (away) void goTo(0); }} className="min-h-11 self-start text-label text-accent-ink underline">뭉치 안내만 1번 칸부터 (답은 그대로)</button>
      )}
      {mode === "create" && !next && (
        // 기간·금액·지역·클릭 주소를 바꾸려면 ② 질문으로 (① 찾기·문구·준비물 답은 그대로, 날짜는 오늘 기준으로 다시, 화면 검토 9)
        <button type="button" onClick={() => dispatch({ type: "editAnswers" })} className="min-h-11 self-start text-label text-accent-ink underline">← ② 답 바꾸기 (기간·금액·지역·클릭 주소)</button>
      )}
    </section>
  );
}

/** 사장님이 직접 할 칸 (안내 목록에 '직접'): 사장님 칸, 하위 단계가 모두 사장님 차례인 칸 */
function isOwnerStep(s: GuideStepItem): boolean {
  return s.entry.auto === "owner" && (s.entry.stages ?? []).every((st) => st.by === "owner");
}

/** EX-01 ④ 세팅 중 알림 (인라인, v4.2): 이유 → 할 일, 금액은 '원'.
 *  - 종료 날짜: 총예산이 '하루 최소 × 기간'보다 적으면 광고가 안 나갈 수 있어요 (오븐로그 11/17)
 *  - 게시 직전 확인: 꼭 채워야 할 칸이 비어 있으면 ▲ */
function InlineNotice({ id, publish, state }: { id: string; publish: boolean; state: FlowState }) {
  if (id === "meta.adset.end_date" || id === BUDGET) {
    // 기간은 시작일부터 (예약 광고면 시작일, 아니면 오늘)
    const start = /^(\d{4})-(\d{2})-(\d{2})$/.exec(state.startDate ?? "");
    const from = start ? new Date(Number(start[1]), Number(start[2]) - 1, Number(start[3])) : new Date();
    const days = daysUntil(state.settings.find((x) => x.fieldId === "meta.adset.end_date")?.value, from > new Date() ? from : new Date());
    if (!days) return null;
    // 총예산을 ② 세팅에서 받았으면 실제로 견줘 본다: 모자라면 ▲, 넉넉하면 알림 없음. 못 받았으면 ● 참고 안내
    const budget = parseWon(state.settings.find((x) => x.fieldId === BUDGET)?.value);
    const least = minBudget(days);
    const each = state.guide?.next ? "세트마다 " : "총예산을 ";   // 다음 테스트는 세트 2개라 세트당 금액, 처음엔 세트 1개라 총액
    if (budget !== null) {
      if (budget >= least) return null;
      return (
        <span role="status" className="flex gap-1.5 rounded-soft border-[1.5px] border-warn-line bg-warn-bg px-2 py-1 text-warn">
          <span aria-hidden="true" className="font-bold">▲</span><span className="sr-only">주의</span>
          <span>총예산 {won(budget)}이 '하루 최소 약 {won(META_DAILY_MIN)} × {days}일 = 약 {won(least)}'보다 적어요 → 광고가 안 나갈 수 있어요. {each}{won(least)} 이상으로 넣거나 기간을 줄여 주세요.</span>
        </span>
      );
    }
    if (id === BUDGET) return null;
    return (
      <span className="flex gap-1.5 rounded-soft border-[1.5px] border-info-line bg-info-bg px-2 py-1 text-info-ink">
        <span aria-hidden="true" className="font-bold text-info">●</span><span className="sr-only">참고</span>
        <span>총예산이 '하루 최소 약 {won(META_DAILY_MIN)} × {days}일 = 약 {won(least)}'보다 적으면 광고가 안 나갈 수 있어요 → {each}그 이상으로 넣어 주세요.</span>
      </span>
    );
  }
  if (publish) {
    const empty = REQUIRED.map((f) => state.settings.find((x) => x.fieldId === f)).filter((x) => x && !x.value.trim());
    // 결제 카드는 게시할 때만 필요해서 [광고 관리자 열기]는 막지 않고, 게시 칸에서 알린다 (meta_fields.yaml payment why, 화면 검토 3)
    const noCard = state.answers["meta.pre.payment"] === "아직이에요";
    if (!empty.length && !noCard) return null;
    return (
      <span role="status" className="flex gap-1.5 rounded-soft border-[1.5px] border-warn-line bg-warn-bg px-2 py-1 text-warn">
        <span aria-hidden="true" className="font-bold">▲</span><span className="sr-only">주의</span>
        <span>
          {empty.length > 0 && `${empty.map((x) => x!.label).join(" · ")} 칸이 비어 있어요 → 채운 뒤 게시해 주세요. `}
          {noCard && "결제 카드가 아직 없어요 → 메타 결제 설정에서 카드를 등록해야 게시돼요 (카드 정보는 사장님이 직접 넣어요)."}
        </span>
      </span>
    );
  }
  return null;
}
