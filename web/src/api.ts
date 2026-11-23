// 서버(server/app.py)의 /analysis·/simulate 응답 모양. 같은 서버가 이 페이지를 띄우므로 주소는 같은 출처.
export interface Arm {
  name: string; spend: number; impressions: number; link_clicks: number; landing_page_views: number;
  cpm: number | null; ctr: number | null; cpc: number | null; click_to_visit: number | null; visits_per_1000won: number | null;
}
export type Word = "확실해요" | "A 쪽이에요" | "B 쪽이에요" | "아직 몰라요";
export interface Metric { key: string; label: string; higher_is_better: boolean; prob_b_better: number; a_interval: [number, number]; b_interval: [number, number]; overlap: boolean; better: "A" | "B"; word: Word }
export interface Verdict {
  a: string; b: string; metrics: Metric[];
  badge: { metric: string; label: string; better: "A" | "B"; prob: number; level: "채택" | "유력" | "보류"; word: Word };
  min_budget: { per_group: number | null; total: number | null; lift: number; confidence: number; power: number | null };
}
export interface Stage { key: string; label: string; count: number; rate?: number; range?: [number, number]; per100?: string; unknown?: boolean }
export interface Change { field_id: string; label: string; new: string; note: string }
export interface Result {
  code: string;
  check: { ok: boolean; read: { days: number; adsets: number; daily_rows: number; placement_rows: number };
    totals: { metric: string; daily: number; placement: number; match: boolean }[];
    warnings: { kind: string; text: string; date?: string }[]; safety: { ok: boolean; text: string }[]; missing: string[] };
  funnel: { arms: { name: string; stages: Stage[] }[]; hint: string | null };
  summary: { arms: Arm[]; placements: { placement: string; label: string; spend: number; share: number }[] };
  verdict: Verdict | null;
  replay: { date: string; prob: number }[];
  diagnosis: { status: string; finding: { title: string; message: string } };
  next: { action: string; change: Change; summary: string[] };
}
export interface Band { median: number; lo: number; hi: number }
export interface Simulation { budget: number; runs: number; arm: string; impressions: Band; link_clicks: Band; visits: Band; histogram: { lo: number; hi: number; count: number }[]; limits: string }

async function call<T>(url: string, init?: RequestInit): Promise<T> {
  let r: Response;
  try {
    r = await fetch(url, init);
  } catch {
    throw new Error("분석 서버에 연결하지 못했어요. 서버를 켠 뒤 다시 시도해 주세요.");
  }
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error ?? body.detail ?? "서버에서 문제가 생겼어요. 잠시 뒤 다시 시도해 주세요.");
  return body as T;
}

export const analyzeFile = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return call<Result>("/analysis", { method: "POST", body: fd });
};
export const example = () => call<Result>("/analysis/example");
export const simulate = (code: string, arm: string, budget: number) =>
  call<Simulation>("/simulate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code, arm, budget }) });
