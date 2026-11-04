"""A warm pool of unoserver instances, each with its own ports and user profile.

Instances are handed out through an asyncio queue, one conversion at a time. The pool
owns the processes: a hung or crashed instance is killed with its whole process group
and replaced with a fresh profile while the rest of the pool keeps serving.
"""

from __future__ import annotations

import asyncio
import csv
import http.client
import io
import logging
import os
import shutil
import signal
import socket
import subprocess
import time
import xmlrpc.client
from dataclasses import dataclass, field
from pathlib import Path

from app.config import PAGE_SIZES, Settings
from app.context import Deadline
from app.errors import ConversionFailed, ConversionTimeout, CorruptFile, EncryptedFile
from app.util import decode_text

log = logging.getLogger(__name__)

# Options for LibreOffice's PDF export filters.
PDF_FILTER_OPTIONS = [
    "SelectPdfVersion=1",  # PDF/A-1b
    "UseLosslessCompression=true",  # also embeds suitable JPEGs without re-encoding them
    "ReduceImageResolution=false",
    "ExportBookmarks=true",
    "EmbedStandardFonts=true",
    "IsSkipEmptyPages=false",
    "ExportNotes=false",
]

_PING_TIMEOUT_SECONDS = 5
_STARTUP_TIMEOUT_SECONDS = 60
_LOAD_FAILURE_MARKERS = (
    "could not load document",
    "unsupported url",
    "illegalargumentexception",
    "ioexception",
    "general error",
)


class _TimeoutTransport(xmlrpc.client.Transport):
    def __init__(self, timeout: float) -> None:
        super().__init__()
        self._timeout = timeout

    def make_connection(self, host):
        connection = http.client.HTTPConnection(host, timeout=self._timeout)
        self._connection = (host, connection)
        return connection


def _rpc(port: int, timeout: float) -> xmlrpc.client.ServerProxy:
    return xmlrpc.client.ServerProxy(
        f"http://127.0.0.1:{port}", transport=_TimeoutTransport(timeout), allow_none=True
    )


@dataclass
class _Instance:
    index: int
    port: int
    uno_port: int
    profile: Path
    process: subprocess.Popen | None = None
    conversions: int = 0
    log_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.log_file = self.profile.with_suffix(".log")

    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def kill(self) -> None:
        if self.process is None:
            return
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            log.error("LibreOffice instance %d did not exit after SIGKILL", self.index)
        self.process = None


def prepare_text_input(src: str, dst: str, is_csv: bool) -> None:
    """Rewrites text input as UTF-8, and CSV with comma separators.

    LibreOffice's filters need the encoding and separator stated up front, so they are
    worked out here. Runs in an isolated process.
    """
    text = decode_text(Path(src).read_bytes())
    if not is_csv:
        Path(dst).write_text(text, encoding="utf-8", newline="")
        return
    sample = text[:65536]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\n")
    csv.field_size_limit(10_000_000)
    for row in csv.reader(io.StringIO(text, newline=""), dialect):
        writer.writerow(row)
    Path(dst).write_text(output.getvalue(), encoding="utf-8", newline="")


