"""가상 케이스 6개를 실제 분석 엔진에 돌려 web/src/steps/cases.ts 로 적는다 (AN-06 근거 탭 표).

사용: .venv/bin/python scripts/virtual_cases.py
같은 설정 두 세트(V2)를 시드 40개로 돌려 '우연인데 차이가 있다고 본 비율'도 같이 적는다.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from server.engine.loop.virtual import CASES, SEED, all_outcomes, outcome  # noqa: E402

NULL_RUNS = 40


def main() -> None:
    rows = all_outcomes()
    same = next(c for c in CASES if c["id"] == "V2")
    words = Counter(outcome(same, seed=s)["word"] for s in range(NULL_RUNS))
    null = {"runs": NULL_RUNS, "sure": words["확실해요"], "lean": words["A 쪽이에요"] + words["B 쪽이에요"], "unknown": words["아직 몰라요"]}
    out = ROOT / "web" / "src" / "steps" / "cases.ts"
    out.write_text(
        "// scripts/virtual_cases.py 가 만든 파일 (손으로 고치지 않음). 원본: server/engine/loop/virtual.py, 시드 " + str(SEED) + "\n"
        "/** AN-06 근거 탭 '가상 케이스' 6개: 메타 설정 하나만 다르게 한 A/B를 오븐로그 실측 비율로 만들어 분석 엔진에 넣은 결과. 판정에는 안 씀. */\n"
        "export interface VirtualCase { id: string; setting: string; basis: string; conclusion: string;\n"
        "  word: \"확실해요\" | \"A 쪽이에요\" | \"B 쪽이에요\" | \"아직 몰라요\" | null; prob: number | null; better: \"A\" | \"B\" | null; alerts: string[] }\n\n"
        f"export const VIRTUAL_CASES: VirtualCase[] = {json.dumps(rows, ensure_ascii=False, indent=2)};\n\n"
        "/** 같은 설정 두 세트(V2)를 시드만 바꿔 돌렸을 때 판정 횟수: 우연한 차이를 차이로 본 비율 */\n"
        f"export const SAME_SETTING_RUNS = {json.dumps(null, ensure_ascii=False)};\n",
        encoding="utf-8")
    print(out.relative_to(ROOT), null)


if __name__ == "__main__":
    main()
