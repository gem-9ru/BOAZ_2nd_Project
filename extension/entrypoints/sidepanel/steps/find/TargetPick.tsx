import { useState } from "react";
import type { Target } from "../../../../lib/flow";
import { ageGroupToRange } from "../../../../lib/settings";

const GROUPS = ["10", "20", "30", "40", "50", "60"];
export const GENDER_WORD: Record<Target["gender"], string> = { female: "여성만", male: "남성만", all: "남녀 모두" };

/** 나이대 묶음 + 성별 → 광고 관리자에 넣을 타깃 (10대는 18세부터, 60대는 65세 이상까지). */
export function toTarget(from: string, to: string, gender: Target["gender"]): Target {
  return { ageMin: ageGroupToRange(from).ageMin, ageMax: ageGroupToRange(to).ageMax, gender };
}

/** '30–59세 · 여성만' (65세는 '65세 이상') */
export function targetLine(t: Target): string {
  const max = t.ageMax >= 65 ? "65세 이상" : `${t.ageMax}세`;
  return `${t.ageMin}–${max} · ${GENDER_WORD[t.gender]}`;
}

/** 추천 타깃을 보여 주고 [나이·성별 바꾸기]로 나이대(부터~까지)와 성별(여성만·남성만·모두)을 고친다. 고른 성별이 찾는 사람 중 몇 %인지도. */
export default function TargetPick({ from, to, gender, rec, female, onChange }: {
  from: string; to: string; gender: Target["gender"];
  rec: { from: string; to: string; gender: Target["gender"] };
  female: number;
  onChange: (v: { from: string; to: string; gender: Target["gender"] }) => void;
}) {
  const [open, setOpen] = useState(false);
  const changed = from !== rec.from || to !== rec.to || gender !== rec.gender;
  const pct = { female: Math.round(female * 100), male: 100 - Math.round(female * 100), all: 100 };
  return (
    <div className="flex flex-col gap-3 rounded-card border border-line bg-paper p-4">
      <div className="flex items-center justify-between gap-3">
        <p className="text-body">
          <span className="font-semibold">{targetLine(toTarget(from, to, gender))}</span>
          <span className="ml-1.5 text-small text-soft">{changed ? "직접 고침" : "추천"}</span>
        </p>
        <button type="button" aria-expanded={open} onClick={() => setOpen((v) => !v)}
          className="shrink-0 rounded-button border border-line bg-paper px-3 py-1 text-caption font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          {open ? "닫기" : "나이·성별 바꾸기"}
        </button>
      </div>
      {open && (
        <div className="flex flex-col gap-3">
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-caption font-semibold text-soft">나이</legend>
            <div className="flex items-center gap-2 text-body">
              <select aria-label="나이 부터" value={from}
                onChange={(e) => { const f = e.target.value; onChange({ from: f, to: Number(to) < Number(f) ? f : to, gender }); }}
                className="rounded-button border border-field-line bg-paper px-2 py-1.5 text-body">
                {GROUPS.map((g) => <option key={g} value={g}>{g}대</option>)}
              </select>
              <span>부터</span>
              <select aria-label="나이 까지" value={to}
                onChange={(e) => { const t = e.target.value; onChange({ from: Number(from) > Number(t) ? t : from, to: t, gender }); }}
                className="rounded-button border border-field-line bg-paper px-2 py-1.5 text-body">
                {GROUPS.map((g) => <option key={g} value={g}>{g}대</option>)}
              </select>
              <span>까지</span>
            </div>
          </fieldset>
          <fieldset className="flex flex-col gap-2">
            <legend className="mb-2 text-caption font-semibold text-soft">성별</legend>
            <div className="flex flex-wrap gap-2">
              {(["female", "male", "all"] as const).map((g) => (
                <label key={g}
                  className={`cursor-pointer rounded-badge border px-3 py-1.5 text-label has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${
                    gender === g ? "border-accent bg-accent font-semibold text-on-accent" : "border-line"}`}>
                  <input type="radio" name="target-gender" value={g} checked={gender === g}
                    onChange={() => onChange({ from, to, gender: g })} className="sr-only" />
                  {GENDER_WORD[g]} <span className="font-normal">(찾는 사람의 {pct[g]}%)</span>
                </label>
              ))}
            </div>
            {gender !== "all" && <p className="text-small text-soft">{gender === "female" ? "남성" : "여성"} {pct[gender === "female" ? "male" : "female"]}%에게는 광고가 안 보여요.</p>}
          </fieldset>
          {changed && (
            <button type="button" onClick={() => onChange(rec)} className="self-start text-caption text-soft underline">추천대로 되돌리기</button>
          )}
        </div>
      )}
    </div>
  );
}
