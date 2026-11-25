"""결과 파일 읽기 (T02): 엑셀 시트·CSV → columns.yaml로 검사된 표.

- 가상 데이터 엑셀은 1행 한글·2행 영문 머리글. 실제 내보내기 CSV는 화면 이름 머리글 한 줄.
  둘 다 aliases로 영문 열 이름에 맞춘다.
- 비율 열(ratio)은 읽기만 하고 합산하지 않는다 (지표는 metrics에서 다시 계산).
- 메타 리포트 맨 아래 '합계' 행처럼 날짜가 없는 행은 뺀다.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

import pandas as pd

from . import specs

DEMO_XLSX = Path(__file__).resolve().parents[1] / "data" / "demo" / "소연베이크_가상광고데이터.xlsx"


@dataclass
class Table:
    name: str
    df: pd.DataFrame
    missing_optional: List[str] = field(default_factory=list)


@dataclass
class Bundle:
    """한 번에 올린 결과 묶음. tables: 표 이름 → Table, problems: 사장님에게 보여 줄 문제 (고치는 법 포함)."""
    tables: Dict[str, Table] = field(default_factory=dict)
    problems: List[str] = field(default_factory=list)

    def get(self, name: str) -> Optional[pd.DataFrame]:
        t = self.tables.get(name)
        return None if t is None else t.df

    def cases(self) -> List[str]:
        seen = []
        for t in self.tables.values():
            if "case" in t.df:
                for c in t.df["case"].dropna().unique():
                    if c not in seen:
                        seen.append(c)
        return seen

    def modes(self) -> List[str]:
        seen = []
        for t in self.tables.values():
            if "mode" in t.df:
                for m in t.df["mode"].dropna().unique():
                    if m not in seen:
                        seen.append(m)
        return seen

    def select(self, case: Optional[str] = None, mode: Optional[str] = None) -> "Bundle":
        """케이스·구분 하나만 남긴 묶음 (열이 없는 표는 그대로)."""
        out = Bundle(problems=list(self.problems))
        for name, t in self.tables.items():
            df = t.df
            if case is not None and "case" in df:
                df = df[df["case"] == case]
            if mode is not None and "mode" in df:
                df = df[df["mode"] == mode]
            out.tables[name] = Table(name, df.reset_index(drop=True), t.missing_optional)
        return out


def _norm(s: str) -> str:
    return "".join(str(s).split()).lower()


def _rename_map(cols: List[str], table: str) -> Dict[str, str]:
    spec = specs.columns()["tables"][table]["columns"]
    lookup = {}
    for name, c in spec.items():
        for alias in [name] + list(c.get("aliases", [])):
            lookup[_norm(alias)] = name
    return {col: lookup[_norm(col)] for col in cols if _norm(col) in lookup}


def _to_number(s: pd.Series) -> pd.Series:
    if s.dtype == object:
        s = s.astype(str).str.replace(",", "").str.replace("%", "").str.replace("원", "").str.strip()
        s = s.replace({"": None, "-": None, "nan": None, "< 10": "5", "<10": "5"})
    return pd.to_numeric(s, errors="coerce")


def clean(df: pd.DataFrame, table: str, label: str = "") -> (Optional[Table], List[str]):
    """머리글을 맞추고 형식을 검사. → (Table 또는 None, 문제 목록)"""
    spec = specs.columns()["tables"][table]
    title = spec["title"]
    df = df.rename(columns=_rename_map(list(df.columns), table))
    df = df.loc[:, ~df.columns.duplicated()]
    known = [c for c in spec["columns"] if c in df.columns]
    df = df[known].copy()
    missing_req = [c for c, s in spec["columns"].items() if s.get("required") and c not in df.columns]
    if missing_req:
        names = ", ".join(f"'{(spec['columns'][c].get('aliases') or [c])[0]}'" for c in missing_req)
        return None, [f"{label or title}: {names} 열이 없어요. {spec['source']}에서 이 열을 넣어 다시 내보내 주세요."]
    for c in known:
        t = spec["columns"][c]["type"]
        if t == "date":
            df[c] = pd.to_datetime(df[c], errors="coerce", format="mixed")
        elif t in ("int", "float", "ratio"):
            df[c] = _to_number(df[c])
        else:
            df[c] = df[c].astype(str).str.strip().where(df[c].notna())
    problems = []
    if "date" in df.columns:
        bad = df["date"].isna().sum()
        df = df[df["date"].notna()]
        if bad and spec["columns"]["date"].get("required"):
            problems.append(f"{label or title}: 날짜가 없는 행 {bad}개(합계 행 등)는 뺐어요.")
    missing_opt = [c for c, s in spec["columns"].items() if not s.get("required") and not s.get("truth") and c not in df.columns]
    return Table(table, df.reset_index(drop=True), missing_opt), problems


def read_excel(path: Union[str, Path, object]) -> Bundle:
    """가상 데이터 엑셀(또는 같은 시트 이름을 쓴 실제 데이터 엑셀) 한 파일."""
    xl = pd.ExcelFile(path)
    b = Bundle()
    for table, spec in specs.columns()["tables"].items():
        if spec["sheet"] not in xl.sheet_names:
            continue
        raw = xl.parse(spec["sheet"], header=None)
        header_row = _find_header_row(raw, table)
        df = xl.parse(spec["sheet"], header=header_row)
        t, problems = clean(df, table, spec["sheet"])
        b.problems += problems
        if t is not None and len(t.df):
            b.tables[table] = t
    if not b.tables:
        b.problems.append("엑셀에서 읽을 시트를 찾지 못했어요. 시트 이름을 '메타_일별'·'네이버_일별'·'스토어_일별'처럼 맞춰 주세요.")
    return b


def _find_header_row(raw: pd.DataFrame, table: str) -> int:
    """영문·한글 머리글 중 사양과 가장 많이 맞는 행 (처음 5행에서)."""
    best, best_hits = 0, -1
    for i in range(min(5, len(raw))):
        hits = len(_rename_map([str(v) for v in raw.iloc[i].tolist()], table))
        if hits >= best_hits and hits > 0:
            best, best_hits = i, hits
    return best


def guess_table(df: pd.DataFrame) -> Optional[str]:
    """CSV 한 파일이 어느 표인지 머리글로 짐작 (필수 열이 다 맞는 표 중 가장 많이 맞는 것)."""
    best, best_hits = None, 0
    for table, spec in specs.columns()["tables"].items():
        m = _rename_map(list(df.columns), table)
        got = set(m.values())
        req = {c for c, s in spec["columns"].items() if s.get("required")}
        if req <= got and len(got) > best_hits:
            best, best_hits = table, len(got)
    return best


def read_csvs(files: List[object]) -> Bundle:
    """실제 내보내기 CSV 여러 개 (메타·네이버·스토어). 어느 표인지는 머리글로 짐작."""
    b = Bundle()
    for f in files:
        name = getattr(f, "name", str(f))
        try:
            df = _read_any_csv(f)
        except Exception:  # noqa: BLE001
            b.problems.append(f"{name}: 파일을 열지 못했어요. CSV(쉼표 구분)나 엑셀로 내보내 주세요.")
            continue
        table = guess_table(df)
        if table is None:
            b.problems.append(f"{name}: 어떤 리포트인지 알아보지 못했어요. 메타는 '일·광고 세트', 네이버는 '키워드별 일별'로 내보내 주세요.")
            continue
        t, problems = clean(df, table, name)
        b.problems += problems
        if t is not None:
            if "mode" not in t.df:
                t.df["mode"] = "real"
            if table in b.tables:
                b.tables[table].df = pd.concat([b.tables[table].df, t.df], ignore_index=True)
            else:
                b.tables[table] = t
    return b


def _read_any_csv(f) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949"):
        try:
            if hasattr(f, "seek"):
                f.seek(0)
            return pd.read_csv(f, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("encoding")


def demo() -> Bundle:
    return read_excel(DEMO_XLSX)
