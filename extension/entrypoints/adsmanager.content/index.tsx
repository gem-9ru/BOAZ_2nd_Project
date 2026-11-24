import ReactDOM from "react-dom/client";
import type { GuideStepItem } from "../../lib/guide";
import { Character } from "./Character";
import { Guide } from "./guideRunner";
import "./overlay.css";

export default defineContentScript({
  matches: ["https://adsmanager.facebook.com/*", "https://business.facebook.com/*"],
  cssInjectionMode: "ui",
  async main(ctx) {
    let guide: Guide | null = null;
    let root: ReactDOM.Root | null = null;
    let timer: number | null = null;

    function stopGuide() {
      guide?.stop();
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
          onDone={() => { guide?.markDone(); render(); }}
          onBack={() => { guide?.back(); render(); }}
          onClose={() => { stopGuide(); ui.remove(); }}
        />,
      );
    }

    browser.runtime.onMessage.addListener((msg: { type?: string; steps?: GuideStepItem[]; startIndex?: number; delta?: number }) => {
      // 패널의 [이전 칸] [다음 칸]
      if (msg.type === "guide:move" && guide) {
        if ((msg.delta ?? 0) < 0) guide.back(); else guide.markDone();
        render();
        return;
      }
      if (msg.type !== "guide:start" || !msg.steps) return;
      stopGuide();
      ui.mount();
      const total = msg.steps.length;
      guide = new Guide(document, msg.steps, msg.startIndex ?? 0, (index) => {
        void browser.runtime.sendMessage({ type: "guide:progress", index, total }).catch(() => {});
        render();
      });
      render();
      // 광고 관리자는 화면을 다시 그리거나 다음 화면으로 넘어간다 → 1초마다 칸을 다시 찾고 다시 그린다.
      timer = window.setInterval(() => {
        guide?.tick();
        render();
      }, 1000);
      return true;
    });
  },
});
