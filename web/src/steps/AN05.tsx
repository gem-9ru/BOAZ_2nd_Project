import type { Result } from "../api";
import { Simulator } from "../blocks/Simulator";
import { Card, won } from "../ui";

/** AN-05 이 칸을 바꾸면: 실측으로 맞춘 모델의 예측 범위 + 다음 테스트 예산(Test & Roll) + 백테스트. */
export function AN05({ r }: { r: Result }) {
  const bt = r.backtest;
  return (
    <>
      <Simulator r={r} />
      {bt.ok && bt.arms && (
        <Card title="이 계산, 맞은 적 있어요?">
          <p className="text-body">{bt.train_days?.map((d) => d.slice(5).replace("-", "/")).join("~")} 자료로 {bt.test_day?.slice(5).replace("-", "/")}을 예측해 봤어요.</p>
          <ul className="grid gap-3 sm:grid-cols-2">
            {bt.arms.map((a) => (
              <li key={a.name} className="rounded-button bg-bg px-4 py-3 text-body">
                <p className="font-semibold">{a.name} <span className="text-caption text-soft">({won(a.budget)} 쓴 날)</span></p>
                <p>클릭 예측 {a.link_clicks.lo}~{a.link_clicks.hi} · 실제 {a.link_clicks.actual} {a.link_clicks.inside ? "✓" : "✕"}</p>
                <p>방문 예측 {a.visits.lo}~{a.visits.hi} · 실제 {a.visits.actual} {a.visits.inside ? "✓" : "✕"}</p>
              </li>
            ))}
          </ul>
          <p className="text-caption text-soft">{bt.note}</p>
        </Card>
      )}
    </>
  );
}
