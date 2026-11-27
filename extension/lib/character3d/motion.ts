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
  sway: number;          // 좌우 뒤뚱 (걸음과 같이)
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

/** 집 쪽 출입구: 광고 관리자 화면 오른쪽 위 끝 바로 바깥 (사이드 패널 제목 왼쪽 둥지와 맞닿은 쪽).
 *  패널 둥지에서 걸어 나온 뭉치가 여기서 화면 안으로 걸어 들어오고, 닫으면 여기로 걸어 나가 패널 둥지로 돌아간다. */
export function home(vp: Viewport): Point {
  return { x: vp.width, y: 16 };
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

export const REST: Pose = { legLeft: 0, legRight: 0, armLeftSwing: 0, armRightSwing: 0, armLeftRaise: 0.12, armRightRaise: 0.12, bob: 0, lean: 0, headTilt: 0, sway: 0 };
const TAU = Math.PI * 2;

/** 한 걸음 주기(왼발+오른발)에 나아가는 거리. 캐릭터 크기 비율. 발이 바닥에서 미끄러지지 않게 주기를 거리로 센다. */
export const STRIDE = { walk: 0.75, run: 1.2 } as const;

/** 시간 t(초)의 자세. point는 side(서 있는 쪽)와 angle(pointAngle)을 받는다.
 *  걷기·뛰기는 cycle(걸음 주기 수, 거리로 셈)을 주면 그걸 쓰고, 없으면 시간으로 센다. */
export function pose(mode: Mode, t: number, point?: { side: Side; angle: number }, cycle?: number): Pose {
  switch (mode) {
    case "walk": {
      const c = cycle ?? t * 2;   // 1초에 두 걸음 주기
      const ph = Math.sin(c * TAU);
      return { ...REST, legLeft: 0.55 * ph, legRight: -0.55 * ph, armLeftSwing: -0.45 * ph, armRightSwing: 0.45 * ph,
        bob: 0.03 * Math.abs(Math.sin(c * TAU)), lean: 0.06, sway: 0.07 * ph };
    }
    case "run": {
      const c = cycle ?? t * 3.2;
      const ph = Math.sin(c * TAU);
      return { ...REST, legLeft: 0.95 * ph, legRight: -0.95 * ph, armLeftSwing: -0.85 * ph, armRightSwing: 0.85 * ph,
        armLeftRaise: 0.35, armRightRaise: 0.35, bob: 0.07 * Math.abs(Math.sin(c * TAU)), lean: 0.28, sway: 0.04 * ph };
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
const NEAR_WIDTH = 380;   // 가리킨 곳부터 오른쪽으로 비워 둘 너비 (메타 칸 한 줄)
const NEAR_BELOW = 70;    // 가리킨 곳 아래로 비워 둘 높이 (제목 아래 칸 하나)
const NEAR_SMALL = 200;   // 이보다 좁은 것(제목·라디오)을 가리킬 때만 아래·오른쪽을 비워 둔다

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
  const clearOf = (t: { left: number; top: number; right: number; bottom: number } | null) => (p: Point) =>
    !t || p.x >= t.right || p.x + bubble.width <= t.left || p.y >= t.bottom || p.y + bubble.height <= t.top;
  // 가리킨 곳 바로 아래·오른쪽도 비워 둔다: 메타는 제목·라디오 아래·옆에 실제 칸(금액·설명)을 둔다 (2026-11-26 실제 화면에서 덮었음)
  const small = target && target.right - target.left < NEAR_SMALL;
  const near = target && (small ? { left: target.left, top: target.top, right: Math.max(target.right, target.left + NEAR_WIDTH), bottom: target.bottom + NEAR_BELOW } : target);
  const around = target ? [
    { x: clampX(target.left), y: near!.bottom + gap },
    { x: clampX(target.left), y: target.top - bubble.height - gap },
  ] : [];
  return [...candidates, ...around].find((p) => fits(p) && clearOf(near)(p))
    ?? candidates.find((p) => fits(p) && clearOf(target)(p)) ?? candidates.find(fits) ?? { x: clampX(candidates[0]!.x), y: clampY(at.y) };
}

// ── 상하좌우 이동 ──

/** 화면에서 가는 방향 → 몸 방향(y축 회전). 0 = 정면(아래로 걸어옴), π = 등(위로 걸어감), π/2 = 오른쪽, -π/2 = 왼쪽.
 *  대각선은 그 사이 (오른쪽 위 = 3π/4, 오른쪽 등이 보임). */
export function headingYaw(dx: number, dy: number): number {
  return Math.atan2(dx, dy);
}

/** a에서 b로 가는 가장 짧은 회전 (-π ~ π). 왼쪽(-π/2)에서 위(π)로 돌 때 한 바퀴 돌지 않게. */
export function angleDiff(a: number, b: number): number {
  return ((((b - a + Math.PI) % TAU) + TAU) % TAU) - Math.PI;
}

/** 출발할 땐 천천히 빨라지고 도착할 땐 천천히 멈춘다 (가속 → 일정 → 감속).
 *  거리가 짧으면 최고 속도에 못 미친 채 감속한다. ramp = 최고 속도까지 걸리는 시간(초). */
export function travelAt(elapsed: number, dist: number, speed: number, ramp: number): { d: number; v: number; done: boolean } {
  if (dist <= 0) return { d: 0, v: 0, done: true };
  const a = speed / Math.max(ramp, 1e-3);
  const peak = Math.min(speed, Math.sqrt(a * dist));   // 짧으면 삼각형
  const tr = peak / a;                                  // 가속·감속에 걸리는 시간
  const dr = (peak * tr) / 2;                           // 가속하며 가는 거리
  const tc = (dist - 2 * dr) / peak;                    // 일정 속도 시간
  const total = 2 * tr + tc;
  const t = Math.max(0, elapsed);
  if (t >= total) return { d: dist, v: 0, done: true };
  if (t < tr) return { d: (a * t * t) / 2, v: a * t, done: false };
  if (t < tr + tc) return { d: dr + peak * (t - tr), v: peak, done: false };
  const left = total - t;
  return { d: dist - (a * left * left) / 2, v: a * left, done: false };
}

export function travelDuration(dist: number, speed: number, ramp: number): number {
  const a = speed / Math.max(ramp, 1e-3);
  const peak = Math.min(speed, Math.sqrt(a * Math.max(dist, 0)));
  return peak > 0 ? 2 * (peak / a) + (dist - (peak * peak) / a) / peak : 0;
}

/** 두 자세 사이 (k = 0이면 a, 1이면 b). 동작이 바뀔 때·멈추며 걸음이 잦아들 때 쓴다. */
export function blendPose(a: Pose, b: Pose, k: number): Pose {
  const w = Math.min(Math.max(k, 0), 1);
  const out = { ...a };
  for (const key of Object.keys(a) as (keyof Pose)[]) out[key] = a[key] + (b[key] - a[key]) * w;
  return out;
}

/** 0→1을 부드럽게 (시작·끝에서 느림). */
export function smooth(k: number): number {
  const x = Math.min(Math.max(k, 0), 1);
  return x * x * (3 - 2 * x);
}

/** 패널 둥지 ↔ 광고 관리자 길: 둥지 입구에서 폴짝 나와 패널 왼쪽 끝(광고 관리자 쪽)으로 걸어 나가고, 들어올 땐 거꾸로.
 *  단위는 3D 모델 단위 (뭉치 키 약 3). 광고 관리자 쪽 뭉치는 NEST_EXIT_MS 뒤에 나타난다. */
export const NEST_TRIP = { inZ: 0.2, outZ: 2.6, peak: 1.1, hopMs: 450, walk: 3.4 } as const;
export const NEST_EXIT_MS = 1900;

export interface TripAt { x: number; y: number; z: number; heading: number; walking: boolean; done: boolean }

/** elapsed(ms) 시점의 위치. exitX = 패널 왼쪽 끝 너머(음수). leaving = 나가는 중, 아니면 들어오는 중 */
export function nestTrip(elapsed: number, exitX: number, leaving: boolean): TripAt {
  const { inZ, outZ, peak, hopMs, walk } = NEST_TRIP;
  const walkMs = (Math.abs(exitX) / walk) * 1000;
  const hop = (k: number, from: number, to: number) => ({ z: from + (to - from) * k, y: peak * 4 * k * (1 - k) });
  if (leaving) {
    if (elapsed < hopMs) return { x: 0, ...hop(elapsed / hopMs, inZ, outZ), heading: 0, walking: true, done: false };
    const k = Math.min(1, (elapsed - hopMs) / walkMs);
    return { x: exitX * k, y: 0, z: outZ, heading: headingYaw(-1, 0), walking: k < 1, done: k >= 1 };
  }
  if (elapsed < walkMs) return { x: exitX * (1 - elapsed / walkMs), y: 0, z: outZ, heading: headingYaw(1, 0), walking: true, done: false };
  const k = Math.min(1, (elapsed - walkMs) / hopMs);
  return { x: 0, ...hop(k, outZ, inZ), heading: k < 1 ? Math.PI : 0, walking: k < 1, done: k >= 1 };
}
