// 대화 상태를 chrome.storage.local에 저장·복원 (사이드 패널을 닫았다 열어도 이어짐).
import { initialState, type FlowState } from "./flow";

export const STATE_KEY = "coach.v3.state";
const KEY = STATE_KEY;

export async function loadState(): Promise<FlowState> {
  const got = await browser.storage.local.get(KEY);
  const saved = got[KEY] as (Omit<FlowState, "step"> & { step: string; result?: unknown }) | undefined;
  if (!saved) return initialState();
  // 예전 ③(패널에서 파일 올리기 → 결과)은 없어졌다: 그 상태로 저장돼 있으면 코드 넣기로 옮긴다
  const { result: _old, ...rest } = saved;
  // 없어진 수정 모드('fix')로 저장돼 있으면 결과 화면으로
  const step = saved.step === "result" ? "upload" : saved.step === "fix" ? "plan" : saved.step;
  return { ...initialState(), ...rest, step } as FlowState;
}

/** 저장. 저장소에 더 새 차례(rev)가 있으면 그건 배경 스크립트가 쓴 뭉치 진행이다 → 진행(guide·step)은 저장소 것을 지키고 나머지는 이 상태로 */
export async function saveState(s: FlowState): Promise<void> {
  const got = (await browser.storage.local.get(KEY))[KEY] as FlowState | undefined;
  const merged = got && (got.rev ?? 0) > (s.rev ?? 0) ? { ...s, guide: got.guide, step: got.step, rev: got.rev } : s;
  await browser.storage.local.set({ [KEY]: merged });
}
