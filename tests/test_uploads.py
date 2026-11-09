"""MVP 7e 4c: 올린 파일의 열 짐작을 한 곳(uploads.guess_columns)으로. 광고 리포트·판매처 통계·주문 내역이 같은 규칙을 씀."""
from src.engine import measure as MS
from src.engine import orders as OR
from src.engine import report as R
from src.engine import uploads as U


def test_guess_columns_rules():
    fields = [("revenue", ["결제금액", "매출"]), ("orders", ["결제", "구매"])]
    # 한 열은 한 항목에만 (매출을 먼저 보므로 '결제금액'이 구매 수로 잡히지 않음), 공백·대소문자 무시
    got = U.guess_columns(fields, ["결제 금액", "결제수"])
    assert got == {"revenue": "결제 금액", "orders": "결제수"}
    # '='로 시작하면 정확히 같은 이름만, exclude 낱말이 든 열은 포함 검사에서 뺌
    f2 = [("clicks", ["=링크 클릭", "클릭"]), ("cost", ["비용"])]
    assert U.guess_columns(f2, ["링크 클릭률", "클릭수", "평균비용", "총비용"], exclude=("률", "평균")) == {"clicks": "클릭수", "cost": "총비용"}
    assert U.guess_columns(f2, []) == {"clicks": None, "cost": None}


def test_three_file_kinds_use_the_same_guess():
    naver = ["캠페인", "노출수", "클릭수", "평균클릭비용(VAT포함,원)", "총비용(VAT포함,원)", "전환수"]
    assert R.map_columns(naver, "naver")["cost"] == "총비용(VAT포함,원)"
    assert MS.detect_columns(["날짜", "유입수", "상품상세 조회수", "장바구니", "결제수", "결제금액"])["orders"] == "결제수"
    assert OR.detect(["order.ordererNo", "order.paymentDate", "order.orderId"])["customer"] == "order.ordererNo"
