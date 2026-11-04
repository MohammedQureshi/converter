"""Stage 4: HEIC/AVIF, SVG/EPS, HTML/Markdown and email."""

from __future__ import annotations

import http.server
import io
import threading
from email.message import EmailMessage

import pikepdf
import pytest
from conftest import assert_valid_pdfa, convert, start_service
from fixtures.generate import EXPECTATIONS, STATIC, TEXT, THIRD_PARTY, TITLE, encrypted_pdf, make_docx, picture, png_bytes
from PIL import Image
from test_images_pdf import page_size, rendered_page
from test_office import pdf_text

FORMATS = ["heic", "heif", "avif", "svg", "eps", "html", "htm", "md", "eml", "msg"]


class _Recorder(http.server.BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_GET(self):  # noqa: N802
        type(self).hits.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.end_headers()
        self.wfile.write(png_bytes(picture((8, 8))))

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def listener():
    """An HTTP server that records any request, proving that no engine reached out."""
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Recorder)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    _Recorder.hits = []
    yield f"http://127.0.0.1:{server.server_address[1]}", _Recorder
    server.shutdown()


@pytest.mark.parametrize("ext", FORMATS)
def test_format_converts_to_pdfa(api, samples, tmp_path, ext):
    response = convert(api, f"sample.{ext}", samples[ext].read_bytes())
    out = assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-source-format"] == ext
    assert response.headers["x-pdfa-validated"] == "true"
    expect = EXPECTATIONS[ext]
    pages = int(response.headers["x-page-count"])
    assert expect.min_pages <= pages <= expect.max_pages, f"{ext}: {pages} pages"
    with pikepdf.open(out) as pdf:
        assert len(pdf.pages) == pages


# ---- modern images ------------------------------------------------------------------


def test_heic_flattens_alpha(api, tmp_path):
    out = assert_valid_pdfa(convert(api, "alpha.heic", (STATIC / "alpha.heic").read_bytes()), tmp_path)
    assert rendered_page(out).getpixel((5, 5)) == (255, 255, 255)


def test_avif_with_alpha_is_flattened(api, tmp_path):
    buffer = io.BytesIO()
    Image.new("RGBA", (64, 64), (255, 0, 0, 0)).save(buffer, "AVIF", quality=90)
    out = assert_valid_pdfa(convert(api, "alpha.avif", buffer.getvalue()), tmp_path)
    red, green, blue = rendered_page(out).getpixel((5, 5))
    assert min(red, green, blue) >= 250


# ---- SVG and EPS --------------------------------------------------------------------


def test_svg_keeps_title_and_native_size(api, samples, tmp_path):
    out = assert_valid_pdfa(convert(api, "drawing.svg", samples["svg"].read_bytes()), tmp_path)
    assert page_size(out) == pytest.approx((225, 150), abs=1)  # 300 x 200 px at 96 dpi
    with pikepdf.open(out) as pdf, pdf.open_metadata() as meta:
        assert meta["dc:title"] == TITLE


def test_svg_stays_vector_with_real_text(api, samples, tmp_path):
    out = assert_valid_pdfa(convert(api, "drawing.svg", samples["svg"].read_bytes()), tmp_path)
    assert "quick brown" in pdf_text(out.read_bytes())


def test_svg_transparency_renders_correctly(api, tmp_path):
    svg = (
        b'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
        b'<rect width="150" height="150" fill="#f00"/>'
        b'<rect x="50" y="50" width="150" height="150" fill="#00f" fill-opacity="0.5"/></svg>'
    )
    response = convert(api, "alpha.svg", svg)
    out = assert_valid_pdfa(response, tmp_path)
    red, green, blue = rendered_page(out).getpixel((75, 75))
    assert abs(red - 128) < 6 and green < 6 and abs(blue - 128) < 6, (red, green, blue)
    assert response.headers["x-flattened-pages"] == "1"


def test_svg_cannot_fetch_urls_or_read_files(api, listener, tmp_path):
    url, recorder = listener
    secret = tmp_path / "secret.png"
    secret.write_bytes(png_bytes(Image.new("RGB", (100, 100), (0, 255, 0))))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="100" height="100">'
        f'<image width="100" height="100" xlink:href="{url}/svg-remote.png"/>'
        f'<image width="100" height="100" xlink:href="file://{secret}"/>'
        f'<style>@import url("{url}/svg-style.css");</style>'
        f'<use xlink:href="{url}/svg-use.svg#a"/>'
        "</svg>"
    ).encode()
    recorder.hits.clear()
    out = assert_valid_pdfa(convert(api, "fetch.svg", svg), tmp_path)
    assert recorder.hits == []
    assert rendered_page(out).getpixel((50, 50)) != (0, 255, 0), "a local file was read into the output"


