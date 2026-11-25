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
