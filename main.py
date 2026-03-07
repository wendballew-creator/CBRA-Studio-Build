from __future__ import annotations

from dotenv import load_dotenv, find_dotenv
import os

# Load .env from current working directory (reliable under uvicorn reload)
dotenv_path = find_dotenv(usecwd=True)
load_dotenv(dotenv_path, override=True)

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any

from cbra_engine import run_cbra
from cbra.compression import enforce_fieldartifact_compression

from uuid import uuid4
from datetime import datetime

from cbra.models import Message, LoopCycle, DriftEvent
from cbra.store import (
    create_thread,
    get_thread,
    append_message,
    append_loopcycle,
    append_drift_event,
    get_field,
    create_field,
)

app = FastAPI(title="CBRA Writing Support")
app.mount("/ui", StaticFiles(directory="ui", html=True), name="static")

def ok(*, request_id: str, thread_id: Optional[str], text: Optional[str] = None, debug: Any = None, data: Any = None):
    return {
        "request_id": request_id,
        "thread_id": thread_id,
        "text": text,
        "debug": debug,
        "data": data,
    }


def err(*, request_id: str, code: str, message: str):
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }

class GenerateRequest(BaseModel):
    user_text: str = Field(..., min_length=1)
    mode: Literal["production", "debug"] = "production"

@app.post("/generate")
async def generate(req: GenerateRequest):
    request_id = str(uuid4())
    try:
        result = run_cbra(req.user_text, mode=req.mode)
        return ok(
            request_id=request_id,
            thread_id=None,
            text=result.get("text"),
            debug=result.get("debug"),
            data=None,
        )
    except Exception as e:
        # Keep it structured (no raw stack trace in response)
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(e))

@app.post("/chat/{thread_id}")
def chat(thread_id: str, request: GenerateRequest):
    request_id = str(uuid4())
    try:
        thread = get_thread(thread_id)
        if thread is None:
            thread = create_thread(thread_id)

        append_message(
            thread_id,
            Message(role="user", content=request.user_text),
        )

        result = run_cbra(
            request.user_text,
            mode=request.mode,
            thread_id=thread_id,
            field_id=thread.current_field_id,
        )
        if "loopcycle" in result and isinstance(result["loopcycle"], dict):
            
            # --- Compression enforcement (FieldArtifact) ---
            # loopcycle payload is the FieldArtifact dict itself; enforce compression on it directly.
            if isinstance(result, dict) and isinstance(result.get("loopcycle"), dict):
                enforced_fa, _compression_violations = enforce_fieldartifact_compression(result["loopcycle"])
                result["loopcycle"] = enforced_fa
            append_loopcycle(thread_id, LoopCycle(**result["loopcycle"]))
        # If drift detected, log DriftEvent
        lc = result.get("loopcycle") if isinstance(result.get("loopcycle"), dict) else None
        if lc and lc.get("drift_detected"):
            drift_notes = lc.get("notes") if isinstance(lc.get("notes"), dict) else {}
            reintegration_target = drift_notes.get("reintegration_target") or lc.get("reintegration_stage") or "Field Entry"
            detected_at_stage = drift_notes.get("detected_at_stage") or "Articulation"
            reintegration_stage = drift_notes.get("reintegration_stage") or lc.get("reintegration_stage")

            last_event = thread.drift_events[-1] if getattr(thread, "drift_events", None) else None
            is_duplicate = (
                last_event is not None
                and last_event.kind == "DRIFT_DETECTED"
                and last_event.reintegration_target == reintegration_target
                and last_event.detected_at_stage == detected_at_stage
                and last_event.reintegration_stage == reintegration_stage
            )

            if not is_duplicate:
                append_drift_event(
                    thread_id,
                    DriftEvent(
                        kind="DRIFT_DETECTED",
                        severity="low",
                        reintegration_target=reintegration_target,
                        detected_at_stage=detected_at_stage,
                        reintegration_stage=reintegration_stage,
                        notes=f"Drift detected during {detected_at_stage} stage.",
                    ),
                )

            append_message(
                thread_id,
                Message(role="assistant", content=result["text"]),
            )

        return result
    except Exception as e:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(e))

@app.get("/thread/{thread_id}")
def get_thread_route(thread_id: str):
    request_id = str(uuid4())

    thread = get_thread(thread_id)
    if thread is None:
        thread = create_thread(thread_id)

    return ok(
        request_id=request_id,
        thread_id=thread.id,
        text=None,
        debug=None,
        data=thread.model_dump(),
    )

@app.get("/thread/{thread_id}/export")
def export_thread(thread_id: str):
    request_id = str(uuid4())

    return ok(
        request_id=request_id,
        thread_id=thread_id,
        text=None,
        debug=None,
        data=thread.dict(),
    )
# ------------------------------
# Attachment Support (.docx, .txt, .md)
# ------------------------------

from fastapi import UploadFile, File
import io
from docx import Document

def _extract_text_from_upload(upload: UploadFile) -> str:
    name = (upload.filename or "").lower()
    data = upload.file.read()

    # txt / md
    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="replace")

    # docx
    if name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        parts = []
        for p in doc.paragraphs:
            t = (p.text or "").strip()
            if t:
                parts.append(t)
        return "\n".join(parts)

    raise HTTPException(status_code=400, detail="Unsupported file type. Use .docx, .txt, or .md")

@app.get("/field/{field_id}")
def read_field(field_id: str):
    request_id = str(uuid4())
    field = get_field(field_id)
    if field is None:
        return err(request_id=request_id, code="FIELD_NOT_FOUND", message="Field not found")
    return ok(
        request_id=request_id,
        thread_id=field.thread_id,
        text=None,
        debug=None,
        data=field.dict(),
    )

@app.post("/chat/{thread_id}/file")
def chat_with_file(
    thread_id: str,
    user_text: str = "",
    mode: Literal["production", "debug"] = "production",
    upload: UploadFile = File(...)
):
    thread = get_thread(thread_id) or create_thread(thread_id)

    doc_text = _extract_text_from_upload(upload)

    MAX_CHARS = 25000
    if len(doc_text) > MAX_CHARS:
        doc_text = doc_text[:MAX_CHARS] + "\n\n[TRUNCATED]"

    combined = (user_text or "").strip()
    if combined:
        combined += "\n\n"
    combined += f"ATTACHMENT ({upload.filename}):\n{doc_text}"

    append_message(thread_id, Message(
        role="user",
        content=f"{user_text}\n\n[Attached: {upload.filename}]",
    ))

    result = run_cbra(user_text=combined, mode=mode)

    append_message(thread_id, Message(
        role="assistant",
        content=result.get("text", ""),
    ))

    if "loopcycle" in result and isinstance(result["loopcycle"], dict):

        # --- Compression enforcement (FieldArtifact) ---
        # loopcycle payload is the FieldArtifact/LoopCycle-shaped dict itself; enforce directly.
        if isinstance(result, dict) and isinstance(result.get("loopcycle"), dict):
            enforced_fa, _compression_violations = enforce_fieldartifact_compression(result["loopcycle"])
            result["loopcycle"] = enforced_fa

        append_loopcycle(thread_id, LoopCycle(**result["loopcycle"]))

    return {
        "request_id": str(uuid4()),
        "thread_id": thread_id,
        "text": result.get("text", ""),
        "debug": result.get("debug"),
        "loopcycle": result.get("loopcycle"),
        "data": None,
    }
