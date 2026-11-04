"""Attempts to make LibreOffice fetch URLs or read local files from inside a document."""

from __future__ import annotations

import http.server
import io
import os
import subprocess
import threading
import zipfile

import pytest
from conftest import assert_valid_pdfa, convert
from docx import Document
from fixtures.generate import picture, png_bytes
from PIL import Image
from test_images_pdf import rendered_page
from test_office import pdf_text


class _Recorder(http.server.BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_GET(self):  # noqa: N802
        type(self).hits.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.end_headers()
        self.wfile.write(png_bytes(Image.new("RGB", (200, 200), (0, 255, 0))))

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def listener():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Recorder)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", _Recorder
    server.shutdown()


def _docx_with_linked_image(target: str) -> bytes:
    """A DOCX whose picture is an external link, resolved when the file is opened."""
    document = Document()
    document.add_paragraph("Document with a linked picture")
    document.add_picture(io.BytesIO(png_bytes(picture((16, 16)))))
    buffer = io.BytesIO()
    document.save(buffer)
    out = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(buffer.getvalue())) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "word/document.xml":
                data = data.replace(b"r:embed=", b"r:link=")
            if item.filename == "word/_rels/document.xml.rels":
                import re

                data = re.sub(
                    rb'<Relationship [^>]*relationships/image"[^>]*/>',
                    (
                        '<Relationship Id="rId9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" '
                        f'Target="{target}" TargetMode="External"/>'
                    ).encode(),
                    data,
                )
            if item.filename == "word/document.xml":
                import re

                data = re.sub(rb'r:link="[^"]*"', b'r:link="rId9"', data)
            zout.writestr(item, data)
    return out.getvalue()


def _odt_with_linked_image(target: str, tmp_path) -> bytes:
    from odf.opendocument import OpenDocumentText
    from odf.text import P

    path = tmp_path / "base.odt"
    document = OpenDocumentText()
    document.text.addElement(P(text="ODT with a linked picture"))
    document.save(str(path))
    out = io.BytesIO()
    frame = (
        '<text:p><draw:frame xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
        'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" text:anchor-type="paragraph" svg:width="5cm" svg:height="5cm" draw:name="linked">'
        f'<draw:image xlink:href="{target}" xlink:type="simple" xlink:show="embed" xlink:actuate="onLoad"/>'
        "</draw:frame></text:p>"
    )
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "content.xml":
                data = data.replace(b"</office:text>", frame.encode() + b"</office:text>")
            zout.writestr(item, data)
    return out.getvalue()


def _has_green(path) -> bool:
    image = rendered_page(path).convert("RGB")
    return any(
        image.getpixel((x, y))[1] > 200 and image.getpixel((x, y))[0] < 60
        for x in range(0, image.width, 8) for y in range(0, image.height, 8)
    )


def _stock_libreoffice_pdf(name: str, data: bytes, tmp_path):
    """Converts with an unhardened profile, the way LibreOffice behaves out of the box."""
    source = tmp_path / name
    source.write_bytes(data)
    subprocess.run(
        ["soffice", "--headless", "--norestore", f"-env:UserInstallation=file://{tmp_path}/stock-profile",
         "--convert-to", "pdf", "--outdir", str(tmp_path / "stock"), str(source)],
        check=True, capture_output=True, timeout=120,
    )
    return tmp_path / "stock" / f"{source.stem}.pdf"


def _libreoffice_version() -> tuple[int, ...]:
    version = subprocess.run(["dpkg-query", "-W", "-f=${Version}", "libreoffice-core-nogui"], capture_output=True, text=True).stdout
    return tuple(int(part) for part in version.split(":")[-1].split("-")[0].split(".")[:3])


def _require_vulnerable_stock_libreoffice() -> None:
    """Stock 26.8.1 follows these links; the same files do nothing on stock 26.8.2.

    The LibreOffice pin is a series and each architecture can be on a different release, so
    older builds must still prove these documents are a real attack. Newer ones report a skip.
    """
    if _libreoffice_version() >= (26, 8, 2):
        pytest.skip("stock LibreOffice 26.8.2 or newer no longer follows these links; the hardening is now defence in depth")


