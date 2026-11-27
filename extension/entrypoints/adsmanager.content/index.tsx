import ReactDOM from "react-dom/client";
import { guideSignature, type GuideMsg } from "../../lib/guide";
import { Character } from "./Character";
import { Guide } from "./guideRunner";
import "./overlay.css";

export default defineContentScript({
  matches: ["https://adsmanager.facebook.com/*", "https://business.facebook.com/*"],
  cssInjectionMode: "ui",
  async main(ctx) {
    let guide: Guide | null = null;
    let lastSig = "";   // 지금 뭉치가 받은 안내 묶음 (guideSignature)
    let root: ReactDOM.Root | null = null;
    let timer: number | null = null;
    let focus = false;   // EX-03 다음 테스트: 바꿀 칸(첫 칸)만 밝게, 나머지는 흐리게

    function stopGuide() {
      guide?.kill();
      guide = null;
      if (timer !== null) window.clearInterval(timer);
      timer = null;
    }
    ctx.onInvalidated(stopGuide);

    const ui = await createShadowRootUi(ctx, {
      name: "ad-coach-buddy",
      position: "overlay",
      onMount(container) {
        root = ReactDOM.createRoot(container);
        return root;
      },
      onRemove(r) {
        r?.unmount();
      },
    });

    function render() {
      if (!guide || !root) return;
      root.render(
        <Character
          view={guide.view()}
          keepOthers={focus && guide.view().index === 0}
          onDone={() => { guide?.apply(); render(); }}
          onBack={() => { guide?.back(); render(); }}
          onToggleAuto={() => { guide?.setAuto(!guide.view().auto); render(); }}
          onArrive={(el) => guide?.arrived(el, performance.now())}
          onClose={() => {
            // 집에 도착: 패널 제목 왼쪽 집에 다시 앉힌다 (배경 스크립트가 저장 → 패널이 따라감)
            void browser.runtime.sendMessage({ type: "guide:closed" } satisfies GuideMsg).catch(() => {});
            stopGuide();
            ui.remove();
          }}
        />,
      );
    }

    browser.runtime.onMessage.addListener((msg: GuideMsg) => {
      // 패널의 [이전 칸] [다음 칸]
      if (msg.type === "guide:goto" && guide) {
        guide.goTo(msg.index);
        render();
        return;
      }
      if (msg.type === "guide:move" && guide) {
        if (msg.delta < 0) guide.back(); else guide.apply();
        render();
        return;
      }
      if (msg.type !== "guide:start" || !msg.steps) return;
      // 뭉치가 도는 중에 '시작'이 한 번 더 오면(2026-11-26 실제 콘솔 'start 0 (restart)') 새 뭉치는 자동 진행이 꺼진 채 시작했다
      // → 사장님이 켜 둔 자동 진행은 이어 간다
      const sig = guideSignature(msg.steps);
      const wasAuto = Boolean(guide?.view().auto) && sig === lastSig;   // 같은 안내를 다시 받을 때만 (새 안내는 [자동 진행]을 눌러야 시작)
      lastSig = sig;
      console.debug("[ad-coach] start", msg.startIndex ?? 0, guide ? `(restart, auto ${wasAuto})` : "");
      stopGuide();
      focus = Boolean(msg.focus);
      ui.mount();
      const total = msg.steps.length;
      guide = new Guide(document, msg.steps, msg.startIndex ?? 0, (index) => {
        void browser.runtime.sendMessage({ type: "guide:progress", index, total, sig: msg.sig } satisfies GuideMsg).catch(() => {});
        render();
      });
      guide.followBuddy();   // 뭉치가 칸에 도착한 뒤에 누르고 넣는다
      // 자동 진행은 사장님이 말풍선의 [자동 진행]을 눌러야 시작 (2026-11-26 사용자: "바로 자동진행하지 말고")
      if (wasAuto) guide.setAuto(true);
      render();
      // 광고 관리자는 화면을 다시 그리거나 다음 화면으로 넘어간다 → 0.5초마다 칸을 다시 찾고, 자동 진행 한 걸음, 다시 그린다.
      timer = window.setInterval(() => {
        guide?.tick();
        guide?.autoStep(performance.now());
        render();
      }, 500);
      // 바로 '받았어요'로 답한다 (true를 돌려주면 패널이 답을 끝없이 기다려 '잠시만요…'에 멈춘다)
      return Promise.resolve({ started: true });
    });
  },
});
