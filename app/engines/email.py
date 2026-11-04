"""Parses EML and MSG into a neutral form, and renders the email's cover document.

The parsing runs in an isolated process. The pipeline then renders the HTML in Chromium,
converts each attachment recursively, and merges everything.
"""

from __future__ import annotations

import base64
import html
import re
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path

import extract_msg
import olefile

from app.errors import CorruptFile
from app.util import decode_text, safe_filename

_MESSAGE_STYLE = (
    'font-family:"Liberation Sans","Noto Sans","Noto Sans CJK SC",sans-serif;font-size:10.5pt;line-height:1.4'
)


def parse_email(src: str, fmt: str, out_dir: str, max_attachments: int) -> dict:
    """Returns headers and body, with attachments extracted to files in `out_dir`."""
    try:
        parsed = _parse_msg(src) if fmt == "msg" else _parse_eml(src)
    except CorruptFile:
        raise
    except (olefile.OleFileError, ValueError, KeyError, IndexError, OSError, TypeError, AttributeError) as exc:
        raise CorruptFile("The email is damaged and cannot be read") from exc

    html_body = parsed["html"]
    inline = parsed.pop("inline")
    if html_body:
        html_body = _embed_inline_images(html_body, inline)

    out = Path(out_dir)
    attachments = []
    skipped = []
    for index, (name, payload) in enumerate(parsed.pop("attachments")):
        clean_name = safe_filename(name, default=f"attachment-{index + 1}")
        if len(attachments) >= max_attachments:
            skipped.append({"name": clean_name, "reason": f"limit of {max_attachments} attachments reached"})
            continue
        path = out / f"attachment-{index:04d}.bin"
        path.write_bytes(payload)
        attachments.append({"name": clean_name, "path": str(path)})

    parsed["html"] = html_body
    parsed["attachments"] = attachments
    parsed["skipped"] = skipped
    return parsed


def _parse_eml(src: str) -> dict:
    with open(src, "rb") as handle:
        message: EmailMessage = BytesParser(policy=policy.default).parse(handle)
    return _from_email_message(message)


def _text_of(part) -> str:
    try:
        return part.get_content()
    except (LookupError, UnicodeError, KeyError, ValueError):
        return decode_text(part.get_payload(decode=True) or b"")


def _leaf_parts(message: EmailMessage):
    """Yields the message's parts, treating an attached message as one unit.

    `walk()` would descend into attached messages, mixing their parts into this one.
    """
    for part in message.iter_parts():
        if part.get_content_type() == "message/rfc822":
            yield part
        elif part.is_multipart():
            yield from _leaf_parts(part)
        else:
            yield part


def _from_email_message(message: EmailMessage) -> dict:
    html_part = message.get_body(preferencelist=("html",))
    text_part = message.get_body(preferencelist=("plain",))
    inline: dict[str, tuple[str, bytes]] = {}
    attachments: list[tuple[str, bytes]] = []
    html_body = _text_of(html_part) if html_part is not None else None
    text_body = _text_of(text_part) if text_part is not None else None

    if html_part is None and text_part is None and not message.is_multipart():
        text_body = _text_of(message)

    for part in _leaf_parts(message) if message.is_multipart() else ():
        if part is html_part or part is text_part:
            continue
        content_type = part.get_content_type()
        filename = part.get_filename()
        if content_type == "message/rfc822":
            nested = part.get_payload(0) if part.is_multipart() else None
            if nested is not None:
                attachments.append((filename or f'{nested.get("Subject") or "message"}.eml', nested.as_bytes()))
            continue
        # Whether the HTML references an image decides what it is: some mail clients mark
        # inline images as attachments, and unreferenced ones must not be lost.
        content_id = (part.get("Content-ID") or "").strip().strip("<>")
        if content_id and content_type.startswith("image/") and html_body and f"cid:{content_id}" in html_body:
            inline[content_id] = (content_type, part.get_payload(decode=True) or b"")
            continue
        if part.get_content_disposition() == "attachment" or filename or not content_type.startswith("text/"):
            attachments.append((filename or "attachment", part.get_payload(decode=True) or b""))

    return {
        "subject": str(message.get("Subject") or ""),
        "from": str(message.get("From") or ""),
        "to": str(message.get("To") or ""),
        "cc": str(message.get("Cc") or ""),
        "date": str(message.get("Date") or ""),
        "html": html_body,
        "text": text_body,
        "inline": inline,
        "attachments": attachments,
    }


