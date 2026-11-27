import idle from "../assets/mungchi/idle.png";
import point from "../assets/mungchi/point.png";
import run from "../assets/mungchi/run.png";
import walk from "../assets/mungchi/walk.png";
import wave from "../assets/mungchi/wave.png";

/** 뭉치 포즈 5개 (꾸미기안_뭉치: 영상에서 잘라 배경을 지운 PNG). 머리줄 = 가만히 · 업로드 = 손 흔들기 · 결론 = 가리키기 · 보내기 = 뛰기.
 *  장식이라 화면 낭독기에는 읽히지 않는다 (alt=""). 원본 3D 렌더가 생기면 이 파일만 바꾸면 된다. */
const POSE = { idle, wave, point, walk, run } as const;
export type Pose = keyof typeof POSE;

export function Mungchi({ pose, className = "" }: { pose: Pose; className?: string }) {
  return <img src={POSE[pose]} alt="" aria-hidden="true" draggable={false} className={`pointer-events-none select-none mungchi-shadow ${className}`} />;
}
