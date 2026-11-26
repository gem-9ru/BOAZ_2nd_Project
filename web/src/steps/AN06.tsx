import { useState } from "react";
import type { Result } from "../api";
import { Button, Card, josa, Tabs, TestTag, won } from "../ui";
import { DEV_LABEL } from "./Certainty";
import { VIRTUAL_CASES } from "./cases";
import { Lead } from "./shared";

const EVIDENCE = ["메타 공식 신호", "우리 실측 2건", "논문", "가상 케이스", "한계"] as const;
/** 근거 탭은 개발 표기 (v4.2: 확실 / 유력 / 보류) */
const DEV_WORD = { "확실해요": "확실", "A 쪽이에요": "유력", "B 쪽이에요": "유력", "아직 몰라요": "보류" } as const;
const ALERT_WORD: Record<string, string> = { no_delivery: "안 나간 날", underspent: "예산 덜 씀", spend_gap: "돈 쏠림", small_sample: "클릭 적음",
  low_visit_rate: "페이지 도착 적음", high_frequency: "반복 노출", an_skew: "Audience Network 쏠림", missing_column: "열 빠짐", sum_mismatch: "합계 안 맞음" };

/** AN-06 보내기 + 근거 (v4.2): '이 테스트를 준비' · 지금 세트(그대로) → 새 세트(바꿀 값) · 체크리스트 4개(ALT 번호 숨김)
 *  · 확장 프로그램으로 보내기 · 근거 탭(근거 탭만 확실 / 유력 / 보류 표기). */
export function AN06({ r, onCopied, onSend }: { r: Result; onCopied: (msg: string) => void; onSend?: () => void }) {
  const c = r.matrix.change ?? r.next.change;
  const checklist = c.checklist ?? r.alerts.filter((a) => a.level === "warn").map((a) => a.todo);
  const [tab, setTab] = useState<(typeof EVIDENCE)[number]>("메타 공식 신호");
  const what = c.what ?? c.label;
  const days = c.days ?? r.check.read.days;   // 서버가 하루 최소를 넘게 맞춘 기간
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
      <Lead>{c.tested === false
        ? (what.endsWith("소재") ? `${josa(what, "을를")} 넣은 세트 하나만 더 만들면 돼요` : `${c.label} 칸만 바꾼 세트 하나만 더 만들면 돼요`)
        : `${c.label} 칸 하나만 바꾸면 돼요`}</Lead>
      <Card title="테스트안" summary={c.path ?? c.label}>
        <div className="flex flex-col gap-2 rounded-button border-2 border-accent px-5 py-4">
          <p className="flex flex-wrap items-center gap-2 text-lead font-bold">
            <span>지금 세트: {c.now ? <>{c.now} <span className="font-normal text-soft">(그대로)</span></> : "그대로"}</span>
            <span aria-hidden="true">·</span>
            <span>새 세트: {c.new_short ?? c.new}</span>
            {c.tag && <TestTag text={c.tag} />}
          </p>
          <p className="text-body">이유: {c.reason ?? c.note}</p>
          {c.tested === false && <p className="text-body">{what} 효과: 아직 몰라요 → 이번 테스트로 확인</p>}
          <p className="text-body text-soft">세트당 총 {won(c.per_set ?? 5000)}, {days}일 · 두 세트 같은 날 같이 시작</p>
        </div>
      </Card>
      <Card title="다음 테스트 체크리스트" summary={`${checklist.length}개만 지키면 다음 결과로 효과를 잴 수 있어요`}>
        <ul className="flex flex-col gap-2">
          {checklist.map((t) => (
            <li key={t}><label className="flex min-h-11 cursor-pointer items-center gap-3 text-body"><input type="checkbox" className="size-5 shrink-0 accent-action" />{t}</label></li>
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
        <Tabs label="근거" value={tab} onChange={setTab} items={EVIDENCE.map((t) => ({ id: t, label: t }))} />
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
          {tab === "가상 케이스" && <>
            <p>메타 설정을 하나만 다르게 한 A/B 두 세트를 오븐로그 실측 비율로 만들어, 이 분석을 그대로 돌려 본 결과예요.
              판정 규칙이 맞게 움직이는지 보려는 것이라 <b>판정에는 쓰지 않아요</b>. (네이버 광고는 돌리지 않아서 메타만)</p>
            <div className="overflow-x-auto">
              <table className="w-full text-body">
                <caption className="sr-only">가상 케이스 6개 결과</caption>
                <thead><tr className="text-left text-caption text-soft">
                  <th className="py-2 pr-3">다르게 한 메타 설정</th><th className="pr-3">숫자 근거</th><th className="pr-3">분석이 낸 결론</th>
                  <th className="pr-3">판정 (근거 탭 표기)</th><th>뜬 알림</th>
                </tr></thead>
                <tbody>
                  {VIRTUAL_CASES.map((v) => (
                    <tr key={v.id} className="border-t border-line align-top">
                      <th scope="row" className="py-2 pr-3 text-left font-semibold">{v.id} {v.setting}</th>
                      <td className="py-2 pr-3 text-soft">{v.basis}</td>
                      <td className="py-2 pr-3">{v.conclusion}</td>
                      <td className="py-2 pr-3">{v.word ? `${DEV_WORD[v.word]} (${v.better}가 나을 확률 ${Math.round((v.prob ?? 0) * 100)}%)` : "–"}</td>
                      <td className="py-2">{v.alerts.length ? v.alerts.map((k) => ALERT_WORD[k] ?? k).join(" · ") : "없음"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>· 실측: 오븐로그 A(자동)·B(직접 고르기)의 광고비·누르는 비율·도착 비율 · 가정: 실측에 없는 값(V5·V6) · 시드 고정이라 다시 돌려도 같은 숫자</p>
          </>}
          {tab === "한계" && <p>소액·짧은 기간이라 범위가 넓어요. 예산을 크게 늘릴 때 단가가 오르는 효과는 넣지 않았어요. 광고 전후 비교로는 효과를 말하지 않고, 같은 기간에 동시에 돌린 A/B 비교로만 말해요.</p>}
        </div>
      </Card>
    </>
  );
}
