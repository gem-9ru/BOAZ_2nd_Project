import { useState } from "react";
import type { Result } from "../api";
import { Button, Card, TestTag, won } from "../ui";
import { DEV_LABEL } from "./Certainty";
import { Lead } from "./shared";

const EVIDENCE = ["메타 공식 신호", "우리 실측 2건", "논문", "가상 케이스", "한계"] as const;

/** AN-06 보내기 + 근거 (v4.2): '이 테스트를 준비' · 지금 세트(그대로) → 새 세트(바꿀 값) · 체크리스트 4개(ALT 번호 숨김)
 *  · 확장 프로그램으로 보내기 · 근거 탭(근거 탭만 확실 / 유력 / 보류 표기). */
export function AN06({ r, onCopied, onSend }: { r: Result; onCopied: (msg: string) => void; onSend?: () => void }) {
  const c = r.matrix.change ?? r.next.change;
  const checklist = c.checklist ?? r.alerts.filter((a) => a.level === "warn").map((a) => a.todo);
  const [tab, setTab] = useState<(typeof EVIDENCE)[number]>("메타 공식 신호");
  const what = c.unknown?.split("가 손님을")[0] ?? c.label;
  const days = r.check.read.days;
  // 옆 광고 어시스턴트(확장 프로그램 패널)로 바로 보낸다. 패널이 안 열려 있을 때를 위해 코드도 복사해 둔다.
  function send() {
    onSend?.();
    const done = `오른쪽 광고 어시스턴트로 보냈어요. 패널이 안 열려 있으면 확장 프로그램 ③ 분석에 코드 ${r.code}를 넣어 주세요`;
    navigator.clipboard.writeText(r.code).then(() => onCopied(`${done} (코드 복사됨)`), () => onCopied(done));
  }
  function download() {
    const blob = new Blob([JSON.stringify({ code: r.code, change: c, keep: r.matrix.keep, dont: r.matrix.dont, checklist }, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), { href: URL.createObjectURL(blob), download: `광고어시스턴트_계획_${r.code}.json` });
    a.click();
    URL.revokeObjectURL(a.href);
  }
  const ok = r.matrix.keep[0];
  return (
    <>
      <Lead>{c.tested === false ? `${what}를 넣은 세트 하나만 더 만들면 돼요` : `${c.label} 칸 하나만 바꾸면 돼요`}</Lead>
      <Card title="테스트안" summary={c.path ?? c.label}>
        <div className="flex flex-col gap-2 rounded-button border-2 border-accent px-5 py-4">
          <p className="flex flex-wrap items-center gap-2 text-lead font-bold">
            <span>지금 세트: {c.now ? <>{c.now} <span className="font-normal text-soft">(그대로)</span></> : "지금 소재 그대로"}</span>
            <span aria-hidden="true">·</span>
            <span>새 세트: {c.new_short ?? c.new}</span>
            {c.tag && <TestTag text={c.tag} />}
          </p>
          <p className="text-body">이유: {c.reason ?? c.note}</p>
          {c.tested === false && <p className="text-body">{what} 효과: 아직 몰라요 → 이번 테스트로 확인</p>}
          <p className="text-body text-soft">세트당 총 {won(c.per_set ?? 5000)}, {days}일 (Test & Roll 권장 범위 안)</p>
        </div>
      </Card>
      <Card title="다음 테스트 체크리스트" summary={`${checklist.length}개만 지키면 다음 결과로 효과를 잴 수 있어요`}>
        <ul className="flex flex-col gap-2">
          {checklist.map((t) => (
            <li key={t}><label className="flex items-start gap-2 text-body"><input type="checkbox" className="mt-1 accent-action" />{t}</label></li>
          ))}
        </ul>
      </Card>
      <Card title="확장 프로그램으로 보내기" summary="누르면 오른쪽 광고 어시스턴트가 테스트안을 받아, 광고 관리자에서 이 칸만 짚어 드려요. 게시는 사장님이 직접 해요">
        <p className="text-body text-soft">패널이 안 열려 있으면 확장 프로그램 ③ 분석에 이 코드를 넣어도 돼요: <b className="text-title tracking-[0.3em] tabular-nums text-ink">{r.code}</b></p>
        <div className="flex flex-wrap gap-3 print:hidden">
          <Button onClick={send}>확장 프로그램으로 보내기</Button>
          <Button kind="secondary" onClick={download}>계획 파일 내려받기</Button>
          <Button kind="secondary" onClick={() => window.print()}>결과 PDF</Button>
        </div>
      </Card>
      <Card title="근거" summary="이 결론이 어디서 나왔는지예요. 근거 탭은 확실 / 유력 / 보류로 적어요">
        <div role="tablist" aria-label="근거" className="flex flex-wrap gap-2">
          {EVIDENCE.map((t) => (
            <button key={t} role="tab" type="button" aria-selected={tab === t} onClick={() => setTab(t)}
              className={`rounded-badge border px-3 py-1 text-caption ${tab === t ? "border-accent bg-accent text-on-accent font-semibold" : "border-line bg-surface"}`}>{t}</button>
          ))}
        </div>
        <div className="flex flex-col gap-2 text-body" role="tabpanel">
          {tab === "메타 공식 신호" && <>
            <p>· 퍼널 진단: 링크 클릭 vs 랜딩 페이지 조회 (Meta 비즈니스 도움말)</p>
            <p>· Breakdown effect: 노출 위치는 평균이 아니라 다음 1건 비용 기준으로 배분</p>
            <p>· 학습 단계: 7일 안에 최적화 이벤트 약 50건</p>
            {c.meta_says && <p>· {c.meta_says}</p>}
          </>}
          {tab === "우리 실측 2건" && <>
            <p>· 오븐로그: 수동 노출 위치가 광고비(CPM) {ok ? ok.reason.replace("↓ 광고비 ", "").replace(" 싸요 · 확실해요", "") : "15%"} 저렴 · 판정 {DEV_LABEL["채택"]}</p>
            <p>· 희수 실험: 수동 세트 광고비(CPM) 36% 저렴 — 두 실측이 같은 방향이에요.</p>
            {r.verdict && <p>· 손님 1명당 비용 판정: {DEV_LABEL[r.verdict.badge.level]} ({Math.round(r.verdict.badge.prob * 100)}%){r.verdict.badge.capped ? ` · ${r.verdict.badge.capped.join(", ")}` : ""}</p>}
            {c.rule && <p>· 이번 결론 규칙(진단 {c.rule.row}번): {DEV_LABEL[c.rule.level]} · 효과는 {DEV_LABEL[c.certainty?.level ?? "보류"]} (돌려 본 적 없음)</p>}
          </>}
          {tab === "논문" && <p>Lewis & Rao 2015 · Gordon 외 2019 · Johnson 외 2017 · Feit & Berman 2019 · Scott 2010 · Efron & Morris 1975 · Kohavi 외 2020</p>}
          {tab === "가상 케이스" && <p>판정 규칙을 확인하려고 만든 가상 케이스 6개가 있어요. 판정에는 쓰지 않아요.</p>}
          {tab === "한계" && <p>소액·짧은 기간이라 범위가 넓어요. 예산을 크게 늘릴 때 단가가 오르는 효과는 넣지 않았어요. 광고 전후 비교로는 효과를 말하지 않고, 같은 기간에 동시에 돌린 A/B 비교로만 말해요.</p>}
        </div>
      </Card>
    </>
  );
}
