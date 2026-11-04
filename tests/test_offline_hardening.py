"""Offline operation, container hardening, licensing constraints and log hygiene."""

from __future__ import annotations

import http.server
import importlib.util
import io
import os
import socket
import subprocess
import threading
import time
from email.message import EmailMessage
from pathlib import Path

import pikepdf
import pytest
from conftest import assert_valid_pdfa, convert, start_service
from fixtures.generate import THIRD_PARTY, make_docx, png_bytes
from PIL import Image
from test_office import pdf_text
from test_resilience import descendants
from test_security import _docx_with_linked_image

internal_only = pytest.mark.skipif(
    not os.environ.get("EXPECT_INTERNAL_NETWORK"), reason="runs on the compose internal network"
)
hardened = pytest.mark.skipif(
    not os.environ.get("EXPECT_HARDENED_CONTAINER"), reason="runs in the hardened compose container"
)
SENTINEL = "ZQX7SENTINEL"


# ---- network isolation --------------------------------------------------------------


def _can_connect(host: str, port: int, timeout: float = 3) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@internal_only
@pytest.mark.parametrize("address, port", [("1.1.1.1", 443), ("8.8.8.8", 53), ("151.101.0.223", 443)])
def test_the_internet_is_unreachable(address, port):
    assert not _can_connect(address, port)


@internal_only
def test_public_dns_does_not_resolve():
    with pytest.raises(OSError):
        socket.getaddrinfo("example.com", 443)


class _Recorder(http.server.BaseHTTPRequestHandler):
    hits: list[str] = []

    def do_GET(self):  # noqa: N802
        type(self).hits.append(self.path)
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.end_headers()
        self.wfile.write(png_bytes(Image.new("RGB", (50, 50), (0, 255, 0))))

    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def outbound_listener():
    """Listens on this container's network address, so a fetch would leave through the interface."""
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 0), _Recorder)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        try:
            probe.connect(("10.255.255.255", 1))
            address = probe.getsockname()[0]
        except OSError:
            address = "127.0.0.1"
    yield f"http://{address}:{server.server_address[1]}", _Recorder
    server.shutdown()


REMOTE_URLS = ["http://example.com/logo.png", "https://cdn.example.net/hero.jpg"]


@pytest.mark.parametrize("url", REMOTE_URLS)
def test_html_referencing_a_remote_image_converts_with_no_outbound_request(api, outbound_listener, tmp_path, url):
    base, recorder = outbound_listener
    recorder.hits.clear()
    html = f'<html><body><p>Offline text</p><img src="{url}"><img src="{base}/html.png"></body></html>'.encode()
    started = time.monotonic()
    response = convert(api, "remote.html", html)
    out = assert_valid_pdfa(response, tmp_path)
    assert recorder.hits == []
    assert time.monotonic() - started < 20, "the conversion appears to have waited on the network"
    assert "Offline text" in pdf_text(out.read_bytes())


def test_docx_referencing_a_remote_image_converts_with_no_outbound_request(api, outbound_listener, tmp_path):
    base, recorder = outbound_listener
    recorder.hits.clear()
    response = convert(api, "remote.docx", _docx_with_linked_image(f"{base}/docx.png"))
    assert_valid_pdfa(response, tmp_path)
    assert recorder.hits == []


def test_email_referencing_a_remote_image_converts_with_no_outbound_request(api, outbound_listener, tmp_path):
    base, recorder = outbound_listener
    recorder.hits.clear()
    message = EmailMessage()
    message["Subject"] = "Newsletter"
    message.set_content("Text")
    message.add_alternative(f'<html><body><p>Mail text</p><img src="{base}/mail.png"></body></html>', subtype="html")
    assert_valid_pdfa(convert(api, "remote.eml", bytes(message)), tmp_path)
    assert recorder.hits == []


# ---- Chromium -----------------------------------------------------------------------


def _browser_command(service) -> str:
    pids = descendants(service.process.pid, "/chromium")
    assert pids
    commands = subprocess.run(["ps", "-ww", "-o", "args=", "-p", ",".join(map(str, pids))], capture_output=True, text=True).stdout
    return next(line for line in commands.splitlines() if "--type=" not in line)


