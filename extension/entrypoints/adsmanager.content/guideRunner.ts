// 안내 진행 (DOM만 다루고 그리기는 Character.tsx). 테스트할 수 있게 화면 그리기와 나눴다.
import type { GuideStepItem } from "../../lib/guide";
import { isKorean, locate } from "./locate";

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
      return { index: this.index, total, found: true, target: this.target, publish: item.entry.publish,
               text: item.entry.say.replace("{value}", item.value ?? ""), copy: item.value };
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
    this.target = item && this.languageOk ? locate(this.doc, item.entry.find) : null;
    if (this.target && item && item.entry.done === "value") {
      const el = this.target;
      const onChange = () => this.advance();
      el.addEventListener("input", onChange, { once: true });
      el.addEventListener("change", onChange, { once: true });
      this.detach = () => {
        el.removeEventListener("input", onChange);
        el.removeEventListener("change", onChange);
      };
    }
    if (!this.target && item && this.languageOk && this.retryMs > 0 && this.tries < MAX_TRIES) {
      this.timer = setTimeout(() => this.retryNow(), this.retryMs);
    }
  }
}
