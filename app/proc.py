"""Subprocess runner with deadline enforcement. Argument lists only, never a shell."""

from __future__ import annotations

import asyncio
import os
import signal
from dataclasses import dataclass
from pathlib import Path

from app.context import Deadline


@dataclass
class ProcResult:
    returncode: int
    stdout: bytes
    stderr: bytes


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


async def run_process(
    argv: list[str],
    *,
    deadline: Deadline,
    semaphore: asyncio.Semaphore | None = None,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> ProcResult:
    """Runs a command in its own process group; the whole group dies if time runs out.

    Waiting for the semaphore counts against the deadline, since the caller is waiting too.
    """
    try:
        async with asyncio.timeout(deadline.remaining()):
            if semaphore is not None:
                await semaphore.acquire()
            try:
                proc = await asyncio.create_subprocess_exec(
                    *argv,
                    stdin=asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    start_new_session=True,
                    env=env,
                    cwd=cwd,
                )
                try:
                    stdout, stderr = await proc.communicate()
                except BaseException:
                    # Timeout or cancellation: kill the group, and do not leave a zombie.
                    _kill_group(proc.pid)
                    await asyncio.shield(proc.wait())
                    raise
            finally:
                if semaphore is not None:
                    semaphore.release()
    except TimeoutError:
        raise deadline.timeout_error() from None
    return ProcResult(proc.returncode, stdout, stderr)
