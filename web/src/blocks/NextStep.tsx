import type { Result } from "../api";
import { Button, Card, HowCalculated, won } from "../ui";

/** 11 다음에 할 일 (5 다음 세팅): 결과 화면은 다음 할 일 하나로 끝낸다. 챗봇에는 4자리 코드로 넘긴다. */
export function NextStep({ r, onCopied }: { r: Result; onCopied: (msg: string) => void }) {
  const n = r.next;
  const mb = r.verdict?.min_budget;
  function copy() {
    navigator.clipboard.writeText(r.code).then(() => onCopied("코드를 복사했어요"), () => onCopied("복사하지 못했어요. 코드를 직접 적어 주세요"));
  }
  function download() {
    const blob = new Blob([JSON.stringify({ code: r.code, ...n }, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `광고코치_다음세팅_${r.code}.json` });
    a.click();
    URL.revokeObjectURL(a.href);
  }
  return (
    <Card id="next" step={11} title="다음에 할 일">
      <ul className="flex flex-col gap-1 text-body border-l-4 border-accent pl-4">
        {n.summary.map((l) => <li key={l}>{l}</li>)}
      </ul>
      <p className="text-caption font-semibold text-accent-ink">{n.action}</p>
      <div className="rounded-button border-2 border-ink px-5 py-4">
        <p className="text-lead"><b>{n.change.label}</b> → {n.change.new}</p>
        <p className="text-body text-soft">{n.change.note}</p>
      </div>
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <p className="text-caption text-soft">Ad assistant 확장 → ③ 분석에 이 코드를 넣으면 캐릭터가 이 칸을 짚어 드려요</p>
          <p className="text-hero font-bold tracking-[0.3em] tabular-nums">{r.code}</p>
        </div>
        <Button onClick={copy}>코드 복사</Button>
        <Button kind="secondary" onClick={download}>요약 파일 받기</Button>
      </div>
      {mb?.per_group && (
        <HowCalculated easy="'확실히 고르려면 얼마를 더 써야 하나'를 시뮬레이션으로 계산했어요.">
          <p>최소 검증 예산 세트당 {won(mb.per_group)} (두 세트 {won(mb.total)}): 1,000원당 도착이 {Math.round(mb.lift * 100)}% 좋을 때, {Math.round(mb.confidence * 100)}% 확신으로 승자를 고를 확률이 {Math.round((mb.power ?? 0) * 100)}%가 되는 예산이에요 (희수 8장 ④).</p>
          <p>한 사이클에 바꾸는 칸은 하나예요. 근거: Feit & Berman (2019) — 작은 테스트로 고르고 이긴 쪽에 몰아주기</p>
        </HowCalculated>
      )}
    </Card>
  );
}
