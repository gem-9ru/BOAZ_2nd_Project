
export type Settings = Record<string, string>;

const QUESTIONS: { id: string; label: string; options?: string[]; number?: true }[] = [
  { id: "meta.campaign.objective", label: "캠페인 목표", options: ["트래픽", "판매", "인지도"] },
  { id: "meta.adset.daily_budget", label: "세트당 하루 예산", number: true },   // 하루 예산임을 분명히 (v4.2)
  { id: "meta.adset.age_gender", label: "연령", options: ["20대", "30대", "40대", "50대", "전체"] },
  { id: "meta.adset.placements", label: "노출 위치", options: ["자동 (어드밴티지+)", "수동"] },
  { id: "meta.ad.format", label: "소재 형식", options: ["이미지 1장", "동영상", "여러 장 (슬라이드)"] },
];


/** 입력 ② 내 광고 설정 (세팅값) (v4 8장, v4.2 이름): 확장 프로그램에서 오면 받은 칸 수만, 아니면 5문항(선택). */
export function MySettings({ received, value, onChange }: { received: number | null; value: Settings; onChange: (s: Settings) => void }) {
  if (received !== null) {
    return (
      <p role="status" className="rounded-button bg-ok-bg px-4 py-3 text-body">
        <span aria-hidden="true" className="mr-2 font-bold">✓</span>내 광고 설정 (세팅값): 확장 프로그램에서 자동으로 받음 ({received}칸). 결과를 내 설정 기준으로 보여 드려요.
      </p>
    );
  }
  const set = (id: string, v: string) => onChange({ ...value, [id]: v });
  // 업로드 화면 접기 '내 광고 설정이 없어요' 안에 바로 펼친다 (축소안 v5: 따로 카드·버튼 없이)
  return (
        <div className="flex flex-col gap-stack">
          <p className="text-soft">확장 프로그램을 연결하지 않았다면 5개만 넣어 주세요. 넣지 않아도 분석은 돼요. 넣으면 칸마다 바꿀지·둘지를 더 정확히 알려 드려요.</p>
          {QUESTIONS.map((q) => (
            <fieldset key={q.id} className="flex flex-col gap-2">
              <legend className="mb-1 text-body font-semibold">{q.label}</legend>
              {q.number ? (
                <label className="flex items-center gap-2 text-body">
                  <span className="sr-only">세트당 하루 예산 (원)</span>
                  <input type="number" min={0} step={100} inputMode="numeric" value={value[q.id] ?? ""} onChange={(e) => set(q.id, e.target.value)}
                    aria-label="세트당 하루 예산 (원)" className="w-36 rounded-button border border-field-line bg-surface px-3 py-2 tabular-nums" />원
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
  );
}
