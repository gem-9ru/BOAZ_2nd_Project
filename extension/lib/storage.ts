// 대화 상태를 chrome.storage.local에 저장·복원 (사이드 패널을 닫았다 열어도 이어짐).
import { initialState, type FlowState } from "./flow";

const KEY = "coach.v3.state";

export async function loadState(): Promise<FlowState> {
  const got = await browser.storage.local.get(KEY);
  const saved = got[KEY] as (Omit<FlowState, "step"> & { step: string; result?: unknown }) | undefined;
  if (!saved) return initialState();
  // 예전 ③(패널에서 파일 올리기 → 결과)은 없어졌다: 그 상태로 저장돼 있으면 코드 넣기로 옮긴다
  const { result: _old, ...rest } = saved;
  const step = saved.step === "result" ? "upload" : saved.step;
  return { ...initialState(), ...rest, step } as FlowState;
}

export async function saveState(s: FlowState): Promise<void> {
  await browser.storage.local.set({ [KEY]: s });
}
