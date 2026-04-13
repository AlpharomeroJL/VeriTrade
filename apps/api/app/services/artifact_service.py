import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.challenge.erc8004_artifact_validation_bridge import maybe_emit_validation_request_for_artifact
from app.config import get_settings
from app.models import Artifact

log = logging.getLogger(__name__)


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
    try:
        emit = maybe_emit_validation_request_for_artifact(
            settings,
            artifact_type=artifact_type,
            artifact_id=row.id,
            related_id=related_id,
            payload=payload,
            artifact_json_path=out_path,
        )
        if emit is not None and not emit.get("ok", True):
            log.debug("artifact validation emit result: %s", emit)
    except Exception as e:
        log.warning("artifact validation emit unexpected error (ignored): %s", e)
    return row