def test_svg_with_xml_entities_is_rejected(api):
    svg = (
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><text y="20">&xxe;</text></svg>'
    )
    response = convert(api, "xxe.svg", svg)
    assert response.status_code == 422
    assert response.json()["error"] == "CORRUPT_FILE"


def test_eps_is_cropped_to_its_bounding_box(api, samples, tmp_path):
    out = assert_valid_pdfa(convert(api, "figure.eps", samples["eps"].read_bytes()), tmp_path)
    assert page_size(out) == pytest.approx((300, 200), abs=1)
    assert "Fixture EPS text" in pdf_text(out.read_bytes())


def test_eps_cannot_read_files_under_safer(api):
    eps = (
        b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 400 100\n"
        b"/Helvetica findfont 8 scalefont setfont 10 50 moveto\n"
        b"(/etc/passwd) (r) file 100 string readstring pop show\nshowpage\n"
    )
    response = convert(api, "steal.eps", eps)
    if response.status_code == 200:
        assert "root:" not in pdf_text(response.content)
    else:
        assert response.status_code == 422


# ---- HTML and Markdown --------------------------------------------------------------


def test_html_blocks_all_network_and_file_access(api, listener, tmp_path):
    url, recorder = listener
    html = f"""<!doctype html><html><head>
      <link rel="stylesheet" href="{url}/html-style.css">
      <script src="{url}/html-script.js"></script>
      <meta http-equiv="refresh" content="0;url={url}/html-refresh">
      <style>@import url("{url}/html-import.css"); body {{ background: url("{url}/html-bg.png"); }}
             @font-face {{ font-family: x; src: url("{url}/html-font.woff"); }} p {{ font-family: x; }}</style>
    </head><body><p>Local content only</p>
      <img src="{url}/html-img.png">
      <iframe src="{url}/html-frame"></iframe>
      <iframe src="file:///etc/passwd" width="600" height="300"></iframe>
      <object data="{url}/html-object"></object>
      <embed src="{url}/html-embed">
      <video src="{url}/html-video" poster="{url}/html-poster"></video>
    </body></html>""".encode()
    recorder.hits.clear()
    response = convert(api, "fetch.html", html)
    out = assert_valid_pdfa(response, tmp_path)
    assert recorder.hits == [], f"the renderer made requests: {recorder.hits}"
    text = pdf_text(out.read_bytes())
    assert "Local content only" in text
    assert "root:" not in text


def test_html_scripts_do_not_run_by_default(api, listener, tmp_path):
    url, recorder = listener
    html = f"""<html><body><p id="target">Original</p>
      <script>
        document.getElementById("target").textContent = "Changed by script";
        fetch("{url}/html-fetch");
        new Image().src = "{url}/html-js-image";
        navigator.sendBeacon("{url}/html-beacon");
      </script></body></html>""".encode()
    recorder.hits.clear()
    out = assert_valid_pdfa(convert(api, "script.html", html), tmp_path)
    text = pdf_text(out.read_bytes())
    assert "Original" in text and "Changed by script" not in text
    assert recorder.hits == []


def test_html_inline_images_and_title_are_kept(api, samples, tmp_path):
    out = assert_valid_pdfa(convert(api, "page.html", samples["html"].read_bytes()), tmp_path)
    with pikepdf.open(out) as pdf, pdf.open_metadata() as meta:
        assert meta["dc:title"] == TITLE
        assert meta["dc:source"] == "page.html"
    assert "quick brown" in pdf_text(out.read_bytes())
    assert page_size(out) == pytest.approx((595.28, 841.89), abs=2)


def test_html_honours_declared_charset(api, tmp_path):
    html = '<html><head><meta charset="windows-1252"></head><body>Café Zoë</body></html>'.encode("cp1252")
    out = assert_valid_pdfa(convert(api, "latin.html", html), tmp_path)
    assert "Café Zoë" in pdf_text(out.read_bytes())


def test_html_with_css_transparency_reports_flattened_pages(api, tmp_path):
    html = b'<html><body><div style="background:rgba(255,0,0,.3);opacity:.8">Translucent</div></body></html>'
    response = convert(api, "alpha.html", html)
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-flattened-pages"] == "1"


def test_html_without_transparency_keeps_searchable_text(api, tmp_path):
    response = convert(api, "plain.html", b"<html><body><h1>Heading</h1><p>Body paragraph</p></body></html>")
    out = assert_valid_pdfa(response, tmp_path)
    assert "x-flattened-pages" not in response.headers
    assert "Body paragraph" in pdf_text(out.read_bytes())


def test_markdown_renders_structure_and_title(api, samples, tmp_path):
    out = assert_valid_pdfa(convert(api, "readme.md", samples["md"].read_bytes()), tmp_path)
    text = pdf_text(out.read_bytes())
    assert "quick brown" in text and "print('hello')" in text
    assert "|---|" not in text  # the table was rendered, not left as Markdown source
    with pikepdf.open(out) as pdf, pdf.open_metadata() as meta:
        assert meta["dc:title"] == TITLE


