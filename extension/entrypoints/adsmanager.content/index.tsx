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
          onClose={() => { guide?.stop(); ui.remove(); }}
        />,
      );
    }

    browser.runtime.onMessage.addListener((msg: { type?: string; steps?: GuideStepItem[]; startIndex?: number }) => {
      if (msg.type !== "guide:start" || !msg.steps) return;
      guide?.stop();
      ui.mount();
      guide = new Guide(document, msg.steps, msg.startIndex ?? 0, (index) => {
        void browser.runtime.sendMessage({ type: "guide:progress", index }).catch(() => {});
        render();
      });
      render();
      // 화면이 바뀌어 칸이 새로 생기면 다시 그린다 (찾는 중 → 찾음).
      const id = window.setInterval(render, 1000);
      ctx.onInvalidated(() => window.clearInterval(id));
    });
  },
});
