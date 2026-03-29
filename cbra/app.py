from __future__ import annotations

from dotenv import load_dotenv, find_dotenv
import os
import io
from uuid import uuid4
from typing import Optional, Literal, Any, List, Dict

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from docx import Document
from pypdf import PdfReader

from cbra.engine import run_cbra

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

# Load .env from current working directory (reliable under uvicorn reload)
dotenv_path = find_dotenv(usecwd=True)
load_dotenv(dotenv_path, override=True)

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


def _get_active_attachments(thread) -> List[Dict[str, Any]]:
    attachments = getattr(thread, "active_attachments", None) or []
    normalized: List[Dict[str, Any]] = []
    for item in attachments:
        if isinstance(item, dict):
            text = str(item.get("text", "") or "")
            name = str(item.get("name", "attachment") or "attachment")
            media_type = item.get("media_type")
            if text:
                normalized.append({
                    "name": name,
                    "text": text,
                    "media_type": media_type,
                    "chars": len(text),
                })
    if not normalized:
        legacy_name = getattr(thread, "active_attachment_name", None)
        legacy_text = getattr(thread, "active_attachment_text", None)
        if legacy_text:
            normalized.append({
                "name": legacy_name or "attachment",
                "text": legacy_text,
                "media_type": None,
                "chars": len(legacy_text),
            })
    return normalized


def _set_active_attachments(thread, attachments: List[Dict[str, Any]]) -> None:
    thread.active_attachments = attachments
    if attachments:
        thread.active_attachment_name = attachments[0]["name"]
        thread.active_attachment_text = attachments[0]["text"]
    else:
        thread.active_attachment_name = None
        thread.active_attachment_text = None


def _clear_active_attachments(thread) -> None:
    thread.active_attachments = []
    thread.active_attachment_name = None
    thread.active_attachment_text = None


def _active_attachment_names(thread) -> List[str]:
    return [item["name"] for item in _get_active_attachments(thread)]


def _active_attachment_sources(thread) -> Optional[list[str]]:
    attachments = _get_active_attachments(thread)
    if not attachments:
        return None
    return [f"ATTACHMENT ({item['name']}):\n{item['text']}" for item in attachments]


def _combined_attachment_block(thread) -> str:
    sources = _active_attachment_sources(thread) or []
    return "\n\n".join(sources)


def _inject_attachment_metadata(result: Dict[str, Any], thread) -> None:
    names = _active_attachment_names(thread)
    payload = {
        "active_attachment_count": len(names),
        "active_attachment_names": names,
        "active_attachment_present": bool(names),
    }
    if isinstance(result.get("debug"), dict):
        result["debug"]["attachments"] = payload
    if isinstance(result.get("loopcycle"), dict):
        notes = result["loopcycle"].setdefault("notes", {})
        if isinstance(notes, dict):
            notes["active_attachment_count"] = len(names)
            notes["active_attachment_names"] = names


def _extract_text_from_upload(upload: UploadFile) -> str:
    name = (upload.filename or "").lower()
    data = upload.file.read()

    if name.endswith(".txt") or name.endswith(".md"):
        return data.decode("utf-8", errors="replace")

    if name.endswith(".docx"):
        doc = Document(io.BytesIO(data))
        parts = []
        for p in doc.paragraphs:
            t = (p.text or "").strip()
            if t:
                parts.append(t)
        return "\n".join(parts)

    if name.endswith(".pdf"):
        parts = []
        reader = PdfReader(io.BytesIO(data))
        for page in reader.pages:
            text = (page.extract_text() or "").strip()
            if text:
                parts.append(text)
        return "\n\n".join(parts)

    raise HTTPException(status_code=400, detail="Unsupported file type. Use .pdf, .docx, .txt, or .md")


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

        effective_user_text = request.user_text

        result = run_cbra(
            effective_user_text,
            mode=request.mode,
            thread_id=thread_id,
            field_id=thread.current_field_id,
            sources=_active_attachment_sources(thread),
        )

        if "loopcycle" in result and isinstance(result["loopcycle"], dict):
            append_loopcycle(thread_id, LoopCycle(**result["loopcycle"]))

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

        _inject_attachment_metadata(result, thread)
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
    thread = get_thread(thread_id)
    if thread is None:
        thread = create_thread(thread_id)

    return ok(
        request_id=request_id,
        thread_id=thread_id,
        text=None,
        debug=None,
        data=thread.model_dump(),
    )


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
        data=field.dict() if hasattr(field, "dict") else field.model_dump(),
    )


@app.post("/chat/{thread_id}/file")
def chat_with_file(
    thread_id: str,
    user_text: str = "",
    mode: Literal["production", "debug"] = "production",
    upload: Optional[UploadFile] = File(None),
    uploads: Optional[List[UploadFile]] = File(None),
):
    thread = get_thread(thread_id) or create_thread(thread_id)

    incoming_uploads: List[UploadFile] = []
    if upload is not None and getattr(upload, "filename", None):
        incoming_uploads.append(upload)
    for item in uploads or []:
        if item is not None and getattr(item, "filename", None):
            incoming_uploads.append(item)

    if not incoming_uploads:
        raise HTTPException(status_code=400, detail="No file uploaded")

    attachments: List[Dict[str, Any]] = []
    MAX_CHARS = 25000
    for item in incoming_uploads:
        doc_text = _extract_text_from_upload(item)
        if len(doc_text) > MAX_CHARS:
            doc_text = doc_text[:MAX_CHARS] + "\n\n[TRUNCATED]"
        attachments.append({
            "name": item.filename or "attachment",
            "text": doc_text,
            "media_type": getattr(item, "content_type", None),
            "chars": len(doc_text),
        })

    _set_active_attachments(thread, attachments)

    combined = (user_text or "").strip()

    attached_names = ", ".join(_active_attachment_names(thread))
    append_message(thread_id, Message(
        role="user",
        content=f"{user_text}\n\n[Attached: {attached_names}]",
    ))

    result = run_cbra(
        user_text=combined or "Use the attached document(s).",
        mode=mode,
        thread_id=thread_id,
        field_id=thread.current_field_id,
        sources=_active_attachment_sources(thread),
    )

    append_message(thread_id, Message(
        role="assistant",
        content=result.get("text", ""),
    ))

    if "loopcycle" in result and isinstance(result["loopcycle"], dict):
        append_loopcycle(thread_id, LoopCycle(**result["loopcycle"]))

    _inject_attachment_metadata(result, thread)
    return {
        "request_id": str(uuid4()),
        "thread_id": thread_id,
        "text": result.get("text", ""),
        "debug": result.get("debug"),
        "loopcycle": result.get("loopcycle"),
        "data": None,
    }


@app.post("/thread/{thread_id}/attachments/clear")
def clear_active_attachment(thread_id: str):
    request_id = str(uuid4())
    thread = get_thread(thread_id)
    if thread is None:
        thread = create_thread(thread_id)

    cleared_names = _active_attachment_names(thread)
    _clear_active_attachments(thread)

    return ok(
        request_id=request_id,
        thread_id=thread_id,
        text=None,
        debug=None,
        data={
            "cleared": bool(cleared_names),
            "cleared_attachment_name": cleared_names[0] if cleared_names else None,
            "cleared_attachment_names": cleared_names,
            "active_attachment_name": None,
            "active_attachment_names": [],
            "active_attachment_count": 0,
        },
    )