def test_control_stock_libreoffice_fetches_docx_links(listener, tmp_path):
    """Positive control: these documents are a real attack, so the tests below mean something."""
    _require_vulnerable_stock_libreoffice()
    url, recorder = listener
    recorder.hits.clear()
    _stock_libreoffice_pdf("control.docx", _docx_with_linked_image(f"{url}/control-docx.png"), tmp_path)
    assert recorder.hits == ["/control-docx.png"]


def test_control_stock_libreoffice_embeds_local_files_from_docx(tmp_path):
    _require_vulnerable_stock_libreoffice()
    secret = tmp_path / "secret.png"
    secret.write_bytes(png_bytes(Image.new("RGB", (200, 200), (0, 255, 0))))
    pdf = _stock_libreoffice_pdf("control-file.docx", _docx_with_linked_image(f"file://{secret}"), tmp_path)
    assert _has_green(pdf)


def test_docx_linked_image_cannot_reach_the_network(api, listener, tmp_path):
    url, recorder = listener
    recorder.hits.clear()
    response = convert(api, "linked.docx", _docx_with_linked_image(f"{url}/docx-ssrf.png"))
    out = assert_valid_pdfa(response, tmp_path)
    assert recorder.hits == [], f"LibreOffice fetched {recorder.hits}"
    assert not _has_green(out)


def test_odt_linked_image_cannot_reach_the_network(api, listener, tmp_path):
    """Defence in depth: stock LibreOffice does not fetch this while converting either."""
    url, recorder = listener
    recorder.hits.clear()
    response = convert(api, "linked.odt", _odt_with_linked_image(f"{url}/odt-ssrf.png", tmp_path))
    out = assert_valid_pdfa(response, tmp_path)
    assert recorder.hits == [], f"LibreOffice fetched {recorder.hits}"
    assert not _has_green(out)


def test_odt_linked_image_cannot_read_local_files(api, tmp_path):
    """Defence in depth, as above."""
    secret = tmp_path / "secret.png"
    secret.write_bytes(png_bytes(Image.new("RGB", (200, 200), (0, 255, 0))))
    os.chmod(tmp_path, 0o755)
    response = convert(api, "local.odt", _odt_with_linked_image(f"file://{secret}", tmp_path))
    out = assert_valid_pdfa(response, tmp_path)
    assert not _has_green(out), "a local file was embedded into the output"


def test_docx_linked_image_cannot_read_local_files(api, tmp_path):
    secret = tmp_path / "secret.png"
    secret.write_bytes(png_bytes(Image.new("RGB", (200, 200), (0, 255, 0))))
    response = convert(api, "local.docx", _docx_with_linked_image(f"file://{secret}"))
    out = assert_valid_pdfa(response, tmp_path)
    assert not _has_green(out), "a local file was embedded into the output"


def test_spreadsheet_webservice_formula_does_not_fetch(api, listener, tmp_path):
    """Defence in depth: stock LibreOffice does not recalculate this on load either."""
    import openpyxl

    url, recorder = listener
    recorder.hits.clear()
    workbook = openpyxl.Workbook()
    workbook.active["A1"] = f'=WEBSERVICE("{url}/calc-ssrf")'
    workbook.active["A2"] = "Sheet with a web formula"
    path = tmp_path / "web.xlsx"
    workbook.save(path)
    out = assert_valid_pdfa(convert(api, "web.xlsx", path.read_bytes()), tmp_path)
    assert recorder.hits == [], f"LibreOffice fetched {recorder.hits}"
    assert "Sheet with a web formula" in pdf_text(out.read_bytes())


def test_spreadsheet_external_link_does_not_read_local_files(api, tmp_path):
    """A formula pulling cells from a file on the server's disk must not resolve."""
    import openpyxl

    secret = tmp_path / "secret.csv"
    secret.write_text("TOP-SECRET-VALUE\n")
    workbook = openpyxl.Workbook()
    workbook.active["A1"] = f"='file://{secret}'#$secret.A1"
    workbook.active["A2"] = f'=WEBSERVICE("file://{secret}")'
    path = tmp_path / "local.xlsx"
    workbook.save(path)
    out = assert_valid_pdfa(convert(api, "local.xlsx", path.read_bytes()), tmp_path)
    assert "TOP-SECRET-VALUE" not in pdf_text(out.read_bytes())
