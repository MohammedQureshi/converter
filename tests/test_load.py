"""Concurrency and latency. Prints a table and writes JSON to TEST_RESULTS_DIR.

    docker compose -f docker-compose.test.yml run --rm converter pytest tests/test_load.py -s
"""

from __future__ import annotations

import concurrent.futures
import json
import statistics
import time

import pytest
from conftest import RESULTS_DIR, convert, verapdf
from fixtures.generate import make_docx

pytestmark = pytest.mark.load

CONCURRENT_REQUESTS = 20
FORMAT_REPEATS = 5


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _report(name: str, data: dict) -> None:
    (RESULTS_DIR / f"{name}.json").write_text(json.dumps(data, indent=2))


def test_20_concurrent_docx_conversions(api, service, tmp_path):
    docx = make_docx(tmp_path / "load.docx", cjk=False).read_bytes()
    convert(api, "warm.docx", docx)  # JIT and page-cache warmup, not counted

    def one(index: int) -> tuple[float, int, str]:
        started = time.monotonic()
        response = convert(api, f"load-{index}.docx", docx)
        return (time.monotonic() - started) * 1000, response.status_code, response.headers.get("x-pdfa-validated", "")

    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(CONCURRENT_REQUESTS) as pool:
        results = list(pool.map(one, range(CONCURRENT_REQUESTS)))
    wall = time.monotonic() - started

    latencies = [r[0] for r in results]
    summary = {
        "requests": CONCURRENT_REQUESTS,
        "lo_pool_size": 4,
        "p50_ms": round(percentile(latencies, 0.50)),
        "p95_ms": round(percentile(latencies, 0.95)),
        "max_ms": round(max(latencies)),
        "wall_s": round(wall, 2),
        "throughput_per_s": round(CONCURRENT_REQUESTS / wall, 2),
    }
    _report("load_docx", summary)
    print(f"\n20 concurrent DOCX (validation on, pool of 4): {summary}")
    assert all(r[1] == 200 for r in results), [r[1] for r in results]
    assert all(r[2] == "true" for r in results)
    assert summary["p95_ms"] < 30_000


def test_mixed_concurrent_load_stays_compliant(api, samples, tmp_path):
    formats = ["docx", "xlsx", "pptx", "png", "jpg", "html", "md", "svg", "eps", "pdf", "eml", "heic", "tif", "csv", "txt", "odt"]

    def one(ext: str):
        return ext, convert(api, f"mixed.{ext}", samples[ext].read_bytes(), validate="false")

    with concurrent.futures.ThreadPoolExecutor(16) as pool:
        results = list(pool.map(one, formats * 2))
    for index, (ext, response) in enumerate(results):
        assert response.status_code == 200, f"{ext}: {response.text[:200]}"
        out = tmp_path / f"{index}.{ext}.pdf"
        out.write_bytes(response.content)
    sample = tmp_path / "0.docx.pdf"
    assert verapdf(sample).compliant


