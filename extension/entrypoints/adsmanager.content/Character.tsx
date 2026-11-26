import { useEffect, useRef, useState } from "react";
import { Character3D } from "../../lib/character3d/Character3D";
import { bubbleSpot, gaitFor, handPoint, headingYaw, home, pointAngle, standSpot, travelAt, type Mode, type Point, type Side } from "../../lib/character3d/motion";
import { groupOf } from "../../lib/guide";
import type { GuideView } from "./guideRunner";
import { isChoice, reveal } from "./locate";

interface Props {
  view: GuideView;
  onDone: () => void;
  onBack: () => void;
  onClose: () => void;
  onToggleAuto?: () => void;
  /** EX-03 다음 테스트의 바꿀 칸: 이 칸만 밝게 두고 나머지 화면은 흐리게, '나머지 칸은 그대로(유지)' 표시 */
  keepOthers?: boolean;
  /** 뭉치가 칸 옆에 도착해 가리키면 그 칸, 다시 걷기 시작하면 null (자동 진행은 도착한 뒤에 누르고 넣는다) */
  onArrive?: (el: HTMLElement | null) => void;
}

const BUBBLE_GAP = 4;
const RAMP_WALK = 0.35;   // 최고 속도까지 걸리는 시간(초)
const RAMP_RUN = 0.5;

/** 짚을 영역: 작은 고르는 칸은 이름표(aria-labelledby·label)까지 합쳐서 테두리와 뭉치가 글자를 가리지 않게. */
function targetBox(el: HTMLElement): DOMRect {
  const r = el.getBoundingClientRect();
  if (!isChoice(el)) return r;
  const ids = (el.getAttribute("aria-labelledby") ?? "").split(/\s+/).filter(Boolean);
  const labels = [...ids.map((id) => el.ownerDocument.getElementById(id)), ...((el as HTMLInputElement).labels ?? [])]
    .filter((x): x is HTMLElement => Boolean(x))
    .map((x) => x.getBoundingClientRect())
    .filter((b) => b.width > 0 && Math.abs(b.top + b.height / 2 - (r.top + r.height / 2)) < 60);   // 같은 줄의 이름표만
  if (!labels.length) return r;
  const left = Math.min(r.left, ...labels.map((b) => b.left)), top = Math.min(r.top, ...labels.map((b) => b.top));
  const right = Math.max(r.right, ...labels.map((b) => b.right)), bottom = Math.max(r.bottom, ...labels.map((b) => b.bottom));
  return { left, top, right, bottom, width: right - left, height: bottom - top, x: left, y: top, toJSON: () => ({}) } as DOMRect;
}

function num(el: Element | null, name: string, fallback: number): number {
  const v = el ? parseFloat(getComputedStyle(el).getPropertyValue(name)) : NaN;
  return Number.isFinite(v) ? v : fallback;
}

/** 광고 관리자 위의 뭉치(3D) + 말풍선.
 *  집(화면 오른쪽 위, 사이드 패널 쪽)에서 걸어 나와 칸 옆까지 걷거나(가까우면) 뛰어가서(멀면) 팔로 가리킨다.
 *  닫으면 집으로 돌아간 뒤 사라진다. 크기·속도·색은 design-system 토큰(--character-*). */
