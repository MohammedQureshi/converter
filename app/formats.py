"""Supported formats, grouped by family."""

from __future__ import annotations

FAMILIES: dict[str, list[str]] = {
    "word_processing": ["doc", "docx", "dot", "dotx", "docm", "odt", "rtf", "txt", "wpd", "wps"],
    "spreadsheet": ["xls", "xlsx", "xlsm", "ods", "csv"],
    "presentation": ["ppt", "pptx", "pps", "ppsx", "odp"],
    "diagram": ["vsd", "vsdx", "odg"],
    "raster_image": ["jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp"],
    "modern_image": ["heic", "heif", "avif"],
    "vector": ["svg", "eps"],
    "web": ["html", "htm", "md"],
    "email": ["eml", "msg"],
    "pdf": ["pdf"],
}

EXTENSION_TO_FAMILY = {ext: family for family, exts in FAMILIES.items() for ext in exts}
SUPPORTED_EXTENSIONS = frozenset(EXTENSION_TO_FAMILY)
OFFICE_FAMILIES = frozenset({"word_processing", "spreadsheet", "presentation", "diagram"})

# Text formats: libmagic cannot tell these apart, so the extension decides.
TEXT_EXTENSIONS = frozenset({"txt", "csv", "html", "htm", "md", "eml", "svg"})
