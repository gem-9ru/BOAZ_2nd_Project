// 캐릭터 진행을 저장소에 쓰는 일 (사이드 패널이 닫혀 있어도 배경 스크립트가 한다) + 안내 시작 재시도.
import { reduce } from "./flow";
import type { GuideMsg } from "./guide";
import { loadState, saveState } from "./storage";

export type ProgressMessage = Extract<GuideMsg, { type: "guide:progress" }>;

export async function handleProgress(msg: ProgressMessage): Promise<void> {
  const s = await loadState();
  if (!s.guide) return;
  // 패널이 안내를 바꿨는데(답 바꾸기·결과 받기·처음부터 뒤 새 안내) 광고 관리자에 남은 예전 뭉치가 보낸 진행이면 버린다 (재검토 B9)
  if (msg.sig && msg.sig !== s.guide.sig) return;
  const next =
    msg.index >= msg.total
      ? reduce(s, s.guide.mode === "export" ? { type: "startUpload" } : { type: "guideDone" })
      : reduce(s, { type: "guideProgress", index: msg.index });
  await saveState({ ...next, rev: (s.rev ?? 0) + 1 });
}

/** 광고 관리자 위 [닫기]: 뭉치가 집(패널 제목 왼쪽)으로 돌아온다. 진행 칸은 그대로 둔다. */
export async function handleClosed(): Promise<void> {
  const s = await loadState();
  await saveState({ ...reduce(s, { type: "guideClosed" }), rev: (s.rev ?? 0) + 1 });
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