def _realistic_documents(tmp_path) -> dict[str, tuple[str, bytes]]:
    """Larger inputs, closer to what real callers send than the small format samples."""
    from docx import Document
    from docx.shared import Inches
    from fixtures.generate import TEXT, make_pdf, picture
    from PIL import Image
    from pptx import Presentation
    from pptx.util import Inches as PptxInches
    import io
    import openpyxl

    photo = io.BytesIO()
    noise = Image.effect_noise((1600, 1200), 40)
    Image.merge("RGB", (noise, noise.rotate(180), noise.point(lambda v: 255 - v))).save(photo, "JPEG", quality=70)
    small_photo = io.BytesIO()
    picture((800, 600)).save(small_photo, "JPEG", quality=80)

    document = Document()
    for section in range(30):
        document.add_heading(f"Section {section + 1}", level=1)
        for _ in range(6):
            document.add_paragraph(TEXT * 8)
        if section % 3 == 0:
            document.add_picture(io.BytesIO(small_photo.getvalue()), width=Inches(5))
        document.add_page_break()
    docx = io.BytesIO()
    document.save(docx)

    workbook = openpyxl.Workbook()
    for sheet_index in range(3):
        sheet = workbook.create_sheet(f"Sheet {sheet_index}")
        for row in range(1500):
            sheet.append([row, row * 1.5, f"Item {row}", TEXT[:30], row % 7, "2026-11-04", row * 0.1, "Note"])
    xlsx = io.BytesIO()
    workbook.save(xlsx)

    presentation = Presentation()
    for index in range(20):
        slide = presentation.slides.add_slide(presentation.slide_layouts[1])
        slide.shapes.title.text = f"Slide {index + 1}"
        slide.placeholders[1].text = TEXT
        slide.shapes.add_picture(io.BytesIO(small_photo.getvalue()), PptxInches(1), PptxInches(3.5), height=PptxInches(3))
    pptx = io.BytesIO()
    presentation.save(pptx)

    html = "<html><body>" + "".join(f"<h2>Heading {i}</h2><p>{TEXT * 10}</p><table border=1><tr><td>a</td><td>b</td></tr></table>" for i in range(150)) + "</body></html>"

    return {
        "DOCX, 30 sections with images": ("report.docx", docx.getvalue()),
        "XLSX, 4,500 rows": ("data.xlsx", xlsx.getvalue()),
        "PPTX, 20 slides with images": ("deck.pptx", pptx.getvalue()),
        "PDF, 100 pages": ("long.pdf", make_pdf(tmp_path / "long.pdf", pages=100).read_bytes()),
        "JPEG, 1600x1200 photo": ("photo.jpg", photo.getvalue()),
        "HTML, long article": ("article.html", html.encode()),
    }


def test_latency_realistic_documents(api, tmp_path):
    rows = []
    for label, (name, data) in _realistic_documents(tmp_path).items():
        convert(api, name, data, validate="false")
        timings_plain, timings_validated = [], []
        for _ in range(3):
            started = time.monotonic()
            response = convert(api, name, data, validate="false")
            timings_plain.append((time.monotonic() - started) * 1000)
            assert response.status_code == 200, f"{label}: {response.text[:200]}"
        started = time.monotonic()
        response = convert(api, name, data)
        timings_validated.append((time.monotonic() - started) * 1000)
        assert response.status_code == 200
        assert response.headers["x-pdfa-validated"] == "true", label
        rows.append(
            {
                "document": label,
                "input_kb": round(len(data) / 1024),
                "output_kb": round(len(response.content) / 1024),
                "pages": int(response.headers["x-page-count"]),
                "median_ms_no_validation": round(statistics.median(timings_plain)),
                "ms_validated": round(timings_validated[0]),
            }
        )
    _report("latency_realistic", {"rows": rows})
    print("\nrealistic documents:")
    for row in rows:
        print(f"REAL {row['document']:<32} {row['input_kb']:>6} KB -> {row['output_kb']:>6} KB {row['pages']:>4} pp {row['median_ms_no_validation']:>6} ms {row['ms_validated']:>6} ms validated")


def test_latency_per_format(api, samples):
    """Sequential, so these are single-request latencies on warm engines."""
    rows = []
    for ext, path in sorted(samples.items()):
        data = path.read_bytes()
        convert(api, f"warm.{ext}", data, validate="false")
        with_validation, without_validation = [], []
        for _ in range(FORMAT_REPEATS):
            started = time.monotonic()
            response = convert(api, f"bench.{ext}", data, validate="false")
            without_validation.append((time.monotonic() - started) * 1000)
            assert response.status_code == 200, f"{ext}: {response.text[:200]}"
        for _ in range(2):
            started = time.monotonic()
            response = convert(api, f"bench.{ext}", data)
            with_validation.append((time.monotonic() - started) * 1000)
            assert response.status_code == 200
        rows.append(
            {
                "format": ext,
                "input_kb": round(len(data) / 1024, 1),
                "output_kb": round(len(response.content) / 1024, 1),
                "median_ms_no_validation": round(statistics.median(without_validation)),
                "median_ms_validated": round(statistics.median(with_validation)),
            }
        )
    _report("latency_per_format", {"rows": rows})
    print("\nformat  input KB  output KB  no validation  validated")
    for row in rows:
        print(f"{row['format']:<7} {row['input_kb']:>8} {row['output_kb']:>10} {row['median_ms_no_validation']:>11} ms {row['median_ms_validated']:>7} ms")
