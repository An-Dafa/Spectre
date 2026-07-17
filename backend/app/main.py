from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit, crypto, government, live, redaction, runtime, storage, system
from app.ai.runtime import detector
from app.core.config import get_settings
from app.db.database import init_db, session_scope
from app.services.vault_service import ensure_active_vault_key

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Spectre visual privacy and safety middleware API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with session_scope() as db:
        ensure_active_vault_key(db)
    detector.load()
    if not detector.loaded:
        raise RuntimeError(f"Failed to load detection model: {detector.load_error or 'unknown error'}")


@app.get("/")
def root() -> dict[str, str]:
    return {"app": settings.app_name, "docs": "/docs", "health": "/api/health"}


app.include_router(system.router, prefix="/api")
app.include_router(redaction.router, prefix="/api")
app.include_router(live.router, prefix="/api")
app.include_router(storage.router, prefix="/api")
app.include_router(crypto.router, prefix="/api")
app.include_router(runtime.router, prefix="/api")
app.include_router(government.router, prefix="/api")
app.include_router(audit.router, prefix="/api")

