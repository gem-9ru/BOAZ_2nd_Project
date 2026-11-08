"""주문 내역 → 재구매 실측 (MVP 7b). 스마트스토어 커머스API '상품 주문 정보 구조체' 항목 이름(커머스API_주문데이터_매핑.md 2장),
한글 열 이름이면 짐작 규칙 + 사용자 수정 (측정 키트와 같은 방식).

- 개인정보 열(이름·전화·주소·주문자 ID·배송지 등)은 읽자마자 버린다. 주문자 번호는 해시로만 메모리에서 쓰고, 파일은 저장하지 않는다.
- 취소·반품 제외 → 고객별 첫 구매 날 → 관찰 기간 안 재구매 횟수.
- 관찰이 12개월보다 짧으면 지금 엔진 리텐션 곡선 모양(바닥값·감소 속도)에 관찰값을 맞춰 1년으로 늘린다 (관찰분 등급 A, 늘린 부분 C).
"""
import hashlib
import re
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

DAYS_PER_MONTH = 30.4
# 개인정보: 열 이름에 이 말이 들어가면 읽자마자 버림 (주문자 번호 ordererNo는 해시용이라 남김)
PII_WORDS = ("orderername", "orderertel", "ordererid", "shippingaddress", "receiver", "pickuplocation", "entrymethod",
             "이름", "성명", "전화", "연락처", "휴대", "주소", "수취인", "수령인", "배송지", "이메일", "email", "아이디")
FIELDS = {
    # 항목: (화면 이름, 짐작할 열 이름 조각 — 앞에 있는 것부터)
    "customer": ("주문자 번호", ["order.ordererno", "ordererno", "주문자번호", "구매자번호", "회원번호", "고객번호", "customer"]),
    "date": ("결제(주문) 일시", ["order.paymentdate", "paymentdate", "결제일", "결제일시", "주문일", "주문일시", "orderdate", "date"]),
    "order": ("주문 번호", ["order.orderid", "orderid", "주문번호"]),
    "status": ("주문 상태", ["productorderstatus", "주문상태", "상품주문상태", "status"]),
    "inflow": ("유입 경로", ["productorder.inflowpath", "inflowpath", "유입경로", "유입"]),
}
CANCEL_WORDS = ("CANCEL", "RETURN", "취소", "반품", "환불")


class OrdersError(ValueError):
    """화면에 그대로 보여 줄 고치는 법 문구."""


def drop_pii(df: pd.DataFrame) -> pd.DataFrame:
    keep = [c for c in df.columns if not any(w in re.sub(r"[\s._]", "", str(c)).lower() for w in PII_WORDS)
            or "ordererno" in str(c).lower()]
    return df[keep]


def detect(columns: List[str]) -> Dict[str, Optional[str]]:
    norm = {c: re.sub(r"\s+", "", str(c)).lower() for c in columns}
    out, used = {}, set()
    for key, (_, words) in FIELDS.items():
        out[key] = None
        for w in words:
            hit = next((c for c in columns if c not in used and w in norm[c]), None)
            if hit is not None:
                out[key] = hit
                used.add(hit)
                break
    return out


def _hash(v) -> str:
    return hashlib.sha256(str(v).encode("utf-8")).hexdigest()[:16]


def read_orders(f) -> pd.DataFrame:
    """CSV(BOM 포함)·엑셀 → 개인정보 열을 버린 표. 빈 파일이면 OrdersError."""
    name = getattr(f, "name", str(f)).lower()
    try:
        df = pd.read_csv(f, encoding="utf-8-sig", dtype=str) if name.endswith(".csv") else pd.read_excel(f, dtype=str)
    except pd.errors.EmptyDataError as e:
        raise OrdersError("주문 파일이 비어 있어요. 스마트스토어센터(또는 커머스API)에서 주문 내역을 다시 내려받아 올려 주세요.") from e
    df.columns = [str(c).replace("﻿", "").strip() for c in df.columns]
    df = drop_pii(df)
    if df.empty:
        raise OrdersError("주문 파일에 주문이 한 줄도 없어요. 기간을 넓혀 다시 내려받아 주세요.")
    return df


