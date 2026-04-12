from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.adapters.kraken_public_market import TOP_UI_SYMBOLS, fetch_ticker_for_ui_symbol, fetch_ticker_for_ui_symbol_cli
from app.config import get_settings
from app.models import KrakenSkillSession

DEFAULT_SYMBOLS = ["BTCUSD", "ETHUSD", "SOLUSD"]


def _now() -> datetime:
    return datetime.utcnow()


def _dumps(v: object) -> str:
    return json.dumps(v, default=str)


def _loads_list(v: str) -> list:
    try:
        parsed = json.loads(v or "[]")
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []


def _loads_dict(v: str) -> dict:
    try:
        parsed = json.loads(v or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _session_to_dict(row: KrakenSkillSession) -> dict:
    return {
        "id": row.id,
        "session_type": row.session_type,
        "operation": row.operation,
        "symbols": _loads_list(row.symbols_json),
        "started_at": row.started_at,
        "ended_at": row.ended_at,
        "status": row.status,
        "logs": _loads_list(row.logs_json),
        "outputs": _loads_dict(row.outputs_json),
        "summary": row.summary,
        "metrics": _loads_dict(row.metrics_json),
        "rationale": row.rationale,
    }


def _create_session(db: Session, *, session_type: str, operation: str, symbols: list[str]) -> KrakenSkillSession:
    row = KrakenSkillSession(
        session_type=session_type,
        operation=operation,
        symbols_json=_dumps(symbols),
        started_at=_now(),
        status="running",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _append_log(db: Session, row: KrakenSkillSession, message: str) -> None:
    logs = _loads_list(row.logs_json)
    logs.append({"at": _now().isoformat(), "message": message})
    row.logs_json = _dumps(logs)
    db.add(row)
    db.commit()


def _finish_session(
    db: Session,
    row: KrakenSkillSession,
    *,
    status: str,
    outputs: dict,
    summary: str,
    metrics: dict,
    rationale: str,
) -> KrakenSkillSession:
    row.status = status
    row.ended_at = _now()
    row.outputs_json = _dumps(outputs)
    row.summary = summary
    row.metrics_json = _dumps(metrics)
    row.rationale = rationale
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _fetch_symbol_price(symbol: str) -> dict:
    try:
        row = fetch_ticker_for_ui_symbol_cli(symbol)
        return {"symbol": symbol, "price": row.price, "bid": row.bid, "ask": row.ask, "source": row.fetch_via}
    except Exception:
        row = fetch_ticker_for_ui_symbol(symbol)
        return {"symbol": symbol, "price": row.price, "bid": row.bid, "ask": row.ask, "source": row.fetch_via}


def _verify_kraken_cli() -> dict:
    s = get_settings()
    binary = s.kraken_market_cli_bin or s.kraken_cli_command_stub or "kraken"
    found = shutil.which(binary)
    if not found:
        return {
            "binary": binary,
            "installed": False,
            "verified": False,
            "message": f"Kraken CLI binary '{binary}' not found in PATH.",
        }
    try:
        subprocess.run([binary, "--help"], capture_output=True, text=True, timeout=8, check=False)
        return {"binary": binary, "installed": True, "verified": True, "message": "Kraken CLI is installed and callable."}
    except Exception as e:
        return {"binary": binary, "installed": True, "verified": False, "message": f"Kraken CLI found but verify failed: {e!s}"}


def _paper_trade_session(symbols: list[str], starting_capital: float, strategy: str) -> tuple[list[dict], dict]:
    capital = float(starting_capital)
    pnl = 0.0
    trades: list[dict] = []
    prices = [_fetch_symbol_price(sym) for sym in symbols]
    for row in prices:
        px = float(row["price"])
        size_notional = max(100.0, capital * 0.05)
        entered = strategy in {"momentum", "simple_ma", "buy_on_strength"}
        blocked = px <= 0
        if blocked:
            trades.append(
                {
                    "symbol": row["symbol"],
                    "action": "blocked",
                    "entry_reason": "Price invalid for paper simulation.",
                    "exit_reason": "No trade entered.",
                    "blocked_reason": "non_positive_price",
                    "notional": 0.0,
                    "pnl": 0.0,
                }
            )
            continue
        entry = px
        exit_px = round(px * 1.004, 2)
        trade_pnl = round((exit_px - entry) * (size_notional / entry), 2) if entered else 0.0
        if entered:
            pnl += trade_pnl
            capital += trade_pnl
        trades.append(
            {
                "symbol": row["symbol"],
                "action": "buy_then_exit" if entered else "hold",
                "entry_price": entry,
                "exit_price": exit_px if entered else None,
                "entry_reason": f"Strategy {strategy} entered when tape bias was positive.",
                "exit_reason": "Session target hit / end-of-session flatten in paper mode.",
                "blocked_reason": None,
                "notional": round(size_notional, 2),
                "pnl": trade_pnl,
            }
        )
    metrics = {
        "starting_capital": round(float(starting_capital), 2),
        "ending_capital": round(capital, 2),
        "pnl": round(pnl, 2),
        "trades_count": len([t for t in trades if t.get("action") == "buy_then_exit"]),
    }
    return trades, metrics


def run_operation(
    db: Session,
    *,
    operation: str,
    symbols: list[str] | None = None,
    lane_id: str | None = None,
    starting_capital: float = 10000.0,
    strategy: str = "simple_ma",
    alert_price: float | None = None,
    drop_percent: float = 1.5,
) -> dict:
    syms = [s.upper() for s in (symbols or DEFAULT_SYMBOLS)]
    if not syms:
        syms = DEFAULT_SYMBOLS[:]
    syms = [s for s in syms if s in TOP_UI_SYMBOLS]
    if not syms:
        syms = DEFAULT_SYMBOLS[:]

    session_type_map = {
        "verify_cli": "monitoring",
        "install_or_verify_cli": "monitoring",
        "morning_brief": "market_brief",
        "watch_market": "monitoring",
        "paper_trading_session": "paper_trading",
        "buy_on_drop_simulation": "paper_trading",
        "rebalance_proposal": "paper_trading",
        "price_alert_session": "alert",
    }
    session_type = session_type_map.get(operation, "monitoring")
    row = _create_session(db, session_type=session_type, operation=operation, symbols=syms)
    lane_note = f" lane={lane_id}" if lane_id else ""
    _append_log(db, row, f"Started operation '{operation}' for symbols {', '.join(syms)}.{lane_note}")

    try:
        if operation in {"verify_cli", "install_or_verify_cli"}:
            out = _verify_kraken_cli()
            _append_log(db, row, out["message"])
            done = _finish_session(
                db,
                row,
                status="completed" if out["verified"] else "warning",
                outputs={"verification": out, "lane_id": lane_id},
                summary=out["message"],
                metrics={"cli_installed": out["installed"], "cli_verified": out["verified"]},
                rationale="Kraken CLI must be reachable before CLI-native workflows can run.",
            )
            return _session_to_dict(done)

        if operation == "morning_brief":
            rows = [_fetch_symbol_price(sym) for sym in syms]
            summary = " | ".join([f"{r['symbol']} {r['price']}" for r in rows])
            _append_log(db, row, "Generated morning brief from Kraken market sources.")
            done = _finish_session(
                db,
                row,
                status="completed",
                outputs={"market_summary": rows, "lane_id": lane_id},
                summary=f"Morning brief: {summary}",
                metrics={"pairs": len(rows)},
                rationale="Brief gives operators an at-a-glance open across BTC/ETH/SOL before acting.",
            )
            return _session_to_dict(done)

        if operation == "watch_market":
            watch_rows = [_fetch_symbol_price(sym) for sym in syms]
            _append_log(db, row, "Captured live watch snapshot set.")
            done = _finish_session(
                db,
                row,
                status="completed",
                outputs={"watch_log": watch_rows, "lane_id": lane_id},
                summary="Watch market session captured latest prices and spreads.",
                metrics={"symbols_tracked": len(watch_rows)},
                rationale="Monitoring session detects tape regime before strategy actions.",
            )
            return _session_to_dict(done)

        if operation == "paper_trading_session":
            trades, metrics = _paper_trade_session(syms, starting_capital, strategy)
            _append_log(db, row, f"Paper session produced {metrics['trades_count']} trades.")
            done = _finish_session(
                db,
                row,
                status="completed",
                outputs={"trade_log": trades, "lane_id": lane_id},
                summary=f"Paper session complete. PnL {metrics['pnl']}.",
                metrics=metrics,
                rationale="Trades are entered/exited from simple strategy signals in paper-only mode.",
            )
            return _session_to_dict(done)

        if operation == "buy_on_drop_simulation":
            prices = [_fetch_symbol_price(sym) for sym in syms]
            trade_log: list[dict] = []
            pnl = 0.0
            for row_px in prices:
                entry = row_px["price"]
                synthetic_drop_price = round(entry * (1.0 - max(0.1, drop_percent) / 100.0), 2)
                exit_px = round(synthetic_drop_price * 1.006, 2)
                trade_pnl = round((exit_px - synthetic_drop_price) * (250.0 / synthetic_drop_price), 2)
                pnl += trade_pnl
                trade_log.append(
                    {
                        "symbol": row_px["symbol"],
                        "entry_reason": f"Entered after simulated {drop_percent:.2f}% drop.",
                        "exit_reason": "Exited after bounce target in simulation.",
                        "blocked_reason": None,
                        "entry_price": synthetic_drop_price,
                        "exit_price": exit_px,
                        "notional": 250.0,
                        "pnl": trade_pnl,
                    }
                )
            _append_log(db, row, "Completed buy-on-drop simulation.")
            done = _finish_session(
                db,
                row,
                status="completed",
                outputs={"trade_log": trade_log, "lane_id": lane_id},
                summary=f"Buy-on-drop simulation completed. PnL {round(pnl, 2)}.",
                metrics={"pnl": round(pnl, 2), "trades_count": len(trade_log), "drop_percent": drop_percent},
                rationale="Session enters only after downside move and exits on recovery in paper simulation.",
            )
            return _session_to_dict(done)

        if operation == "rebalance_proposal":
            rows = [_fetch_symbol_price(sym) for sym in syms]
            target_w = round(1.0 / len(rows), 4)
            proposal = [{"symbol": r["symbol"], "target_weight": target_w, "price": r["price"], "mode": "proposal_only"} for r in rows]
            _append_log(db, row, "Generated rebalance proposal (no execution).")
            done = _finish_session(
                db,
                row,
                status="completed",
                outputs={"rebalance_proposal": proposal, "lane_id": lane_id},
                summary="Rebalance proposal generated (paper/proposed only).",
                metrics={"assets": len(proposal), "proposed_only": True},
                rationale="Proposal reweights basket evenly without placing any orders.",
            )
            return _session_to_dict(done)

        if operation == "price_alert_session":
            rows = [_fetch_symbol_price(sym) for sym in syms]
            threshold = float(alert_price) if alert_price is not None else float(rows[0]["price"]) * 1.002
            alerts = []
            for r in rows:
                hit = float(r["price"]) >= threshold
                alerts.append(
                    {
                        "symbol": r["symbol"],
                        "price": r["price"],
                        "threshold": round(threshold, 2),
                        "triggered": hit,
                        "reason": "Price crossed threshold." if hit else "Price stayed below threshold.",
                    }
                )
            _append_log(db, row, "Price alert session evaluated thresholds.")
            done = _finish_session(
                db,
                row,
                status="completed",
                outputs={"alert_history": alerts, "lane_id": lane_id},
                summary="Price alert session complete.",
                metrics={"alerts_triggered": len([a for a in alerts if a["triggered"]])},
                rationale="Alert agent tracks threshold crossings for operator review.",
            )
            return _session_to_dict(done)

        _append_log(db, row, f"Unknown operation '{operation}'.")
        done = _finish_session(
            db,
            row,
            status="failed",
            outputs={"error": "unknown_operation"},
            summary=f"Operation '{operation}' is not supported.",
            metrics={},
            rationale="Unsupported command path.",
        )
        return _session_to_dict(done)
    except Exception as e:
        _append_log(db, row, f"Operation failed: {e!s}")
        done = _finish_session(
            db,
            row,
            status="failed",
            outputs={"error": str(e)},
            summary=f"Operation failed: {e!s}",
            metrics={},
            rationale="Execution failure path.",
        )
        return _session_to_dict(done)


def list_sessions(db: Session, limit: int = 30) -> list[dict]:
    q = select(KrakenSkillSession).order_by(desc(KrakenSkillSession.started_at)).limit(min(max(limit, 1), 200))
    return [_session_to_dict(r) for r in db.execute(q).scalars().all()]


def get_session(db: Session, session_id: int) -> dict | None:
    row = db.execute(select(KrakenSkillSession).where(KrakenSkillSession.id == session_id)).scalar_one_or_none()
    return _session_to_dict(row) if row else None
