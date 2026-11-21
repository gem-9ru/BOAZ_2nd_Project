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
