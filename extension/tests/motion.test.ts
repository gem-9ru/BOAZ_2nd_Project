// 3D 캐릭터 동작 계산 (WebGL 없이 확인할 수 있는 부분)
import { describe, expect, it } from "vitest";
import { gaitFor, home, pointAngle, pose, standSpot, travelMs } from "../lib/character3d/motion";

const speeds = { walk: 260, run: 620, runDistance: 420 };
const vp = { width: 1200, height: 800 };

describe("걷기·뛰기", () => {
  it("walks when close and runs when far", () => {
    expect(gaitFor(200, speeds)).toBe("walk");
    expect(gaitFor(900, speeds)).toBe("run");
  });
  it("travel time follows the speed of the gait", () => {
    expect(travelMs(260, speeds)).toBeCloseTo(1000, 0);
    expect(travelMs(1240, speeds)).toBeCloseTo(2000, 0);
  });
});

describe("집과 서는 자리", () => {
  it("home is at the top right edge, next to the side panel", () => {
    const h = home(vp, 120);
    expect(h.x).toBeGreaterThan(vp.width - 120);
    expect(h.y).toBeLessThan(120);
  });

  it("stands right of the field when there is room, and points left", () => {
    const s = standSpot({ left: 100, top: 300, right: 400, bottom: 340, width: 300, height: 40 }, vp, 120);
    expect(s.x).toBeGreaterThanOrEqual(400);
    expect(s.side).toBe("right");
    expect(s.y + 120 * 0.45).toBeCloseTo(320, -1);
  });

  it("stands left of the field near the right edge, and stays on screen", () => {
    const s = standSpot({ left: 900, top: 10, right: 1180, bottom: 50, width: 280, height: 40 }, vp, 120);
    expect(s.side).toBe("left");
    expect(s.x + 120).toBeLessThanOrEqual(900);
    expect(s.y).toBeGreaterThanOrEqual(8);
  });
});

describe("자세", () => {
  it("walking swings the legs in opposite directions", () => {
    const p = pose("walk", 0.125);
    expect(Math.sign(p.legLeft)).toBe(-Math.sign(p.legRight));
    expect(Math.abs(p.legLeft)).toBeGreaterThan(0.2);
  });

  it("running swings more and leans forward", () => {
    const w = pose("walk", 0.125), r = pose("run", 0.078);
    expect(Math.abs(r.legLeft)).toBeGreaterThan(Math.abs(w.legLeft));
    expect(r.lean).toBeGreaterThan(w.lean);
  });

  it("pointing raises the arm on the target's side toward it", () => {
    // 칸 오른쪽에 서서(side right) 왼쪽 칸을 가리키면 화면 왼팔을 든다
    const left = pose("point", 1, { side: "right", angle: pointAngle({ x: 500, y: 300 }, { x: 200, y: 300 }) });
    expect(left.armLeftRaise).toBeGreaterThan(1.2);
    expect(Math.abs(left.armRightRaise)).toBeLessThan(0.4);
    const up = pointAngle({ x: 500, y: 300 }, { x: 500, y: 100 });
    expect(up).toBeCloseTo(Math.PI / 2, 2);
  });
});

import { bubbleSpot } from "../lib/character3d/motion";

describe("말풍선 자리", () => {
  const size = 120, bubble = { width: 340, height: 160 };
  it("never covers the field it points at", () => {
    const field = { left: 870, top: 365, right: 1110, bottom: 405, width: 240, height: 40 };
    const at = { x: 1120, y: 330 };
    const b = bubbleSpot(at, size, bubble, { width: 1280, height: 800 }, field);
    const overlap = b.x < field.right && b.x + bubble.width > field.left && b.y < field.bottom && b.y + bubble.height > field.top;
    expect(overlap).toBe(false);
    expect(b.x).toBeGreaterThanOrEqual(8);
    expect(b.y + bubble.height).toBeLessThanOrEqual(800 - 8);
  });
  it("sits right of 뭉치 when there is room", () => {
    const b = bubbleSpot({ x: 300, y: 100 }, size, bubble, { width: 1280, height: 800 }, { left: 60, top: 120, right: 290, bottom: 160, width: 230, height: 40 });
    expect(b.x).toBe(300 + size + 4);
  });
});

