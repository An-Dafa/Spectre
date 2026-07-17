from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.engine import process_screen_text, process_visual, supported_flow


app = FastAPI(
    title="Spectre Backend",
    version="0.1.0",
    description="Spectre middleware backend: unsafe source in, safe destination out.",
)


class VisualFlowRequest(BaseModel):
    enabled_rules: list[str] | None = Field(default=None)


class ScreenShieldRequest(BaseModel):
    text: str
    enabled_rules: list[str] | None = Field(default=None)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"app": "Spectre", "status": "ok"}


@app.get("/api/flow")
def flow() -> dict[str, Any]:
    return supported_flow()


@app.post("/api/kyc/process")
def enterprise_kyc(request: VisualFlowRequest) -> dict[str, Any]:
    return _run_visual("enterprise_kyc", request.enabled_rules)


@app.post("/api/live/frame")
def liveshield(request: VisualFlowRequest) -> dict[str, Any]:
    return _run_visual("liveshield", request.enabled_rules)


@app.post("/api/screen/redact")
def screen_shield(request: ScreenShieldRequest) -> dict[str, Any]:
    try:
        return process_screen_text(request.text, request.enabled_rules)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _run_visual(track: str, enabled_rules: list[str] | None) -> dict[str, Any]:
    try:
        return process_visual(track, enabled_rules)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
