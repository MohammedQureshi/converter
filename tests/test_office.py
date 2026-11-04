"""Stage 2: Office formats through the LibreOffice pool, end to end."""

from __future__ import annotations

import io
import zipfile

import openpyxl
import pikepdf
import pytest
from conftest import assert_valid_pdfa, convert
from fixtures.generate import EXPECTATIONS, TITLE, make_docx, make_xlsx, picture

OFFICE_FORMATS = ["doc", "docx", "dot", "dotx", "docm", "odt", "rtf", "txt", "wpd", "wps",
                  "xls", "xlsx", "xlsm", "ods", "csv", "ppt", "pptx", "pps", "ppsx", "odp",
                  "vsd", "vsdx", "odg"]


@pytest.mark.parametrize("ext", OFFICE_FORMATS)
def test_office_format_converts_to_pdfa(api, samples, tmp_path, ext):
    response = convert(api, f"sample.{ext}", samples[ext].read_bytes())
    out = assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-source-format"] == ext
    assert response.headers["x-pdfa-validated"] == "true"
    expect = EXPECTATIONS[ext]
    pages = int(response.headers["x-page-count"])
    assert expect.min_pages <= pages <= expect.max_pages, f"{ext}: {pages} pages"
    assert int(response.headers["x-conversion-ms"]) > 0
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == pages


def test_office_output_is_not_rewritten_by_ghostscript(api, tmp_path):
    """LibreOffice's native PDF/A export is used; Ghostscript must not touch the file."""
    path = make_docx(tmp_path / "latin.docx", cjk=False)
    response = convert(api, "latin.docx", path.read_bytes())
    assert_valid_pdfa(response, tmp_path)
    with pikepdf.open(io.BytesIO(response.content)) as pdf:
        assert "Ghostscript" not in str(pdf.docinfo.get("/Producer", ""))
        assert "LibreOffice" in str(pdf.docinfo.get("/Producer", ""))


def test_cjk_document_is_compliant_and_keeps_real_text(api, tmp_path):
    """LibreOffice's export of CJK fonts breaks PDF/A-1 and must be repaired, not shipped."""
    response = convert(api, "cjk.txt", "中文文本 日本語 한국어\nLatin text too\n".encode())
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-pdfa-validated"] == "true"
    text = pdf_text(response.content)
    assert "中文文本" in text and "Latin text too" in text


def test_metadata_carries_filename_and_title(api, samples, tmp_path):
    response = convert(api, "Quarterly Report ü.docx", samples["docx"].read_bytes())
    out = assert_valid_pdfa(response, tmp_path)
    with pikepdf.open(out) as pdf, pdf.open_metadata() as meta:
        assert meta["dc:source"] == "Quarterly Report ü.docx"
        assert meta["dc:title"] == TITLE
        assert meta.pdfa_status == "1B"
        assert str(pdf.docinfo["/Title"]) == TITLE


def test_spreadsheet_fits_page_width(api, tmp_path):
    """A 40-column sheet would span many pages wide without fit-to-width."""
    path = make_xlsx(tmp_path / "wide.xlsx", wide=True)
    response = convert(api, "wide.xlsx", path.read_bytes())
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-page-count"] == "1"


def test_spreadsheet_keeps_authors_own_scaling(api, tmp_path):
    """An explicit print scale chosen by the author is honoured, not overridden."""
    path = make_xlsx(tmp_path / "scaled.xlsx", wide=True)
    workbook = openpyxl.load_workbook(path)
    workbook.active.page_setup.scale = 100
    workbook.active.sheet_properties.pageSetUpPr = openpyxl.worksheet.properties.PageSetupProperties(fitToPage=False)
    workbook.active.page_setup.scale = 90
    workbook.save(path)
    response = convert(api, "scaled.xlsx", path.read_bytes())
    assert_valid_pdfa(response, tmp_path)
    assert int(response.headers["x-page-count"]) > 1


def test_large_spreadsheet_stays_compact(api, tmp_path):
    """Per-cell tags made a sheet like this 9 MB. The text must still be real and searchable."""
    path = tmp_path / "rows.xlsx"
    workbook = openpyxl.Workbook()
    for row in range(4500):
        workbook.active.append([row, row * 1.5, f"Item {row}", "2026-11-04", row % 7, "Note"])
    workbook.save(path)
    response = convert(api, "rows.xlsx", path.read_bytes())
    assert_valid_pdfa(response, tmp_path)
    assert len(response.content) < 1_500_000, f"{len(response.content)} bytes"
    assert "Item 4499" in pdf_text(response.content)


def test_word_documents_keep_their_tags(api, tmp_path):
    path = make_docx(tmp_path / "tagged.docx", cjk=False)
    response = convert(api, "tagged.docx", path.read_bytes())
    assert_valid_pdfa(response, tmp_path)
    with pikepdf.open(io.BytesIO(response.content)) as pdf:
        assert "/StructTreeRoot" in pdf.Root


def test_spreadsheet_respects_print_area(api, tmp_path):
    path = tmp_path / "area.xlsx"
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet["A1"] = "Inside the print area"
    sheet["H40"] = "Outside the print area"
    sheet.print_area = "A1:C5"
    workbook.save(path)
    response = convert(api, "area.xlsx", path.read_bytes())
    assert_valid_pdfa(response, tmp_path)
    text = pdf_text(response.content)
    assert "Inside the print area" in text and "Outside the print area" not in text