@pytest.mark.parametrize(
    "flag",
    [
        "--disable-background-networking",
        "--disable-component-update",
        "--safebrowsing-disable-auto-update",
        "--metrics-recording-only",
        "--disable-sync",
        "--no-pings",
    ],
)
def test_chromium_runs_with_background_traffic_disabled(service, flag):
    assert flag in _browser_command(service)


def test_chromium_is_the_debian_package_and_playwright_has_no_browsers():
    package = subprocess.run(["dpkg-query", "-W", "-f=${Status}", "chromium"], capture_output=True, text=True).stdout
    assert "install ok installed" in package
    assert list(Path("/opt/ms-playwright").iterdir()) == []
    assert os.environ["PLAYWRIGHT_BROWSERS_PATH"] == "/opt/ms-playwright"
    assert os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] == "1"


# ---- LibreOffice ---------------------------------------------------------------------


def test_libreoffice_profile_blocks_updates_and_linked_content():
    registry = Path("/opt/lo-template/user/registrymodifications.xcu").read_text()
    assert 'BlockUntrustedRefererLinks" oor:op="fuse"><value>true' in registry
    assert "Job['UpdateCheck']/Arguments\"><prop oor:name=\"AutoCheckEnabled\" oor:op=\"fuse\"><value>false" in registry
    assert 'DisableMacrosExecution" oor:op="fuse"><value>true' in registry


# ---- container hardening --------------------------------------------------------------


@hardened
def test_root_filesystem_is_read_only():
    for path in ["/srv/probe", "/opt/probe", "/etc/probe", "/probe"]:
        with pytest.raises(OSError):
            Path(path).write_text("x")


@hardened
def test_work_dirs_are_tmpfs():
    mounts = {line.split()[1]: line.split()[2] for line in Path("/proc/mounts").read_text().splitlines()}
    assert mounts.get("/tmp/work") == "tmpfs"
    assert mounts.get("/tmp/lo") == "tmpfs"
    assert mounts.get("/tmp") == "tmpfs"


@hardened
def test_no_capabilities_and_no_new_privileges():
    status = dict(line.split(":\t", 1) for line in Path("/proc/self/status").read_text().splitlines() if ":\t" in line)
    assert int(status["CapEff"], 16) == 0
    assert int(status["CapBnd"], 16) == 0
    assert status["NoNewPrivs"].strip() == "1"


@hardened
def test_cpu_and_memory_limits_are_set():
    assert Path("/sys/fs/cgroup/memory.max").read_text().strip() != "max"
    assert Path("/sys/fs/cgroup/cpu.max").read_text().split()[0] != "max"


@hardened
def test_pool_defaults_respect_the_cpu_limit():
    from app.config import effective_cpus

    quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
    assert effective_cpus() == max(1, int(int(quota) / int(period)))


def test_default_service_runs_as_non_root():
    assert os.getuid() == 10001


# ---- licensing constraints --------------------------------------------------------------


def test_heic_is_decoder_only():
    import pillow_heif

    info = pillow_heif.libheif_info()
    assert "libde265" in str(info["decoders"]).lower()
    assert "x265" not in str(info["encoders"]).lower()
    assert "x265" not in str(info).lower()


def test_no_hevc_encoder_or_microsoft_fonts_are_installed():
    packages = subprocess.run(["dpkg-query", "-W", "-f=${Package}\n"], capture_output=True, text=True).stdout.split()
    assert not [p for p in packages if "x265" in p or "mscorefonts" in p]
    assert "ghostscript" in packages and "libheif-plugin-libde265" in packages


def test_ghostscript_is_only_called_from_its_engine_module():
    """Keeps Ghostscript swappable: nothing else may start it."""
    engine = Path("/srv/app/engines/ghostscript.py")
    assert '"gs"' in engine.read_text()
    offenders = [p.name for p in Path("/srv/app").rglob("*.py") if p != engine and ('"gs"' in p.read_text() or "'gs'" in p.read_text())]
    assert offenders == []


