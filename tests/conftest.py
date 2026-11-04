"""Test harness: runs the real service as a uvicorn subprocess and talks to it over HTTP."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).parent))

from fixtures.generate import generate_all  # noqa: E402

API_KEY = "test-api-key"
RESULTS_DIR = Path(os.environ.get("TEST_RESULTS_DIR", "/tmp/test-results"))


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@dataclass
class Service:
    base_url: str
    process: subprocess.Popen
    log_path: Path
    work_dir: Path

    def client(self, api_key: str | None = API_KEY, timeout: float = 180) -> httpx.Client:
        headers = {"X-API-Key": api_key} if api_key else {}
        return httpx.Client(base_url=self.base_url, headers=headers, timeout=timeout)

    def logs(self) -> str:
        return self.log_path.read_text(errors="replace")

    def stop(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=45)
        except subprocess.TimeoutExpired:
            self.process.kill()


def start_service(name: str, env_overrides: dict[str, str] | None = None, wait_ready: bool = True) -> Service:
    root = Path(tempfile.mkdtemp(prefix=f"svc-{name}-"))
    port = free_port()
    work_dir = root / "work"
    env = {
        **os.environ,
        "API_KEY": API_KEY,
        "LO_POOL_SIZE": "4",
        "LOG_LEVEL": "INFO",
        "WORK_DIR": str(work_dir),
        "LO_RUN_DIR": str(root / "lo"),
        "LO_BASE_PORT": str(free_port_range()),
        **(env_overrides or {}),
    }
    log_path = root / "service.log"
    handle = log_path.open("wb")
    process = subprocess.Popen(
        ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port), "--no-access-log"],
        stdout=handle,
        stderr=subprocess.STDOUT,
        env=env,
        cwd="/srv",
        start_new_session=True,
    )
    service = Service(f"http://127.0.0.1:{port}", process, log_path, work_dir)
    if wait_ready:
        wait_until_ready(service)
    return service


_next_port = 21000


def free_port_range() -> int:
    global _next_port
    _next_port += 200
    return _next_port


def wait_until_ready(service: Service, timeout: float = 120) -> None:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if service.process.poll() is not None:
            raise RuntimeError(f"Service exited during startup:\n{service.logs()[-3000:]}")
        try:
            response = httpx.get(f"{service.base_url}/health/ready", timeout=8)
            if response.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Service not ready after {timeout}s:\n{service.logs()[-3000:]}")


def wait_until_live(service: Service, timeout: float = 120) -> None:
    started = time.monotonic()
    while time.monotonic() - started < timeout:
        if service.process.poll() is not None:
            raise RuntimeError(f"Service exited during startup:\n{service.logs()[-3000:]}")
        try:
            if httpx.get(f"{service.base_url}/health/live", timeout=5).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise RuntimeError(f"Service not live after {timeout}s")


@pytest.fixture(scope="session")
def service():
    svc = start_service("main")
    yield svc
    svc.stop()


@pytest.fixture(scope="session")
def api(service):
    with service.client() as client:
        yield client


@pytest.fixture(scope="session")
def samples(tmp_path_factory) -> dict[str, Path]:
    return generate_all(tmp_path_factory.mktemp("samples"))


@dataclass
class VeraResult:
    compliant: bool
    failures: list[str]


def verapdf(path: Path) -> VeraResult:
    """Runs veraPDF directly, so tests do not rely on the service's own report."""
    result = subprocess.run(
        ["verapdf", "--flavour", "1b", "--format", "json", str(path)],
        capture_output=True, text=True, timeout=120,
    )
    job = json.loads(result.stdout)["report"]["jobs"][0]
    report = job["validationResult"]
    report = report[0] if isinstance(report, list) else report
    failures = [
        f'{rule["clause"]}-{rule["testNumber"]} ({rule["failedChecks"]}x): {rule.get("description", "")[:100]}'
        for rule in report["details"]["ruleSummaries"]
        if rule.get("failedChecks")
    ]
    return VeraResult(bool(report["compliant"]), failures)


def convert(client: httpx.Client, name: str, data: bytes, **form) -> httpx.Response:
    return client.post("/v1/convert", files={"file": (name, data)}, data=form)


def assert_valid_pdfa(response: httpx.Response, tmp_path: Path, name: str = "out.pdf") -> Path:
    assert response.status_code == 200, response.text[:800]
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    out = tmp_path / name
    out.write_bytes(response.content)
    report = verapdf(out)
    assert report.compliant, f"veraPDF failures: {report.failures}"
    return out


@pytest.fixture(scope="session", autouse=True)
def _results_dir():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
