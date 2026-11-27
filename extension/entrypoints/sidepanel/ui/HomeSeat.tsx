import { useEffect, useRef, useState } from "react";
import { Character3D } from "../../../lib/character3d/Character3D";

function homeSize(): number {
  const v = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--character-home-size"));
  return Number.isFinite(v) ? v : 40;
}

const AWAY = "뭉치가 광고 관리자에서 안내하고 있어요";

// 둥지 나뭇가지: 타원 둘레를 따라 조금씩 비뚤게 놓은 짧은 곡선. 매번 같은 모양이 나오도록 고정 씨앗으로 뽑는다.
const TONES = ["stroke-belly-ink", "stroke-belly-strong", "stroke-belly", "stroke-belly-ink"];
function twigs(n: number, seed: number, from: number, to: number, rMin: number, rMax: number) {
  let s = seed;
  const rand = () => ((s = (s * 16807) % 2147483647) - 1) / 2147483646;
  return Array.from({ length: n }, (_, i) => {
    const t = from + ((to - from) * (i + rand())) / n;
    const r = rMin + (rMax - rMin) * rand();
    const [x, y] = [24 + 22 * r * Math.cos(t), 24 + 19 * r * Math.sin(t)];
    const a = Math.atan2(19 * Math.cos(t), -22 * Math.sin(t)) + (rand() - 0.5) * 0.9;
    const L = 4 + rand() * 6, bend = (rand() - 0.5) * 3;
    const [dx, dy] = [(Math.cos(a) * L) / 2, (Math.sin(a) * L) / 2];
    const f = (v: number) => v.toFixed(1);
    return {
      d: `M${f(x - dx)} ${f(y - dy)} Q${f(x - dy * bend / L * 2)} ${f(y + dx * bend / L * 2)} ${f(x + dx)} ${f(y + dy)}`,
      tone: TONES[i % TONES.length],
      w: 0.7 + rand() * 0.9,
    };
  });
}
const BACK_TWIGS = twigs(46, 7, 0, Math.PI * 2, 0.8, 1.06);
const FRONT_TWIGS = twigs(30, 13, Math.PI * 0.06, Math.PI * 0.94, 0.66, 1.04);

function Twigs({ list }: { list: ReturnType<typeof twigs> }) {
  return (
    <g className="fill-none" strokeLinecap="round">
      {list.map((t, i) => <path key={i} d={t.d} className={t.tone} strokeWidth={t.w} />)}
    </g>
  );
}

/** 패널 제목 왼쪽 = 뭉치 집(나뭇가지 둥지). 평소엔 둥지 속 크림색 깔개에 앉아 숨 쉬고(가리키면 손 흔듦),
 *  광고 관리자에서 안내하는 동안엔 뭉치 깃털 하나만 남은 빈 둥지. */
export function HomeSeat({ away }: { away: boolean }) {
  const [hi, setHi] = useState(false);
  // 안내를 마치고 집에 돌아오면 잠깐 손을 흔든다
  const wasAway = useRef(away);
  useEffect(() => {
    if (wasAway.current && !away) {
      setHi(true);
      const t = setTimeout(() => setHi(false), 2400);
      wasAway.current = away;
      return () => clearTimeout(t);
    }
    wasAway.current = away;
  }, [away]);
  const size = homeSize();
  const box = size * 1.2; // 둥지는 뭉치보다 조금 넓게
  return (
    <span className="relative inline-block shrink-0" style={{ width: box, height: box }}
      title={away ? AWAY : undefined}
      onMouseEnter={away ? undefined : () => setHi(true)} onMouseLeave={away ? undefined : () => setHi(false)}>
      {/* 둥지 뒤쪽: 엮은 가지 벽 + 안쪽 깔개(뭉치가 보라 배경과 겹치지 않게 뒤를 다 받쳐 준다) */}
      <svg viewBox="0 0 48 48" aria-hidden="true" className="pointer-events-none absolute inset-0 size-full">
        <ellipse cx="24" cy="24" rx="22.5" ry="19.5" className="fill-belly-strong stroke-belly-ink" strokeWidth="0.8" />
        <Twigs list={BACK_TWIGS} />
        <ellipse cx="24" cy="23" rx="17" ry="14" className="fill-belly stroke-belly-ink" strokeWidth="0.6" />
        <ellipse cx="24" cy="21" rx="15.5" ry="11.5" className="fill-none stroke-belly-strong" strokeWidth="2" strokeOpacity="0.45" />
        {away && (
          <g strokeLinecap="round">
            <path d="M15 31 Q20 20 33 22 Q25 31 15 31 Z" className="fill-accent-line stroke-accent-ink" strokeWidth="0.8" />
            <path d="M13 33 L30 23.5" className="fill-none stroke-accent-ink" strokeWidth="0.8" />
          </g>
        )}
      </svg>
      {!away && (
        <span className="absolute" style={{ left: size * 0.1, top: size * 0.2 }}>
          <Character3D mode={hi ? "wave" : "idle"} size={size} label="뭉치 (집에 있어요)" />
        </span>
      )}
      {/* 둥지 앞쪽 테두리: 엮은 가지가 뭉치 아랫부분을 살짝 가린다 */}
      <svg viewBox="0 0 48 48" aria-hidden="true" className="pointer-events-none absolute inset-0 size-full">
        <path d="M1.5 24 C1.5 50 46.5 50 46.5 24 C40 38 8 38 1.5 24 Z" className="fill-belly-strong stroke-belly-ink" strokeWidth="0.8" />
        <Twigs list={FRONT_TWIGS} />
      </svg>
      {away && <span className="sr-only">{AWAY}</span>}
    </span>
  );
}