def test_third_party_licences_are_in_the_image():
    text = Path("/srv/THIRD_PARTY_LICENSES.md").read_text()
    for section in ("## Python packages", "## System packages", "## Fonts", "## Other components"):
        assert section in text
    for needle in ("| extract-msg |", "| pikepdf |", "| ghostscript |", "| libreoffice-core-nogui |", "| chromium |", "| unoserver |", "Noto Sans CJK"):
        assert needle in text, needle
    assert "| veraPDF | 1.30.3 | MPL-2.0" in text
    assert "mscorefonts" not in text
    assert "pip-licenses" not in text.split("## Python packages")[1].split("## Fonts")[0]


def test_every_installed_python_package_is_listed():
    from importlib import metadata

    def normalise(name: str) -> str:
        return name.lower().replace("_", "-").replace(".", "-")

    listed = normalise(Path("/srv/THIRD_PARTY_LICENSES.md").read_text())
    test_only = {"pytest", "pluggy", "iniconfig", "packaging", "httpx", "httpcore", "certifi", "h11", "python-docx", "openpyxl", "et-xmlfile", "python-pptx", "xlsxwriter", "odfpy", "defusedxml", "reportlab", "pygments", "pip", "setuptools", "wheel"}
    installed = {normalise(d.metadata["Name"]) for d in metadata.distributions()}
    missing = sorted(name for name in installed - test_only if f"| {name} |" not in listed)
    assert missing == []


def test_every_font_is_listed():
    families = subprocess.run(["fc-list", "--format=%{family}\n"], capture_output=True, text=True).stdout
    text = Path("/srv/THIRD_PARTY_LICENSES.md").read_text()
    missing = {line.split(",")[0] for line in families.splitlines() if line and line.split(",")[0] not in text}
    assert missing == set()


@pytest.fixture(scope="module")
def no_msg_service():
    service = start_service("nomsg", {"ENABLE_MSG": "false", "LO_POOL_SIZE": "1"})
    yield service
    service.stop()


def test_msg_is_enabled_by_default(api):
    response = convert(api, "mail.msg", (THIRD_PARTY / "testMSG.msg").read_bytes(), validate="false")
    assert response.status_code == 200
    assert "msg" in api.get("/v1/formats").json()["families"]["email"]


def test_msg_can_be_disabled(no_msg_service):
    with no_msg_service.client() as client:
        response = convert(client, "mail.msg", (THIRD_PARTY / "testMSG.msg").read_bytes())
        assert response.status_code == 415
        assert response.json()["error"] == "UNSUPPORTED_FORMAT"
        assert "msg" not in client.get("/v1/formats").json()["families"]["email"]


def test_disabled_msg_attachment_is_noted_not_fatal(no_msg_service, tmp_path):
    message = EmailMessage()
    message["Subject"] = "Has an Outlook attachment"
    message.set_content("Body")
    message.add_attachment((THIRD_PARTY / "testMSG.msg").read_bytes(), maintype="application", subtype="vnd.ms-outlook", filename="inner.msg")
    with no_msg_service.client() as client:
        response = convert(client, "outer.eml", bytes(message))
    assert_valid_pdfa(response, tmp_path)
    assert response.headers["x-attachments-skipped"] == "1"


# ---- logging ---------------------------------------------------------------------------


def _assert_clean(service) -> None:
    time.sleep(0.3)
    logs = service.logs()
    assert SENTINEL not in logs, [line[:300] for line in logs.splitlines() if SENTINEL in line][:5]


@pytest.fixture(scope="module")
def log_service():
    service = start_service("logs", {"LO_POOL_SIZE": "1", "LOG_LEVEL": "DEBUG", "CONVERSION_TIMEOUT_SECONDS": "5"})
    yield service
    service.stop()


