import { useEffect, useState } from "react";
import { audienceSplit } from "../../../../lib/api";
import { GENDER_LABEL, ageSpan, ageSpanLabel, genderFrom } from "../../../../lib/settings";

const AGE_ORDER = ["10", "20", "30", "40", "50", "60"];

/** 연령 막대 그림: 광고를 보여 줄 나이대(많이 찾는 이웃 나이대까지) + 성별 비중.
 *  split(검색어·분야)을 주면 나이대마다 여성·남성 비중을 따로 받아 막대를 둘로 나눠 그린다 (못 받으면 한 덩어리). */
export default function AgeFigure({ audience: aud, headline, caption = "광고를 보여 줄 사람", split }: {
  audience: { female: number; ages: Record<string, number>; top_age: string };
  headline?: string;
  caption?: string;
  split?: { keyword: string; category: string };
}) {
  const [fem, setFem] = useState<Record<string, number>>({});
  useEffect(() => {
    if (!split) return;
    let live = true;
    void audienceSplit(split.keyword, split.category, aud.ages).then((r) => { if (live) setFem(r); });
    return () => { live = false; };
  }, [split?.keyword, split?.category, aud.ages]);
  const hasSplit = Object.keys(fem).length > 0;
  const gender = genderFrom(aud.female);
  const span = ageSpan(aud.ages);
  const inSpan = (a: string) => span.groups.includes(a);
  const top = span.groups.reduce((b, a) => ((aud.ages[a] ?? 0) > (aud.ages[b] ?? 0) ? a : b));
  const who = `${ageSpanLabel(span.groups)} ${gender === "all" ? "" : GENDER_LABEL[gender]}`.trim();
  const ages = AGE_ORDER.filter((a) => a in aud.ages);
  const max = Math.max(...ages.map((a) => aud.ages[a] ?? 0)) || 1;

  return (
    <figure className="flex flex-col gap-4 rounded-card border border-line bg-paper p-4">
      <figcaption className="flex items-end justify-between gap-3">
        <span className="flex flex-col gap-0.5">
          <span className="text-caption text-soft">{caption}</span>
          <strong className="text-number font-bold leading-tight tracking-tight">{who}</strong>
        </span>
        <span className="mb-1 shrink-0 rounded-badge bg-sunk px-2.5 py-1 text-small text-soft">
          여성 {Math.round(aud.female * 100)}% · 남성 {100 - Math.round(aud.female * 100)}%
        </span>
      </figcaption>
      <div className="flex flex-col gap-1.5">
        <div className="flex h-28 items-end gap-2 border-b border-line" role="img"
          aria-label={`연령대별 검색 비중: ${ages.map((a) => `${a}대 ${Math.round((aud.ages[a] ?? 0) * 100)}%${a in fem ? ` (여성 ${Math.round(fem[a]! * 100)}%)` : ""}`).join(", ")}`}>
          {ages.map((a) => {
            const share = aud.ages[a] ?? 0;
            const isTop = inSpan(a);
            return (
              <div key={a} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
                <span aria-hidden className={`text-small tabular-nums ${isTop ? "font-bold text-accent-ink" : "text-soft"}`}>
                  {Math.round(share * 100)}%
                </span>
                {a in fem ? (
                  // 위 = 남성(연하게), 아래 = 여성(진하게)
                  <div aria-hidden className="flex w-full max-w-10 flex-col overflow-hidden rounded-t-md"
                    style={{ height: `${Math.max(4, Math.round((share / max) * 76))}px` }}>
                    <div className={isTop ? "bg-accent-soft" : "bg-sunk"} style={{ flexGrow: 1 - fem[a]! }} />
                    <div className={isTop ? "bg-accent" : "bg-line"} style={{ flexGrow: fem[a]! }} />
                  </div>
                ) : (
                  <div aria-hidden
                    className={`w-full max-w-10 rounded-t-md ${isTop ? "bg-accent" : "bg-line"}`}
                    style={{ height: `${Math.max(4, Math.round((share / max) * 76))}px` }} />
                )}
              </div>
            );
          })}
        </div>
        <div aria-hidden className="flex gap-2">
          {ages.map((a) => (
            <span key={a} className={`flex-1 text-center text-small ${inSpan(a) ? "font-semibold" : "text-soft"}`}>{a}대</span>
          ))}
        </div>
      </div>
      {hasSplit && (
        <p aria-hidden className="flex items-center gap-3 text-small text-soft">
          <span className="inline-flex items-center gap-1"><i className="inline-block size-2.5 rounded-sm bg-accent" />여성</span>
          <span className="inline-flex items-center gap-1"><i className="inline-block size-2.5 rounded-sm bg-accent-soft" />남성</span>
          <span>막대 안에서 아래가 여성, 위가 남성이에요</span>
        </p>
      )}
      {span.groups.length > 1 && (
        <p className="text-small text-soft">
          {top}대가 가장 많이 찾고, 옆 나이대도 많이 찾아서 함께 넣었어요 (전체의 {Math.round(span.groups.reduce((t, a) => t + (aud.ages[a] ?? 0), 0) * 100)}%).
        </p>
      )}
      {headline && (
        <p className="rounded-button bg-accent-soft px-3 py-2.5 text-caption leading-relaxed text-ink">{headline}</p>
      )}
    </figure>
  );
}
