"""FastAPI application: routes, middleware and engine lifecycle."""

from __future__ import annotations

import asyncio
import concurrent.futures
import hmac
import json
import logging
import shutil
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Any

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app import isolate
from app.config import get_settings
from app.context import Deadline, configure_logging, note_request, request_id_var, request_summary_var
from app.engines.ghostscript import Ghostscript
from app.engines.html import Chromium
from app.engines.libreoffice import LibreOfficePool
from app.engines.verapdf import VeraPdf
from app.errors import (
    ApiError,
    FileTooLarge,
    MethodNotAllowed,
    NotFound,
    Unauthorized,
)
from app.formats import FAMILIES
from app.pipeline import ConversionResult, Engines, Pipeline
from app.util import content_disposition, safe_filename

log = logging.getLogger("app")

# The body limit allows for multipart boundaries and form fields around the file.
_MULTIPART_OVERHEAD_BYTES = 64 * 1024
_LOGGED_ROUTES = {"/v1/convert", "/v1/formats"}
_CHUNK_BYTES = 1024 * 1024


class _Services:
    """Engines, created at startup."""

    pipeline: Pipeline
    engines: Engines
    ready_cache: tuple[float, dict] | None = None


services = _Services()


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    if not settings.api_key:
        raise RuntimeError("API_KEY must be set")
    settings.work_dir.mkdir(parents=True, exist_ok=True)
    # Anything left here belongs to a previous process that did not exit cleanly.
    for leftover in settings.work_dir.iterdir():
        shutil.rmtree(leftover, ignore_errors=True)

    asyncio.get_running_loop().set_default_executor(
        concurrent.futures.ThreadPoolExecutor(max_workers=max(32, settings.lo_pool_size * 2), thread_name_prefix="blocking")
    )
    await isolate.init(settings.gs_concurrency, settings.memory_limit_bytes)

    # Requests are not accepted until this completes, so callers never meet a cold engine.
    libreoffice = LibreOfficePool(settings)
    chromium = Chromium(settings)
    started = time.monotonic()
    await asyncio.gather(libreoffice.start(), chromium.start())
    engines = Engines(libreoffice, Ghostscript(settings), chromium, VeraPdf(settings))
    services.engines = engines
    services.pipeline = Pipeline(settings, engines)
    log.info("Service ready", extra={"fields": {"startupMs": round((time.monotonic() - started) * 1000)}})
    try:
        yield
    finally:
        await chromium.stop()
        await libreoffice.stop()


app = FastAPI(
    title="PDF/A-1b conversion service",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------
def _error_body(code: str, message: str) -> dict[str, str]:
    return {"error": code, "message": message, "requestId": request_id_var.get()}


def _error_response(status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content=_error_body(code, message),
        headers={"X-Request-Id": request_id_var.get()},
    )


@app.exception_handler(ApiError)
async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
    # Logged by code alone: messages may echo parts of the request.
    note_request(outcome=exc.code)
    return _error_response(exc.status, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
    problems = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ()) if part not in ("body", "query"))
        problems.append(f"{location}: {error.get('msg')}" if location else str(error.get("msg")))
    return _error_response(400, "BAD_REQUEST", "; ".join(problems) or "Invalid request")


@app.exception_handler(StarletteHTTPException)
async def _handle_http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: NotFound.code, 405: MethodNotAllowed.code, 413: FileTooLarge.code}.get(exc.status_code, "BAD_REQUEST")
    return _error_response(exc.status_code, code, str(exc.detail))


@app.exception_handler(Exception)
async def _handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
    log.error("Unhandled error", exc_info=(type(exc), exc, exc.__traceback__))
    note_request(outcome="INTERNAL_ERROR")
    return _error_response(500, "INTERNAL_ERROR", "An internal error occurred")


# ---------------------------------------------------------------------------
# Middleware. Plain ASGI, so uploads are not buffered and context variables propagate.
# ---------------------------------------------------------------------------
class _BodyTooLarge(HTTPException):
    """Raised while the body is being read.

    FastAPI turns exceptions from form parsing into a 400, except for HTTPException, so
    this has to be one for the caller to receive the correct 413.
    """

    def __init__(self) -> None:
        limit = get_settings().max_upload_bytes
        super().__init__(status_code=413, detail=f"The request exceeds the limit of {limit} bytes")


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        supplied = dict(scope["headers"]).get(b"x-request-id", b"").decode("latin-1").strip()
        valid = supplied and len(supplied) <= 128 and all(c.isalnum() or c in "-_.:" for c in supplied)
        request_id = supplied if valid else str(uuid.uuid4())
        token = request_id_var.set(request_id)
        path = scope["path"]
        summary: dict[str, Any] = {"route": path if path in _LOGGED_ROUTES else "other"}
        summary_token = request_summary_var.set(summary)
        started = time.monotonic()

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                summary["status"] = message["status"]
                headers = [(k, v) for k, v in message.get("headers", []) if k.lower() != b"x-request-id"]
                headers.append((b"x-request-id", request_id.encode("latin-1")))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            # The only per-request log line: request ID, format, sizes, duration and outcome.
            # Never the original filename or any file content.
            if not path.startswith("/health/"):
                summary["durationMs"] = round((time.monotonic() - started) * 1000)
                summary.setdefault("outcome", "OK" if summary.get("status", 500) < 400 else "ERROR")
                log.info("Request finished", extra={"fields": summary})
            request_summary_var.reset(summary_token)
            request_id_var.reset(token)


async def _send_json_error(send: Send, status: int, code: str, message: str) -> None:
    body = json.dumps(_error_body(code, message)).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()), (b"connection", b"close")],
        }
    )
    await send({"type": "http.response.body", "body": body})


