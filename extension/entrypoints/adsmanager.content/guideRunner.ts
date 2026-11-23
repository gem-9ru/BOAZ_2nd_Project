// 안내 진행 (DOM만 다루고 그리기는 Character.tsx). 테스트할 수 있게 화면 그리기와 나눴다.
import type { GuideStepItem } from "../../lib/guide";
import { isKorean, locateWith } from "./locate";

export const MAX_TRIES = 3;
const LANGUAGE_TEXT = "화면 언어를 한국어로 바꿔 주세요. (메뉴 › 설정 › 언어) 바꾼 뒤 '했어요'를 눌러 주세요.";

export interface GuideView {
  index: number;
  total: number;
  found: boolean;
  text: string;
  copy?: string;
  image?: string;
  target?: HTMLElement;
  publish?: boolean;
}

export class Guide {
  private tries = 0;
  private target: HTMLElement | null = null;
  private matched = 0;   // 찾은 방법의 순서 (0보다 크면 더 앞의 진짜 칸이 나타나는지 계속 본다)
  private languageOk: boolean;
  private detach: (() => void) | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private doc: Document,
    private steps: GuideStepItem[],
    private index: number,
    private onProgress: (index: number) => void,
    private retryMs = 2000,
  ) {
    this.languageOk = isKorean(doc);
    this.seek();
  }

  view(): GuideView {
    const total = this.steps.length;
    const item = this.steps[this.index];
    if (!item) return { index: this.index, total, found: false, text: "안내를 모두 마쳤어요." };
    if (!this.languageOk) return { index: this.index, total, found: false, text: LANGUAGE_TEXT };
    if (this.target) {
      const hint = item.entry.find[this.matched]?.say;
      return { index: this.index, total, found: true, target: this.target, publish: item.entry.publish,
               text: (hint ?? item.entry.say).replace("{value}", item.value ?? ""), copy: item.value };
    }
    if (this.tries >= MAX_TRIES) {
      return { index: this.index, total, found: false, text: item.entry.fallback.text, image: item.entry.fallback.image, copy: item.value };
    }
    return { index: this.index, total, found: false, text: "칸을 찾는 중이에요…" };
  }

  /** '했어요' 버튼: 언어를 바꿨거나, 못 찾은 칸을 직접 채웠거나, 수동 단계를 마침. 게시 버튼은 절대 누르지 않는다. */
  markDone(): void {
    if (!this.languageOk) {
      this.languageOk = true;
      this.seek();
      return;
    }
    this.advance();
  }

  /** 못 찾았을 때 다시 찾기 (콘텐츠 스크립트는 retryMs마다 부르고, 테스트는 직접 부른다). */
  retryNow(): void {
    if (this.target || !this.steps[this.index]) return;
    this.tries += 1;
    this.seek();
  }

  /** 화면이 바뀌었을 수 있으니 다시 본다: 아직 못 찾았거나, 찾았던 칸이 다시 그려져 사라졌으면 다시 찾는다. */
  tick(): void {
    if (!this.steps[this.index] || !this.languageOk) return;
    const item = this.steps[this.index]!;
    const better = this.matched > 0 && locateWith(this.doc, item.entry.find.slice(0, this.matched)) !== null;
    if (!this.target || !this.target.isConnected || better) {
      const tries = this.tries;
      this.seek();
      this.tries = tries;
    }
  }

  stop(): void {
    this.detach?.();
    if (this.timer) clearTimeout(this.timer);
  }

  private advance(): void {
    this.stop();
    this.index += 1;
    this.tries = 0;
    this.onProgress(this.index);
    this.seek();
  }

  private seek(): void {
    this.detach?.();
    this.detach = null;
    const item = this.steps[this.index];
    const hit = item && this.languageOk ? locateWith(this.doc, item.entry.find) : null;
    this.target = hit?.el ?? null;
    this.matched = hit?.index ?? 0;
    const isHint = hit ? Boolean(item!.entry.find[hit.index]?.say) : false;
    if (this.target && item && item.entry.done === "value" && !isHint) {
      const el = this.target;
      const onChange = () => this.advance();
      // 'change'는 입력을 마쳤을 때(칸을 떠나거나 고름) 한 번 온다. 글자 하나마다 오는 'input'으로 넘기지 않는다.
      el.addEventListener("change", onChange, { once: true });
      this.detach = () => el.removeEventListener("change", onChange);
    }
    if (!this.target && item && this.languageOk && this.retryMs > 0 && this.tries < MAX_TRIES) {
      this.timer = setTimeout(() => this.retryNow(), this.retryMs);
    }
  }
}
