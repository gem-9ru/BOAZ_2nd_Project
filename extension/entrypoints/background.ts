import type { GuideMsg } from "../lib/guide";
import { handleClosed, handleProgress } from "../lib/progress";

export default defineBackground(() => {
  // 확장 아이콘을 누르면 사이드 패널이 열린다.
  browser.sidePanel?.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
  // 캐릭터 진행은 패널이 닫혀 있어도 저장한다 (패널은 저장소 변화를 보고 따라간다).
  browser.runtime.onMessage.addListener((msg: GuideMsg) => {
    if (msg?.type === "guide:progress") void handleProgress(msg);
    if (msg?.type === "guide:closed") void handleClosed();
  });
});
