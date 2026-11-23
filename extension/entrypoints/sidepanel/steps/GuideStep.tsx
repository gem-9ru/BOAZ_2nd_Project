import { useState } from "react";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { stepsFor } from "../../../lib/guide";
import { ADS_MANAGER_URL, GUIDE } from "../../../lib/guideList";
import { sendWithRetry } from "../../../lib/progress";
import { Coach, ErrorLine, PrimaryButton } from "../ui/Coach";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

const ADS_MANAGER_MATCH = ["https://adsmanager.facebook.com/*", "https://business.facebook.com/*"];

/** ② 안내 / ③ 바꾸기 / 결과 내보내기: 광고 관리자 탭에 캐릭터를 부른다. 진행은 배경 스크립트가 저장소에 쓰고 패널이 따라간다. */
export default function GuideStep({ state, dispatch }: Props) {
  const mode = state.guide?.mode ?? "create";
  // 바꿀 칸: 분석 페이지 코드로 받은 것(plan)이 있으면 그것 하나, 없으면 예전 패널 분석 결과
  const changes = state.plan ? [state.plan.change] : state.result?.changes ?? [];
  const steps = stepsFor(mode, GUIDE, state.settings, changes);
  const index = state.guide?.index ?? 0;
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function open() {
    setBusy(true);
    setError(null);
    // 이미 열린 광고 관리자 탭이 있으면 그 탭으로 (반쯤 채운 초안을 떠나지 않게)
    const [existing] = await browser.tabs.query({ url: ADS_MANAGER_MATCH });
    const tab = existing ?? (await browser.tabs.create({ url: ADS_MANAGER_URL }));
    if (existing?.id) await browser.tabs.update(existing.id, { active: true });
    const ok = await sendWithRetry(() => browser.tabs.sendMessage(tab.id!, { type: "guide:start", steps, startIndex: index }));
    setBusy(false);
    if (!ok) setError("캐릭터를 부르지 못했어요. 광고 관리자 화면이 다 뜬 뒤 다시 시도해 주세요.");
  }

  // 수정 안내 목록에 없는 칸만 바뀌었으면: 탭을 열지 않고 글로 알려 준다.
  if (mode === "edit" && steps.length === 0) {
    return (
      <section className="flex flex-col gap-5">
        <Coach>이 칸들은 광고 관리자에서 직접 바꿔 주세요.</Coach>
        <ul className="flex flex-col gap-2">
          {changes.map((c) => (
            <li key={c.field_id} className="text-[15px]">{c.label} → {c.new}</li>
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

  return (
    <section className="flex flex-col gap-5">
      <Coach>{intro}</Coach>
      <ol className="flex flex-col gap-1.5">
        {steps.map((s, i) => (
          <li
            key={s.entry.id}
            aria-current={i === index ? "step" : undefined}
            className={`text-[13px] flex gap-2 ${i === index ? "font-semibold text-ink" : i < index ? "text-soft line-through" : "text-soft"}`}
          >
            <span className="w-5 text-right">{i < index ? "✓" : i + 1}</span>
            <span>
              {state.settings.find((x) => x.fieldId === s.entry.id)?.label ?? s.entry.fallback.text}
              {s.value ? ` · ${s.value}` : ""}
            </span>
          </li>
        ))}
      </ol>
      {error && <ErrorLine message={error} onRetry={open} />}
      <PrimaryButton onClick={open} busy={busy}>광고 관리자 열기</PrimaryButton>
    </section>
  );
}
