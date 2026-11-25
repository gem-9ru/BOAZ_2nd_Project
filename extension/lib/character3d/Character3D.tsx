// 뭉치를 Three.js로 그리는 칸 하나. 광고 관리자 위(오버레이)와 패널 제목 왼쪽 집에서 같이 쓴다.
// WebGL이 없으면(테스트·오래된 브라우저) 2D 그림으로 대신한다.
import { useEffect, useRef } from "react";
import { angleDiff, blendPose, pose as poseAt, REST, smooth, STRIDE, type Mode, type Pose, type Side } from "./motion";

export interface Character3DProps {
  mode: Mode;
  size: number;
  /** 바라보는 방향: -1 왼쪽으로 걸음, 1 오른쪽으로 걸음, 0 정면 (move가 있으면 move를 따른다) */
  facing?: -1 | 0 | 1;
  /** 지금 움직임: heading = headingYaw(dx, dy) (0 아래·정면, π 위·등), speed = 지금 속도(px/초), full = 최고 속도(px/초) */
  move?: { heading: number; speed: number; full: number };
  point?: { side: Side; angle: number };
  label?: string;
}

export function hasWebGL(): boolean {
  return typeof window !== "undefined" && typeof window.WebGLRenderingContext !== "undefined";
}

/** 색은 design-system 토큰(--character-*)에서만 받는다. */
function cssVar(el: Element, name: string): string {
  return getComputedStyle(el).getPropertyValue(name).trim();
}