def _parse_msg(src: str) -> dict:
    message = extract_msg.openMsg(src, delayAttachments=False)
    try:
        html_bytes = None
        try:
            html_bytes = message.htmlBody
        except Exception:  # noqa: BLE001 - HTML can be derived from RTF, which may be malformed
            html_bytes = None
        inline: dict[str, tuple[str, bytes]] = {}
        attachments: list[tuple[str, bytes]] = []
        for attachment in message.attachments:
            name = getattr(attachment, "longFilename", None) or getattr(attachment, "shortFilename", None) or "attachment"
            data = attachment.data
            if isinstance(data, extract_msg.msg_classes.MSGFile):
                # An embedded message: re-export it so the pipeline can recurse into it.
                nested_path = Path(src).with_name(f"nested-{len(attachments)}.msg")
                data.export(str(nested_path))
                attachments.append((f"{name}.msg" if not name.lower().endswith(".msg") else name, nested_path.read_bytes()))
                continue
            if not isinstance(data, (bytes, bytearray)):
                continue
            content_id = (getattr(attachment, "cid", None) or "").strip().strip("<>")
            mime = (getattr(attachment, "mimetype", None) or "").lower()
            if content_id and html_bytes and content_id.encode() in html_bytes:
                inline[content_id] = (mime or "application/octet-stream", bytes(data))
            else:
                attachments.append((name, bytes(data)))
        return {
            "subject": str(message.subject or ""),
            "from": str(message.sender or ""),
            "to": str(message.to or ""),
            "cc": str(message.cc or ""),
            "date": str(message.date or ""),
            "html": decode_text(html_bytes) if html_bytes else None,
            "text": str(message.body) if message.body else None,
            "inline": inline,
            "attachments": attachments,
        }
    finally:
        message.close()


def _embed_inline_images(body: str, inline: dict[str, tuple[str, bytes]]) -> str:
    """Turns cid: references into data: URIs, the only thing the renderer may load."""
    def replace(match: re.Match) -> str:
        entry = inline.get(match.group(1))
        if entry is None:
            return match.group(0)
        mime, payload = entry
        if not re.fullmatch(r"[a-zA-Z0-9.+/-]+", mime or ""):
            mime = "application/octet-stream"
        return f"data:{mime};base64,{base64.b64encode(payload).decode('ascii')}"

    return re.sub(r"cid:([^\"'\s>)]+)", replace, body, flags=re.IGNORECASE)


def render_cover(parsed: dict, attachment_notes: list[dict]) -> str:
    """Builds the HTML for the message: a header table, attachment notes, then the body.

    Every header value is escaped. The body HTML is deliberately left as sent, because
    rendering runs with JavaScript off and no network, and a sanitiser would damage layout.
    """
    rows = []
    for label, key in (("From", "from"), ("To", "to"), ("Cc", "cc"), ("Date", "date"), ("Subject", "subject")):
        value = parsed.get(key)
        if value:
            rows.append(
                f'<tr><td style="padding:2px 12px 2px 0;font-weight:bold;vertical-align:top">{label}</td>'
                f'<td style="padding:2px 0">{html.escape(value)}</td></tr>'
            )
    if attachment_notes:
        items = "".join(
            f"<li>{html.escape(note['name'])}"
            + (f" &mdash; not converted: {html.escape(note['reason'])}" if note.get("reason") else "")
            + "</li>"
            for note in attachment_notes
        )
        rows.append(
            '<tr><td style="padding:2px 12px 2px 0;font-weight:bold;vertical-align:top">Attachments</td>'
            f'<td style="padding:2px 0"><ul style="margin:0;padding-left:18px">{items}</ul></td></tr>'
        )
    header = (
        f'<div style="{_MESSAGE_STYLE};border-bottom:1px solid #999;padding-bottom:8px;margin-bottom:12px">'
        f'<table style="border-collapse:collapse;{_MESSAGE_STYLE}">{"".join(rows)}</table></div>'
    )

    title = html.escape(parsed.get("subject") or "")
    if parsed.get("html"):
        body = parsed["html"]
        match = re.search(r"<body[^>]*>", body, re.IGNORECASE)
        if match:
            return body[: match.end()] + header + body[match.end():]
        return f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head><body>{header}{body}</body></html>'

    text = html.escape(parsed.get("text") or "")
    return (
        f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title></head>'
        f'<body>{header}<div style="{_MESSAGE_STYLE};white-space:pre-wrap;overflow-wrap:anywhere">{text}</div></body></html>'
    )
