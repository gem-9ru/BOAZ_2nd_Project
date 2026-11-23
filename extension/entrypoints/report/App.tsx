import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Analysis } from "../../lib/api";
import { pct, pctRange } from "../../lib/format";
import { GradeBadge } from "../sidepanel/ui/GradeBadge";

// dataviz 검사 통과 팔레트 (밝은 화면, 배경 #FFFDF8): A #3D6FB8 / B #E07A2E. B는 대비 3:1 미만이라 항상 글자로 같이 적는다.
const SERIES = "#3D6FB8";
const B_COLOR = "#E07A2E";
const GRID = "#E2DCD0";
const INK = "#16213A";
const SOFT = "#4A5568";

function Panel({ title, children, note }: { title: string; children: React.ReactNode; note?: string }) {
  return (
    <section className="bg-paper border border-line rounded-2xl p-6 flex flex-col gap-3 min-w-0">
      <h2 className="text-[20px] font-bold">{title}</h2>
      {children}
      {note && <p className="text-[14px] text-soft">{note}</p>}
    </section>
  );
}

function Funnel({ f }: { f: Analysis["charts"]["funnel"] }) {
  const steps = [
    { label: "광고를 본 횟수 (노출)", value: f.impressions },
    { label: "링크를 누른 횟수 (링크 클릭)", value: f.link_clicks },
    { label: "가게 페이지에 도착 (랜딩 페이지 조회)", value: f.landing_page_views },
  ];
  return (
    <ol className="flex flex-col gap-3">
      {steps.map((s, i) => {
        const prev = i > 0 ? steps[i - 1]!.value : null;
        return (
          <li key={s.label} className="grid grid-cols-[1fr_auto] gap-x-4 items-center">
            <span className="text-[15px] text-soft">{s.label}</span>
            <strong className="text-[28px] tabular-nums">{s.value.toLocaleString()}</strong>
            <div className="h-2 rounded-r bg-line col-span-2">
              <div className="h-2 rounded-r" style={{ background: SERIES, width: `${steps[0]!.value > 0 ? Math.max((s.value / steps[0]!.value) * 100, 1) : 0}%` }} />
            </div>
            {prev !== null && prev > 0 && (
              <span className="text-[13px] text-soft col-span-2">앞 단계의 {pct(s.value / prev)}</span>
            )}
          </li>
        );
      })}
    </ol>
  );
}

function RangeBar({ e }: { e: NonNullable<Analysis["expect"]> }) {
  const max = Math.max(e.current[1], e.expected[1]) * 1.15;
  const row = (label: string, r: [number, number], color: string) => (
    <div className="grid grid-cols-[96px_1fr_150px] items-center gap-3">
      <span className="text-[14px] text-soft">{label}</span>
      <div className="relative h-4 bg-cream rounded">
        <div className="absolute h-4 rounded" style={{ left: `${(r[0] / max) * 100}%`, width: `${((r[1] - r[0]) / max) * 100}%`, background: color }} />
      </div>
      <span className="text-[15px] tabular-nums">{pctRange(r)}</span>
    </div>
  );
  return (
    <div className="flex flex-col gap-3">
      {row("지금", e.current, SERIES)}
      {row("앞으로", e.expected, B_COLOR)}
      <div className="flex items-center gap-2 text-[14px] text-soft">
        {e.label} · 90% 범위 <GradeBadge grade={e.grade} />
      </div>
    </div>
  );
}

