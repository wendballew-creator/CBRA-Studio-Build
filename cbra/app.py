from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from cbra.engine import articulate, initialize_field_state, step_field
from cbra.models import FieldState, Stream

APP_TITLE = "CBRA Writing Support"
APP_VERSION = "0.2.0-field-prototype"

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
UI_INDEX = PROJECT_ROOT / "ui" / "index.html"
if not UI_INDEX.exists():
    fallback_ui = BASE_DIR / "ui" / "index.html"
    if fallback_ui.exists():
        UI_INDEX = fallback_ui

app = FastAPI(title=APP_TITLE, version=APP_VERSION)

# Simple in-memory session substrate for the field prototype
THREAD_FIELDS: Dict[str, FieldState] = {}


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


def _state_to_dict(state: FieldState) -> Dict[str, Any]:
    if is_dataclass(state):
        return asdict(state)
    return dict(state)


def _append_user_stream(state: FieldState, text: str) -> None:
    state.streams.append(
        Stream(
            stream_id="user_{0}".format(state.timestep + 1),
            kind="user_input",
            payload={"text": text},
            participation=1.0,
            persistence=0.8,
        )
    )


def _run_field_turn(state: FieldState, user_text: str) -> Dict[str, Any]:
    _append_user_stream(state, user_text)
    step_field(state, user_text)
    text = articulate(state)

    debug = {
        "field_signature": dict(state.field_signature),
        "field_values": asdict(state.field_values),
        "drift_flags": asdict(state.drift_flags),
        "timestep": state.timestep,
        "stream_count": len(state.streams),
        "streams": [asdict(s) for s in state.streams],
        "notes": dict(state.notes),
    }

    return {
        "text": text,
        "debug": debug,
        "field": _state_to_dict(state),
    }


@app.get("/", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
def ui() -> HTMLResponse:
    if not UI_INDEX.exists():
        return HTMLResponse(
            "<html><body><h1>UI not found</h1><p>ui/index.html is missing.</p></body></html>",
            status_code=404,
        )
    return HTMLResponse(UI_INDEX.read_text(encoding="utf-8", errors="replace"))


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "ok": True,
        "app": APP_TITLE,
        "version": APP_VERSION,
        "active_threads": len(THREAD_FIELDS),
    }


@app.post("/generate")
async def generate(req: GenerateRequest) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        state = initialize_field_state(req.user_text)
        result = _run_field_turn(state, req.user_text)
        return ok(
            request_id=request_id,
            thread_id=None,
            text=result["text"],
            debug=result["debug"] if req.mode == "debug" else None,
            data={"field": result["field"]},
        )
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))


@app.post("/chat/{thread_id}")
async def chat(thread_id: str, req: GenerateRequest) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        state = THREAD_FIELDS.get(thread_id)
        if state is None:
            state = initialize_field_state(req.user_text)
            THREAD_FIELDS[thread_id] = state

        result = _run_field_turn(state, req.user_text)

        return ok(
            request_id=request_id,
            thread_id=thread_id,
            text=result["text"],
            debug=result["debug"] if req.mode == "debug" else None,
            data={"field": result["field"]},
        )
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))


@app.get("/thread/{thread_id}")
def get_thread_route(thread_id: str) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        state = THREAD_FIELDS.get(thread_id)
        if state is None:
            return err(request_id=request_id, code="NOT_FOUND", message="Thread not found")
        return ok(
            request_id=request_id,
            thread_id=thread_id,
            text=None,
            debug=None,
            data={"field": _state_to_dict(state)},
        )
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))


@app.delete("/thread/{thread_id}")
def delete_thread_route(thread_id: str) -> Dict[str, Any]:
    request_id = str(uuid4())
    try:
        existed = thread_id in THREAD_FIELDS
        THREAD_FIELDS.pop(thread_id, None)
        return ok(
            request_id=request_id,
            thread_id=thread_id,
            text=None,
            debug=None,
            data={"deleted": existed},
        )
    except Exception as exc:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(exc))