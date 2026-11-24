import type { Result } from "../api";
import { Card } from "../ui";
import { CertaintyBadge } from "./Certainty";

/** AN-01 확인 + 결론: 첫 화면에 '바꿀 칸 1개'. 중간에 나가도 무엇을 바꿀지는 가져가게 (역피라미드). */
export function AN01({ r, onApply }: { r: Result; onApply: () => void }) {
  const m = r.matrix;
  const c = m.change ?? r.next.change;
  const read = r.check.read;
  return (
    <>
      <Card title="이번에 바꿀 칸">
        <div className="flex flex-col gap-3 rounded-button border-2 border-accent bg-accent-soft px-5 py-4">
          <p className="text-caption font-semibold text-accent-ink">{c.path ?? c.label}</p>
          <p className="text-title font-bold leading-snug">{c.new}</p>
          <div className="flex flex-wrap items-center gap-2">
            {c.certainty && <CertaintyBadge level={c.certainty.level} />}
            {c.grade && <span className="text-caption text-soft">근거 {c.grade} · {c.certainty?.why}</span>}
          </div>
          {c.now && <p className="text-body text-soft">지금 값: {c.now}</p>}
          <p className="text-body">{c.reason ?? c.note}</p>
          <div><button type="button" onClick={onApply} className="h-button rounded-button bg-button px-5 text-body font-semibold text-button-fg hover:bg-button-hover">바로 적용하기</button></div>
        </div>
      </Card>
      <Card title="나머지 칸은 이렇게">
        <ul className="grid gap-3 sm:grid-cols-3">
          <Group title="그대로 두기" items={m.keep.map((k) => `${k.path}: ${k.value}`)} />
          <Group title="지켜보기" items={m.watch.map((w) => w.text)} />
          <Group title="하지 말기" items={m.dont.map((d) => d.split(" — ")[0] ?? d)} />
        </ul>
      </Card>
      <p className="text-caption text-soft">
        파일 확인: {read.days}일 · 광고 세트 {read.adsets}개 · 노출 위치 {read.placement_rows}줄{" "}
        {r.check.totals.every((t) => t.match) ? "· 합계가 맞아요 ✓" : "· 합계가 안 맞아요"}
      </p>
    </>
  );
}

function Group({ title, items }: { title: string; items: string[] }) {
  return (
    <li className="rounded-button bg-bg px-4 py-3">
      <h3 className="mb-2 text-body font-bold">{title}</h3>
      {items.length ? <ul className="flex flex-col gap-1 text-caption">{items.map((t) => <li key={t}>{t}</li>)}</ul> : <p className="text-caption text-soft">없어요</p>}
    </li>
  );
}
