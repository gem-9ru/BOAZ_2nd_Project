// 서버(localhost:8000) 응답 모양. 서버 server/app.py와 같은 이름을 쓴다.

export interface Research {
  headline: string;
  keywords: { keyword: string; total_qc: number }[];
  audience: { keyword: string; female: number; ages: Record<string, number>; top_age: string } | null;
  fetched: string;
  source: "live" | "cache";
  notice: string | null;
}

export interface Copy {
  primary_text: string;
  headline: string;
}

export interface Field {
  id: string;
  kind: "question" | "precheck";
  label: string;
  ask: string;
  options: string[] | null;
  default: string | null;
  why: string;
}

export interface PresetField {
  id: string;
  label: string;
  default: string;
  why: string;
}

export interface Change {
  field_id: string;
  label: string;
  new: string;
  note: string;
}

export interface Analysis {
  status: "fired" | "hold" | "normal";
  finding: { id: string; title: string; funnel: string; message: string };
  changes: Change[];
  expect: {
    metric: string;
    label: string;
    current: [number, number];
    expected: [number, number];
    prob_better: number | null;
    grade: "checked" | "hypothesis";
  } | null;
  charts: {
    funnel: { impressions: number; link_clicks: number; landing_page_views: number };
    daily: { date: string; ctr: number | null; cpm: number | null; spend: number }[];
    placement: { placement: string; spend: number; link_clicks: number }[];
  };
  ab: { a: string; b: string; prob_b_better: number } | null;
}

export const BASE = "http://localhost:8000";

/** 서버가 꺼져 있거나 닿지 않음. */
export class ServerDown extends Error {
  constructor() {
    super("도우미 서버에 연결할 수 없어요. 서버를 켠 뒤 다시 시도해 주세요.");
  }
}

/** 서버가 입력을 거절함 (message는 사장님께 그대로 보여 줘도 되는 문장). */
export class BadInput extends Error {}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, init);
  } catch {
    throw new ServerDown();
  }
  const body = await res.json().catch(() => ({}));
  if (res.status === 400) throw new BadInput(body.error ?? "입력을 확인해 주세요.");
  if (!res.ok) throw new ServerDown();
  return body as T;
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export function research(product: string, seeds?: string[]): Promise<Research> {
  return call("/research", json(seeds ? { product, seeds } : { product }));
}

export function copies(body: { product: string; strengths: string[]; keywords: string[] }): Promise<{ copies: Copy[]; source: string }> {
  return call("/copies", json(body));
}

export function fields(): Promise<{ fields: Field[]; defaults: PresetField[] }> {
  return call("/fields");
}

export function analyze(file: File): Promise<Analysis> {
  const form = new FormData();
  form.append("file", file);
  return call("/analyze", { method: "POST", body: form });
}
