"""HTTP interface for the enactment runtime: one store per browser session,
progress as server-sent events, and a plain page.

This is a transport layer. Nothing here reasons; it routes arrivals to a
``Runtime``, streams the lifecycle facts and round events the runtime emits,
and returns records. The historical application under ``cbra/app.py`` is not
touched and its routes are not reused.
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import re
import threading
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from .graph import Configuration
from .material import Corpus
from .persistence import JsonStore
from .proposer import Proposer
from .runtime import Runtime

SESSION_ID = re.compile(r"^[a-f0-9]{12}$")
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def history(config: Configuration) -> List[Dict[str, Any]]:
    """The conversation as records: arrivals, effects, and interventions in
    order. Built from the trace; nothing is stored separately for it."""
    arrival_seq: Dict[str, int] = {}
    for fact in config.lifecycle:
        if fact.get("fact") == "reconfiguration_open" and fact.get("arrival") in config.transports:
            arrival_seq[str(fact.get("turn"))] = config.transports[fact["arrival"]].sequence
    returns: Dict[str, List[Dict[str, Any]]] = {}
    for cut in config.cuts.values():
        if cut.kind == "apparatus" and cut.label.startswith("release_constraints_fired"):
            returns.setdefault(str(cut.payload.get("turn")), []).append(
                {"round": int(cut.label.rsplit(":r", 1)[-1]), "constraints": cut.payload.get("violations", [])})
    items: List[Dict[str, Any]] = []
    for trace in config.transports.values():
        if trace.role == "user_message":
            items.append({"order": trace.sequence, "kind": "arrival", "handle": trace.handle, "text": trace.text})
        elif trace.role == "effect_report":
            items.append({"order": trace.sequence, "kind": "effect", "handle": trace.handle, "text": trace.text})
    for cut in config.cuts.values():
        if cut.kind != "intervention":
            continue
        turn = str(cut.payload.get("turn"))
        p = cut.payload
        items.append({
            "order": arrival_seq.get(turn, 0) + 0.5,
            "kind": "intervention", "id": cut.id, "turn": turn, "status": cut.status,
            "form": p.get("form"), "release_kind": p.get("kind"), "text": p.get("text"), "action": p.get("action"), "rounds": p.get("rounds"),
            "returns": sorted(returns.get(turn, []), key=lambda r: r["round"]),
            "withheld_constraints": p.get("withheld_constraints", []),
            "claims": p.get("claims", []), "claims_stripped": p.get("claims_stripped", []),
            "person_state_live": p.get("person_state_live"),
            "material": [{"handle": h, "file": config.transports[h].provenance.get("file"),
                          "heading": config.transports[h].provenance.get("heading"),
                          "terms": list(config.transports[h].provenance.get("terms") or []),
                          "drawn_by": config.transports[h].provenance.get("drawn_by"),
                          "via": config.transports[h].provenance.get("via"),
                          "consequential": bool(config.transports[h].provenance.get("consequential"))}
                         for h in p.get("material", []) if h in config.transports],
            "care_delta": sorted((p.get("care_delta") or {}).keys()),
            "play_delta": {k: sorted(v.keys()) for k, v in (p.get("play_delta") or {}).items()},
            "reopen_conditions": list(cut.invalidation_conditions),
            "response_demand": p.get("response_demand", {}),
            "unmarked": list(cut.unmarked),
            "reopened_reason": cut.invalidation_reason,
        })
    items.sort(key=lambda i: i["order"])
    return items


def compact_trace(config: Configuration) -> Dict[str, Any]:
    return {
        "session": config.session, "version": config.version,
        "counts": {"transports": len(config.transports), "cuts": len(config.cuts), "deltas": len(config.deltas),
                   "lifecycle": len(config.lifecycle), "unresolved": len(config.unresolved),
                   "live_edges": sum(len(v) for v in config._dependents.values())},
        "cuts": [{"id": c.id, "kind": c.kind, "label": c.label, "status": c.status, "version": c.version,
                  "depends_on": list(c.depends_on), "invalidation_conditions": list(c.invalidation_conditions),
                  "role": c.payload.get("role"), "turn": c.payload.get("turn"),
                  "reason": c.invalidation_reason} for c in config.cuts.values()],
        "lifecycle": list(config.lifecycle),
        "unresolved": list(config.unresolved),
    }


class Session:
    def __init__(self, session_id: str, runtime: Runtime, events: "queue.Queue[Dict[str, Any]]") -> None:
        self.id = session_id
        self.runtime = runtime
        self.events = events
        self.lock = threading.Lock()


def create_app(proposer: Optional[Proposer] = None, store_dir: str = os.path.join(".cbra-runtime", "sessions"),
               model: Optional[str] = None, max_rounds: int = 3, corpus_dir: Optional[str] = None,
               embedder: Any = None, embedding_cache: Optional[str] = None) -> FastAPI:
    app = FastAPI(title="CBRA enactment slice", docs_url=None, redoc_url=None)
    corpus = Corpus(corpus_dir, embedder=embedder, cache_dir=embedding_cache) if corpus_dir else None
    sessions: Dict[str, Session] = {}
    registry_lock = threading.Lock()
    state: Dict[str, Any] = {"proposer": proposer}

    def get_proposer() -> Proposer:
        if state["proposer"] is None:
            if not os.environ.get("OPENAI_API_KEY"):
                raise HTTPException(503, "No OPENAI_API_KEY in the server environment; the proposer cannot be started.")
            from .proposer import OpenAIResponsesProposer
            state["proposer"] = OpenAIResponsesProposer(model=model)
        return state["proposer"]

    def open_session(session_id: str, create: bool) -> Session:
        if not SESSION_ID.match(session_id):
            raise HTTPException(400, "bad session id")
        with registry_lock:
            if session_id in sessions:
                return sessions[session_id]
            store = JsonStore(os.path.join(store_dir, session_id + ".json"))
            if not store.exists() and not create:
                raise HTTPException(404, "no such session")
            events: "queue.Queue[Dict[str, Any]]" = queue.Queue()
            runtime = Runtime(get_proposer(), store=store, max_rounds=max_rounds, channel="web",
                              observer=events.put, material=corpus)
            runtime.config.session = session_id
            session = Session(session_id, runtime, events)
            sessions[session_id] = session
            return session

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(os.path.join(STATIC_DIR, "index.html"), media_type="text/html")

    @app.post("/api/session")
    def new_session() -> Dict[str, Any]:
        session_id = uuid.uuid4().hex[:12]
        session = open_session(session_id, create=True)
        session.runtime._save()
        return {"session": session_id}

    @app.get("/api/session/{session_id}")
    def read_session(session_id: str) -> Dict[str, Any]:
        session = open_session(session_id, create=False)
        cfg = session.runtime.config
        return {"session": session_id, "version": cfg.version, "history": history(cfg),
                "busy": session.lock.locked(), "unresolved": list(cfg.unresolved)}

    @app.post("/api/session/{session_id}/turn")
    def turn(session_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        session = open_session(session_id, create=False)
        text = str(body.get("text", "")).strip()
        if not text:
            raise HTTPException(400, "empty arrival")
        if not session.lock.acquire(blocking=False):
            raise HTTPException(409, "a turn is already forming in this session")
        try:
            result = session.runtime.turn(text, channel="web")
        except Exception as error:  # the turn's partial trace is saved by the runtime; report, do not hide
            session.events.put({"event": "error", "kind": "turn", "error": "%s: %s" % (type(error).__name__, error)})
            return JSONResponse({"error": "%s: %s" % (type(error).__name__, error),
                                 "history": history(session.runtime.config)}, status_code=500)
        finally:
            session.lock.release()
        record = result.as_record()
        record.pop("deltas", None)
        record["history"] = history(session.runtime.config)
        session.events.put({"event": "done", "kind": "turn", "turn": result.turn, "released": result.released,
                            "form": result.form, "intervention": result.intervention})
        return record

    @app.post("/api/session/{session_id}/effect")
    def effect(session_id: str, body: Dict[str, Any]) -> Dict[str, Any]:
        session = open_session(session_id, create=False)
        text = str(body.get("text", "")).strip()
        if not text:
            raise HTTPException(400, "empty effect")
        conditions = body.get("conditions")
        if conditions is not None:
            conditions = [str(c).strip() for c in conditions if str(c).strip()]
        if not session.lock.acquire(blocking=False):
            raise HTTPException(409, "a turn is already forming in this session")
        try:
            result = session.runtime.effect(text, conditions=conditions, channel="web")
        except Exception as error:
            session.events.put({"event": "error", "kind": "effect", "error": "%s: %s" % (type(error).__name__, error)})
            return JSONResponse({"error": "%s: %s" % (type(error).__name__, error),
                                 "history": history(session.runtime.config)}, status_code=500)
        finally:
            session.lock.release()
        record = result.as_record()
        record["history"] = history(session.runtime.config)
        session.events.put({"event": "done", "kind": "effect", "reinserted": result.reinserted,
                            "reopened": result.reopened, "conditions": result.conditions})
        return record

    @app.get("/api/session/{session_id}/trace")
    def trace(session_id: str) -> Dict[str, Any]:
        return compact_trace(open_session(session_id, create=False).runtime.config)

    @app.get("/api/canon")
    def canon() -> Dict[str, Any]:
        return corpus.describe() if corpus else {"directory": None, "index": None, "files": [], "sections": 0}

    @app.get("/api/session/{session_id}/self")
    def account(session_id: str) -> Dict[str, Any]:
        return open_session(session_id, create=False).runtime.account_of_self()

    @app.get("/api/session/{session_id}/events")
    async def events(session_id: str, request: Request) -> StreamingResponse:
        session = open_session(session_id, create=False)

        async def stream():
            yield "retry: 2000\n\n"
            idle = 0.0
            while True:
                if await request.is_disconnected():
                    return
                try:
                    event = session.events.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.25)
                    idle += 0.25
                    if idle >= 15:
                        idle = 0.0
                        yield ": ping\n\n"
                    continue
                idle = 0.0
                yield "data: %s\n\n" % json.dumps(event, ensure_ascii=False)

        return StreamingResponse(stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

    return app
