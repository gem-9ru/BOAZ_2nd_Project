import { josa } from "../../../lib/josa";
import type { Field } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { prepFields, prepMissing } from "../../../lib/settings";
import { Coach, PrimaryButton } from "../ui/Coach";
import { useState } from "react";
import { Question, TEXT_BUTTON } from "./QuestionStep";

/** 시작 전 준비물: ① 찾기 앞에서 광고에 꼭 필요한 것(로그인·페이지·결제 수단)과 있으면 좋은 것(사진·주소·언어)을 한 칸씩 확인.
 *  없다고 하면 그 자리에서 만드는 법·링크를 보여 준다 (질문 칸 사양은 meta_fields.yaml stage '사전 점검').
 *  꼭 필요한 것이 빠져도 ① 찾기·② 문구는 할 수 있고, [광고 관리자 열기]만 막는다. */
export default function PrepStep({ state, dispatch, fields }: { state: FlowState; dispatch: (ev: FlowEvent) => void; fields: Field[] }) {
  const items = prepFields(fields);
  const next = items.find((f) => !(f.id in state.answers));
  const index = next ? items.indexOf(next) : items.length;
  const missing = prepMissing(fields, state.answers);
  const back = state.settings.length > 0;   // 세팅 목록에서 다시 보러 옴
  const [helpFirst, setHelpFirst] = useState<{ id: string; answer: string } | null>(null);   // [만드는 법 보기]로 돌아간 칸

  return (
    <section className="flex flex-col gap-5">
      {index === 0 && (
        <Coach avatar={false}>안녕하세요, 광고 세팅을 같이 할 뭉치예요. 시작하기 전에 준비물을 확인할게요 (2분). 없는 게 있으면 만드는 방법을 바로 알려 드려요. 예산과 기간은 뒤에서 같이 정해요.</Coach>
      )}
      {next ? (
        <>
          <p className="text-caption text-soft">준비물 {index + 1} / {items.length}{next.required ? " · 꼭 필요해요" : ""}</p>
          {index > 0 && (
            <button type="button" onClick={() => dispatch({ type: "unanswer", id: items[index - 1]!.id })} className={TEXT_BUTTON}>
              ← 이전 준비물
            </button>
          )}
          <Question key={next.id} field={next} startHelp={helpFirst?.id === next.id ? helpFirst.answer : undefined} answers={state.answers} keywords={state.keywords} checked={state.checks?.[next.id] ?? []}
            onCheck={(i) => dispatch({ type: "toggleCheck", key: next.id, index: i })}
            onAnswer={(value, extra = {}) => {
              dispatch({ type: "answer", id: next.id, value });
              for (const [k, v] of Object.entries(extra)) dispatch({ type: "answer", id: k, value: v });
            }} />
        </>
      ) : (
        <>
          {/* 세팅 목록에서 [준비물 다시 보기]로 왔으면 그 목록으로 돌아간다는 말 (QA 목록 밖) */}
          <Coach>{missing.length === 0
            ? (back ? "준비물이 다 있어요. 세팅 목록으로 돌아갈게요." : "준비물이 다 있어요. 이제 무엇을 파는지부터 같이 볼게요.")
            : `${missing.join(" · ")}${josa(missing[missing.length - 1]!, "은", "는")} 광고 관리자에 들어가기 전에 꼭 있어야 해요. ${back ? "준비한 뒤 세팅 목록에서 광고 관리자를 열어 주세요." : "상품 찾기와 문구는 먼저 해 두실 수 있어요."}`}</Coach>
          <ul className="flex flex-col gap-2">
            {items.map((f) => {
              const ok = state.answers[f.id] === f.options?.[0] || (f.options == null && Boolean(state.answers[f.id]));
              return (
                <li key={f.id} className="flex items-start justify-between gap-3 rounded-button bg-paper px-3 py-2 text-body">
                  <span>
                    <span aria-hidden className={ok ? "text-accent-ink" : f.required ? "text-warn" : "text-soft"}>{ok ? "✓ " : f.required ? "▲ " : "· "}</span>
                    <span className="sr-only">{ok ? "됨" : f.required ? "꼭 필요한데 아직 안 됨" : "아직 안 됨"} </span>
                    {f.label}
                    <span className="block text-caption text-soft">{state.answers[f.id] || "비워 둠"}</span>
                  </span>
                  {!ok && f.required && f.help?.[state.answers[f.id] ?? ""] ? (
                    <button type="button" onClick={() => { setHelpFirst({ id: f.id, answer: state.answers[f.id]! }); dispatch({ type: "unanswer", id: f.id }); }}
                      className="inline-flex min-h-11 shrink-0 items-center rounded-button border border-accent px-3 text-caption font-semibold text-accent-ink">만드는 법 보기</button>
                  ) : (
                    <button type="button" onClick={() => dispatch({ type: "unanswer", id: f.id })} className={`shrink-0 ${TEXT_BUTTON}`}>다시 답하기</button>
                  )}
                </li>
              );
            })}
          </ul>
          <PrimaryButton onClick={() => dispatch({ type: "prepDone", missing })}>{back ? "세팅 목록으로" : "시작할게요"}</PrimaryButton>
        </>
      )}
    </section>
  );
}