export function Character({ view, onDone, onBack, onClose, onToggleAuto, onArrive, keepOthers }: Props) {
  const [rect, setRect] = useState<DOMRect | null>(null);
  const rectFor = useRef<HTMLElement | null>(null);   // rect가 어느 칸의 상자인지
  const host = useRef<HTMLDivElement>(null);
  const size = num(host.current, "--character-size", 120);
  const vp = () => ({ width: window.innerWidth, height: window.innerHeight });
  const [pos, setPos] = useState<Point>(() => home(vp(), size));
  const [mode, setMode] = useState<Mode>("idle");
  const [move, setMove] = useState<{ heading: number; speed: number; full: number } | undefined>();
  const [point, setPoint] = useState<{ side: Side; angle: number } | undefined>();
  const [leaving, setLeaving] = useState(false);
  const posRef = useRef(pos);
  posRef.current = pos;

  useEffect(() => {
    if (!view.target) return setRect(null);
    const target = view.target;
    let shown = reveal(target);
    const update = () => {
      // 아직 그려지지 않았거나, 사용자가 스크롤해 메타가 다시 지웠으면 그 구역으로 다시 간다
      if (target.getClientRects().length === 0) shown = false;
      if (!shown) shown = reveal(target);
      const r = targetBox(target);
      rectFor.current = target;
      setRect(shown && r.width > 0 ? r : null);
    };
    update();
    const id = window.setInterval(update, 300);
    return () => window.clearInterval(id);
  }, [view.target, view.index]);

  // 갈 곳: 나갈 땐 집, 칸이 있으면 칸 옆, 못 찾았으면 화면 오른쪽 아래 (말풍선의 대신 그림 옆)
  const spot = leaving ? { ...home(vp(), size), side: "right" as Side }
    : rect ? standSpot(rect, vp(), size)
    : { x: window.innerWidth - size - 400, y: window.innerHeight - size - 220, side: "right" as Side };
  const key = `${Math.round(spot.x)},${Math.round(spot.y)},${leaving}`;

  useEffect(() => {
    const speeds = {
      walk: num(host.current, "--character-walk-speed", 260),
      run: num(host.current, "--character-run-speed", 620),
      runDistance: num(host.current, "--character-run-distance", 420),
    };
    const from = posRef.current;
    const dx = spot.x - from.x, dy = spot.y - from.y;
    const dist = Math.hypot(dx, dy);
    const arrive = () => {
      if (leaving) return onClose();
      if (rect) {
        setMode("point");
        setPoint({ side: spot.side, angle: pointAngle(handPoint(spot, size, spot.side), { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 }) });
      } else {
        setMode("wave");
        setPoint(undefined);
      }
      setMove(undefined);
    };
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
    if (dist < 2 || reduce) {
      setPos({ x: spot.x, y: spot.y });
      arrive();
      return;
    }
    const gait = gaitFor(dist, speeds);
    const speed = gait === "run" ? speeds.run : speeds.walk;
    setMode(gait);
    // 상하좌우·대각선 모두: 가는 방향으로 몸을 돌리고(아래 = 정면, 위 = 등), 천천히 출발해 천천히 멈춘다
    const heading = headingYaw(dx, dy);
    const ramp = gait === "run" ? RAMP_RUN : RAMP_WALK;
    setMove({ heading, speed: 0, full: speed });
    const start = performance.now();
    let raf = 0;
    const step = (now: number) => {
      const { d, v, done } = travelAt((now - start) / 1000, dist, speed, ramp);
      const k = d / dist;
      setPos({ x: from.x + dx * k, y: from.y + dy * k });
      setMove({ heading, speed: v, full: speed });
      if (!done) raf = requestAnimationFrame(step);
      else arrive();
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [key]);

  // 사장님 차례로 기다리는 중이면 가리키기 대신 손을 흔들며 기다린다 (테두리가 칸을 보여 준다). 뭉치가 다시 할 차례면 가리키기
  const waitOwner = view.waiting === "owner";
  useEffect(() => {
    if (mode === "point" && waitOwner) setMode("wave");
    else if (mode === "wave" && !waitOwner && rect) setMode("point");
  }, [mode, waitOwner, rect !== null]);

  // 도착 신호: 지금 칸 옆에 서서 가리키는 중일 때만 그 칸을 알린다 (걷는 중·다른 칸 상자면 null)
  useEffect(() => {
    const here = mode === "point" && rect && view.target && rectFor.current === view.target ? view.target : null;
    onArrive?.(here);
  }, [mode, view.target, rect !== null]);

  // 말풍선: 가리키는 칸을 덮지 않는 자리 (오른쪽 → 왼쪽 → 아래 → 위)
  const bubbleEl = useRef<HTMLDivElement>(null);
  const bubble = { width: num(host.current, "--coach-width", 340), height: bubbleEl.current?.offsetHeight || 170 };
  const b = bubbleSpot(pos, size, bubble, vp(), rect, BUBBLE_GAP);
  const bubbleLeft = b.x, bubbleTop = b.y;
  const moving = mode === "walk" || mode === "run";
  // 첫 칸에서 아직 자동 진행을 안 켰으면: [자동 진행] 안내 한 줄 + 단추 강조 (2026-11-26 사용자: 처음엔 멈춘 채 시작)
  // 사장님이 직접 할 차례 (사장님 칸·뭉치가 못 해서 기다림·게시): 꼬리표·테두리·주 버튼을 크게 (2026-11-26 사용자)
  const publishTurn = view.waiting === "publish" || Boolean(view.publish);
  const ownerTurn = Boolean(view.owner) || view.waiting === "owner" || publishTurn;
  const firstAsk = Boolean(onToggleAuto) && view.index === 0 && !view.auto && view.waiting !== "publish";

  return (
    <div ref={host} className="coach-host">
      {rect && !leaving && (
        <div
          className={keepOthers ? "coach-ring coach-ring-focus" : "coach-ring"}
          style={{ left: rect.left - 6, top: rect.top - 6, width: rect.width + 12, height: rect.height + 12 }}
        />
      )}
      {rect && !leaving && keepOthers && (
        // 테두리 오른쪽 위: 메타 칸 이름표는 왼쪽 위에 있어서 그쪽에 두면 이름표를 덮는다 (2026-11-26 실제 화면 확인)
        <p className="coach-keep" style={{ right: window.innerWidth - (rect.right + 6), top: Math.max(4, rect.top - 28) }}>
          이 칸만 바꿔요 · 나머지 칸은 그대로 (유지)
        </p>
      )}
      <div className="coach-mungchi" style={{ left: pos.x, top: pos.y, width: size, height: size }} data-mode={mode}>
        <Character3D mode={mode} size={size} move={move} point={point} label="광고 어시스턴트 뭉치" />
      </div>
      {!leaving && (
        <div ref={bubbleEl} className="coach-bubble-wrap" style={{ left: bubbleLeft, top: bubbleTop, opacity: moving ? "var(--coach-moving-opacity)" : 1 }}>
          <div className={ownerTurn ? "coach-bubble coach-bubble-owner" : "coach-bubble"}>
            {/* 화면 읽기: 바뀌는 안내만 알림 영역 (단추까지 넣으면 0.5초마다 다시 읽힐 수 있다) */}
            {/* 꾸미기안_뭉치: 맨 위 칩('1 / 14 · 캠페인') + ✕ 닫기 */}
            <div className="coach-hd">
              <p className="coach-count">{Math.min(view.index + 1, view.total)} / {view.total}{groupOf(view.id) ? ` · ${groupOf(view.id)}` : ""}</p>
              <button type="button" className="coach-close" onClick={() => setLeaving(true)} aria-label="안내 닫기">✕</button>
            </div>
            <div role="status">
              {ownerTurn && <p className="coach-owner"><strong>직접</strong> {publishTurn ? "게시해 주세요" : "눌러 주세요"}</p>}
              <p className="coach-text">{markDirect(view.text)}</p>
            </div>
            {view.image && !view.found && <img src={browser.runtime.getURL(`/${view.image}` as never)} alt="이 칸이 있는 화면" className="coach-shot" />}
            {view.total > 1 && view.total <= 30 && (
              <div className="coach-dots" aria-hidden="true">
                {Array.from({ length: view.total }, (_, i) => <i key={i} className={i <= view.index ? "on" : undefined} />)}
              </div>
            )}
            <div className="coach-actions">
              <button type="button" className="coach-ghost" onClick={onBack} disabled={view.index === 0} aria-label="이전 칸">◀</button>
              {/* [다음 칸]: 페이지에서 대신 고르기·넣기·누르기 (게시는 안 함). 직접 맞출 칸에선 [다 했어요].
                  게시 칸에선 [게시했어요]: 사장님이 직접 게시한 뒤 누르면 다음으로 (뭉치는 게시 버튼을 누르지 않음) */}
              <button type="button" className={ownerTurn ? "coach-primary coach-primary-owner" : "coach-primary"} onClick={onDone}>
                {publishTurn ? "게시했어요" : view.waiting === "owner" ? "다 했어요" : "다음 칸"}
              </button>
              {onToggleAuto && view.waiting !== "publish" && (
                <button type="button" onClick={onToggleAuto} aria-pressed={Boolean(view.auto)} className={firstAsk ? "coach-ghost coach-attn" : "coach-ghost"}>{view.auto ? "잠깐 멈추기" : "자동 진행"}</button>
              )}
            </div>
            {firstAsk && <p className="coach-note">[자동 진행]을 누르면 뭉치가 칸을 차례로 채워요. 게시는 하지 않아요.</p>}
            {view.publish && <p className="coach-note">캐릭터는 게시 버튼을 누르지 않아요.</p>}
            {keepOthers && <p className="coach-note">흐리게 보이는 나머지 칸은 지난번 그대로 두세요. 두 세트가 이 칸 하나만 달라야 비교할 수 있어요.</p>}
          </div>
        </div>
      )}
    </div>
  );
}

/** 말풍선 글 속 '직접'을 굵은 꼬리표로 (사장님이 해야 하는 일이 한눈에 보이게) */
/** '직접'은 보라 꼬리표, 작은따옴표로 싼 값('트래픽')은 배 색 밑줄 (꾸미기안_뭉치 .card .tx b) */
function markDirect(text: string) {
  return text.split(/(직접|'[^']{1,40}')/).map((part, i) => (part === "직접" ? <strong key={i} className="coach-direct">직접</strong>
    : /^'.+'$/.test(part) ? <b key={i} className="coach-val">{part}</b> : part));
}
