"""계획 파일과 '다음 달로 넘어가기' (T12).

- Plan: 이번 달 세팅(가게 정보·고른 매체·답·예산 계획)과 지난 달 기록(history)을 한 덩어리로 든다.
- to_json / from_json: 사장님이 내려받아 보관했다가 다음 달에 다시 올리는 파일. 깨졌거나 다른 파일이면 PlanError.
- next_month: 진단 결과(findings)가 바꾸라고 한 칸을 answers에 반영하고, 한 달 뒤 Plan과 '바뀐 칸 표'를 돌려준다.
"""
import copy
import json
from dataclasses import asdict, dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd

from . import diagnose, intake, specs

VERSION = "2.0.0"
FORMAT_TAG = "ad-coach-plan"   # 파일 안에 적어 두는 표시 (다른 JSON 파일과 구분)
REQUIRED = ("store", "media", "answers", "budget_plan", "history")
# 일 예산 칸 → budget_plan 키 (다음 달 예산 계획도 같이 맞춘다)
BUDGET_KEYS = {"meta.adset.daily_budget": "meta_daily", "naver.campaign.daily_budget": "naver_daily",
               "naver.group.bid": "naver_bid"}


class PlanError(Exception):
    """계획 파일을 읽을 수 없을 때. 메시지는 사장님에게 그대로 보여 줘도 되는 쉬운 문장."""


@dataclass
class Plan:
    version: str = VERSION
    month_index: int = 1
    created: str = ""
    store: Dict[str, object] = field(default_factory=dict)   # name, product, product_slug, store_type, price, margin_per_order, budget, seeds
    media: List[str] = field(default_factory=list)
    answers: Dict[str, object] = field(default_factory=dict)
    budget_plan: Dict[str, object] = field(default_factory=dict)
    history: List[Dict[str, object]] = field(default_factory=list)   # {"month", "fired", "changes"}


# ── 저장·불러오기 ─────────────────────────────────────────

def _plain(x: object) -> object:
    """numpy·pandas 숫자처럼 JSON이 모르는 값을 기본 파이썬 값으로."""
    if hasattr(x, "item"):
        try:
            return x.item()
        except (ValueError, TypeError):
            pass
    if hasattr(x, "isoformat"):
        return x.isoformat()
    raise TypeError(f"저장할 수 없는 값이에요: {type(x).__name__}")


def to_json(plan: Plan) -> str:
    """계획을 사람이 열어 봐도 읽히는 JSON 글로."""
    data = {"format": FORMAT_TAG, **asdict(plan)}
    return json.dumps(data, ensure_ascii=False, indent=2, default=_plain)


def _bad(why: str) -> PlanError:
    return PlanError(f"{why} 앞에서 내려받은 '계획 파일'을 올렸는지 확인해 주세요.")


def from_json(text: object) -> Plan:
    """JSON 글(또는 바이트)을 Plan으로. 깨진 글·다른 프로그램의 파일·모자란 항목은 PlanError."""
    if isinstance(text, (bytes, bytearray)):
        try:
            text = text.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise _bad("파일을 글자로 읽을 수 없어요.")
    if not isinstance(text, str) or not text.strip():
        raise _bad("파일이 비어 있어요.")
    try:
        data = json.loads(text)
    except ValueError:
        raise _bad("파일이 깨졌거나 계획 파일이 아니에요.")
    if not isinstance(data, dict):
        raise _bad("계획 파일 모양이 아니에요.")
    if data.get("format", FORMAT_TAG) != FORMAT_TAG:
        raise _bad("이 프로그램에서 만든 파일이 아니에요.")
    missing = [k for k in REQUIRED if k not in data]
    if missing:
        raise _bad(f"계획에 꼭 필요한 항목({', '.join(missing)})이 없어요.")
    if not str(data.get("version", "")).startswith("2."):
        raise _bad(f"파일 버전({data.get('version', '알 수 없음')})이 달라서 읽을 수 없어요.")
    if not (isinstance(data["store"], dict) and isinstance(data["answers"], dict)
            and isinstance(data["budget_plan"], dict) and isinstance(data["media"], list)
            and isinstance(data["history"], list)):
        raise _bad("계획 항목의 모양이 맞지 않아요.")
    month = data.get("month_index", 1)
    if isinstance(month, bool) or not isinstance(month, int) or month < 1:
        raise _bad("몇 번째 달인지 알 수 없어요.")
    return Plan(version=str(data["version"]), month_index=month, created=str(data.get("created", "")),
                store=data["store"], media=[str(m) for m in data["media"]], answers=data["answers"],
                budget_plan=data["budget_plan"], history=data["history"])


# ── 다음 달로 ─────────────────────────────────────────────