export default function ReportApp({ result: r }: { result: Analysis }) {
  const daily = r.charts.daily.map((d) => ({ ...d, ctrPct: d.ctr === null ? null : +(d.ctr * 100).toFixed(2), day: d.date.slice(5) }));
  return (
    <main className="min-h-screen bg-cream text-ink p-10 flex flex-col gap-6 max-w-[1840px] mx-auto">
      <header className="flex items-end justify-between gap-6">
        <div>
          <p className="text-[15px] text-soft">광고 결과 보고서</p>
          <h1 className="text-[36px] font-bold">{r.finding.title}</h1>
          <p className="text-[18px] max-w-[70ch]">{r.finding.message}</p>
        </div>
        {r.changes[0] && (
          <div className="bg-ink text-cream rounded-2xl px-6 py-4 max-w-[480px]">
            <p className="text-[14px] text-line">다음 할 일</p>
            <p className="text-[20px] font-bold">{r.changes[0].label} → {r.changes[0].new}</p>
          </div>
        )}
      </header>

      <div className="grid grid-cols-3 gap-6">
        <Panel title="손님이 어디까지 왔나">
          <Funnel f={r.charts.funnel} />
        </Panel>
        <Panel title="일별 링크 클릭률 (%)" note="노출이 0인 날은 비워 뒀어요.">
          <div className="h-56">
            <ResponsiveContainer>
              <LineChart data={daily} margin={{ top: 8, right: 16, bottom: 0, left: -8 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="day" stroke={SOFT} tickLine={false} />
                <YAxis stroke={SOFT} tickLine={false} axisLine={false} />
                <Tooltip formatter={(v) => [`${v}%`, "링크 클릭률"]} />
                <Line dataKey="ctrPct" stroke={SERIES} strokeWidth={2} dot={{ r: 4 }} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        <Panel title="일별 1,000회 노출당 비용 (원)">
          <div className="h-56">
            <ResponsiveContainer>
              <LineChart data={daily} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid stroke={GRID} vertical={false} />
                <XAxis dataKey="day" stroke={SOFT} tickLine={false} />
                <YAxis stroke={SOFT} tickLine={false} axisLine={false} />
                <Tooltip formatter={(v) => [`${Number(v).toLocaleString()}원`, "CPM"]} />
                <Line dataKey="cpm" stroke={SERIES} strokeWidth={2} dot={{ r: 4 }} connectNulls={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <div className="grid grid-cols-3 gap-6">
        <Panel title="노출 위치별 지출 (원)">
          <div className="h-64">
            <ResponsiveContainer>
              <BarChart data={topPlacements(r.charts.placement, 7)} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 24 }}>
                <CartesianGrid stroke={GRID} horizontal={false} />
                <XAxis type="number" stroke={SOFT} tickLine={false} />
                <YAxis type="category" dataKey="placement" width={170} stroke={SOFT} tickLine={false} />
                <Tooltip formatter={(v) => [`${Number(v).toLocaleString()}원`, "지출"]} />
                <Bar dataKey="spend" fill={SERIES} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
        {r.expect && (
          <Panel title={r.status === "hold" ? "기간을 늘리면 범위가 좁혀져요" : "바꾸면 이 범위"}>
            <RangeBar e={r.expect} />
          </Panel>
        )}
        {r.ab && (
          <Panel title="두 광고 비교 (같은 돈)" note="5천 원 규모라 승패를 단정하지 않고 확률로 말해요.">
            <div className="flex flex-col gap-2 text-[16px]">
              <p><span className="inline-block size-3 rounded-full mr-2" style={{ background: SERIES }} />A {abName(r.ab.a, "A")}</p>
              <p><span className="inline-block size-3 rounded-full mr-2" style={{ background: B_COLOR }} />B {abName(r.ab.b, "B")}</p>
              <p className="text-[32px] font-bold" style={{ color: INK }}>B가 나을 확률 약 {Math.round(r.ab.prob_b_better * 100)}%</p>
            </div>
          </Panel>
        )}
      </div>

      <table aria-label="일별 숫자" className="text-[14px] bg-paper rounded-2xl overflow-hidden">
        <thead>
          <tr className="text-left text-soft"><th className="p-3">날짜</th><th className="p-3">지출(원)</th><th className="p-3">링크 클릭률</th><th className="p-3">CPM(원)</th></tr>
        </thead>
        <tbody>
          {r.charts.daily.map((d) => (
            <tr key={d.date} className="border-t border-line">
              <td className="p-3">{d.date}</td>
              <td className="p-3 tabular-nums">{d.spend.toLocaleString()}</td>
              <td className="p-3 tabular-nums">{d.ctr === null ? "—" : pct(d.ctr, 2)}</td>
              <td className="p-3 tabular-nums">{d.cpm === null ? "—" : d.cpm.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}

/** 'A_자동노출위치' → '자동노출위치' (앞 글자 A/B가 범례와 겹치지 않게). */
function abName(name: string, letter: string): string {
  return name.replace(new RegExp(`^${letter}[_\\s.-]+`, "i"), "");
}

type PlacementRow = { placement: string; spend: number; link_clicks: number };

/** 노출 위치가 많으면 이름이 겹쳐 빠진다 → 지출 상위 n개 + 나머지는 '기타 N곳'으로 합친다. */
export function topPlacements(rows: PlacementRow[], n: number): PlacementRow[] {
  const sorted = [...rows].sort((a, b) => b.spend - a.spend);
  if (sorted.length <= n) return sorted;
  const rest = sorted.slice(n);
  return [...sorted.slice(0, n), {
    placement: `기타 ${rest.length}곳`,
    spend: rest.reduce((s, x) => s + x.spend, 0),
    link_clicks: rest.reduce((s, x) => s + x.link_clicks, 0),
  }];
}
