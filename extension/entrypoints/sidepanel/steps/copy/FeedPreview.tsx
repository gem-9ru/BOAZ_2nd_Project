/** 인스타그램·페이스북 피드에 뜨는 모양으로 문구를 작게 미리 보기 (사진은 자리만). 본문은 피드처럼 두 줄에서 접힌다. */
export default function FeedPreview({ name, headline, text }: { name: string; headline: string; text: string }) {
  return (
    <div aria-hidden className="overflow-hidden rounded-card border border-line bg-paper">
      <div className="flex items-center gap-2 px-3 py-2">
        <span className="size-6 shrink-0 rounded-badge bg-sunk" />
        <span className="flex flex-col leading-tight">
          <span className="text-caption font-semibold text-ink">{name}</span>
          <span className="text-small text-soft">광고</span>
        </span>
      </div>
      <div className="grid aspect-square w-full place-items-center bg-sunk text-small text-soft">사진 자리</div>
      <div className="flex items-center justify-between gap-2 border-b border-line px-3 py-2">
        <span className="min-w-0 truncate text-caption font-semibold text-ink">{headline || "제목"}</span>
        <span className="shrink-0 rounded-button bg-accent px-2 py-1 text-small font-semibold text-on-accent">더 알아보기</span>
      </div>
      <p className="line-clamp-2 px-3 py-2 text-caption text-ink">
        <span className="font-semibold">{name}</span> {text || "본문"}
      </p>
    </div>
  );
}
