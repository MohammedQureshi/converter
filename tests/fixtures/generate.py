"""Builds a sample file for every supported format.

Everything is generated here, so no copyrighted documents are involved. The exceptions
are formats no open-source tool can write, which come from tests/fixtures/third_party
(see the NOTICE file there).
"""

from __future__ import annotations

import base64
import io
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path

import openpyxl
from docx import Document
from docx.shared import Inches
from odf.draw import Frame, Page, TextBox
from odf.opendocument import OpenDocumentDrawing, OpenDocumentPresentation, OpenDocumentSpreadsheet, OpenDocumentText
from odf.style import MasterPage, PageLayout, PageLayoutProperties
from odf.table import Table, TableCell, TableRow
from odf.text import H, P
from PIL import Image, ImageCms, ImageDraw
from pptx import Presentation
from pptx.util import Inches as PptxInches
from reportlab.pdfgen import canvas

THIRD_PARTY = Path(__file__).parent / "third_party"
STATIC = Path(__file__).parent / "static"
TITLE = "Fixture Title"
TEXT = "The quick brown fox jumps over the lazy dog"


@dataclass(frozen=True)
class Expect:
    min_pages: int = 1
    max_pages: int = 1


# Expected page count per format.
EXPECTATIONS: dict[str, Expect] = {
    **{ext: Expect(1, 3) for ext in ("doc", "docx", "dot", "dotx", "docm", "odt", "rtf", "txt")},
    "wpd": Expect(1, 3),
    "wps": Expect(1, 3),
    **{ext: Expect(1, 3) for ext in ("xls", "xlsx", "xlsm", "ods", "csv")},
    **{ext: Expect(2, 2) for ext in ("ppt", "pptx", "pps", "ppsx")},
    "odp": Expect(1, 2),
    "vsd": Expect(1, 5),
    "vsdx": Expect(1, 5),
    "odg": Expect(1, 2),
    **{ext: Expect(1, 1) for ext in ("jpg", "jpeg", "png", "gif", "bmp", "webp", "heic", "heif", "avif")},
    "tif": Expect(3, 3),  # multi-page: one page per frame
    "tiff": Expect(3, 3),
    "svg": Expect(1, 1),
    "eps": Expect(1, 1),
    "html": Expect(1, 2),
    "htm": Expect(1, 2),
    "md": Expect(1, 2),
    "eml": Expect(3, 6),  # cover + PNG + DOCX attachments
    "msg": Expect(1, 4),
    "pdf": Expect(2, 2),
}


