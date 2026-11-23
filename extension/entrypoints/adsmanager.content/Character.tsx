import { useEffect, useState } from "react";
import type { GuideView } from "./guideRunner";
import { reveal } from "./locate";

interface Props {
  view: GuideView;
  onDone: () => void;
  onClose: () => void;
}

const SIZE = 64;

/** 광고 관리자 위의 캐릭터 + 말풍선. 대상 칸 둘레에 주황 테두리를 그리고 그 옆으로 걸어간다. */
export function Character({ view, onDone, onClose }: Props) {
  const [rect, setRect] = useState<DOMRect | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setCopied(false);
    if (!view.target) return setRect(null);
    const target = view.target;
    let shown = reveal(target);
    const update = () => {
      if (!shown) shown = reveal(target);   // 아직 그려지지 않았으면 다시 그 구역으로
      const r = target.getBoundingClientRect();
      setRect(shown && r.width > 0 ? r : null);
    };
    update();
    const id = window.setInterval(update, 300);
    return () => window.clearInterval(id);
  }, [view.target, view.index]);

  // 대상이 있으면 그 오른쪽, 없으면 화면 오른쪽 아래 구석.
  const left = rect ? Math.min(rect.right + 16, window.innerWidth - 360) : window.innerWidth - 380;
  const top = rect ? Math.max(rect.top - 8, 16) : window.innerHeight - 260;

  return (
    <>
      {rect && (
        <div
          className="coach-ring"
          style={{ left: rect.left - 6, top: rect.top - 6, width: rect.width + 12, height: rect.height + 12 }}
        />
      )}
      <div className="coach-buddy" style={{ left, top }}>
        <svg width={SIZE} height={SIZE} viewBox="0 0 420 420" aria-hidden="true">
          <ellipse cx="210" cy="250" rx="160" ry="150" fill="#F2994A" />
          <ellipse cx="210" cy="290" rx="100" ry="80" fill="#F7B77A" />
          <circle cx="160" cy="210" r="18" fill="#16213A" />
          <circle cx="260" cy="210" r="18" fill="#16213A" />
          <path d="M190 245 L230 245 L210 272 Z" fill="#A8481A" />
        </svg>
        <div className="coach-bubble" role="status">
          <p className="coach-count">{Math.min(view.index + 1, view.total)} / {view.total}</p>
          <p className="coach-text">{view.text}</p>
          {view.image && !view.found && <img src={browser.runtime.getURL(`/${view.image}` as never)} alt="이 칸이 있는 화면" className="coach-shot" />}
          <div className="coach-actions">
            {view.copy && (
              <button
                type="button"
                onClick={() => navigator.clipboard.writeText(view.copy!).then(() => setCopied(true))}
              >
                {copied ? "복사했어요" : "값 복사"}
              </button>
            )}
            <button type="button" className="coach-primary" onClick={onDone}>했어요</button>
            <button type="button" onClick={onClose} aria-label="안내 닫기">닫기</button>
          </div>
          {view.publish && <p className="coach-note">캐릭터는 게시 버튼을 누르지 않아요.</p>}
        </div>
      </div>
    </>
  );
}
