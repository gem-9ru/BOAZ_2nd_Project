import type { FlowEvent, FlowState } from "../../../lib/flow";
import { Coach, PrimaryButton } from "../ui/Coach";

/** 종료일 다음 날 → '12월 7일' */
function nextDay(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  const n = new Date(y!, m! - 1, d! + 1);
  return `${n.getMonth() + 1}월 ${n.getDate()}일`;
}

/** 광고를 켠 뒤: 결과를 보러 올 날 + 내보내기 안내 + 올리기. */
export default function WaitStep({ state, dispatch }: { state: FlowState; dispatch: (ev: FlowEvent) => void }) {
  const day = state.endDate ? nextDay(state.endDate) : null;
  const [y, m, d] = (state.startDate ?? "").split("-").map(Number);
  const later = y && m && d ? new Date(y, m - 1, d) > new Date() : false;   // 예약 광고: 시작일이 오늘보다 뒤
  return (
    <section className="flex flex-col gap-5">
      <Coach>
        {later && `광고는 ${m}월 ${d}일에 시작해요. `}
        {day ? `${day}에 결과를 보러 오세요.` : "광고가 끝나면 결과를 보러 오세요."} 알림은 따로 가지 않아요. 그날 이 패널을 다시 열면 이 화면이 그대로 있어요.
      </Coach>
      <button type="button" onClick={() => dispatch({ type: "startExport" })} className="text-left text-body underline">
        결과 내보내는 법 보기
      </button>
      <PrimaryButton onClick={() => dispatch({ type: "startUpload" })}>결과 분석하기</PrimaryButton>
    </section>
  );
}
