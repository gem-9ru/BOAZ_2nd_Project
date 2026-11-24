import type { Result } from "../api";
import { Funnel } from "../blocks/Funnel";
import { KeyNumbers } from "../blocks/KeyNumbers";
import { Card } from "../ui";
import { AlertLine, rowLevel, Signal } from "./shared";

const FUNNEL_ROWS = ["1", "2", "3", "4"];
const NAMES: Record<string, string> = { "1": "노출 단가 (CPM)", "2": "클릭률 (CTR)", "3": "클릭 후 도착", "4": "도착 후 행동" };

/** AN-02 어디서 막혔나: 퍼널 신호등 CPM → CTR → 도착 → 행동. 위에서부터 처음 막힌 단계가 고칠 곳. */
export function AN02({ r }: { r: Result }) {
  const rows = r.matrix.rows.filter((x) => FUNNEL_ROWS.includes(x.row));
  const alerts = r.alerts.filter((a) => a.screen === "AN-02");
  return (
    <>
      <Card title="퍼널 신호등">
        <ol className="flex flex-col gap-2" aria-label="퍼널 단계">
          {rows.map((x, i) => (
            <li key={x.row} className="flex items-start gap-3 rounded-button bg-bg px-4 py-3">
              <span className="mt-0.5"><Signal level={rowLevel(x)} /></span>
              <div className="flex-1">
                <p className="text-body font-semibold">{i + 1}. {NAMES[x.row]}</p>
                <p className="text-caption text-soft">{x.signal}{x.detail ? ` — ${x.detail}` : ""}</p>
              </div>
            </li>
          ))}
        </ol>
        <p className="text-caption text-soft">✓ 괜찮음 · ▲ 비교보다 나쁨 · ■ 기준 미달 · – 자료가 없거나 적음</p>
        {alerts.length > 0 && <ul className="flex flex-col gap-2">{alerts.map((a) => <AlertLine key={a.kind + a.text} a={a} />)}</ul>}
      </Card>
      <details className="group rounded-card border border-card-border bg-card">
        <summary className="cursor-pointer px-card py-4 text-body font-semibold text-details-fg">🔎 단계별 숫자와 범위 펼치기</summary>
        <div className="flex flex-col gap-group p-card pt-0">
          <KeyNumbers r={r} />
          <Funnel r={r} />
        </div>
      </details>
    </>
  );
}
