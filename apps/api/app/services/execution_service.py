from datetime import datetime

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Execution, TradeIntent


def assert_paper_only() -> None:
    s = get_settings()
    if s.allow_real_orders or s.enable_live_trading or s.execution_provider.lower() != "paper":
        raise RuntimeError("Real execution disabled; paper only.")


def simulate_execution(db: Session, intent: TradeIntent, mark_price: float) -> Execution:
    assert_paper_only()
    if intent.approved_size <= 0:
        ex = Execution(
            intent_id=intent.id,
            venue="paper",
            order_type="market",
            status="rejected",
            fill_price=None,
            fill_size=None,
            fees=0.0,
            message="Zero approved size",
            created_at=datetime.utcnow(),
        )
        db.add(ex)
        db.commit()
        db.refresh(ex)
        return ex

    fill_price = mark_price
    fill_size = round(intent.approved_size / fill_price, 8) if fill_price else 0.0
    fee = round(intent.approved_size * 0.0005, 4)
    ex = Execution(
        intent_id=intent.id,
        venue="paper",
        order_type="market",
        status="filled",
        fill_price=fill_price,
        fill_size=fill_size,
        fees=fee,
        message="Paper fill simulated",
        created_at=datetime.utcnow(),
    )
    db.add(ex)
    intent.status = "executed"
    db.add(intent)
    db.commit()
    db.refresh(ex)
    return ex
