// 광고 어시스턴트 3D 캐릭터의 동작 계산 (WebGL 없이 계산만). 값(속도·크기)은 design-system 토큰에서 받는다.

export type Mode = "idle" | "walk" | "run" | "point" | "wave";
export type Side = "left" | "right";

export interface Speeds {
  walk: number;        // px/초
  run: number;         // px/초
  runDistance: number; // 이보다 멀면 뛴다 (px)
}

export interface Box { left: number; top: number; right: number; bottom: number; width: number; height: number }
export interface Viewport { width: number; height: number }
export interface Point { x: number; y: number }

/** 관절 각도(라디안). 화면 기준 왼팔·오른팔 (캐릭터는 화면을 보고 선다). */
export interface Pose {
  legLeft: number;       // 앞뒤로 흔들기
  legRight: number;
  armLeftSwing: number;  // 걸을 때 앞뒤로
  armRightSwing: number;
  armLeftRaise: number;  // 옆으로 들기 (0 = 내림, π/2 = 수평)
  armRightRaise: number;
  bob: number;           // 위아래 출렁임 (몸 크기 비율)
  lean: number;          // 앞으로 기울기
  headTilt: number;
}

const MARGIN = 8;
const HAND_HEIGHT = 0.45; // 손이 캐릭터 칸 위에서 이 비율 높이

export function gaitFor(distance: number, s: Speeds): "walk" | "run" {
  return distance > s.runDistance ? "run" : "walk";
}

export function travelMs(distance: number, s: Speeds): number {
  const speed = gaitFor(distance, s) === "run" ? s.run : s.walk;
  return (distance / speed) * 1000;
}

/** 집: 광고 관리자 화면의 오른쪽 위 끝 (사이드 패널 제목 왼쪽 집과 맞닿은 쪽). 반쯤 화면 밖에서 걸어 나온다. */
export function home(vp: Viewport, size: number): Point {
  return { x: vp.width - size * 0.35, y: 16 };
}

/** 칸 옆 서는 자리: 오른쪽에 자리가 있으면 오른쪽(왼쪽을 가리킴), 없으면 왼쪽. 손 높이를 칸 가운데에 맞춘다. */
export function standSpot(r: Box, vp: Viewport, size: number): Point & { side: Side } {
  const right = r.right + MARGIN + size <= vp.width - MARGIN;
  const x = right ? r.right + MARGIN : Math.max(MARGIN, r.left - MARGIN - size);
  const y = Math.min(Math.max(MARGIN, r.top + r.height / 2 - size * HAND_HEIGHT), vp.height - size - MARGIN);
  return { x, y, side: right ? "right" : "left" };
}

/** 손에서 목표까지의 각도 (화면 기준, 위쪽이 +). 0 = 오른쪽, π = 왼쪽, π/2 = 위. */
export function pointAngle(from: Point, to: Point): number {
  return Math.atan2(from.y - to.y, to.x - from.x);
}

export function handPoint(at: Point, size: number, side: Side): Point {
  return { x: at.x + (side === "right" ? size * 0.2 : size * 0.8), y: at.y + size * HAND_HEIGHT };
}

const REST: Pose = { legLeft: 0, legRight: 0, armLeftSwing: 0, armRightSwing: 0, armLeftRaise: 0.12, armRightRaise: 0.12, bob: 0, lean: 0, headTilt: 0 };

/** 시간 t(초)의 자세. point는 side(서 있는 쪽)와 angle(pointAngle)을 받는다. */
export function pose(mode: Mode, t: number, point?: { side: Side; angle: number }): Pose {
  const TAU = Math.PI * 2;
  switch (mode) {
    case "walk": {
      const ph = Math.sin(t * TAU * 2);   // 1초에 두 걸음 주기
      return { ...REST, legLeft: 0.55 * ph, legRight: -0.55 * ph, armLeftSwing: -0.45 * ph, armRightSwing: 0.45 * ph,
        bob: 0.03 * Math.abs(Math.sin(t * TAU * 2)), lean: 0.06 };
    }
    case "run": {
      const ph = Math.sin(t * TAU * 3.2);
      return { ...REST, legLeft: 0.95 * ph, legRight: -0.95 * ph, armLeftSwing: -0.85 * ph, armRightSwing: 0.85 * ph,
        armLeftRaise: 0.35, armRightRaise: 0.35, bob: 0.07 * Math.abs(Math.sin(t * TAU * 3.2)), lean: 0.28 };
    }
    case "point": {
      // 서 있는 쪽의 반대편(목표 쪽) 팔을 목표 각도로 든다. 화면 왼쪽을 가리키면 왼팔.
      const side = point?.side ?? "right";
      const a = point?.angle ?? Math.PI;
      // 팔 들기: 목표가 수평이면 π/2, 위면 더, 아래면 덜
      const toward = side === "right" ? Math.PI - a : a;
      const raise = Math.min(Math.max(Math.PI / 2 + Math.atan2(Math.sin(toward), Math.abs(Math.cos(toward))), 0.6), 2.6);
      const breathe = 0.012 * Math.sin(t * TAU * 0.8);
      const tap = 0.08 * Math.max(0, Math.sin(t * TAU * 1.2)); // 손끝을 살짝 까딱
      // 팔을 살짝 앞으로 내밀어(swing) 몸 뒤로 숨지 않게
      return side === "right"
        ? { ...REST, armLeftRaise: raise + tap, armLeftSwing: -0.35, armRightRaise: 0.15, bob: breathe, headTilt: 0.15 }
        : { ...REST, armRightRaise: raise + tap, armRightSwing: -0.35, armLeftRaise: 0.15, bob: breathe, headTilt: -0.15 };
    }
    case "wave": {
      const w = Math.sin(t * TAU * 2);
      return { ...REST, armRightRaise: 2.4 + 0.35 * w, bob: 0.015 * Math.sin(t * TAU), headTilt: 0.08 * w };
    }
    default:
      return { ...REST, bob: 0.015 * Math.sin(t * Math.PI * 2 * 0.7) };
  }
}

/** 말풍선 자리: 뭉치 오른쪽 → 왼쪽 → 아래 → 위 순서로, 가리키는 칸을 덮지 않고 화면 안에 들어오는 첫 자리. */
export function bubbleSpot(at: Point, size: number, bubble: { width: number; height: number }, vp: Viewport, target: Box | null, gap = 4): Point {
  const clampY = (y: number) => Math.min(Math.max(MARGIN, y), vp.height - bubble.height - MARGIN);
  const clampX = (x: number) => Math.min(Math.max(MARGIN, x), vp.width - bubble.width - MARGIN);
  const candidates: Point[] = [
    { x: at.x + size + gap, y: clampY(at.y) },
    { x: at.x - bubble.width - gap, y: clampY(at.y) },
    { x: clampX(at.x + size / 2 - bubble.width / 2), y: at.y + size + gap },
    { x: clampX(at.x + size / 2 - bubble.width / 2), y: at.y - bubble.height - gap },
  ];
  const fits = (p: Point) => p.x >= MARGIN && p.x + bubble.width <= vp.width - MARGIN && p.y >= MARGIN && p.y + bubble.height <= vp.height - MARGIN;
  const clear = (p: Point) => !target || p.x >= target.right || p.x + bubble.width <= target.left || p.y >= target.bottom || p.y + bubble.height <= target.top;
  return candidates.find((p) => fits(p) && clear(p)) ?? candidates.find(fits) ?? { x: clampX(candidates[0]!.x), y: clampY(at.y) };
}
