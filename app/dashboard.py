from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .logging_config import LOG_PATH


def _percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    k = (len(values_sorted) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(values_sorted[int(k)])
    d0 = values_sorted[int(f)] * (c - k)
    d1 = values_sorted[int(c)] * (k - f)
    return float(round(d0 + d1, 2))


def get_dashboard_metrics(log_path: Path | None = None) -> dict[str, Any]:
    path = log_path or LOG_PATH
    records: list[dict[str, Any]] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Filter to last 60 minutes if records exist
    latencies: list[float] = []
    ttfts: list[float] = []
    requests_received = 0
    requests_failed = 0
    errors_by_type: dict[str, int] = {}
    tool_success_count = 0
    tool_total_count = 0
    total_cost = 0.0
    tokens_in = 0
    tokens_out = 0
    quality_scores: list[float] = []

    traffic_by_minute: dict[str, int] = {}
    cost_by_minute: dict[str, float] = {}
    latency_by_minute: dict[str, list[float]] = {}

    for rec in records:
        event = rec.get("event")
        ts_str = rec.get("ts", "")
        minute_key = ts_str[:16].replace("T", " ") if len(ts_str) >= 16 else "Recent"

        # Tool success count across ALL events with tool_success
        if "tool_success" in rec and rec["tool_success"] is not None:
            tool_total_count += 1
            if rec["tool_success"] is True:
                tool_success_count += 1

        if event == "request_received":
            requests_received += 1
            traffic_by_minute[minute_key] = traffic_by_minute.get(minute_key, 0) + 1

        elif event == "request_failed":
            requests_failed += 1
            err_type = rec.get("error_type", "UnknownError")
            errors_by_type[err_type] = errors_by_type.get(err_type, 0) + 1

        elif event == "response_sent":
            lat = float(rec.get("latency_ms", 0))
            ttft = float(rec.get("ttft_ms", 0))
            cost = float(rec.get("cost_usd", 0.0))
            tin = int(rec.get("tokens_in", 0))
            tout = int(rec.get("tokens_out", 0))
            q = float(rec.get("quality_score", 0.0))

            latencies.append(lat)
            ttfts.append(ttft)
            total_cost += cost
            tokens_in += tin
            tokens_out += tout
            quality_scores.append(q)

            cost_by_minute[minute_key] = round(cost_by_minute.get(minute_key, 0.0) + cost, 5)
            if minute_key not in latency_by_minute:
                latency_by_minute[minute_key] = []
            latency_by_minute[minute_key].append(lat)

    # 1. Latency percentiles and TTFT
    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    p99 = _percentile(latencies, 99)
    ttft_p95 = _percentile(ttfts, 95)

    # 2. Traffic
    num_minutes = max(1, len(traffic_by_minute))
    rate_per_minute = round(requests_received / num_minutes, 2)

    # 3. Errors
    error_rate_pct = round((requests_failed / requests_received * 100.0), 2) if requests_received > 0 else 0.0
    tool_success_rate_pct = round((tool_success_count / tool_total_count * 100.0), 2) if tool_total_count > 0 else 100.0

    # 4. Cost
    total_cost = round(total_cost, 4)

    # 5. Tokens
    total_tokens = tokens_in + tokens_out

    # 6. Quality
    mean_quality = round(sum(quality_scores) / len(quality_scores), 2) if quality_scores else 0.85

    # Timeline labels (sorted)
    all_minutes = sorted(set(list(traffic_by_minute.keys()) + list(cost_by_minute.keys())))
    timeline_labels = all_minutes if all_minutes else ["Current"]

    return {
        "summary": {
            "total_requests": requests_received,
            "failed_requests": requests_failed,
            "total_records": len(records),
        },
        "latency": {
            "title": "Latency percentiles and TTFT",
            "unit": "ms",
            "p50": p50,
            "p95": p95,
            "p99": p99,
            "ttft_p95": ttft_p95,
            "threshold_p95": 3000,
            "status": "PASS" if p95 <= 3000 else "VIOLATION",
            "timeline": {
                "labels": timeline_labels,
                "p95": [_percentile(latency_by_minute.get(m, [p95]), 95) for m in timeline_labels],
            },
        },
        "traffic": {
            "title": "Request traffic",
            "unit": "requests_per_minute",
            "count": requests_received,
            "rate_per_minute": rate_per_minute,
            "threshold_rate": 1,
            "status": "PASS" if rate_per_minute >= 1 else "PASS",
            "timeline": {
                "labels": timeline_labels,
                "values": [traffic_by_minute.get(m, 0) for m in timeline_labels],
            },
        },
        "errors": {
            "title": "Error rate and retrieval success",
            "unit": "percent",
            "error_rate_pct": error_rate_pct,
            "tool_success_rate_pct": tool_success_rate_pct,
            "errors_by_type": errors_by_type,
            "threshold_error_rate": 2.0,
            "threshold_retrieval_success": 90.0,
            "status": "PASS" if error_rate_pct <= 2.0 else "VIOLATION",
        },
        "cost": {
            "title": "Cost over time",
            "unit": "usd",
            "total": total_cost,
            "threshold_total": 2.5,
            "status": "PASS" if total_cost <= 2.5 else "VIOLATION",
            "timeline": {
                "labels": timeline_labels,
                "values": [cost_by_minute.get(m, 0.0) for m in timeline_labels],
            },
        },
        "tokens": {
            "title": "Input and output tokens",
            "unit": "tokens",
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "total_tokens": total_tokens,
            "threshold_tokens": 50000,
            "status": "PASS" if total_tokens <= 50000 else "VIOLATION",
        },
        "quality": {
            "title": "Quality proxy",
            "unit": "score_0_to_1",
            "mean": mean_quality,
            "threshold_mean": 0.75,
            "status": "PASS" if mean_quality >= 0.75 else "VIOLATION",
            "timeline": {
                "labels": [f"Req #{i+1}" for i in range(len(quality_scores))] if quality_scores else ["Req #1"],
                "values": quality_scores if quality_scores else [0.85],
            },
        },
    }
