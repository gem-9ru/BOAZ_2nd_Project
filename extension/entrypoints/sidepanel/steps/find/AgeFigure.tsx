import { GENDER_LABEL, genderFrom } from "../../../../lib/settings";

const AGE_ORDER = ["10", "20", "30", "40", "50", "60"];

/** 연령 막대 그림: 가장 눈에 띄게 찾는 연령대 + 성별 비중. */
export default function AgeFigure({ audience: aud, headline }: {
  audience: { female: number; ages: Record<string, number>; top_age: string };
  headline?: string;
}) {
  const gender = genderFrom(aud.female);
  const top = aud.top_age ?? "30";
  const who = `${top}대 ${gender === "all" ? "" : GENDER_LABEL[gender]}`.trim();
  const ages = AGE_ORDER.filter((a) => a in aud.ages);
  const max = Math.max(...ages.map((a) => aud.ages[a] ?? 0)) || 1;

  return (
    <figure className="flex flex-col gap-4 rounded-card border border-line bg-paper p-4">
      <figcaption className="flex items-end justify-between gap-3">
        <span className="flex flex-col gap-0.5">
          <span className="text-caption text-soft">가장 눈에 띄게 찾는 사람</span>
          <strong className="text-number font-bold leading-tight tracking-tight">{who}</strong>
        </span>
        <span className="mb-1 shrink-0 rounded-badge bg-sunk px-2.5 py-1 text-small text-soft">
          여성 {Math.round(aud.female * 100)}% · 남성 {100 - Math.round(aud.female * 100)}%
        </span>
      </figcaption>
      <div className="flex flex-col gap-1.5">
        <div className="flex h-28 items-end gap-2 border-b border-line" role="img"
          aria-label={`연령대별 검색 비중: ${ages.map((a) => `${a}대 ${Math.round((aud.ages[a] ?? 0) * 100)}%`).join(", ")}`}>
          {ages.map((a) => {
            const share = aud.ages[a] ?? 0;
            const isTop = a === top;
            return (
              <div key={a} className="flex h-full flex-1 flex-col items-center justify-end gap-1">
                <span aria-hidden className={`text-small tabular-nums ${isTop ? "font-bold text-accent-ink" : "text-soft"}`}>
                  {Math.round(share * 100)}%
                </span>
                <div aria-hidden
                  className={`w-full max-w-10 rounded-t-md ${isTop ? "bg-accent" : "bg-line"}`}
                  style={{ height: `${Math.max(4, Math.round((share / max) * 76))}px` }} />
              </div>
            );
          })}
        </div>
        <div aria-hidden className="flex gap-2">
          {ages.map((a) => (
            <span key={a} className={`flex-1 text-center text-small ${a === top ? "font-semibold" : "text-soft"}`}>{a}대</span>
          ))}
        </div>
      </div>
      {headline && (
        <p className="rounded-button bg-accent-soft px-3 py-2.5 text-caption leading-relaxed text-ink">{headline}</p>
      )}
    </figure>
  );
}