def test_csv_detects_encoding_and_delimiter(api, tmp_path):
    """Semicolons in Windows-1252: separate columns and correct accents in the output."""
    data = "name;city\nZoë;Köln\nRené;Orléans\n".encode("cp1252")
    response = convert(api, "latin.csv", data)
    assert_valid_pdfa(response, tmp_path)
    text = pdf_text(response.content)
    assert "Köln" in text and "Orléans" in text
    assert "name;city" not in text


def test_text_file_keeps_unicode(api, tmp_path):
    response = convert(api, "notes.txt", "Ελληνικά 中文 text\n".encode())
    assert_valid_pdfa(response, tmp_path)
    assert "Ελληνικά" in pdf_text(response.content)


def test_docx_jpeg_is_not_recompressed(api, tmp_path):
    """A JPEG in a document reaches the PDF byte for byte, without quality loss."""
    from docx import Document
    from docx.shared import Inches

    buffer = io.BytesIO()
    picture((640, 480)).save(buffer, "JPEG", quality=85)
    jpeg = buffer.getvalue()
    document = Document()
    document.add_picture(io.BytesIO(jpeg), width=Inches(4))
    doc_buffer = io.BytesIO()
    document.save(doc_buffer)

    response = convert(api, "photo.docx", doc_buffer.getvalue())
    assert_valid_pdfa(response, tmp_path)
    with pikepdf.open(io.BytesIO(response.content)) as pdf:
        streams = [obj.read_raw_bytes() for obj in pdf.objects
                   if isinstance(obj, pikepdf.Stream) and obj.get("/Subtype") == "/Image" and obj.get("/Filter") == "/DCTDecode"]
    assert any(raw.rstrip() == jpeg.rstrip() for raw in streams), "embedded JPEG differs from the original"


def test_transparency_in_docx_remains_compliant(api, tmp_path):
    """PNG alpha in a document: LibreOffice flattens per object and keeps real text."""
    from docx import Document
    from docx.shared import Inches
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGBA", (200, 200), (255, 0, 0, 100)).save(buffer, "PNG")
    document = Document()
    document.add_paragraph("Searchable text beside a transparent image")
    document.add_picture(io.BytesIO(buffer.getvalue()), width=Inches(2))
    doc_buffer = io.BytesIO()
    document.save(doc_buffer)
    response = convert(api, "alpha.docx", doc_buffer.getvalue())
    assert_valid_pdfa(response, tmp_path)
    assert "Searchable text" in pdf_text(response.content)


def test_macro_document_converts_without_running_macros(api, service, tmp_path):
    """An ODT whose open event runs a macro that writes a file must not execute it."""
    marker = tmp_path / "macro-ran"
    basic = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<script:module xmlns:script="http://openoffice.org/2000/script" script:name="Module1" script:language="StarBasic">\n'
        "Sub Main\n"
        f'  Open "{marker}" For Output As #1\n  Print #1, "x"\n  Close #1\n'
        "End Sub\n</script:module>\n"
    )
    source = tmp_path / "plain.odt"
    from odf.opendocument import OpenDocumentText
    from odf.text import P

    document = OpenDocumentText()
    document.text.addElement(P(text="Document with an auto-run macro"))
    document.save(str(source))

    out = io.BytesIO()
    with zipfile.ZipFile(source) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "content.xml":
                data = data.replace(
                    b"<office:body>",
                    b'<office:scripts><office:event-listeners>'
                    b'<script:event-listener script:language="ooo:script" script:event-name="office:load-finished" '
                    b'xlink:href="vnd.sun.star.script:Standard.Module1.Main?language=Basic&amp;location=document" '
                    b'xmlns:script="urn:oasis:names:tc:opendocument:xmlns:script:1.0" xmlns:xlink="http://www.w3.org/1999/xlink"/>'
                    b"</office:event-listeners></office:scripts><office:body>",
                )
            if item.filename == "META-INF/manifest.xml":
                data = data.replace(
                    b"</manifest:manifest>",
                    b'<manifest:file-entry manifest:full-path="Basic/Standard/Module1.xml" manifest:media-type="text/xml"/>'
                    b'<manifest:file-entry manifest:full-path="Basic/Standard/script-lb.xml" manifest:media-type="text/xml"/>'
                    b'<manifest:file-entry manifest:full-path="Basic/script-lc.xml" manifest:media-type="text/xml"/>'
                    b"</manifest:manifest>",
                )
            zout.writestr(item, data)
        zout.writestr("Basic/Standard/Module1.xml", basic)
        zout.writestr(
            "Basic/Standard/script-lb.xml",
            '<?xml version="1.0" encoding="UTF-8"?>\n<library:library xmlns:library="http://openoffice.org/2000/library" '
            'library:name="Standard" library:readonly="false" library:passwordprotected="false">'
            '<library:element library:name="Module1"/></library:library>',
        )
        zout.writestr(
            "Basic/script-lc.xml",
            '<?xml version="1.0" encoding="UTF-8"?>\n<library:libraries xmlns:library="http://openoffice.org/2000/library" '
            'xmlns:xlink="http://www.w3.org/1999/xlink"><library:library library:name="Standard" library:link="false"/></library:libraries>',
        )
    response = convert(api, "macro.odt", out.getvalue())
    assert_valid_pdfa(response, tmp_path)
    assert not marker.exists(), "the document's macro executed"


def pdf_text(data: bytes) -> str:
    """Extracts text with Ghostscript's txtwrite device, which applies ToUnicode maps."""
    import subprocess
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "in.pdf"
        src.write_bytes(data)
        output = subprocess.run(
            ["gs", "-q", "-dSAFER", "-dBATCH", "-dNOPAUSE", "-sDEVICE=txtwrite", "-sOutputFile=-", str(src)],
            capture_output=True, timeout=60,
        )
        return output.stdout.decode("utf-8", "replace")

