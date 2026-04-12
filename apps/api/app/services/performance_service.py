from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Execution, PerformanceSnapshot, TradeIntent


def get_latest(db: Session) -> PerformanceSnapshot | None:
    q = select(PerformanceSnapshot).order_by(desc(PerformanceSnapshot.timestamp)).limit(1)
    return db.execute(q).scalar_one_or_none()


def seed_starting_performance(db: Session) -> PerformanceSnapshot:
    settings = get_settings()
    row = PerformanceSnapshot(
        timestamp=datetime.utcnow(),
        equity=float(settings.default_starting_equity),
        pnl_daily=0.0,
        pnl_total=0.0,
        drawdown=0.0,
        position_notional=0.0,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def set_open_position_notional(db: Session, position_notional: float) -> PerformanceSnapshot:
    """Narrow demo hook: pretend an existing book so risk room is tight (allow_with_reduction path)."""
    prev = get_latest(db)
    if prev is None:
        prev = seed_starting_performance(db)
    row = PerformanceSnapshot(
        timestamp=datetime.utcnow(),
        equity=float(prev.equity),
        pnl_daily=0.0,
        pnl_total=float(prev.pnl_total),
        drawdown=float(prev.drawdown),
        position_notional=float(position_notional),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def apply_execution_to_performance(db: Session, execution: Execution) -> PerformanceSnapshot:
    settings = get_settings()
    prev = get_latest(db)
    if prev is None:
        prev = seed_starting_performance(db)

    intent = db.get(TradeIntent, execution.intent_id)
    if intent is None or execution.status != "filled" or execution.fill_price is None or execution.fill_size is None:
        return prev

    notional = execution.fill_price * execution.fill_size
    fees = execution.fees
    prev_cash = prev.equity - prev.position_notional
    pos = prev.position_notional

    if intent.action.lower() == "buy":
        new_cash = prev_cash - notional - fees
        new_pos = pos + notional
    else:
        new_cash = prev_cash + notional - fees
        new_pos = max(0.0, pos - notional)

    new_equity = new_cash + new_pos
    pnl_total = new_equity - float(settings.default_starting_equity)

    peak = db.scalar(select(func.max(PerformanceSnapshot.equity)))
    peak = max(float(settings.default_starting_equity), peak or 0.0, new_equity)
    drawdown = max(0.0, peak - new_equity)

    row = PerformanceSnapshot(
        timestamp=datetime.utcnow(),
        equity=round(new_equity, 4),
        pnl_daily=round(new_equity - prev.equity, 4),
        pnl_total=round(pnl_total, 4),
        drawdown=round(drawdown, 4),
        position_notional=round(new_pos, 4),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