def picture(size=(320, 240), mode="RGB") -> Image.Image:
    """A gradient with a drawn shape, so lossy re-encoding would be detectable."""
    gradient = Image.linear_gradient("L").resize(size)
    red, green = gradient, gradient.rotate(90, expand=False).resize(size)
    blue = Image.new("L", size, 128)
    image = Image.merge("RGB", (red, green, blue))
    ImageDraw.Draw(image).ellipse([size[0] // 4, size[1] // 4, size[0] // 2, size[1] // 2], fill=(255, 255, 0))
    return image.convert(mode)


def png_bytes(image: Image.Image | None = None, **kwargs) -> bytes:
    buffer = io.BytesIO()
    (image or picture()).save(buffer, "PNG", **kwargs)
    return buffer.getvalue()


def _rewrite_content_type(src: Path, dst: Path, old: str, new: str) -> None:
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "[Content_Types].xml":
                assert old.encode() in data, f"{old} not in content types"
                data = data.replace(old.encode(), new.encode())
            zout.writestr(item, data)


WORD_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"


def make_docx(path: Path, *, pages: int = 1, with_image: bool = True, cjk: bool = True) -> Path:
    document = Document()
    document.core_properties.title = TITLE
    document.add_heading("Fixture document", level=1)
    document.add_paragraph(TEXT + " — Unicode: naïve café Ελληνικά" + (" 中文." if cjk else "."))
    table = document.add_table(rows=2, cols=2)
    for row in table.rows:
        for cell in row.cells:
            cell.text = "cell"
    if with_image:
        document.add_picture(io.BytesIO(png_bytes()), width=Inches(2))
    for page in range(1, pages):
        document.add_page_break()
        document.add_paragraph(f"Page {page + 1}")
    document.save(path)
    return path


def make_xlsx(path: Path, wide: bool = False) -> Path:
    workbook = openpyxl.Workbook()
    workbook.properties.title = TITLE
    sheet = workbook.active
    sheet.title = "Data"
    sheet.append(["Name", "Value", "Note"])
    for index in range(10):
        sheet.append([f"Row {index}", index * 3.5, TEXT])
    if wide:
        for column in range(1, 41):
            sheet.cell(row=1, column=column, value=f"Column {column}")
            sheet.column_dimensions[openpyxl.utils.get_column_letter(column)].width = 18
    workbook.save(path)
    return path


def make_pptx(path: Path) -> Path:
    presentation = Presentation()
    presentation.core_properties.title = TITLE
    for index in range(2):
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = f"Slide {index + 1}"
        slide.placeholders[1].text = TEXT
    slide.shapes.add_picture(io.BytesIO(png_bytes()), PptxInches(1), PptxInches(4), height=PptxInches(1.5))
    presentation.save(path)
    return path


def _make_odt(path: Path) -> Path:
    document = OpenDocumentText()
    document.text.addElement(H(outlinelevel=1, text="Fixture ODT"))
    document.text.addElement(P(text=TEXT))
    document.save(str(path))
    return path


def _make_ods(path: Path) -> Path:
    document = OpenDocumentSpreadsheet()
    table = Table(name="Data")
    for row_index in range(4):
        row = TableRow()
        for column in range(3):
            cell = TableCell()
            cell.addElement(P(text=f"R{row_index}C{column}"))
            row.addElement(cell)
        table.addElement(row)
    document.spreadsheet.addElement(table)
    document.save(str(path))
    return path


def _odf_page_setup(document):
    layout = PageLayout(name="Layout")
    layout.addElement(PageLayoutProperties(pagewidth="28cm", pageheight="21cm", printorientation="landscape"))
    document.automaticstyles.addElement(layout)
    master = MasterPage(name="Standard", pagelayoutname=layout)
    document.masterstyles.addElement(master)
    return master


def _make_odp(path: Path) -> Path:
    document = OpenDocumentPresentation()
    master = _odf_page_setup(document)
    page = Page(masterpagename=master)
    frame = Frame(width="20cm", height="4cm", x="2cm", y="2cm")
    box = TextBox()
    box.addElement(P(text=TEXT))
    frame.addElement(box)
    page.addElement(frame)
    document.presentation.addElement(page)
    document.save(str(path))
    return path


def _make_odg(path: Path) -> Path:
    document = OpenDocumentDrawing()
    master = _odf_page_setup(document)
    page = Page(masterpagename=master)
    frame = Frame(width="20cm", height="4cm", x="2cm", y="2cm")
    box = TextBox()
    box.addElement(P(text=TEXT))
    frame.addElement(box)
    page.addElement(frame)
    document.drawing.addElement(page)
    document.save(str(path))
    return path


def _soffice_convert(src: Path, target: str, out_dir: Path, name: str) -> Path:
    """Legacy binary formats are written by LibreOffice itself."""
    export_dir = out_dir / f"export-{name}"
    export_dir.mkdir(exist_ok=True)
    subprocess.run(
        [
            "soffice", "--headless", "--norestore", "--nologo", "--nofirststartwizard",
            f"-env:UserInstallation=file://{out_dir}/soffice-profile",
            "--convert-to", target, "--outdir", str(export_dir), str(src),
        ],
        check=True, capture_output=True, timeout=120,
    )
    produced = next(export_dir.iterdir())
    final = out_dir / name
    shutil.move(produced, final)
    export_dir.rmdir()
    return final


def make_multipage_tiff(path: Path) -> Path:
    frames = [picture().convert("RGB"), picture().convert("L"), picture().convert("1")]
    frames[0].save(path, "TIFF", save_all=True, append_images=frames[1:], compression="tiff_deflate", dpi=(150, 150))
    return path


def make_svg(path: Path) -> Path:
    path.write_text(
        '<?xml version="1.0"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200" viewBox="0 0 300 200">\n'
        f"<title>{TITLE}</title>\n"
        '<rect x="10" y="10" width="280" height="180" fill="#ddeeff" stroke="#003366"/>\n'
        f'<text x="20" y="100" font-family="Liberation Sans" font-size="14">{TEXT[:30]}</text>\n'
        "</svg>\n",
        encoding="utf-8",
    )
    return path


def make_eps(path: Path) -> Path:
    path.write_text(
        "%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 300 200\n%%Title: Fixture EPS\n%%EndComments\n"
        "0.8 0.9 1 setrgbcolor 10 10 280 180 rectfill\n"
        "0 0 0 setrgbcolor /Helvetica findfont 14 scalefont setfont 20 100 moveto (Fixture EPS text) show\n"
        "showpage\n%%EOF\n",
        encoding="ascii",
    )
    return path


HTML_DOC = (
    '<!doctype html><html><head><meta charset="utf-8"><title>' + TITLE + "</title></head><body>"
    "<h1>Fixture HTML</h1><p>" + TEXT + " 中文 العربية</p>"
    '<table border="1"><tr><td>a</td><td>b</td></tr></table>'
    '<img alt="inline" src="data:image/png;base64,' + base64.b64encode(png_bytes(picture((64, 64)))).decode() + '">'
    "</body></html>"
)


def make_eml(path: Path, attachments_dir: Path) -> Path:
    message = EmailMessage()
    message["Subject"] = "Fixture email subject"
    message["From"] = "Alice Example <alice@example.test>"
    message["To"] = "Bob Example <bob@example.test>"
    message["Date"] = "Wed, 04 Nov 2026 10:00:00 +0000"
    message.set_content("Plain text body. " + TEXT)
    message.add_alternative(
        '<html><body><h2>HTML body</h2><p>' + TEXT + '</p><img src="cid:logo123" alt="logo"></body></html>',
        subtype="html",
    )
    html_part = message.get_body(preferencelist=("html",))
    html_part.add_related(png_bytes(picture((64, 64))), "image", "png", cid="<logo123>", filename="logo.png")
    message.add_attachment(png_bytes(), maintype="image", subtype="png", filename="photo.png")
    docx_path = make_docx(attachments_dir / "attached.docx")
    message.add_attachment(
        docx_path.read_bytes(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="report.docx",
    )
    path.write_bytes(bytes(message))
    return path


def make_pdf(path: Path, pages: int = 2) -> Path:
    document = canvas.Canvas(str(path))
    document.setTitle(TITLE)
    for page in range(pages):
        document.drawString(72, 720, f"{TEXT} — page {page + 1}")
        document.showPage()
    document.save()
    return path


def generate_all(out: Path) -> dict[str, Path]:
    """Writes one sample per supported extension and returns {extension: path}."""
    out.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}

    files["docx"] = make_docx(out / "sample.docx")
    files["xlsx"] = make_xlsx(out / "sample.xlsx")
    files["pptx"] = make_pptx(out / "sample.pptx")
    files["odt"] = _make_odt(out / "sample.odt")
    files["ods"] = _make_ods(out / "sample.ods")
    files["odp"] = _make_odp(out / "sample.odp")
    files["odg"] = _make_odg(out / "sample.odg")

    files["dotx"] = out / "sample.dotx"
    _rewrite_content_type(files["docx"], files["dotx"], WORD_MAIN, WORD_MAIN.replace("document.main", "template.main"))
    files["docm"] = out / "sample.docm"
    _rewrite_content_type(files["docx"], files["docm"], WORD_MAIN, "application/vnd.ms-word.document.macroEnabled.main+xml")
    files["xlsm"] = out / "sample.xlsm"
    _rewrite_content_type(
        files["xlsx"], files["xlsm"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        "application/vnd.ms-excel.sheet.macroEnabled.main+xml",
    )
    files["ppsx"] = out / "sample.ppsx"
    _rewrite_content_type(
        files["pptx"], files["ppsx"],
        "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
        "application/vnd.openxmlformats-officedocument.presentationml.slideshow.main+xml",
    )

    files["doc"] = _soffice_convert(files["docx"], 'doc:MS Word 97', out, "sample.doc")
    files["dot"] = _soffice_convert(files["docx"], 'dot:MS Word 97 Vorlage', out, "sample.dot")
    files["rtf"] = _soffice_convert(files["docx"], "rtf", out, "sample.rtf")
    files["xls"] = _soffice_convert(files["xlsx"], "xls:MS Excel 97", out, "sample.xls")
    files["ppt"] = _soffice_convert(files["pptx"], "ppt:MS PowerPoint 97", out, "sample.ppt")
    files["pps"] = _soffice_convert(files["pptx"], "pps:MS PowerPoint 97 AutoPlay", out, "sample.pps")

    files["txt"] = out / "sample.txt"
    files["txt"].write_text(f"{TEXT}\nUnicode: naïve café Ελληνικά 中文 العربية\n", encoding="utf-8")
    files["csv"] = out / "sample.csv"
    files["csv"].write_text("name;value;note\nCafé;1,5;中文\nZoë;2,5;Ελληνικά\n", encoding="utf-8")

    for ext, source in {"wpd": "testWordPerfect.wpd", "wps": "testWORKSWordProcessor4.0.wps", "vsd": "testVISIO.vsd", "vsdx": "testVISIO.vsdx", "msg": "testMSG_att_doc.msg"}.items():
        files[ext] = out / f"sample.{ext}"
        shutil.copy(THIRD_PARTY / source, files[ext])

    for ext in ("jpg", "jpeg"):
        files[ext] = out / f"sample.{ext}"
        picture().save(files[ext], "JPEG", quality=88, dpi=(150, 150))
    files["png"] = out / "sample.png"
    picture().save(files["png"], "PNG", dpi=(150, 150))
    files["gif"] = out / "sample.gif"
    picture().convert("P").save(files["gif"], "GIF")
    files["bmp"] = out / "sample.bmp"
    picture().save(files["bmp"], "BMP")
    files["webp"] = out / "sample.webp"
    picture().save(files["webp"], "WEBP", lossless=True)
    files["tif"] = make_multipage_tiff(out / "sample.tif")
    files["tiff"] = make_multipage_tiff(out / "sample.tiff")

    # The image has no HEVC encoder, so HEIC samples are pre-made (see static/README.txt).
    for ext in ("heic", "heif"):
        files[ext] = out / f"sample.{ext}"
        shutil.copy(STATIC / "sample.heic", files[ext])
    files["avif"] = out / "sample.avif"
    picture().save(files["avif"], "AVIF", quality=80)

    files["svg"] = make_svg(out / "sample.svg")
    files["eps"] = make_eps(out / "sample.eps")
    for ext in ("html", "htm"):
        files[ext] = out / f"sample.{ext}"
        files[ext].write_text(HTML_DOC, encoding="utf-8")
    files["md"] = out / "sample.md"
    files["md"].write_text(
        f"# {TITLE}\n\n{TEXT}\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n```python\nprint('hello')\n```\n",
        encoding="utf-8",
    )
    attachments_dir = out / "email-parts"
    attachments_dir.mkdir(exist_ok=True)
    files["eml"] = make_eml(out / "sample.eml", attachments_dir)
    files["pdf"] = make_pdf(out / "sample.pdf")
    return files


# Helpers for individual tests -------------------------------------------------------


def rgba_png(alpha: int = 128) -> bytes:
    """A half-transparent red image."""
    return png_bytes(Image.new("RGBA", (100, 100), (255, 0, 0, alpha)))


def exif_jpeg(orientation: int, size=(200, 100)) -> bytes:
    """A JPEG that displays as landscape only if EXIF orientation is honoured."""
    image = picture(size)
    exif = Image.Exif()
    exif[0x0112] = orientation
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=90, exif=exif)
    return buffer.getvalue()


def jpeg_with_icc(profile: bytes) -> bytes:
    buffer = io.BytesIO()
    picture().save(buffer, "JPEG", quality=90, icc_profile=profile)
    return buffer.getvalue()


def icc_v4_profile() -> bytes:
    return ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()


def animated_gif() -> bytes:
    frames = [Image.new("P", (50, 50), color) for color in (1, 2, 3)]
    buffer = io.BytesIO()
    frames[0].save(buffer, "GIF", save_all=True, append_images=frames[1:], duration=100, loop=0)
    return buffer.getvalue()


def encrypted_pdf(path: Path, user_password: str = "secret", owner_password: str = "owner") -> Path:
    import pikepdf

    plain = path.with_suffix(".plain.pdf")
    make_pdf(plain, pages=1)
    with pikepdf.open(plain) as pdf:
        pdf.save(path, encryption=pikepdf.Encryption(user=user_password, owner=owner_password))
    plain.unlink()
    return path

