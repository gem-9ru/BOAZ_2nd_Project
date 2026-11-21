// 대화 상태를 chrome.storage.local에 저장·복원 (사이드 패널을 닫았다 열어도 이어짐).
import { initialState, type FlowState } from "./flow";

const KEY = "coach.v3.state";

export async function loadState(): Promise<FlowState> {
  const got = await browser.storage.local.get(KEY);
  const saved = got[KEY] as FlowState | undefined;
  return saved ? { ...initialState(), ...saved } : initialState();
}

export async function saveState(s: FlowState): Promise<void> {
  await browser.storage.local.set({ [KEY]: s });
}
