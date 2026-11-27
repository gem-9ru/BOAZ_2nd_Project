import { useState } from "react";
import type { Kind, Result } from "../api";
import { Card, Tabs } from "../ui";

const ORDER = ["캠페인", "광고 세트", "광고"];
const LOOK: Record<Kind, string> = { 테스트: "bg-accent text-on-accent", "다시 보기": "bg-warn-bg text-warn", 그대로: "bg-sunk text-soft" };
type Item = { field_id: string; path: string; kind: Kind; text: string; value?: string };

/** 내 세팅 칸 목록: 확장 프로그램이 넘긴 세팅이 있으면 전부, 없으면 결과 파일로 알 수 있는 칸만. 광고 관리자 순서. */
export function settingItems(r: Result): Item[] {
  const m = r.matrix;
  const full = m.settings ?? [];
  const items: Item[] = full.map((x) => ({ field_id: x.field_id, path: x.path, kind: x.kind, text: x.note, value: x.value }));
  // 받은 설정에 없는 칸도 결과 파일로 알 수 있으면 넣는다 (설정을 몇 칸만 받았어도 그대로·다시 보기 칸이 빠지지 않게)
  const add = (x: Item) => { if (!items.some((y) => y.path === x.path)) items.push(x); };
  if (m.change?.path) add({ field_id: m.change.field_id, path: m.change.path, kind: "테스트", text: m.change.reason ?? "", value: m.change.now ?? undefined });
  m.keep.forEach((k) => add({ field_id: k.field_id, path: k.path, kind: "그대로", text: k.reason, value: k.value }));
  m.watch.forEach((w) => add({ field_id: w.field_id, path: w.path, kind: "다시 보기", text: w.text }));
  items.sort((a, b) => ORDER.indexOf(a.path.split(" › ")[0]!) - ORDER.indexOf(b.path.split(" › ")[0]!));
  return items;
}

/** 접기 줄 미리보기: '테스트 1 · 다시 보기 2 · 그대로 1' */
export const settingPreview = (r: Result) => {
  const items = settingItems(r);
  return (["테스트", "다시 보기", "그대로"] as Kind[]).map((k) => `${k} ${items.filter((x) => x.kind === k).length}`).join(" · ");
};

/** 내 세팅 칸별 상태 (기존 AN-03): 광고 관리자 순서(캠페인 → 광고 세트 → 광고) 표 + 상태 탭(전체/테스트/다시 보기/그대로).
 *  테스트 행 = 바이올렛 왼쪽 테두리, 선택 행 = 연보라. 근거는 사장님 말로. 행을 누르면 아래에 상세. */
export function SettingsDetail({ r }: { r: Result }) {
  const m = r.matrix;
  const full = m.settings ?? [];
  const items = settingItems(r);
  const [tab, setTab] = useState<"전체" | Kind>("전체");
  const [sel, setSel] = useState<string | null>(m.keep[0]?.field_id ?? null);
  const n = (k: Kind) => items.filter((x) => x.kind === k).length;
  const shown = tab === "전체" ? items : items.filter((x) => x.kind === tab);
  const meta = r.alerts.find((a) => a.kind === "meta_vs_measured");
  const picked = items.find((x) => x.field_id === sel);
  const tabs: ("전체" | Kind)[] = ["전체", "테스트", "다시 보기", "그대로"];
  return (
    <>
      <Card title="광고 관리자 순서로 본 내 세팅" summary="광고 관리자 칸 이름 그대로, 위에서부터 캠페인 → 광고 세트 → 광고 순서예요">
        <Tabs label="상태로 거르기" value={tab} onChange={setTab}
          items={tabs.map((t) => ({ id: t, label: <>{t} <span className="tabular-nums">{t === "전체" ? items.length : n(t)}</span></> }))} />
        <div className="overflow-x-auto">
          <table className="w-full text-body max-sm:block">
            <thead className="max-sm:sr-only"><tr className="text-left text-caption text-soft">
              <th className="py-2 pl-3 pr-3">단계</th><th className="pr-3">칸</th><th className="pr-3">지금 값</th><th className="pr-3">상태</th><th>근거</th>
            </tr></thead>
            <tbody className="max-sm:flex max-sm:flex-col">
              {shown.map((x) => {
                const [stage, name] = x.path.split(" › ");
                return (
                  <tr key={x.field_id + x.kind} onClick={() => setSel(x.field_id)} aria-selected={sel === x.field_id}
                    className={`cursor-pointer border-t border-line align-top max-sm:flex max-sm:flex-wrap max-sm:items-center max-sm:gap-x-2 max-sm:gap-y-1 max-sm:py-3 max-sm:pr-3 ${x.kind === "테스트" ? "border-l-4 border-l-accent" : "border-l-4 border-l-transparent"} ${sel === x.field_id ? "bg-accent-soft" : ""}`}>
                    <td className="py-2 pl-3 pr-3 text-caption text-soft whitespace-nowrap max-sm:p-0 max-sm:pl-3">{stage}</td>
                    <th scope="row" className="py-2 pr-3 text-left font-semibold max-sm:p-0">
                      <button type="button" onClick={() => setSel(x.field_id)} className="text-left">{name}</button>
                    </th>
                    <td className="py-2 pr-3 max-sm:order-last max-sm:w-full max-sm:p-0 max-sm:pl-3"><span className="text-soft sm:hidden">지금 값: </span>{x.value ?? (full.length ? "—" : <span className="text-caption text-soft">확장에서 넘기면 보여요</span>)}</td>
                    <td className="py-2 pr-3 max-sm:p-0"><span className={`rounded-badge px-2.5 py-0.5 text-caption font-bold whitespace-nowrap ${LOOK[x.kind]}`}>{x.kind}</span></td>
                    <td className="py-2 text-caption text-soft max-sm:order-last max-sm:w-full max-sm:p-0 max-sm:pl-3">{x.text}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {!full.length && <p className="text-caption text-soft">확장 프로그램에서 넘어온 내 광고 설정이 있으면 모든 칸을 보여 줘요. 지금은 결과 파일로 알 수 있는 칸만 보여요.</p>}
      </Card>
      {picked && (
        <section aria-label="선택한 칸" className="flex flex-col gap-1 rounded-button bg-accent-soft px-4 py-3 text-body">
          <p><b>선택한 칸: {picked.path.split(" › ").pop()}</b> · 상태 {picked.kind}</p>
          {picked.field_id === "meta.adset.placements" && meta && <p>메타 추천: 자동 (Advantage+)</p>}
          <p>우리가 돌려 본 결과: {picked.field_id === "meta.adset.placements" && meta ? (meta.text.split("결과에선 ")[1] ?? meta.text) : picked.text === "—" ? "이번 결과로는 바꿀 이유가 없었어요" : picked.text}</p>
          <p>권장: {picked.kind === "테스트" ? `${m.change?.new_short ?? m.change?.new ?? "바꿔서"} 테스트` : picked.kind === "다시 보기" ? "다음 결과에서 다시 보기" : "그대로"}</p>
        </section>
      )}
    </>
  );
}
