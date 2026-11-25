import type { ReactNode } from "react";
import type { Segment } from "../../../../lib/api";
import { compact } from "../../../../lib/format";
import MonthBars from "./MonthBars";

const TREND_SOURCE: Record<"search" | "shopping", string> = { search: "검색어 트렌드", shopping: "쇼핑인사이트 클릭" };

/** 3) 손님 무리 카드: 하나를 고른다. 고른 카드 아래에 연령 그림(또는 직접 정하기)을 붙인다. */
export default function SegmentCards({ segments, selected, dropped, onPick, onResearch, selectedDetail }: {
  segments: Segment[];
  selected?: Segment;
  dropped: string[];
  onPick: (seg: Segment) => void;
  onResearch: () => void;
  selectedDetail?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2.5">
      <span className="text-caption font-semibold text-soft">손님 무리</span>
      <p className="-mt-1 text-small text-soft">이 말들을 찾는 손님을 무리로 나눠 봤어요. 광고를 보여 줄 무리를 하나 골라 주세요.</p>
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
                </span>
                <span id={lineId} className="text-caption leading-relaxed">
                  {seg.line || (seg.audience ? "" : "누가 찾는지 자료가 아직 없어요")}
                </span>
                {seg.trend && <MonthBars monthly={seg.trend.monthly} />}
                <span className="text-small text-soft">대표 검색어: {seg.lead} · 월 {compact(seg.total_qc)}회</span>
                {words.length > 0 && <span className="text-small text-soft">함께 찾는 말: {words.join(" · ")}</span>}
                {seg.trend && seg.trend_source && (
                  <span className="text-small text-soft">달별 자료: {TREND_SOURCE[seg.trend_source]}</span>
                )}
              </label>
              {leadOff && (
                <div className="flex flex-col gap-1.5">
                  <p className="text-small text-soft">대표 검색어 '{seg.lead}'를 뺐어요. 남긴 말로 손님을 다시 찾을 수 있어요.</p>
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
