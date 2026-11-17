"""Thin FastAPI adapter over durable native CBRA sessions."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import List, Optional, Union
from uuid import uuid4

from fastapi import (
    FastAPI,
    File,
    Form,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from cbra.api_models import (
    AttachmentTurnRequest,
    CreateThreadRequest,
    ErrorResponse,
    HealthResponse,
    SessionSummaryResponse,
    TurnPageResponse,
    TurnRequest,
    TurnResponse,
)
from cbra.attachments import (
    AttachmentLimits,
    AttachmentTooLargeError,
    InvalidAttachmentError,
    UnsupportedAttachmentError,
    build_attachment_streams,
    read_uploaded_attachments,
)
from cbra.application import (
    NativeApplicationService,
    RuntimeCorpusIncompatibilityError,
    TurnProjectionPaginationError,
)
from cbra.corpus import (
    CorpusLimits,
    load_canonical_snapshot,
)
from cbra.native import (
    NativePersistenceError,
    NativeSessionError,
    SessionOwnershipError,
    StaleRevisionError,
    TurnConflictError,
)
from cbra.providers.application_activation import (
    ApplicationRendererActivation,
    application_renderer_from_environment,
)
from cbra.store import (
    NativeSessionRepository,
    SessionAlreadyExistsError,
    SessionNotFoundError,
    SessionRepositoryError,
)


APP_TITLE = "CBRA Writing Support"
APP_VERSION = "0.9.0-temporal-markdown"

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
UI_INDEX = PROJECT_ROOT / "ui" / "index.html"
if not UI_INDEX.exists():
    fallback_ui = BASE_DIR / "ui" / "index.html"
    if fallback_ui.exists():
        UI_INDEX = fallback_ui
UI_MARKDOWN = PROJECT_ROOT / "ui" / "markdown.js"
if not UI_MARKDOWN.exists():
    fallback_markdown = BASE_DIR / "ui" / "markdown.js"
    if fallback_markdown.exists():
        UI_MARKDOWN = fallback_markdown

PathLike = Union[str, os.PathLike]


def _request_id() -> str:
    return str(uuid4())


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    fields=None,
) -> JSONResponse:
    body = ErrorResponse(
        request_id=_request_id(),
        error={
            "code": code,
            "message": message,
            "fields": fields,
        },
    )
    if hasattr(body, "model_dump"):
        content = body.model_dump(mode="json", exclude_none=True)
    else:
        content = body.dict(exclude_none=True)
    return JSONResponse(status_code=status_code, content=content)


def _validation_fields(exc: RequestValidationError):
    fields = []
    for error in exc.errors():
        location = error.get("loc", ())
        visible = [
            str(item)
            for item in location
            if item not in {"body", "path", "query"}
        ]
        if visible:
            field = ".".join(visible)
            if field not in fields:
                fields.append(field)
    return fields or None


def _default_session_root() -> Path:
    configured = os.environ.get("CBRA_SESSION_ROOT")
    if configured:
        return Path(configured)
    return PROJECT_ROOT / ".cbra-runtime" / "sessions"


def _default_corpus_root() -> Path:
    configured = os.environ.get("CBRA_CORPUS_ROOT")
    if configured:
        return Path(configured)
    return PROJECT_ROOT / "corpus"


def create_app(
    *,
    session_root: Optional[PathLike] = None,
    repository: Optional[NativeSessionRepository] = None,
    compress: bool = True,
    service: Optional[NativeApplicationService] = None,
    corpus_root: Optional[PathLike] = None,
    corpus_limits: Optional[CorpusLimits] = None,
    attachment_limits: Optional[AttachmentLimits] = None,
) -> FastAPI:
    """Construct an injectable HTTP adapter with explicit durable storage."""
    supplied = sum(
        item is not None for item in (session_root, repository, service)
    )
    if supplied > 1:
        raise ValueError(
            "Provide only one of session_root, repository, or service"
        )
    if service is not None and (
        corpus_root is not None or corpus_limits is not None
    ):
        raise ValueError(
            "A supplied service already owns its canonical corpus snapshot"
        )

    renderer_activation = ApplicationRendererActivation()
    if service is None:
        renderer_activation = application_renderer_from_environment()
    try:
        resolved_attachment_limits = (
            attachment_limits
            if attachment_limits is not None
            else AttachmentLimits.from_environment()
        )
        if service is None:
            resolved_corpus_root = Path(
                corpus_root if corpus_root is not None
                else _default_corpus_root()
            )
            canonical_corpus = load_canonical_snapshot(
                resolved_corpus_root,
                limits=(
                    corpus_limits
                    if corpus_limits is not None
                    else CorpusLimits.from_environment()
                ),
            )
            NativeApplicationService.assert_corpus_compatibility(
                canonical_corpus
            )
            if repository is None:
                resolved_root = Path(
                    session_root if session_root is not None
                    else _default_session_root()
                )
                resolved_root.mkdir(parents=True, exist_ok=True)
                repository = NativeSessionRepository(
                    resolved_root,
                    compress=compress,
                )
            service = NativeApplicationService(
                repository,
                canonical_corpus=canonical_corpus,
                renderer=renderer_activation.renderer,
                renderer_binding=renderer_activation.renderer_binding,
            )
    except Exception:
        renderer_activation.close()
        raise

    @asynccontextmanager
    async def lifespan(application_instance: FastAPI):
        try:
            yield
        finally:
            renderer_activation.close()

    application = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        lifespan=lifespan,
    )
    application.state.native_service = service
    application.state.attachment_limits = resolved_attachment_limits

    @application.exception_handler(RequestValidationError)
    async def invalid_request(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _error_response(
            status_code=422,
            code="invalid_request",
            message="Request validation failed.",
            fields=_validation_fields(exc),
        )

    @application.exception_handler(SessionNotFoundError)
    async def missing_session(
        request: Request,
        exc: SessionNotFoundError,
    ) -> JSONResponse:
        return _error_response(
            status_code=404,
            code="session_not_found",
            message="The requested native session does not exist.",
        )

    @application.exception_handler(StaleRevisionError)
    async def stale_revision(
        request: Request,
        exc: StaleRevisionError,
    ) -> JSONResponse:
        return _error_response(
            status_code=409,
            code="stale_revision",
            message="The native session revision has changed.",
        )

    @application.exception_handler(TurnConflictError)
    async def turn_conflict(
        request: Request,
        exc: TurnConflictError,
    ) -> JSONResponse:
        return _error_response(
            status_code=409,
            code="turn_conflict",
            message="The turn ID already names different material.",
        )

    @application.exception_handler(SessionAlreadyExistsError)
    async def creation_conflict(
        request: Request,
        exc: SessionAlreadyExistsError,
    ) -> JSONResponse:
        return _error_response(
            status_code=409,
            code="session_conflict",
            message="A new native session could not be claimed.",
        )

    @application.exception_handler(TurnProjectionPaginationError)
    async def invalid_pagination(
        request: Request,
        exc: TurnProjectionPaginationError,
    ) -> JSONResponse:
        return _error_response(
            status_code=422,
            code="invalid_pagination",
            message="The requested transcript page is invalid.",
        )

    @application.exception_handler(AttachmentTooLargeError)
    async def attachment_too_large(
        request: Request,
        exc: AttachmentTooLargeError,
    ) -> JSONResponse:
        return _error_response(
            status_code=413,
            code="attachment_too_large",
            message="The submitted attachment request is too large.",
        )

    @application.exception_handler(UnsupportedAttachmentError)
    async def unsupported_attachment(
        request: Request,
        exc: UnsupportedAttachmentError,
    ) -> JSONResponse:
        return _error_response(
            status_code=415,
            code="unsupported_attachment",
            message="The submitted attachment format is unsupported.",
        )

    @application.exception_handler(InvalidAttachmentError)
    async def invalid_attachment(
        request: Request,
        exc: InvalidAttachmentError,
    ) -> JSONResponse:
        return _error_response(
            status_code=422,
            code="invalid_attachment",
            message="The submitted attachment could not be accepted.",
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        if exc.status_code == 404:
            code = "route_not_found"
            message = "The requested route does not exist."
        elif exc.status_code == 405:
            code = "method_not_allowed"
            message = "The requested method is not supported."
        else:
            code = "http_error"
            message = "The HTTP request could not be completed."
        return _error_response(
            status_code=exc.status_code,
            code=code,
            message=message,
        )

    durable_errors = (
        NativePersistenceError,
        SessionOwnershipError,
        SessionRepositoryError,
        NativeSessionError,
    )

    @application.exception_handler(Exception)
    async def safe_server_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        if isinstance(exc, durable_errors):
            return _error_response(
                status_code=500,
                code="invalid_durable_state",
                message="The durable native session could not be used.",
            )
        return _error_response(
            status_code=500,
            code="internal_error",
            message="The request could not be completed.",
        )

    @application.get("/", response_class=HTMLResponse)
    @application.get("/ui", response_class=HTMLResponse)
    def ui() -> HTMLResponse:
        if not UI_INDEX.exists():
            return HTMLResponse(
                (
                    "<html><body><h1>UI not found</h1>"
                    "<p>ui/index.html is missing.</p></body></html>"
                ),
                status_code=404,
            )
        return HTMLResponse(
            UI_INDEX.read_text(encoding="utf-8", errors="replace")
        )

    @application.get("/ui/markdown.js")
    def ui_markdown() -> Response:
        if not UI_MARKDOWN.exists():
            return Response(
                content="Markdown renderer not found.",
                status_code=404,
                media_type="text/plain",
            )
        return Response(
            content=UI_MARKDOWN.read_text(
                encoding="utf-8",
                errors="replace",
            ),
            media_type="application/javascript",
        )

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            ok=True,
            app=APP_TITLE,
            version=APP_VERSION,
            persistence="native_session_repository",
        )

    @application.post(
        "/generate",
        response_model=TurnResponse,
        status_code=201,
        responses={
            200: {"model": TurnResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def generate(
        req: CreateThreadRequest,
        response: Response,
    ) -> TurnResponse:
        result = service.create_thread(
            req.thread_id,
            req.user_text,
            turn_id=req.turn_id,
        )
        response.status_code = 200 if result.replayed else 201
        return TurnResponse.from_result(
            _request_id(),
            result,
            include_debug=req.mode == "debug",
        )

    @application.post(
        "/generate/attachments",
        response_model=TurnResponse,
        status_code=201,
        responses={
            200: {"model": TurnResponse},
            409: {"model": ErrorResponse},
            413: {"model": ErrorResponse},
            415: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def generate_with_attachments(
        response: Response,
        thread_id: str = Form(...),
        user_text: str = Form(...),
        turn_id: str = Form(...),
        attachment_ids: List[str] = Form(
            ...,
            alias="attachment_id",
        ),
        files: List[UploadFile] = File(...),
        mode: str = Form("production"),
    ):
        try:
            request_model = CreateThreadRequest(
                thread_id=thread_id,
                user_text=user_text,
                turn_id=turn_id,
                mode=mode,
            )
        except ValidationError as exc:
            return _error_response(
                status_code=422,
                code="invalid_request",
                message="Request validation failed.",
                fields=_validation_fields(exc),
            )
        uploads = await read_uploaded_attachments(
            attachment_ids=attachment_ids,
            uploads=files,
            limits=resolved_attachment_limits,
        )
        streams = build_attachment_streams(
            thread_id=request_model.thread_id,
            turn_id=request_model.turn_id,
            attachments=uploads,
            limits=resolved_attachment_limits,
        )
        result = service.create_thread(
            request_model.thread_id,
            request_model.user_text,
            turn_id=request_model.turn_id,
            additional_streams=streams,
        )
        response.status_code = 200 if result.replayed else 201
        return TurnResponse.from_result(
            _request_id(),
            result,
            include_debug=request_model.mode == "debug",
        )

    @application.post(
        "/chat/{thread_id}",
        response_model=TurnResponse,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def chat(
        thread_id: str,
        req: TurnRequest,
    ) -> TurnResponse:
        result = service.submit_thread_turn(
            thread_id,
            req.user_text,
            turn_id=req.turn_id,
            expected_revision=req.expected_revision,
        )
        return TurnResponse.from_result(
            _request_id(),
            result,
            include_debug=req.mode == "debug",
        )

    @application.post(
        "/chat/{thread_id}/attachments",
        response_model=TurnResponse,
        responses={
            404: {"model": ErrorResponse},
            409: {"model": ErrorResponse},
            413: {"model": ErrorResponse},
            415: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    async def chat_with_attachments(
        thread_id: str,
        user_text: str = Form(...),
        turn_id: str = Form(...),
        expected_revision: int = Form(...),
        attachment_ids: List[str] = Form(
            ...,
            alias="attachment_id",
        ),
        files: List[UploadFile] = File(...),
        mode: str = Form("production"),
    ):
        try:
            request_model = AttachmentTurnRequest(
                user_text=user_text,
                turn_id=turn_id,
                expected_revision=expected_revision,
                mode=mode,
            )
        except ValidationError as exc:
            return _error_response(
                status_code=422,
                code="invalid_request",
                message="Request validation failed.",
                fields=_validation_fields(exc),
            )
        uploads = await read_uploaded_attachments(
            attachment_ids=attachment_ids,
            uploads=files,
            limits=resolved_attachment_limits,
        )
        streams = build_attachment_streams(
            thread_id=thread_id,
            turn_id=request_model.turn_id,
            attachments=uploads,
            limits=resolved_attachment_limits,
        )
        result = service.submit_thread_turn(
            thread_id,
            request_model.user_text,
            turn_id=request_model.turn_id,
            expected_revision=request_model.expected_revision,
            additional_streams=streams,
        )
        return TurnResponse.from_result(
            _request_id(),
            result,
            include_debug=request_model.mode == "debug",
        )

    @application.get(
        "/thread/{thread_id}",
        response_model=SessionSummaryResponse,
        responses={
            404: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def get_thread_route(thread_id: str) -> SessionSummaryResponse:
        summary = service.summarize_thread(thread_id)
        return SessionSummaryResponse.from_summary(
            _request_id(),
            summary,
        )

    @application.get(
        "/thread/{thread_id}/turns",
        response_model=TurnPageResponse,
        responses={
            404: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            500: {"model": ErrorResponse},
        },
    )
    def get_thread_turns_route(
        thread_id: str,
        after_revision: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=100),
    ) -> TurnPageResponse:
        page = service.project_thread_turns(
            thread_id,
            after_revision=after_revision,
            limit=limit,
        )
        return TurnPageResponse.from_page(
            _request_id(),
            page,
        )

    return application


def _blocked_default_application(
    error: RuntimeCorpusIncompatibilityError,
) -> FastAPI:
    """Remain importable while making default ASGI startup fail explicitly."""

    @asynccontextmanager
    async def blocked_lifespan(_: FastAPI):
        raise RuntimeCorpusIncompatibilityError(str(error))
        yield  # pragma: no cover

    blocked = FastAPI(
        title=APP_TITLE,
        version=APP_VERSION,
        lifespan=blocked_lifespan,
    )
    blocked.state.startup_block = str(error)
    return blocked


try:
    app = create_app()
except RuntimeCorpusIncompatibilityError as startup_error:
    app = _blocked_default_application(startup_error)
