"""사양 파일(v2/specs/*.yaml) 읽기와 검사.

사양이 코드보다 먼저다: 칸·컬럼·규칙을 바꾸려면 YAML을 고치고, 이 모듈의 check_all()이 서로 맞는지 확인한다.
"""
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import yaml

SPEC_DIR = Path(__file__).resolve().parents[1] / "specs"

FIELD_KINDS = {"question", "precheck", "llm", "auto", "default", "next_cycle"}
COLUMN_TYPES = {"str", "date", "int", "float", "ratio"}
OPS = {">", ">=", "<", "<=", "=="}


def _load(name: str) -> dict:
    return yaml.safe_load((SPEC_DIR / name).read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def fields(media: str) -> Dict:
    """media: 'meta' | 'naver' → {"title", "fields": [...]}"""
    return _load(f"{media}_fields.yaml")


@lru_cache(maxsize=None)
def all_fields() -> Dict[str, dict]:
    """칸 id → 칸 사양 (두 매체 합침)."""
    out = {}
    for media in ("meta", "naver"):
        for f in fields(media)["fields"]:
            out[f["id"]] = dict(f, media=media)
    return out


@lru_cache(maxsize=None)
def columns() -> Dict:
    return _load("columns.yaml")


@lru_cache(maxsize=None)
def rules() -> List[dict]:
    return _load("rules.yaml")["rules"]


@lru_cache(maxsize=None)
def assumptions() -> Dict:
    return _load("assumptions.yaml")


def check_all() -> List[str]:
    """사양끼리 어긋난 곳 목록 (비어 있으면 통과)."""
    problems = []
    ids = set()
    for media in ("meta", "naver"):
        for f in fields(media)["fields"]:
            fid = f.get("id", "?")
            if fid in ids:
                problems.append(f"칸 id 중복: {fid}")
            ids.add(fid)
            if not fid.startswith(media + "."):
                problems.append(f"{fid}: id가 '{media}.'로 시작하지 않음")
            if f.get("kind") not in FIELD_KINDS:
                problems.append(f"{fid}: kind '{f.get('kind')}' 모름")
            if f.get("kind") in ("question", "precheck", "llm") and not f.get("ask"):
                problems.append(f"{fid}: 묻는 칸인데 ask 없음")
            if f.get("kind") == "auto" and not f.get("auto"):
                problems.append(f"{fid}: auto 칸인데 auto 함수 이름 없음")
            if not f.get("why"):
                problems.append(f"{fid}: why(한 줄 설명) 없음")
            if f.get("options") and f.get("default") not in (None, "") and f["default"] not in f["options"]:
                problems.append(f"{fid}: default가 options에 없음")
    rule_ids = {r["id"] for r in rules()}
    for media in ("meta", "naver"):
        for f in fields(media)["fields"]:
            for rid in f.get("next_cycle", []) or []:
                if rid not in rule_ids:
                    problems.append(f"{f['id']}: next_cycle의 규칙 {rid} 없음")
            if f.get("shared_with") and f["shared_with"] not in ids:
                problems.append(f"{f['id']}: shared_with {f['shared_with']} 없음")
    for r in rules():
        for c in r.get("when", []):
            if c.get("op") not in OPS:
                problems.append(f"{r['id']}: op '{c.get('op')}' 모름")
        for ch in r.get("changes", []) or []:
            if ch.get("field") not in ids:
                problems.append(f"{r['id']}: 바꿀 칸 {ch.get('field')} 없음")
            if ("set" in ch) == ("set_from" in ch):
                problems.append(f"{r['id']}: {ch.get('field')}에 set과 set_from 중 하나만")
    for tname, t in columns()["tables"].items():
        for cname, c in t["columns"].items():
            if c.get("type") not in COLUMN_TYPES:
                problems.append(f"{tname}.{cname}: type '{c.get('type')}' 모름")
    return problems
