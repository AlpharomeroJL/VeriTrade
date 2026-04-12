from __future__ import annotations

import os
import threading
import time
from datetime import datetime, timedelta
from typing import Any

from app.config import get_settings
from app.database import get_session_factory
from app.services import control_service, lane_service, pipeline_service

_lock = threading.Lock()
_enabled = False
_cadence_seconds = 15
_last_cycle_at: datetime | None = None
_next_cycle_at: datetime | None = None
_history: list[dict[str, Any]] = []
_MAX_HISTORY = 32


def _append_history(item: dict[str, Any]) -> None:
    global _history
    _history = [item, *_history][:_MAX_HISTORY]


def _outcome_from_result(res: dict[str, Any]) -> tuple[str, str]:
    if not res.get("ok"):
        return "error", str(res.get("error", "cycle_failed"))
    if res.get("skipped"):
        return "skipped", "Stand aside — no trade this cycle (hold / no-signal), not a hard safety block."
    if res.get("blocked"):
        return "blocked", "Risk router blocked the trade."
    if res.get("escalated"):
        return "review", "Escalated for manual review."
    verdict = str(res.get("verdict", ""))
    if verdict == "allow_with_reduction":
        return "reduced", "Allowed with reduction under policy limits."
    return "allowed", "Allowed and simulated in paper execution."


def _cycle_detail_technical(res: dict[str, Any]) -> str:
    parts: list[str] = []
    v = res.get("verdict")
    if v:
        parts.append(f"verdict={v}")
    exs = res.get("execution_status")
    if exs:
        parts.append(f"exec={exs}")
    lid = res.get("lane_id")
    if lid:
        parts.append(f"lane={lid}")
    return " · ".join(parts) if parts else "—"


def _cycle_detail(res: dict[str, Any], note: str) -> str:
    """Plain-English first — materially different voice for spot vs futures vs core pipeline."""
    lid = res.get("lane_id")
    verdict = str(res.get("verdict", "") or "")
    blocked = bool(res.get("blocked"))
    escalated = bool(res.get("escalated"))
    exs = str(res.get("execution_status") or "")
    if verdict == "skip" or res.get("skipped"):
        if lid == "futures_tactical":
            return (
                "Tactical futures (paper): stood aside — tape did not clear the tactical entry bar, so no simulated fill."
            )
        if lid == "spot_momentum":
            return (
                "Spot momentum (paper): stood aside — chop or weak alignment; this is a passive skip, not a hard risk stop."
            )
        return "Stood aside this cycle — passive no-trade while the tape is watched."
    if lid == "futures_tactical":
        if blocked:
            return (
                "Tactical futures (paper): no position opened. "
                "This lane uses a hotter, smaller playbook—tighter caps and quicker halts when the tape or gates disagree."
            )
        if escalated:
            return (
                "Tactical futures (paper): waiting on review. "
                "The futures gate wants clearer evidence before a simulated fill is acceptable."
            )
        if verdict == "allow_with_reduction":
            return (
                "Tactical futures (paper): we trimmed size, then ran a governed simulated trade. "
                "Exposure stays conservative because tactical risk is treated as sharper than spot."
            )
        return (
            "Tactical futures (paper): compact simulated round-trip under futures-style limits. "
            f"Simulator outcome: {exs or 'recorded'}."
        )
    if lid == "spot_momentum":
        if blocked:
            return (
                "Spot momentum (paper): no fill—safety stopped the path. "
                "This lane still refuses stale prices, volatility spikes, and churn so the book does not thrash."
            )
        if escalated:
            return (
                "Spot momentum (paper): paused for review. "
                "Momentum entries need enough confidence; the lane waits rather than forcing a trade."
            )
        if verdict == "allow_with_reduction":
            return (
                "Spot momentum (paper): approved a smaller slice so headroom and policy stay intact. "
                "Still a spot-style fill at the snapshot reference price."
            )
        return (
            "Spot momentum (paper): steadier trend-style simulated trade against the spot snapshot. "
            f"Simulator outcome: {exs or 'recorded'}."
        )
    if lid:
        lbl = str(res.get("lane_label") or "Lane")
        if blocked:
            return f"{lbl} (paper): no trade — risk stopped before commitment."
        return f"{lbl} (paper): {note}"
    return (
        f"Core demo pipeline (paper): {note} "
        "Single-loop MA-style path; stale/vol checks use the latest ingested snapshot."
    )


def _runner() -> None:
    global _last_cycle_at, _next_cycle_at
    while True:
        time.sleep(1)
        with _lock:
            enabled = _enabled
            next_at = _next_cycle_at
        if not enabled or next_at is None:
            continue
        now = datetime.utcnow()
        if now < next_at:
            continue
        factory = get_session_factory()
        db = factory()
        try:
            lanes = [l for l in lane_service.list_lanes(db) if l.get("status") == "running"]
            if lanes:
                res = lane_service.run_lane_once(db, lanes[0]["lane_id"])
            else:
                res = pipeline_service.run_strategy_cycle(db, ingest_market=True, force_step=False)
            out, note = _outcome_from_result(res)
            detail = _cycle_detail(res, note)
            detail_technical = _cycle_detail_technical(res)
            stamp = datetime.utcnow()
            with _lock:
                _last_cycle_at = stamp
                _next_cycle_at = stamp + timedelta(seconds=_cadence_seconds)
                _append_history(
                    {
                        "timestamp": stamp,
                        "outcome": out,
                        "verdict": res.get("verdict"),
                        "execution_status": res.get("execution_status"),
                        "note": note,
                        "lane_id": res.get("lane_id"),
                        "lane_label": res.get("lane_label"),
                        "detail": detail,
                        "detail_technical": detail_technical,
                    }
                )
        finally:
            db.close()


_thread_started = False


def ensure_runner_started() -> None:
    global _thread_started
    if os.environ.get("PYTEST") == "1":
        return
    if not get_settings().veritrade_autonomous_runner:
        return
    with _lock:
        if _thread_started:
            return
        t = threading.Thread(target=_runner, name="veritrade-autonomous-loop", daemon=True)
        t.start()
        _thread_started = True


def start_autonomous(cadence_seconds: int, *, set_system_running: bool = True) -> dict[str, Any]:
    global _enabled, _cadence_seconds, _next_cycle_at
    cadence = max(5, min(120, int(cadence_seconds)))
    if set_system_running:
        factory = get_session_factory()
        db = factory()
        try:
            control_service.set_mode(db, "running")
        finally:
            db.close()
    ensure_runner_started()
    with _lock:
        _enabled = True
        _cadence_seconds = cadence
        if _next_cycle_at is None:
            _next_cycle_at = datetime.utcnow()
    return get_status()


def stop_autonomous() -> dict[str, Any]:
    global _enabled, _next_cycle_at
    with _lock:
        _enabled = False
        _next_cycle_at = None
    return get_status()


def get_status() -> dict[str, Any]:
    with _lock:
        enabled = _enabled
        cadence = _cadence_seconds
        last = _last_cycle_at
        nxt = _next_cycle_at
    now = datetime.utcnow()
    secs = None
    if enabled and nxt is not None:
        secs = max(0, int((nxt - now).total_seconds()))
    return {
        "enabled": enabled,
        "cadence_seconds": cadence,
        "last_cycle_at": last,
        "next_cycle_at": nxt,
        "next_cycle_in_seconds": secs,
    }


def get_recent_history(limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        rows = list(_history[: max(1, min(limit, _MAX_HISTORY))])
    return rows
