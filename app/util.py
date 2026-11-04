"""Small helpers shared across the service."""

from __future__ import annotations

import re
import unicodedata
from pathlib import PurePosixPath, PureWindowsPath
from urllib.parse import quote

_UNSAFE = re.compile(r"[\x00-\x1f\x7f-\x9f]|[￰-￿]")


def safe_filename(name: str | None, default: str = "document") -> str:
    """The display name of an upload, with any path or control characters removed.

    The result only goes into metadata and response headers. Engines never see it: they
    read a generated `input.<ext>` file inside the request's temp directory.
    """
    if not name:
        return default
    name = PureWindowsPath(PurePosixPath(name).name).name
    name = unicodedata.normalize("NFC", _UNSAFE.sub("", name)).strip().strip(".")
    return name[:200] or default


def extension_of(name: str | None) -> str:
    if not name or "." not in name:
        return ""
    ext = name.rsplit(".", 1)[-1].lower()
    return ext if ext.isalnum() and len(ext) <= 8 else ""


def content_disposition(filename: str) -> str:
    """An attachment header with an ASCII fallback plus the RFC 5987 UTF-8 name."""
    stem = filename.rsplit(".", 1)[0] if "." in filename else filename
    ascii_stem = re.sub(r"[^A-Za-z0-9._ -]", "_", stem).strip() or "document"
    utf8 = quote(f"{stem}.pdf", safe="")
    return f"attachment; filename=\"{ascii_stem}.pdf\"; filename*=UTF-8''{utf8}"


def _looks_western_single_byte(data: bytes) -> bool:
    """Accented Western text has isolated high bytes; multi-byte encodings have runs of them.

    Statistical detection is unreliable on short text ("Köln" in Windows-1252 was read as
    Big5), so this clear-cut case is settled before it gets that far.
    """
    runs = re.findall(rb"[\x80-\xff]+", data)
    if not runs:
        return True
    return sum(1 for run in runs if len(run) == 1) / len(runs) >= 0.9


def decode_text(data: bytes) -> str:
    """Decodes text of unknown encoding: BOM, then strict UTF-8, then detection."""
    for bom, encoding in (
        (b"\xef\xbb\xbf", "utf-8-sig"),
        (b"\xff\xfe\x00\x00", "utf-32"),
        (b"\x00\x00\xfe\xff", "utf-32"),
        (b"\xff\xfe", "utf-16"),
        (b"\xfe\xff", "utf-16"),
    ):
        if data.startswith(bom):
            return data.decode(encoding, errors="replace")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        pass
    if _looks_western_single_byte(data):
        return data.decode("cp1252", errors="replace")
    from charset_normalizer import from_bytes

    best = from_bytes(data[:262_144]).best()
    if best is not None:
        return data.decode(best.encoding, errors="replace")
    return data.decode("cp1252", errors="replace")