def test_markdown_raw_html_cannot_reach_the_network(api, listener, tmp_path):
    url, recorder = listener
    recorder.hits.clear()
    source = f'# Doc\n\n<img src="{url}/md-img.png">\n\n![remote]({url}/md-link.png)\n'.encode()
    assert_valid_pdfa(convert(api, "remote.md", source), tmp_path)
    assert recorder.hits == []


# ---- email --------------------------------------------------------------------------


def _email(subject="Subject line", html=None, text=None) -> EmailMessage:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = "Alice <alice@example.test>"
    message["To"] = "Bob <bob@example.test>"
    message["Date"] = "Wed, 04 Nov 2026 10:00:00 +0000"
    message.set_content(text or TEXT)
    if html:
        message.add_alternative(html, subtype="html")
    return message


def test_eml_merges_body_and_attachments_with_metadata(api, samples, tmp_path):
    response = convert(api, "mail.eml", samples["eml"].read_bytes())
    out = assert_valid_pdfa(response, tmp_path)
    text = pdf_text(out.read_bytes())
    assert "Alice Example" in text and "Fixture email subject" in text
    assert "HTML body" in text
    assert "photo.png" in text and "report.docx" in text
    assert "Fixture document" in text  # text from inside the DOCX attachment
    with pikepdf.open(out) as pdf, pdf.open_metadata() as meta:
        assert meta["dc:title"] == "Fixture email subject"
        assert meta["dc:source"] == "mail.eml"
    assert "x-attachments-skipped" not in response.headers


def test_eml_inline_image_is_embedded(api, tmp_path):
    message = _email(html='<html><body><img src="cid:pic1" width="100" height="100"></body></html>')
    message.get_body(preferencelist=("html",)).add_related(
        png_bytes(Image.new("RGB", (100, 100), (0, 200, 0))), "image", "png", cid="<pic1>", filename="pic.png"
    )
    response = convert(api, "inline.eml", bytes(message))
    out = assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-page-count"] == "1"  # the inline image is not also an attachment
    image = rendered_page(out, dpi=150).convert("RGB")
    assert any(
        image.getpixel((x, y))[1] > 150 and image.getpixel((x, y))[0] < 60
        for x in range(0, image.width, 10) for y in range(0, image.height, 10)
    ), "the inline image is missing from the page"


def test_eml_remote_content_is_blocked(api, listener, tmp_path):
    url, recorder = listener
    recorder.hits.clear()
    html = f'<html><body><p>Tracker</p><img src="{url}/mail-tracking-pixel.gif"></body></html>'
    assert_valid_pdfa(convert(api, "tracker.eml", bytes(_email(html=html))), tmp_path)
    assert recorder.hits == []


def test_eml_headers_are_escaped(api, listener, tmp_path):
    url, recorder = listener
    recorder.hits.clear()
    message = _email(subject=f'<img src="{url}/header-injection"> Injected')
    out = assert_valid_pdfa(convert(api, "header.eml", bytes(message)), tmp_path)
    assert recorder.hits == []
    assert "<img src=" in pdf_text(out.read_bytes())


def test_unsupported_and_encrypted_attachments_are_noted_not_fatal(api, tmp_path):
    message = _email()
    message.add_attachment(b"MZ\x90\x00" + bytes(200), maintype="application", subtype="octet-stream", filename="virus.exe")
    locked = encrypted_pdf(tmp_path / "locked.pdf")
    message.add_attachment(locked.read_bytes(), maintype="application", subtype="pdf", filename="locked.pdf")
    message.add_attachment(png_bytes(), maintype="image", subtype="png", filename="good.png")
    response = convert(api, "mixed.eml", bytes(message))
    out = assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-attachments-skipped"] == "2"
    assert response.headers["x-page-count"] == "2"  # cover + the one good attachment
    text = pdf_text(out.read_bytes())
    assert "virus.exe" in text and "not converted" in text and "locked.pdf" in text


def _nested(levels: int) -> bytes:
    from email import message_from_bytes, policy

    data = bytes(_email(subject=f"Level {levels}", text=f"Body at depth {levels}"))
    for level in range(levels - 1, -1, -1):
        outer = _email(subject=f"Level {level}", text=f"Body at depth {level}")
        outer.add_attachment(message_from_bytes(data, policy=policy.default), filename=f"level-{level + 1}.eml")
        data = bytes(outer)
    return data


