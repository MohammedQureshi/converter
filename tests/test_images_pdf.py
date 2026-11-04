"""Stage 3: PDF input and raster images, including the fidelity rules."""

from __future__ import annotations

import io
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pikepdf
import pytest
from conftest import assert_valid_pdfa, convert, start_service
from fixtures.generate import (
    EXPECTATIONS,
    TITLE,
    animated_gif,
    encrypted_pdf,
    exif_jpeg,
    icc_v4_profile,
    jpeg_with_icc,
    make_pdf,
    picture,
    png_bytes,
    rgba_png,
)
from PIL import Image

RASTER_FORMATS = ["jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp"]


@dataclass
class EmbeddedImage:
    filter: str
    colorspace: str
    raw: bytes
    has_smask: bool


def page_images(path: Path) -> list[EmbeddedImage]:
    with pikepdf.open(path) as pdf:
        return [
            EmbeddedImage(str(obj.get("/Filter")), str(obj.get("/ColorSpace")), obj.read_raw_bytes(), "/SMask" in obj)
            for obj in pdf.objects
            if isinstance(obj, pikepdf.Stream) and obj.get("/Subtype") == "/Image"
        ]


def page_size(path: Path, index: int = 0) -> tuple[float, float]:
    with pikepdf.open(path) as pdf:
        box = pdf.pages[index].mediabox
        return float(box[2]) - float(box[0]), float(box[3]) - float(box[1])


def rendered_page(path: Path, dpi: int = 72) -> Image.Image:
    out = path.with_suffix(".render.png")
    subprocess.run(
        ["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=png16m", f"-r{dpi}", "-dFirstPage=1", "-dLastPage=1", f"-sOutputFile={out}", str(path)],
        check=True, timeout=60,
    )
    return Image.open(out).convert("RGB")


# ---- every format ---------------------------------------------------------------


@pytest.mark.parametrize("ext", RASTER_FORMATS + ["pdf"])
def test_format_converts_to_pdfa(api, samples, tmp_path, ext):
    response = convert(api, f"sample.{ext}", samples[ext].read_bytes())
    out = assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-source-format"] == ext
    assert response.headers["x-pdfa-validated"] == "true"
    expect = EXPECTATIONS[ext]
    assert expect.min_pages <= int(response.headers["x-page-count"]) <= expect.max_pages
    with pikepdf.open(out) as pdf:
        assert pdf.pages


# ---- JPEG fidelity ---------------------------------------------------------------


def _embedded_jpeg(path: Path) -> bytes:
    streams = [image for image in page_images(path) if image.filter == "/DCTDecode"]
    assert streams, "no JPEG stream in the output"
    return streams[0].raw


def test_jpeg_is_embedded_byte_for_byte(api, samples, tmp_path):
    original = samples["jpg"].read_bytes()
    out = assert_valid_pdfa(convert(api, "photo.jpg", original), tmp_path)
    assert _embedded_jpeg(out) == original


def test_jpeg_with_v2_icc_profile_is_untouched_and_keeps_its_colours(api, tmp_path):
    """Ghostscript would re-encode this, so images must not go through it."""
    profile = Path("/usr/share/color/icc/ghostscript/a98.icc").read_bytes()
    original = jpeg_with_icc(profile)
    out = assert_valid_pdfa(convert(api, "adobe.jpg", original), tmp_path)
    assert _embedded_jpeg(out) == original
    assert "/ICCBased" in page_images(out)[0].colorspace


def test_jpeg_with_v4_icc_profile_is_converted_to_stay_compliant(api, tmp_path):
    """PDF/A-1 cannot hold ICC v4, so this is the one colour case that must be re-encoded."""
    response = convert(api, "v4.jpg", jpeg_with_icc(icc_v4_profile()))
    assert_valid_pdfa(response, tmp_path)


