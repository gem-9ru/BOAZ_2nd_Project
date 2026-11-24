import { useState } from "react";
import { Button, Card, Grade } from "../ui";

const PREP = [
  "광고 세트 2개, 하나만 다르게 (예: 노출 위치만)",
  "세트마다 하루 약 ₩1,350 × 4일 (세트당 약 ₩5,400)",
  "총예산·연령·지역은 두 세트가 같게",
  "끝나면 '분석 데이터'에서 '일'과 '노출 위치'를 골라 CSV로 내보내기",
];

/** 화면 0: 무엇을 해 주는지 한 줄 + 할 수 있는 일 셋 (올리기 · 예시 · 아직 안 돌림). */
export function Start({ onFile, onExample, busy, error }: {
  onFile: (f: File) => void; onExample: () => void; busy: boolean; error: string | null;
}) {
  const [prep, setPrep] = useState(false);
  const [over, setOver] = useState(false);
  const [done, setDone] = useState<boolean[]>(PREP.map(() => false));
  return (
    <div className="flex flex-col gap-group">
      <header className="flex flex-col gap-3">
        <p className="text-caption font-semibold text-accent-ink">Ad assistant · 결과 분석</p>
        <h1 className="text-hero-sm sm:text-hero font-bold leading-tight">5,000원으로 먼저 돌려 보세요</h1>
        <p className="text-lead text-soft max-w-[60ch]">그 결과 파일을 올리면 20만 번 계산해 다음에 바꿀 칸 하나와 예상 범위를 알려 드려요.</p>
      </header>

      <Card title="메타 결과 파일 올리기">
        <label htmlFor="csv"
          onDragOver={(e) => { e.preventDefault(); setOver(true); }}
          onDragLeave={() => setOver(false)}
          onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files?.[0]; if (f && !busy) onFile(f); }}
          className={`flex flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed px-6 py-8 text-center cursor-pointer focus-within:outline-2 focus-within:outline-focus focus-within:outline-offset-2 ${over ? "border-ink bg-sunk" : "border-line bg-bg"}`}>
          <span className="text-body text-soft">메타 결과 CSV를 여기에 끌어다 놓거나</span>
          <span className="inline-flex items-center h-button px-5 rounded-button bg-button text-button-fg text-body font-semibold">파일 고르기</span>
          <input id="csv" type="file" accept=".csv,text/csv" disabled={busy} aria-label="메타 결과 CSV"
            aria-describedby={error ? "csv-help csv-error" : "csv-help"} aria-invalid={error ? true : undefined} className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
        </label>
        <ol id="csv-help" className="text-caption text-soft list-decimal pl-5 flex flex-col gap-0.5">
          <li>광고 관리자 → <b>광고 세트</b> 탭에서 비교할 세트 체크</li>
          <li>날짜를 광고를 돌린 기간으로</li>
          <li><b>분석 데이터</b>에서 <b>일</b>과 <b>노출 위치</b>를 고른 뒤 내보내기(.csv)</li>
        </ol>
        <div className="text-caption text-soft">
          <p className="font-semibold text-ink">꼭 있어야 하는 열</p>
          <ul className="flex flex-wrap gap-x-3">
            {["지출 금액", "노출", "링크 클릭", "랜딩 페이지 조회"].map((c) => <li key={c}>✓ {c}</li>)}
          </ul>
          <p>'조회'는 랜딩 페이지 조회가 아니에요. '랜딩 페이지 조회'를 골라 주세요. (없으면 '들어온 사람'을 계산하지 못해요)</p>
        </div>
        {busy && <p role="status" className="text-body text-soft">파일을 읽고 20만 번 계산하는 중이에요…</p>}
        {error && <p id="csv-error" role="alert" className="text-body text-warn">{error}</p>}
      </Card>

      <div className="grid gap-stack sm:grid-cols-2">
        <Card title="파일이 아직 없다면">
          <p className="text-body text-soft">팀이 직접 돌린 오븐로그 A/B 실측(11/17~20)으로 결과 화면을 먼저 볼 수 있어요. <Grade g="A" /></p>
          <Button kind="secondary" onClick={onExample} busy={busy}>예시로 보기 (오븐로그 실측)</Button>
        </Card>
        <Card title="아직 광고를 안 돌려 봤다면">
          <p className="text-body text-soft">비교할 수 있게 작게 한 번 돌리는 법을 알려 드려요.</p>
          <Button kind="secondary" onClick={() => setPrep((v) => !v)}>아직 안 돌려 봤어요</Button>
          {prep && (
            <fieldset className="flex flex-col gap-2">
              <legend className="text-body font-semibold mb-2">광고 전 준비 <span className="text-soft tabular-nums">{done.filter(Boolean).length}/{PREP.length}</span></legend>
              {PREP.map((t, i) => (
                <label key={t} className="flex gap-2 text-body items-start">
                  <input type="checkbox" checked={done[i]} onChange={() => setDone((d) => d.map((x, j) => (j === i ? !x : x)))} className="mt-1 accent-action" />
                  {t}
                </label>
              ))}
              <p className="text-caption text-soft">작은 테스트로 고른 뒤 이긴 쪽에 몰아주는 방식 (Feit & Berman, 2019)</p>
            </fieldset>
          )}
        </Card>
      </div>
    </div>
  );
}
