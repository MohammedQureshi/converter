"""File type detection from content, using libmagic.

The extension only settles what content cannot: zip containers without a telling
content type, OLE variants that differ by template flag (doc/dot, ppt/pps), and plain
text formats.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from pathlib import Path

import magic
import msoffcrypto
import olefile

from app.errors import CorruptFile, EncryptedFile, UnsupportedFormat
from app.formats import EXTENSION_TO_FAMILY, SUPPORTED_EXTENSIONS, TEXT_EXTENSIONS
from app.util import extension_of

_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"

_DIRECT_MIME = {
    "application/pdf": "pdf",
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/apng": "png",
    "image/gif": "gif",
    "image/bmp": "bmp",
    "image/x-ms-bmp": "bmp",
    "image/tiff": "tif",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heic-sequence": "heic",
    "image/heif": "heif",
    "image/heif-sequence": "heif",
    "image/avif": "avif",
    "image/avif-sequence": "avif",
    "text/rtf": "rtf",
    "application/rtf": "rtf",
    "application/vnd.wordperfect": "wpd",
    "application/wordperfect": "wpd",
    "application/vnd.ms-works": "wps",
}

# Spellings of one format; a caller's chosen spelling is kept in X-Source-Format.
_ALIASES = {
    "jpg": {"jpg", "jpeg"},
    "tif": {"tif", "tiff"},
    "html": {"html", "htm"},
    "heic": {"heic", "heif"},
    "heif": {"heic", "heif"},
}

_OOXML_MAIN_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml": "docx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.template.main+xml": "dotx",
    "application/vnd.ms-word.document.macroenabled.main+xml": "docm",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml": "xlsx",
    "application/vnd.ms-excel.sheet.macroenabled.main+xml": "xlsm",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml": "pptx",
    "application/vnd.openxmlformats-officedocument.presentationml.slideshow.main+xml": "ppsx",
    "application/vnd.ms-visio.drawing.main+xml": "vsdx",
}

_ODF_TYPES = {
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.oasis.opendocument.presentation": "odp",
    "application/vnd.oasis.opendocument.graphics": "odg",
}

_ZIP_OFFICE_EXTENSIONS = {"docx", "dotx", "docm", "xlsx", "xlsm", "pptx", "ppsx", "vsdx", "odt", "ods", "odp", "odg"}
_OLE_EXTENSIONS = {"doc", "dot", "xls", "ppt", "pps", "vsd", "wps", "msg"}
# libmagic has weak signatures for these, so unknown bytes go to LibreOffice to judge.
_WEAK_SIGNATURE_EXTENSIONS = {"wpd", "wps", "vsd"}
_TEXTUAL_MIME_PREFIXES = ("text/",)
_TEXTUAL_MIMES = {"application/json", "application/csv", "application/xml", "image/svg+xml", "message/rfc822"}
_UNKNOWN_BINARY = {"application/octet-stream", "application/x-empty", "inode/x-empty"}


@dataclass(frozen=True)
class Detected:
    fmt: str  # Canonical format: decides the engine and the temp file's extension.
    source_format: str  # Reported in X-Source-Format.
    family: str
    mime: str


def _result(fmt: str, ext: str, mime: str) -> Detected:
    source = ext if ext in _ALIASES.get(fmt, ()) else fmt
    return Detected(fmt=fmt, source_format=source, family=EXTENSION_TO_FAMILY[fmt], mime=mime)


def _inspect_zip(path: Path, ext: str, mime: str, max_uncompressed: int) -> Detected:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if sum(info.file_size for info in archive.infolist()) > max_uncompressed:
                raise CorruptFile("The file expands to an unreasonable size when decompressed")

            if "mimetype" in names:
                odf_type = archive.read("mimetype").decode("ascii", "replace").strip()
                if odf_type in _ODF_TYPES:
                    if "META-INF/manifest.xml" in names and b"encryption-data" in archive.read("META-INF/manifest.xml"):
                        raise EncryptedFile("The document is password-protected")
                    return _result(_ODF_TYPES[odf_type], ext, mime)

            if "[Content_Types].xml" in names:
                content_types = archive.read("[Content_Types].xml").decode("utf-8", "replace").lower()
                for content_type, fmt in _OOXML_MAIN_TYPES.items():
                    if f'"{content_type}"' in content_types:
                        return _result(fmt, ext, mime)
                raise UnsupportedFormat("This Office Open XML document type is not supported")
    except zipfile.BadZipFile:
        if ext in _ZIP_OFFICE_EXTENSIONS:
            raise CorruptFile(f"The .{ext} file is damaged and cannot be read") from None
        raise UnsupportedFormat("Zip archives are not supported") from None

    if ext in _ZIP_OFFICE_EXTENSIONS:
        raise CorruptFile(f"The .{ext} file does not contain a valid document") from None
    raise UnsupportedFormat("Zip archives are not supported")


def _ole_is_encrypted(path: Path) -> bool:
    try:
        with path.open("rb") as handle:
            return bool(msoffcrypto.OfficeFile(handle).is_encrypted())
    except Exception:  # noqa: BLE001 - msoffcrypto rejects any format it does not recognise
        return False


def _inspect_ole(path: Path, ext: str, mime: str) -> Detected:
    try:
        with olefile.OleFileIO(str(path)) as ole:
            streams = {"/".join(parts) for parts in ole.listdir(streams=True, storages=False)}
    except (OSError, olefile.OleFileError, ValueError, IndexError) as exc:
        if ext in _OLE_EXTENSIONS:
            raise CorruptFile(f"The .{ext} file is damaged and cannot be read") from exc
        raise UnsupportedFormat("This file type is not supported") from exc

    top_level = {name.split("/")[0] for name in streams}

    if "EncryptionInfo" in streams or "EncryptedPackage" in streams:
        raise EncryptedFile("The document is password-protected")
    if any(name.startswith("__substg1.0_") or name.startswith("__properties_version1.0") for name in top_level):
        return _result("msg", ext, mime)

    fmt: str | None = None
    if "WordDocument" in top_level:
        fmt = "dot" if ext == "dot" else "doc"
    elif "Workbook" in top_level or "Book" in top_level:
        fmt = "xls"
    elif "PowerPoint Document" in top_level:
        fmt = "pps" if ext == "pps" else "ppt"
    elif "VisioDocument" in top_level:
        fmt = "vsd"
    elif {"CONTENTS", "MN0", "SPELLING"} & top_level or ext == "wps":
        fmt = "wps"

    if fmt is None:
        if ext in _OLE_EXTENSIONS:
            raise CorruptFile(f"The .{ext} file is damaged and cannot be read")
        raise UnsupportedFormat("This OLE container holds an unsupported document type")
    if fmt in {"doc", "dot", "xls", "ppt", "pps"} and _ole_is_encrypted(path):
        raise EncryptedFile("The document is password-protected")
    return _result(fmt, ext, mime)


def _inspect_text(path: Path, ext: str, mime: str) -> Detected:
    head = path.open("rb").read(4096).lstrip(b"\xef\xbb\xbf \t\r\n").lower()

    if ext == "svg":
        if b"<svg" in head or b"<?xml" in head or b"<!doctype svg" in head:
            return _result("svg", ext, mime)
        raise CorruptFile("The .svg file does not contain SVG markup")
    if mime == "image/svg+xml" and ext not in TEXT_EXTENSIONS:
        if not ext:
            return _result("svg", ext, mime)
        raise UnsupportedFormat(f"Files with extension .{ext} are not supported")

    # Legacy Word and Excel exports are often really HTML wearing a .doc or .xls name.
    if ext in {"doc", "xls"} and mime == "text/html":
        return _result("html", "html", mime)

    if ext in TEXT_EXTENSIONS:
        return _result("html" if ext == "htm" else ext, ext, mime)

    if not ext:
        if mime == "text/html":
            return _result("html", "html", mime)
        if mime == "message/rfc822":
            return _result("eml", "eml", mime)
        if mime == "text/csv" or mime == "application/csv":
            return _result("csv", "csv", mime)
        if mime == "text/plain":
            return _result("txt", "txt", mime)
        raise UnsupportedFormat(f"Content type {mime} is not supported")

    if ext in SUPPORTED_EXTENSIONS:
        raise CorruptFile(f"The file is named .{ext} but its content is not a valid {ext.upper()} file")
    raise UnsupportedFormat(f"Files with extension .{ext} are not supported")


def _is_eps(path: Path, ext: str) -> bool:
    head = path.open("rb").read(64)
    if head.startswith(b"\xc5\xd0\xd3\xc6"):  # DOS EPS binary header
        return True
    if head.startswith(b"%!PS"):
        return ext == "eps" or b"EPSF" in head.split(b"\n")[0]
    return False


def detect(path: Path, filename: str | None, max_uncompressed: int = 1_073_741_824) -> Detected:
    """Identifies a file from its content, or raises the matching API error."""
    ext = extension_of(filename)
    if path.stat().st_size == 0:
        raise CorruptFile("The file is empty")

    mime = (magic.from_file(str(path), mime=True) or "application/octet-stream").lower()
    head = path.open("rb").read(8)

    if head.startswith(_OLE_SIGNATURE):
        return _inspect_ole(path, ext, mime)
    if mime in {"application/zip", "application/x-zip-compressed", "application/x-zip"} or head.startswith(b"PK\x03\x04"):
        return _inspect_zip(path, ext, mime, max_uncompressed)
    if mime in _DIRECT_MIME:
        return _result(_DIRECT_MIME[mime], ext, mime)
    if _is_eps(path, ext):
        return _result("eps", ext, mime)
    if mime == "application/postscript":
        raise UnsupportedFormat("PostScript files are not supported; only EPS")
    if mime.startswith(_TEXTUAL_MIME_PREFIXES) or mime in _TEXTUAL_MIMES:
        return _inspect_text(path, ext, mime)
    if mime in _UNKNOWN_BINARY or re.fullmatch(r"application/x-(?:data|garbage)", mime):
        if ext in _WEAK_SIGNATURE_EXTENSIONS:
            return _result(ext, ext, mime)
        if ext in SUPPORTED_EXTENSIONS:
            raise CorruptFile(f"The file is named .{ext} but its content is not a valid {ext.upper()} file")
    raise UnsupportedFormat(f"Content type {mime} is not supported")
