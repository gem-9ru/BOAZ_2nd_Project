"""가상 케이스 6개 (메타 설정만 다르게): 분석 엔진이 규칙대로 결론·알림을 내는지. 화면 표(web/src/steps/cases.ts)와도 같은지."""
import json
import re
from pathlib import Path

from server.engine.loop.virtual import CASES, all_outcomes

CASES_TS = Path(__file__).resolve().parents[2] / "web" / "src" / "steps" / "cases.ts"


def test_six_meta_only_cases():
    assert [c["id"] for c in CASES] == ["V1", "V2", "V3", "V4", "V5", "V6"]
    assert not any("네이버" in c["setting"] for c in CASES)


def test_each_case_triggers_its_rule():
    o = {x["id"]: x for x in all_outcomes()}
    assert "no_delivery" in o["V3"]["alerts"] and "underspent" in o["V3"]["alerts"] and o["V3"]["conclusion"].startswith("광고 세트 › 예산")
    assert "spend_gap" in o["V4"]["alerts"] and o["V4"]["word"] == "아직 몰라요"   # 돈이 몰리면 판정을 한 단계 낮춤
    assert "low_visit_rate" in o["V5"]["alerts"] and o["V5"]["conclusion"].startswith("광고 › 웹사이트 URL")
    assert "high_frequency" in o["V6"]["alerts"] and "새 소재" in o["V6"]["conclusion"]


def test_screen_table_matches_the_engine():
    text = CASES_TS.read_text(encoding="utf-8")
    rows = json.loads(re.search(r"VIRTUAL_CASES: VirtualCase\[\] = (\[.*?\]);\n", text, re.S).group(1))
    assert rows == all_outcomes(), "엔진이 바뀌었으면 scripts/virtual_cases.py 를 다시 돌려 표를 갱신하세요"
