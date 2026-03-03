from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any

from cbra_engine import run_cbra

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
app.mount("/ui", StaticFiles(directory=".", html=True), name="static")

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
        else:
            # Back-compat: attach a field if missing
            if not getattr(thread, "current_field_id", None):
                f = create_field(thread_id=thread_id)
                thread.current_field_id = f.id

        append_message(
            thread_id,
            Message(role="user", content=request.user_text, timestamp=datetime.utcnow()),
        )

        result = run_cbra(
            request.user_text,
            mode=request.mode,
            thread_id=thread_id,
            field_id=thread.current_field_id,
        )
        if "loopcycle" in result and isinstance(result["loopcycle"], dict):
            append_loopcycle(thread_id, LoopCycle(**result["loopcycle"]))
        # If drift detected, log DriftEvent
        lc = result.get("loopcycle") if isinstance(result.get("loopcycle"), dict) else None
        if lc and lc.get("drift_detected"):
            append_drift_event(
                thread_id,
                DriftEvent(
                    kind="DRIFT_DETECTED",
                    detected_at_stage="Articulation",
                    reintegration_stage=lc.get("reintegration_stage") or "Field Entry",
                    timestamp=datetime.utcnow(),
                ),
            )

        append_message(
            thread_id,
            Message(role="assistant", content=result["text"], timestamp=datetime.utcnow()),
        )

        return ok(
            request_id=request_id,
            thread_id=thread_id,
            text=result.get("text"),
            debug=result.get("debug"),
            data=None,
        )
    except Exception as e:
        return err(request_id=request_id, code="INTERNAL_ERROR", message=str(e))

@app.get("/thread/{thread_id}")
def read_thread(thread_id: str):
    request_id = str(uuid4())
    thread = get_thread(thread_id)
    if thread is None:
        return err(request_id=request_id, code="THREAD_NOT_FOUND", message="Thread not found")

    return ok(
        request_id=request_id,
        thread_id=thread_id,
        text=None,
        debug=None,
        data=thread.dict(),
    )

@app.get("/thread/{thread_id}/export")
def export_thread(thread_id: str):
    request_id = str(uuid4())
    thread = get_thread(thread_id)
    if thread is None:
        return err(request_id=request_id, code="THREAD_NOT_FOUND", message="Thread not found")

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
        timestamp=datetime.utcnow()
    ))

    result = run_cbra(user_text=combined, mode=mode)

    append_message(thread_id, Message(
        role="assistant",
        content=result.get("text", ""),
        timestamp=datetime.utcnow()
    ))

    if "loopcycle" in result and isinstance(result["loopcycle"], dict):
        append_loopcycle(thread_id, LoopCycle(**result["loopcycle"]))

    return {
        "request_id": str(uuid4()),
        "thread_id": thread_id,
        "text": result.get("text", ""),
        "debug": result.get("debug"),
        "data": None,
    }