export function Character3D({ mode, size, facing = 0, point, move, label }: Character3DProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const live = useRef({ mode, facing, point, move });
  live.current = { mode, facing, point, move };

  useEffect(() => {
    const el = canvas.current;
    if (!el || !hasWebGL()) return;
    let stop = false;
    let cleanup = () => {};
    void import("three").then(async (THREE) => {
      if (stop) return;
      const { buildMungchi } = await import("./model");
      const colors = {
        body: cssVar(el, "--character-body"), limb: cssVar(el, "--character-limb"), belly: cssVar(el, "--character-belly"),
        beak: cssVar(el, "--character-beak"), eye: cssVar(el, "--character-eye"), pupil: cssVar(el, "--character-pupil"),
      };
      const light = { sky: cssVar(el, "--character-light-sky"), ground: cssVar(el, "--character-light-ground"), key: cssVar(el, "--character-light-key") };
      if ([...Object.values(colors), ...Object.values(light)].some((v) => !v)) return;   // 토큰을 못 읽으면 그리지 않음
      let renderer: InstanceType<typeof THREE.WebGLRenderer>;
      try {
        renderer = new THREE.WebGLRenderer({ canvas: el, antialias: true, alpha: true });
      } catch {
        return;   // WebGL을 못 열면 아무것도 그리지 않는다 (2D 대신 그림이 아래에 있음)
      }
      renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
      renderer.setSize(size, size, false);
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.shadowMap.enabled = true;
      const scene = new THREE.Scene();
      const cam = new THREE.PerspectiveCamera(30, 1, 0.1, 50);
      cam.position.set(0, 1.9, 8.6);
      cam.lookAt(0, 1.45, 0);
      scene.add(new THREE.HemisphereLight(light.sky, light.ground, 1.4));
      const key = new THREE.DirectionalLight(light.key, 2.2);
      key.position.set(3, 6, 5);
      key.castShadow = true;
      scene.add(key);
      const floor = new THREE.Mesh(new THREE.CircleGeometry(1.6, 32), new THREE.ShadowMaterial({ opacity: 0.18 }));
      floor.rotation.x = -Math.PI / 2;
      floor.receiveShadow = true;
      scene.add(floor);
      const m = buildMungchi(colors);
      scene.add(m.root);

      const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
      const t0 = performance.now();
      let raf = 0;
      let last = t0;
      let yaw = 0;
      let cycle = 0;                 // 걸음 주기 수: 간 거리로 센다 (발이 미끄러지지 않게)
      let shown: Pose = REST;        // 지금 그린 자세
      let from: Pose = REST;         // 동작이 바뀔 때의 자세 (여기서 새 동작으로 섞어 넘어간다)
      let was: Mode = live.current.mode;
      let changedAt = t0;
      const BLEND_MS = 260;
      const TURN_RATE = 12;          // 몸 돌리기 빠르기 (1/초): 약 0.25초에 거의 다 돈다
      const frame = (now: number) => {
        const { mode: md, facing: f, point: pt, move: mv } = live.current;
        const dt = Math.min(0.05, (now - last) / 1000);
        last = now;
        const t = reduce ? 0.25 : (now - t0) / 1000;
        if (md !== was) { from = shown; was = md; changedAt = now; }
        const moving = md === "walk" || md === "run";
        if (moving) cycle += mv ? (dt * mv.speed) / (size * STRIDE[md]) : dt * (md === "run" ? 3.2 : 2);
        let target = poseAt(md, t, pt, moving ? cycle : undefined);
        // 출발·도착할 때(느릴 때)는 걸음 폭도 작게: 서 있는 자세와 섞는다
        if (moving && mv) target = blendPose(poseAt("idle", t), target, smooth(mv.speed / Math.max(1, mv.full * 0.45)));
        shown = blendPose(from, target, reduce ? 1 : smooth((now - changedAt) / BLEND_MS));
        // 가는 방향으로 몸을 돌린다: 아래로 오면 정면, 위로 가면 등, 옆은 옆모습, 대각선은 그 사이.
        // 가리킬 땐 몸을 화면 쪽으로 살짝 열어 팔이 몸 뒤로 숨지 않게. 늘 가장 짧은 쪽으로 돈다.
        const want = moving ? (mv ? mv.heading : (f * Math.PI) / 2) : md === "point" ? (pt?.side === "right" ? 0.3 : -0.3) : 0;
        yaw += angleDiff(yaw, want) * (reduce ? 1 : 1 - Math.exp(-dt * TURN_RATE));
        const p = shown;
        m.root.rotation.y = yaw;
        m.body.position.y = p.bob * 2;
        m.body.rotation.x = p.lean;
        m.body.rotation.z = p.headTilt * 0.4 + p.sway;
        m.legL.rotation.x = p.legLeft;
        m.legR.rotation.x = p.legRight;
        m.armL.rotation.x = p.armLeftSwing;
        m.armR.rotation.x = p.armRightSwing;
        m.armL.rotation.z = -p.armLeftRaise;
        m.armR.rotation.z = p.armRightRaise;
        renderer.render(scene, cam);
        if (!stop) raf = requestAnimationFrame(frame);
      };
      raf = requestAnimationFrame(frame);
      cleanup = () => { cancelAnimationFrame(raf); m.dispose(); floor.geometry.dispose(); renderer.dispose(); };
    });
    return () => { stop = true; cleanup(); };
  }, [size]);

  return (
    <span role={label ? "img" : undefined} aria-label={label} aria-hidden={label ? undefined : true}
      style={{ position: "relative", display: "inline-block", width: size, height: size }}>
      {hasWebGL() ? (
        <canvas ref={canvas} width={size} height={size} style={{ width: size, height: size, display: "block" }} />
      ) : (
        <Flat size={size} />
      )}
    </span>
  );
}

/** WebGL이 없을 때의 뭉치 (예전 2D 그림). */
function Flat({ size }: { size: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 420 420" data-character="flat">
      <ellipse cx="210" cy="250" rx="160" ry="150" style={{ fill: "var(--character-body)" }} />
      <ellipse cx="210" cy="290" rx="100" ry="80" style={{ fill: "var(--character-belly)" }} />
      <circle cx="160" cy="210" r="18" style={{ fill: "var(--character-eye)" }} />
      <circle cx="260" cy="210" r="18" style={{ fill: "var(--character-eye)" }} />
      <path d="M190 245 L230 245 L210 272 Z" style={{ fill: "var(--character-beak)" }} />
    </svg>
  );
}
