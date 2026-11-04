"""HTML to PDF with one long-lived headless Chromium and a new context per request.

Rendering can never reach the network or the filesystem. The page is loaded with
`set_content` (origin about:blank), every request except inline data is aborted, DNS
resolution is disabled, and JavaScript is off unless HTML_ALLOW_INLINE_JS is set.
"""

from __future__ import annotations

import asyncio
import base64
import html as html_lib
import logging
import re
from pathlib import Path

import markdown
from playwright.async_api import Browser, Error as PlaywrightError, Playwright, TimeoutError as PlaywrightTimeout, async_playwright

from app.config import Settings
from app.context import Deadline
from app.errors import ConversionFailed
from app.util import decode_text

log = logging.getLogger(__name__)

_BROWSER_ARGS = [
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--no-first-run",
    "--disable-extensions",
    "--disable-default-apps",
    # No background traffic of any kind: updates, safe browsing, metrics, sync, crash reports.
    "--disable-background-networking",
    "--disable-component-update",
    "--safebrowsing-disable-auto-update",
    "--disable-client-side-phishing-detection",
    "--disable-features=SafeBrowsing,OptimizationHints,MediaRouter,Translate,InterestFeedContentSuggestions",
    "--disable-sync",
    "--metrics-recording-only",
    "--no-pings",
    "--disable-domain-reliability",
    "--disable-breakpad",
    "--no-service-autorun",
    "--host-resolver-rules=MAP * ~NOTFOUND",
]

_MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "sane_lists", "toc", "attr_list", "footnotes"]

MARKDOWN_STYLE = """
body { font-family: "Liberation Sans", "Noto Sans", "Noto Sans CJK SC", sans-serif; font-size: 11pt; line-height: 1.45; color: #1a1a1a; }
h1, h2, h3, h4 { line-height: 1.2; margin: 1.1em 0 0.5em; }
pre, code { font-family: "Liberation Mono", "DejaVu Sans Mono", monospace; font-size: 9.5pt; }
pre { background: #f4f4f4; padding: 8px 10px; white-space: pre-wrap; word-break: break-word; }
table { border-collapse: collapse; margin: 0.8em 0; }
th, td { border: 1px solid #999; padding: 4px 8px; text-align: left; }
blockquote { margin: 0.8em 0; padding-left: 12px; border-left: 3px solid #aaa; color: #444; }
img { max-width: 100%; }
"""


# 1x1 opaque light-grey GIF. Any alpha here would make Ghostscript rasterise the page.
_PLACEHOLDER_IMAGE = "data:image/gif;base64," + base64.b64encode(
    bytes.fromhex("474946383761010001008000 00eeeeee000000 2c00000000010001000002024401003b".replace(" ", ""))
).decode("ascii")

