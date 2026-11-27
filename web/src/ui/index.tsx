// 공통 부품. 색은 토큰 이름(bg-surface, text-soft …)으로만 쓴다. 이름은 UX_설계원칙.md의 부품 이름을 따른다.
import { useState, type ReactNode } from "react";

/** 카드: 블록 하나 = 메시지 하나 (v4.2). 제목 바로 아래 한 줄 요약(summary) → 그 아래 차트·표.
 *  번호는 화면 순서(0~7)라 실제 순서가 있는 곳에만 붙인다. */
export function Card({ id, step, title, summary, badge, children }: {
  id?: string; step?: number; title: string; summary?: ReactNode; badge?: ReactNode; children?: ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={id ? `${id}-title` : undefined}
      className="bg-card border border-card-border rounded-card shadow-card p-card flex flex-col gap-stack min-w-0 scroll-mt-4">
      <div className="flex flex-col gap-1">
        <h2 id={id ? `${id}-title` : undefined} className="text-title font-bold flex flex-wrap items-baseline gap-2">
          {step !== undefined && <span className="text-caption font-semibold text-soft tabular-nums">{step}</span>}
          {title}{badge}
        </h2>
        {summary && <p className="text-body text-soft">{summary}</p>}
      </div>
      {children}
    </section>
  );
}

/** 주 버튼 / 보조 버튼 / 로딩 버튼 (누른 버튼에 '…중'을 띄워 같은 자리에서 기다리게 한다). */
export function Button({ children, onClick, kind = "primary", busy, disabled, type = "button", title }: {
  children: ReactNode; onClick?: () => void; kind?: "primary" | "secondary"; busy?: boolean; disabled?: boolean; type?: "button" | "submit"; title?: string;
}) {
  const look = kind === "primary"
    ? "bg-button text-button-fg shadow-press hover:bg-button-hover active:translate-y-0.5 active:shadow-none"
    : "border-2 border-accent bg-surface text-accent-ink hover:bg-accent-soft";
  return (
    <button type={type} onClick={onClick} disabled={disabled || busy} aria-busy={busy || undefined} title={title}
      className={`h-button px-6 rounded-button text-body font-bold disabled:cursor-default disabled:border-[1.5px] disabled:border-disabled-line disabled:bg-disabled-bg disabled:text-disabled-fg disabled:shadow-none ${look}`}>
      {busy ? "계산하는 중…" : children}
    </button>
  );
}

export type Word = "확실해요" | "A 쪽이에요" | "B 쪽이에요" | "아직 몰라요";

/** 판정 배지 (v4.2 AN-TXT): 사이트 전체에서 '확실해요 / ○ 쪽이에요 / 아직 몰라요' 3개만.
 *  확실해요 = 진한 바이올렛 · ○ 쪽이에요 = 연한 바이올렛 · 아직 몰라요 = 회색. 색만으로 말하지 않게 모양(●◐○)도. */