def clean(df: pd.DataFrame, mapping: Dict[str, Optional[str]]) -> pd.DataFrame:
    """필요한 열만 남긴 표: cid(해시), date, oid, inflow. 취소·반품 제외."""
    missing = [FIELDS[k][0] for k in ("customer", "date") if not mapping.get(k) or mapping[k] not in df.columns]
    if missing:
        raise OrdersError(f"{', '.join(missing)} 열을 찾지 못했어요. 아래 '열 맞추기'에서 직접 골라 주세요.")
    out = pd.DataFrame({"cid": df[mapping["customer"]].map(_hash),
                        "date": pd.to_datetime(df[mapping["date"]].astype(str).str.slice(0, 19), errors="coerce")})
    out["oid"] = df[mapping["order"]].astype(str) if mapping.get("order") in df.columns else out.index.astype(str)
    out["inflow"] = df[mapping["inflow"]].fillna("(없음)").astype(str) if mapping.get("inflow") in df.columns else "(없음)"
    if mapping.get("status") in df.columns:
        st = df[mapping["status"]].fillna("").astype(str).str.upper()
        out = out[~st.str.contains("|".join(CANCEL_WORDS), regex=True).values]
    out = out.dropna(subset=["date"])
    if out.empty:
        raise OrdersError("취소·반품을 빼니 남는 주문이 없어요. 날짜 열이 맞는지 확인해 주세요.")
    return out.drop_duplicates("oid") if mapping.get("order") in df.columns else out


def _repeats_expected(params, scale: float, exposure: np.ndarray) -> float:
    """손님마다 첫 구매 뒤 exposure개월 동안 엔진 곡선(배수 scale)으로 기대되는 재구매 횟수의 합.
    엔진의 r(k)는 첫 구매 뒤 k번째 달(경과 k ~ k+1개월)의 몫이라, 경과 e개월이면 재구매가 쌓인 시간은 e − 1개월."""
    r = params.with_changes(retention_scale=scale).retention(13)
    cum = np.concatenate([[0.0], np.cumsum(r[1:] * params.purchase_freq)])        # cum[k] = 1..k번째 달 합
    x = np.clip(exposure - 1.0, 0, 11)
    k = np.floor(x).astype(int)
    frac = x - k
    nxt = np.minimum(k + 1, 11)
    return float((cum[k] + frac * (cum[nxt] - cum[k])).sum())


def measure(orders: pd.DataFrame, params, end: Optional[pd.Timestamp] = None) -> Dict:
    """관찰 재구매 → 1년 재구매 횟수. params: 엔진 FunnelParams (곡선 모양). 결과에 고객 식별자는 없음."""
    end = end or orders["date"].max()
    first = orders.sort_values("date").groupby("cid").first()
    counts = orders.groupby("cid")["oid"].nunique()
    repeats = (counts - 1).reindex(first.index).fillna(0)
    exposure = ((end - first["date"]).dt.days / DAYS_PER_MONTH).clip(lower=0).values
    observed_months = float((orders["date"].max() - orders["date"].min()).days / DAYS_PER_MONTH)
    total = float(repeats.sum())
    base = params.with_changes(retention_scale=1.0)

    def fit(rep_total: float, exp: np.ndarray) -> float:
        if rep_total <= 0 or _repeats_expected(base, 1.0, exp) <= 0:
            return 0.0
        # 곡선이 첫 달들에서 100%에 닿으면(재구매가 아주 많은 가게) 배수를 키워도 관찰 기간 기대값이 거의 늘지 않아
        # 맞추기가 끝없이 커질 수 있다 → 곡선이 설명할 수 있는 최대의 97%까지만 맞춤 (가장 작은 배수)
        ceiling = _repeats_expected(base, 1e4, exp)
        rep_total = min(rep_total, 0.97 * ceiling)
        lo, hi = 0.0, 1.0
        while _repeats_expected(base, hi, exp) < rep_total and hi < 1e4:
            hi *= 2
        for _ in range(50):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if _repeats_expected(base, mid, exp) < rep_total else (lo, mid)
        return hi

    def per_year(scale: float) -> float:
        return float(base.with_changes(retention_scale=scale).retention(12)[1:].sum() * params.purchase_freq)

    scale = fit(total, exposure)
    by_inflow = []
    for path, g in first.groupby("inflow"):
        idx = first.index.isin(g.index)
        s = fit(float(repeats[idx].sum()), exposure[idx])
        by_inflow.append({"inflow": path, "customers": int(idx.sum()), "repeat_share": float((repeats[idx] > 0).mean()),
                          "repeats_observed": float(repeats[idx].mean()), "repeats_year": per_year(s)})
    by_inflow.sort(key=lambda r: -r["customers"])
    return {
        "customers": int(len(first)), "orders": int(orders["oid"].nunique()), "observed_months": observed_months,
        "repeat_share": float((repeats > 0).mean()), "repeats_observed": float(repeats.mean()),
        "repeats_year": per_year(scale), "extended": observed_months < 11.5, "scale": scale, "by_inflow": by_inflow,
    }
