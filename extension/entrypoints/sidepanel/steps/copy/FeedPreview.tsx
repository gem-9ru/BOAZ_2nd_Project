/** 메타 권장 길이: 제목 27자, 기본 문구 50~150자 — 메타 광고 가이드 '이미지 · 페이스북 피드 · 트래픽' 텍스트 권장 사항 (2026-11-26 확인). 권장일 뿐, 넘는다고 잘린다는 말은 문서에 없음 */
export const HEAD_REC = 27;
export const TEXT_REC_MIN = 50;

export type PreviewKind = "ig" | "fb" | "story";
export const PREVIEW_LABEL: Record<PreviewKind, string> = { ig: "인스타 피드", fb: "페이스북 피드", story: "스토리" };

/** 광고가 뜨는 자리마다 문구가 보이는 모양을 작게 미리 보기 (사진은 내 사진 또는 자리만).
 *  - 인스타 피드: 사진 → [더 알아보기] 막대 → '가게 이름 본문' 두 줄 (메타 가이드 권장: 제목 40자·본문 125자, 제목이 어디 보이는지는 확인 못 함)
 *  - 페이스북 피드: 본문 → 사진 → 제목 + [더 알아보기]
 *  - 스토리: 세로 화면 가득 사진, 아래에 본문과 [더 알아보기] (메타 가이드: 9:16, 위 14%·아래 35% 비우기. 본문 한 줄 자르기는 확인 못 한 그림일 뿐) */
export default function FeedPreview({ name, headline, text, photo, kind = "fb" }: {
  name: string; headline: string; text: string; photo?: string | null; kind?: PreviewKind;
}) {
  const head = (
    <div className="flex items-center gap-2 px-3 py-2">
      <span className="size-6 shrink-0 rounded-badge bg-sunk" />
      <span className="flex flex-col leading-tight">
        <span className="text-caption font-semibold text-ink">{name}</span>
        <span className="text-small text-soft">광고</span>
      </span>
    </div>
  );
  const picture = (ratio: string) => photo
    ? <img src={photo} alt="" className={`${ratio} w-full object-cover`} />
    : <div className={`grid ${ratio} w-full place-items-center bg-sunk text-small text-soft`}>사진 자리</div>;
  const cta = <span className="shrink-0 rounded-button bg-accent px-2 py-1 text-small font-semibold text-on-accent">더 알아보기</span>;

  if (kind === "story") {
    return (
      <div aria-hidden className="mx-auto w-1/2 min-w-36 overflow-hidden rounded-card border border-line bg-paper">
        {head}
        {picture("aspect-[9/16]")}
        <div className="flex flex-col gap-1.5 px-3 py-2">
          <p className="line-clamp-1 text-small text-ink">{text || "본문"}</p>
          <span className="self-center">{cta}</span>
        </div>
      </div>
    );
  }
  if (kind === "ig") {
    return (
      <div aria-hidden className="overflow-hidden rounded-card border border-line bg-paper">
        {head}
        {picture("aspect-square")}
        <div className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
          <span className="text-caption font-semibold text-ink">더 알아보기</span>
          <span className="text-caption text-soft">›</span>
        </div>
        <p className="line-clamp-2 px-3 py-2 text-caption text-ink">
          <span className="font-semibold">{name}</span> {text || "본문"}
        </p>
      </div>
    );
  }
  return (
    <div aria-hidden className="overflow-hidden rounded-card border border-line bg-paper">
      {head}
      <p className="line-clamp-3 px-3 pb-2 text-caption text-ink">{text || "본문"}</p>
      {picture("aspect-square")}
      <div className="flex items-center justify-between gap-2 px-3 py-2">
        <span className="min-w-0 truncate text-caption font-semibold text-ink">{headline || "제목"}</span>
        {cta}
      </div>
    </div>
  );
}
