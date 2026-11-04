"""Raster images to PDF, using Pillow, img2pdf and pillow-heif.

JPEG, PNG and TIFF data is embedded without re-encoding whenever PDF/A-1 allows it.
img2pdf writes PDF/A-1b directly, which matters because Ghostscript would decode and
re-encode any JPEG that carries an ICC profile (measured: 319 KB became 1.39 MB). Only
images PDF/A-1 cannot hold as they are go on to Ghostscript for conversion:

* CMYK, because the file's OutputIntent is sRGB
* ICC v4 profiles, because PDF/A-1 is limited to ICC v2
* 16 bits per channel, because PDF 1.4 tops out at 8
"""

from __future__ import annotations

import warnings
from pathlib import Path

import img2pdf
import pillow_heif
from PIL import Image, ImageOps

from app.errors import CorruptFile, TooManyPages

pillow_heif.register_heif_opener()

_MAX_PAGE_POINTS = 14400.0  # PDF 1.4 implementation limit
_MIN_PAGE_POINTS = 3.0
_DEFAULT_DPI = 96.0
_MIRRORED_ORIENTATIONS = {2, 4, 5, 7}  # /Rotate can express rotation, but not a mirror image


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in {"RGBA", "LA", "PA", "RGBa", "La"} or "transparency" in image.info


def _flatten(image: Image.Image) -> Image.Image:
    """PDF/A-1 forbids transparency, so composite onto white."""
    info = dict(image.info)
    grayscale = image.mode in {"L", "LA", "La", "I;16", "I", "1"}
    rgba = image.convert("LA" if grayscale else "RGBA")
    background = Image.new("L" if grayscale else "RGB", rgba.size, 255 if grayscale else (255, 255, 255))
    background.paste(rgba.convert("L" if grayscale else "RGB"), mask=rgba.getchannel("A"))
    for key in ("dpi", "icc_profile"):
        if key in info:
            background.info[key] = info[key]
    return background


def _icc_major(profile: bytes | None) -> int:
    return profile[8] if profile and len(profile) > 8 else 0


def _orientation(image: Image.Image) -> int:
    try:
        return int(image.getexif().get(0x0112, 1) or 1)
    except Exception:  # noqa: BLE001 - malformed EXIF just means no orientation
        return 1


def _png_is_16bit(path: Path) -> bool:
    with path.open("rb") as handle:
        header = handle.read(26)
    return len(header) >= 25 and header[:8] == b"\x89PNG\r\n\x1a\n" and header[24] == 16


def _save_png(image: Image.Image, path: Path) -> Path:
    kwargs = {}
    if image.info.get("dpi"):
        kwargs["dpi"] = image.info["dpi"]
    if image.info.get("icc_profile"):
        kwargs["icc_profile"] = image.info["icc_profile"]
    if image.mode not in {"1", "L", "P", "RGB", "I;16"}:
        image = image.convert("RGB")
    image.save(path, "PNG", **kwargs)
    return path


def _normalise_frame(image: Image.Image, dpi: tuple | None) -> Image.Image:
    """Applies EXIF orientation and removes transparency from a decoded frame."""
    frame = ImageOps.exif_transpose(image)
    frame.info.setdefault("icc_profile", image.info.get("icc_profile"))
    if dpi:
        frame.info["dpi"] = dpi
    return _flatten(frame) if _has_alpha(frame) else frame


def _native_layout(width_px, height_px, dpi):
    """Native page size from pixel size and DPI, clamped to PDF's page size limits."""
    dpi_x = dpi[0] if dpi and dpi[0] and dpi[0] > 1 else _DEFAULT_DPI
    dpi_y = dpi[1] if dpi and dpi[1] and dpi[1] > 1 else _DEFAULT_DPI
    width, height = width_px * 72.0 / dpi_x, height_px * 72.0 / dpi_y
    longest = max(width, height)
    if longest > _MAX_PAGE_POINTS:
        width, height = width * _MAX_PAGE_POINTS / longest, height * _MAX_PAGE_POINTS / longest
    width, height = max(width, _MIN_PAGE_POINTS), max(height, _MIN_PAGE_POINTS)
    return width, height, width, height