import { angleDiff, blendPose, headingYaw, pose as poseAt, REST, travelAt, travelDuration } from "../lib/character3d/motion";

describe("상하좌우로 걸을 때 몸 방향", () => {
  it("faces the way it walks: down = front, up = back, sides = profile", () => {
    expect(headingYaw(0, 100)).toBeCloseTo(0, 5);                 // 아래로 걸어옴 → 정면
    expect(Math.abs(headingYaw(0, -100))).toBeCloseTo(Math.PI, 5); // 위로 걸어감 → 등
    expect(headingYaw(100, 0)).toBeCloseTo(Math.PI / 2, 5);        // 오른쪽
    expect(headingYaw(-100, 0)).toBeCloseTo(-Math.PI / 2, 5);      // 왼쪽
  });
  it("diagonals sit between the two directions", () => {
    expect(headingYaw(100, -100)).toBeCloseTo((3 * Math.PI) / 4, 5);  // 오른쪽 위: 오른쪽 등
    expect(headingYaw(-100, 100)).toBeCloseTo(-Math.PI / 4, 5);       // 왼쪽 아래: 왼쪽 앞
  });
  it("turns the short way round, never a full spin", () => {
    expect(angleDiff(-Math.PI / 2, Math.PI)).toBeCloseTo(-Math.PI / 2, 5);   // 왼쪽 → 위: 90°만
    expect(angleDiff(Math.PI * 0.9, -Math.PI * 0.9)).toBeCloseTo(Math.PI * 0.2, 5);
    for (const [a, b] of [[0, 3], [3, -3], [-2.5, 2.5], [10, -10]]) expect(Math.abs(angleDiff(a!, b!))).toBeLessThanOrEqual(Math.PI + 1e-9);
  });
});

describe("천천히 출발해 천천히 멈춤", () => {
  const speed = 170, ramp = 0.35;
  it("starts and ends at zero speed and covers the whole distance", () => {
    const total = travelDuration(600, speed, ramp);
    expect(travelAt(0, 600, speed, ramp).v).toBe(0);
    expect(travelAt(total / 2, 600, speed, ramp).v).toBeCloseTo(speed, 5);
    const end = travelAt(total, 600, speed, ramp);
    expect(end.d).toBe(600);
    expect(end.done).toBe(true);
    expect(travelAt(total - 0.01, 600, speed, ramp).v).toBeLessThan(speed * 0.1);
  });
  it("never jumps or goes backwards", () => {
    const total = travelDuration(600, speed, ramp);
    let prev = 0;
    for (let t = 0; t <= total + 0.05; t += 1 / 60) {
      const { d } = travelAt(t, 600, speed, ramp);
      expect(d).toBeGreaterThanOrEqual(prev - 1e-9);
      expect(d - prev).toBeLessThanOrEqual(speed / 60 + 1e-6);   // 한 프레임에 최고 속도보다 많이 가지 않음
      prev = d;
    }
    expect(prev).toBe(600);
  });
  it("short hops never reach full speed but still ease in and out", () => {
    const total = travelDuration(20, speed, ramp);
    let top = 0;
    for (let t = 0; t <= total; t += 0.005) top = Math.max(top, travelAt(t, 20, speed, ramp).v);
    expect(top).toBeLessThan(speed);
    expect(travelAt(total, 20, speed, ramp).d).toBe(20);
  });
});

describe("동작 이어 붙이기", () => {
  it("steps follow distance: one cycle puts the legs back where they started", () => {
    const a = poseAt("walk", 0, undefined, 0.25), b = poseAt("walk", 99, undefined, 1.25);
    expect(a.legLeft).toBeCloseTo(b.legLeft, 5);
  });
  it("walking waddles side to side with the steps", () => {
    expect(Math.sign(poseAt("walk", 0, undefined, 0.25).sway)).toBe(-Math.sign(poseAt("walk", 0, undefined, 0.75).sway));
  });
  it("blending moves smoothly from one pose to the next", () => {
    const run = poseAt("run", 0, undefined, 0.25);
    const half = blendPose(REST, run, 0.5);
    expect(half.lean).toBeCloseTo(run.lean / 2, 5);
    expect(blendPose(REST, run, 0)).toEqual(REST);
    expect(blendPose(REST, run, 1).legLeft).toBeCloseTo(run.legLeft, 5);
  });
});
