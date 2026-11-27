// 뭉치 집: 나뭇가지로 엮은 지붕 있는 둥근 둥지(앞에 동그란 입구). 패널 제목 왼쪽에서 뭉치가 이 안에 앉아 있다.
// 안쪽은 밝은 깔개라 입구로 보이는 뭉치 뒤가 보라 머리 바탕과 겹치지 않는다. 색은 design-system 토큰(--character-nest-*).
import * as THREE from "three";
import { mergeGeometries } from "three/examples/jsm/utils/BufferGeometryUtils.js";

export interface NestColors { wall: string; lining: string; twig: string; twigLight: string; feather: string; quill: string }

/** 둥지 크기 (뭉치 모델 단위: 뭉치 키 약 3). 입구는 +z(카메라 쪽). */
export const NEST = { cy: 2, r: 2.5, sy: 0.8, mouth: (38 * Math.PI) / 180 } as const;

export function buildNest(c: NestColors): { root: THREE.Group; feather: THREE.Group; dispose: () => void } {
  const geos: THREE.BufferGeometry[] = [];
  const mats: THREE.Material[] = [];
  const keep = <T extends THREE.BufferGeometry>(g: T) => { geos.push(g); return g; };
  const mat = (color: string, side: THREE.Side = THREE.FrontSide) => {
    const m = new THREE.MeshStandardMaterial({ color, roughness: 0.95, side }); mats.push(m); return m;
  };
  const root = new THREE.Group();
  const cosMouth = Math.cos(NEST.mouth);

  // 껍질: 구에서 입구 쪽 삼각형만 뺀다. 바깥 = 벽, 조금 작은 안쪽(뒷면) = 깔개
  const sphere = new THREE.SphereGeometry(NEST.r, 56, 40).toNonIndexed();
  const pos = sphere.getAttribute("position");
  const kept: number[] = [];
  for (let i = 0; i < pos.count; i += 3) {
    let z = 0;
    for (let k = 0; k < 3; k++) z += pos.getZ(i + k) / NEST.r / 3;
    if (z > cosMouth) continue;
    for (let k = 0; k < 3; k++) kept.push(pos.getX(i + k), pos.getY(i + k), pos.getZ(i + k));
  }
  sphere.dispose();
  const shell = keep(new THREE.BufferGeometry());
  shell.setAttribute("position", new THREE.Float32BufferAttribute(kept, 3));
  shell.computeVertexNormals();
  const place = (o: THREE.Object3D) => { o.scale.y *= NEST.sy; o.position.y = NEST.cy; root.add(o); return o; };
  const wall = place(new THREE.Mesh(shell, mat(c.twig)));   // 가지 사이 틈은 진하게 (깊어 보이게)
  wall.receiveShadow = true;
  const lining = place(new THREE.Mesh(shell, mat(c.lining, THREE.BackSide)));
  lining.scale.multiplyScalar(0.95);
  lining.receiveShadow = true;

  // 입구 둘레 바탕 고리 (위에 가지를 감는다)
  const rim = place(new THREE.Mesh(keep(new THREE.TorusGeometry(NEST.r * Math.sin(NEST.mouth), 0.16, 8, 48)), mat(c.twig)));
  rim.position.z = NEST.r * cosMouth;

  // 나뭇가지: 껍질 표면을 따라 휘어 감긴 가는 가지 (주로 둘레 방향, 조금씩 비스듬히). 사이 틈은 진한 바탕이 비쳐 깊어 보인다.
  // 고정 씨앗이라 매번 같은 모양. 색별로 하나로 합쳐 그린다
  let s = 11;
  const rand = () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646;
  const tones = [c.wall, c.twig, c.wall, c.twigLight, c.wall, c.twig, c.wall, c.wall];   // 밝은 가지는 드문드문
  const byTone: THREE.BufferGeometry[][] = tones.map(() => []);
  const world = (v: THREE.Vector3) => new THREE.Vector3(v.x, v.y * NEST.sy + NEST.cy, v.z);
  const tube = (pts: THREE.Vector3[], tone: number) => {
    const g = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(world)), 8, 0.035 + rand() * 0.03, 4, false);
    byTone[tone % tones.length]!.push(g);
  };
  const up = new THREE.Vector3(0, 1, 0);
  const inMouth = (v: THREE.Vector3) => v.z / v.length() > cosMouth - 0.06;
  let tone = 0;
  for (let i = 0; i < 520; i++) {
    const n = new THREE.Vector3(rand() * 2 - 1, rand() * 2 - 1, rand() * 2 - 1);
    if (n.lengthSq() < 0.01) continue;
    n.normalize();
    const h = new THREE.Vector3().crossVectors(up, n);
    if (h.lengthSq() < 0.01) h.set(1, 0, 0);
    h.normalize();
    const m = new THREE.Vector3().crossVectors(n, h);
    const tilt = (rand() - 0.5) * 0.9;
    const t = h.multiplyScalar(Math.cos(tilt)).add(m.multiplyScalar(Math.sin(tilt)));
    const arc = (0.5 + rand() * 0.9) / NEST.r, lift = 1.01 + rand() * 0.06, bow = (rand() - 0.5) * 0.06;
    const pts = Array.from({ length: 5 }, (_, k) => {
      const ang = -arc / 2 + (arc * k) / 4, sag = bow * Math.sin((Math.PI * k) / 4);
      return n.clone().multiplyScalar(Math.cos(ang)).add(t.clone().multiplyScalar(Math.sin(ang))).multiplyScalar(NEST.r * (lift + sag));
    });
    if (pts.some(inMouth)) continue;   // 입구는 비워 둔다
    tube(pts, tone++);
  }
  // 입구 둘레: 고리를 따라 여러 겹 감은 가지
  for (let i = 0; i < 44; i++) {
    const start = rand() * Math.PI * 2, span = 0.6 + rand() * 0.7, a0 = NEST.mouth + (rand() - 0.5) * 0.12, lift = 1.03 + rand() * 0.09;
    tube(Array.from({ length: 5 }, (_, k) => {
      const t = start + (span * k) / 4, a = a0 + (rand() - 0.5) * 0.04;
      return new THREE.Vector3(Math.sin(a) * Math.cos(t), Math.sin(a) * Math.sin(t), Math.cos(a)).multiplyScalar(NEST.r * lift);
    }), tone++);
  }
  // 바깥으로 삐친 가지 몇 개
  for (let i = 0; i < 12; i++) {
    const n = new THREE.Vector3(rand() * 2 - 1, rand() * 1.2 - 0.6, rand() * 2 - 1.4).normalize();
    if (inMouth(n)) continue;
    const t = new THREE.Vector3().crossVectors(up, n).normalize();
    tube(Array.from({ length: 4 }, (_, k) => n.clone().add(t.clone().multiplyScalar(k * 0.12)).normalize().multiplyScalar(NEST.r * (1.02 + k * 0.06))), tone++);
  }
  tones.forEach((color, i) => {
    const list = byTone[i]!;
    if (!list.length) return;
    const merged = keep(mergeGeometries(list)!);
    list.forEach((g) => g.dispose());
    root.add(new THREE.Mesh(merged, mat(color)));
  });

  // 뭉치 깃털 하나: 뭉치가 나가 있는 동안 빈 둥지에 남아 '집이 비었다'를 보여 준다 (입구 턱 위로 보이게 안쪽 벽에 비스듬히 기대 둠)
  const feather = new THREE.Group();
  const vane = new THREE.Mesh(keep(new THREE.SphereGeometry(1, 24, 12)), mat(c.feather));
  vane.scale.set(0.3, 0.8, 0.05);
  feather.add(vane);
  const quill = new THREE.Mesh(keep(new THREE.CapsuleGeometry(0.03, 1.9, 3, 6)), mat(c.quill));
  quill.position.set(0, -0.15, 0.04);
  feather.add(quill);
  feather.position.set(0.15, 1.6, -0.2);
  feather.rotation.set(-0.35, 0.25, -0.75);
  feather.visible = false;
  root.add(feather);

  return { root, feather, dispose: () => { geos.forEach((g) => g.dispose()); mats.forEach((m) => m.dispose()); } };
}
