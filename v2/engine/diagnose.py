"""진단 (T10): 지표(metrics) + 규칙(rules.yaml) → 사장님에게 보여 줄 진단 카드와 '다음 달에 바꿀 칸'.

- 규칙의 조건이 모두 참이면 fired, 하나라도 거짓이면 passed.
- 조건에 쓰는 지표가 없거나 None이면(그 데이터가 안 올라옴) no_data로 건너뛴다.
- 숫자는 metrics.fmt로 보기 좋게 바꿔 문장에 넣는다.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from . import specs
from .metrics import fmt

_OPS = {
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    "==": lambda a, b: a == b,
}


@dataclass
class Change:
    """다음 달에 바꿀 칸 하나."""
    field_id: str
    label: str
    media: str
    new: object
    note: str
    rule_id: str


@dataclass
class Finding:
    id: str
    title: str
    funnel: str
    status: str                      # "fired" | "passed" | "no_data"
    message: str = ""                # fired일 때만 채움
    evidence: Dict[str, str] = field(default_factory=dict)
    changes: List[Change] = field(default_factory=list)
    advice: Optional[str] = None
    caveat: Optional[str] = None
    grade: str = "hypothesis"


def _present(value) -> bool:
    """None과 NaN(float·numpy)은 '값 없음'으로 본다."""
    if value is None:
        return False
    try:
        return not bool(value != value)
    except (TypeError, ValueError):
        return True


def _has(metrics: dict, name: str) -> bool:
    return _present(metrics.get(name))


def _holds(cond: dict, metrics: dict) -> bool:
    return bool(_OPS[cond["op"]](metrics[cond["metric"]], cond["value"]))


def _message(says: str, metrics: dict) -> str:
    """says의 {metric}을 fmt한 값으로 바꾼다. 없는 지표는 '-'."""
    class _Fmt(dict):
        def __missing__(self, key):
            return "-"
    values = _Fmt({k: fmt(k, v) for k, v in metrics.items() if _present(v)})
    try:
        return says.format_map(values)
    except (ValueError, IndexError):
        return says


def _changes(rule: dict, metrics: dict) -> List[Change]:
    """set_from 지표가 없으면 그 칸은 뺀다."""
    out = []
    fields = specs.all_fields()
    for ch in rule.get("changes") or []:
        fid = ch["field"]
        if "set_from" in ch:
            if not _has(metrics, ch["set_from"]):
                continue
            new = metrics[ch["set_from"]]
        else:
            new = ch["set"]
        spec = fields.get(fid, {})
        out.append(Change(field_id=fid, label=spec.get("label", fid), media=spec.get("media", fid.split(".")[0]),
                          new=new, note=ch.get("note", ""), rule_id=rule["id"]))
    return out


def _evaluate_rule(rule: dict, metrics: dict) -> Finding:
    base = dict(id=rule["id"], title=rule["title"], funnel=rule.get("funnel", ""), grade=rule.get("grade", "hypothesis"))
    conds = rule.get("when", [])
    if not all(_has(metrics, c["metric"]) for c in conds):
        return Finding(status="no_data", **base)
    if not all(_holds(c, metrics) for c in conds):
        return Finding(status="passed", **base)
    evidence = {c["metric"]: fmt(c["metric"], metrics[c["metric"]]) for c in conds}
    return Finding(status="fired", message=_message(rule["says"], metrics), evidence=evidence,
                   changes=_changes(rule, metrics), advice=rule.get("advice"), caveat=rule.get("caveat"), **base)


def evaluate(metrics: dict, rules: Optional[list] = None) -> List[Finding]:
    """모든 규칙을 사양 순서대로 평가한다."""
    return [_evaluate_rule(r, metrics) for r in (rules if rules is not None else specs.rules())]


def fired(findings) -> List[Finding]:
    return [f for f in findings if f.status == "fired"]


def next_changes(findings) -> List[Change]:
    """fired 규칙의 변경을 모은다. 같은 칸은 먼저 나온 규칙의 값 하나만 쓰고 note는 합친다."""
    out: Dict[str, Change] = {}
    for f in fired(findings):
        for ch in f.changes:
            if ch.field_id not in out:
                out[ch.field_id] = Change(ch.field_id, ch.label, ch.media, ch.new, ch.note, ch.rule_id)
            elif ch.note and ch.note not in out[ch.field_id].note:
                first = out[ch.field_id]
                first.note = f"{first.note} / {ch.note}" if first.note else ch.note
    return list(out.values())
