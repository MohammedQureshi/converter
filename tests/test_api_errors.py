"""The API contract: authentication, limits, the error model, and request IDs."""

from __future__ import annotations

import io
import os
import stat
import time
import uuid
import zipfile
from pathlib import Path

import httpx
import pikepdf
import pytest
from conftest import assert_valid_pdfa, convert, start_service
from fixtures.generate import THIRD_PARTY, encrypted_pdf, make_docx, make_pdf, png_bytes
from PIL import Image


def assert_error(response: httpx.Response, status: int, code: str) -> dict:
    assert response.status_code == status, response.text[:500]
    assert response.headers["content-type"].startswith("application/json")
    body = response.json()
    assert set(body) == {"error", "message", "requestId"}
    assert body["error"] == code
    assert body["message"]
    uuid.UUID(body["requestId"])
    return body


# ---- authentication ----------------------------------------------------------------


def test_missing_api_key_is_401(service, samples):
    with service.client(api_key=None) as client:
        assert_error(convert(client, "a.png", samples["png"].read_bytes()), 401, "UNAUTHORIZED")


def test_wrong_api_key_is_401(service, samples):
    with service.client(api_key="wrong") as client:
        assert_error(convert(client, "a.png", samples["png"].read_bytes()), 401, "UNAUTHORIZED")


@pytest.mark.parametrize("method, path", [("GET", "/v1/formats"), ("POST", "/v1/convert")])
def test_other_endpoints_need_a_key(service, method, path):
    with service.client(api_key=None) as client:
        assert_error(client.request(method, path), 401, "UNAUTHORIZED")


@pytest.mark.parametrize("path", ["/health/live", "/health/ready"])
def test_health_needs_no_key(service, path):
    with service.client(api_key=None) as client:
        assert client.get(path).status_code == 200


def test_auth_is_checked_before_a_huge_body_is_read(service):
    """Anonymous callers must not be able to make the service spool uploads to disk."""
    with service.client(api_key=None) as client:
        response = client.post("/v1/convert", files={"file": ("big.pdf", b"x" * 1024)})
        assert response.status_code == 401


def test_service_refuses_to_start_without_an_api_key():
    service = start_service("nokey", {"API_KEY": ""}, wait_ready=False)
    try:
        assert service.process.wait(timeout=30) != 0
        assert "API_KEY must be set" in service.logs()
    finally:
        service.stop()


# ---- size limit --------------------------------------------------------------------


def test_over_5mb_is_413(api):
    assert_error(convert(api, "big.pdf", b"%PDF-1.4\n" + bytes(5_242_880)), 413, "FILE_TOO_LARGE")


def test_exactly_5mb_is_accepted_and_output_may_exceed_it(api, tmp_path):
    source = make_pdf(tmp_path / "padded.pdf", pages=1).read_bytes()
    padded = source + b"\n%" + b"x" * (5_242_880 - len(source) - 2)
    assert len(padded) == 5_242_880
    assert convert(api, "padded.pdf", padded, validate="false").status_code == 200


def test_one_byte_over_is_413(api, tmp_path):
    source = make_pdf(tmp_path / "padded.pdf", pages=1).read_bytes()
    padded = source + b"\n%" + b"x" * (5_242_880 - len(source) - 1)
    assert len(padded) == 5_242_881
    assert_error(convert(api, "padded.pdf", padded), 413, "FILE_TOO_LARGE")


def test_output_larger_than_the_input_limit_is_allowed(api, tmp_path):
    """A CMYK JPEG must be decoded to convert it, so the output is far larger than the input."""
    noise = Image.effect_noise((1800, 1800), 60)
    image = Image.merge("CMYK", (noise, noise.rotate(90), noise.rotate(180), Image.new("L", noise.size, 0)))
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=30)
    assert len(buffer.getvalue()) < 5_242_880
    response = convert(api, "large.jpg", buffer.getvalue(), validate="false")
    assert response.status_code == 200, response.text[:300]
    assert len(response.content) > 5_242_880