export function VerdictBadge({ word, small }: { word: Word | string; small?: boolean }) {
  const look = word === "확실해요" ? { cls: "bg-adopt text-on-accent", mark: "●" }
    : word === "아직 몰라요" ? { cls: "bg-hold-bg text-hold", mark: "○" } : { cls: "bg-likely-bg text-adopt ring-[1.5px] ring-inset ring-likely", mark: "◐" };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-badge px-3 py-1 font-bold whitespace-nowrap ${small ? "text-caption px-2.5 py-0.5" : "text-body"} ${look.cls}`}>
      <span aria-hidden="true">{look.mark}</span>{word}
    </span>
  );
}

/** 나은 쪽 확률 → 판정 3단어 (90% 이상 / 70~90% / 70% 미만). 기준은 서버 verdict.py와 같다. */
/** 'B가 나을 확률'을 나은 쪽 기준 확률로 (B가 낫다 → p, A가 낫다 → 1 − p). */
/** 나을 확률 글자: 100%라고 단정하지 않는다 (표본으로 구한 값이라 99.5% 넘으면 '99% 넘게', 감사 20) */
export function probText(p: number): string {
  return p >= 0.995 ? "99% 넘게" : pct(p);
}

export function betterProb(better: "A" | "B" | string, probB: number): number {
  return better === "B" ? probB : 1 - probB;
}

/** A/B 세트 색 (A = 회색, B = 바이올렛) */
export const seriesBg = (b: boolean | number) => (b ? "bg-series-b" : "bg-series-a");

export function wordOf(probB: number): Word {
  const p = Math.max(probB, 1 - probB);
  const better = probB >= 0.5 ? "B" : "A";
  return p >= 0.9 ? "확실해요" : p >= 0.7 ? `${better} 쪽이에요` : "아직 몰라요";
}

/** 테스트 제안 태그: 돌려 본 적 없는 선택지 (판정 배지 대신). 뭉치 배 색이라 보라 판정 배지와 구분돼요 (꾸미기안_뭉치). */
export function TestTag({ text = "테스트 제안" }: { text?: string }) {
  return <span className="inline-flex items-center rounded-badge bg-belly px-2.5 py-0.5 text-caption font-bold text-belly-ink whitespace-nowrap">{text}</span>;
}

/** ● 참고만 배지 (ALT-22): 노출이 적은 칸. 파랑 바탕 + 흰 글자, 그 칸 숫자는 연하게(text-soft). 회색은 '아직 몰라요'에만. */
export function ReferenceBadge() {
  return (
    <span className="ml-2 inline-flex items-center gap-1 rounded-badge bg-reference px-2 py-0.5 text-small font-bold text-on-accent whitespace-nowrap">
      <span aria-hidden="true">●</span>참고만
    </span>
  );
}

/** 근거 등급: A 실측 · B 매체 추산 · D 우리 가정. 글자(A·B)는 세트 이름과 헷갈려서 화면엔 말로만. */
export const GRADE_LABEL: Record<string, string> = { A: "실측", B: "매체 추산", D: "가정" };
export function Grade({ g }: { g: "A" | "B" | "D" }) {
  return <span className="inline-block shrink-0 rounded-badge border border-line px-2 py-0.5 text-caption text-soft whitespace-nowrap">근거: {GRADE_LABEL[g]}</span>;
}

/** 🔎 접기: 기본은 사장님용, 펼치면 계산 방법·지표 숫자(CPM·CTR·CPC)·근거. 지표 숫자는 여기에만 (v4.2). */
export function HowCalculated({ easy, title = "이 숫자는 어떻게 나왔나요?", children }: { easy?: string; title?: string; children: ReactNode }) {
  return (
    <details className="rounded-button bg-details px-4 py-3 group">
      <summary className="cursor-pointer text-body font-semibold text-details-fg"><span aria-hidden="true">🔎 </span>{title}</summary>
      <div className="mt-3 flex flex-col gap-2 text-body text-soft">
        {easy && <p><b className="text-ink">쉽게 말하면:</b> {easy}</p>}
        {children}
      </div>
    </details>
  );
}

export type Level = "block" | "warn" | "info" | "ok";

const LEVEL = {
  block: { shape: "■", sign: "✕", name: "차단", mark: "bg-block", box: "bg-block-bg text-block-ink" },
  warn: { shape: "▲", sign: "!", name: "주의", mark: "bg-warn-mark", box: "bg-warn-bg text-warn" },
  info: { shape: "●", sign: "i", name: "참고", mark: "bg-info", box: "bg-info-bg text-ink" },
  ok: { shape: "✓", sign: "", name: "정상", mark: "bg-ok", box: "bg-ok-bg text-ink" },
} as const;

/** 알림 모양: 색만으로 말하지 않게 모양 + 기호 + 이름 (■✕ 차단 · ▲! 주의 · ●i 참고 · ✓ 정상, WCAG 1.4.1). */
export function AlertMark({ level }: { level: Level }) {
  const l = LEVEL[level];
  const shape = level === "block" ? "rounded-mark" : level === "warn" ? "[clip-path:polygon(50%_0,100%_100%,0_100%)] pt-1" : "rounded-badge";
  return (
    <span className="inline-flex items-center gap-1 shrink-0" title={l.name}>
      <span aria-hidden="true" className={`inline-grid size-4 place-items-center text-mark font-bold text-on-accent ${l.mark} ${shape}`}>
        {level === "ok" ? "✓" : l.sign}
      </span>
      <span className="sr-only">{l.name}</span>
    </span>
  );
}

/** 탭 단추 줄 (같은 화면 안에서 보기 바꾸기). big: 화면의 주 탭 (AN-04 비교 기준) */
export function Tabs<T extends string>({ label, items, value, onChange, big = false }:
  { label: string; items: { id: T; label: ReactNode }[]; value: T; onChange: (id: T) => void; big?: boolean }) {
  return (
    <div role="tablist" aria-label={label} className="flex flex-wrap gap-2">
      {items.map((t) => (
        <button key={t.id} role="tab" type="button" aria-selected={value === t.id} onClick={() => onChange(t.id)}
          className={`rounded-badge border ${big ? "px-4 py-1.5 text-body" : "px-3 py-1 text-caption"} ${value === t.id ? "border-accent bg-accent text-on-accent font-semibold" : "border-line bg-surface"}`}>
          {t.label}
        </button>
      ))}
    </div>
  );
}

/** 토스트: 복사처럼 이미 끝난 일을 슬쩍 알린다 (버튼 없음). */
export function Toast({ text }: { text: string | null }) {
  return (
    <div aria-live="polite" className="fixed bottom-6 left-1/2 -translate-x-1/2">
      {text && <p className="rounded-button bg-action text-on-action px-4 py-2 text-body shadow-float">{text}</p>}
    </div>
  );
}

/** 금액은 '원' (v4.2): 6,342원 · 만 원 단위로 딱 떨어지면 10만 원. '₩'는 쓰지 않는다. */
export function won(x: number | null | undefined): string {
  if (x == null) return "–";
  const n = Math.round(x);
  return n >= 10000 && n % 10000 === 0 ? `${(n / 10000).toLocaleString()}만 원` : `${n.toLocaleString()}원`;
}
/** 비율을 사람 수로: 0.0173 → '약 17명' (1,000명 중). 노출 대비 클릭은 사람 수가 아니라 횟수라 unit '번'. */
export function people(rate: number | null | undefined, base = 1000, unit = "명"): string {
  if (rate == null) return "–";
  const n = rate * base;
  return n >= 1 ? `약 ${Math.round(n)}${unit}` : `약 ${n.toFixed(1)}${unit}`;
}
/** 범위 표기: '보통 13명 (적게 7명 ~ 많이 20명)'. */
export function band(b: { median: number; lo: number; hi: number }, unit = "명", fmt: (x: number) => string = (x) => Math.round(x).toLocaleString()): string {
  return `보통 ${fmt(b.median)}${unit} (적게 ${fmt(b.lo)}${unit} ~ 많이 ${fmt(b.hi)}${unit})`;
}
/** 받침에 맞는 조사: josa("세로 소재", "을를") → "세로 소재를", josa("새 문구", "이가") → "새 문구가" */
export function josa(word: string, pair: "이가" | "을를" | "은는" | "과와" = "이가"): string {
  const c = word.trim().slice(-1).charCodeAt(0);
  const has = c >= 0xac00 && c <= 0xd7a3 && (c - 0xac00) % 28 !== 0;
  return word + (has ? pair[0] : pair[1]);
}
/** '2026-11-18' → '11/18' */
export function md(d: string | undefined): string {
  if (!d) return "";
  const [, m, day] = d.slice(0, 10).split("-");
  return `${Number(m)}/${Number(day)}`;
}
export function pct(x: number | null | undefined, digits = 0): string {
  return x == null ? "–" : `${(x * 100).toFixed(digits)}%`;
}

/** 접기 줄 (축소안 v5): '▸ 이름 ······ 핵심 한 줄'. 닫힌 줄에도 핵심 숫자를 미리 보여서 안 열어도 감이 오게.
 *  내용은 열었을 때만 그린다 (예상 방문자 수처럼 서버에 묻는 내용이 미리 돌지 않게). */
export function Fold({ label, preview, children, open: start = false }: { label: ReactNode; preview?: ReactNode; children: ReactNode; open?: boolean }) {
  const [open, setOpen] = useState(start);
  return (
    <details open={open} className="group border-t border-line first:border-t-0">
      <summary onClick={(e) => { e.preventDefault(); setOpen((x) => !x); }} className={`flex cursor-pointer list-none flex-wrap items-baseline justify-between gap-x-4 gap-y-1 px-5 py-3 text-label [&::-webkit-details-marker]:hidden ${open ? "font-bold" : ""}`}>
        <span><span aria-hidden="true" className="inline-block w-4 text-soft">{open ? "▾" : "▸"}</span>{label}</span>
        {preview && <span className="text-caption font-normal text-soft">{preview}</span>}
      </summary>
      {open && <div className="mx-3 mb-3 flex flex-col gap-stack rounded-button bg-accent-faint px-4 py-3 text-body">{children}</div>}
    </details>
  );
}

/** 접기 줄 묶음 상자. title: 맨 위 '궁금하면 열어 보세요' 같은 머리줄. */
export function Folds({ title, children, label }: { title?: string; children: ReactNode; label?: string }) {
  return (
    <section aria-label={label ?? title ?? "더 보기"} className="overflow-hidden rounded-card border border-line bg-surface shadow-card">
      {title && <p className="px-5 pt-3 pb-1 text-caption font-bold text-soft">{title}</p>}
      {children}
    </section>
  );
}

/** 보조 버튼 (테두리만, 축소안 v5 ghost): 화면에 진한 버튼은 하나뿐이라 나머지는 이것. */
export function Ghost({ children, onClick, disabled }: { children: ReactNode; onClick?: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      className="inline-flex min-h-11 items-center gap-2 rounded-button border-2 border-accent bg-surface px-5 text-label font-bold text-accent-ink hover:bg-accent-soft disabled:opacity-(--state-disabled-opacity)">{children}</button>
  );
}

/** 큰 주 버튼 (꾸미기안_뭉치 .big): 화면마다 하나. 아래 진한 보라 그림자로 눌리는 느낌. */
export function BigButton({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return (
    <button type="button" onClick={onClick}
      className="inline-flex h-13 items-center gap-2 rounded-button bg-button px-6 text-lead font-bold text-button-fg shadow-cta hover:bg-button-hover active:translate-y-0.5 active:shadow-none">{children}</button>
  );
}

/** 제목: 강조할 말에 배 색 밑줄 (꾸미기안_뭉치 .h1 em). parts = [앞, 강조, 뒤] */
export function Title({ parts }: { parts: readonly [string, string, string] }) {
  return <>{parts[0]}<em className="mark-belly">{parts[1]}</em>{parts[2]}</>;
}
