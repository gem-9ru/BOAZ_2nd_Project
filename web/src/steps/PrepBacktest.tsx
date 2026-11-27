import type { Result } from "../api";
import { Card, md } from "../ui";

/** 예측이 맞았나? (기존 AN-05 검증 카드): 앞 날짜로 마지막 날을 예측해 실제와 비교. ③ 준비하기 접기 안에 들어간다. */
export function Backtest({ r }: { r: Result }) {
  const bt = r.backtest;
  const allIn = bt.arms?.every((a) => a.visits.inside && a.link_clicks.inside);
  return (
    <>
      {bt.ok && bt.arms && (
        <Card title="예측이 맞았나? (검증)"
          summary={`${bt.train_days?.length ? (bt.train_days.length > 1 ? `${md(bt.train_days[0])}~${md(bt.train_days[bt.train_days.length - 1])}` : md(bt.train_days[0])) : ""} 자료로 ${md(bt.test_day)}을 예측 → ${allIn ? "실제 A·B 모두 범위 안" : "범위를 벗어난 세트가 있어요"}`}>
          <ul className="grid gap-3 sm:grid-cols-2">
            {bt.arms.map((a, i) => (
              <li key={a.name} className="rounded-button bg-bg px-4 py-3 text-body">
                <p className="font-semibold">{"AB"[i] ?? a.name}</p>
                <p>클릭 예측 {a.link_clicks.lo}~{a.link_clicks.hi}번 · 실제 {a.link_clicks.actual}번 {a.link_clicks.inside ? "✓" : "✕"}</p>
                <p>방문자 예측 {a.visits.lo}~{a.visits.hi}명 · 실제 {a.visits.actual}명 {a.visits.inside ? "✓" : "✕"}</p>
              </li>
            ))}
          </ul>
          <p className="text-caption text-soft">(한 번 해 본 결과라 참고용) {bt.note}</p>
        </Card>
      )}
    </>
  );
}
