# PDF/A-1b conversion service

Converts 42 file formats to **PDF/A-1b** over HTTP. You send a file and get a PDF back. The service stores nothing and has no object storage client: saving the result, to S3 or anywhere else, is the caller's job. It is built for synchronous callers: engines stay warm, so a typical document converts in tens to hundreds of milliseconds.

Everything runs in Docker. Engines, fonts, the ICC profile, the browser and the validator are baked into the image, and nothing is downloaded at runtime. It runs with no network access beyond receiving requests, and makes no outbound connections.

- [Quick start](#quick-start)
- [API](#api)
- [Configuration](#configuration)
- [Supported formats](#supported-formats)
- [How conversion works](#how-conversion-works)
- [Known limitations](#known-limitations)
- [Measured performance](#measured-performance)
- [Operations](#operations)
- [Offline and government deployment](#offline-and-government-deployment)
- [Security](#security)
- [Supply chain](#supply-chain)
- [Testing](#testing)
- [Licences](#licences)

## Quick start

Run the service:

```bash
make up
```

The service is then at `http://localhost:8080`, in one container, `pdfa-converter-api-1`, running the production image. Stop it with `make down`.

Convert a file:

```bash
curl -f -H "X-API-Key: dev-api-key-change-me" -F file=@report.docx http://localhost:8080/v1/convert -o report.pdf
```

Build and run the full test suite inside Docker:

```bash
docker compose -f docker-compose.test.yml run --rm --build converter pytest
```

Build the production image, which has no test tooling:

```bash
docker build -t pdfa-converter .
```

`API_KEY` is required in production, and the service refuses to start without it. Compose supplies a development key, which `.env` can override (see `.env.example`). Every other setting has a default: to change one locally, add it under `environment` in `docker-compose.yml`. `make help` lists the common tasks.

## API

Endpoints under `/v1` need the `X-API-Key` header. Health endpoints do not.

### `POST /v1/convert`

Multipart upload.

| Field | Required | Description |
|---|---|---|
| `file` | yes | The file, up to 5 MB |
| `validate` | no | `true` or `false`. Overrides `VALIDATE_DEFAULT` |

The response body is the PDF:

```bash
curl -f -D - -H "X-API-Key: $API_KEY" -F file=@report.docx -F validate=true http://localhost:8080/v1/convert -o report.pdf
```

**When calling this from your application:**

- **Check `X-PdfA-Validated` before keeping the PDF.** With `STRICT_VALIDATION` off, a PDF that fails validation still comes back as a 200, marked `false`.
- **Set your response timeout above `CONVERSION_TIMEOUT_SECONDS`,** so the service's own 504 arrives first.
- **Retry only on 5xx, never on 4xx.** A 504 is usually not worth retrying, because a document that used the whole time budget will probably do it again.
- **Stream the response to disk** rather than holding it in memory. Output size has no limit.

### Response headers

Every successful conversion returns:

| Header | Value |
|---|---|
| `X-Source-Format` | Format detected from the content, such as `docx` |
| `X-Conversion-Ms` | Conversion time |
| `X-PdfA-Validated` | `true`, `false`, or `skipped` |
| `X-Page-Count` | Pages in the output |
| `X-Request-Id` | The caller's ID if valid, otherwise a generated one |
| `Content-Disposition` | The original filename with a `.pdf` extension, so `report.docx` gives `report.pdf`. `filename*` holds the exact name, and `filename` is a plain ASCII fallback |

To save under that name with curl, use `-OJ` instead of `-o`. curl reads the ASCII fallback, so other alphabets become underscores.

These appear only when they apply:

| Header | Meaning |
|---|---|
| `X-Flattened-Pages` | Pages rendered to an image because they used transparency, so their text is no longer searchable. See [limitations](#known-limitations) |
| `X-Attachments-Skipped` | Email attachments that could not be converted. Each is also named on the email's first page |

### `GET /v1/formats`

```bash
curl -H "X-API-Key: $API_KEY" http://localhost:8080/v1/formats
```

Returns supported extensions grouped by family.

### `GET /health/live` and `GET /health/ready`

```bash
curl http://localhost:8080/health/ready
```

`live` means the process is up. `ready` returns 200 only if a LibreOffice instance is alive, Ghostscript runs and Chromium is connected. Otherwise it returns 503. Either way, the JSON body shows each check. The result is cached for `READY_CACHE_SECONDS`.

### Errors

Every error is JSON:

```json
{ "error": "ENCRYPTED_FILE", "message": "The PDF is encrypted", "requestId": "6b29117a-31d4-4690-8292-b14ea9776e88" }
```

| Status | Code | Meaning |
|---|---|---|
| 400 | `BAD_REQUEST` | Missing or invalid field |
| 401 | `UNAUTHORIZED` | Missing or wrong API key |
| 404, 405 | `NOT_FOUND`, `METHOD_NOT_ALLOWED` | No such route or method |
| 413 | `FILE_TOO_LARGE` | Input over the limit. Output size is never limited |
| 415 | `UNSUPPORTED_FORMAT` | Not a supported format |
| 422 | `ENCRYPTED_FILE` | Password-protected or encrypted PDF or Office file |
| 422 | `CORRUPT_FILE` | The file is damaged, empty, or not what its name says |
| 422 | `TOO_MANY_PAGES` | Over `MAX_PAGES` |
| 422 | `PDFA_VALIDATION_FAILED` | Output failed validation, with `STRICT_VALIDATION` on |
| 500 | `CONVERSION_FAILED` | An engine failed on an input that was not identifiably bad |
| 500 | `INTERNAL_ERROR` | Unexpected error. Search the logs for the `requestId` |
| 504 | `CONVERSION_TIMEOUT` | Over `CONVERSION_TIMEOUT_SECONDS` |

## Configuration

All settings are environment variables. Blank values count as unset.

### Core

| Variable | Default | Description |
|---|---|---|
| `API_KEY` | none, **required** | Value callers send in `X-API-Key` |
| `MAX_UPLOAD_BYTES` | `5242880` | Input limit. Does not apply to output |
| `LO_POOL_SIZE` | CPU count | LibreOffice instances. Respects container CPU limits |
| `GS_CONCURRENCY` | CPU count | Concurrent Ghostscript runs, and separately, concurrent decoder processes |
| `CONVERSION_TIMEOUT_SECONDS` | `60` | Time limit for one conversion across all its engine calls, including queueing |
| `MAX_PAGES` | `500` | Page limit |
| `VALIDATE_DEFAULT` | `true` | Validate unless the request says otherwise |
| `STRICT_VALIDATION` | `false` | Return 422 instead of the PDF when validation fails |
| `DEFAULT_PAGE_SIZE` | `native` | `native`, `A3`, `A4`, `A5`, `LETTER` or `LEGAL` (see below) |
| `ENABLE_MSG` | `true` | Convert Outlook `.msg` files, which uses the GPL-licensed extract-msg |
| `LOG_LEVEL` | `INFO` | Logs are one JSON object per line, on stdout. They never contain filenames or file contents |

`DEFAULT_PAGE_SIZE` controls layout for sources without a fixed page:

- **`native`:** images use their pixel size and DPI (96 if unknown), SVGs their stated size. HTML, Markdown, email, text and CSV use A4.
- **A named size:** images are placed on that page, oriented to match and shrunk only if too big. HTML, Markdown, email, text and CSV use that size. Documents with their own page setup, such as DOCX and PDF, always keep it.

### Tuning

| Variable | Default | Description |
|---|---|---|
| `LO_MAX_CONVERSIONS` | `200` | Recycle a LibreOffice instance after this many conversions |
| `LO_HEALTH_INTERVAL_SECONDS` | `15` | How often idle instances are checked |
| `LO_BASE_PORT` | `2100` | First internal port for the pool. Uses two per instance, on localhost |
| `READY_CACHE_SECONDS` | `5` | How long a `/health/ready` result is reused |
| `CHROMIUM_CONCURRENCY` | CPU count | Concurrent HTML renders |
| `VERAPDF_CONCURRENCY` | CPU count | Concurrent validations |
| `MAX_EMAIL_DEPTH` | `3` | Levels of emails nested inside emails |
| `MAX_EMAIL_ATTACHMENTS` | `20` | Attachments converted per email |
| `MAX_IMAGE_PIXELS` | `200000000` | Larger images are rejected before decoding |
| `MAX_UNCOMPRESSED_BYTES` | `1073741824` | Larger expansions of Office files are rejected (zip bombs) |
| `ENGINE_MEMORY_LIMIT_MB` | `2048` | Address-space limit for Ghostscript and decoders. `0` disables it |
| `HTML_ALLOW_INLINE_JS` | `false` | Run inline scripts in HTML uploads. Network access stays blocked, and email never runs scripts |
| `CHROMIUM_EXECUTABLE` | `/usr/bin/chromium` | The browser Playwright drives |
| `WORK_DIR` | `/tmp/work` | Per-request temp directories |
| `LO_RUN_DIR` | `/tmp/lo` | LibreOffice profiles and logs |

## Supported formats

| Family | Extensions | Stage 1 engine | Stage 2 |
|---|---|---|---|
| Word processing | doc, docx, dot, dotx, docm, odt, rtf, txt, wpd, wps | LibreOffice | Native export |
| Spreadsheets | xls, xlsx, xlsm, ods, csv | LibreOffice, fit to page width | Native export |
| Presentations | ppt, pptx, pps, ppsx, odp | LibreOffice | Native export |
| Diagrams | vsd, vsdx, odg | LibreOffice Draw | Native export |
| Raster images | jpg, jpeg, png, gif, bmp, tif, tiff, webp | Pillow + img2pdf | img2pdf's PDF/A mode |
| Modern images | heic, heif (decoder-only libheif + libde265); avif (Pillow) | Then as above | img2pdf's PDF/A mode |
| Vector | svg | CairoSVG | Ghostscript |
| Vector | eps | Ghostscript | Same pass |
| Web | html, htm, md | Chromium | Ghostscript |
| Email | eml, msg | Rendered with Chromium; attachments converted recursively; merged with pikepdf | Ghostscript |
| PDF | pdf | Passes through | Ghostscript |

Anything else gets a 415. The type comes from the file's content, using libmagic plus OOXML, ODF and OLE container inspection. The extension only separates what content cannot, such as doc from dot, ppt from pps, and plain-text formats. So a PNG named `.jpg` converts as a PNG, and an executable named `.pdf` is refused.

## How conversion works

**Warm engines.** A pool of unoserver instances, one Chromium browser (Debian's package, driven by Playwright) and a preloaded forkserver all start before the service accepts requests. The pool lives inside the app rather than the entrypoint because the app has to queue, health-check and kill instances.

**Fidelity by format:**

- **JPEG:** embedded byte for byte, using a page rotation for EXIF orientation. ICC profiles are kept, so the colours of an Adobe RGB photo survive.
- **PNG and TIFF:** embedded losslessly. Fax-compressed TIFFs pass through as they are.
- **Transparency:** flattened onto white, losslessly.
- **GIF, BMP, WebP, HEIC, AVIF:** the first frame is decoded and stored as lossless PNG.
- **DPI:** preserved, so the physical page size is right.
- **Office:** images are not downsampled or recompressed. Metric-compatible fonts stop layouts from shifting (Carlito for Calibri, Caladea for Cambria, Liberation for Arial, Times and Courier).
- **Spreadsheets:** each sheet fits one page wide, unless the author set their own scaling, which is kept. Their accessibility tags are removed: LibreOffice writes several uncompressible objects per cell, which turned a 4,500-row sheet into 9 MB (362 KB without them).
- **Metadata:** the source filename goes into XMP `dc:source`. The title goes into `dc:title` when there is one (document title, email subject, HTML title, first Markdown heading).

**Three departures from a simple "everything through Ghostscript" design,** each based on measured behaviour:

1. **Raster images skip Ghostscript when possible.** Ghostscript decodes and re-encodes any JPEG with an ICC profile, which covers most camera photos: one sample grew from 319 KB to 1.39 MB, with its colours converted. img2pdf writes valid PDF/A-1b directly with the original bytes. Only images PDF/A-1 cannot hold go to Ghostscript: CMYK, ICC v4 profiles, and 16-bit depth.
2. **Office documents with CJK text do get a Ghostscript pass.** LibreOffice's export is used directly otherwise, but it embeds OpenType/CFF fonts such as Noto CJK without the `/CharSet` entry PDF/A-1 requires, so its output fails validation. The service detects that exact condition and repairs it, and the text stays searchable.
3. **EPS is converted in a single Ghostscript pass,** since Ghostscript is its stage 1 engine anyway.

**Features removed after Ghostscript.** `PDFACompatibilityPolicy=1` does not remove everything PDF/A-1 forbids (embedded files survive it, for example), so a final step strips attachments, JavaScript, forbidden actions and annotations, layers, and XFA.

## Known limitations

**Transparency in PDF, SVG, HTML and email input rasterises the whole page.** PDF/A-1 forbids transparency and Ghostscript can only flatten per page, so a page using `rgba()`, `opacity`, `box-shadow`, or an alpha PNG becomes one 720 dpi image. It looks right, but **its text is no longer searchable or selectable**. The `X-Flattened-Pages` header reports how many pages this affected, so a caller can decide what to do. Pages without transparency keep real text. LibreOffice flattens per object, so Office documents are not affected.

**PDF/A-1 itself removes:**

- Transparency, as above
- Layers: optional content is flattened
- File attachments, including those inside PDF input
- JavaScript and other active content
- 16-bit colour depth, reduced to 8-bit
- CMYK and ICC v4 colour, converted to sRGB. These images must be re-encoded (losslessly), so the file grows

**Formats:**

- Apple Pages, Numbers and Keynote are not supported, and neither are `.ps`, `.dotm`, `.pptm`, `.xltx`, or zip archives.
- Animated GIF and WebP use the first frame only. Multi-image HEIC uses the primary image.
- Macros in Office files are never run. Fields that rely on them keep their last saved values.

**Layout:**

- LibreOffice's pagination can differ from Microsoft Office's, especially with fonts not in the image. [Mount the real fonts](#custom-fonts) when exact layout matters.
- Tables of contents keep their saved page numbers, which may not match if pagination shifts.
- Very wide spreadsheets shrink to fit one page wide and can become hard to read. Print areas set by the author are respected.
- Output is declared PDF/A-1b, not 1a. Word and presentation documents keep LibreOffice's tags, which helps accessibility but is not a 1a claim. Spreadsheets, and anything that goes through Ghostscript, have none.

**HTML and email:**

- Remote images, stylesheets and fonts never load. Remote images appear as light-grey placeholders at their stated size. This also stops tracking pixels.
- `<video>` and `<audio>` are hidden.
- JavaScript is off for HTML uploads by default, so pages that build their content with scripts render empty. `HTML_ALLOW_INLINE_JS=true` runs inline scripts, and remote scripts stay blocked.
- Winmail.dat (TNEF), encrypted attachments and unsupported attachment types are listed on the first page as not converted, rather than failing the email.
- S/MIME-encrypted message bodies cannot be read.

**Validation** starts a JVM per call, which adds about 0.4–0.5 s, and more for files with many objects. Turn it off per request when latency matters more.

## Measured performance

Measured on Apple silicon (arm64) with Docker Desktop, in the hardened test container limited to 4 CPUs and 6 GB, with a LibreOffice pool of 4 and warm engines. Run `make load` to reproduce these on your own hardware.

**Small sample files, one request at a time (median, per format family):**

| Family | No validation | With validation |
|---|---|---|
| Raster images | 23–35 ms | 422–448 ms |
| HEIC, HEIF, AVIF | 40–55 ms | 433–452 ms |
| EPS | 49 ms | 450 ms |
| PDF | 66 ms | 480 ms |
| SVG | 67 ms | 477 ms |
| Diagrams | 44–46 ms | 459–471 ms |
| Word processing | 35–156 ms | 448–606 ms |
| Spreadsheets | 47–150 ms | 454–578 ms |
| Presentations | 44–142 ms | 464–566 ms |
| HTML, Markdown | 229–250 ms | 662–679 ms |
| Email | 236–336 ms | 684–800 ms |

**Larger documents:**

| Document | Input | Output | Pages | No validation | With validation |
|---|---|---|---|---|---|
| JPEG, 1600x1200 photo | 712 KB | 716 KB | 1 | 40 ms | 438 ms |
| DOCX, 30 sections with images | 47 KB | 130 KB | 40 | 119 ms | 1.2 s |
| PPTX, 20 slides with images | 57 KB | 81 KB | 20 | 216 ms | 670 ms |
| PDF, 100 pages | 50 KB | 53 KB | 100 | 146 ms | 607 ms |
| HTML, long article | 75 KB | 58 KB | 30 | 398 ms | 972 ms |
| XLSX, 4,500 rows | 172 KB | 362 KB | 96 | 1.1 s | 4.7 s |

Validation is the slowest step, and its cost grows with content: the spreadsheet spends about 3.6 s in veraPDF. Consider `validate=false` for large spreadsheets on latency-sensitive paths.

**20 concurrent DOCX conversions, with validation:** p50 3.4 s, p95 5.0 s, 3.9 conversions per second. Validation is what limits throughput here: 20 JVMs share 4 CPUs.

**Memory:** about 510 MB idle with a pool of 4, and about 920 MB with 12 instances, which is what `make up` starts where Docker has 12 CPUs. The full test suite, which also runs several extra service instances and tmpfs files in the same container, peaked at 3.8 GB, so treat that as an upper bound for this pool size rather than a production figure.

**Image size:** about 0.8 GB compressed and 2.0 GB on disk. Docker Desktop displays it as 2.9 GB. The largest parts are Chromium (379 MB), Python packages (252 MB), LibreOffice (258 MB), the JRE (195 MB) and fonts (166 MB).

## Operations

### Sizing

Each LibreOffice instance converts one document at a time, so `LO_POOL_SIZE` sets Office throughput. See [measured performance](#measured-performance) for real figures. Run one worker per container and scale with more containers: all heavy work already happens in child processes.

### Failure handling

- A hung or crashed LibreOffice instance is killed with its whole process group and replaced with a fresh profile in about 5 seconds, while other instances keep serving. A request that hit a dead instance is retried once on another one.
- Idle instances are health-checked every `LO_HEALTH_INTERVAL_SECONDS`, and recycled after `LO_MAX_CONVERSIONS`.
- A crashed Chromium is relaunched on the next request, and renders it took down are retried once.
- Parsers and decoders (Pillow, libheif, cairo, qpdf, the email parsers) each run in a killable child process, so a hang or crash in one cannot affect the service.
- The conversion timeout covers the whole request, and when it fires, the running engine is killed. Waiting in a queue counts, because the caller is waiting too. Under sustained overload you will see 504s rather than unbounded queues.
- Temp directories are removed after success, errors, timeouts and client disconnects. Anything left by a crash is removed at the next start.

### Custom fonts

Mount fonts at `/fonts/custom`. They are indexed at startup and available to every engine.

```yaml
volumes:
  - ./fonts:/fonts/custom:ro
```

### Container requirements

- Runs as non-root (UID 10001). This is set in the image.
- `/tmp` must be writable.
- Listens on port 8080.
- Multi-arch: tested on `linux/arm64`, and on `linux/amd64` under emulation.

### Running in production

`docker-compose.yml` is deliberately minimal and is for local use: it sets only the port and the API key. The image needs nothing else to run, and no other services.

The settings below live outside the image, so your platform has to apply them. Because this service opens untrusted files, apply all of them in production. This is the setup the test suite runs and verifies, in `docker-compose.test.yml`:

```bash
docker run -d --name pdfa-converter -p 8080:8080 -e API_KEY="$API_KEY" --read-only --cap-drop ALL --security-opt no-new-privileges --cpus 4 --memory 6g --pids-limit 2048 --tmpfs /tmp:size=2g,mode=1777,uid=10001,gid=10001,exec --tmpfs /tmp/work:size=1g,mode=0700,uid=10001,gid=10001 --tmpfs /tmp/lo:size=512m,mode=0700,uid=10001,gid=10001 pdfa-converter:runtime
```

- **Network:** allow inbound traffic only from your applications, and block all outbound traffic. The service makes no outbound connections.
- **Pool size:** `LO_POOL_SIZE` defaults to the container's CPU limit. With no limit it uses every CPU on the host, which also means more memory, so set a limit.
- **Temporary storage:** the tmpfs mounts keep documents off disk. On Kubernetes, use `emptyDir` with `medium: Memory`, and count it toward the pod's memory limit.
- **Health checks:** Kubernetes and ECS ignore the image's `HEALTHCHECK`, so configure them yourself. Use `/health/live` for restarts and `/health/ready` for traffic, and allow about 90 seconds for startup.

### Versions

| Component | Version | Source |
|---|---|---|
| Python | 3.12.16 | Official image, pinned by digest |
| LibreOffice | Series `26.8.*`: 26.8.2.2 on arm64 and 26.8.1.1 on amd64 at the time of writing | Debian trixie-backports (trixie itself has 25.2) |
| Chromium | 156.0.8078.79 | Debian trixie-security |
| Ghostscript | 10.05.1 | Debian trixie with security patches. Upstream has newer releases |
| libheif, libde265 | 1.23.6, 1.0.15 | Debian trixie-security. pillow-heif is compiled against these |
| veraPDF | 1.30.3 | Official installer, SHA-256 checked |
| OpenJDK | 21.0.13 | Debian trixie-security |
| Playwright | 1.64.1 | PyPI. Its browser download is unused |
| unoserver | 3.7 | PyPI |

`/srv/versions.txt` in the image records the exact engine versions.

**LibreOffice is the one package pinned to a series, not an exact version.** It comes from Debian backports, where only the newest upload is available and each architecture receives it at a different time. During development, an exact pin stopped building within the hour, when a new upload had reached arm64 but not amd64. So two builds can contain different patch releases: **build once and promote the image by digest** rather than rebuilding per environment.

This matters for security too. Stock LibreOffice 26.8.1 fetches a URL and embeds a local file from a crafted DOCX, and 26.8.2 does neither with the same file. The service's own hardening blocks this on both, and is tested on both.

## Offline and government deployment

The container makes no outbound connections, so it needs no internet access and no route to anything else on your network. It only has to accept requests from your application.

**Proof.** `docker compose -f docker-compose.test.yml run --rm --build converter pytest` runs the full suite on an `internal: true` network, with nothing else attached. Tests in that run confirm that public addresses and DNS are unreachable, and that documents referencing remote images (HTML, DOCX, email) convert with no outbound request. Requests are watched by a listener on the container's own network address.

**Local access.** `make up` runs the service on a normal Docker network with none of the hardening, so the container has a route out at the network level. The engines still block outbound requests themselves. For production, see [Running in production](#running-in-production).

**Building from internal mirrors.** Every source is a build argument:

```bash
docker build \
  --build-arg PYTHON_IMAGE=registry.internal/python:3.12.16-slim-trixie \
  --build-arg APT_MIRROR=https://apt.internal \
  --build-arg PIP_INDEX_URL=https://pypi.internal/simple \
  --build-arg PIP_TRUSTED_HOST=pypi.internal \
  --build-arg VERAPDF_URL=https://files.internal/verapdf-greenfield-1.30.3-installer.zip \
  -t pdfa-converter .
```

- `APT_MIRROR` replaces `http://deb.debian.org`, so it must serve both `/debian` and `/debian-security`, including `trixie-backports`.
- All system packages come from that one mirror, including Chromium: Playwright's browser download is not used.
- Python packages stay hash-checked, and the veraPDF installer stays SHA-256 checked, whatever the source.
- veraPDF is not packaged by Debian, so `VERAPDF_URL` needs a copy on an internal file server.

**Blocked at runtime:**

- **LibreOffice:** update checks are off and linked or remote content is blocked, through `registrymodifications.xcu` in the image.
- **Chromium:** background networking, updates, safe browsing, metrics and sync are disabled at launch. Every request is intercepted and aborted unless it is `data:`, `blob:` or `about:`. Local files are aborted too, which is stricter than necessary, because the service never loads pages from disk.

## Security

- **Authentication:** the API key is compared in constant time and checked before any request body is read.
- **Upload limit:** enforced while bytes arrive, including chunked uploads with no `Content-Length`, so oversized bodies never reach the disk.
- **LibreOffice:** macros never run, enforced both by the profile and per document. External links are blocked: stock LibreOffice fetches the network and embeds local files through a crafted DOCX, and the tests prove this both ways.
- **Ghostscript:** always `-dSAFER`, with read access granted only to the ICC directory.
- **Chromium:** every network request is blocked, and DNS is disabled. Pages load with no origin, so they cannot read local files. JavaScript is off by default. Chromium's own sandbox is off, because it needs user namespaces that Docker's default seccomp profile blocks; these measures compensate.
- **SVG:** external entities and all URLs except `data:` are refused.
- **Resource limits:** page count, pixel count, decompressed size, attachment count, nesting depth, memory, and time.
- **Commands:** always argument lists, never a shell. Engines only ever see generated filenames, so uploaded names cannot inject anything.
- **Internal ports:** the LibreOffice pool listens on localhost only.
- **Logs:** request ID, detected format, sizes, duration and outcome only. Filenames and file contents are never logged, exception messages are reduced to their type, and engine output is discarded. A test sends a marker through every engine and failure path and checks it never reaches a log.

## Supply chain

All versions are pinned, and the tools run from pinned images. Neither tool needs the Docker socket, because the image is exported to a file first.

```bash
make licenses   # copies THIRD_PARTY_LICENSES.md out of the production image
```

```bash
make sbom       # SPDX and CycloneDX SBOMs with syft, in sbom/
```

```bash
make scan       # trivy, HIGH and CRITICAL with a fix available
```

`TRIVY_EXIT_CODE=1` makes `make scan` fail on findings, for CI. Trivy downloads its vulnerability database, so an offline environment needs a mirrored database.

**Latest scan (Debian 13.7, 4 November 2026):** 0 HIGH or CRITICAL findings with a fix available. Without that filter, there are 115 with no fix published yet (113 HIGH and 2 CRITICAL), all in Debian packages. The 2 CRITICAL are a denial of service in libxml2 (CVE-2026-6653, which matters because libxml2 parses untrusted documents here, though engines run with timeouts and restarts) and a CA distrust update in OpenJDK (CVE-2026-114820, which does not apply, because the JRE only runs veraPDF offline). Review this list when patching.

### Monthly patching

Do this monthly, and immediately for a critical LibreOffice, Chromium, Ghostscript or libheif advisory, since all of them parse untrusted input.

1. Update the Python base image digest in the `Dockerfile`, and any version in its `ARG` lines.
2. Run `make build`. A build error like `Version '...' was not found` names a pin Debian has replaced. Find the new version with `docker run --rm debian:trixie apt-cache policy <package>` and update it. Chromium changes most often.
3. Update `requirements.in` as needed and regenerate the lock files, using the command at the top of that file.
4. Run `make test` and `make test-offline`.
5. Run `make scan`, and review anything new. Run it with `--ignore-unfixed` removed from the Makefile to review unfixed findings too.
6. Run `make sbom licenses`, and keep the results with the release.
7. Promote the tested image by digest.

## Testing

Everything runs inside Docker:

```bash
docker compose -f docker-compose.test.yml run --rm --build converter pytest
```

Every format is converted and checked for a valid PDF, a veraPDF PDF/A-1b pass, and a sensible page count. veraPDF runs directly from the tests, independently of the service's own report. Other tests cover the error paths, engine timeouts and crash recovery, attempted SSRF and file disclosure, network isolation, container hardening, log hygiene, and the licensing constraints.

Run the load test and print the latency tables:

```bash
make load
```

Run the tests with all networking disabled:

```bash
make test-offline
```

Tests that need the isolated network and hardening from `docker-compose.test.yml` are reported as skipped in that run.

### GitLab CI

`.gitlab-ci.yml` runs the same suite on merge requests, branches and tags, in the same hardened container on the same internal-only network. The load test is a separate manual job, because it depends on timing and a busy runner can fail it with nothing wrong.

- **Runner:** needs privileged containers for Docker-in-Docker, plus at least 8 GB of memory. 4 CPUs is best: the CPU limit adapts to smaller runners, but a few tests check that work finishes within a few seconds, so they are more likely to fail on 2 CPUs.
- **Build time:** every pipeline builds the image from scratch unless your runner keeps a Docker cache.
- **No internet access:** set `APT_MIRROR`, `PIP_INDEX_URL` and `PIP_TRUSTED_HOST` as CI/CD variables. The Python base image, the veraPDF installer and the job's Docker images also need internal copies, and those are not covered by these variables.

Fixtures are generated in the tests wherever possible. Two kinds are not:

- No open-source tool can write WordPerfect, Works, Visio or Outlook MSG files, or legacy password-protected Office files, so a few small samples come from Apache Tika's test suite under Apache-2.0. See `tests/fixtures/third_party/NOTICE.txt`.
- The images have no HEVC encoder, so the HEIC samples are pre-made. See `tests/fixtures/static/README.txt`.

## Licences

`THIRD_PARTY_LICENSES.md` lists every Python package, system package and font with its licence. It is generated at build time from pip-licenses and dpkg data, and is included in the image at `/srv/THIRD_PARTY_LICENSES.md`.

This service is deployed as SaaS and the software is never distributed, which is the basis for these choices. Have your legal team confirm them; this is a summary, not legal advice.

| Component | Licence | How it is used |
|---|---|---|
| **Ghostscript** | **AGPL-3.0** | The unmodified Debian package, run only as an external process. It is never patched or linked as a library. All calls are in `app/engines/ghostscript.py`, so it can be swapped for a commercially licensed build or another engine |
| **extract-msg** | **GPL-3.0** | Imported by the app to read `.msg` files. Enabled by default, and `ENABLE_MSG=false` turns it off |
| **veraPDF** | MPL-2.0 | The MPL-2.0 option of its dual GPL-3.0+ / MPL-2.0 licence is chosen |
| LibreOffice | MPL-2.0 | Run as a separate process |
| img2pdf, CairoSVG | LGPL-3.0 | |
| pikepdf | MPL-2.0 | |
| Chromium, Playwright | BSD-3-Clause, Apache-2.0 | |
| FastAPI, Pillow, pillow-heif, and others | Permissive | |

**HEIC is decoder-only.** pillow-heif's published wheel bundles an x265 HEVC encoder, so it is compiled from source against Debian's libheif, with only the libde265 (HEVC) and dav1d (AV1) decoder plugins installed. A build step and a test both fail if any x265 package appears. AVIF is decoded by Pillow's own bundled library, which pillow-heif no longer handles.

**Fonts.** Microsoft core fonts are not installed. Metric-compatible alternatives are used instead, and a build step fails if they appear.

HEVC decoding through libde265 may be subject to patent licensing in some countries if HEIC support is used commercially.
