// 캐릭터 진행을 저장소에 쓰는 일 (사이드 패널이 닫혀 있어도 배경 스크립트가 한다) + 안내 시작 재시도.
import { reduce } from "./flow";
import { loadState, saveState } from "./storage";

export interface ProgressMessage {
  type: "guide:progress";
  index: number;
  total: number;
}

export async function handleProgress(msg: ProgressMessage): Promise<void> {
  const s = await loadState();
  if (!s.guide) return;
  const next =
    msg.index >= msg.total
      ? reduce(s, s.guide.mode === "export" ? { type: "startUpload" } : { type: "guideDone" })
      : reduce(s, { type: "guideProgress", index: msg.index });
  await saveState(next);
}

/** 광고 관리자는 늦게 뜨고 주소를 바꾸기도 해서, 캐릭터에게 보내는 첫 메시지를 몇 번 다시 보낸다. */
export async function sendWithRetry(send: () => Promise<unknown>, tries = 6, delayMs = 1500): Promise<boolean> {
  for (let i = 0; i < tries; i += 1) {
    try {
      await send();
      return true;
    } catch {
      if (delayMs) await new Promise((r) => setTimeout(r, delayMs));
    }
  }
  return false;
}
