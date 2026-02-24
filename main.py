from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal, Any

from cbra_engine import run_cbra

from uuid import uuid4
from datetime import datetime

from cbra.models import Message, LoopCycle
from cbra.store import create_thread, get_thread, append_message, append_loopcycle

app = FastAPI(title="CBRA Writing Support")

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
            create_thread(thread_id)

        append_message(
            thread_id,
            Message(role="user", content=request.user_text, timestamp=datetime.utcnow()),
        )

        result = run_cbra(user_text=request.user_text, mode=request.mode)
        if "loopcycle" in result and isinstance(result["loopcycle"], dict):
            append_loopcycle(thread_id, LoopCycle(**result["loopcycle"]))

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
