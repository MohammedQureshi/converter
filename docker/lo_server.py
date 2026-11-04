#!/usr/bin/python3
"""Starts stock unoserver with two additions it has no option for.

Runs under Debian's /usr/bin/python3, the only interpreter that can import `uno`. The
app talks to it over unoserver's normal XML-RPC API. `UnoConverter.convert` offers no
hook, so this wraps the desktop object it calls `loadComponentFromURL` on:

* Security: every document loads hidden, with macros forced off and links never updated.
  These settings apply per document, on top of the profile's registry settings.
* Layout: spreadsheets without their own scaling fit one page wide, and text and CSV
  files (which have no page setup of their own) use the configured page size.
"""

import logging
import os
import sys

import uno  # noqa: F401 - installs the import hook that the com.sun.star imports need
from com.sun.star.beans import PropertyValue
from unoserver import converter, server

log = logging.getLogger("lo_server")

MACRO_NEVER_EXECUTE = 0  # com.sun.star.document.MacroExecMode.NEVER_EXECUTE
UPDATE_NEVER = 0  # com.sun.star.document.UpdateDocMode.NO_UPDATE

# Separator, quote, UTF-8, first line, auto columns, language, not all text, detect numbers.
CSV_FILTER = ("Text - txt - csv (StarCalc)", "44,34,76,1,,0,false,true")
TEXT_FILTER = ("Text (encoded)", "UTF8")

PAGE_WIDTH = int(os.environ.get("LO_TEXT_PAGE_WIDTH", "21000"))  # 1/100 mm
PAGE_HEIGHT = int(os.environ.get("LO_TEXT_PAGE_HEIGHT", "29700"))


def _set_page_size(doc):
    styles = doc.StyleFamilies.getByName("PageStyles")
    for name in styles.ElementNames:
        style = styles.getByName(name)
        style.Width = PAGE_WIDTH
        style.Height = PAGE_HEIGHT


def _fit_sheets_to_width(doc):
    """Fits each sheet to one page wide, unless the author chose scaling themselves."""
    styles = doc.StyleFamilies.getByName("PageStyles")
    sheets = doc.Sheets
    for index in range(sheets.Count):
        style = styles.getByName(sheets.getByIndex(index).PageStyle)
        has_own_scaling = (
            style.ScaleToPages != 0 or style.ScaleToPagesX != 0 or style.ScaleToPagesY != 0 or style.PageScale != 100
        )
        if not has_own_scaling:
            style.ScaleToPagesX = 1
            style.ScaleToPagesY = 0


class _Desktop:
    def __init__(self, desktop):
        self._desktop = desktop

    def __getattr__(self, name):
        return getattr(self._desktop, name)

    def loadComponentFromURL(self, url, target, flags, props):
        extension = url.rsplit(".", 1)[-1].lower()
        settings = {p.Name: p.Value for p in props}
        settings.update(Hidden=True, MacroExecutionMode=MACRO_NEVER_EXECUTE, UpdateDocMode=UPDATE_NEVER)
        if extension == "csv":
            settings["FilterName"], settings["FilterOptions"] = CSV_FILTER
        elif extension == "txt":
            settings["FilterName"], settings["FilterOptions"] = TEXT_FILTER
        props = tuple(PropertyValue(Name=k, Value=v) for k, v in settings.items())

        doc = self._desktop.loadComponentFromURL(url, target, flags, props)
        if doc is None:
            return None
        try:
            if extension in ("csv", "txt"):
                _set_page_size(doc)
            if doc.supportsService("com.sun.star.sheet.SpreadsheetDocument"):
                _fit_sheets_to_width(doc)
        except Exception:  # noqa: BLE001 - a layout tweak must never fail the conversion
            log.exception("Could not adjust page layout for %s", extension)
        return doc


class HardenedConverter(converter.UnoConverter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.desktop = _Desktop(self.desktop)


converter.UnoConverter = HardenedConverter

if __name__ == "__main__":
    sys.exit(server.main())
