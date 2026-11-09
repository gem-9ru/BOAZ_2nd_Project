"""올린 파일의 열 짐작 (MVP 7e 4c): 광고 리포트·판매처 통계·주문 내역이 같은 규칙 하나를 쓴다.

규칙: 항목을 정해진 순서로 보고, 항목마다 낱말을 앞에서부터 대 보며 처음 맞는 열을 고른다. 한 열은 한 항목에만.
낱말이 '='로 시작하면 이름이 정확히 같아야 하고, 아니면 이름에 들어 있으면 된다 (exclude 낱말이 든 열은 뺌).
파일마다 다른 것(별칭·거를 열)은 각 모듈의 표(report.WORDS·measure.FIELDS·orders.FIELDS)에 있다.
"""
import re
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple


def squash(name) -> str:
    """공백을 모두 빼고 소문자로 (판매처 통계·주문 내역: '상품상세 조회수' = '상품상세조회수')."""
    return re.sub(r"\s+", "", str(name)).lower()


def guess_columns(fields: Iterable[Tuple[str, Sequence[str]]], columns: List, norm: Callable = squash,
                  exclude: Sequence[str] = (), exclude_except: Sequence[str] = ()) -> Dict[str, Optional[str]]:
    """fields: (항목, 낱말 목록) 순서대로 → {항목: 열 이름 또는 None}. norm: 열 이름·낱말을 비교 전에 다듬는 함수.
    exclude: 포함 검사에서 이 낱말이 든 열은 빼기 ('클릭률'·'평균클릭비용' 같은 파생 열), exclude_except 항목은 예외."""
    names = {c: norm(c) for c in columns}
    out, used = {}, set()
    for key, words in fields:
        out[key] = None
        for w in words:
            exact, word = w.startswith("="), norm(w.lstrip("="))
            for c in columns:
                if c in used:
                    continue
                name = names[c]
                if exact and name != word:
                    continue
                if not exact and (word not in name or (key not in exclude_except and any(x in name for x in exclude))):
                    continue
                out[key] = c
                used.add(c)
                break
            if out[key] is not None:
                break
    return out
