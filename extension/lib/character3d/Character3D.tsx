// 뭉치를 Three.js로 그리는 칸 하나. 광고 관리자 위(오버레이)와 패널 제목 왼쪽 집에서 같이 쓴다.
// WebGL이 없으면(테스트·오래된 브라우저) 2D 그림으로 대신한다.
import { useEffect, useRef } from "react";
import { pose as poseAt, type Mode, type Side } from "./motion";

export interface Character3DProps {
  mode: Mode;
  size: number;
  /** 바라보는 방향: -1 왼쪽으로 걸음, 1 오른쪽으로 걸음, 0 정면 */
  facing?: -1 | 0 | 1;
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

export function Character3D({ mode, size, facing = 0, point, label }: Character3DProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const live = useRef({ mode, facing, point });
  live.current = { mode, facing, point };

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
      let yaw = 0;
      const frame = (now: number) => {
        const { mode: md, facing: f, point: pt } = live.current;
        const t = reduce ? 0.25 : (now - t0) / 1000;
        const p = poseAt(md, t, pt);
        // 걸을 땐 가는 쪽으로 몸을 돌리고, 가리킬 땐 몸을 화면 쪽으로 살짝 열어 팔이 몸 뒤로 숨지 않게
        const want = md === "walk" || md === "run" ? f * 1.0 : md === "point" ? (pt?.side === "right" ? 0.3 : -0.3) : 0;
        yaw += (want - yaw) * (reduce ? 1 : 0.15);
        m.root.rotation.y = yaw;
        m.body.position.y = p.bob * 2;
        m.body.rotation.x = p.lean;
        m.body.rotation.z = p.headTilt * 0.4;
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
