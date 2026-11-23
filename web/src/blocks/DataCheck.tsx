import type { Result } from "../api";
import { Card, HowCalculated } from "../ui";

const METRIC = { spend: "지출", impressions: "노출", link_clicks: "링크 클릭" } as Record<string, string>;

/** 1 데이터 점검: 파일이 제대로 인식됐나 + 해석 안전장치 (✅ 정상 / ⚠️ 확인 필요). */
export function DataCheck({ c }: { c: Result["check"] }) {
  const r = c.read;
  const items = [
    ...c.totals.map((t) => ({ ok: t.match, text: `${METRIC[t.metric] ?? t.metric} 합계가 일자별·노출 위치별로 ${t.match ? "같아요" : "달라요"}` })),
    ...c.safety,
  ];
  return (
    <Card id="check" step={1} title="데이터 점검">
      <p className="text-lead">기간 {r.days}일 · 광고 세트 {r.adsets}개 · 일자별 {r.daily_rows}행 · 노출 위치 {r.placement_rows}행을 읽었어요.</p>
      <ul className="flex flex-col gap-1 text-body">
        {items.map((i) => (
          <li key={i.text} className="flex gap-2"><span aria-hidden="true">{i.ok ? "✅" : "⚠️"}</span><span className="sr-only">{i.ok ? "정상" : "확인 필요"}</span>{i.text}</li>
        ))}
      </ul>
      {c.missing.map((m) => <p key={m} role="alert" className="text-body text-warn">{m}</p>)}
      <HowCalculated easy="결과를 보기 전에 파일이 멀쩡한지부터 확인해요. 합계가 안 맞거나 광고가 안 나간 날이 있으면 결과가 틀릴 수 있어요.">
        <p>일자별 표의 합과 노출 위치 표의 합을 지출·노출·링크 클릭마다 대조해요 (도달은 겹쳐 세어져서 더하지 않아요). 한글 깨짐(UTF-8·CP949)은 알아서 처리해요.</p>
        <p>근거: Kohavi 외 (2020) — 실험 결과를 보기 전에 데이터 품질부터 검사 · Gordon 외 (2019) — 사람을 나눠 보여 주는 실험이 관측 비교보다 정확</p>
      </HowCalculated>
    </Card>
  );
}
