import { useEffect, useRef, useState } from "react";
import type { Field, OptionHelp, PresetField } from "../../../lib/api";
import type { FlowEvent, FlowState } from "../../../lib/flow";
import { SETTING_ORDER, askedFields, buildSettings, routeFromPrep, isoDate, minBudget, parseWon, scheduleDays, scheduleFrom } from "../../../lib/settings";
import { Coach, PrimaryButton } from "../ui/Coach";

const PREP = "사전 점검";   // 준비물 화면에서 묻는 칸 (settings.ts PREP_STAGE)
const REQUIRED_TEXT = new Set(["meta.ad.website_url"]);
/** 글자 버튼(이전·다시 고르기·나중에)도 손가락으로 누를 수 있게 높이 44px */
export const TEXT_BUTTON = "inline-flex min-h-11 items-center self-start text-caption text-soft underline";
/** 돈과 바로 이어지는 질문: 설명을 본문 크기·진한 글자로 (작은 회색 글씨에 숨기지 않음) */
/** 보기 버튼 (키보드로 옮길 때 초점이 보이게) */
const OPTION = "rounded-button border border-line px-4 py-3 text-left text-body focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent";
const MONEY = new Set(["meta.adset.lifetime_budget", "meta.pre.payment"]);
/** 글자 칸 이름·예시 (메타 화면 이름 대신 사장님 말로) */
const INPUT: Record<string, { label: string; placeholder: string }> = {
  "meta.pre.ig_account": { label: "인스타그램 아이디", placeholder: "예: ovenlog" },
};

interface Props {
  state: FlowState;
  dispatch: (ev: FlowEvent) => void;
  fields: Field[];
  defaults: PresetField[];
}

