"""AARRR 기반 광고 예산 시뮬레이터 엔진 v0."""
from .acquisition import Channel, MetaCurve, NaverCurve
from .model import FunnelParams, SimResult, simulate
from .optimize import budget_scan, lever_table, optimize_allocation

__all__ = [
    "Channel", "MetaCurve", "NaverCurve", "FunnelParams", "SimResult", "simulate",
    "budget_scan", "lever_table", "optimize_allocation",
]
