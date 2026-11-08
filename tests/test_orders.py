"""MVP 7b: 주문 내역 → 재구매 실측."""
import io
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import coach as C  # noqa: E402
from src.engine import orders as O  # noqa: E402

PARAMS = C.coach_params(20_000, 7_000, 0.0)


def _csv(rows, cols):
    buf = io.BytesIO(pd.DataFrame(rows, columns=cols).to_csv(index=False).encode("utf-8-sig"))
    buf.name = "orders.csv"
    return buf


COLS = ["order.orderId", "order.ordererNo", "order.ordererName", "order.ordererTel", "productOrder.shippingAddress",
        "order.paymentDate", "productOrder.productOrderStatus", "productOrder.inflowPath"]


def test_personal_columns_never_reach_the_result():
    rows = [["1", "C1", "홍길동", "010-1111-2222", "서울시 어딘가", "2026-08-01", "PURCHASE_DECIDED", "네이버 쇼핑"],
            ["2", "C1", "홍길동", "010-1111-2222", "서울시 어딘가", "2026-09-01", "DELIVERED", "네이버 쇼핑"]]
    df = O.read_orders(_csv(rows, COLS))
    assert not {"order.ordererName", "order.ordererTel", "productOrder.shippingAddress"} & set(df.columns)
    clean = O.clean(df, O.detect(list(df.columns)))
    assert "C1" not in set(clean["cid"])                       # 주문자 번호는 해시로만
    res = O.measure(clean, PARAMS)
    text = json.dumps(res, ensure_ascii=False, default=str)
    for secret in ("홍길동", "010-1111-2222", "서울시", "C1"):
        assert secret not in text


def test_cancel_and_return_excluded():
    rows = [["1", "A", "", "", "", "2026-08-01", "PURCHASE_DECIDED", "x"],
            ["2", "A", "", "", "", "2026-08-15", "CANCELED", "x"],
            ["3", "A", "", "", "", "2026-08-20", "RETURNED", "x"],
            ["4", "B", "", "", "", "2026-08-02", "DELIVERED", "x"]]
    clean = O.clean(O.read_orders(_csv(rows, COLS)), O.detect(COLS))
    assert len(clean) == 2
    res = O.measure(clean, PARAMS)
    assert res["customers"] == 2 and res["repeats_observed"] == 0


def test_short_observation_is_extended_to_a_year():
    rows, oid = [], 0
    for i in range(40):                                        # 손님 40명: 8월 1일 첫 구매, 절반은 9월 1일에 한 번 더
        oid += 1
        rows.append([str(oid), f"c{i}", "", "", "", "2026-08-01", "DELIVERED", "네이버 쇼핑" if i % 2 else "검색광고(SA)"])
        if i % 2 == 0:
            oid += 1
            rows.append([str(oid), f"c{i}", "", "", "", "2026-09-01", "DELIVERED", "검색광고(SA)"])
    rows.append([str(oid + 1), "z", "", "", "", "2026-10-31", "DELIVERED", "네이버 쇼핑"])   # 관찰 끝 = 10월 말 (3개월)
    res = O.measure(O.clean(O.read_orders(_csv(rows, COLS)), O.detect(COLS)), PARAMS)
    assert res["extended"] and 2.5 < res["observed_months"] < 3.2
    assert res["repeats_year"] > res["repeats_observed"]        # 남은 달을 곡선으로 늘림
    by = {r["inflow"]: r for r in res["by_inflow"]}
    assert by["검색광고(SA)"]["repeat_share"] == 1.0 and by["네이버 쇼핑"]["repeat_share"] == 0.0


def test_errors_say_how_to_fix():
    empty = io.BytesIO(b""); empty.name = "orders.csv"
    with pytest.raises(O.OrdersError, match="비어 있어요"):
        O.read_orders(empty)
    df = O.read_orders(_csv([["1", "2026-08-01"]], ["주문번호", "결제일"]))
    with pytest.raises(O.OrdersError, match="열을 찾지 못했어요"):
        O.clean(df, O.detect(list(df.columns)))


@pytest.mark.parametrize("ex", ["coffee", "protein"])
def test_demo_orders_measure(ex):
    df = O.read_orders(ROOT / "data" / "examples" / "demo_store" / ex / "orders.csv")
    res = O.measure(O.clean(df, O.detect(list(df.columns))), PARAMS)
    assert res["extended"] and res["customers"] > 50 and 0 < res["repeats_observed"] < res["repeats_year"]
    assert 3 <= res["repeats_year"] <= 9          # 가상 데이터는 엔진 곡선(1년 6번)으로 만듦 → 3개월·손님 70~100명이라 오차 있음
