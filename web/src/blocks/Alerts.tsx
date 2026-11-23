import type { Result } from "../api";
import { Banner } from "../ui";

/** 2 게재 이상 알림 (있을 때만): 결과를 믿을 수 있는지에 영향을 주므로 결론보다 위. */
export function Alerts({ c }: { c: Result["check"] }) {
  if (c.warnings.length === 0) return null;
  return (
    <section id="alerts" aria-labelledby="alerts-title" className="flex flex-col gap-2">
      <h2 id="alerts-title" className="text-body font-bold text-warn"><span className="text-caption text-soft mr-2">2</span>게재 이상 알림</h2>
      {c.warnings.map((w) => <Banner key={w.text}>{w.text}</Banner>)}
    </section>
  );
}