/** ② 질문: 한 번에 하나씩. 다 답하면 광고 관리자에 넣을 세팅값 목록을 만든다. */
export default function QuestionStep({ state, dispatch, fields, defaults: all }: Props) {
  // 처음 세팅할 때 준비물에서 받은 주소로 갈 곳이 정해졌으면 '어디로 보낼까요'를 다시 묻지 않는다 (세팅 목록·[② 답 바꾸기]에서 보이고 바꿀 수 있음).
  // 세팅 뒤 준비물을 다시 답한 경우(세팅 목록이 있음)에는 새 주소를 확인하게 그대로 묻는다
  const fromPrep = state.settings.length ? {} : routeFromPrep(state.answers);
  const asked = askedFields(fields).filter((f) => !(f.id in fromPrep));
  const defaults = all.filter((d) => !SETTING_ORDER.includes(d.id));   // 뭉치가 안내하는 칸은 '묻지 않고 둔 칸'이 아님
  const next = asked.find((f) => !(f.id in state.answers));
  const index = next ? asked.indexOf(next) : asked.length;

  /** extra: 같은 자리에서 이어 받은 칸 (예: 갈 곳 → 그 주소) */
  function answer(id: string, value: string, extra: Record<string, string> = {}) {
    dispatch({ type: "answer", id, value });
    for (const [k, v] of Object.entries(extra)) dispatch({ type: "answer", id: k, value: v });
    const answers = { ...fromPrep, ...state.answers, [id]: value, ...extra };
    if (asked.every((f) => f.id in answers) && state.target && state.copy) {
      const when = scheduleFrom(answers["meta.adset.end_date"] ?? "14일");
      dispatch({ type: "questionsDone", settings: buildSettings(fields, answers, state.target, state.copy, when),
        startDate: when.start, endDate: when.end });
    }
  }

  return (
    <section className="flex flex-col gap-5">
      {index === 0 && (
        <Coach avatar={!next}>광고 관리자에 넣을 것 {asked.length}가지만 물어볼게요. 사장님이 마지막에 '게시'를 누르기 전에는 돈이 나가지 않아요.</Coach>
      )}
      <p className="text-caption text-soft">질문 {Math.min(index + 1, asked.length)} / {asked.length}</p>
      {index === 0 && next && (
        // 첫 질문에서도 뒤로: ② 문구로 (QA 목록 밖)
        <button type="button" onClick={() => dispatch({ type: "editCopy" })} className={TEXT_BUTTON}>← 문구로 돌아가기</button>
      )}
      {index > 0 && next && (
        <button type="button" onClick={() => dispatch({ type: "unanswer", id: asked[index - 1]!.id })}
          className={TEXT_BUTTON}>
          ← 이전 질문
        </button>
      )}
      {next && (
        <Question key={next.id} field={next} answers={state.answers} prev={state.prevAnswers} keywords={state.keywords} checked={state.checks?.[next.id] ?? []}
          onCheck={(index) => dispatch({ type: "toggleCheck", key: next.id, index })}
          onAnswer={(v, extra) => answer(next.id, v, extra)} />
      )}
      {defaults.length > 0 && (
        <details className="text-caption text-soft">
          <summary className="flex min-h-11 cursor-pointer items-center">묻지 않고 이렇게 두었어요 ({defaults.length}칸)</summary>
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

/** 지난번 답 한 줄: 날짜 답('2026-12-01~2026-12-14')은 '12월 1일 ~ 12월 14일'로 */
function shownBefore(v: string): string {
  const m = /^(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?~(\d{4}-\d{2}-\d{2})(?: (\d{2}:\d{2}))?$/.exec(v);
  return m ? `${monthDay(m[1]!, m[2])} ~ ${monthDay(m[3]!, m[4])}` : v;
}

/** 앞 답에 따라 정해지는 값 (default_if·note_if): 맞는 게 없으면 undefined */
function byEarlier(map: Record<string, Record<string, string>> | null | undefined, answers: Record<string, string>): string | undefined {
  for (const [id, byAnswer] of Object.entries(map ?? {})) {
    const got = answers[id];
    if (got !== undefined && byAnswer[got]) return byAnswer[got];
  }
  return undefined;
}

export function Question({ field, answers, prev = {}, keywords, checked, onCheck, onAnswer, startHelp }: {
  field: Field; answers: Record<string, string>;
  /** 지운 답 (이전 질문·답 바꾸기): 직접 넣었던 날짜·금액·주소·글자를 다시 채운다 */
  prev?: Record<string, string>;
  keywords: string[]; checked: number[]; onCheck: (index: number) => void;
  onAnswer: (v: string, extra?: Record<string, string>) => void;
  /** 처음부터 열어 둘 '만드는 법' (준비물 요약의 [만드는 법 보기]) */
  startHelp?: string;
}) {
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => title.current?.focus(), []);   // 새 질문이 나오면 화면 읽기·키보드가 그 질문부터
  const note = byEarlier(field.note_if, answers);
  const was = prev[field.id];
  const custom = was !== undefined && !field.options?.includes(was);   // 지난번에 직접 넣은 값 (날짜·금액·가게 주변)
  const [text, setText] = useState(was ?? field.default ?? "");
  const [bad, setBad] = useState(false);
  const [helpFor, setHelpFor] = useState<string | null>(startHelp ?? null);   // 할 일이 있는 답을 골랐을 때 (예: 페이지 없어요)
  const help = helpFor ? field.help?.[helpFor] : undefined;
  const [picked, setPicked] = useState<string | null>(null);     // 이어 받을 주소가 있는 답을 골랐을 때 (예: 스토어 상품 페이지)
  const [dates, setDates] = useState(custom && field.custom === "dates");                      // [날짜 직접 정하기]를 눌렀을 때
  const [areaFor, setAreaFor] = useState<string | null>(null);    // 가게·배달을 골랐을 때 (가게 주소·반경)
  const [money, setMoney] = useState(custom && field.custom === "won");                      // [금액 직접 넣기]를 눌렀을 때
  // 총예산 질문: 앞에서 고른 기간으로 '세트마다 적어도 ○원'을 알려 주고, 그보다 적은 금액엔 ▲ (EX-01 ④)
  const days = field.custom === "won" ? scheduleDays(scheduleFrom(answers["meta.adset.end_date"] ?? "14일")) : 0;
  const least = days > 0 ? minBudget(days) : 0;
  const enough = (o: string) => (parseWon(o) ?? Infinity) >= least;
  const base = byEarlier(field.default_if, answers) ?? field.default;
  // 기본 권장 금액이 이 기간엔 모자라면, 충분한 가장 작은 금액을 권장 (없으면 권장 없음)
  const recommended = least > 0 && base && !enough(base) ? field.options?.find(enough) : base;
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
    const before = answers[field.id] ?? was;
    setPicked(o); setUrl(fill(field.then_ask?.prefill?.[o], answers) || (before === o ? answers[to] ?? prev[to] ?? "" : "")); setBad(false);
  };
  const pick = (o: string) => {
    if (field.help?.[o]) return setHelpFor(o);
    if (field.custom === "area" && field.custom_for?.includes(o)) return setAreaFor(o);
    if (field.answer_as?.[o]) return onAnswer(field.answer_as[o]!);
    finish(o);
  };
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
        <h2 ref={title} tabIndex={-1} className="text-lead font-semibold outline-none">{field.ask}</h2>
        {field.why && <p className={`mt-1 ${MONEY.has(field.id) ? "text-body text-ink" : "text-caption text-soft"}`}>{field.why}</p>}
        {note && <p className="text-caption text-ink mt-1">{note}</p>}
        {least > 0 && <p className="text-caption text-ink mt-1">광고 기간이 {days}일이라 적어도 약 {least.toLocaleString()}원 (하루 최소 약 1,336원 × {days}일)은 넣어야 광고가 나가요.</p>}
      </Coach>
      {money ? (
        <WonInput least={least} initial={custom ? was : undefined} onBack={() => setMoney(false)} onDone={(v) => onAnswer(v)} />
      ) : areaFor ? (
        <ShopArea way={areaFor} initial={was} onBack={() => setAreaFor(null)} onDone={(v) => onAnswer(v)} />
      ) : dates ? (
        <DateRange initial={custom ? was : undefined} onBack={() => setDates(false)} onDone={(v) => onAnswer(v)} />
      ) : then && picked ? (
        <div className="flex flex-col gap-2">
          {field.stage !== PREP && <p className="text-caption"><span className="font-semibold">{picked}</span>로 보낼게요.</p>}
          <label htmlFor="then-url" className="text-caption text-soft">{then.say[picked] ?? "주소를 알려 주세요."}</label>
          <input id="then-url" value={url} onChange={(e) => setUrl(e.target.value)} inputMode="url" autoComplete="off"
            placeholder={picked.includes("인스타") || thenField(picked)?.includes("insta") ? "https://www.instagram.com/가게아이디" : "https://smartstore.naver.com/가게이름/products/…"}
            aria-invalid={bad || undefined} aria-describedby={bad ? "then-url-error" : undefined}
            className="rounded-button border border-field-line bg-paper px-3 py-2.5 text-body" />
          {bad && <p id="then-url-error" role="alert" className="text-caption text-block-ink">https:// 로 시작하는 주소로 넣어 주세요. 예: https://smartstore.naver.com/가게이름</p>}
          <PrimaryButton onClick={submitThen} disabled={!url.trim()}>다음</PrimaryButton>
          {then.none?.[picked] && (
            <button type="button" onClick={() => finish(then.none![picked]!)} className="inline-flex min-h-11 items-center self-start text-caption text-accent-ink underline">
              상품 페이지 주소가 없어요 → 인스타그램 프로필로 보낼게요
            </button>
          )}
          {field.stage === PREP && (
            // 준비물에선 주소가 없어도 막지 않는다 (클릭 주소는 ② 세팅에서 다시 묻는다, QA P-05)
            <button type="button" onClick={() => onAnswer(picked)} className="inline-flex min-h-11 items-center self-start text-caption text-accent-ink underline">
              주소 없이 넘어가기 (② 세팅에서 다시 물어봐요)
            </button>
          )}
          <button type="button" onClick={() => setPicked(null)} className={TEXT_BUTTON}>← 다시 고르기</button>
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
          {/* '나중에'도 같은 무게의 버튼으로 (UX 원칙 5) */}
          <button type="button" onClick={() => finish(helpFor)} className="min-h-11 w-full rounded-button border border-line px-4 py-2.5 text-body">{help.later}</button>
          <button type="button" onClick={() => setHelpFor(null)} className={TEXT_BUTTON}>← 다시 고르기</button>
        </div>
      ) : field.options ? (
        <div className="flex flex-col gap-2">
          {/* 지난번에 보기 밖의 값을 넣었으면 (가게 주변 주소·직접 넣은 금액·날짜) 그 값을 한 줄로 */}
          {was !== undefined && !field.options.some((o) => was === o || field.answer_as?.[o] === was) && (
            <p className="text-caption text-ink">✓ 지난번 답: {shownBefore(was)}</p>
          )}
          {field.options.map((o) => {
            const short = least > 0 && (parseWon(o) ?? Infinity) < least;   // 이 기간엔 광고가 안 나갈 수 있는 금액
            const before = was !== undefined && (was === o || field.answer_as?.[o] === was);   // [② 답 바꾸기]로 돌아왔을 때 지난번 답
            return (
              <button
                key={o}
                type="button"
                onClick={() => pick(o)}
                className={OPTION}
              >
                {o}
                {before && <span className="block text-caption text-ink">✓ 지난번 답</span>}
                {o === recommended && !short && <span className="block text-caption text-accent-ink">권장</span>}
                {short && <span className="block text-caption font-normal text-warn"><span aria-hidden="true">▲ </span><span className="sr-only">주의 </span>{days}일 동안 쓰기엔 적어요</span>}
              </button>
            );
          })}
          {field.custom === "won" && (
            <button type="button" onClick={() => setMoney(true)} className={OPTION}>
              금액 직접 넣기
            </button>
          )}
          {field.custom === "dates" && (
            <button type="button" onClick={() => setDates(true)} className={OPTION}>
              날짜 직접 정하기
            </button>
          )}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <label htmlFor={field.id} className="text-caption text-soft">{INPUT[field.id]?.label ?? field.label}</label>
          <input
            id={field.id}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.nativeEvent.isComposing) { e.preventDefault(); submit(); } }}
            placeholder={INPUT[field.id]?.placeholder}
            aria-invalid={bad || undefined} aria-describedby={bad ? `${field.id}-error` : undefined}
            className="rounded-button border border-field-line bg-paper px-3 py-2.5 text-body"
          />
          {bad && <p id={`${field.id}-error`} role="alert" className="text-caption text-block-ink">가게 주소를 https:// 로 시작하는 주소로 넣어 주세요. 예: https://smartstore.naver.com/가게이름</p>}
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
      className="min-h-11 self-start rounded-button border border-accent bg-paper px-4 py-2 text-label font-semibold text-accent-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
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

/** '2026-12-01' → '12월 1일', 시각이 있으면 '12월 1일 오전 9시' */
function monthDay(iso: string, time = ""): string {
  const [, m, d] = iso.split("-").map(Number);
  if (!time) return `${m}월 ${d}일`;
  const [h, min] = time.split(":").map(Number);
  const half = h! < 12 ? "오전" : "오후";
  const h12 = h! % 12 === 0 ? 12 : h! % 12;
  return `${m}월 ${d}일 ${half} ${h12}시${min ? ` ${min}분` : ""}`;
}

/** 시작일·종료일 고르기 (시각은 선택). 시작일은 내일이 기본(오늘도 고를 수 있음), 종료일은 시작일 다음 날부터. 기간은 시작일·종료일을 모두 셈 */
function DateRange({ initial, onBack, onDone }: { initial?: string; onBack: () => void; onDone: (value: string) => void }) {
  const now = new Date();
  const today = isoDate(now);
  const got = initial ? scheduleFrom(initial) : undefined;   // 지난번에 고른 날짜·시각
  const [start, setStart] = useState(got?.start ?? scheduleFrom("1일", now).start);   // 기본은 칩과 같이 내일 시작
  const [end, setEnd] = useState(got?.end ?? "");
  const [startTime, setStartTime] = useState(got?.startTime ?? "");
  const [endTime, setEndTime] = useState(got?.endTime ?? "");
  const [tried, setTried] = useState(false);
  const pad = (n: number) => String(n).padStart(2, "0");
  const startBad = Boolean(start) && start < today;
  const timeBad = !startBad && start === today && Boolean(startTime) && startTime <= `${pad(now.getHours())}:${pad(now.getMinutes())}`;
  const endBad = Boolean(start && end) && end <= start;
  const ok = Boolean(start && end) && !startBad && !timeBad && !endBad;
  const days = ok ? Math.round((Date.parse(end) - Date.parse(start)) / 86400000) + 1 : 0;
  const box = "rounded-button border border-field-line bg-paper px-3 py-2.5 text-body";
  const value = `${start}${startTime ? ` ${startTime}` : ""}~${end}${endTime ? ` ${endTime}` : ""}`;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1">
        <div className="flex gap-2">
          <div className="flex flex-1 flex-col gap-1">
            <label htmlFor="date-start" className="text-caption text-soft">시작일</label>
            <input id="date-start" type="date" value={start} min={today} onChange={(e) => setStart(e.target.value)}
              aria-invalid={(tried && startBad) || undefined} aria-describedby={tried && startBad ? "date-start-error" : undefined} className={box} />
          </div>
          <div className="flex w-28 flex-col gap-1">
            <label htmlFor="time-start" className="text-caption text-soft">시작 시각</label>
            <input id="time-start" type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)}
              aria-invalid={(tried && timeBad) || undefined} aria-describedby={tried && timeBad ? "time-start-error" : undefined} className={box} />
          </div>
        </div>
        {tried && startBad && <p id="date-start-error" role="alert" className="text-caption text-block-ink">오늘이나 그 뒤 날짜로 골라 주세요.</p>}
        {tried && timeBad && <p id="time-start-error" role="alert" className="text-caption text-block-ink">오늘 시작하면 지금보다 뒤 시각으로 골라 주세요.</p>}
      </div>
      <div className="flex flex-col gap-1">
        <div className="flex gap-2">
          <div className="flex flex-1 flex-col gap-1">
            <label htmlFor="date-end" className="text-caption text-soft">종료일</label>
            <input id="date-end" type="date" value={end} min={start || today} onChange={(e) => setEnd(e.target.value)}
              aria-invalid={(tried && endBad) || undefined} aria-describedby={tried && !startBad && endBad ? "date-end-error" : undefined} className={box} />
          </div>
          <div className="flex w-28 flex-col gap-1">
            <label htmlFor="time-end" className="text-caption text-soft">종료 시각</label>
            <input id="time-end" type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} className={box} />
          </div>
        </div>
        {tried && !startBad && endBad && <p id="date-end-error" role="alert" className="text-caption text-block-ink">종료일을 시작일 다음 날 이후로 골라 주세요.</p>}
      </div>
      <p className="text-caption text-soft">시각은 비워 두면 광고 관리자에 정해진 시각 그대로 둬요.</p>
      {ok && <p className="text-body">{monthDay(start, startTime)}부터 {monthDay(end, endTime)}까지, {days}일 동안 광고해요.</p>}
      <PrimaryButton onClick={() => (ok ? onDone(value) : setTried(true))} disabled={!start || !end}>다음</PrimaryButton>
      <button type="button" onClick={onBack} className={TEXT_BUTTON}>← 다시 고르기</button>
    </div>
  );
}

/** 총예산 직접 넣기 (원). 하루 최소 × 기간보다 적으면 ▲로 알려 주되 막지는 않는다 (사장님이 정함). 답: '25,000원' */
function WonInput({ least, initial, onBack, onDone }: { least: number; initial?: string; onBack: () => void; onDone: (value: string) => void }) {
  const [raw, setRaw] = useState(initial ? String(parseWon(initial) ?? "") : "");
  const n = parseWon(raw);
  const short = n !== null && least > 0 && n < least;
  const unread = raw.trim() !== "" && n === null;   // 숫자로 못 읽음 → 왜 [다음]이 안 눌리는지 알려 줌
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor="budget-won" className="text-caption text-soft">기간 전체 총예산 (원)</label>
      <input id="budget-won" value={raw} onChange={(e) => setRaw(e.target.value)} inputMode="numeric" autoComplete="off"
        placeholder="예: 25000" aria-describedby={short ? "budget-short" : unread ? "budget-unread" : undefined} aria-invalid={unread || undefined}
        className="rounded-button border border-field-line bg-paper px-3 py-2.5 text-body" />
      {n !== null && <p className="text-caption text-ink">{n.toLocaleString()}원</p>}
      {unread && <p id="budget-unread" role="alert" className="text-caption text-block-ink">숫자로 넣어 주세요 (예: 30000 또는 3만)</p>}
      {short && (
        <p id="budget-short" role="status" className="flex gap-1.5 rounded-soft border-[1.5px] border-warn-line bg-warn-bg px-2 py-1 text-caption text-warn">
          <span aria-hidden="true" className="font-bold">▲</span><span className="sr-only">주의</span>
          <span>약 {least.toLocaleString()}원보다 적어서 광고가 안 나갈 수 있어요 → 금액을 늘리거나 기간을 줄여 주세요.</span>
        </p>
      )}
      <PrimaryButton onClick={() => n !== null && onDone(`${n.toLocaleString()}원`)} disabled={n === null}>다음</PrimaryButton>
      <button type="button" onClick={onBack} className={TEXT_BUTTON}>← 다시 고르기</button>
    </div>
  );
}

