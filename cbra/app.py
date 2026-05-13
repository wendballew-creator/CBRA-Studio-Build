from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from cbra.engine import run_cbra
from cbra.models import DriftEvent, LoopCycle, Message
from cbra.store import (
    append_drift_event,
    append_loopcycle,
    append_message,
    clear_active_attachment,
    export_thread_markdown,
    get_field,
    get_thread,
    set_active_attachment,
)

APP_TITLE = "CBRA Writing Support"
APP_VERSION = "0.1.0"

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
UI_INDEX = PROJECT_ROOT / "ui" / "index.html"
if not UI_INDEX.exists():
    fallback_ui = BASE_DIR / "ui" / "index.html"
    if fallback_ui.exists():
        UI_INDEX = fallback_ui


class GenerateRequest(BaseModel):
    user_text: str = Field(..., min_length=1)
    mode: Literal["production", "debug"] = "production"


def ok(
    *,
    request_id: str,
    thread_id: Optional[str],
    text: Optional[str],
    debug: Optional[Dict[str, Any]],
    data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "request_id": request_id,
        "thread_id": thread_id,
        "text": text,
        "debug": debug,
        "data": data,
    }


def err(*, request_id: str, code: str, message: str) -> Dict[str, Any]:
    return {
        "request_id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }


app = FastAPI(title=APP_TITLE, version=APP_VERSION)


def _coerce_loopcycle(result: Dict[str, Any]) -> LoopCycle:
    loopcycle_payload = dict(result.get("loopcycle") or {})
    return LoopCycle.model_validate(loopcycle_payload)


def _coerce_debug_drift(result: Dict[str, Any]) -> Optional[DriftEvent]:
    debug = result.get("debug") or {}
    if not debug or not debug.get("drift_detected"):
        return None
    return DriftEvent(
        kind=str(debug.get("drift_kind") or "unknown_drift"),
        severity="low",
        detected_at_stage=str(debug.get("drift_kind") or "unknown"),
        reintegration_stage=debug.get("reintegration_stage"),
    )


def _attachment_sources_from_thread(thread: Any) -> list[str]:
    sources: list[str] = []
    active_name = getattr(thread, "active_attachment_name", None)
    active_text = getattr(thread, "active_attachment_text", None)
    if active_name and active_text:
        sources.append(f"ATTACHMENT ({active_name}):\n{active_text}")
    for item in getattr(thread, "active_attachments", []) or []:
        name = str(item.get("name", "")).strip()
        text = str(item.get("text", "") or "")
        if name and text:
            source = f"ATTACHMENT ({name}):\n{text}"
            if source not in sources:
                sources.append(source)
    return sources


@app.get("/", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
def ui() -> HTMLResponse:
    if not UI_INDEX.exists():
        return HTMLResponse(
            "<html><body><h1>UI not found</h1><p>ui/index.html is missing.</p></body></html>",
            status_code=404,
        )
    return HTMLResponse(UI_INDEX.read_text(encoding="utf-8", errors="replace"))


@app.post("/generate")
async def generate(req: GenerateRequest) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        result = run_cbra(req.user_text, mode=req.mode)
        return ok(
            request_id=request_id,
            thread_id=None,
            text=result.get("text"),
            debug=result.get("debug"),
            data={"loopcycle": result.get("loopcycle")},
        )
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))


@app.post("/chat/{thread_id}")
async def chat(thread_id: str, req: GenerateRequest) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        thread = get_thread(thread_id)
        sources = _attachment_sources_from_thread(thread) if thread is not None else []

        append_message(thread_id, Message(role="user", content=req.user_text))
        current_field_id = getattr(thread, "current_field_id", None) if thread is not None else None

        result = run_cbra(
            req.user_text,
            mode=req.mode,
            thread_id=thread_id,
            field_id=current_field_id,
            sources=sources,
        )

        append_message(thread_id, Message(role="assistant", content=str(result.get("text") or "")))

        loopcycle = _coerce_loopcycle(result)
        append_loopcycle(thread_id, loopcycle)

        drift = _coerce_debug_drift(result)
        if drift is not None:
            append_drift_event(thread_id, drift)

        return ok(
            request_id=request_id,
            thread_id=thread_id,
            text=result.get("text"),
            debug=result.get("debug"),
            data={"loopcycle": result.get("loopcycle")},
        )
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))


@app.get("/thread/{thread_id}")
def get_thread_route(thread_id: str) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        thread = get_thread(thread_id)
        if thread is None:
            return err(request_id=request_id, code="NOT_FOUND", message="Thread not found")
        return ok(
            request_id=request_id,
            thread_id=thread_id,
            text=None,
            debug=None,
            data={"thread": thread.model_dump()},
        )
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))


@app.get("/thread/{thread_id}/export")
def export_thread(thread_id: str):
    export_path = export_thread_markdown(thread_id)
    return FileResponse(
        path=str(export_path),
        media_type="text/markdown",
        filename=Path(export_path).name,
    )


@app.get("/field/{field_id}")
def read_field(field_id: str) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        field = get_field(field_id)
        if field is None:
            return err(request_id=request_id, code="NOT_FOUND", message="Field not found")
        payload = field.model_dump() if hasattr(field, "model_dump") else dict(field)
        return ok(
            request_id=request_id,
            thread_id=payload.get("thread_id"),
            text=None,
            debug=None,
            data={"field": payload},
        )
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))


@app.post("/chat/{thread_id}/file")
async def chat_with_file(
    thread_id: str,
    user_text: str = Form(""),
    mode: Literal["production", "debug"] = Form("production"),
    upload: Optional[UploadFile] = File(None),
    uploads: Optional[list[UploadFile]] = File(None),
) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        saved_attachments = []

        all_uploads: list[UploadFile] = []
        if upload is not None:
            all_uploads.append(upload)
        if uploads:
            all_uploads.extend(uploads)

        for item in all_uploads:
            raw = await item.read()
            text = raw.decode("utf-8", errors="replace")
            set_active_attachment(thread_id, item.filename or "attachment.txt", text)
            saved_attachments.append(
                {
                    "name": item.filename or "attachment.txt",
                    "chars": len(text),
                }
            )

        if not user_text.strip():
            return ok(
                request_id=request_id,
                thread_id=thread_id,
                text=None,
                debug=None,
                data={"attachments": saved_attachments},
            )

        req = GenerateRequest(user_text=user_text, mode=mode)
        return await chat(thread_id, req)
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))


@app.post("/thread/{thread_id}/attachments/clear")
def clear_active_attachment_route(thread_id: str) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        clear_active_attachment(thread_id)
        return ok(
            request_id=request_id,
            thread_id=thread_id,
            text=None,
            debug=None,
            data={"cleared": True},
        )
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))
