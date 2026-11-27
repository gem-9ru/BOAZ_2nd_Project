import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, PrimaryButton } from "../ui/Coach";

/** 종료일 다음 날 → '12월 7일' */
function nextDay(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const n = new Date(y!, m! - 1, d! + 1);
  return `${n.getMonth() + 1}월 ${n.getDate()}일`;
}

const md = (iso: string) => { const [, m, d] = iso.split("-").map(Number); return `${m}월 ${d}일`; };

/** 광고를 켠 뒤: 결과를 보러 올 날 + 돈이 얼마까지만 나가는지 + 내보내기 안내 + 올리기 (끝나기 전엔 작은 버튼). */
export default function WaitStep({ state, dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
  const day = state.endDate ? nextDay(state.endDate) : null;
  const [y, m, d] = (state.startDate ?? "").split("-").map(Number);
  const later = y && m && d ? new Date(y, m - 1, d) > new Date() : false;   // 예약 광고: 시작일이 오늘보다 뒤
  const end = state.endDate?.slice(0, 10);
  const running = end ? new Date(`${end}T23:59:59`) >= new Date() : false;   // 아직 안 끝남 → 분석은 작은 버튼
  const over = Boolean(end) && !running;   // 광고가 끝남
  const budget = state.settings.find((x) => x.fieldId === "meta.adset.lifetime_budget")?.value;
  return (
    <section className="flex flex-col gap-5">
      <Coach>
        {!running && end ? "광고가 끝났어요. 결과 파일을 받아 분석해 볼 차례예요 → 아래 [결과 분석하기]를 눌러 주세요." : <>
        {later && `광고는 ${m}월 ${d}일에 시작해요. `}
        {day ? `${day}에 결과를 보러 오세요.` : "광고가 끝나면 결과를 보러 오세요."} 알림은 따로 가지 않아요. 그날 이 패널을 다시 열면 이 화면이 그대로 있어요.</>}
      </Coach>
      {!over && (budget || end) && (   // 끝난 뒤에는 '나가요·멈춰요'(앞으로 일)를 빼고 할 일 하나만
        <p className="rounded-card border border-line bg-paper px-3 py-2 text-body">
          {budget && `광고 세트 하나에 총 ${budget}까지만 나가요 (세트가 2개면 2배). `}
          {end && `${md(end)}이 지나면 저절로 멈춰요.`}
        </p>
      )}
      {!over && (   // 끝난 뒤에는 [결과 분석하기] 다음 화면에 내보내기 안내가 있다
        <button type="button" onClick={() => dispatch({ type: "startExport" })} className="flex min-h-11 items-center text-left text-body underline">
          결과 내보내는 법 보기
        </button>
      )}
      {running ? (
        <>
          {/* 끝나기 전엔 작은 글자 버튼: 큰 버튼과 같은 무게면 미리 누르기 쉽다 (QA R-01) */}
          <button type="button" onClick={() => dispatch({ type: "startUpload" })}
            className="inline-flex min-h-11 items-center self-start text-label font-semibold text-accent-ink underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
            그래도 지금 결과 분석하기
          </button>
          <p className="-mt-3 text-caption text-soft">광고가 끝난 뒤 받아야 합계가 맞아요 → {day}부터 눌러 주세요.</p>
        </>
      ) : <PrimaryButton onClick={() => dispatch({ type: "startUpload" })}>결과 분석하기</PrimaryButton>}
    </section>
  );
}
