// 광고 어시스턴트 캐릭터 '뭉치' 3D 모델 (2026-11-25 시안 A 선택).
// 동그란 보라 새 + 주황 배·부리 + 머리깃 + 관절 있는 팔다리. 색은 design-system 토큰(--character-*)에서 받는다.
import * as THREE from "three";

export interface MungchiColors { body: string; limb: string; belly: string; beak: string; eye: string; pupil: string }

export interface Mungchi {
  root: THREE.Group;   // 바닥 기준 (방향 돌리기)
  body: THREE.Group;   // 출렁임·기울기
  armL: THREE.Group;   // 화면 왼쪽 어깨 관절
  armR: THREE.Group;
  legL: THREE.Group;   // 엉덩이 관절
  legR: THREE.Group;
  dispose: () => void;
}

export function buildMungchi(c: MungchiColors): Mungchi {
  const geos: THREE.BufferGeometry[] = [];
  const mats: THREE.Material[] = [];
  const mat = (color: string, roughness = 0.55) => { const m = new THREE.MeshStandardMaterial({ color, roughness }); mats.push(m); return m; };
  const mesh = (g: THREE.BufferGeometry, m: THREE.Material) => { geos.push(g); const x = new THREE.Mesh(g, m); x.castShadow = true; return x; };
  const sphere = (r: number, m: THREE.Material, seg = 40) => mesh(new THREE.SphereGeometry(r, seg, seg), m);
  const capsule = (r: number, l: number, m: THREE.Material) => mesh(new THREE.CapsuleGeometry(r, l, 10, 24), m);

  const body = mat(c.body), limb = mat(c.limb), belly = mat(c.belly), beak = mat(c.beak, 0.4), eye = mat(c.eye, 0.3), pupil = mat(c.pupil, 0.3);
  const root = new THREE.Group();
  const trunk = new THREE.Group();
  root.add(trunk);

  const ball = sphere(1, body, 64); ball.scale.set(1, 1.02, 0.92); ball.position.y = 1.55; trunk.add(ball);
  const tummy = sphere(0.72, belly, 48); tummy.scale.set(1, 1, 0.45); tummy.position.set(0, 1.25, 0.62); trunk.add(tummy);
  for (const s of [-1, 1]) {
    const e = sphere(0.2, eye); e.scale.set(1, 1.15, 0.6); e.position.set(s * 0.36, 1.85, 0.78); trunk.add(e);
    const p = sphere(0.11, pupil); p.position.set(s * 0.36, 1.84, 0.88); trunk.add(p);
    const hl = sphere(0.04, eye); hl.position.set(s * 0.36 + 0.04, 1.89, 0.9); trunk.add(hl);
  }
  const bill = mesh(new THREE.ConeGeometry(0.16, 0.32, 24), beak); bill.rotation.x = Math.PI / 2; bill.position.set(0, 1.62, 0.98); trunk.add(bill);
  for (const [dx, h, rz] of [[-0.12, 0.34, 0.35], [0.04, 0.42, 0], [0.18, 0.3, -0.4]] as const) {
    const f = capsule(0.07, h, limb); f.position.set(dx, 2.62 + h / 2, -0.05); f.rotation.z = rz; trunk.add(f);
  }

  const joint = (x: number, y: number) => { const g = new THREE.Group(); g.position.set(x, y, 0); trunk.add(g); return g; };
  const [armL, armR] = [-1, 1].map((s) => {
    const sh = joint(s * 0.95, 1.5);
    const arm = capsule(0.11, 0.42, limb); arm.position.y = -0.27; sh.add(arm);
    const hand = sphere(0.15, body); hand.position.y = -0.55; sh.add(hand);
    return sh;
  }) as [THREE.Group, THREE.Group];
  const [legL, legR] = [-1, 1].map((s) => {
    const hip = joint(s * 0.36, 0.75);
    const leg = capsule(0.12, 0.32, limb); leg.position.y = -0.22; hip.add(leg);
    const foot = sphere(0.19, beak, 32); foot.scale.set(1, 0.6, 1.55); foot.position.set(0, -0.48, 0.08); hip.add(foot);
    return hip;
  }) as [THREE.Group, THREE.Group];

  return { root, body: trunk, armL, armR, legL, legR, dispose: () => { geos.forEach((g) => g.dispose()); mats.forEach((m) => m.dispose()); } };
}
