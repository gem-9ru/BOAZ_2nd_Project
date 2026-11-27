"""희수 실험 정리 엑셀 → 분석 서버가 읽는 세로형 CSV (오븐로그 정리본과 같은 모양).

사용: .venv/bin/python scripts/heesu_example.py ~/Downloads/트래픽_메타AB_20261117-20261120.xlsx
출력: server/data/demo/모닝빈_메타AB_20261117-20261120.csv

- '노출 위치' 시트 → 3_노출위치 (세트 × 노출 위치 기간 합계: 지출·노출·도달·링크 클릭·랜딩 페이지 조회)
- '일자별(부록)' 시트 → 5_부록_일자별 (지출·노출·도달·링크 클릭)
- 원본 일자별에 랜딩 페이지 조회가 없다 → 세트의 기간 합계(노출 위치 시트)를 그날 링크 클릭 비율로 나눠 넣는다
  (기간 합계는 원본과 같음, 날짜별 숫자만 추정 · 6_한계에 적음)
- 세트 이름: 비교한 칸이 화면에 보이게 'A_어드밴티지노출위치·자동타겟' / 'B_수동노출위치·연령20~39' (원본: 타깃과 노출 위치를 함께 바꾼 묶음 비교)
"""
import csv
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "server" / "data" / "demo" / "모닝빈_메타AB_20261117-20261120.csv"
NAMES = {"A": "A_어드밴티지노출위치·자동타겟 (메타 기본: 어드밴티지+ 타겟·노출 위치)",
         "B": "B_수동노출위치·연령20~39 (우리 설정: 20~39세·노출 위치 직접)"}
PLATFORM = {"Instagram": "instagram", "Facebook": "facebook"}


def _sheet(xlsx: Path, name: str) -> pd.DataFrame:
    raw = pd.read_excel(xlsx, sheet_name=name, header=None)
    head = next(i for i, r in raw.iterrows() if r.astype(str).str.contains("광고 세트").any())
    df = raw.iloc[head + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[head]]
    df = df.dropna(subset=["광고 세트"])
    return df[df["광고 세트"].astype(str).str.match(r"^[AB] ") & pd.to_numeric(df["지출(원)"], errors="coerce").notna()]   # 세트 줄만 (합계·메모 줄 뺌)


def _arm(label: str) -> str:
    return "A" if str(label).strip().startswith("A") else "B"


def _split(total: int, weights: list) -> list:
    """total을 weights 비율로 정수로 나눔 (합이 total과 같게, 큰 나머지부터 1씩)."""
    s = sum(weights)
    if not s:
        return [0] * len(weights)
    raw = [total * w / s for w in weights]
    out = [int(x) for x in raw]
    for i in sorted(range(len(raw)), key=lambda i: raw[i] - out[i], reverse=True)[: total - sum(out)]:
        out[i] += 1
    return out


def convert(xlsx: Path) -> list:
    place = _sheet(xlsx, "노출 위치")
    daily = _sheet(xlsx, "일자별(부록)")
    rows = [["section", "ad_set", "date", "platform", "position", "metric", "value", "note"],
            ["0_설정", "", "", "", "", "원본", "모닝빈 실험 정리 엑셀 (트래픽_메타AB_20261117-20261120.xlsx)", ""],
            ["0_설정", "", "", "", "", "비교 방식", "메타 기본 세팅 vs 우리가 정한 세팅 묶음 비교 (타깃과 노출 위치가 함께 다름)", ""],
            ["0_설정", "", "", "", "", "예산", "캠페인별 총예산 ₩5,400 (합계 ₩10,800)", ""]]
    period = "2026-11-17~2026-11-20"
    lpv_total = {}
    for _, r in place.iterrows():
        arm = _arm(r["광고 세트"])
        lpv_total[arm] = lpv_total.get(arm, 0) + int(r["랜딩 조회"])
        for metric, col in (("지출(원)", "지출(원)"), ("노출", "노출"), ("도달", "도달"), ("링크 클릭", "링크 클릭"), ("랜딩 페이지 조회", "랜딩 조회")):
            rows.append(["3_노출위치", NAMES[arm], period, PLATFORM.get(str(r["플랫폼"]), str(r["플랫폼"]).lower()), str(r["노출 위치"]), metric, int(r[col]), ""])
    for arm in ("A", "B"):
        mine = daily[daily["광고 세트"].map(_arm) == arm]
        lpv = _split(lpv_total.get(arm, 0), [int(c) for c in mine["링크 클릭"]])
        for (_, r), v in zip(mine.iterrows(), lpv):
            date = pd.Timestamp(r["날짜"]).strftime("%Y-%m-%d")
            for metric, col in (("지출(원)", "지출(원)"), ("노출", "노출"), ("도달", "도달"), ("링크 클릭", "링크 클릭")):
                rows.append(["5_부록_일자별", NAMES[arm], date, "", "", metric, int(r[col]), ""])
            rows.append(["5_부록_일자별", NAMES[arm], date, "", "", "랜딩 페이지 조회", v, "원본 일자별에 없음 → 기간 합계를 그날 링크 클릭 비율로 나눔"])
    rows.append(["6_한계", "", "", "", "", "한계", "표본이 작음(링크 클릭 A 6·B 41), A 게재 중단(11/18~19), 지출 규모 다름, 타깃·노출 위치 묶음 비교, 일자별 랜딩 조회는 추정", ""])
    return rows


def main() -> None:
    rows = convert(Path(sys.argv[1]).expanduser())
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        csv.writer(f).writerows(rows)
    print(OUT.relative_to(ROOT), len(rows) - 1, "rows")


if __name__ == "__main__":
    main()
