"""
benchmark/workloads/base.py — Shared benchmarking utilities.
"""

from __future__ import annotations

import time
import math
from typing import Any, Callable, TypeVar

T = TypeVar("T")

WARMUP_ITERATIONS = 10
MEASURED_ITERATIONS = 100


def calculate_percentiles(durations_ms: list[float]) -> dict[str, float]:
    """
    Calculate p50 and p95 latencies from measured duration list in milliseconds.
    """
    if not durations_ms:
        return {"p50": 0.0, "p95": 0.0, "mean": 0.0, "min": 0.0, "max": 0.0}

    sorted_d = sorted(durations_ms)
    n = len(sorted_d)

    p50_idx = int(math.ceil(0.50 * n)) - 1
    p95_idx = int(math.ceil(0.95 * n)) - 1

    p50 = sorted_d[max(0, min(p50_idx, n - 1))]
    p95 = sorted_d[max(0, min(p95_idx, n - 1))]

    return {
        "p50": round(p50, 4),
        "p95": round(p95, 4),
        "mean": round(sum(sorted_d) / n, 4),
        "min": round(sorted_d[0], 4),
        "max": round(sorted_d[-1], 4),
    }


def measure_execution(fn: Callable[[], Any]) -> float:
    """
    Execute callable and measure duration in milliseconds using high-resolution performance counter.
    """
    t0 = time.perf_counter()
    fn()
    t1 = time.perf_counter()
    return (t1 - t0) * 1000.0