def test_cmyk_jpeg_is_converted_to_stay_compliant(api, tmp_path):
    buffer = io.BytesIO()
    picture().convert("CMYK").save(buffer, "JPEG", quality=90)
    out = assert_valid_pdfa(convert(api, "cmyk.jpg", buffer.getvalue()), tmp_path)
    assert page_images(out)[0].colorspace != "/DeviceCMYK"


# ---- lossless images and transparency ---------------------------------------------


def test_png_pixels_are_preserved_exactly(api, samples, tmp_path):
    response = convert(api, "image.png", samples["png"].read_bytes())
    out = assert_valid_pdfa(response, tmp_path)
    assert page_images(out)[0].filter == "/FlateDecode"
    assert rendered_page(out, dpi=150).tobytes() == picture().tobytes()


def test_png_with_alpha_is_flattened_onto_white(api, tmp_path):
    out = assert_valid_pdfa(convert(api, "alpha.png", rgba_png(128)), tmp_path)
    assert not any(image.has_smask for image in page_images(out))
    red, green, blue = rendered_page(out).getpixel((10, 10))
    assert red >= 250 and 120 <= green <= 135 and 120 <= blue <= 135, (red, green, blue)


def test_gray_alpha_png_is_flattened(api, tmp_path):
    image = Image.new("RGBA", (60, 60), (0, 0, 255, 0)).convert("LA")
    out = assert_valid_pdfa(convert(api, "la.png", png_bytes(image)), tmp_path)
    assert rendered_page(out).getpixel((5, 5)) == (255, 255, 255)


def test_palette_png_with_transparency_is_flattened(api, tmp_path):
    image = Image.new("P", (60, 60), 1)
    image.putpalette([0, 0, 0, 255, 0, 0])
    buffer = io.BytesIO()
    image.save(buffer, "PNG", transparency=1)
    out = assert_valid_pdfa(convert(api, "palette.png", buffer.getvalue()), tmp_path)
    assert rendered_page(out).getpixel((5, 5)) == (255, 255, 255)


def test_16_bit_png_stays_compliant(api, tmp_path):
    image = Image.linear_gradient("L").resize((64, 64)).convert("I;16")
    assert_valid_pdfa(convert(api, "deep.png", png_bytes(image)), tmp_path)


# ---- geometry ---------------------------------------------------------------------


def test_dpi_sets_the_physical_page_size(api, tmp_path):
    """320 x 240 px at 150 dpi is 153.6 x 115.2 points."""
    buffer = io.BytesIO()
    picture().save(buffer, "PNG", dpi=(150, 150))
    out = assert_valid_pdfa(convert(api, "dpi.png", buffer.getvalue()), tmp_path)
    width, height = page_size(out)
    assert width == pytest.approx(153.6, abs=0.5) and height == pytest.approx(115.2, abs=0.5)


def test_exif_rotation_is_respected_without_re_encoding(api, tmp_path):
    original = exif_jpeg(6)  # 200 x 100 stored, displays as 100 x 200
    out = assert_valid_pdfa(convert(api, "rotated.jpg", original), tmp_path)
    assert _embedded_jpeg(out) == original
    with pikepdf.open(out) as pdf:
        assert int(pdf.pages[0].get("/Rotate", 0)) in (90, 270)
    rendered = rendered_page(out)
    assert rendered.height > rendered.width


def test_exif_mirroring_is_respected(api, tmp_path):
    """/Rotate cannot express a mirror image, so the pixels are transposed losslessly."""
    response = convert(api, "mirrored.jpg", exif_jpeg(5))
    out = assert_valid_pdfa(response, tmp_path)
    rendered = rendered_page(out)
    assert rendered.height > rendered.width


def test_multi_page_tiff_gives_one_page_per_frame(api, samples, tmp_path):
    response = convert(api, "scan.tiff", samples["tiff"].read_bytes())
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-page-count"] == "3"


def test_multi_page_tiff_with_alpha_frame(api, tmp_path):
    buffer = io.BytesIO()
    frames = [picture().convert("RGBA"), picture().convert("L")]
    frames[0].save(buffer, "TIFF", save_all=True, append_images=frames[1:], compression="tiff_deflate")
    response = convert(api, "alpha.tif", buffer.getvalue())
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-page-count"] == "2"


