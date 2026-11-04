"""PDF inspection, merging and metadata. Runs in isolated processes (see app.isolate)."""

from __future__ import annotations

from pathlib import Path

import pikepdf

from app.errors import CorruptFile, EncryptedFile

_CONTROL_CHARS = {c: None for c in range(32) if c not in (9, 10, 13)}


def _clean(text: str | None) -> str | None:
    if not text:
        return None
    cleaned = str(text).translate(_CONTROL_CHARS).strip()
    return cleaned[:1000] or None


def inspect_pdf(path: str) -> dict:
    """Page count and title of a PDF; rejects encrypted and unreadable files."""
    try:
        with pikepdf.open(path) as pdf:
            if pdf.is_encrypted:
                raise EncryptedFile("The PDF is encrypted")
            pages = len(pdf.pages)
            if pages == 0:
                raise CorruptFile("The PDF has no pages")
            return {"pages": pages, "title": _read_title(pdf)}
    except pikepdf.PasswordError:
        raise EncryptedFile("The PDF is password-protected") from None
    except pikepdf.PdfError as exc:
        raise CorruptFile("The PDF is damaged and cannot be read") from exc


def _read_title(pdf: pikepdf.Pdf) -> str | None:
    title = None
    try:
        # No `with` block: exiting one would stamp pikepdf as the Producer.
        title = pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=False).get("dc:title")
    except Exception:  # noqa: BLE001 - malformed XMP should not fail the conversion
        pass
    if not title and pdf.docinfo is not None and "/Title" in pdf.docinfo:
        try:
            title = str(pdf.docinfo["/Title"])
        except Exception:  # noqa: BLE001
            pass
    return _clean(title)


def has_type1_font_without_charset(path: str) -> bool:
    """True if a Type 1 font lacks the /CharSet entry that PDF/A-1 requires (rule 6.3.5-2).

    LibreOffice embeds OpenType/CFF fonts this way, which includes the Noto CJK family, so
    its "PDF/A-1b" export of any document with Chinese, Japanese or Korean text fails
    validation. A Ghostscript pass rewrites these fonts correctly.
    """
    with pikepdf.open(path) as pdf:
        for obj in pdf.objects:
            if isinstance(obj, pikepdf.Dictionary) and obj.get("/Type") == "/FontDescriptor":
                if "/FontFile" in obj and "/CharSet" not in obj:
                    return True
    return False


def merge_pdfs(paths: list[str], out_path: str) -> int:
    """Concatenates PDFs and returns the page count."""
    with pikepdf.new() as merged:
        for path in paths:
            with pikepdf.open(path) as part:
                merged.pages.extend(part.pages)
        merged.save(out_path)
        return len(merged.pages)


def _count_flattened_pages(pdf: pikepdf.Pdf) -> int:
    """Pages Ghostscript rendered to one bitmap because they used transparency.

    Those pages keep their appearance but lose searchable text. A flattened page is a
    single image at the 720 dpi pdfwrite device resolution, with no text operators.
    """
    flattened = 0
    for page in pdf.pages:
        try:
            images = page.get_images() if hasattr(page, "get_images") else page.images
            if len(images) != 1:
                continue
            image = next(iter(images.values()))
            box = page.mediabox
            width_pt = float(box[2]) - float(box[0])
            if width_pt <= 0 or abs(int(image.Width) / width_pt * 72 - 720) > 8:
                continue
            if not any(
                str(item.operator) in {"Tj", "TJ", "'", '"'} for item in pikepdf.parse_content_stream(page)
            ):
                flattened += 1
        except Exception:  # noqa: BLE001 - this is only a reporting signal
            continue
    return flattened


