"""Timeouts, crash recovery, cleanup and engine isolation."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import time

import httpx
import pytest
from conftest import API_KEY, assert_valid_pdfa, convert, start_service
from fixtures.generate import make_docx, png_bytes
from PIL import Image

HANGING_EPS = b"%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 100 100\n{ } loop\n"


def descendants(root_pid: int, match: str) -> list[int]:
    """PIDs of processes whose command line contains `match` and that belong to this service."""
    # -ww: without a terminal, ps otherwise cuts command lines at 80 columns.
    output = subprocess.run(["ps", "-ww", "-eo", "pid=,ppid=,args="], capture_output=True, text=True).stdout
    children: dict[int, list[int]] = {}
    commands: dict[int, str] = {}
    for line in output.splitlines():
        pid, ppid, args = line.strip().split(None, 2)
        children.setdefault(int(ppid), []).append(int(pid))
        commands[int(pid)] = args
    found, stack = [], [root_pid]
    while stack:
        for child in children.get(stack.pop(), []):
            stack.append(child)
            if match in commands[child]:
                found.append(child)
    return found


def wait_for(predicate, timeout: float, message: str, interval: float = 0.25):
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        value = predicate()
        if value:
            return value
        time.sleep(interval)
    raise AssertionError(message)


def work_dir_entries(service) -> list[str]:
    return [p.name for p in service.work_dir.iterdir()] if service.work_dir.exists() else []


def lo_status(service) -> dict:
    return httpx.get(f"{service.base_url}/health/ready", timeout=10).json()["checks"]["libreoffice"]


# ---- timeouts ------------------------------------------------------------------------


@pytest.fixture(scope="module")
def quick_timeout():
    service = start_service("quick", {"CONVERSION_TIMEOUT_SECONDS": "4", "LO_POOL_SIZE": "1", "HTML_ALLOW_INLINE_JS": "true", "READY_CACHE_SECONDS": "0"})
    yield service
    service.stop()


def assert_timeout(response, service):
    assert response.status_code == 504, response.text[:300]
    body = response.json()
    assert body["error"] == "CONVERSION_TIMEOUT" and body["requestId"]
    assert work_dir_entries(service) == []


def test_ghostscript_timeout_kills_the_process(quick_timeout):
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(1) as pool, quick_timeout.client() as client:
        started = time.monotonic()
        future = pool.submit(convert, client, "hang.eps", HANGING_EPS)
        # While it runs, the process must be visible, or the check below would prove nothing.
        wait_for(lambda: descendants(quick_timeout.process.pid, "-sDEVICE=pdfwrite"), 3, "Ghostscript never started", 0.05)
        response = future.result()
    assert_timeout(response, quick_timeout)
    assert time.monotonic() - started < 8
    assert descendants(quick_timeout.process.pid, "-sDEVICE=pdfwrite") == []


def test_chromium_timeout_on_endless_script(quick_timeout, samples):
    with quick_timeout.client() as client:
        response = convert(client, "spin.html", b"<html><body><script>while(true){}</script></body></html>")
        assert_timeout(response, quick_timeout)
        # The service recovers, without waiting for anything to restart.
        html = convert(client, "ok.html", b"<html><body><p>Recovered</p></body></html>", validate="false")
    assert html.status_code == 200, html.text[:300]


def test_libreoffice_timeout_replaces_the_instance(quick_timeout):
    """A very long text file keeps LibreOffice busy far past the 4s limit."""
    big = ("All work and no play makes Jack a dull boy. " * 40 + "\n").encode() * 2800
    assert len(big) < 5_242_880
    with quick_timeout.client() as client:
        response = convert(client, "long.txt", big)
        assert_timeout(response, quick_timeout)
        wait_for(lambda: lo_status(quick_timeout)["idle"] == 1, 60, "the instance was not replaced")
        small = convert(client, "ok.txt", b"Back in service\n", validate="false")
    assert small.status_code == 200, small.text[:300]


def test_isolated_decoder_timeout_kills_the_child(quick_timeout):
    """An SVG with a huge pattern tiling keeps cairo busy; the child must be killed."""
    shapes = "".join(f'<use xlink:href="#a{i}"/><use xlink:href="#a{i}"/>' for i in range(1))
    levels = "".join(
        f'<g id="a{i}"><use xlink:href="#a{i + 1}"/><use xlink:href="#a{i + 1}"/><use xlink:href="#a{i + 1}"/></g>' for i in range(30)
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="100" height="100">'
        f'<defs>{levels}<rect id="a30" width="1" height="1"/></defs>{shapes}</svg>'
    ).encode()
    forkserver = descendants(quick_timeout.process.pid, "multiprocessing.forkserver")
    assert len(forkserver) == 1

    def worker_children() -> list[int]:
        listing = subprocess.run(["ps", "-ww", "-eo", "pid=,ppid="], capture_output=True, text=True).stdout
        return [int(line.split()[0]) for line in listing.splitlines() if int(line.split()[1]) == forkserver[0]]

    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(1) as pool, quick_timeout.client() as client:
        started = time.monotonic()
        future = pool.submit(convert, client, "billion-laughs.svg", svg)
        wait_for(worker_children, 3, "the decoder process never started", 0.02)
        response = future.result()
    assert_timeout(response, quick_timeout)
    assert time.monotonic() - started < 8
    assert worker_children() == []


def test_timeout_does_not_block_other_requests(quick_timeout, samples):
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(2) as pool, quick_timeout.client() as client:
        hanging = pool.submit(convert, client, "hang.eps", HANGING_EPS)
        time.sleep(0.5)
        started = time.monotonic()
        quick = convert(client, "ok.png", samples["png"].read_bytes(), validate="false")
        elapsed = time.monotonic() - started
        assert quick.status_code == 200
        assert elapsed < 2, f"another request waited {elapsed:.1f}s behind a hanging one"
        assert hanging.result().status_code == 504


# ---- crash recovery ------------------------------------------------------------------


@pytest.fixture(scope="module")
def watchdog_service():
    service = start_service("watchdog", {"LO_POOL_SIZE": "2", "LO_HEALTH_INTERVAL_SECONDS": "1", "READY_CACHE_SECONDS": "0"})
    yield service
    service.stop()


def test_crashed_soffice_is_restarted(watchdog_service, tmp_path):
    before = descendants(watchdog_service.process.pid, "soffice.bin")
    assert len(before) == 2
    os.kill(before[0], signal.SIGKILL)

    def replaced():
        now = descendants(watchdog_service.process.pid, "soffice.bin")
        status = lo_status(watchdog_service)
        return len(now) == 2 and before[0] not in now and status["idle"] == 2

    wait_for(replaced, 60, "the crashed instance was not replaced")
    docx = make_docx(tmp_path / "a.docx", cjk=False)
    with watchdog_service.client() as client:
        for _ in range(4):
            assert_valid_pdfa(convert(client, "a.docx", docx.read_bytes(), validate="false"), tmp_path)


def test_hung_soffice_is_detected_and_replaced(watchdog_service, tmp_path):
    """A frozen process stays alive, so only the health check can notice it."""
    wait_for(lambda: lo_status(watchdog_service)["idle"] == 2, 60, "pool not idle")
    before = descendants(watchdog_service.process.pid, "soffice.bin")
    assert len(before) == 2
    os.kill(before[0], signal.SIGSTOP)

    def replaced():
        now = descendants(watchdog_service.process.pid, "soffice.bin")
        return before[0] not in now and len(now) == 2 and lo_status(watchdog_service)["idle"] == 2

    try:
        wait_for(replaced, 90, "the hung instance was not replaced")
    except AssertionError as exc:
        raise AssertionError(f"{exc}\nstatus={lo_status(watchdog_service)}\nprocesses={descendants(watchdog_service.process.pid, 'soffice.bin')} frozen={before[0]}\n{watchdog_service.logs()[-2500:]}") from None
    docx = make_docx(tmp_path / "b.docx", cjk=False)
    with watchdog_service.client() as client:
        assert_valid_pdfa(convert(client, "b.docx", docx.read_bytes()), tmp_path)


def test_request_right_after_a_crash_is_not_failed(tmp_path):
    """soffice can die behind a running unoserver, which then reports faults, not disconnects.

    The health check takes seconds to notice, so a request in that window must be retried
    on a healthy instance instead of receiving a 500. No watchdog runs in this test.
    """
    service = start_service("afterkill", {"LO_POOL_SIZE": "2", "LO_HEALTH_INTERVAL_SECONDS": "600"})
    try:
        docx = make_docx(tmp_path / "a.docx", cjk=False).read_bytes()
        pids = descendants(service.process.pid, "soffice.bin")
        os.kill(pids[0], signal.SIGKILL)
        with service.client() as client:
            statuses = [convert(client, "a.docx", docx, validate="false").status_code for _ in range(4)]
        assert statuses == [200, 200, 200, 200]
    finally:
        service.stop()


def test_crash_during_a_request_is_retried_or_reported(watchdog_service, tmp_path):
    """Killing every instance mid-request: the caller gets an answer, never a hang."""
    import concurrent.futures

    wait_for(lambda: lo_status(watchdog_service)["idle"] == 2, 60, "pool not idle")
    big = ("Filler text for a slow conversion. " * 40 + "\n").encode() * 700
    with concurrent.futures.ThreadPoolExecutor(1) as pool, watchdog_service.client() as client:
        future = pool.submit(convert, client, "slow.txt", big, validate="false")
        time.sleep(0.4)
        for pid in descendants(watchdog_service.process.pid, "soffice.bin"):
            os.kill(pid, signal.SIGKILL)
        response = future.result(timeout=120)
    assert response.status_code in (200, 500), response.text[:300]
    if response.status_code == 500:
        assert response.json()["error"] == "CONVERSION_FAILED"
    wait_for(lambda: lo_status(watchdog_service)["idle"] == 2, 60, "the pool did not recover")


def test_killed_chromium_is_relaunched(watchdog_service, tmp_path):
    with watchdog_service.client() as client:
        assert convert(client, "a.html", b"<p>Before</p>", validate="false").status_code == 200
        browsers = descendants(watchdog_service.process.pid, "/chromium")
        assert browsers, subprocess.run(["ps", "-eo", "pid,ppid,stat,args"], capture_output=True, text=True).stdout[:3000]
        for pid in browsers:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        time.sleep(1)
        response = convert(client, "b.html", b"<p>After the crash</p>", validate="false")
    assert response.status_code == 200, response.text[:300]


def test_instances_are_recycled_after_their_conversion_limit(tmp_path):
    service = start_service("recycle", {"LO_POOL_SIZE": "1", "LO_MAX_CONVERSIONS": "2"})
    try:
        docx = make_docx(tmp_path / "a.docx", cjk=False).read_bytes()
        first = descendants(service.process.pid, "soffice.bin")
        with service.client() as client:
            for _ in range(3):
                assert convert(client, "a.docx", docx, validate="false").status_code == 200
        wait_for(lambda: descendants(service.process.pid, "soffice.bin") not in ([], first), 60, "the instance was not recycled")
    finally:
        service.stop()


def test_shutdown_leaves_no_engine_processes():
    service = start_service("shutdown", {"LO_POOL_SIZE": "2"})
    root = service.process.pid
    pool_pids = descendants(root, "soffice.bin") + descendants(root, "lo_server.py")
    assert pool_pids
    service.stop()
    time.sleep(1)
    alive = []
    for pid in pool_pids:
        try:
            os.kill(pid, 0)
            state = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
            if state and not state.startswith("Z"):
                alive.append(pid)
        except ProcessLookupError:
            pass
    assert alive == []


# ---- cleanup -------------------------------------------------------------------------


@pytest.fixture(scope="module")
def clean_service():
    service = start_service("clean", {"LO_POOL_SIZE": "1"})
    yield service
    service.stop()


def test_temp_dirs_are_removed_after_success_and_errors(clean_service, samples, tmp_path):
    with clean_service.client() as client:
        assert convert(client, "a.pdf", samples["pdf"].read_bytes(), validate="false").status_code == 200
        assert convert(client, "a.exe", b"MZ\x90\x00" + bytes(200)).status_code == 415
        assert convert(client, "a.pdf", b"%PDF-1.4\nbroken").status_code == 422
    time.sleep(0.2)
    assert work_dir_entries(clean_service) == []


def test_temp_dir_is_removed_when_the_client_disconnects_mid_download(clean_service):
    """A background task would not run here; the response has to clean up itself."""
    noise = Image.effect_noise((1200, 1200), 90).convert("RGB")
    data = png_bytes(noise)
    assert len(data) < 5_242_880
    boundary = "b0undary"
    body = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="validate"\r\n\r\nfalse\r\n'
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="n.png"\r\n\r\n'
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    host, port = clean_service.base_url.removeprefix("http://").split(":")
    with socket.create_connection((host, int(port)), timeout=60) as sock:
        sock.sendall(
            f"POST /v1/convert HTTP/1.1\r\nHost: x\r\nX-API-Key: {API_KEY}\r\n"
            f"Content-Type: multipart/form-data; boundary={boundary}\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body
        )
        assert sock.recv(4096).startswith(b"HTTP/1.1 200")
    wait_for(lambda: work_dir_entries(clean_service) == [], 15, "the temp dir was left behind")


def test_leftovers_from_a_previous_run_are_removed_at_startup(tmp_path):
    work = tmp_path / "work"
    (work / "stale-request").mkdir(parents=True)
    (work / "stale-request" / "secret.docx").write_bytes(b"old data")
    service = start_service("sweep", {"WORK_DIR": str(work), "LO_POOL_SIZE": "1"})
    try:
        assert list(work.iterdir()) == []
    finally:
        service.stop()


# ---- limits and isolation ------------------------------------------------------------


def test_decompression_bomb_image_is_rejected(service, api):
    """A small PNG that decodes to 500 megapixels must not be decoded."""
    import struct
    import zlib

    width, height = 25000, 20000
    raw = zlib.compressobj(9)
    row = b"\x00" * (width // 8 + 1)
    compressed = raw.compress(row * 400) + raw.flush()

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))

    bomb = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 1, 0, 0, 0, 0))
        + chunk(b"IDAT", compressed)
        + chunk(b"IEND", b"")
    )
    response = convert(api, "bomb.png", bomb)
    assert response.status_code == 422, response.text[:300]
    assert response.json()["error"] == "CORRUPT_FILE"


def test_zip_bomb_office_file_is_rejected(api):
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", '<Types><Override ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr("word/document.xml", b"\x00" * (1100 * 1024 * 1024))
    data = buffer.getvalue()
    assert len(data) < 5_242_880
    response = convert(api, "bomb.docx", data)
    assert response.status_code == 422
    assert response.json()["error"] == "CORRUPT_FILE"


def test_memory_hungry_decoder_cannot_take_down_the_service(samples):
    """With a low memory limit the child fails; the service keeps answering."""
    service = start_service("lowmem", {"ENGINE_MEMORY_LIMIT_MB": "400", "LO_POOL_SIZE": "1"})
    try:
        data = png_bytes(Image.new("L", (15000, 15000), 128))
        with service.client() as client:
            response = convert(client, "large.png", data, validate="false")
            assert response.status_code in (200, 422, 500), response.text[:300]
            assert convert(client, "ok.png", samples["png"].read_bytes(), validate="false").status_code == 200
    finally:
        service.stop()


def test_runs_as_non_root():
    assert os.getuid() != 0
    assert not os.access("/srv/app", os.W_OK)
    assert not os.access("/opt/verapdf", os.W_OK)


def test_nothing_was_left_in_the_main_work_dir(service, api, samples):
    assert convert(api, "a.png", samples["png"].read_bytes(), validate="false").status_code == 200
    wait_for(lambda: work_dir_entries(service) == [], 10, "the temp dir was left behind")