def test_nested_emails_are_converted_recursively(api, tmp_path):
    response = convert(api, "nested.eml", _nested(2))
    out = assert_valid_pdfa(response, tmp_path)
    text = pdf_text(out.read_bytes())
    for depth in range(3):
        assert f"Body at depth {depth}" in text
    assert "x-attachments-skipped" not in response.headers


def test_email_recursion_depth_is_limited(api, tmp_path):
    """The default depth limit is 3: levels 0-3 convert, and level 4 is noted instead."""
    response = convert(api, "deep.eml", _nested(5))
    out = assert_valid_pdfa(response, tmp_path)
    text = pdf_text(out.read_bytes())
    assert "Body at depth 3" in text
    assert "Body at depth 4" not in text
    assert "nested more than" in text
    assert response.headers["x-attachments-skipped"] == "1"


@pytest.fixture(scope="module")
def limited_service():
    service = start_service("limits", {"MAX_EMAIL_ATTACHMENTS": "2", "LO_POOL_SIZE": "1"})
    yield service
    service.stop()


def test_email_attachment_count_is_limited(limited_service, tmp_path):
    message = _email()
    for index in range(4):
        message.add_attachment(png_bytes(), maintype="image", subtype="png", filename=f"image-{index}.png")
    with limited_service.client() as client:
        response = convert(client, "many.eml", bytes(message))
    out = assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-page-count"] == "3"
    assert response.headers["x-attachments-skipped"] == "2"
    assert "limit of 2 attachments" in pdf_text(out.read_bytes())


@pytest.mark.parametrize("name", ["testMSG.msg", "testMSG_att_doc.msg", "testMSG_att_msg.msg", "testMSG_chinese.msg"])
def test_real_outlook_messages(api, tmp_path, name):
    response = convert(api, name, (THIRD_PARTY / name).read_bytes())
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-source-format"] == "msg"


def test_msg_with_word_attachment_includes_it(api, tmp_path):
    response = convert(api, "with-doc.msg", (THIRD_PARTY / "testMSG_att_doc.msg").read_bytes())
    assert_valid_pdfa(response, tmp_path)
    assert int(response.headers["x-page-count"]) >= 2
    assert "x-attachments-skipped" not in response.headers


def test_msg_with_nested_message_recurses(api, tmp_path):
    response = convert(api, "with-msg.msg", (THIRD_PARTY / "testMSG_att_msg.msg").read_bytes())
    assert_valid_pdfa(response, tmp_path)
    assert int(response.headers["x-page-count"]) >= 2
    assert "x-attachments-skipped" not in response.headers


def test_email_with_docx_attachment_is_merged_from_a_real_file(api, tmp_path):
    docx = make_docx(tmp_path / "a.docx", cjk=False)
    message = _email()
    message.add_attachment(
        docx.read_bytes(),
        maintype="application",
        subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="a.docx",
    )
    out = assert_valid_pdfa(convert(api, "doc.eml", bytes(message)), tmp_path)
    assert "Fixture document" in pdf_text(out.read_bytes())


def test_remote_images_do_not_cost_the_page_its_text(api, tmp_path):
    """Chromium's broken-image icon has alpha, which would rasterise the whole page."""
    html = (
        b'<html><body><p>Searchable newsletter text</p>'
        b'<img src="http://127.0.0.1:9/hero.png" width="300" height="100" alt="hero">'
        b'<img src="relative/path.png"><img src="cid:unresolved"><img src="file:///etc/hostname">'
        b'<picture><source srcset="http://127.0.0.1:9/a.webp"><img src="http://127.0.0.1:9/a.png"></picture>'
        b"<video src='http://127.0.0.1:9/v' controls></video></body></html>"
    )
    response = convert(api, "newsletter.html", html)
    out = assert_valid_pdfa(response, tmp_path)
    assert "x-flattened-pages" not in response.headers
    assert "Searchable newsletter text" in pdf_text(out.read_bytes())


def test_meta_refresh_does_not_blank_the_page(api, tmp_path):
    html = b'<html><head><META HTTP-EQUIV="Refresh" CONTENT="0; url=http://127.0.0.1:9/"></head><body><p>Still here</p></body></html>'
    out = assert_valid_pdfa(convert(api, "refresh.html", html), tmp_path)
    assert "Still here" in pdf_text(out.read_bytes())


def test_inline_image_marked_as_attachment_is_not_listed_twice(api, tmp_path):
    """add_related with a filename produces Content-Disposition: attachment."""
    message = _email(html='<html><body><p>Text</p><img src="cid:logo"></body></html>')
    message.get_body(preferencelist=("html",)).add_related(
        png_bytes(), "image", "png", cid="<logo>", filename="logo.png"
    )
    response = convert(api, "marked.eml", bytes(message))
    out = assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-page-count"] == "1"
    assert "x-flattened-pages" not in response.headers
    assert "logo.png" not in pdf_text(out.read_bytes())
