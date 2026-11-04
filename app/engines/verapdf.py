"""veraPDF validation against the PDF/A-1b profile."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

from app.config import Settings
from app.context import Deadline
from app.proc import run_process

log = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    compliant: bool
    failures: list[str] = field(default_factory=list)


class VeraPdf:
    def __init__(self, settings: Settings) -> None:
        self._semaphore = asyncio.Semaphore(settings.verapdf_concurrency)

    async def validate(self, path: Path, deadline: Deadline) -> ValidationResult:
        result = await run_process(
            ["verapdf", "--flavour", "1b", "--format", "json", "--loglevel", "1", str(path)],
            deadline=deadline,
            semaphore=self._semaphore,
        )
        try:
            return _parse_report(result.stdout)
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            # A validator failure says nothing about the file, but it also proves nothing,
            # so it counts as "not validated".
            log.error(
                "veraPDF returned no usable report",
                extra={"fields": {"rc": result.returncode, "error": type(exc).__name__}},
            )
            return ValidationResult(compliant=False, failures=["validator error"])


def _parse_report(stdout: bytes) -> ValidationResult:
    job = json.loads(stdout)["report"]["jobs"][0]
    report = job["validationResult"]
    if isinstance(report, list):
        report = report[0]
    failures = [
        f'{rule["clause"]}-{rule["testNumber"]}: {rule.get("description", "")[:120]}'
        for rule in report["details"]["ruleSummaries"]
        if rule.get("failedChecks")
    ]
    return ValidationResult(compliant=bool(report["compliant"]), failures=failures)
