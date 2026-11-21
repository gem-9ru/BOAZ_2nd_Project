export default defineBackground(() => {
  // 확장 아이콘을 누르면 사이드 패널이 열린다.
  browser.sidePanel?.setPanelBehavior({ openPanelOnActionClick: true }).catch(() => {});
});