class ApiKeyMiddleware:
    """Checks the key before any body is read, so anonymous uploads cost nothing.

    FastAPI parses form bodies before running dependencies, so a dependency could not do this.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["path"].startswith("/v1/"):
            supplied = dict(scope["headers"]).get(b"x-api-key", b"")
            if not hmac.compare_digest(supplied, get_settings().api_key.encode()):
                await _send_json_error(send, 401, Unauthorized.code, "Missing or invalid API key")
                return
        await self.app(scope, receive, send)


class BodyLimitMiddleware:
    """Enforces the upload limit while the body arrives.

    Without this, Starlette would spool an arbitrarily large multipart body to disk before
    any route code could look at its size. Chunked uploads have no Content-Length, so bytes
    are counted as well.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {"POST", "PUT", "PATCH"}:
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        limit = settings.max_upload_bytes + _MULTIPART_OVERHEAD_BYTES
        too_large = f"The request exceeds the limit of {settings.max_upload_bytes} bytes"

        declared = dict(scope["headers"]).get(b"content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            await _send_json_error(send, 413, FileTooLarge.code, too_large)
            return

        received = 0
        response_started = False

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _BodyTooLarge()
            return message

        async def tracking_send(message: Message) -> None:
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _BodyTooLarge:
            if not response_started:
                await _send_json_error(send, 413, FileTooLarge.code, too_large)


# Added last means outermost: request ID, then auth, then the body limit.
app.add_middleware(BodyLimitMiddleware)
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(RequestIdMiddleware)


# ---------------------------------------------------------------------------
# Temp directory handling
# ---------------------------------------------------------------------------
def _new_work_dir() -> Path:
    path = get_settings().work_dir / uuid.uuid4().hex
    path.mkdir(mode=0o700)
    return path


class _CleanupFileResponse(FileResponse):
    """Removes the request's temp directory once the response ends, however it ends.

    A BackgroundTask would be skipped if the client disconnected mid-download.
    """

    def __init__(self, *args: Any, work_dir: Path, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._work_dir = work_dir

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            await super().__call__(scope, receive, send)
        finally:
            shutil.rmtree(self._work_dir, ignore_errors=True)


def _result_headers(result: ConversionResult) -> dict[str, str]:
    validated = "skipped" if result.validated is None else str(result.validated).lower()
    headers = {
        "X-Source-Format": result.source_format,
        "X-Conversion-Ms": str(result.conversion_ms),
        "X-PdfA-Validated": validated,
        "X-Page-Count": str(result.pages),
    }
    if result.attachments_skipped:
        headers["X-Attachments-Skipped"] = str(result.attachments_skipped)
    if result.flattened_pages:
        headers["X-Flattened-Pages"] = str(result.flattened_pages)
    return headers


def _log_success(result: ConversionResult) -> None:
    note_request(
        pages=result.pages,
        outputBytes=result.size_bytes,
        conversionMs=result.conversion_ms,
        validated=result.validated,
    )


def _stream_response(result: ConversionResult, filename: str, work_dir: Path) -> Response:
    headers = _result_headers(result)
    headers["Content-Disposition"] = content_disposition(filename)
    return _CleanupFileResponse(result.pdf, media_type="application/pdf", headers=headers, work_dir=work_dir)


async def _copy_upload(upload: UploadFile, dst: Path) -> None:
    limit = get_settings().max_upload_bytes
    written = 0
    with dst.open("wb") as handle:
        while chunk := await upload.read(_CHUNK_BYTES):
            written += len(chunk)
            if written > limit:
                raise FileTooLarge(f"The file exceeds the limit of {limit} bytes")
            handle.write(chunk)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.post("/v1/convert")
async def convert_upload(
    file: Annotated[UploadFile, File()],
    validate_pdfa: Annotated[bool | None, Form(alias="validate")] = None,
) -> Response:
    filename = safe_filename(file.filename)
    work_dir = _new_work_dir()
    keep_for_stream = False
    try:
        source = work_dir / "source"
        await _copy_upload(file, source)
        result = await services.pipeline.convert(source, filename, work_dir, validate=validate_pdfa)
        _log_success(result)

        keep_for_stream = True
        return _stream_response(result, filename, work_dir)
    finally:
        await file.close()
        if not keep_for_stream:
            shutil.rmtree(work_dir, ignore_errors=True)


@app.get("/v1/formats")
async def formats() -> dict[str, Any]:
    if get_settings().enable_msg:
        return {"families": FAMILIES}
    return {"families": {family: [ext for ext in exts if ext != "msg"] for family, exts in FAMILIES.items()}}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------
@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


async def _readiness() -> dict[str, Any]:
    engines = services.engines
    checks: dict[str, Any] = {}

    pool = engines.libreoffice.status()
    checks["libreoffice"] = {"ok": pool["alive"] > 0, **pool}

    try:
        checks["ghostscript"] = {"ok": await engines.ghostscript.check(Deadline(5))}
    except ApiError:
        checks["ghostscript"] = {"ok": False}

    checks["chromium"] = {"ok": engines.chromium.is_ready()}

    return {"status": "ok" if all(check["ok"] for check in checks.values()) else "unavailable", "checks": checks}


@app.get("/health/ready")
async def ready() -> JSONResponse:
    now = time.monotonic()
    cached = services.ready_cache
    if cached is None or now - cached[0] >= get_settings().ready_cache_seconds:
        cached = (now, await _readiness())
        services.ready_cache = cached
    body = cached[1]
    return JSONResponse(body, status_code=200 if body["status"] == "ok" else 503)
