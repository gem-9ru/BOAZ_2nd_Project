"""시연 저장본 만들기: 진짜 키(.env)로 한 번 받아 새로 생긴 저장본만 server/data/cache_examples 로 복사.

사용: python scripts/pin_find_examples.py "수제 쿠키" 답례품쿠키 디저트선물 수제쿠키 쿠키선물세트 휘낭시에
출력은 복사한 파일 이름뿐이다(키·응답 내용은 출력하지 않음).
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server.engine import market, naver_api  # noqa: E402


def _snapshot() -> dict:
    if not naver_api.CACHE_DIR.exists():
        return {}
    return {p.name: p.stat().st_mtime_ns for p in naver_api.CACHE_DIR.glob("*.json")}


def main(argv: list) -> int:
    if len(argv) < 2:
        print('사용: pin_find_examples.py "상품" 검색어1 검색어2 ...')
        return 2
    product, seeds = argv[0], argv[1:]
    before = _snapshot()
    category = market.guess_category(product, online=True)
    report = market.build(seeds, online=True, category=category, product=product)
    if report is None:
        print("자료를 받지 못했어요:", naver_api.last_error() or "이유 없음")
        return 1
    naver_api.EXAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    for name, mtime in sorted(_snapshot().items()):
        if before.get(name) != mtime:        # 새로 생겼거나 새로 받아 덮어쓴 것만
            shutil.copy2(naver_api.CACHE_DIR / name, naver_api.EXAMPLES_DIR / name)
            copied.append(name)
    print(f"분야: {category}  복사 {len(copied)}개")
    for name in copied:
        print(" ", name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