def test_group4_tiff_is_passed_through(api, tmp_path):
    buffer = io.BytesIO()
    picture().convert("1").save(buffer, "TIFF", compression="group4")
    out = assert_valid_pdfa(convert(api, "fax.tif", buffer.getvalue()), tmp_path)
    assert "CCITTFaxDecode" in page_images(out)[0].filter


def test_animated_gif_uses_first_frame_only(api, tmp_path):
    response = convert(api, "anim.gif", animated_gif())
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-page-count"] == "1"


def test_animated_webp_uses_first_frame_only(api, tmp_path):
    buffer = io.BytesIO()
    frames = [Image.new("RGB", (50, 50), color) for color in ("red", "green", "blue")]
    frames[0].save(buffer, "WEBP", save_all=True, append_images=frames[1:], duration=100, lossless=True)
    out = assert_valid_pdfa(convert(api, "anim.webp", buffer.getvalue()), tmp_path)
    assert page_count(out) == 1
    red, green, blue = rendered_page(out).getpixel((5, 5))
    assert red > 200 and green < 50 and blue < 50


@pytest.mark.parametrize("size", [(1, 1), (30000, 4)])
def test_extreme_image_sizes_produce_legal_pages(api, tmp_path, size):
    """PDF pages must stay between 3 and 14400 points on each side."""
    buffer = io.BytesIO()
    Image.new("L", size, 128).save(buffer, "PNG")
    out = assert_valid_pdfa(convert(api, "extreme.png", buffer.getvalue()), tmp_path)
    width, height = page_size(out)
    assert 3 <= width <= 14400 and 3 <= height <= 14400


def page_count(path: Path) -> int:
    with pikepdf.open(path) as pdf:
        return len(pdf.pages)


# ---- configured page size ---------------------------------------------------------


@pytest.fixture(scope="module")
def a4_service():
    service = start_service("a4", {"DEFAULT_PAGE_SIZE": "A4", "LO_POOL_SIZE": "1"})
    yield service
    service.stop()


def test_a4_mode_uses_an_a4_page_oriented_to_the_image(a4_service, tmp_path):
    buffer = io.BytesIO()
    picture().save(buffer, "PNG", dpi=(150, 150))  # landscape
    with a4_service.client() as client:
        out = assert_valid_pdfa(convert(client, "small.png", buffer.getvalue()), tmp_path)
    assert page_size(out) == pytest.approx((841.89, 595.28), abs=1)


def test_a4_mode_shrinks_oversized_images_to_fit(a4_service, tmp_path):
    buffer = io.BytesIO()
    picture((3000, 4000)).save(buffer, "PNG", dpi=(72, 72))
    with a4_service.client() as client:
        out = assert_valid_pdfa(convert(client, "big.png", buffer.getvalue()), tmp_path)
    assert page_size(out) == pytest.approx((595.28, 841.89), abs=1)


# ---- PDF input ----------------------------------------------------------------------


def test_pdf_keeps_page_count_and_title(api, samples, tmp_path):
    out = assert_valid_pdfa(convert(api, "input.pdf", samples["pdf"].read_bytes()), tmp_path)
    with pikepdf.open(out) as pdf, pdf.open_metadata() as meta:
        assert len(pdf.pages) == 2
        assert meta["dc:title"] == TITLE
        assert meta["dc:source"] == "input.pdf"


def test_pdf_with_javascript_and_attachment_drops_them(api, tmp_path):
    source = make_pdf(tmp_path / "active.pdf", pages=1)
    with pikepdf.open(source, allow_overwriting_input=True) as pdf:
        pdf.Root.Names = pikepdf.Dictionary(
            JavaScript=pikepdf.Dictionary(
                Names=pikepdf.Array(["run", pikepdf.Dictionary(S=pikepdf.Name.JavaScript, JS=pikepdf.String("app.alert(1)"))])
            )
        )
        pdf.attachments["note.txt"] = pikepdf.AttachedFileSpec(pdf, b"attached", mime_type="text/plain")
        pdf.save(source)
    out = assert_valid_pdfa(convert(api, "active.pdf", source.read_bytes()), tmp_path)
    with pikepdf.open(out) as pdf:
        assert "/JavaScript" not in str(pdf.Root.get("/Names", ""))
        assert len(pdf.attachments) == 0
    assert b"app.alert" not in out.read_bytes()


