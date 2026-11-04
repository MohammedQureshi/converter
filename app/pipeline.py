"""The conversion pipeline.

Stage 1 turns any supported input into a PDF, stage 2 normalises it to PDF/A-1b unless the
engine already wrote PDF/A, and stage 3 optionally validates the result with veraPDF.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

from app import isolate, pdftools
from app.config import Settings
from app.context import Deadline, note_request
from app.detect import Detected, detect
from app.engines import email as email_engine
from app.engines import html as html_engine
from app.engines import images as image_engine
from app.engines import vector as vector_engine
from app.engines.ghostscript import Ghostscript
from app.engines.html import Chromium
from app.engines.libreoffice import LibreOfficePool, prepare_text_input
from app.engines.verapdf import VeraPdf
from app.errors import ApiError, ConversionTimeout, CorruptFile, PdfaValidationFailed, TooManyPages, UnsupportedFormat
from app.formats import OFFICE_FAMILIES
from app.util import decode_text, safe_filename

log = logging.getLogger(__name__)


@dataclass
class Engines:
    libreoffice: LibreOfficePool
    ghostscript: Ghostscript
    chromium: Chromium
    verapdf: VeraPdf


@dataclass
class Stage1Result:
    pdf: Path
    is_pdfa: bool = False
    title: str | None = None
    expected_pages: int | None = None
    attachments_skipped: int = 0
    strip_tags: bool = False


@dataclass
class ConversionResult:
    pdf: Path
    source_format: str
    pages: int
    size_bytes: int
    validated: bool | None  # None means validation was skipped.
    conversion_ms: int
    title: str | None = None
    attachments_skipped: int = 0
    flattened_pages: int = 0
    validation_failures: list[str] = field(default_factory=list)


class Pipeline:
    def __init__(self, settings: Settings, engines: Engines) -> None:
        self.settings = settings
        self.engines = engines

    async def convert(self, src: Path, filename: str, work_dir: Path, *, validate: bool | None) -> ConversionResult:
        started = time.monotonic()
        deadline = Deadline(self.settings.conversion_timeout_seconds)
        display_name = safe_filename(filename)

        detected = await self._detect(src, display_name, deadline)
        note_request(format=detected.source_format, inputBytes=src.stat().st_size)
        stage1 = await self._stage1(src, detected, work_dir, deadline, depth=0)
        pdf = stage1.pdf

        # Stage 2
        used_ghostscript = not stage1.is_pdfa
        if used_ghostscript:
            pdfa = work_dir / "normalised.pdf"
            await self.engines.ghostscript.to_pdfa(pdf, pdfa, deadline)
            pdf = pdfa

        final_path = work_dir / "output.pdf"
        final = await isolate.run(
            pdftools.finalize_pdf,
            str(pdf),
            str(final_path),
            display_name,
            stage1.title,
            used_ghostscript,
            stage1.strip_tags,
            deadline=deadline,
        )
        pages = final["pages"]
        if pages > self.settings.max_pages:
            raise TooManyPages(f"The document has {pages} pages; the limit is {self.settings.max_pages}")
        if stage1.expected_pages is not None and pages != stage1.expected_pages:
            # Returning a silently shortened document would be worse than an error.
            log.warning("Page count changed", extra={"fields": {"expected": stage1.expected_pages, "actual": pages}})
            raise CorruptFile(f"Only {pages} of {stage1.expected_pages} pages could be processed; the PDF may be damaged")

        # Stage 3
        run_validation = self.settings.validate_default if validate is None else validate
        validated: bool | None = None
        failures: list[str] = []
        if run_validation:
            report = await self.engines.verapdf.validate(final_path, deadline)
            validated, failures = report.compliant, report.failures
            if not validated:
                log.warning("PDF/A validation failed", extra={"fields": {"failedRules": failures[:10]}})
                if self.settings.strict_validation:
                    raise PdfaValidationFailed("The output did not pass PDF/A-1b validation: " + "; ".join(failures[:3]))

        return ConversionResult(
            pdf=final_path,
            source_format=detected.source_format,
            pages=pages,
            size_bytes=final_path.stat().st_size,
            validated=validated,
            conversion_ms=round((time.monotonic() - started) * 1000),
            title=final["title"],
            attachments_skipped=stage1.attachments_skipped,
            flattened_pages=final["flattened_pages"],
            validation_failures=failures,
        )

    async def _detect(self, path: Path, name: str, deadline: Deadline) -> Detected:
        detected: Detected = await isolate.run(detect, path, name, self.settings.max_uncompressed_bytes, deadline=deadline)
        if detected.fmt == "msg" and not self.settings.enable_msg:
            raise UnsupportedFormat("Outlook .msg files are not enabled on this service")
        return detected

    async def _stage1(self, src: Path, detected: Detected, work_dir: Path, deadline: Deadline, depth: int) -> Stage1Result:
        family = detected.family
        if family in OFFICE_FAMILIES:
            return await self._office(src, detected, work_dir, deadline)
        if family in {"raster_image", "modern_image"}:
            return await self._image(src, work_dir, deadline)
        if detected.fmt == "svg":
            out = work_dir / "stage1.pdf"
            title = await isolate.run(vector_engine.convert_svg, str(src), str(out), deadline=deadline)
            return Stage1Result(pdf=out, title=title)
        if detected.fmt == "eps":
            return await self._eps(src, work_dir, deadline)
        if family == "web":
            return await self._web(src, detected, work_dir, deadline)
        if family == "email":
            return await self._email(src, detected, work_dir, deadline, depth)
        if family == "pdf":
            info = await isolate.run(pdftools.inspect_pdf, str(src), deadline=deadline)
            self._check_pages(info["pages"])
            return Stage1Result(pdf=src, title=info["title"], expected_pages=info["pages"])
        raise AssertionError(f"Unrouted family {family}")

    def _check_pages(self, pages: int) -> None:
        if pages > self.settings.max_pages:
            raise TooManyPages(f"The document has {pages} pages; the limit is {self.settings.max_pages}")

    async def _office(self, src: Path, detected: Detected, work_dir: Path, deadline: Deadline) -> Stage1Result:
        # LibreOffice picks its import filter partly from the name, so it gets the real format.
        named = work_dir / f"office-input.{detected.fmt}"
        if detected.fmt in {"txt", "csv"}:
            await isolate.run(prepare_text_input, str(src), str(named), detected.fmt == "csv", deadline=deadline)
        else:
            named.hardlink_to(src)
        out = work_dir / "office-output.pdf"
        await self.engines.libreoffice.convert(named, out, deadline)
        # LibreOffice's PDF/A export is used directly, so the file is not rewritten twice,
        # except in the one case where it is known to be non-compliant.
        fonts_need_repair = await isolate.run(pdftools.has_type1_font_without_charset, str(out), deadline=deadline)
        # LibreOffice forces tags on in PDF/A-1 mode, and for a spreadsheet that means several
        # uncompressible objects per cell: a 4,500-row sheet became 9 MB and took 8 seconds to
        # validate. PDF/A-1b does not require tags, so spreadsheets drop them.
        return Stage1Result(pdf=out, is_pdfa=not fonts_need_repair, strip_tags=detected.family == "spreadsheet")

    async def _image(self, src: Path, work_dir: Path, deadline: Deadline) -> Stage1Result:
        out = work_dir / "image.pdf"
        result = await isolate.run(
            image_engine.convert_image,
            str(src),
            str(out),
            str(work_dir),
            self.settings.page_size_points,
            self.settings.max_pages,
            self.settings.max_image_pixels,
            str(self.settings.pdfa_icc_path),
            deadline=deadline,
        )
        return Stage1Result(pdf=out, is_pdfa=result["is_pdfa"])

    async def _eps(self, src: Path, work_dir: Path, deadline: Deadline) -> Stage1Result:
        # Ghostscript is the stage 1 engine and writes PDF/A in the same pass, so a second
        # pass would only add latency.
        out = work_dir / "eps.pdf"
        named = work_dir / "input.eps"
        named.hardlink_to(src)
        await self.engines.ghostscript.to_pdfa(named, out, deadline, eps=True)
        return Stage1Result(pdf=out, is_pdfa=True)

    async def _web(self, src: Path, detected: Detected, work_dir: Path, deadline: Deadline) -> Stage1Result:
        if detected.fmt == "md":
            html = await isolate.run(_read_markdown, str(src), deadline=deadline)
        else:
            html = await isolate.run(_read_html, str(src), deadline=deadline)
        out = work_dir / "web.pdf"
        await self.engines.chromium.render(html, out, deadline)
        return Stage1Result(pdf=out)

    async def _email(self, src: Path, detected: Detected, work_dir: Path, deadline: Deadline, depth: int) -> Stage1Result:
        email_dir = work_dir / f"email-{depth}-{src.stem}"
        email_dir.mkdir()
        parsed = await isolate.run(
            email_engine.parse_email,
            str(src),
            detected.fmt,
            str(email_dir),
            self.settings.max_email_attachments,
            deadline=deadline,
        )
        notes = [{"name": s["name"], "reason": s["reason"]} for s in parsed["skipped"]]
        skipped = len(notes)
        parts: list[Path] = []
        for attachment in parsed["attachments"]:
            name, reason, pdf, nested_skips = await self._attachment(attachment, email_dir, deadline, depth)
            notes.append({"name": name, "reason": reason})
            if pdf is not None:
                parts.append(pdf)
            else:
                skipped += 1
            skipped += nested_skips

        cover_html = email_engine.render_cover(parsed, notes)
        cover = email_dir / "cover.pdf"
        await self.engines.chromium.render(cover_html, cover, deadline, allow_js=False)

        merged = email_dir / "merged.pdf"
        pages = await isolate.run(
            pdftools.merge_pdfs, [str(p) for p in [cover, *parts]], str(merged), deadline=deadline
        )
        self._check_pages(pages)
        return Stage1Result(pdf=merged, title=parsed.get("subject") or None, attachments_skipped=skipped)

    async def _attachment(
        self, attachment: dict, email_dir: Path, deadline: Deadline, depth: int
    ) -> tuple[str, str | None, Path | None, int]:
        """Converts one attachment. A bad attachment is noted on the cover and does not fail the email."""
        name, path = attachment["name"], Path(attachment["path"])
        directory = path.with_suffix("")
        directory.mkdir()
        try:
            detected = await self._detect(path, name, deadline)
            if detected.family == "email" and depth + 1 > self.settings.max_email_depth:
                return name, f"nested more than {self.settings.max_email_depth} levels deep", None, 0
            result = await self._stage1(path, detected, directory, deadline, depth + 1)
            return name, None, result.pdf, result.attachments_skipped
        except ConversionTimeout:
            raise
        except ApiError as exc:
            log.info("Attachment not converted", extra={"fields": {"code": exc.code}})
            return name, exc.message, None, 0


def _read_markdown(path: str) -> str:
    return html_engine.markdown_to_html(decode_text(Path(path).read_bytes()))


def _read_html(path: str) -> str:
    return html_engine.read_html(Path(path))

