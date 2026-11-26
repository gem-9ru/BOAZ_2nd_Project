import type { ReactNode } from "react";
import type { Result } from "../api";
import { Funnel } from "../blocks/Funnel";
import { KeyNumbers } from "../blocks/KeyNumbers";
import { Card, HowCalculated, people, VerdictBadge, won } from "../ui";
import { armName, Lead, Signal, type SignalKind } from "./shared";

const paren = (s: string) => (s.includes(" ") ? `${s.replace(" ", "(")})` : s);   // 'B 수동' → 'B(수동)'

type Line = { n: string; stage: string; meaning: ReactNode; suspect: string; kind: SignalKind };

/** AN-02 어디서 막혔나 (v4.2): 퍼널 신호등 4단계. 숫자 칸 대신 사람 수로 푼 '뜻' 한 칸,
 *  A/B 판정은 3단어 배지. CPM·CTR 원래 숫자는 🔎 안에만. 위에서부터 처음 막힌 곳이 고칠 곳. */
export function AN02({ r }: { r: Result }) {
  const arms = r.summary.arms.slice(0, 2);
  const row = (id: string) => r.matrix.rows.find((x) => x.row === id);
  const cpm = r.verdict?.metrics.find((m) => m.key === "cpm");
  const two = arms.length === 2;
  const both = (f: (a: (typeof arms)[number]) => string) => arms.map((a, i) => `${"AB"[i]} ${f(a)}`).join(" · ");
  const ok = (id: string) => row(id)?.status !== "blocked";

  let first: Line;
  if (two && cpm) {
    const bi = cpm.better === "B" ? 1 : 0;
    const cheap = arms[bi]!, dear = arms[1 - bi]!;
    const pct = cheap.cpm && dear.cpm ? Math.round((1 - cheap.cpm / dear.cpm) * 100) : 0;
    const unknown = cpm.word === "아직 몰라요";
    first = { n: "①", stage: "광고가 보이는 값", suspect: "노출 위치 · 타깃", kind: unknown ? "unknown" : "worse",
      meaning: unknown ? <>두 세트가 비슷해요 <VerdictBadge word="아직 몰라요" small /></>
        : <>{paren(armName(cheap.name, bi))}가 {pct}% 싸요 <VerdictBadge word={cpm.word} small /></> };
  } else {
    const skip = row("1")?.status === "skip";
    first = { n: "①", stage: "광고가 보이는 값", suspect: ok("1") ? "—" : "노출 위치 · 타깃", kind: skip ? "unknown" : ok("1") ? "ok" : "low", meaning: row("1")?.signal ?? "–" };
  }
  const lines: Line[] = [
    first,
    { n: "②", stage: "본 사람이 누르는 정도", suspect: ok("2") ? "—" : "소재 · 문구 · 형식", kind: ok("2") ? "ok" : "low",
      meaning: `1,000명이 보면 ${both((a) => people(a.ctr))} → ${ok("2") ? "괜찮아요" : "기준보다 적어요"}` },
    { n: "③", stage: "누른 뒤 페이지에 들어오는 정도", suspect: ok("3") ? "—" : "웹사이트 URL · 페이지 속도", kind: ok("3") ? "ok" : "low",
      meaning: `누른 100명 중 ${both((a) => `${Math.round((a.click_to_visit ?? 0) * 100)}명`)} → ${ok("3") ? "괜찮아요" : "적어요"}` },
    { n: "④", stage: "들어온 뒤 행동", suspect: "—", kind: row("4")?.status === "ok" ? "ok" : "unknown",
      meaning: row("4")?.status === "ok" ? (row("4")?.signal ?? "")
        : <>{(row("4")?.signal ?? "행동 숫자가 파일에 없어요").replace(/ → 아직 몰라요$/, "")} → <VerdictBadge word="아직 몰라요" small /></> },
  ];
  const blocked = lines.find((l) => l.kind === "low");
  const lead = blocked ? `'${blocked.stage}'에서 처음 막혔어요`
    : first.kind === "worse" ? `광고가 보이는 단계에서만 ${cpm?.better === "B" ? "A" : "B"}가 비쌌고, 그 아래는 괜찮아요`
    : "크게 막힌 곳은 없어요";

  return (
    <>
      <Lead sub="위에서부터 처음 막힌 곳이 고칠 곳이에요 · 광고가 보이고 → 눌리고 → 페이지에 오고 → 행동하기까지">{lead}</Lead>
      <Card title="단계별 신호" summary="광고가 보이고 → 눌리고 → 페이지에 오고 → 행동하기까지, 사람 수로 풀어 봤어요">
        <div className="overflow-x-auto">
          <table className="w-full text-body">
            <thead><tr className="text-left text-caption text-soft">
              <th className="w-8 py-2"><span className="sr-only">신호</span></th><th className="py-2 pr-3">단계</th><th className="pr-3">뜻</th><th>의심할 칸</th>
            </tr></thead>
            <tbody>
              {lines.map((l) => (
                <tr key={l.n} className="border-t border-line align-top">
                  <td className="py-3"><Signal kind={l.kind} /></td>
                  <th scope="row" className="py-3 pr-3 text-left font-semibold">{l.n} {l.stage}</th>
                  <td className="py-3 pr-3"><span className="inline-flex flex-wrap items-center gap-1.5">{l.meaning}</span></td>
                  <td className="py-3 text-soft">{l.suspect}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-caption text-soft">✓ 괜찮음 · ↓ 비교 대상보다 나쁨 · ▲ 기준 미달 · – 아직 몰라요</p>
        {(r.matrix.meta_signals?.length ?? 0) > 0 && (
          <section aria-label="메타 진단" className="flex flex-col gap-1 border-t border-line pt-3 text-body">
            <p className="text-caption font-semibold text-soft">메타 관련성 진단도 같이 봤어요 (참고)</p>
            <ul className="flex flex-col gap-1">
              {r.matrix.meta_signals!.map((m) => <li key={m.key}>{"①②③④"[Number(m.row) - 1] ?? ""} {m.text}</li>)}
            </ul>
          </section>
        )}
      </Card>
      <Card title="의심할 칸" summary="처음 막힌 단계에 연결된 칸이 의심할 칸이에요">
        <ul className="grid gap-1 text-body sm:grid-cols-2">
          <li>① 보이는 값 → 노출 위치 · 타깃 · 입찰</li>
          <li>② 누르는 정도 → 소재 · 문구 · 형식</li>
          <li>③ 페이지 도착 → 웹사이트 URL · 페이지 속도</li>
          <li>④ 행동 → 랜딩 페이지 · 전환 이벤트</li>
        </ul>
      </Card>
      <HowCalculated easy="광고 관리자 숫자를 그대로 쓰고, 사람이 적으면 우연일 수 있어서 가능한 범위를 같이 적었어요.">
        {two && cpm && (
          <p>광고 1,000번 보여주는 데 드는 돈 (CPM): {both((a) => won(a.cpm))} (적게~많게 A {won(cpm.a_interval[0])}~{won(cpm.a_interval[1])} · B {won(cpm.b_interval[0])}~{won(cpm.b_interval[1])}, 95% 범위)</p>
        )}
        <p>본 사람 중 누른 비율 (CTR): {both((a) => `${((a.ctr ?? 0) * 100).toFixed(2)}%`)}</p>
        <p>신호 기준값: 누르는 정도 1,000명 중 10명(1%) 미만 · 페이지 도착 누른 100명 중 60명 미만이면 ▲</p>
        <p>메타 관련성 진단(품질·참여율·전환율 순위): {r.matrix.rankings
          ? "파일에 있어서 '평균 이하'인 것만 참고로 보여 드려요. 신호등과 결론은 우리 숫자로만 정해요."
          : "파일에 없거나 노출이 적어 비어 있어서 건너뛰었어요. 광고 관리자 열에 '품질 순위·참여율 순위·전환율 순위'를 넣어 내보내면 같이 봐요."}</p>
        <KeyNumbers r={r} />
        <Funnel r={r} />
      </HowCalculated>
    </>
  );
}
