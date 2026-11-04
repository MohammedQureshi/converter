"""SVG to PDF with CairoSVG. EPS goes through Ghostscript (see app.pipeline)."""

from __future__ import annotations

import html
import re
from pathlib import Path

import cairosvg
import pikepdf

from app.errors import CorruptFile

_MAX_PAGE_POINTS = 14400.0  # PDF 1.4 implementation limit
_TITLE = re.compile(rb"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def _render(data: bytes, dst: str, scale: float = 1) -> None:
    # With unsafe=False, CairoSVG refuses XML entities and external DTDs, and resolves
    # every URL except data: to an empty image, so an SVG cannot read files or the network.
    cairosvg.svg2pdf(bytestring=data, write_to=dst, unsafe=False, scale=scale)


def convert_svg(src: str, dst: str) -> str | None:
    """Renders an SVG at its native size. Returns its title, if it has one."""
    data = Path(src).read_bytes()
    try:
        _render(data, dst)
        with pikepdf.open(dst) as pdf:
            box = pdf.pages[0].mediabox
            width, height = float(box[2]) - float(box[0]), float(box[3]) - float(box[1])
        longest = max(width, height)
        if longest > _MAX_PAGE_POINTS:
            _render(data, dst, scale=_MAX_PAGE_POINTS / longest)
        elif 0 < min(width, height) < 3:
            _render(data, dst, scale=3 / min(width, height))
    except Exception as exc:  # noqa: BLE001 - CairoSVG raises many types on malformed input
        raise CorruptFile("The SVG could not be parsed") from exc
    match = _TITLE.search(data[:65536])
    if match:
        title = html.unescape(match.group(1).decode("utf-8", "replace")).strip()
        return title or None
    return None
