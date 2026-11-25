import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(() => cleanup());

// jsdom에는 ResizeObserver가 없어서 Recharts의 ResponsiveContainer가 멈춘다 (테스트 환경만).
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver;
(globalThis as { __AD_COACH_QUIET__?: boolean }).__AD_COACH_QUIET__ = true;   // 진단 줄([ad-coach])은 테스트 출력에 안 보이게
