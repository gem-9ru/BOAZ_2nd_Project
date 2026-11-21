import { useState } from "react";
import type { Field, PresetField } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { askedFields, buildSettings, endDateFrom } from "../../../lib/settings";
import { Coach, PrimaryButton } from "../ui/Coach";

const REQUIRED_TEXT = new Set(["meta.ad.website_url"]);

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
  fields: Field[];
  defaults: PresetField[];
}

/** ② 질문: 한 번에 하나씩. 다 답하면 광고 관리자에 넣을 세팅값 목록을 만든다. */
export default function QuestionStep({ state, dispatch, fields, defaults }: Props) {
  const asked = askedFields(fields);
  const next = asked.find((f) => !(f.id in state.answers));
  const index = next ? asked.indexOf(next) : asked.length;

  function answer(id: string, value: string) {
    dispatch({ type: "answer", id, value });
    const answers = { ...state.answers, [id]: value };
    if (asked.every((f) => f.id in answers) && state.target && state.copy) {
      const endDate = endDateFrom(answers["meta.adset.end_date"] ?? "14일");
      dispatch({ type: "questionsDone", settings: buildSettings(fields, answers, state.target, state.copy, endDate), endDate });
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <p className="text-[13px] text-soft">질문 {Math.min(index + 1, asked.length)} / {asked.length}</p>
      {next && <Question key={next.id} field={next} onAnswer={(v) => answer(next.id, v)} />}
      {defaults.length > 0 && (
        <details className="text-[13px] text-soft">
          <summary className="cursor-pointer">묻지 않고 이렇게 두었어요 ({defaults.length}칸)</summary>
          <ul className="mt-2 flex flex-col gap-2">
            {defaults.map((d) => (
              <li key={d.id}>
                <span className="text-ink">{d.label}: {d.default}</span> — {d.why}
              </li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}

function Question({ field, onAnswer }: { field: Field; onAnswer: (v: string) => void }) {
  const [text, setText] = useState(field.default ?? "");
  return (
    <div className="flex flex-col gap-3">
      <Coach>
        <h2 className="text-[17px] font-semibold">{field.ask}</h2>
        {field.why && <p className="text-[13px] text-soft mt-1">{field.why}</p>}
      </Coach>
      {field.options ? (
        <div className="flex flex-col gap-2">
          {field.options.map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => onAnswer(o)}
              className={`rounded-xl border px-4 py-3 text-left text-[15px] ${o === field.default ? "border-ink bg-paper font-semibold" : "border-line"}`}
            >
              {o}
              {o === field.default && <span className="block text-[13px] font-normal text-soft">권장</span>}
            </button>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <label htmlFor={field.id} className="text-[13px] text-soft">{field.label}</label>
          <input
            id={field.id}
            value={text}
            onChange={(e) => setText(e.target.value)}
            className="rounded-xl border border-line bg-paper px-3 py-2.5 text-[15px]"
          />
          <PrimaryButton onClick={() => onAnswer(text.trim())} disabled={REQUIRED_TEXT.has(field.id) && !text.trim()}>
            다음
          </PrimaryButton>
        </div>
      )}
    </div>
  );
}
