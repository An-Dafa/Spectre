from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.services.audit_service import list_audit_logs

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
def get_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    record_id: str | None = None,
    zone: str | None = None,
    event_type: str | None = None,
) -> dict[str, object]:
    logs = list_audit_logs(db=db, limit=limit, record_id=record_id, zone=zone, event_type=event_type)
    return {"logs": logs, "count": len(logs), "filters": {"limit": limit, "record_id": record_id, "zone": zone, "event_type": event_type}}
