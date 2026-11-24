import { useState } from "react";
import { Card } from "../ui";

export type Settings = Record<string, string>;

const QUESTIONS: { id: string; label: string; options?: string[]; number?: true }[] = [
  { id: "meta.campaign.objective", label: "캠페인 목표", options: ["트래픽", "판매", "인지도"] },
  { id: "meta.adset.daily_budget", label: "세트당 하루 예산", number: true },
  { id: "meta.adset.age_gender", label: "연령", options: ["20대", "30대", "40대", "50대", "전체"] },
  { id: "meta.adset.placements", label: "노출 위치", options: ["자동 (어드밴티지+)", "수동"] },
  { id: "meta.ad.format", label: "소재 형식", options: ["이미지 1장", "동영상", "여러 장 (슬라이드)"] },
];

/** 입력 ② 내 세팅값 (v4 8장): 확장 프로그램에서 오면 받은 개수만, 아니면 5문항(선택). */
export function MySettings({ received, value, onChange }: { received: number | null; value: Settings; onChange: (s: Settings) => void }) {
  const [open, setOpen] = useState(false);
  if (received !== null) {
    return (
      <p role="status" className="rounded-button bg-ok-bg px-4 py-3 text-body">
        <span aria-hidden="true" className="mr-2 font-bold">✓</span>확장 프로그램에서 이번 세팅값 {received}개를 받았어요. 결과를 내 세팅 기준으로 보여 드려요.
      </p>
    );
  }
  const set = (id: string, v: string) => onChange({ ...value, [id]: v });
  return (
    <Card title="내 세팅 (선택)">
      <p className="text-body text-soft">세팅값을 알려 주면 '내 세팅 카드'에서 칸마다 바꿀지·둘지를 알려 드려요. 몰라도 분석은 돼요.</p>
      {!open ? (
        <div><button type="button" onClick={() => setOpen(true)} className="rounded-button border border-accent px-4 py-2 text-body font-semibold text-accent-ink">내 세팅 알려 주기 (5문항)</button></div>
      ) : (
        <div className="flex flex-col gap-stack">
          {QUESTIONS.map((q) => (
            <fieldset key={q.id} className="flex flex-col gap-2">
              <legend className="mb-1 text-body font-semibold">{q.label}</legend>
              {q.number ? (
                <label className="flex items-center gap-2 text-body">
                  <span className="sr-only">세트당 하루 예산 (원)</span>
                  <input type="number" min={0} step={100} inputMode="numeric" value={value[q.id] ?? ""} onChange={(e) => set(q.id, e.target.value)}
                    aria-label="세트당 하루 예산 (원)" className="w-36 rounded-button border border-line bg-surface px-3 py-2 tabular-nums" />원
                </label>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {q.options!.map((o) => (
                    <label key={o} className={`cursor-pointer rounded-badge border px-3 py-1.5 text-body has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent ${value[q.id] === o ? "border-accent bg-accent text-on-accent font-semibold" : "border-line bg-surface"}`}>
                      <input type="radio" name={q.id} value={o} checked={value[q.id] === o} onChange={() => set(q.id, o)} className="sr-only" />{o}
                    </label>
                  ))}
                </div>
              )}
            </fieldset>
          ))}
        </div>
      )}
    </Card>
  );
}
