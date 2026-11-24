import type { Arm, Result } from "../api";
import { Card, Grade, won } from "../ui";

type Row = { label: string; term?: string; get: (a: Arm) => number | null; show: (x: number) => string; higher?: boolean };
const RATES: Row[] = [
  { label: "1,000원으로 데려온 방문자", get: (a) => a.visits_per_1000won, show: (x) => `${x.toFixed(1)}명`, higher: true },
  { label: "클릭 1번에 드는 돈", term: "(CPC)", get: (a) => a.cpc, show: won, higher: false },
  { label: "광고 1,000번 보여주는 데 드는 돈", term: "(CPM)", get: (a) => a.cpm, show: won, higher: false },
  { label: "본 사람 중 누른 비율", term: "(CTR)", get: (a) => a.ctr, show: (x) => `${(x * 100).toFixed(2)}% · 100명 중 약 ${Math.round(x * 100)}명`, higher: true },
];
const TOTALS: Row[] = [
  { label: "쓴 돈", get: (a) => a.spend, show: won },
  { label: "본 횟수", term: "(노출)", get: (a) => a.impressions, show: (x) => `${x.toLocaleString()}번` },
  { label: "누른 횟수", term: "(링크 클릭)", get: (a) => a.link_clicks, show: (x) => `${x.toLocaleString()}번` },
  { label: "들어온 사람", term: "(랜딩 페이지 도착)", get: (a) => a.landing_page_views, show: (x) => `${x.toLocaleString()}명` },
];

/** 4 핵심 숫자 카드: 효율(비용·비율)을 위, 총량을 아래. 나은 쪽은 ▲와 글자로 (색만으로 구분하지 않기). */
export function KeyNumbers({ r }: { r: Result }) {
  const arms = r.summary.arms.slice(0, 2);
  const cell = (row: Row, a: Arm, i: number) => {
    const x = row.get(a);
    const others = arms.map(row.get);
    const best = row.higher === undefined || others.some((o) => o == null) ? null
      : row.higher ? Math.max(...(others as number[])) : Math.min(...(others as number[]));
    const few = a.link_clicks < 10 && row.label !== "쓴 돈" && row.label !== "본 횟수";
    return (
      <td key={i} className={`py-2 px-3 text-right tabular-nums ${few ? "text-soft" : ""}`}>
        {x == null ? "–" : row.show(x)}
        {arms.length > 1 && best != null && x === best && <span className="ml-1 text-adopt" aria-label="더 나음">▲</span>}
        {few && <span className="block text-caption">참고용</span>}
      </td>
    );
  };
  const rows = (list: Row[]) => list.map((row) => (
    <tr key={row.label} className="border-t border-line">
      <th scope="row" className="py-2 pr-3 text-left font-normal">{row.label} {row.term && <span className="text-caption text-soft">{row.term}</span>}</th>
      {arms.map((a, i) => cell(row, a, i))}
    </tr>
  ));
  return (
    <Card id="numbers" title="핵심 숫자">
      <div className="overflow-x-auto">
        <table className="w-full text-body">
          <thead>
            <tr className="text-caption text-soft">
              <th className="text-left font-normal pb-2" />
              {arms.map((a, i) => (
                <th key={a.name} className="text-right font-semibold pb-2 px-3">
                  <span className="inline-block size-2.5 rounded-badge mr-1.5 align-middle" style={{ background: i ? "var(--tone-series-b)" : "var(--tone-series-a)" }} />
                  {"AB"[i]} · {a.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>{rows(RATES)}</tbody>
          <tbody className="text-soft">{rows(TOTALS)}</tbody>
        </table>
      </div>
      <p className="text-caption text-soft flex items-center gap-2"><Grade g="A" /> ▲ 더 나은 쪽 · 지출 규모가 다르면 총량 비교는 참고만</p>
    </Card>
  );
}
