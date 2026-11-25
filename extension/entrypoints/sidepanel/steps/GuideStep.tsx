import { useState } from "react";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { stepsFor } from "../../../lib/guide";
import { ADS_MANAGER_URL, GUIDE } from "../../../lib/guideList";
import { sendWithRetry } from "../../../lib/progress";
import { Coach, PrimaryButton, WarnLine } from "../ui/Coach";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

const isAds = (url?: string) => /^https:\/\/(adsmanager|business)\.facebook\.com\//.test(url ?? "");

/** 뭉치를 보낼 광고 관리자 탭: 지금 창에서 보고 있는 탭 → 다른 광고 관리자 탭 (반쯤 채운 초안을 떠나지 않게). */
async function findAdsTab() {
  const [active] = await browser.tabs.query({ active: true, currentWindow: true }).catch(() => []);
  if (active && isAds(active.url)) return active;
  const all = (await browser.tabs.query({})).filter((t) => isAds(t.url));
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
  const steps = stepsFor(mode, GUIDE, state.settings, changes);
  const index = state.guide?.index ?? 0;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function open() {
    setBusy(true);
    setError(null);
    dispatch({ type: "guideOpened" });   // 뭉치가 집을 나선다
    const tab = await adsTab();
    const send = () => browser.tabs.sendMessage(tab.id!, { type: "guide:start", steps, startIndex: index });
    let ok = await sendWithRetry(send, 2, 800);
    if (!ok && tab.id) {
      // 확장을 다시 불러오기 전에 열린 탭은 뭉치 스크립트가 없다 → 새로고침해서 넣고 다시 부른다
      let reloaded = false;
      try { await browser.tabs.reload(tab.id); reloaded = true; } catch { /* 새로고침 못 함 → 아래 ▲ 안내 */ }
      if (reloaded) ok = await sendWithRetry(send);
    }
    setBusy(false);
    if (!ok) setError("캐릭터를 부르지 못했어요. 광고 관리자 화면이 다 뜬 뒤 다시 시도해 주세요.");
  }

  // [이전 칸] [다음 칸]: 광고 관리자 탭의 캐릭터를 움직인다 (진행은 배경 스크립트가 저장소에 쓴다).
  async function move(delta: 1 | -1) {
    const tab = await findAdsTab();
    if (!tab?.id) { setError("광고 관리자 탭이 없어요. '광고 관리자 열기'를 먼저 눌러 주세요."); return; }
    await browser.tabs.sendMessage(tab.id, { type: "guide:move", delta }).catch(() => setError("캐릭터를 부르지 못했어요. 광고 관리자 화면이 다 뜬 뒤 다시 시도해 주세요."));
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

  const intro = {
    create: "광고 관리자를 열면 캐릭터가 칸마다 무엇을 넣을지 알려 드려요. '동의하고 게시' 버튼은 마지막에 직접 눌러 주세요.",
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
        {steps.map((s, i) => (
          <li
            key={s.entry.id}
            aria-current={i === index ? "step" : undefined}
            className={`text-caption flex gap-2 rounded-button px-2 py-1 ${i === index ? "bg-accent-soft font-semibold text-ink" : i < index ? "text-soft line-through" : "text-soft"}`}
          >
            <span className="w-5 text-right">{i < index ? "✓" : i + 1}</span>
            <span>
              {state.settings.find((x) => x.fieldId === s.entry.id)?.label ?? s.entry.fallback.text}
              {s.value ? ` · ${s.value}` : ""}
            </span>
          </li>
        ))}
      </ol>
      {error && <WarnLine message={error} onRetry={open} />}
      <PrimaryButton onClick={open} busy={busy}>광고 관리자 열기</PrimaryButton>
      <div className="flex gap-2">
        <button type="button" onClick={() => void move(-1)} disabled={index === 0}
          className="flex-1 rounded-button border border-line bg-paper py-2 text-body disabled:opacity-(--state-disabled-opacity)">이전 칸</button>
        <button type="button" onClick={() => void move(1)} disabled={index >= total}
          className="flex-1 rounded-button border border-accent bg-paper py-2 text-body font-semibold text-accent-ink disabled:opacity-(--state-disabled-opacity)">다음 칸</button>
      </div>
    </section>
  );
}
