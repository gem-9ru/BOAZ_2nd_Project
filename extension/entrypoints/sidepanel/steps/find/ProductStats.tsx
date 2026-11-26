import type { ProductStats as Stats } from "../../../../lib/api";
import AgeFigure from "./AgeFigure";
import MonthBars from "./MonthBars";

/** 내 상품 그대로: 한 달 검색 수 + (분야를 알면) 찾는 사람의 연령·성별(나이대마다 여성·남성) + 몇 월에 많이 찾나. */
export default function ProductStats({ stats, hasCategory, category }: { stats: Stats; hasCategory: boolean; category?: string }) {
  const trend = stats.trend;
  return (
    <div className="flex flex-col gap-2.5">
      <span className="text-caption font-semibold text-soft">'{stats.keyword}' 검색</span>
      <div className="flex items-end justify-between gap-3 rounded-card border border-line bg-paper p-4">
        <span className="flex flex-col gap-0.5">
          <span className="text-caption text-soft">한 달 검색 수</span>
          <strong className="text-number font-bold leading-tight tracking-tight tabular-nums">
            {stats.total_qc.toLocaleString()}회
          </strong>
        </span>
        {stats.mobile != null && (
          <span className="mb-1 shrink-0 rounded-badge bg-sunk px-2.5 py-1 text-small text-soft">
            모바일 {Math.round(stats.mobile * 100)}% · PC {100 - Math.round(stats.mobile * 100)}%
          </span>
        )}
      </div>
      {stats.audience
        ? <AgeFigure audience={stats.audience} caption="이 상품을 찾는 사람"
            split={category ? { keyword: stats.keyword, category } : undefined} />
        : (
          <p className="text-small text-soft">
            {hasCategory ? "이 말을 찾는 사람의 나이·성별 자료는 네이버에 아직 없어요." : "분야를 고르면 누가 찾는지도 보여 드릴게요."}
          </p>
        )}
      {trend?.peak_month && (
        <div className="flex flex-col gap-2 rounded-card border border-line bg-paper p-4">
          <span className="text-caption text-soft">언제 많이 찾나요?</span>
          <strong className="text-body font-semibold">
            {trend.peak_month}월에 가장 많이 찾아요{trend.seasonal ? "" : " · 다른 달과 크게 차이 나지 않아요"}
          </strong>
          <MonthBars monthly={trend.monthly} />
          <span className="text-small text-soft">지난 12달 네이버 쇼핑 클릭 기준 · 가장 많은 달을 100으로 본 비율</span>
        </div>
      )}
    </div>
  );
}
