import { useState } from "react";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { nextTestSteps, stepsFor, type GuideMsg } from "../../../lib/guide";
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

  async function open() {
    setBusy(true);
    setError(null);
    dispatch({ type: "guideOpened" });   // 뭉치가 집을 나선다
    const tab = await adsTab();
    // 처음 쓰는 사장님: 메타가 로그인 화면으로 보낸다 → 로그인은 사장님이 직접, 광고 관리자가 뜨면 이어서 부른다
    if (tab.id && !(await waitForAds(tab, () => { setLogin(true); setBusy(false); }))) {
      setLogin(false);
      setBusy(false);
      setError("광고 관리자 화면이 뜨지 않았어요 → 로그인한 뒤 '광고 관리자 열기'를 다시 눌러 주세요.");
      return;
    }
    setLogin(false);
    setBusy(true);
    const send = () => browser.tabs.sendMessage(tab.id!, { type: "guide:start", steps, startIndex: index, ...(next ? { focus: true } : {}) } satisfies GuideMsg);
    let ok = await sendWithRetry(send, 2, 800);
    if (!ok && tab.id) {
      // 확장을 다시 불러오기 전에 열린 탭은 뭉치 스크립트가 없다 → 새로고침해서 넣고 다시 부른다
      let reloaded = false;
      try { await browser.tabs.reload(tab.id); reloaded = true; } catch { /* 새로고침 못 함 → 아래 ▲ 안내 */ }
      if (reloaded) ok = await sendWithRetry(send);
    }
    setBusy(false);
    if (!ok) setError("캐릭터를 부르지 못했어요 → 광고 관리자 화면이 다 뜬 뒤 다시 시도해 주세요.");
  }

  // [이전 칸] [다음 칸]: 광고 관리자 탭의 캐릭터를 움직인다 (진행은 배경 스크립트가 저장소에 쓴다).
  async function move(delta: 1 | -1) {
    const tab = await findAdsTab();
    if (!tab?.id) { setError("광고 관리자 탭이 없어요 → '광고 관리자 열기'를 먼저 눌러 주세요."); return; }
    await browser.tabs.sendMessage(tab.id, { type: "guide:move", delta } satisfies GuideMsg).catch(() => setError("캐릭터를 부르지 못했어요 → 광고 관리자 화면이 다 뜬 뒤 다시 시도해 주세요."));
  }

  // 수정 안내 목록에 없는 칸만 바뀌었으면: 탭을 열지 않고 글로 알려 준다.
  if (mode === "edit" && steps.length === 0) {
    return (
      <section className="flex flex-col gap-5">
        <Coach>이 칸들은 광고 관리자에서 직접 바꿔 주세요.</Coach>
        <ul className="flex flex-col gap-2">
          {changes.map((c) => (
            <li key={c.field_id} className="text-body">{c.label} → {c.new}</li>
          ))}
        </ul>
        <PrimaryButton onClick={() => dispatch({ type: "guideDone" })}>바꿨어요</PrimaryButton>
      </section>
    );
  }

  const target = next?.send.find((s) => !s.entry.publish && !s.entry.id.startsWith("next."));   // 복제 칸 다음의 바꿀 칸
  const targetLabel = target ? state.settings.find((x) => x.fieldId === target.entry.id)?.label ?? target.entry.fallback.text : "";
  const val = (id: string) => state.settings.find((x) => x.fieldId === id)?.value ?? "";
  const money = `${val("meta.adset.lifetime_budget")} · ${val("meta.adset.start_date")} ~ ${val("meta.adset.end_date")}`;
  const intro = {
    create: next
      ? `다음 테스트 세팅이에요. 지난 광고는 끝났으니 ① 지난 광고 세트를 복제해 새 세트 2개를 만들어요 (하나는 지난번 그대로, 하나는 바꿀 세트). ② 바꿀 세트에서 '${targetLabel}' 칸만 바꿔요. ③ 두 세트 모두 총예산 ${money} 로 맞춰요 (돈이 정한 만큼만 나가게). 그 밖의 칸은 지난번 값 그대로예요. 뭉치가 차례로 짚고, '그대로' 세트의 금액·날짜는 사장님이 직접 맞춰요. '동의하고 게시'는 마지막에 직접 눌러 주세요.`
      : "광고 관리자를 열면 캐릭터가 칸마다 무엇을 넣을지 알려 드려요. '동의하고 게시' 버튼은 마지막에 직접 눌러 주세요.",
    edit: "바꿀 칸만 캐릭터가 짚어 드려요. 광고 관리자에서 지난번 광고 세트나 광고를 열어 수정하세요.",
    export: "광고 관리자에서 결과를 내보내는 곳을 캐릭터가 짚어 드려요.",
  }[mode];

  const total = steps.length;
  return (
    <section className="flex flex-col gap-5">
      <Coach>{intro}</Coach>
      {total > 0 && (
        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between text-caption">
            <span className="font-semibold text-accent-ink">지금 칸</span>
            <span className="tabular-nums text-soft">{Math.min(index + 1, total)} / {total}</span>
          </div>
          <div role="progressbar" aria-label="세팅 진행" aria-valuemin={0} aria-valuemax={total} aria-valuenow={index}
            className="h-2 overflow-hidden rounded-badge bg-sunk">
            <div className="h-full rounded-badge bg-accent transition-[width]" style={{ width: `${(index / total) * 100}%` }} />
          </div>
        </div>
      )}
      <ol className="flex flex-col gap-1.5">
        {shown.map((s, n) => {
          // 다음 테스트 세팅: 보내는 칸(바꿀 칸·게시 확인)만 순서대로, 나머지는 지난번 값으로 끝난 칸
          const i = next ? steps.indexOf(s) : n;
          const done = next ? i < 0 || i < index : i < index;
          const now = i >= 0 && i === index;
          return (
            <li
              key={s.entry.id + s.entry.mode}
              aria-current={now ? "step" : undefined}
              className={`text-caption flex gap-2 rounded-button px-2 py-1 ${now ? "bg-accent-soft font-semibold text-ink" : done ? "text-soft line-through" : "text-soft"}`}
            >
              <span className="w-5 text-right">{done ? "✓" : n + 1}</span>
              <span className="flex flex-col gap-1">
                <span>
                  {state.settings.find((x) => x.fieldId === s.entry.id)?.label ?? s.entry.fallback.text}
                  {s.value ? ` · ${s.value}` : ""}
                  {next && now && !s.entry.publish && <span className="ml-1 rounded-badge bg-accent px-1.5 text-small text-on-accent">지금</span>}
                </span>
                {mode === "create" && !done && <InlineNotice id={s.entry.id} publish={Boolean(s.entry.publish)} state={state} />}
              </span>
            </li>
          );
        })}
      </ol>
      {login && (
        <p role="status" className="rounded-button bg-info-bg px-3 py-2 text-caption text-ink">
          <span aria-hidden="true" className="font-bold text-info">● </span><span className="sr-only">참고 </span>
          광고 관리자 대신 페이스북 로그인 화면이 열렸어요. 그 탭에서 페이스북에 로그인해 주세요 (비밀번호는 사장님이 직접 넣어요). 로그인이 끝나 광고 관리자가 뜨면 뭉치가 이어서 시작해요.
        </p>
      )}
      {error && <WarnLine message={error} onRetry={open} />}
      {mode === "create" && (state.prepMissing?.length ?? 0) > 0 && (
        <div role="status" className="flex flex-col gap-2 rounded-button bg-warn-bg px-3 py-2 text-caption text-warn">
          <span><span aria-hidden="true" className="font-bold">▲ </span><span className="sr-only">주의 </span>
            {state.prepMissing!.join(" · ")}이(가) 아직 없어요 → 없으면 광고를 낼 수 없어요. 준비한 뒤 광고 관리자를 열어 주세요.</span>
          <button type="button" onClick={() => dispatch({ type: "openPrep" })} className="self-start font-semibold underline">준비물 다시 보기</button>
        </div>
      )}
      <PrimaryButton onClick={open} busy={busy} disabled={mode === "create" && (state.prepMissing?.length ?? 0) > 0}>광고 관리자 열기</PrimaryButton>
      <div className="flex gap-2">
        <button type="button" onClick={() => void move(-1)} disabled={index === 0}
          className="flex-1 rounded-button border border-line bg-paper py-2 text-body disabled:opacity-(--state-disabled-opacity)">이전 칸</button>
        <button type="button" onClick={() => void move(1)} disabled={index >= total}
          className="flex-1 rounded-button border border-accent bg-paper py-2 text-body font-semibold text-accent-ink disabled:opacity-(--state-disabled-opacity)">다음 칸</button>
      </div>
    </section>
  );
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
        <span role="status" className="flex gap-1.5 rounded-button bg-warn-bg px-2 py-1 text-warn">
          <span aria-hidden="true" className="font-bold">▲</span><span className="sr-only">주의</span>
          <span>총예산 {won(budget)}이 '하루 최소 약 {won(META_DAILY_MIN)} × {days}일 = 약 {won(least)}'보다 적어요 → 광고가 안 나갈 수 있어요. {each}{won(least)} 이상으로 넣거나 기간을 줄여 주세요.</span>
        </span>
      );
    }
    if (id === BUDGET) return null;
    return (
      <span className="flex gap-1.5 rounded-button bg-info-bg px-2 py-1 text-ink">
        <span aria-hidden="true" className="font-bold text-info">●</span><span className="sr-only">참고</span>
        <span>총예산이 '하루 최소 약 {won(META_DAILY_MIN)} × {days}일 = 약 {won(least)}'보다 적으면 광고가 안 나갈 수 있어요 → {each}그 이상으로 넣어 주세요.</span>
      </span>
    );
  }
  if (publish) {
    const empty = REQUIRED.map((f) => state.settings.find((x) => x.fieldId === f)).filter((x) => x && !x.value.trim());
    if (!empty.length) return null;
    return (
      <span role="status" className="flex gap-1.5 rounded-button bg-warn-bg px-2 py-1 text-warn">
        <span aria-hidden="true" className="font-bold">▲</span><span className="sr-only">주의</span>
        <span>{empty.map((x) => x!.label).join(" · ")} 칸이 비어 있어요 → 채운 뒤 게시해 주세요.</span>
      </span>
    );
  }
  return null;
}
