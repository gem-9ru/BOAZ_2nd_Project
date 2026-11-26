import type { ReactNode } from "react";
import type { Segment } from "../../../../lib/api";
import { compact } from "../../../../lib/format";
import { GENDER_LABEL, ageSpan, ageSpanLabel, genderFrom } from "../../../../lib/settings";
import MonthBars from "./MonthBars";

const TREND_SOURCE: Record<"search" | "shopping", string> = { search: "네이버 검색", shopping: "네이버 쇼핑 클릭" };

/** 3) 손님 무리 카드: 하나를 고른다. 고른 카드 아래에 연령 그림(또는 직접 정하기)을 붙인다. */
/** 카드 제목 옆 한 줄: 누가 찾나 ('30~40대 여성'). 자료가 없으면 '누가 찾는지 자료 없음'. */
function who(seg: Segment): string {
  if (!seg.audience) return "누가 클릭하는지 자료 없음";
  const g = genderFrom(seg.audience.female);
  return `${ageSpanLabel(ageSpan(seg.audience.ages).groups)}${g === "all" ? " 남녀" : ` ${GENDER_LABEL[g]}`}`;
}

/** '로/으로': 받침이 있으면(ㄹ 받침 빼고) '으로' */
function euro(word: string): string {
  const c = word.charCodeAt(word.length - 1) - 0xac00;
  if (c < 0 || c > 11171) return "(으)로";
  return c % 28 === 0 || c % 28 === 8 ? "로" : "으로";
}

/** 무리 크기: 전체 검색 중 몇 %인지 (무리 검색 수 합 기준). */
function shareOf(seg: Segment, all: Segment[]): number {
  const total = all.reduce((n, s) => n + s.total_qc, 0);
  return total > 0 ? Math.round((seg.total_qc / total) * 100) : 0;
}

export default function SegmentCards({ segments, selected, dropped, onPick, onResearch, selectedDetail, product = "" }: {
  segments: Segment[];
  product?: string;
  selected?: Segment;
  dropped: string[];
  onPick: (seg: Segment) => void;
  onResearch: () => void;
  selectedDetail?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <span className="text-caption font-semibold text-soft">손님 무리</span>
      <p className="-mt-1 text-small text-soft">같은 목적으로 찾는 손님끼리 묶었어요 (선물로 / 시즌에 / 상품 자체로). 광고를 보여 줄 무리를 하나 골라 주세요.</p>
      <div role="radiogroup" aria-label="광고를 보여 줄 손님" className="flex flex-col gap-2.5">
        {segments.map((seg) => {
          const on = selected?.intent === seg.intent;
          const words = seg.keywords.filter((k) => !dropped.includes(k));
          const leadOff = dropped.includes(seg.lead);
          const lineId = `seg-line-${seg.intent}`;
          return (
            <div key={seg.intent}
              className={`flex flex-col gap-3 rounded-card border p-4 transition-colors ${on ? "border-accent bg-accent-soft" : "border-line bg-paper"}`}>
              <label className="flex cursor-pointer flex-col gap-2.5 has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-4 has-[:focus-visible]:outline-accent">
                <span className="flex items-center gap-2">
                  <input type="radio" name="segment" value={seg.intent} checked={on} onChange={() => onPick(seg)}
                    aria-label={seg.label} aria-describedby={lineId} className="sr-only" />
                  <span aria-hidden className={`grid size-4 shrink-0 place-items-center rounded-badge border ${on ? "border-accent bg-accent" : "border-line"}`}>
                    {on && <i className="block size-1.5 rounded-badge bg-on-accent" />}
                  </span>
                  <strong className="text-body font-semibold">{seg.label}</strong>
                  <span className="ml-auto shrink-0 rounded-badge bg-sunk px-2 py-0.5 text-caption text-ink">{who(seg)}</span>
                </span>
                <span id={lineId} className="text-caption leading-relaxed">
                  {seg.line || (seg.audience ? "" : "누가 클릭하는지 자료가 아직 없어요")}
                </span>
                {seg.trend && <MonthBars monthly={seg.trend.monthly} />}
                {seg.trend?.peak_month && (
                  <span className="text-small text-soft">
                    {seg.trend.seasonal ? `${seg.trend.peak_month}월에 가장 많이 찾아요` : "달마다 비슷하게 찾아요"}
                    {seg.trend_source ? ` (이 무리 검색어 ${Math.min(5, seg.keywords.length)}개 묶음, ${TREND_SOURCE[seg.trend_source]} 기준)` : ""}
                  </span>
                )}
                {segments.length > 1 && (
                  <span className="flex items-center gap-2">
                    <span aria-hidden className="h-1.5 flex-1 overflow-hidden rounded-badge border border-line bg-paper">
                      <span className={`block h-full ${on ? "bg-accent" : "bg-soft"}`} style={{ width: `${shareOf(seg, segments)}%` }} />
                    </span>
                    <span className="shrink-0 text-caption text-soft">전체 검색의 {shareOf(seg, segments)}%</span>
                  </span>
                )}
                <span className="text-small text-soft">주로 찾는 말: {seg.lead} · 이 무리 전체 한 달 {compact(seg.total_qc)}번</span>
                {seg.audience && product && !seg.lead.replace(/\s/g, "").includes(product.replace(/\s/g, "")) && (
                  <span className="text-caption text-warn">
                    ▲ 이 무리의 나이·성별은 '{seg.lead}'{euro(seg.lead)} 클릭한 사람 자료예요. '{product}'를 찾는 손님과 다를 수 있어요.
                  </span>
                )}
                {words.length > 1 && <span className="text-small text-soft">이렇게도 찾아요: {words.filter((w) => w !== seg.lead).join(" · ")}</span>}
              </label>
              {leadOff && (
                <div className="flex flex-col gap-1.5">
                  <p className="text-small text-soft">주로 찾는 말 '{seg.lead}'를 뺐어요. 남긴 말로 손님을 다시 찾을 수 있어요.</p>
                  <button type="button" onClick={onResearch}
                    className="self-start rounded-button border border-accent bg-paper px-3 py-1.5 text-caption font-semibold text-accent-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
                    이 말로 손님 다시 찾기
                  </button>
                </div>
              )}
              {on && selectedDetail}
            </div>
          );
        })}
      </div>
    </div>
  );
}
