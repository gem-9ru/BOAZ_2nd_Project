import { useState } from "react";
import type { Kind, Result } from "../api";
import { Card } from "../ui";
import { Lead } from "./shared";

const ORDER = ["캠페인", "광고 세트", "광고"];
const LOOK: Record<Kind, string> = { 테스트: "bg-accent text-on-accent", "다시 보기": "bg-warn-bg text-warn", 그대로: "bg-sunk text-soft" };
type Item = { field_id: string; path: string; kind: Kind; text: string; value?: string };

/** AN-03 내 세팅 카드 (v4.2): 광고 관리자 순서(캠페인 → 광고 세트 → 광고) 표 + 상태 탭(전체/테스트/다시 보기/그대로).
 *  테스트 행 = 바이올렛 왼쪽 테두리, 선택 행 = 연보라. 근거는 사장님 말로, 증감은 ↑↓. 행을 누르면 아래에 상세. */
export function AN03({ r, focus }: { r: Result; focus?: string | null }) {
  const m = r.matrix;
  const full = m.settings ?? [];
  const items: Item[] = full.map((x) => ({ field_id: x.field_id, path: x.path, kind: x.kind, text: x.note, value: x.value }));
  if (!full.length) {
    if (m.change?.path) items.push({ field_id: m.change.field_id, path: m.change.path, kind: "테스트", text: m.change.reason ?? "", value: m.change.now ?? undefined });
    m.keep.forEach((k) => items.push({ field_id: k.field_id, path: k.path, kind: "그대로", text: k.reason, value: k.value }));
    m.watch.forEach((w) => { if (!items.some((x) => x.path === w.path)) items.push({ field_id: w.field_id, path: w.path, kind: "다시 보기", text: w.text }); });
  }
  items.sort((a, b) => ORDER.indexOf(a.path.split(" › ")[0]!) - ORDER.indexOf(b.path.split(" › ")[0]!));
  const [tab, setTab] = useState<"전체" | Kind>("전체");
  const [sel, setSel] = useState<string | null>(focus ?? m.keep[0]?.field_id ?? null);
  const n = (k: Kind) => items.filter((x) => x.kind === k).length;
  const shown = tab === "전체" ? items : items.filter((x) => x.kind === tab);
  const meta = r.alerts.find((a) => a.kind === "meta_vs_measured");
  const picked = items.find((x) => x.field_id === sel);
  const tabs: ("전체" | Kind)[] = ["전체", "테스트", "다시 보기", "그대로"];
  return (
    <>
      <Lead>테스트할 칸 {n("테스트")}개, 다시 볼 칸 {n("다시 보기")}개, 나머지 {n("그대로")}개는 그대로 두세요</Lead>
      <Card title="광고 관리자 순서로 본 내 세팅" summary="광고 관리자 칸 이름 그대로, 위에서부터 캠페인 → 광고 세트 → 광고 순서예요">
        <div role="tablist" aria-label="상태로 거르기" className="flex flex-wrap gap-2">
          {tabs.map((t) => (
            <button key={t} role="tab" type="button" aria-selected={tab === t} onClick={() => setTab(t)}
              className={`rounded-badge border px-3 py-1 text-caption ${tab === t ? "border-accent bg-accent text-on-accent font-semibold" : "border-line bg-surface"}`}>
              {t} <span className="tabular-nums">{t === "전체" ? items.length : n(t)}</span>
            </button>
          ))}
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-body">
            <thead><tr className="text-left text-caption text-soft">
              <th className="py-2 pl-3 pr-3">단계</th><th className="pr-3">칸</th><th className="pr-3">지금 값</th><th className="pr-3">상태</th><th>근거</th>
            </tr></thead>
            <tbody>
              {shown.map((x) => {
                const [stage, name] = x.path.split(" › ");
                return (
                  <tr key={x.field_id + x.kind} onClick={() => setSel(x.field_id)} aria-selected={sel === x.field_id}
                    className={`cursor-pointer border-t border-line align-top ${x.kind === "테스트" ? "border-l-4 border-l-accent" : "border-l-4 border-l-transparent"} ${sel === x.field_id ? "bg-accent-soft" : ""}`}>
                    <td className="py-2 pl-3 pr-3 text-caption text-soft whitespace-nowrap">{stage}</td>
                    <th scope="row" className="py-2 pr-3 text-left font-semibold">
                      <button type="button" onClick={() => setSel(x.field_id)} className="text-left">{name}</button>
                    </th>
                    <td className="py-2 pr-3">{x.value ?? "—"}</td>
                    <td className="py-2 pr-3"><span className={`rounded-badge px-2.5 py-0.5 text-caption font-bold whitespace-nowrap ${LOOK[x.kind]}`}>{x.kind}</span></td>
                    <td className="py-2 text-caption text-soft">{x.text}</td>
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
