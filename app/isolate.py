"""Runs parsers and decoders in killable child processes.

Pillow, libheif, cairo, qpdf and the email parsers all read untrusted bytes. A thread
cannot be killed, so a hung decoder would outlive its timeout, and a segfault would take
the service down. Each call therefore gets its own process, forked from a forkserver that
has already imported the heavy libraries, which keeps the per-call overhead to milliseconds.
"""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import resource
import warnings
from typing import Any, Callable

from app.context import Deadline
from app.errors import ApiError, ConversionFailed

log = logging.getLogger(__name__)

_ctx = multiprocessing.get_context("forkserver")
_semaphore: asyncio.Semaphore | None = None
_memory_limit: int | None = None

_PRELOAD = [
    "app.detect",
    "app.pdftools",
    "app.engines.images",
    "app.engines.vector",
    "app.engines.email",
    "uvicorn",
]


def _noop() -> None:
    return None


async def init(concurrency: int, memory_limit: int | None) -> None:
    """Starts the forkserver and waits for the preload, so no request pays for it."""
    global _semaphore, _memory_limit
    _semaphore = asyncio.Semaphore(concurrency)
    _memory_limit = memory_limit
    _ctx.set_forkserver_preload(_PRELOAD)
    await run(_noop, deadline=Deadline(120))


def _child(conn, memory_limit: int | None, fn: Callable, args: tuple, kwargs: dict) -> None:
    try:
        # Libraries in here log and warn about what they parse. Nothing of that may be printed.
        logging.disable(logging.CRITICAL)
        warnings.simplefilter("ignore")
        if memory_limit:
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        conn.send(("ok", fn(*args, **kwargs)))
    except ApiError as exc:
        conn.send(("api_error", exc))
    except MemoryError:
        conn.send(("error", "ran out of memory"))
    except BaseException as exc:  # noqa: BLE001 - everything must reach the parent
        conn.send(("error", type(exc).__name__))
    finally:
        conn.close()


async def run(fn: Callable[..., Any], *args: Any, deadline: Deadline, **kwargs: Any) -> Any:
    """Runs `fn` in a child process, killing it if the deadline passes."""
    assert _semaphore is not None, "isolate.init() has not run"
    loop = asyncio.get_running_loop()
    try:
        async with asyncio.timeout(deadline.remaining()):
            async with _semaphore:
                recv_conn, send_conn = _ctx.Pipe(duplex=False)
                process = _ctx.Process(
                    target=_child,
                    args=(send_conn, _memory_limit, fn, args, kwargs),
                    daemon=True,
                )
                readable = loop.create_future()
                # Starting is shielded: if the deadline lands here, the process must be
                # fully started before it can be killed, or it would run on unsupervised.
                start = asyncio.ensure_future(asyncio.to_thread(process.start))
                try:
                    await asyncio.shield(start)
                except asyncio.CancelledError:
                    await start
                    process.kill()
                    await asyncio.to_thread(process.join, 5)
                    raise
                finally:
                    send_conn.close()
                try:
                    loop.add_reader(recv_conn.fileno(), lambda: readable.done() or readable.set_result(None))
                    try:
                        await readable
                    finally:
                        loop.remove_reader(recv_conn.fileno())
                    try:
                        status, payload = recv_conn.recv()
                    except EOFError:
                        await asyncio.to_thread(process.join, 5)
                        raise ConversionFailed(
                            f"Engine process died unexpectedly (exit code {process.exitcode})"
                        ) from None
                finally:
                    recv_conn.close()
                    if process.is_alive():
                        process.join(0.05)
                    if process.is_alive():
                        process.kill()
                    await asyncio.shield(asyncio.to_thread(process.join, 5))
    except TimeoutError:
        raise deadline.timeout_error() from None

    if status == "ok":
        return payload
    if status == "api_error":
        raise payload
    log.warning("Engine process error in %s: %s", getattr(fn, "__name__", fn), payload)
    raise ConversionFailed("The file could not be processed")
