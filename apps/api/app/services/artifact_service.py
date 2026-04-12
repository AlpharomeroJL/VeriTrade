import json
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Artifact


def write_artifact(
    db: Session,
    artifact_type: str,
    related_id: str,
    payload: dict,
    status: str = "recorded",
) -> Artifact:
    summary = json.dumps(payload, default=str)[:4000]
    row = Artifact(
        artifact_type=artifact_type,
        related_id=related_id,
        timestamp=datetime.utcnow(),
        status=status,
        payload_summary=summary,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    settings = get_settings()
    Path(settings.artifacts_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(settings.artifacts_dir) / f"{artifact_type}_{row.id}.json"
    out_path.write_text(
        json.dumps({"type": artifact_type, "related_id": related_id, "payload": payload}, indent=2, default=str),
        encoding="utf-8",
    )
    return row
