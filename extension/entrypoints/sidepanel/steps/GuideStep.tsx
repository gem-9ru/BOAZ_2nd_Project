import { useEffect } from "react";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { stepsFor } from "../../../lib/guide";
import { ADS_MANAGER_URL, GUIDE } from "../../../lib/guideList";
import { Coach, PrimaryButton } from "../ui/Coach";

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
}

/** ② 안내 / ③ 바꾸기 / 결과 내보내기: 광고 관리자 탭을 열고 캐릭터에게 단계를 넘긴다. 진행은 캐릭터가 알려 준다. */
export default function GuideStep({ state, dispatch }: Props) {
  const mode = state.guide?.mode ?? "create";
  const steps = stepsFor(mode, GUIDE, state.settings, state.result?.changes ?? []);
  const index = state.guide?.index ?? 0;

  useEffect(() => {
    const onMessage = (msg: { type?: string; index?: number }) => {
      if (msg.type === "guide:progress" && typeof msg.index === "number") {
        if (msg.index >= steps.length) dispatch(mode === "export" ? { type: "startUpload" } : { type: "guideDone" });
        else dispatch({ type: "guideProgress", index: msg.index });
      }
    };
    browser.runtime.onMessage.addListener(onMessage);
    return () => browser.runtime.onMessage.removeListener(onMessage);
  }, [steps.length, mode]);

  async function open() {
    const tab = await browser.tabs.create({ url: ADS_MANAGER_URL });
    const send = () => tab.id && browser.tabs.sendMessage(tab.id, { type: "guide:start", steps, startIndex: index }).catch(() => {});
    const onUpdated = (id: number, info: { status?: string }) => {
      if (id === tab.id && info.status === "complete") {
        browser.tabs.onUpdated.removeListener(onUpdated);
        setTimeout(send, 1500);   // 광고 관리자는 화면을 늦게 그린다
      }
    };
    browser.tabs.onUpdated.addListener(onUpdated);
  }

  const intro = {
    create: "광고 관리자를 열면 캐릭터가 칸마다 무엇을 넣을지 알려 드려요. 게시 버튼은 마지막에 직접 눌러 주세요.",
    edit: "바꿀 칸만 캐릭터가 짚어 드려요. 광고 세트를 열어 수정하세요.",
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
      <PrimaryButton onClick={open}>광고 관리자 열기</PrimaryButton>
    </section>
  );
}