class LibreOfficePool:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._queue: asyncio.Queue[_Instance] = asyncio.Queue()
        self._instances: list[_Instance] = []
        self._tasks: set[asyncio.Task] = set()
        self._watchdog: asyncio.Task | None = None
        self._stopping = False

    async def start(self) -> None:
        root = self._settings.lo_run_dir
        root.mkdir(parents=True, exist_ok=True)
        base = self._settings.lo_base_port
        self._instances = [
            _Instance(index=i, port=base + 2 * i, uno_port=base + 2 * i + 1, profile=root / f"profile-{i}")
            for i in range(self._settings.lo_pool_size)
        ]
        results = await asyncio.gather(
            *(self._launch(instance) for instance in self._instances), return_exceptions=True
        )
        for instance, result in zip(self._instances, results):
            if isinstance(result, Exception):
                log.error("LibreOffice instance %d failed to start: %s", instance.index, result)
                self._spawn_restart(instance)
            else:
                self._queue.put_nowait(instance)
        if self._queue.empty():
            raise RuntimeError("No LibreOffice instance could be started")
        self._watchdog = asyncio.create_task(self._watch())
        log.info("LibreOffice pool ready", extra={"fields": {"instances": self._queue.qsize()}})

    async def stop(self) -> None:
        self._stopping = True
        if self._watchdog:
            self._watchdog.cancel()
        for task in list(self._tasks):
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        for instance in self._instances:
            await asyncio.to_thread(instance.kill)

    def status(self) -> dict:
        alive = sum(1 for instance in self._instances if instance.alive())
        return {"size": len(self._instances), "alive": alive, "idle": self._queue.qsize()}

    def _launch_blocking(self, instance: _Instance) -> None:
        instance.kill()
        shutil.rmtree(instance.profile, ignore_errors=True)
        shutil.copytree(self._settings.lo_template_dir, instance.profile)
        width, height = PAGE_SIZES[self._settings.fallback_page_name]
        env = {
            **os.environ,
            # unoserver lives outside the app's Python 3.12 environment.
            "PYTHONPATH": "/opt/unoserver",
            "HOME": str(instance.profile),
            "LO_TEXT_PAGE_WIDTH": str(round(width / 72 * 2540)),
            "LO_TEXT_PAGE_HEIGHT": str(round(height / 72 * 2540)),
        }
        with instance.log_file.open("wb") as log_handle:
            instance.process = subprocess.Popen(
                [
                    "/usr/bin/python3",
                    str(self._settings.lo_server_script),
                    "--port", str(instance.port),
                    "--uno-port", str(instance.uno_port),
                    "--user-installation", str(instance.profile),
                    "--quiet",  # unoserver's normal logging names every file it opens
                ],
                stdin=subprocess.DEVNULL,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                env=env,
                start_new_session=True,
            )
        instance.conversions = 0

    async def _launch(self, instance: _Instance) -> None:
        await asyncio.to_thread(self._launch_blocking, instance)
        started = time.monotonic()
        while time.monotonic() - started < _STARTUP_TIMEOUT_SECONDS:
            if not instance.alive():
                raise RuntimeError(f"unoserver exited during startup (see {instance.log_file})")
            if await asyncio.to_thread(self._ping, instance):
                return
            await asyncio.sleep(0.25)
        await asyncio.to_thread(instance.kill)
        raise RuntimeError("unoserver did not become ready in time")

    @staticmethod
    def _ping(instance: _Instance) -> bool:
        """`info` goes through the UNO bridge, so it proves soffice itself responds."""
        try:
            _rpc(instance.port, _PING_TIMEOUT_SECONDS).info()
            return True
        except Exception:  # noqa: BLE001 - any failure at all means the instance is not healthy
            return False

    def _spawn_restart(self, instance: _Instance) -> None:
        task = asyncio.create_task(self._restart(instance))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _restart(self, instance: _Instance) -> None:
        attempt = 0
        while not self._stopping:
            try:
                await self._launch(instance)
                log.info("LibreOffice instance restarted", extra={"fields": {"instance": instance.index}})
                self._queue.put_nowait(instance)
                return
            except Exception as exc:  # noqa: BLE001 - keep trying; the instance must come back
                attempt += 1
                log.error("LibreOffice instance %d restart failed: %s", instance.index, exc)
                await asyncio.sleep(min(30, 2**attempt))

    async def _watch(self) -> None:
        """Pings idle instances and replaces any that stopped responding."""
        while True:
            await asyncio.sleep(self._settings.lo_health_interval_seconds)
            for _ in range(self._queue.qsize()):
                try:
                    instance = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                try:
                    healthy = instance.alive() and await asyncio.to_thread(self._ping, instance)
                except Exception:  # noqa: BLE001 - nothing may end this loop or lose the instance
                    log.exception("Health check failed unexpectedly")
                    healthy = False
                if healthy:
                    self._queue.put_nowait(instance)
                else:
                    log.warning("LibreOffice instance unhealthy, restarting", extra={"fields": {"instance": instance.index}})
                    self._spawn_restart(instance)

    async def _acquire(self, deadline: Deadline) -> _Instance:
        while True:
            try:
                async with asyncio.timeout(deadline.remaining()):
                    instance = await self._queue.get()
            except TimeoutError:
                raise deadline.timeout_error() from None
            if instance.alive():
                return instance
            log.warning("LibreOffice instance found dead, restarting", extra={"fields": {"instance": instance.index}})
            self._spawn_restart(instance)

    @staticmethod
    def _convert_blocking(port: int, src: str, dst: str, timeout: float) -> None:
        _rpc(port, timeout).convert(src, None, dst, "pdf", None, PDF_FILTER_OPTIONS, False, None, None)

    async def convert(self, src: Path, dst: Path, deadline: Deadline) -> None:
        """Exports `src` as PDF/A-1b to `dst`."""
        for _ in range(2):
            instance = await self._acquire(deadline)
            try:
                timeout = deadline.remaining()
            except ConversionTimeout:
                self._queue.put_nowait(instance)
                raise
            try:
                await asyncio.to_thread(self._convert_blocking, instance.port, str(src), str(dst), timeout)
            except (socket.timeout, TimeoutError):
                # A socket timeout means this instance is stuck on the document.
                log.warning("Conversion timed out, killing instance", extra={"fields": {"instance": instance.index}})
                await asyncio.to_thread(instance.kill)
                self._spawn_restart(instance)
                raise deadline.timeout_error() from None
            except xmlrpc.client.Fault as fault:
                # A fault has two possible causes. LibreOffice may have refused the document,
                # or soffice may have died behind a still-running unoserver, whose bridge then
                # reports faults until the process exits. Only a ping can tell them apart.
                if not await asyncio.to_thread(self._ping, instance):
                    log.warning("LibreOffice instance stopped responding", extra={"fields": {"instance": instance.index}})
                    await asyncio.to_thread(instance.kill)
                    self._spawn_restart(instance)
                    continue
                self._release(instance)
                message = fault.faultString.lower()
                log.info("LibreOffice rejected the document")
                if any(marker in message for marker in _LOAD_FAILURE_MARKERS):
                    if "password" in message:
                        raise EncryptedFile("The document is password-protected") from None
                    raise CorruptFile("The document is damaged or cannot be opened") from None
                raise ConversionFailed("LibreOffice could not convert the document") from None
            except (OSError, xmlrpc.client.Error, http.client.HTTPException) as exc:
                # Connection lost: soffice crashed, possibly on this document. Try once more
                # on a fresh instance, in case the instance was already broken.
                log.warning("LibreOffice instance failed mid-conversion", extra={"fields": {"instance": instance.index, "error": type(exc).__name__}})
                await asyncio.to_thread(instance.kill)
                self._spawn_restart(instance)
                continue
            except BaseException:
                # Cancelled mid-call: the instance is still busy with this document.
                await asyncio.to_thread(instance.kill)
                self._spawn_restart(instance)
                raise
            self._release(instance)
            if not dst.exists() or dst.stat().st_size == 0:
                raise ConversionFailed("LibreOffice produced no output")
            return
        raise ConversionFailed("LibreOffice crashed while converting the document")

    def _release(self, instance: _Instance) -> None:
        instance.conversions += 1
        if instance.conversions >= self._settings.lo_max_conversions:
            # Recycle periodically so long-lived instances cannot grow without limit.
            self._spawn_restart(instance)
        else:
            self._queue.put_nowait(instance)