def setup_context(plan: Plan) -> intake.SetupContext:
    """계획에서 세팅 맥락을 다시 만든다 (바꾸기 전 값을 정확히 보여 주려고)."""
    s, b = plan.store, plan.budget_plan
    product = str(s.get("product") or s.get("name") or "상품")
    return intake.SetupContext(
        product=product, product_slug=str(s.get("product_slug") or ""),
        store_type=str(s.get("store_type") or "smartstore"), month=str(s.get("month") or ""),
        media=list(plan.media), meta_daily=int(b.get("meta_daily") or 0),
        naver_daily=int(b.get("naver_daily") or 0), naver_bid=int(b.get("naver_bid") or 0),
        keywords=list(s.get("seeds") or []))


def _tidy(change: object) -> object:
    """예산·입찰 칸은 원 단위 정수로 다듬은 사본을 쓴다 (지표 값은 소수일 수 있어서)."""
    if change.field_id in BUDGET_KEYS and isinstance(change.new, (int, float)):
        change = copy.copy(change)
        change.new = int(round(float(change.new)))
    return change


def _seen_values(history: List[Dict[str, object]]) -> Dict[str, set]:
    """지난 달들에 칸마다 '바뀌기 전·바뀐 뒤'로 나왔던 값(보이는 글). 옛 계획 파일의 기록도 그대로 읽는다."""
    seen: Dict[str, set] = {}
    for rec in history or []:
        if not isinstance(rec, dict):
            continue
        for row in rec.get("changes") or []:
            if isinstance(row, dict) and row.get("field_id"):
                s = seen.setdefault(str(row["field_id"]), set())
                for k in ("before", "after"):
                    if row.get(k) is not None:
                        s.add(str(row[k]).strip())
    return seen


def _measured_pairs() -> set:
    """(규칙 id, 칸 id) 중 지표로 계산한 값(set_from)을 쓰는 것. 이런 값은 달마다 새로 잰 숫자다."""
    return {(r["id"], c["field"]) for r in specs.rules() for c in (r.get("changes") or []) if "set_from" in c}


def _is_measured(ch: object) -> bool:
    """예산·입찰 칸이거나 set_from(측정값) 규칙에서 나온 제안이면 True."""
    return ch.field_id in BUDGET_KEYS or (ch.rule_id, ch.field_id) in _measured_pairs()


def _was_seen(ch: object, seen: Dict[str, set]) -> bool:
    """이 제안 값이 지난 달에 이미 쓰였거나(다시 적용할 필요 없음) 되돌아가는 값이면 True.

    고르는 값(노출 위치·종료일 등)만 막는다. 측정값(예산·목표 비용)은 다시 같은 숫자가 나올 수 있어서 제외.
    """
    fid = ch.field_id
    if fid not in seen or fid.endswith(".negative") or _is_measured(ch):
        return False
    fields = specs.all_fields()
    spec = fields.get(fid, {"id": fid, "kind": "default"})
    return str(intake.show(spec, ch.new)).strip() in seen[fid]


def _effective_changes(answers: dict, findings: List[diagnose.Finding], ctx: intake.SetupContext,
                       history: Optional[List[Dict[str, object]]] = None) -> list:
    """칸마다 fired 규칙의 제안 중 '지금 값과 다른' 첫 번째(rules.yaml 순서)를 고른다. 같은 값 제안은 건너뛴다.

    지난 달 기록(history)에 나온 값(바뀌기 전 값이든 바뀐 뒤 값이든)을 다시 제안하는 규칙은 건너뛴다.
    그래서 같은 데이터로 다시 진단해도 칸이 원래 값과 새 값 사이를 왔다 갔다 하지 않는다.
    """
    seen = _seen_values(history or [])
    cands: Dict[str, list] = {}
    for f in diagnose.fired(findings):
        for ch in f.changes:
            cands.setdefault(ch.field_id, []).append(_tidy(ch))
    out = []
    for fid, lst in cands.items():
        for ch in lst:
            if not intake.is_noop(answers, ch, ctx) and not _was_seen(ch, seen):
                pick = copy.copy(ch)
                out.append(pick)
                break
    return out


def next_month(plan: Plan, findings: List[diagnose.Finding]) -> Tuple[Plan, pd.DataFrame]:
    """진단이 바꾸라고 한 칸을 반영한 다음 달 계획과 '바뀐 칸' 표(field_id, label, before, after, note).

    원래 plan은 그대로 두고, 새 Plan에 month_index+1, 이번 달 기록(history)을 더한다.
    """
    ctx = setup_context(plan)
    changes = _effective_changes(plan.answers, findings, ctx, plan.history)
    answers, diff = intake.apply_changes(copy.deepcopy(plan.answers), changes, ctx)
    changes = [c for c in changes if c.field_id in set(diff["field_id"])]
    budget_plan = copy.deepcopy(plan.budget_plan)
    for c in changes:
        key = BUDGET_KEYS.get(c.field_id)
        if key:
            budget_plan[key] = c.new
    record = {"month": plan.month_index, "fired": [f.id for f in diagnose.fired(findings)],
              "changes": diff.to_dict("records")}
    new = Plan(version=plan.version, month_index=plan.month_index + 1, created=plan.created,
               store=copy.deepcopy(plan.store), media=list(plan.media), answers=answers,
               budget_plan=budget_plan, history=copy.deepcopy(plan.history) + [record])
    return new, diff
