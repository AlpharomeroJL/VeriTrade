from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import SystemControl


def get_or_create_control(db: Session) -> SystemControl:
    row = db.execute(select(SystemControl).limit(1)).scalar_one_or_none()
    if row is None:
        row = SystemControl(mode="stopped", manual_pause=False, no_trade=False)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def set_mode(db: Session, mode: str) -> SystemControl:
    ctrl = get_or_create_control(db)
    ctrl.mode = mode
    ctrl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ctrl)
    return ctrl


def set_manual_pause(db: Session, paused: bool) -> SystemControl:
    ctrl = get_or_create_control(db)
    ctrl.manual_pause = paused
    ctrl.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(ctrl)
    return ctrl
