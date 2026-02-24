from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from cbra_engine import run_cbra

from uuid import uuid4
from datetime import datetime

from cbra.models import Message
from cbra.store import create_thread, get_thread, append_message

app = FastAPI(title="CBRA Writing Support")

class GenerateRequest(BaseModel):
    user_text: str = Field(..., min_length=1)
    mode: Literal["production", "debug"] = "production"

@app.post("/generate")
async def generate(req: GenerateRequest):
    try:
        return run_cbra(req.user_text, mode=req.mode)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat/{thread_id}")
def chat(thread_id: str, request: GenerateRequest):
    # Create thread if it doesn't exist
    thread = get_thread(thread_id)
    if thread is None:
        thread = create_thread(thread_id)

    # Store user message
    append_message(
        thread_id,
        Message(role="user", content=request.user_text, timestamp=datetime.utcnow()),
    )

    # Generate assistant response (existing engine call)
    result = run_cbra(user_text=request.user_text, mode=request.mode)

    # Store assistant message
    append_message(
        thread_id,
        Message(role="assistant", content=result["text"], timestamp=datetime.utcnow()),
    )

    return {
        "request_id": str(uuid4()),
        "thread_id": thread_id,
        "text": result["text"],
        "debug": result.get("debug"),
    }


@app.get("/thread/{thread_id}")
def read_thread(thread_id: str):
    thread = get_thread(thread_id)
    if thread is None:
        return {"error": {"code": "THREAD_NOT_FOUND", "message": "Thread not found"}}
    return thread


@app.get("/thread/{thread_id}/export")
def export_thread(thread_id: str):
    thread = get_thread(thread_id)
    if thread is None:
        return {"error": {"code": "THREAD_NOT_FOUND", "message": "Thread not found"}}
    return thread.dict()
