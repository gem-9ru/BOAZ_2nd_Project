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
export interface Change { field_id: string; label: string; new: string; note: string; path?: string; now?: string | null;
  reason?: string; certainty?: { level: "채택" | "유력" | "보류"; label: string; why: string }; grade?: string; meta_says?: string | null; checklist?: string[] }
export type AlertLevel = "block" | "warn" | "info";
export interface Alert { level: AlertLevel; mark: string; kind: string; text: string; todo: string; screen: string; date?: string }
export interface MatrixRow { row: string; stage: string; signal: string; status: "ok" | "blocked" | "watch" | "skip" | "found"; field_id: string | null; path: string; detail: string }
export interface SettingRow { field_id: string; path: string; value: string; kind: "변경" | "유지" | "검토" | "그대로"; note: string }
export interface Matrix { settings?: SettingRow[]; rows: MatrixRow[]; change: Change | null; keep: { field_id: string; path: string; value: string; reason: string }[];
  watch: { field_id: string; path: string; text: string }[]; dont: string[]; tested_field: string | null }
export interface Placement { placement: string; label: string; spend: number; share: number; impressions: number; link_clicks: number; ctr: number | null; ctr_adjusted: number; reference_only: boolean }
export interface BacktestBand { lo: number; hi: number; median: number; actual: number; inside: boolean }
export interface Backtest { ok: boolean; train_days?: string[]; test_day?: string; arms?: { name: string; budget: number; link_clicks: BacktestBand; visits: BacktestBand }[]; note: string }
export interface Result {
  code: string;
  alerts: Alert[];
  blocked: boolean;
  matrix: Matrix;
  backtest: Backtest;
  placements: Placement[];
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
export interface Simulation { budget: number; runs: number; arm: string; impressions: Band; link_clicks: Band; visits: Band; histogram: { lo: number; hi: number; count: number }[]; limits: string;
  tried?: boolean; next_test?: { total: number; per_set_lo: number; per_set_hi: number; share_lo: number; share_hi: number; source: string } }
export interface AssistantReply { message: string; suggestions?: string[]; alerts?: Alert[]; source?: "llm" | "rules" }

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

export const analyzeFile = (file: File, extra: { settingsKey?: string | null; settings?: Record<string, string> } = {}) => {
  const fd = new FormData();
  fd.append("file", file);
  // 세팅값: 확장 프로그램이 넘긴 키(값은 서버에) 또는 직접 답한 5문항
  if (extra.settings && Object.keys(extra.settings).length) fd.append("settings", JSON.stringify(extra.settings));
  else if (extra.settingsKey) fd.append("settings_key", extra.settingsKey);
  return call<Result>("/analysis", { method: "POST", body: fd });
};
export const example = (settingsKey?: string | null) =>
  call<Result>(`/analysis/example${settingsKey ? `?settings_key=${encodeURIComponent(settingsKey)}` : ""}`);
export const simulate = (code: string, arm: string, budget: number, total = 100000) =>
  call<Simulation>("/simulate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code, arm, budget, total }) });
export const askAssistant = (code: string, step: string, question?: string) =>
  call<AssistantReply>("/assistant", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ code, step, question }) });
export const receivedSettings = (key: string) => call<{ count: number }>(`/settings/${encodeURIComponent(key)}`);
