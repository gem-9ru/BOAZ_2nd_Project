import { useState } from "react";
import type { Category } from "../../../../lib/api";

/** 쇼핑인사이트 큰 분야 12개 (서버가 categories를 안 줄 때 씀) */
export const CATEGORIES: Category[] = [
  { code: "50000000", name: "패션의류" }, { code: "50000001", name: "패션잡화" },
  { code: "50000002", name: "화장품/미용" }, { code: "50000003", name: "디지털/가전" },
  { code: "50000004", name: "가구/인테리어" }, { code: "50000005", name: "출산/육아" },
  { code: "50000006", name: "식품" }, { code: "50000007", name: "스포츠/레저" },
  { code: "50000008", name: "생활/건강" }, { code: "50000009", name: "여가/생활편의" },
  { code: "50000010", name: "면세점" }, { code: "50005542", name: "도서" },
];

/** 분야 라디오 12개 (칩 모양). */
export function CategoryRadios({ categories, value, onPick }: {
  categories?: Category[]; value?: string; onPick: (code: string) => void;
}) {
  const list = categories?.length ? categories : CATEGORIES;
  return (
    <div role="radiogroup" aria-label="분야" className="flex flex-wrap gap-2">
      {list.map((c) => (
        <label key={c.code}
          className={`inline-flex min-h-11 items-center cursor-pointer rounded-badge border px-3 py-1.5 text-caption has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-accent ${
            value === c.code ? "border-accent bg-accent font-semibold text-on-accent" : "border-line bg-paper"}`}>
          <input type="radio" name="category" value={c.code} checked={value === c.code}
            onChange={() => onPick(c.code)} className="sr-only" />
          {c.name}
        </label>
      ))}
    </div>
  );
}

/** 분야를 못 정했을 때: 후보가 있으면 "이 중 어디에 가까워요?"로 먼저 보이고, [다른 분야]로 12개를 펼친다. */
export function CategoryAsk({ categories, candidates, value, onPick }: {
  categories?: Category[]; candidates?: Category[]; value?: string; onPick: (code: string) => void;
}) {
  const [all, setAll] = useState(false);
  if (!candidates?.length || all) return <CategoryRadios categories={categories} value={value} onPick={onPick} />;
  return (
    <div className="flex flex-col gap-2.5">
      <p className="text-caption">이 중 어디에 가까워요?</p>
      <CategoryRadios categories={candidates} value={value} onPick={onPick} />
      <button type="button" onClick={() => setAll(true)}
        className="self-start rounded-button border border-line bg-paper min-h-11 px-3 py-1 text-caption font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
        다른 분야
      </button>
    </div>
  );
}

/** 1) 분야 줄: "'수제 쿠키'는 '식품'(으)로 볼게요. 맞나요?" + [바꾸기] → 12개 라디오. */
export default function CategoryPick({ product, category, categories, candidates, onPick }: {
  product: string;
  category: Category & { guessed: boolean };
  categories?: Category[];
  /** 가까운 다른 분야 (서버가 추정할 때 함께 본 것). 있으면 [바꾸기]에서 이것부터, 나머지는 '다른 분야' */
  candidates?: Category[];
  onPick: (code: string) => void;
}) {
  const near = (candidates ?? []).filter((c) => c.code !== category.code);
  const [open, setOpen] = useState(false);
  return (
    <div className="flex flex-col gap-2.5">
      <span className="text-caption font-semibold text-soft">분야</span>
      <div className="flex items-center justify-between gap-3 rounded-button bg-sunk px-3 py-2">
        <p className="text-caption">
          '{product}'는 '{category.name}'(으)로 볼게요.{category.guessed ? " 맞나요?" : ""}
        </p>
        <button type="button" aria-expanded={open} onClick={() => setOpen((v) => !v)}
          className="shrink-0 rounded-button border border-line bg-paper min-h-11 px-3 py-1 text-caption font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent">
          바꾸기
        </button>
      </div>
      {open && (near.length
        ? <CategoryAsk categories={categories} candidates={[{ code: category.code, name: category.name }, ...near]} value={category.code} onPick={onPick} />
        : <CategoryRadios categories={categories} value={category.code} onPick={onPick} />)}
    </div>
  );
}
