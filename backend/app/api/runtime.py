from typing import Annotated, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.runtime_policy import load_runtime_policy, reset_runtime_policy, update_runtime_policy
from app.db.database import get_db
from app.services.audit_service import create_audit_log

router = APIRouter(tags=["runtime-policy"])


@router.get("/runtime-policy")
def runtime_policy_get() -> dict[str, object]:
    return {
        "policy": load_runtime_policy(),
        "security": {
            "arbitrary_code_execution": False,
            "eval_enabled": False,
            "allowed_keys_only": True,
            "note": "Dynamic Injection is validated runtime configuration.",
        },
    }


@router.put("/runtime-policy")
def runtime_policy_put(payload: dict[str, Any], db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    policy = update_runtime_policy(payload)
    create_audit_log(db, None, "Dynamic Injection", "runtime_policy_updated", "operator", "Runtime policy updated", policy)
    db.commit()
    return {"policy": policy, "status": "updated"}


@router.post("/runtime-policy/reset")
def runtime_policy_reset(db: Annotated[Session, Depends(get_db)]) -> dict[str, object]:
    policy = reset_runtime_policy()
    create_audit_log(db, None, "Dynamic Injection", "runtime_policy_reset", "operator", "Runtime policy reset", policy)
    db.commit()
    return {"policy": policy, "status": "reset"}