def test_chunked_upload_over_the_limit_is_413(service):
    """With no Content-Length, the limit is enforced by counting bytes as they arrive."""
    boundary = "testboundary"

    def body():
        yield (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="big.pdf"\r\n\r\n').encode()
        for _ in range(7):
            yield b"x" * (1024 * 1024)
        yield f"\r\n--{boundary}--\r\n".encode()

    with service.client() as client:
        response = client.post(
            "/v1/convert",
            content=body(),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Transfer-Encoding": "chunked"},
        )
    assert_error(response, 413, "FILE_TOO_LARGE")


# ---- unsupported types -------------------------------------------------------------


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("readme.txt", "hello")
    return buffer.getvalue()


@pytest.mark.parametrize(
    "name, data",
    [
        ("program.exe", b"MZ\x90\x00\x03\x00\x00\x00" + bytes(512)),
        ("program", b"\x7fELF\x02\x01\x01\x00" + bytes(512)),
        ("archive.zip", _zip_bytes()),
        ("sound.mp3", b"ID3\x04\x00\x00\x00\x00\x00\x00" + bytes(512)),
        ("video.mp4", b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + bytes(512)),
        ("drawing.dwg", b"AC1027" + bytes(512)),
        ("page.ps", b"%!PS-Adobe-3.0\nshowpage\n"),
        ("notes.log", b"plain text in an unsupported extension\n"),
        ("script.py", b"print('hello')\n"),
    ],
)
def test_unsupported_formats_are_415(api, name, data):
    assert_error(convert(api, name, data), 415, "UNSUPPORTED_FORMAT")


def test_executable_with_a_pdf_name_is_415(api):
    """The content decides, not the name."""
    assert_error(convert(api, "invoice.pdf", b"MZ\x90\x00\x03\x00\x00\x00" + bytes(512)), 415, "UNSUPPORTED_FORMAT")


def test_zip_with_a_docx_name_is_rejected(api):
    response = convert(api, "fake.docx", _zip_bytes())
    assert_error(response, 422, "CORRUPT_FILE")


def test_png_with_a_jpg_name_is_converted(api, samples, tmp_path):
    response = convert(api, "wrong.jpg", samples["png"].read_bytes())
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-source-format"] == "png"


def test_file_without_an_extension_is_detected(api, samples, tmp_path):
    response = convert(api, "upload", samples["pdf"].read_bytes())
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-source-format"] == "pdf"


# ---- encrypted files ---------------------------------------------------------------


def test_encrypted_pdf_is_422(api, tmp_path):
    body = assert_error(convert(api, "locked.pdf", encrypted_pdf(tmp_path / "locked.pdf").read_bytes()), 422, "ENCRYPTED_FILE")
    assert "encrypted" in body["message"].lower() or "password" in body["message"].lower()


@pytest.mark.parametrize(
    "name",
    [
        "testWORD_protected_passtika.doc",
        "testWORD_protected_passtika.docx",
        "testEXCEL_protected_passtika.xls",
        "testEXCEL_protected_passtika.xlsx",
        "testPPT_protected_passtika.ppt",
        "testPPT_protected_passtika.pptx",
        "testODTEncrypted.odt",
    ],
)
def test_encrypted_office_files_are_422(api, name):
    assert_error(convert(api, name, (THIRD_PARTY / name).read_bytes()), 422, "ENCRYPTED_FILE")


# ---- corrupt files -----------------------------------------------------------------


def _truncated(data: bytes, keep: float = 0.5) -> bytes:
    return data[: int(len(data) * keep)]


def test_corrupt_inputs_are_422(api, samples):
    cases = {
        "empty.pdf": b"",
        "garbage.pdf": b"%PDF-1.7\nthis is not really a pdf\n%%EOF\n",
        "random.pdf": os.urandom(4096),
        "random.docx": os.urandom(4096),
        "text.png": b"not an image at all\n",
        "truncated.docx": _truncated(samples["docx"].read_bytes()),
        "truncated.xlsx": _truncated(samples["xlsx"].read_bytes()),
        "truncated.png": _truncated(samples["png"].read_bytes()),
        "truncated.jpg": _truncated(samples["jpg"].read_bytes()),
        "truncated.gif": _truncated(samples["gif"].read_bytes()),
        "truncated.webp": _truncated(samples["webp"].read_bytes()),
        "truncated.heic": _truncated(samples["heic"].read_bytes()),
        "broken.svg": b"<svg xmlns='http://www.w3.org/2000/svg'><rect",
        "notsvg.svg": b"just some text\n",
    }
    failures = {}
    for name, data in cases.items():
        response = convert(api, name, data)
        if response.status_code != 422 or response.json()["error"] != "CORRUPT_FILE":
            failures[name] = (response.status_code, response.text[:200])
    assert not failures, failures


def test_truncated_pdf_never_returns_a_bad_file(api, samples, tmp_path):
    """qpdf can often recover a truncated PDF. Either outcome is fine; bad output is not."""
    data = _truncated(samples["pdf"].read_bytes(), 0.8)
    response = convert(api, "truncated.pdf", data)
    if response.status_code == 200:
        assert_valid_pdfa(response, tmp_path)
    else:
        assert_error(response, 422, "CORRUPT_FILE")


def test_corrupt_ole_document_is_422(api, samples):
    data = bytearray(samples["doc"].read_bytes())
    data[512:] = os.urandom(len(data) - 512)
    response = convert(api, "scrambled.doc", bytes(data))
    assert response.status_code == 422, response.text[:300]


# ---- bad requests ------------------------------------------------------------------


def test_missing_file_is_400(api):
    assert_error(api.post("/v1/convert", data={"validate": "true"}), 400, "BAD_REQUEST")


def test_not_multipart_is_400(api):
    assert_error(api.post("/v1/convert", content=b"hello", headers={"Content-Type": "text/plain"}), 400, "BAD_REQUEST")


def test_invalid_validate_value_is_400(api, samples):
    assert_error(convert(api, "a.png", samples["png"].read_bytes(), validate="perhaps"), 400, "BAD_REQUEST")


def test_unknown_route_and_method_use_the_error_model(api):
    assert_error(api.get("/v1/nope"), 404, "NOT_FOUND")
    assert_error(api.get("/v1/convert"), 405, "METHOD_NOT_ALLOWED")


# ---- success contract --------------------------------------------------------------


def test_success_headers_are_all_present(api, samples):
    response = convert(api, "a.png", samples["png"].read_bytes())
    assert response.status_code == 200
    assert response.headers["x-source-format"] == "png"
    assert response.headers["x-pdfa-validated"] == "true"
    assert response.headers["x-page-count"] == "1"
    assert int(response.headers["x-conversion-ms"]) >= 0
    uuid.UUID(response.headers["x-request-id"])
    assert 'filename="a.pdf"' in response.headers["content-disposition"]


def test_validation_can_be_skipped_per_request(api, samples):
    response = convert(api, "a.png", samples["png"].read_bytes(), validate="false")
    assert response.headers["x-pdfa-validated"] == "skipped"


def test_formats_lists_every_family(api):
    families = api.get("/v1/formats").json()["families"]
    assert set(families) == {"word_processing", "spreadsheet", "presentation", "diagram", "raster_image", "modern_image", "vector", "web", "email", "pdf"}
    assert "docx" in families["word_processing"] and "heic" in families["modern_image"]
    assert sum(len(extensions) for extensions in families.values()) == 42


def test_readiness_reports_each_engine(service):
    with service.client() as client:
        checks = client.get("/health/ready").json()["checks"]
    assert checks["libreoffice"]["ok"] and checks["libreoffice"]["alive"] == 4
    assert checks["ghostscript"]["ok"] and checks["chromium"]["ok"] and "s3" not in checks


# ---- request IDs -------------------------------------------------------------------


def test_caller_request_id_is_echoed_and_logged(service, samples):
    request_id = f"caller-{uuid.uuid4()}"
    with service.client() as client:
        response = client.post(
            "/v1/convert", files={"file": ("a.png", samples["png"].read_bytes())}, headers={"X-Request-Id": request_id}
        )
    assert response.headers["x-request-id"] == request_id
    time.sleep(0.2)
    assert request_id in service.logs()


def test_caller_request_id_appears_in_errors(api):
    response = api.post(
        "/v1/convert", files={"file": ("a.exe", b"MZ\x90\x00" + bytes(200))}, headers={"X-Request-Id": "error-id-123"}
    )
    assert response.json()["requestId"] == "error-id-123"
    assert response.headers["x-request-id"] == "error-id-123"


def test_unsafe_request_id_is_replaced(api, samples):
    response = api.post(
        "/v1/convert", files={"file": ("a.png", samples["png"].read_bytes())}, headers={"X-Request-Id": "bad id with spaces"}
    )
    uuid.UUID(response.headers["x-request-id"])


# ---- configuration -----------------------------------------------------------------


def _fake_verapdf(directory: Path, compliant: bool) -> Path:
    """A stand-in validator on PATH, since real output is always compliant."""
    script = directory / "verapdf"
    report = (
        '{"report":{"jobs":[{"validationResult":[{"compliant":%s,"details":{"ruleSummaries":'
        '[{"clause":"6.1","testNumber":1,"failedChecks":1,"description":"Forced failure"}]}}]}]}}'
    ) % str(compliant).lower()
    script.write_text(f"#!/bin/sh\ncat <<'EOF'\n{report}\nEOF\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return directory


def test_strict_mode_turns_validation_failure_into_422(tmp_path, samples):
    fake = _fake_verapdf(tmp_path, compliant=False)
    env = {"STRICT_VALIDATION": "true", "LO_POOL_SIZE": "1", "PATH": f"{fake}:{os.environ['PATH']}"}
    service = start_service("strict", env)
    try:
        with service.client() as client:
            body = assert_error(convert(client, "a.png", samples["png"].read_bytes()), 422, "PDFA_VALIDATION_FAILED")
            assert "Forced failure" in body["message"]
    finally:
        service.stop()


def test_non_strict_mode_reports_failure_in_the_header(tmp_path, samples):
    fake = _fake_verapdf(tmp_path, compliant=False)
    service = start_service("nonstrict", {"LO_POOL_SIZE": "1", "PATH": f"{fake}:{os.environ['PATH']}"})
    try:
        with service.client() as client:
            response = convert(client, "a.png", samples["png"].read_bytes())
        assert response.status_code == 200
        assert response.headers["x-pdfa-validated"] == "false"
    finally:
        service.stop()


def test_broken_validator_counts_as_not_validated(tmp_path, samples):
    script = tmp_path / "verapdf"
    script.write_text("#!/bin/sh\necho 'not json'\nexit 7\n")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    service = start_service("broken-vera", {"LO_POOL_SIZE": "1", "PATH": f"{tmp_path}:{os.environ['PATH']}"})
    try:
        with service.client() as client:
            response = convert(client, "a.png", samples["png"].read_bytes())
        assert response.status_code == 200
        assert response.headers["x-pdfa-validated"] == "false"
    finally:
        service.stop()


def test_validate_default_false_can_be_overridden(samples):
    service = start_service("novalidate", {"VALIDATE_DEFAULT": "false", "LO_POOL_SIZE": "1"})
    try:
        with service.client() as client:
            default = convert(client, "a.png", samples["png"].read_bytes())
            forced = convert(client, "a.png", samples["png"].read_bytes(), validate="true")
        assert default.headers["x-pdfa-validated"] == "skipped"
        assert forced.headers["x-pdfa-validated"] == "true"
    finally:
        service.stop()


def test_max_pages_is_enforced_for_each_engine(samples, tmp_path):
    service = start_service("maxpages", {"MAX_PAGES": "2", "LO_POOL_SIZE": "1"})
    try:
        with service.client() as client:
            pdf = make_pdf(tmp_path / "three.pdf", pages=3).read_bytes()
            assert_error(convert(client, "three.pdf", pdf), 422, "TOO_MANY_PAGES")
            assert_error(convert(client, "scan.tif", samples["tif"].read_bytes()), 422, "TOO_MANY_PAGES")
            docx = make_docx(tmp_path / "three.docx", pages=3, cjk=False).read_bytes()
            assert_error(convert(client, "three.docx", docx), 422, "TOO_MANY_PAGES")
            html = "".join(f'<p style="page-break-after:always">Page {i}</p>' for i in range(3)).encode()
            assert_error(convert(client, "three.html", html), 422, "TOO_MANY_PAGES")
            assert convert(client, "two.pdf", make_pdf(tmp_path / "two.pdf", pages=2).read_bytes()).status_code == 200
    finally:
        service.stop()


def test_invalid_page_size_stops_startup():
    service = start_service("badsize", {"DEFAULT_PAGE_SIZE": "Tabloid"}, wait_ready=False)
    try:
        assert service.process.wait(timeout=30) != 0
    finally:
        service.stop()


def test_pdf_metadata_survives_unusual_filenames(api, samples, tmp_path):
    for name in ["../../../etc/passwd.png", "C:\\Users\\me\\photo.png", "$(touch pwned).png", 'quote".png', "日本語.png"]:
        response = convert(api, name, samples["png"].read_bytes())
        out = assert_valid_pdfa(response, tmp_path)
        with pikepdf.open(out) as pdf, pdf.open_metadata() as meta:
            source = meta["dc:source"]
        assert "/" not in source and "\\" not in source, source
        assert "\n" not in response.headers["content-disposition"]
    assert not Path("pwned").exists()

