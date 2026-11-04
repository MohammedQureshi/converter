"""Ghostscript pdfwrite: normalises PDF and EPS input to PDF/A-1b."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.config import Settings
from app.context import Deadline
from app.errors import ConversionFailed, CorruptFile
from app.proc import run_process

log = logging.getLogger(__name__)

# -dAutoFilter*=false and the Flate filters stop /prepress from choosing lossy JPEG for
# images that have to be re-encoded. Without them, lossless input would become lossy.
_FIDELITY_FLAGS = [
    "-dPDFSETTINGS=/prepress",
    "-dDownsampleColorImages=false",
    "-dDownsampleGrayImages=false",
    "-dDownsampleMonoImages=false",
    "-dPassThroughJPEGImages=true",
    "-dAutoFilterColorImages=false",
    "-dAutoFilterGrayImages=false",
    "-dColorImageFilter=/FlateEncode",
    "-dGrayImageFilter=/FlateEncode",
    "-dEmbedAllFonts=true",
    "-dSubsetFonts=true",
    "-dAutoRotatePages=/None",
]


class Ghostscript:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.gs_concurrency)

    def _command(self, src: Path, dst: Path, eps: bool) -> list[str]:
        argv: list[str] = []
        if self._settings.memory_limit_bytes:
            argv += ["prlimit", f"--as={self._settings.memory_limit_bytes}"]
        argv += [
            "gs",
            "-dSAFER",
            "-dBATCH",
            "-dNOPAUSE",
            "-dNOOUTERSAVE",
            "-dQUIET",
            f"--permit-file-read={self._settings.pdfa_icc_path.parent}/",
            "-sDEVICE=pdfwrite",
            "-dPDFA=1",
            "-dPDFACompatibilityPolicy=1",
            "-sColorConversionStrategy=RGB",
            "-sProcessColorModel=DeviceRGB",
            "-dCompatibilityLevel=1.4",
            *_FIDELITY_FLAGS,
        ]
        if eps:
            argv.append("-dEPSCrop")
        argv += [f"-sOutputFile={dst}", str(self._settings.pdfa_def_path), str(src)]
        return argv

    async def to_pdfa(self, src: Path, dst: Path, deadline: Deadline, *, eps: bool = False) -> None:
        result = await run_process(self._command(src, dst, eps), deadline=deadline, semaphore=self._semaphore)
        if result.returncode != 0:
            log.warning("Ghostscript failed", extra={"fields": {"rc": result.returncode}})
            raise CorruptFile("The file could not be processed; it may be damaged")
        if not dst.exists() or dst.stat().st_size == 0:
            raise ConversionFailed("Ghostscript produced no output")

    async def check(self, deadline: Deadline) -> bool:
        result = await run_process(["gs", "--version"], deadline=deadline)
        return result.returncode == 0
