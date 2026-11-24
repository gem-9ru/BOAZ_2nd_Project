import type { Result } from "../api";
import { Card } from "../ui";

const SECTIONS = ["캠페인", "광고 세트", "광고"] as const;
type Kind = "변경" | "유지" | "검토" | "그대로";
const LOOK: Record<Kind, string> = { 변경: "bg-accent text-on-accent", 유지: "bg-ok-bg text-ink", 검토: "bg-warn-bg text-warn", 그대로: "bg-sunk text-soft" };

/** AN-03 내 세팅 카드: 광고 관리자 순서(캠페인 → 광고 세트 → 광고)로 칸별 변경·유지·검토 + 근거 한 줄. */
export function AN03({ r }: { r: Result }) {
  const m = r.matrix;
  const full = m.settings ?? [];
  const items: { path: string; kind: Kind; text: string; value?: string }[] = full.map((x) => ({ path: x.path, kind: x.kind, text: x.note, value: x.value }));
  if (!full.length && m.change?.path) items.push({ path: m.change.path, kind: "변경", text: `${m.change.new} — ${m.change.reason ?? ""}` });
  if (!full.length) m.keep.forEach((k) => items.push({ path: k.path, kind: "유지", text: `${k.value} — ${k.reason}` }));
  if (!full.length) m.watch.forEach((w) => { if (!items.some((x) => x.path === w.path)) items.push({ path: w.path, kind: "검토", text: w.text }); });
  const meta = r.alerts.filter((a) => a.screen === "AN-03");
  return (
    <Card title="광고 관리자 순서로 본 내 세팅">
      {SECTIONS.map((sec) => {
        const rows = items.filter((x) => x.path.split(" › ")[0] === sec);
        return (
          <section key={sec} className="flex flex-col gap-2">
            <h3 className="text-body font-bold">{sec}</h3>
            {rows.length ? rows.map((x) => (
              <div key={x.path + x.kind} className="flex flex-wrap items-start gap-3 rounded-button border border-line px-4 py-3">
                <span className={`rounded-badge px-2.5 py-0.5 text-caption font-bold ${LOOK[x.kind]}`}>{x.kind}</span>
                <div className="min-w-0 flex-1">
                  <p className="text-body font-semibold">{x.path.split(" › ")[1]}</p>
                  {x.value && <p className="text-caption">지금 값: {x.value}</p>}
                  <p className="text-caption text-soft">{x.text}</p>
                </div>
              </div>
            )) : <p className="text-caption text-soft">이번 결과로 바꿀 것 없어요.</p>}
          </section>
        );
      })}
      {meta.map((a) => <p key={a.kind} className="rounded-button bg-info-bg px-4 py-3 text-body">● {a.text} <span className="text-soft">{a.todo}</span></p>)}
      {!full.length && <p className="text-caption text-soft">확장 프로그램에서 넘어온 세팅값이 있으면 모든 칸을 보여 줘요. 지금은 결과 파일로 알 수 있는 칸만 보여요.</p>}
    </Card>
  );
}