_FORBIDDEN_CATALOG_KEYS = ("/AA", "/OCProperties", "/Collection", "/AF", "/Perms", "/Requirements")
_FORBIDDEN_NAME_TREES = ("/EmbeddedFiles", "/JavaScript", "/AlternatePresentations", "/Renditions")
_FORBIDDEN_ACTIONS = {
    "/JavaScript", "/Launch", "/Sound", "/Movie", "/ResetForm", "/ImportData", "/Hide",
    "/SetOCGState", "/Rendition", "/Trans", "/GoTo3DView",
}
_FORBIDDEN_ANNOTATIONS = {"/FileAttachment", "/Sound", "/Movie", "/Screen", "/3D", "/PrinterMark", "/TrapNet"}


def _is_forbidden_action(action) -> bool:
    return isinstance(action, pikepdf.Dictionary) and str(action.get("/S")) in _FORBIDDEN_ACTIONS


def _strip_forbidden_features(pdf: pikepdf.Pdf) -> None:
    """Removes what PDF/A-1 forbids and Ghostscript may leave behind.

    PDFACompatibilityPolicy=1 does not cover everything: embedded files survive it, for
    example, and the result fails validation. Objects that are no longer referenced are
    left out when qpdf saves the file.
    """
    root = pdf.Root
    for key in _FORBIDDEN_CATALOG_KEYS:
        if key in root:
            del root[key]
    if "/Names" in root:
        for key in _FORBIDDEN_NAME_TREES:
            if key in root.Names:
                del root.Names[key]
    if "/OpenAction" in root and _is_forbidden_action(root.OpenAction):
        del root["/OpenAction"]
    if "/AcroForm" in root:
        form = root.AcroForm
        for key in ("/XFA", "/NeedAppearances"):
            if key in form:
                del form[key]

    for page in pdf.pages:
        if "/AA" in page:
            del page["/AA"]
        if "/Annots" not in page:
            continue
        kept = []
        for annotation in page.Annots:
            if str(annotation.get("/Subtype")) in _FORBIDDEN_ANNOTATIONS:
                continue
            if "/AA" in annotation:
                del annotation["/AA"]
            if "/A" in annotation and _is_forbidden_action(annotation.A):
                del annotation["/A"]
            kept.append(annotation)
        if kept:
            page.Annots = pikepdf.Array(kept)
        else:
            del page["/Annots"]


def _strip_tags(pdf: pikepdf.Pdf) -> None:
    """Removes the structure tree. qpdf then leaves its now-unreferenced objects out of the file.

    The marked-content operators in page streams stay, and are harmless without a tree.
    """
    root = pdf.Root
    for key in ("/StructTreeRoot", "/MarkInfo"):
        if key in root:
            del root[key]
    for page in pdf.pages:
        if "/StructParents" in page:
            del page["/StructParents"]
        for annotation in page.get("/Annots", []):
            if "/StructParent" in annotation:
                del annotation["/StructParent"]


def finalize_pdf(
    path: str, out_path: str, source_filename: str, title: str | None, count_flattened: bool, strip_tags: bool = False
) -> dict:
    """Writes the source filename and title into XMP, keeping the file PDF/A compliant.

    Only metadata changes, and qpdf copies page content without re-encoding it.
    `update_docinfo` keeps the Info dictionary in step with XMP, as PDF/A requires, and
    the editor stamp stays off so the existing dates remain consistent.
    """
    with pikepdf.open(path) as pdf:
        pages = len(pdf.pages)
        flattened = _count_flattened_pages(pdf) if count_flattened else 0
        existing_title = _read_title(pdf)
        _strip_forbidden_features(pdf)
        if strip_tags:
            _strip_tags(pdf)
        with pdf.open_metadata(set_pikepdf_as_editor=False, update_docinfo=True) as meta:
            final_title = _clean(title) or existing_title
            if final_title:
                meta["dc:title"] = final_title
            source = _clean(source_filename)
            if source:
                meta["dc:source"] = source
        pdf.save(
            out_path,
            linearize=False,
            object_stream_mode=pikepdf.ObjectStreamMode.disable,
            stream_decode_level=pikepdf.StreamDecodeLevel.none,
            compress_streams=False,
            preserve_pdfa=True,
            fix_metadata_version=False,
        )
    return {"pages": pages, "title": final_title, "flattened_pages": flattened}