def convert_image(
    src: str,
    dst: str,
    work_dir: str,
    page_size_points: tuple[float, float] | None,
    max_pages: int,
    max_pixels: int,
    pdfa_icc_path: str,
) -> dict:
    """Writes a PDF to `dst`. Returns {"is_pdfa": True} when no Ghostscript pass is needed."""
    Image.MAX_IMAGE_PIXELS = max_pixels
    source = Path(src)
    tmp = Path(work_dir)
    needs_conversion = False
    inputs: list[str] = []

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(source) as image:
                image_format = (image.format or "").upper()
                frames = getattr(image, "n_frames", 1) if image_format == "TIFF" else 1
                if frames > max_pages:
                    raise TooManyPages(f"The image has {frames} pages; the limit is {max_pages}")

                if image_format == "JPEG":
                    image.load()  # Finds truncated data, which img2pdf would embed blindly.
                    if _orientation(image) in _MIRRORED_ORIENTATIONS:
                        inputs.append(str(_save_png(_normalise_frame(image, image.info.get("dpi")), tmp / "image.png")))
                        needs_conversion = _icc_major(image.info.get("icc_profile")) > 2
                    else:
                        inputs.append(src)
                        needs_conversion = image.mode == "CMYK" or _icc_major(image.info.get("icc_profile")) > 2

                elif image_format == "PNG":
                    image.load()
                    is_16bit = _png_is_16bit(source)
                    if _has_alpha(image) or _orientation(image) != 1:
                        inputs.append(str(_save_png(_normalise_frame(image, image.info.get("dpi")), tmp / "image.png")))
                    else:
                        inputs.append(src)
                        needs_conversion = is_16bit
                    needs_conversion = needs_conversion or _icc_major(image.info.get("icc_profile")) > 2

                elif image_format == "TIFF":
                    needs_rewrite = False
                    for index in range(frames):
                        image.seek(index)
                        image.load()
                        if _has_alpha(image) or _orientation(image) in _MIRRORED_ORIENTATIONS:
                            needs_rewrite = True
                        if image.mode == "CMYK" or image.mode.startswith("I;16") or image.mode in {"I", "F"}:
                            needs_conversion = True
                        if _icc_major(image.info.get("icc_profile")) > 2:
                            needs_conversion = True
                    if needs_rewrite:
                        for index in range(frames):
                            image.seek(index)
                            frame = _normalise_frame(image, image.info.get("dpi"))
                            inputs.append(str(_save_png(frame, tmp / f"frame-{index:05d}.png")))
                    else:
                        inputs.append(src)

                else:
                    # GIF, BMP, WebP, HEIC and AVIF cannot be embedded directly, so frame 0 is
                    # decoded to lossless PNG. Animated files intentionally lose later frames.
                    image.seek(0)
                    image.load()
                    icc = image.info.get("icc_profile")
                    inputs.append(str(_save_png(_normalise_frame(image, image.info.get("dpi")), tmp / "image.png")))
                    needs_conversion = _icc_major(icc) > 2
    except (TooManyPages, CorruptFile):
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise CorruptFile("The image dimensions exceed the allowed limit") from None
    except (OSError, ValueError, SyntaxError, EOFError) as exc:
        raise CorruptFile("The image is damaged and cannot be read") from exc

    if page_size_points:
        layout = img2pdf.get_layout_fun(
            pagesize=page_size_points, fit=img2pdf.FitMode.shrink, auto_orient=True
        )
    else:
        layout = _native_layout

    options = {"layout_fun": layout, "rotation": img2pdf.Rotation.ifvalid}
    if not needs_conversion:
        options["pdfa"] = pdfa_icc_path
    try:
        Path(dst).write_bytes(img2pdf.convert(*inputs, **options))
    except (img2pdf.ImageOpenError, img2pdf.AlphaChannelError, ValueError, OSError) as exc:
        raise CorruptFile("The image could not be embedded in a PDF") from exc
    return {"is_pdfa": not needs_conversion}
