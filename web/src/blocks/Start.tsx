import { useState } from "react";
import type { Alert, ExampleName } from "../api";
import { AlertLine } from "../steps/shared";
import { Button, Fold, Folds, Title } from "../ui";
import { Mungchi } from "../ui/Mungchi";
import { MySettings, type Settings } from "./MySettings";

const PREP = [
  "광고 세트 2개, 하나만 다르게 (예: 노출 위치만)",
  "세트마다 하루 약 1,350원 × 4일 (세트당 총 약 5,400원)",
  "총예산·연령·지역은 두 세트가 같게, 같은 날 같이 시작",
  "끝나면 '분석 데이터'에서 '일'과 '노출 위치'를 골라 CSV로 내보내기",
];

/** ⓪ 업로드 (축소안 v5 · 기존 AN-00): 할 일은 하나, 파일 올리기. 내 광고 설정은 확장 프로그램에서 오면 자동이라 상태 한 줄만,
 *  내보내기 방법·필수 열·5문항·'아직 안 돌려 봤어요'는 접기. 문제가 있을 때만 파일 칸 바로 아래에 차단 알림. */
export function Start({ onFile, onExample, onStart, checked, busy, error, received, settings, onSettings }: {
  onFile: (f: File) => void; onExample: (name?: ExampleName) => void; busy: boolean; error: string | null;
  onStart: () => void; checked: { name: string; rows: number; blocks: Alert[] } | null;
  received: number | null; settings: Settings; onSettings: (s: Settings) => void;
}) {
  const [over, setOver] = useState(false);
  const [mine, setMine] = useState(false);   // '5개만 직접 입력하기' 링크 → 접기 3번째 줄을 연다
  const [done, setDone] = useState<boolean[]>(PREP.map(() => false));
  const ready = !!checked && !checked.blocks.length && !busy;
  return (
    <div className="flex flex-col gap-group">
      <div className="flex flex-col gap-1 pt-4">
        <h1 aria-label="돌려 본 광고 결과를 올려 주세요" className="text-hero-sm font-extrabold leading-tight tracking-tight"><Title parts={["돌려 본 광고 결과를 ", "올려 주세요", ""]} /></h1>
        <p className="text-lead font-medium text-soft">파일 하나만 올리면, 다음에 바꿔 볼 칸 1개를 뭉치가 찾아 드려요</p>
      </div>

      <div className="flex flex-col gap-3">
        <label htmlFor="csv"
          onDragOver={(e) => { e.preventDefault(); setOver(true); }}
          onDragLeave={() => setOver(false)}
          onDrop={(e) => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files?.[0]; if (f && !busy) onFile(f); }}
          className={`flex cursor-pointer flex-col items-center justify-center gap-1 rounded-sheet border-2 border-dashed px-6 pt-8 pb-7 text-center focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-focus ${over ? "border-accent bg-accent-soft" : "border-accent-line bg-surface"}`}>
          <Mungchi pose="wave" className="w-28" />
          <span className="mt-1 text-title font-extrabold">광고 결과 파일(CSV)을 여기로 끌어다 놓기</span>
          <span className="text-label text-soft">광고 관리자 › 보고서에서 받은 파일 그대로요</span>
          <span className="mt-4 inline-flex h-13 items-center rounded-button bg-button px-6 text-lead font-bold text-button-fg shadow-press">파일 고르기</span>
          <input id="csv" type="file" accept=".csv,.xlsx,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" disabled={busy} aria-label="광고 결과 파일 (CSV)"
            aria-describedby={error ? "csv-error" : undefined} aria-invalid={error ? true : undefined} className="sr-only"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) onFile(f); e.target.value = ""; }} />
          {received !== null
            ? <span className="mt-4 rounded-badge bg-ok-bg px-3 py-1.5 text-caption text-ink"><span aria-hidden="true" className="font-bold text-ok">✓ </span>내 광고 설정은 확장 프로그램에서 자동으로 받았어요 ({received}칸)</span>
            : <button type="button" onClick={(e) => { e.preventDefault(); setMine(true); }} className="mt-4 text-caption text-accent-ink underline">내 광고 설정 5개만 직접 입력하기 ▸</button>}
        </label>
        {busy && <p role="status" className="text-body text-soft">파일을 읽고 계산하는 중이에요…</p>}
        {error && <p id="csv-error" role="alert" className="rounded-soft border-[1.5px] border-block-line bg-block-bg px-4 py-3 text-body text-block-ink">{error}</p>}
        {/* 올린 파일 검사 결과: 통과면 ✓ 파일 · 줄 수, 차단이면 고칠 방법을 파일 칸 바로 아래에 */}
        {checked && !checked.blocks.length && <p role="status" className="text-body font-semibold text-ok">✓ {checked.name} · {checked.rows}줄 확인</p>}
        {checked && checked.blocks.length > 0 && <ul role="alert" className="flex flex-col gap-2 rounded-soft border-[1.5px] border-block-line bg-block-bg px-4 py-3">{checked.blocks.map((a) => <AlertLine key={a.kind + a.text} a={a} />)}</ul>}
        {/* [분석 시작]은 파일 칸 바로 아래 (통과 표시와 다음에 누를 버튼을 붙여 둔다). 회색일 땐 이유를 글로 */}
        <div className="flex items-center justify-end gap-3">
          {!ready && <span className="text-label text-soft">파일을 올리면 눌러져요</span>}
          <Button onClick={onStart} disabled={!ready}>분석 시작 ▶</Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <span className="text-body text-soft">파일이 없나요?</span>
        <Example icon="🍪" onClick={() => onExample("ovenlog")} disabled={busy}>오븐로그 예시로 보기</Example>
        <Example icon="🧪" onClick={() => onExample("heesu")} disabled={busy}>희수 실험 예시로 보기</Example>
      </div>

      <Folds label="도움말">
        <Fold label="결과 파일은 어떻게 받아요?" preview="광고 관리자 › 보고서 › 일 · 노출 위치">
          <ol className="list-decimal pl-5">
            <li>광고 관리자 → <b>광고 세트</b> 탭에서 비교할 세트 체크</li>
            <li>날짜를 광고를 돌린 기간으로</li>
            <li><b>보고서 › 분석 기준</b>에서 <b>일</b>과 <b>노출 위치</b>를 고른 뒤 내보내기(.csv)</li>
          </ol>
        </Fold>
        <Fold label="꼭 있어야 하는 열" preview="지출 금액 · 노출 · 링크 클릭 · 랜딩 페이지 조회">
          <ul className="flex flex-wrap gap-x-3">{["지출 금액", "노출", "링크 클릭", "랜딩 페이지 조회"].map((c) => <li key={c}>✓ {c}</li>)}</ul>
          <p className="text-soft">'조회'는 랜딩 페이지 조회가 아니에요. '랜딩 페이지 조회'를 골라 주세요. (없으면 '들어온 사람'을 계산하지 못해요)</p>
        </Fold>
        <Fold key={mine ? "mine-open" : "mine"} open={mine} label="내 광고 설정이 없어요" preview={received !== null ? `확장 프로그램에서 받음 (${received}칸)` : "5개만 직접 입력"}>
          <MySettings received={received} value={settings} onChange={onSettings} />
        </Fold>
        <Fold label="아직 광고를 안 돌려 봤어요" preview="작게 두 세트로 돌리는 법">
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 font-semibold">광고 전 준비 <span className="tabular-nums text-soft">{done.filter(Boolean).length}/{PREP.length}</span></legend>
            {PREP.map((t, i) => (
              <label key={t} className="flex items-start gap-2">
                <input type="checkbox" checked={done[i]} onChange={() => setDone((d) => d.map((x, j) => (j === i ? !x : x)))} className="mt-1 accent-action" />{t}
              </label>
            ))}
            <p className="text-caption text-soft">작은 테스트로 고른 뒤 이긴 쪽에 몰아주는 방식 (Feit & Berman, 2019)</p>
          </fieldset>
        </Fold>
      </Folds>

    </div>
  );
}

/** 예시 보기 버튼: 왼쪽에 배 색 네모 그림 (꾸미기안_뭉치 .exb) */
function Example({ icon, children, onClick, disabled }: { icon: string; children: string; onClick: () => void; disabled?: boolean }) {
  return (
    <button type="button" onClick={onClick} disabled={disabled}
      className="inline-flex min-h-11 items-center gap-2 rounded-button border-2 border-line bg-surface px-3.5 text-label font-bold hover:border-accent disabled:opacity-(--state-disabled-opacity)">
      <span aria-hidden="true" className="grid size-7 place-items-center rounded-button bg-belly">{icon}</span>{children}
    </button>
  );
}
