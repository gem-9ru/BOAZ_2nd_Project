import type { ProductStats as Stats } from "../../../../lib/api";
import { times } from "../../../../lib/format";
import { GENDER_LABEL, ageSpan, ageSpanLabel, genderFrom } from "../../../../lib/settings";
import AgeFigure from "./AgeFigure";
import MonthBars from "./MonthBars";
import { nowLine } from "./when";

/** '은/는': 받침이 있으면 '은' */
function topic(word: string): string {
  const c = word.charCodeAt(word.length - 1) - 0xac00;
  return c < 0 || c > 11171 ? "은(는)" : c % 28 ? "은" : "는";
}

/** 같은 분야 평균보다 눈에 띄게(1.2배 이상) 많이 찾는 나이대·성별 한 줄. 없으면 null. */
export function vsCategory(aud: { index?: Record<string, number>; top_age: string } | null): string | null {
  const idx = aud?.index;
  if (!idx) return null;
  const parts: string[] = [];
  const age = idx[aud!.top_age];
  if (age && age >= 1.2) parts.push(`${aud!.top_age}대가 ${age.toFixed(1)}배`);
  const sex = (idx.female ?? 0) >= 1.2 ? ["여성", idx.female!] as const : (idx.male ?? 0) >= 1.2 ? ["남성", idx.male!] as const : null;
  if (sex) parts.push(`${sex[0]}이 ${sex[1].toFixed(1)}배`);
  return parts.length ? `네이버 쇼핑 클릭으로 보면 같은 분야 평균보다 ${parts.join(", ")} 많아요 (1.2배 이상만 보여 줘요 · 이 도구 기준).` : null;
}

/** 내 상품 그대로: 한 달 검색 수 + (분야를 알면) 찾는 사람의 연령·성별(나이대마다 여성·남성) + 몇 월에 많이 찾나. */
export default function ProductStats({ stats, hasCategory, category }: { stats: Stats; hasCategory: boolean; category?: string }) {
  const trend = stats.trend;
  const now = trend ? nowLine(trend.monthly) : null;
  const vs = vsCategory(stats.audience);
  const who = stats.audience
    ? `${ageSpanLabel(ageSpan(stats.audience.ages).groups)}${(() => { const g = genderFrom(stats.audience!.female); return g === "all" ? "" : ` ${GENDER_LABEL[g]}`; })()}`
    : null;
  const line = [`한 달 ${times(stats.total_qc, stats.under)}`, trend?.peak_month ? `'${stats.keyword}'${topic(stats.keyword)} ${trend.peak_month}월에 가장 많이` : null, who ? `${who}${who.endsWith("대") ? "가" : "이"} 쇼핑에서 많이 클릭해요` : null]
    .filter(Boolean).join(" · ");
  return (
    <details className="group flex flex-col gap-2.5 rounded-card border border-line bg-paper p-4">
      <summary className="flex cursor-pointer list-none items-start justify-between gap-3 [&::-webkit-details-marker]:hidden">
        <span className="flex flex-col gap-0.5">
          <span className="text-caption font-semibold text-soft">'{stats.keyword}' 검색</span>
          <span className="text-body">{line}</span>
        </span>
        <span className="shrink-0 text-caption font-semibold text-soft">
          <span className="group-open:hidden">자세히 ▾</span><span className="hidden group-open:inline">접기 ▴</span>
        </span>
      </summary>
      <div className="mt-3 flex flex-col gap-2.5">
      <div className="flex items-end justify-between gap-3 rounded-card border border-line bg-paper p-4">
        <span className="flex flex-col gap-0.5">
          <span className="text-caption text-soft">한 달에 찾는 횟수</span>
          <strong className="text-number font-bold leading-tight tracking-tight tabular-nums">
            {stats.under ? times(stats.total_qc, stats.under) : `${stats.total_qc.toLocaleString()}번`}
          </strong>
        </span>
        {stats.mobile != null && (
          <span className="mb-1 shrink-0 rounded-badge bg-sunk px-2.5 py-1 text-small text-soft">
            모바일 {Math.round(stats.mobile * 100)}% · PC {100 - Math.round(stats.mobile * 100)}%
          </span>
        )}
      </div>
      {vs && <p className="text-caption">{vs}</p>}
      {stats.audience
        ? <AgeFigure audience={stats.audience} caption="네이버 쇼핑에서 이 말로 클릭한 사람"
            split={category ? { keyword: stats.keyword, category } : undefined} />
        : (
          <p className="text-small text-soft">
            {hasCategory ? "이 말로 쇼핑에서 클릭한 사람의 나이·성별 자료는 네이버에 아직 없어요." : "분야를 고르면 누가 클릭하는지도 보여 드릴게요."}
          </p>
        )}
      {trend?.peak_month && (
        <div className="flex flex-col gap-2 rounded-card border border-line bg-paper p-4">
          <span className="text-caption text-soft">언제 많이 찾나요?</span>
          <strong className="text-body font-semibold">
            {trend.peak_month}월에 가장 많이 찾아요{trend.seasonal ? "" : " · 다른 달과 크게 차이 나지 않아요"}
          </strong>
          {now && <p className="text-caption">{now}</p>}
          <MonthBars monthly={trend.monthly} />
          <span className="text-small text-soft">'{stats.keyword}' 한 단어 · 지난 12달 {stats.trend_source === "shopping" ? "네이버 쇼핑 클릭" : "네이버 검색"} 기준 · 가장 많은 달을 100으로 본 비율. 가장 많은 달이 평균의 1.2배 이상이면 철이 있다고 봐요 (이 도구 기준). 손님 무리 카드는 무리의 검색어를 묶어 봐서 달이 다를 수 있어요.</span>
        </div>
      )}
      </div>
    </details>
  );
}
