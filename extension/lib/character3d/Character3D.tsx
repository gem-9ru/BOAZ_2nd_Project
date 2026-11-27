// 뭉치를 Three.js로 그리는 칸 하나. 광고 관리자 위(오버레이)와 패널 제목 왼쪽 집에서 같이 쓴다.
// WebGL이 없으면(테스트·오래된 브라우저) 2D 그림으로 대신한다.
import { useEffect, useRef } from "react";
import { angleDiff, blendPose, nestTrip, NEST_TRIP, pose as poseAt, REST, smooth, STRIDE, type Mode, type Pose, type Side, type TripAt } from "./motion";

export interface Character3DProps {
  mode: Mode;
  size: number;
  /** 바라보는 방향: -1 왼쪽으로 걸음, 1 오른쪽으로 걸음, 0 정면 (move가 있으면 move를 따른다) */
  facing?: -1 | 0 | 1;
  /** 지금 움직임: heading = headingYaw(dx, dy) (0 아래·정면, π 위·등), speed = 지금 속도(px/초), full = 최고 속도(px/초) */
  move?: { heading: number; speed: number; full: number };
  point?: { side: Side; angle: number };
  label?: string;
  /** 패널 제목 왼쪽 집 장면: 둥근 둥지 안에 앉아 있다가 away가 되면 걸어 나가 패널 왼쪽 끝으로 사라지고, 돌아오면 걸어 들어와 앉는다.
   *  left = 둥지 칸 왼쪽으로 더 그릴 폭(px, 패널 끝까지). 칸 높이·둥지 폭 = size */
  nest?: { away: boolean; left: number };
}

export function hasWebGL(): boolean {
  return typeof window !== "undefined" && typeof window.WebGLRenderingContext !== "undefined";
}

/** 색은 design-system 토큰(--character-*)에서만 받는다. */
function cssVar(el: Element, name: string): string {
  return getComputedStyle(el).getPropertyValue(name).trim();
}

export function Character3D({ mode, size, facing = 0, point, move, label, nest }: Character3DProps) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const live = useRef({ mode, facing, point, move, nest });
  live.current = { mode, facing, point, move, nest };
  const left = nest ? Math.max(0, nest.left) : -1;   // -1 = 둥지 없음
  const w = size + Math.max(0, left);

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
      renderer.setSize(w, size, false);
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

      // 집 장면: 둥지를 칸 오른쪽(제목 옆)에 두고, 왼쪽 여백(패널 끝까지)은 걸어 나가는 길
      let home: Awaited<ReturnType<typeof import("./nest").buildNest>> | null = null;
      let exitX = 0;
      if (left >= 0) {
        const { buildNest } = await import("./nest");
        if (stop) { renderer.dispose(); return; }
        const nc = { wall: cssVar(el, "--character-nest-wall"), lining: cssVar(el, "--character-nest-lining"),
          twig: cssVar(el, "--character-nest-twig"), twigLight: cssVar(el, "--character-nest-twig-light"), feather: colors.body, quill: colors.limb };
        if (Object.values(nc).some((v) => !v)) { renderer.dispose(); return; }
        home = buildNest(nc);
        scene.add(home.root);
        const tan = Math.tan((cam.fov * Math.PI) / 360), D = 10.8;   // 둥지(가지 포함 폭 약 5.5)가 칸 폭에 들어오게
        const cx = -(left / 2) / (size / (2 * tan * D));   // 둥지(x=0)가 칸 오른쪽 size 폭 가운데에 오게
        cam.aspect = w / size;
        cam.position.set(cx, 2.6, D);   // 앞으로 걸어 나온 뭉치 발까지 칸에 들어오게 조금 낮게
        cam.lookAt(cx, 1.8, 0);
        cam.updateProjectionMatrix();
        exitX = cx - tan * (D - NEST_TRIP.outZ) * cam.aspect - 1.2;
      }

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
      let trip: { start: number; leaving: boolean } | null = null;
      let out = Boolean(live.current.nest?.away);
      const frame = (now: number) => {
        const { facing: f, point: pt, move: mv, nest: ns } = live.current;
        let md = live.current.mode;
        let at: TripAt | null = null;
        if (home && ns) {
          if (ns.away !== out) { out = ns.away; trip = reduce ? null : { start: now, leaving: out }; }
          if (trip) { at = nestTrip(now - trip.start, exitX, trip.leaving); if (at.done) { trip = null; at = null; } }
          if (at) md = at.walking ? "walk" : "idle";
          m.root.visible = Boolean(at) || !out;
          home.feather.visible = !m.root.visible;   // 빈 둥지엔 깃털 하나
          m.root.position.set(at?.x ?? 0, at?.y ?? 0, at?.z ?? NEST_TRIP.inZ);
          floor.position.set(m.root.position.x, 0.01, m.root.position.z);
          floor.visible = m.root.position.z > 1.6;   // 둥지 안에선 깔개가 바닥
        }
        const dt = Math.min(0.05, (now - last) / 1000);
        last = now;
        const t = reduce ? 0.25 : (now - t0) / 1000;
        if (md !== was) { from = shown; was = md; changedAt = now; }
        const moving = md === "walk" || md === "run";
        if (moving) cycle += mv ? (dt * mv.speed) / (size * STRIDE[md as "walk" | "run"]) : dt * (md === "run" ? 3.2 : 2);
        let target = poseAt(md, t, pt, moving ? cycle : undefined);
        // 출발·도착할 때(느릴 때)는 걸음 폭도 작게: 서 있는 자세와 섞는다
        if (moving && mv) target = blendPose(poseAt("idle", t), target, smooth(mv.speed / Math.max(1, mv.full * 0.45)));
        shown = blendPose(from, target, reduce ? 1 : smooth((now - changedAt) / BLEND_MS));
        // 가는 방향으로 몸을 돌린다: 아래로 오면 정면, 위로 가면 등, 옆은 옆모습, 대각선은 그 사이.
        // 가리킬 땐 몸을 화면 쪽으로 살짝 열어 팔이 몸 뒤로 숨지 않게. 늘 가장 짧은 쪽으로 돈다.
        const want = at ? at.heading : moving ? (mv ? mv.heading : (f * Math.PI) / 2) : md === "point" ? (pt?.side === "right" ? 0.3 : -0.3) : 0;
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
      cleanup = () => { cancelAnimationFrame(raf); m.dispose(); home?.dispose(); floor.geometry.dispose(); renderer.dispose(); };
    });
    return () => { stop = true; cleanup(); };
  }, [size, left]);

  return (
    <span role={label ? "img" : undefined} aria-label={label} aria-hidden={label ? undefined : true}
      style={{ position: "relative", display: "inline-block", width: w, height: size }}>
      {hasWebGL() ? (
        <canvas ref={canvas} width={w} height={size} style={{ width: w, height: size, display: "block" }} />
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
