"""확장의 금지 표현 목록(extension/lib/copyRules.ts)이 서버(copywriter.BANNED)와 같은지."""
import re
from pathlib import Path

from server.engine import copywriter


def test_extension_banned_words_match_server():
    ts = (Path(__file__).resolve().parents[2] / "extension" / "lib" / "copyRules.ts").read_text(encoding="utf-8")
    body = re.search(r"BANNED = \[(.*?)\];", ts, flags=re.S).group(1)
    assert re.findall(r'"([^"]+)"', body) == copywriter.BANNED