def test_logs_never_contain_filenames_or_contents(log_service, samples, tmp_path):
    name = f"{SENTINEL}-confidential"
    body = f"{SENTINEL} private document text\n".encode()
    with log_service.client() as client:
        # Successful conversions from each engine family
        assert convert(client, f"{name}.txt", body).status_code == 200
        assert convert(client, f"{name}.html", f"<html><title>{SENTINEL}</title><p>{SENTINEL}</p></html>".encode()).status_code == 200
        assert convert(client, f"{name}.png", samples["png"].read_bytes()).status_code == 200
        assert convert(client, f"{name}.svg", f'<svg xmlns="http://www.w3.org/2000/svg" width="9" height="9"><title>{SENTINEL}</title></svg>'.encode()).status_code == 200
        # Failures in each engine family
        assert convert(client, f"{name}.pdf", f"%PDF-1.4\n{SENTINEL}\n".encode()).status_code == 422
        assert convert(client, f"{name}.docx", f"{SENTINEL} not a docx".encode()).status_code == 422
        assert convert(client, f"{name}.exe", b"MZ\x90\x00" + bytes(200)).status_code == 415
        assert convert(client, f"{name}.svg", f"<svg><{SENTINEL}".encode()).status_code == 422
        eps = f"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 9 9\n({SENTINEL}) undefinedcommand\n".encode()
        assert convert(client, f"{name}.eps", eps).status_code in (200, 422)
        assert convert(client, f"{name}.eps", b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 9 9\n{ } loop\n").status_code == 504
        # An email with an attachment that fails
        message = EmailMessage()
        message["Subject"] = SENTINEL
        message.set_content(SENTINEL)
        message.add_attachment(b"MZ\x90\x00" + bytes(200), maintype="application", subtype="octet-stream", filename=f"{SENTINEL}.exe")
        assert convert(client, f"{name}.eml", bytes(message)).status_code == 200
    _assert_clean(log_service)
    lo_logs = "".join(p.read_text(errors="replace") for p in Path(log_service.work_dir.parent / "lo").glob("*.log"))
    assert SENTINEL not in lo_logs


def test_each_request_logs_a_summary_with_only_the_allowed_fields(log_service, samples):
    import json

    request_id = f"summary-{os.getpid()}"
    with log_service.client() as client:
        client.post("/v1/convert", files={"file": ("a.png", samples["png"].read_bytes())}, headers={"X-Request-Id": request_id})
    time.sleep(0.3)
    rows = [json.loads(line) for line in log_service.logs().splitlines() if request_id in line and line.startswith("{")]
    summary = next(row for row in rows if row["msg"] == "Request finished")
    assert summary["format"] == "png"
    assert summary["inputBytes"] == len(samples["png"].read_bytes())
    assert summary["status"] == 200 and summary["outcome"] == "OK"
    assert summary["durationMs"] >= 0
    assert set(summary) <= {
        "ts", "level", "logger", "requestId", "msg", "route", "status", "durationMs", "outcome",
        "format", "inputBytes", "outputBytes", "pages", "conversionMs", "validated",
    }


def test_failed_request_logs_its_outcome(log_service):
    import json

    request_id = f"failed-{os.getpid()}"
    with log_service.client() as client:
        client.post("/v1/convert", files={"file": ("a.exe", b"MZ\x90\x00" + bytes(200))}, headers={"X-Request-Id": request_id})
    time.sleep(0.3)
    rows = [json.loads(line) for line in log_service.logs().splitlines() if request_id in line and line.startswith("{")]
    summary = next(row for row in rows if row["msg"] == "Request finished")
    assert summary["outcome"] == "UNSUPPORTED_FORMAT" and summary["status"] == 415


# ---- the service only converts: it has no storage of its own ------------------------------


def test_the_service_has_no_object_storage_client():
    assert importlib.util.find_spec("boto3") is None
    assert not Path("/srv/app/storage").exists()


def test_the_only_conversion_route_takes_an_upload(api):
    assert api.post("/v1/convert/s3", json={}).status_code == 404


def test_docx_output_unchanged_by_offline_mode(api, tmp_path):
    docx = make_docx(tmp_path / "plain.docx", cjk=False).read_bytes()
    out = assert_valid_pdfa(convert(api, "plain.docx", docx), tmp_path)
    with pikepdf.open(io.BytesIO(out.read_bytes())) as pdf:
        assert len(pdf.pages) == 1