_ATTRIBUTES = r"""(?:[^>"']|"[^"]*"|'[^']*')*"""
_IMG_TAG = re.compile(rf"<img\b{_ATTRIBUTES}>", re.IGNORECASE)
_SOURCE_TAG = re.compile(rf"<source\b{_ATTRIBUTES}>", re.IGNORECASE)
_MEDIA_TAG = re.compile(r"<(video|audio)\b", re.IGNORECASE)
_META_TAG = re.compile(rf"<meta\b{_ATTRIBUTES}>", re.IGNORECASE)
_REFRESH_ATTRIBUTE = re.compile(r"""http-equiv\s*=\s*["']?\s*refresh""", re.IGNORECASE)
_SRC_ATTRIBUTE = re.compile(r"""\bsrc\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE)
_SRCSET_ATTRIBUTE = re.compile(r"""\bsrcset\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)""", re.IGNORECASE)


def _is_inline_image(value: str) -> bool:
    return value.strip("\"' \t\r\n").lower().startswith("data:image/")


def _rewrite_img(match: re.Match) -> str:
    tag = _SRCSET_ATTRIBUTE.sub("", match.group(0))
    source = _SRC_ATTRIBUTE.search(tag)
    if source is None:
        return tag.replace("<img", f'<img src="{_PLACEHOLDER_IMAGE}"', 1) if tag[:4] == "<img" else tag
    if _is_inline_image(source.group(1)):
        return tag
    return tag[: source.start()] + f'src="{_PLACEHOLDER_IMAGE}"' + tag[source.end():]


def neutralise_unloadable_content(html: str) -> str:
    """Rewrites what cannot load, since it would otherwise damage the rendered page.

    Remote images always fail here, and Chromium draws a failed image as an icon with an
    alpha channel. That transparency makes Ghostscript rasterise the whole page, so one
    tracking pixel would cost an email all its searchable text. A meta refresh would
    navigate away to a blocked address and leave a blank page.
    """
    html = _META_TAG.sub(lambda m: "" if _REFRESH_ATTRIBUTE.search(m.group(0)) else m.group(0), html)
    # PDF/A cannot hold media, and player controls are drawn with transparency. The browser
    # uses the first of any duplicate attributes, so this overrides the tag's own style.
    html = _MEDIA_TAG.sub(r'<\1 style="display:none!important" ', html)
    html = _SOURCE_TAG.sub(lambda m: m.group(0) if _is_inline_image(m.group(0).split("srcset", 1)[-1].split("=", 1)[-1]) else "", html)
    return _IMG_TAG.sub(_rewrite_img, html)


def markdown_to_html(source: str) -> str:
    body = markdown.markdown(source, extensions=_MARKDOWN_EXTENSIONS, output_format="html")
    match = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.DOTALL | re.IGNORECASE)
    title = html_lib.escape(html_lib.unescape(re.sub(r"<[^>]+>", "", match.group(1))).strip()) if match else ""
    return (
        f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title>'
        f"<style>{MARKDOWN_STYLE}</style></head><body>{body}</body></html>"
    )


def read_html(path: Path) -> str:
    return decode_html_bytes(path.read_bytes())


def decode_html_bytes(data: bytes) -> str:
    declared = re.search(rb"""<meta[^>]+charset=["']?\s*([a-zA-Z0-9_\-]+)""", data[:4096], re.IGNORECASE)
    if declared and not data.startswith((b"\xef\xbb\xbf", b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode(declared.group(1).decode("ascii"), errors="replace")
        except LookupError:
            pass
    return decode_text(data)


class Chromium:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._semaphore = asyncio.Semaphore(settings.chromium_concurrency)
        self._launch_lock = asyncio.Lock()

    async def start(self) -> None:
        self._playwright = await async_playwright().start()
        await self._ensure_browser()

    async def stop(self) -> None:
        try:
            if self._browser is not None:
                await self._browser.close()
        except PlaywrightError:
            pass
        if self._playwright is not None:
            await self._playwright.stop()

    async def _ensure_browser(self) -> Browser:
        async with self._launch_lock:
            if self._browser is None or not self._browser.is_connected():
                if self._browser is not None:
                    log.warning("Chromium is gone, launching a new browser")
                # Chromium's sandbox needs user namespaces, which Docker's default seccomp
                # profile blocks. Disabling network, JS and file access compensates.
                self._browser = await self._playwright.chromium.launch(
                    executable_path=str(self._settings.chromium_executable),
                    args=_BROWSER_ARGS,
                    chromium_sandbox=False,
                    timeout=60_000,
                )
            return self._browser

    def is_ready(self) -> bool:
        return self._browser is not None and self._browser.is_connected()

    async def _kill_browser(self) -> None:
        browser, self._browser = self._browser, None
        if browser is not None:
            try:
                async with asyncio.timeout(5):
                    await browser.close()
            except (TimeoutError, PlaywrightError):
                log.warning("Chromium did not close cleanly")

    async def render(self, html: str, dst: Path, deadline: Deadline, *, allow_js: bool | None = None) -> None:
        """Renders HTML to a PDF file."""
        js_enabled = self._settings.html_allow_inline_js if allow_js is None else allow_js
        for attempt in (1, 2):
            try:
                async with asyncio.timeout(deadline.remaining()):
                    async with self._semaphore:
                        await self._render(html, dst, deadline, js_enabled)
                return
            except (TimeoutError, PlaywrightTimeout):
                raise deadline.timeout_error() from None
            except PlaywrightError as exc:
                # If the browser died, this request may be an innocent bystander, so it gets
                # one retry on a new browser. Otherwise the document itself is the problem.
                if attempt == 1 and not self.is_ready():
                    log.warning("Chromium died during a render, retrying")
                    continue
                log.warning("Chromium failed", extra={"fields": {"error": type(exc).__name__}})
                raise ConversionFailed("The browser could not render the document") from exc

    async def _close_context(self, context) -> None:
        """Closing a context normally ends its renderer, even one stuck in an endless script.

        The browser, and every other render in it, is only sacrificed if that fails.
        """
        try:
            async with asyncio.timeout(5):
                await context.close()
        except (TimeoutError, PlaywrightError):
            log.warning("Chromium context did not close, recycling the browser")
            await self._kill_browser()

    async def _render(self, html: str, dst: Path, deadline: Deadline, js_enabled: bool) -> None:
        browser = await self._ensure_browser()
        context = await browser.new_context(
            java_script_enabled=js_enabled,
            offline=True,
            accept_downloads=False,
            service_workers="block",
            bypass_csp=False,
        )
        try:
            async def guard(route) -> None:
                if route.request.url.startswith(("data:", "about:", "blob:")):
                    await route.continue_()
                else:
                    await route.abort("blockedbyclient")

            await context.route("**/*", guard)
            page = await context.new_page()
            timeout_ms = deadline.remaining() * 1000
            page.set_default_timeout(timeout_ms)
            await page.set_content(neutralise_unloadable_content(html), wait_until="load", timeout=timeout_ms)
            await page.emulate_media(media="print")
            await page.pdf(
                path=str(dst),
                format=self._settings.fallback_page_name,
                print_background=True,
                prefer_css_page_size=True,
                margin={"top": "15mm", "bottom": "15mm", "left": "15mm", "right": "15mm"},
            )
        finally:
            await asyncio.shield(self._close_context(context))
