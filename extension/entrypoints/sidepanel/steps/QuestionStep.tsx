import { useState } from "react";
import type { Field, OptionHelp, PresetField } from "../../../lib/api";
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

  /** extra: 같은 자리에서 이어 받은 칸 (예: 갈 곳 → 그 주소) */
  function answer(id: string, value: string, extra: Record<string, string> = {}) {
    dispatch({ type: "answer", id, value });
    for (const [k, v] of Object.entries(extra)) dispatch({ type: "answer", id: k, value: v });
    const answers = { ...state.answers, [id]: value, ...extra };
    if (asked.every((f) => f.id in answers) && state.target && state.copy) {
      const endDate = endDateFrom(answers["meta.adset.end_date"] ?? "14일");
      dispatch({ type: "questionsDone", settings: buildSettings(fields, answers, state.target, state.copy, endDate), endDate });
    }
  }

  return (
    <section className="flex flex-col gap-5">
      <p className="text-caption text-soft">질문 {Math.min(index + 1, asked.length)} / {asked.length}</p>
      {index > 0 && next && (
        <button type="button" onClick={() => dispatch({ type: "unanswer", id: asked[index - 1]!.id })}
          className="self-start text-caption text-soft underline">
          ← 이전 질문
        </button>
      )}
      {next && (
        <Question key={next.id} field={next} answers={state.answers} keywords={state.keywords} checked={state.checks?.[next.id] ?? []}
          onCheck={(index) => dispatch({ type: "toggleCheck", key: next.id, index })}
          onAnswer={(v, extra) => answer(next.id, v, extra)} />
      )}
      {defaults.length > 0 && (
        <details className="text-caption text-soft">
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

/** 가게 주소: 'smartstore.naver.com/…'처럼 적어도 받아 https://를 붙인다. 점이 없으면 주소가 아니다. */
export function webAddress(raw: string): string | null {
  const v = raw.trim();
  if (!v || !v.includes(".") || /\s/.test(v)) return null;
  return /^https?:\/\//i.test(v) ? v : `https://${v}`;
}

/** '…{meta.pre.ig_account}' → 앞에서 받은 답을 넣는다 (인스타 아이디의 @·공백은 뺌). 빈 답이 들어가면 빈 칸으로.
 *  틀이 여러 개면 다 채워지는 첫 틀. */
function fill(template: string | string[] | undefined, answers: Record<string, string>): string {
  if (Array.isArray(template)) {
    for (const t of template) { const v = fill(t, answers); if (v) return v; }
    return "";
  }
  if (!template) return "";
  let empty = false;
  const out = template.replace(/\{([^}]+)\}/g, (_, id: string) => {
    const v = (answers[id] ?? "").replace(/^@/, "").replace(/\s+/g, "");
    if (!v) empty = true;
    return v;
  });
  return empty ? "" : out;
}

/** 앞 답에 따라 정해지는 값 (default_if·note_if): 맞는 게 없으면 undefined */
function byEarlier(map: Record<string, Record<string, string>> | null | undefined, answers: Record<string, string>): string | undefined {
  for (const [id, byAnswer] of Object.entries(map ?? {})) {
    const got = answers[id];
    if (got !== undefined && byAnswer[got]) return byAnswer[got];
  }
  return undefined;
}

function Question({ field, answers, keywords, checked, onCheck, onAnswer }: {
  field: Field; answers: Record<string, string>; keywords: string[]; checked: number[]; onCheck: (index: number) => void;
  onAnswer: (v: string, extra?: Record<string, string>) => void;
}) {
  const recommended = byEarlier(field.default_if, answers) ?? field.default;
  const note = byEarlier(field.note_if, answers);
  const [text, setText] = useState(field.default ?? "");
  const [bad, setBad] = useState(false);
  const [helpFor, setHelpFor] = useState<string | null>(null);   // 할 일이 있는 답을 골랐을 때 (예: 페이지 없어요)
  const help = helpFor ? field.help?.[helpFor] : undefined;
  const [picked, setPicked] = useState<string | null>(null);     // 이어 받을 주소가 있는 답을 골랐을 때 (예: 스토어 상품 페이지)
  const [url, setUrl] = useState("");
  const then = picked ? field.then_ask : undefined;
  /** 이 답을 고르면 주소를 이어 받을 칸 (없으면 바로 넘어감) */
  const thenField = (o: string): string | undefined => {
    const t = field.then_ask;
    if (!t?.say[o]) return undefined;
    return typeof t.field === "string" ? t.field : t.field[o];
  };
  /** 답을 정함: 이어 받을 주소가 있으면 주소 칸을 열고, 없으면 바로 넘어감 */
  const finish = (o: string) => {
    const to = thenField(o);
    if (!to) return onAnswer(o);
    // 미리 채우기: 틀 → (같은 답을 골랐던 적이 있으면) 그때 넣은 주소. 다른 답의 주소는 쓰지 않음 (인스타 주소가 상품 주소로 새지 않게)
    setPicked(o); setUrl(fill(field.then_ask?.prefill?.[o], answers) || (answers[field.id] === o ? answers[to] ?? "" : "")); setBad(false);
  };
  const pick = (o: string) => (field.help?.[o] ? setHelpFor(o) : finish(o));
  function submitThen() {
    const u = webAddress(url);
    const to = picked ? thenField(picked) : undefined;
    if (!u || !to || !picked) return setBad(true);
    onAnswer(picked, { [to]: u });
  }
  const isUrl = field.id === "meta.ad.website_url";
  function submit() {
    if (!isUrl) return onAnswer(text.trim());
    const url = webAddress(text);
    if (!url) return setBad(true);
    setBad(false);
    onAnswer(url);
  }
  return (
    <div className="flex flex-col gap-3">
      <Coach>
        <h2 className="text-lead font-semibold">{field.ask}</h2>
        {field.why && <p className="text-caption text-soft mt-1">{field.why}</p>}
        {note && <p className="text-caption text-ink mt-1">{note}</p>}
      </Coach>
      {then && picked ? (
        <div className="flex flex-col gap-2">
          <p className="text-caption"><span className="font-semibold">{picked}</span>로 보낼게요.</p>
          <label htmlFor="then-url" className="text-caption text-soft">{then.say[picked] ?? "주소를 알려 주세요."}</label>
          <input id="then-url" value={url} onChange={(e) => setUrl(e.target.value)} inputMode="url" autoComplete="off"
            placeholder={picked.includes("인스타") || thenField(picked)?.includes("insta") ? "https://www.instagram.com/가게아이디" : "https://smartstore.naver.com/가게이름/products/…"}
            aria-invalid={bad || undefined}
            className="rounded-button border border-field-line bg-paper px-3 py-2.5 text-body" />
          {bad && <p role="alert" className="text-caption text-block-ink">https:// 로 시작하는 주소로 넣어 주세요. 예: https://smartstore.naver.com/가게이름</p>}
          <PrimaryButton onClick={submitThen} disabled={!url.trim()}>다음</PrimaryButton>
          <button type="button" onClick={() => setPicked(null)} className="self-start text-caption text-soft underline">← 다시 고르기</button>
        </div>
      ) : help && helpFor ? (
        <div className="flex flex-col gap-3 rounded-card border border-line bg-paper p-4">
          <p className="text-body">{help.say}</p>
          {help.steps ? (
            <HelpChecklist steps={help.steps} checked={checked} keywords={keywords} onCheck={onCheck} />
          ) : help.url && (
            <NewTabLink url={help.url}>{help.link}</NewTabLink>
          )}
          <PrimaryButton onClick={() => finish(help.done_value)}>{help.done}</PrimaryButton>
          <div className="flex items-center justify-between gap-2">
            <button type="button" onClick={() => setHelpFor(null)} className="text-caption text-soft underline">← 다시 고르기</button>
            <button type="button" onClick={() => finish(helpFor)} className="text-caption text-soft underline">{help.later}</button>
          </div>
        </div>
      ) : field.options ? (
        <div className="flex flex-col gap-2">
          {field.options.map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => pick(o)}
              className={`rounded-button border px-4 py-3 text-left text-body ${o === recommended ? "border-ink bg-paper font-semibold" : "border-line"}`}
            >
              {o}
              {o === recommended && <span className="block text-caption font-normal text-soft">권장</span>}
            </button>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <label htmlFor={field.id} className="text-caption text-soft">{field.label}</label>
          <input
            id={field.id}
            value={text}
            onChange={(e) => setText(e.target.value)}
            aria-invalid={bad || undefined}
            className="rounded-button border border-field-line bg-paper px-3 py-2.5 text-body"
          />
          {bad && <p role="alert" className="text-caption text-block-ink">가게 주소를 https:// 로 시작하는 주소로 넣어 주세요. 예: https://smartstore.naver.com/가게이름</p>}
          <PrimaryButton onClick={submit} disabled={REQUIRED_TEXT.has(field.id) && !text.trim()}>
            다음
          </PrimaryButton>
        </div>
      )}
    </div>
  );
}

function NewTabLink({ url, children }: { url: string; children: React.ReactNode }) {
  return (
    <a href={url} target="_blank" rel="noopener noreferrer"
      className="self-start rounded-button border border-accent bg-paper px-4 py-2 text-label font-semibold text-accent-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
      {children} <span aria-hidden>↗</span><span className="sr-only"> (새 탭)</span>
    </a>
  );
}

/** 할 일 체크리스트: 사장님이 직접 체크 (다 체크하지 않아도 넘어갈 수 있음). 남은 일을 'n / 전체'로 보여 줌 */
function HelpChecklist({ steps, checked, keywords, onCheck }: {
  steps: NonNullable<OptionHelp["steps"]>; checked: number[]; keywords: string[]; onCheck: (index: number) => void;
}) {
  const words = keywords.slice(0, 3);
  return (
    <div className="flex flex-col gap-3">
      <p className="self-end text-caption text-soft">{checked.filter((i) => i < steps.length).length} / {steps.length}</p>
      <ul className="flex flex-col gap-3">
        {steps.map((st, i) => (
          <li key={st.text} className="flex flex-col gap-2">
            <label className="flex items-start gap-2 text-body">
              <input type="checkbox" checked={checked.includes(i)} onChange={() => onCheck(i)} className="mt-1 accent-accent" />
              <span className={checked.includes(i) ? "text-soft line-through" : ""}>{st.text}</span>
            </label>
            {st.hint === "keywords" && words.length > 0 && (
              <p className="pl-6 text-caption text-soft">상품명에 이 말을 넣으면 네이버에서 잘 찾아져요: <span className="text-ink">{words.join(" · ")}</span></p>
            )}
            {st.url && <div className="pl-6"><NewTabLink url={st.url}>{st.link ?? "열기"}</NewTabLink></div>}
          </li>
        ))}
      </ul>
    </div>
  );
}