def test_pdf_with_form_fields_stays_compliant(api, tmp_path):
    from reportlab.pdfgen import canvas

    source = tmp_path / "form.pdf"
    document = canvas.Canvas(str(source))
    document.drawString(72, 720, "Form with a field")
    document.acroForm.textfield(name="field", x=72, y=650, width=200, height=20, value="Filled in")
    document.linkURL("https://example.test/", (72, 700, 200, 730))
    document.showPage()
    document.save()
    assert_valid_pdfa(convert(api, "form.pdf", source.read_bytes()), tmp_path, "form-out.pdf")


def test_pdf_with_layers_and_actions_stays_compliant(api, tmp_path):
    source = make_pdf(tmp_path / "layers.pdf", pages=1)
    with pikepdf.open(source, allow_overwriting_input=True) as pdf:
        layer = pdf.make_indirect(pikepdf.Dictionary(Type=pikepdf.Name.OCG, Name=pikepdf.String("Layer")))
        pdf.Root.OCProperties = pikepdf.Dictionary(
            OCGs=pikepdf.Array([layer]),
            D=pikepdf.Dictionary(ON=pikepdf.Array([layer])),
        )
        pdf.Root.OpenAction = pikepdf.Dictionary(S=pikepdf.Name.JavaScript, JS=pikepdf.String("app.alert(1)"))
        pdf.pages[0].AA = pikepdf.Dictionary(
            O=pikepdf.Dictionary(S=pikepdf.Name.JavaScript, JS=pikepdf.String("app.alert(2)"))
        )
        pdf.save(source)
    out = assert_valid_pdfa(convert(api, "layers.pdf", source.read_bytes()), tmp_path, "layers-out.pdf")
    with pikepdf.open(out) as pdf:
        assert "/OCProperties" not in pdf.Root
        assert "/OpenAction" not in pdf.Root or str(pdf.Root.OpenAction.get("/S")) != "/JavaScript"


def test_transparent_pdf_is_flattened_and_reported(api, tmp_path):
    """Ghostscript rasterises pages that use transparency, and callers are told how many."""
    import cairosvg

    pdf = tmp_path / "alpha.pdf"
    cairosvg.svg2pdf(
        bytestring=b'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
        b'<rect width="150" height="150" fill="#f00"/><rect x="50" y="50" width="150" height="150" fill="#00f" fill-opacity="0.5"/></svg>',
        write_to=str(pdf),
    )
    response = convert(api, "alpha.pdf", pdf.read_bytes())
    out = assert_valid_pdfa(response, tmp_path, "flat.pdf")
    assert response.headers["x-flattened-pages"] == "1"
    red, green, blue = rendered_page(out).getpixel((75, 75))
    assert abs(red - 128) < 6 and green < 6 and abs(blue - 128) < 6, (red, green, blue)


def test_password_protected_pdf_is_rejected(api, tmp_path):
    path = encrypted_pdf(tmp_path / "locked.pdf")
    response = convert(api, "locked.pdf", path.read_bytes())
    assert response.status_code == 422
    assert response.json()["error"] == "ENCRYPTED_FILE"


def test_owner_password_pdf_is_rejected(api, tmp_path):
    """It opens without a password but is still encrypted, which PDF/A forbids."""
    path = encrypted_pdf(tmp_path / "restricted.pdf", user_password="", owner_password="owner")
    response = convert(api, "restricted.pdf", path.read_bytes())
    assert response.status_code == 422
    assert response.json()["error"] == "ENCRYPTED_FILE"
