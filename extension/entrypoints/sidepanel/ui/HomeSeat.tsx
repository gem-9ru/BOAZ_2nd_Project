import { useEffect, useRef, useState } from "react";
import { Character3D } from "../../../lib/character3d/Character3D";

function homeSize(): number {
  const v = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--character-home-size"));
  return Number.isFinite(v) ? v : 40;
}

/** 패널 제목 왼쪽 = 뭉치 집. 평소엔 앉아서 숨 쉬고(가리키면 손 흔듦), 광고 관리자에서 안내하는 동안엔 자리가 빈다. */
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
  if (away) {
    return (
      <span title="뭉치가 광고 관리자에서 안내하고 있어요" style={{ width: size, height: size }}
        className="inline-grid shrink-0 place-items-center rounded-badge border-2 border-dashed border-line text-small text-soft">
        <span aria-hidden="true">→</span>
        <span className="sr-only">뭉치가 광고 관리자에서 안내하고 있어요</span>
      </span>
    );
  }
  return (
    <span className="shrink-0" onMouseEnter={() => setHi(true)} onMouseLeave={() => setHi(false)}>
      <Character3D mode={hi ? "wave" : "idle"} size={size} label="뭉치 (집에 있어요)" />
    </span>
  );
}
