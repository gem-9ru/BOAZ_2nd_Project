import type { Result } from "../api";
import { Button, Card } from "../ui";
import { CertaintyBadge } from "./Certainty";

/** AN-06 보내기 + 근거: 변경안 · 다음 테스트 체크리스트(남은 ▲) · 확장 프로그램으로 보내기 · 근거 탭. */
export function AN06({ r, onCopied }: { r: Result; onCopied: (msg: string) => void }) {
  const c = r.matrix.change ?? r.next.change;
  const checklist = c.checklist ?? r.alerts.filter((a) => a.level === "warn").map((a) => a.todo);
  function send() {
    navigator.clipboard.writeText(r.code).then(() => onCopied("코드를 복사했어요. 확장 프로그램 ③에 붙여 넣으세요"), () => onCopied("복사하지 못했어요. 코드를 직접 적어 주세요"));
  }
  function download() {
    const blob = new Blob([JSON.stringify({ code: r.code, change: c, keep: r.matrix.keep, dont: r.matrix.dont, checklist }, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `광고어시스턴트_변경안_${r.code}.json` });
    a.click();
    URL.revokeObjectURL(a.href);
  }
  return (
    <>
      <Card title="변경안">
        <div className="flex flex-col gap-2 rounded-button border-2 border-accent px-5 py-4">
          <p className="text-caption font-semibold text-accent-ink">{c.path ?? c.label}</p>
          <p className="text-lead font-bold">{c.now ? `${c.now} → ` : ""}{c.new}</p>
          {c.certainty && <div><CertaintyBadge level={c.certainty.level} /></div>}
        </div>
        <h3 className="text-body font-bold">다음 테스트 전에 확인할 것</h3>
        <ul className="flex flex-col gap-2">
          {checklist.map((t) => (
            <li key={t}><label className="flex items-start gap-2 text-body"><input type="checkbox" className="mt-1 accent-action" />{t}</label></li>
          ))}
        </ul>
      </Card>
      <Card title="확장 프로그램으로 보내기">
        <p className="text-body">확장 프로그램 ③ 분석에 이 코드를 넣으면, 광고 관리자에서 이 칸만 짚어 드려요. 게시는 사장님이 직접 해요.</p>
        <p className="text-hero font-bold tracking-[0.3em] tabular-nums">{r.code}</p>
        <div className="flex flex-wrap gap-3">
          <Button onClick={send}>확장 프로그램으로 보내기</Button>
          <Button kind="secondary" onClick={download}>변경안 파일 받기</Button>
        </div>
      </Card>
      <details className="rounded-card border border-card-border bg-card">
        <summary className="cursor-pointer px-card py-4 text-body font-semibold text-details-fg">🔎 근거 보기</summary>
        <div className="flex flex-col gap-3 p-card pt-0 text-body">
          <p><b>메타 신호</b> {c.meta_says ?? "광고 관련성 진단 열이 파일에 있으면 여기에 같이 보여요."}</p>
          <p><b>실측</b> 오븐로그(수동 노출 위치가 CPM 15% 저렴) · 희수 실험(CPM 36% 저렴) — 두 실측이 같은 방향이에요.</p>
          <p><b>판단 규칙</b> 위에서부터 처음 막힌 단계 하나만, 한 번에 칸 1개, 평균만 보고 자르지 않기, 메타 추천과 다르면 실측 우선.</p>
          <p><b>논문</b> Lewis & Rao 2015 · Gordon 외 2019 · Feit & Berman 2019 · Scott 2010 · Efron & Morris 1975 · Kohavi 외 2020</p>
          <p><b>한계</b> 소액·짧은 기간이라 범위가 넓어요. 예산을 크게 늘릴 때 단가가 오르는 효과는 넣지 않았어요.</p>
        </div>
      </details>
    </>
  );
}