const RADII = ["3km", "5km", "10km"];

/** 가게·배달: 가게 주소(시·구·동)와 반경. 값은 세팅 목록·뭉치 안내에 그대로 보인다 (지도에서 고르는 건 사장님) */
function ShopArea({ way, initial, onBack, onDone }: { way: string; initial?: string; onBack: () => void; onDone: (value: string) => void }) {
  const got = /^가게 주변 (\S+) · (.+)$/.exec(initial ?? "");   // 지난번 답 '가게 주변 5km · 서울 마포구 망원동'
  const [address, setAddress] = useState(got?.[2] ?? "");
  const [radius, setRadius] = useState(got && RADII.includes(got[1]!) ? got[1]! : "5km");
  const place = address.trim().replace(/\s+/g, " ");
  return (
    <div className="flex flex-col gap-3">
      <p className="text-caption"><span className="font-semibold">{way}</span> → 가게 주변 손님에게만 보여 줄게요.</p>
      <div className="flex flex-col gap-1">
        <label htmlFor="shop-address" className="text-caption text-soft">가게 주소 (시·구·동)</label>
        <input id="shop-address" value={address} onChange={(e) => setAddress(e.target.value)} autoComplete="off"
          placeholder="예: 서울 마포구 망원동" className="rounded-button border border-field-line bg-paper px-3 py-2.5 text-body" />
      </div>
      <div className="flex flex-col gap-1">
        <p id="shop-radius" className="text-caption text-soft">가게에서 얼마나 멀리까지</p>
        <div role="group" aria-labelledby="shop-radius" className="flex gap-2">
          {RADII.map((r) => (
            <button key={r} type="button" aria-pressed={r === radius} onClick={() => setRadius(r)}
              className={`min-h-11 rounded-button border px-4 py-2 text-body ${r === radius ? "border-ink bg-paper font-semibold" : "border-line"}`}>
              {r}
            </button>
          ))}
        </div>
      </div>
      <PrimaryButton onClick={() => place && onDone(`가게 주변 ${radius} · ${place}`)} disabled={!place}>다음</PrimaryButton>
      <button type="button" onClick={onBack} className={TEXT_BUTTON}>← 다시 고르기</button>
    </div>
  );
}
