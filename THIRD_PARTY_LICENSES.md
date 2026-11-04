# Third-party licences

Generated at image build time by `docker/generate_licenses.py`, from pip-licenses and dpkg
data, so it matches this image exactly. It is a factual inventory and not legal advice.

## Notes

- **Deployment model:** this software is run as a service and is never distributed.
- **Ghostscript (AGPL-3.0):** the unmodified Debian package, run only as an external process.
  It is not patched, and not linked as a library. All calls are in `app/engines/ghostscript.py`.
- **extract-msg (GPL-3.0):** used to read `.msg` files. Controlled by `ENABLE_MSG`.
- **veraPDF:** used under the MPL-2.0 option of its dual licence.
- **HEIC/HEIF:** decoder only (libheif and libde265). No HEVC encoder is installed.
- **Microsoft core fonts:** not installed.

## Other components

| Component | Version | Licence | URL |
|---|---|---|---|
| veraPDF | 1.30.3 | MPL-2.0 (the MPL-2.0 option of its dual GPL-3.0+ / MPL-2.0 licence is chosen) | https://verapdf.org |

## Python packages (55)

| Package | Version | Licence | URL |
|---|---|---|---|
| annotated-doc | 0.0.5 | MIT | https://github.com/fastapi/annotated-doc |
| annotated-types | 0.8.0 | MIT | https://github.com/annotated-types/annotated-types |
| anyio | 4.16.0 | MIT | https://anyio.readthedocs.io/en/stable/versionhistory.html |
| beautifulsoup4 | 4.15.0 | MIT License | https://www.crummy.com/software/BeautifulSoup/bs4/ |
| cairocffi | 1.7.1 | BSD License | https://doc.courtbouillon.org/cairocffi/stable/changelog.html |
| CairoSVG | 2.9.1 | LGPL-3.0-or-later | https://courtbouillon.org/cairosvg |
| cffi | 2.1.1 | MIT-0 | https://cffi.readthedocs.io/en/latest/whatsnew.html |
| charset-normalizer | 3.5.2 | MIT | https://github.com/jawah/charset_normalizer/blob/master/CHANGELOG.md |
| click | 8.5.0 | BSD-3-Clause | https://github.com/pallets/click/ |
| colorclass | 2.2.2 | MIT License | https://github.com/matthewdeanmartin/colorclass |
| compressed-rtf | 1.0.7 | MIT | https://github.com/delimitry/compressed_rtf |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause | https://github.com/pyca/cryptography |
| cssselect2 | 0.10.1 | BSD License | https://doc.courtbouillon.org/cssselect2/ |
| defusedxml | 0.7.1 | Python Software Foundation License | https://github.com/tiran/defusedxml |
| easygui | 0.98.3 | BSD License | https://github.com/robertlugg/easygui |
| ebcdic | 2.0.1 | BSD-2-Clause | https://pypi.python.org/pypi/ebcdic |
| extract-msg | 0.58.1 | GPL | https://github.com/TeamMsgExtractor/msg-extractor |
| fastapi | 0.162.0 | MIT | https://github.com/fastapi/fastapi |
| greenlet | 3.5.6 | MIT AND PSF-2.0 | https://greenlet.readthedocs.io |
| h11 | 0.16.0 | MIT License | https://github.com/python-hyper/h11 |
| idna | 3.20 | BSD-3-Clause | https://github.com/kjd/idna |
| img2pdf | 0.6.3 | GNU Lesser General Public License v3 (LGPLv3) | UNKNOWN |
| lark | 1.3.1 | MIT License | https://github.com/lark-parser/lark |
| lxml | 6.1.3 | BSD-3-Clause | https://lxml.de/ |
| Markdown | 3.11.2 | BSD-3-Clause | https://Python-Markdown.github.io/ |
| msoffcrypto-tool | 6.1.0 | MIT License | https://github.com/nolze/msoffcrypto-tool |
| olefile | 0.47 | BSD License | https://www.decalage.info/python/olefileio |
| oletools | 0.60.2 | BSD License | https://github.com/decalage2/oletools |
| opentelemetry-api | 1.45.2 | Apache-2.0 | https://github.com/open-telemetry/opentelemetry-python/tree/main/opentelemetry-api |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | https://github.com/pypa/packaging |
| pcodedmp | 1.2.6 | GNU General Public License v3 (GPLv3) | https://github.com/bontchev/pcodedmp |
| pikepdf | 10.17.0 | MPL-2.0 | https://github.com/pikepdf/pikepdf |
| pillow | 13.0.0 | MIT-CMU | https://python-pillow.org |
| pillow_heif | 1.8.1 | BSD-3-Clause | https://github.com/bigcat88/pillow_heif |
| playwright | 1.64.1 | Apache-2.0 | https://github.com/Microsoft/playwright-python |
| pycparser | 3.12 | BSD-3-Clause | https://github.com/eliben/pycparser |
| pydantic | 2.14.2 | MIT | https://github.com/pydantic/pydantic |
| pydantic-settings | 2.16.2 | MIT | https://github.com/pydantic/pydantic-settings |
| pydantic_core | 2.50.2 | MIT | https://github.com/pydantic |
| pyee | 14.0.0 | MIT License | https://github.com/jfhbrook/pyee |
| pyparsing | 3.3.3 | MIT | https://github.com/pyparsing/pyparsing/ |
| python-dotenv | 1.2.4 | BSD-3-Clause | https://github.com/theskumar/python-dotenv |
| python-magic | 0.4.27 | MIT License | http://github.com/ahupp/python-magic |
| python-multipart | 0.0.33 | Apache-2.0 | https://github.com/Kludex/python-multipart |
| red-black-tree-mod | 1.22 | MIT | http://stromberg.dnsalias.org/~strombrg/red-black-tree-mod/ |
| RTFDE | 0.1.2.2 | GNU Lesser General Public License v3 (LGPLv3) | https://github.com/seamustuohy/RTFDE |
| soupsieve | 4.0 | MIT | https://github.com/facelessuser/soupsieve |
| starlette | 1.10.0 | BSD-3-Clause | https://github.com/Kludex/starlette |
| tinycss2 | 1.5.1 | BSD License | https://www.courtbouillon.org/tinycss2 |
| typing-inspection | 0.4.4 | MIT | https://github.com/pydantic/typing-inspection |
| typing_extensions | 4.16.0 | PSF-2.0 | https://github.com/python/typing_extensions |
| tzlocal | 5.4.5 | MIT | https://github.com/regebro/tzlocal/blob/master/CHANGES.txt |
| unoserver | 3.7 | MIT |  |
| uvicorn | 0.54.0 | BSD-3-Clause | https://uvicorn.dev/ |
| webencodings | 0.6.1 | BSD License | https://github.com/CourtBouillon/webencodings |

## Fonts (230 families)

| Family | Package | Version | Licence | Files |
|---|---|---|---|---|
| Caladea | fonts-crosextra-caladea | 20200211-2 | OFL-1.1, Apache-2.0 | 4 |
| Carlito | fonts-crosextra-carlito | 20230309-2 | OFL-1.1, GPL-2+ | 4 |
| DejaVu Sans | fonts-dejavu-core | 2.37-8 | bitstream-vera, GPL-2+ | 2 |
| DejaVu Serif | fonts-dejavu-core | 2.37-8 | bitstream-vera, GPL-2+ | 2 |
| DejaVu Math TeX Gyre | fonts-dejavu-extra | 2.37-8 | bitstream-vera, GPL-2+ | 1 |
| DejaVu Sans | fonts-dejavu-extra | 2.37-8 | bitstream-vera, GPL-2+ | 7 |
| DejaVu Serif | fonts-dejavu-extra | 2.37-8 | bitstream-vera, GPL-2+ | 6 |
| DejaVu Sans Mono | fonts-dejavu-mono | 2.37-8 | bitstream-vera, GPL-2+ | 4 |
| Liberation Mono | fonts-liberation | 1:2.1.5-3 | SIL-OFL-1.1, GPL-2+ | 4 |
| Liberation Sans | fonts-liberation | 1:2.1.5-3 | SIL-OFL-1.1, GPL-2+ | 4 |
| Liberation Serif | fonts-liberation | 1:2.1.5-3 | SIL-OFL-1.1, GPL-2+ | 4 |
| Noto Sans CJK HK | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Sans CJK JP | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Sans CJK KR | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Sans CJK SC | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Sans CJK TC | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Sans Mono CJK HK | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Sans Mono CJK JP | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Sans Mono CJK KR | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Sans Mono CJK SC | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Sans Mono CJK TC | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Serif CJK HK | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Serif CJK JP | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Serif CJK KR | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Serif CJK SC | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Serif CJK TC | fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ | 2 |
| Noto Kufi Arabic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Looped Lao | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Looped Thai | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Music | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Naskh Arabic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Nastaliq Urdu | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Rashi Hebrew | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 4 |
| Noto Sans Adlam | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Adlam Unjoined | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Anatolian Hieroglyphs | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Arabic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Armenian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Avestan | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Balinese | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Bamum | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Bassa Vah | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Batak | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Bengali | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Bhaiksuki | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Brahmi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Buginese | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Buhid | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Canadian Aboriginal | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Carian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Caucasian Albanian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Chakma | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Cham | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Cherokee | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Coptic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Cuneiform | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Cypriot | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Deseret | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Devanagari | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Display | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 4 |
| Noto Sans Duployan | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Egyptian Hieroglyphs | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Elbasan | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Elymaic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Ethiopic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Georgian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Glagolitic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Gothic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Grantha | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Gujarati | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Gunjala Gondi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Gurmukhi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Hanifi Rohingya | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Hanunoo | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Hatran | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Hebrew | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Imperial Aramaic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Indic Siyaq Numbers | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Inscriptional Pahlavi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Inscriptional Parthian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Javanese | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Kaithi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Kannada | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Kayah Li | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Kharoshthi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Khmer | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Khojki | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Khudawadi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Lao | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Lepcha | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Limbu | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Linear A | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Linear B | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Lisu | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Lycian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Lydian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Mahajani | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Malayalam | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Mandaic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Manichaean | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Marchen | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Masaram Gondi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Math | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Mayan Numerals | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Medefaidrin | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Meetei Mayek | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Mende Kikakui | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Meroitic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Miao | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Modi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Mongolian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Mro | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Multani | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Myanmar | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans NKo | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Nabataean | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans New Tai Lue | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Newa | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Nushu | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Ogham | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Ol Chiki | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Old Hungarian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Old Italic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Old North Arabian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Old Permic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Old Persian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Old Sogdian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Old South Arabian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Old Turkic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Oriya | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Osage | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Osmanya | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Pahawh Hmong | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Palmyrene | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Pau Cin Hau | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans PhagsPa | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Phoenician | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Psalter Pahlavi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Rejang | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Runic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Samaritan | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Saurashtra | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Sharada | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Shavian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Siddham | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans SignWriting | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Sinhala | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Sogdian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Sora Sompeng | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Soyombo | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Sundanese | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Syloti Nagri | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Symbols | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Symbols2 | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Syriac | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tagalog | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tagbanwa | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tai Le | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tai Tham | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Tai Viet | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Takri | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tamil | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Tamil Supplement | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Telugu | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Thaana | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Thai | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Sans Tifinagh | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh APT | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh Adrar | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh Agraw Imazighen | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh Ahaggar | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh Air | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh Azawagh | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh Ghat | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh Hawad | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh Rhissa Ixa | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh SIL | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tifinagh Tawellemmet | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Tirhuta | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Ugaritic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Vai | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Wancho | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Warang Citi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Yi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Zanabazar Square | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Serif | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 4 |
| Noto Serif Ahom | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Serif Armenian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Balinese | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Serif Bengali | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Devanagari | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Display | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 4 |
| Noto Serif Dogra | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Serif Ethiopic | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Georgian | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Grantha | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Serif Gujarati | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Gurmukhi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Hebrew | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Hmong Nyiakeng | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Kannada | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Khmer | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Khojki | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Lao | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Malayalam | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Myanmar | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Sinhala | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Tamil | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Tamil Slanted | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Tangut | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Serif Telugu | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Thai | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Tibetan | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Serif Yezidi | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| Noto Traditional Nushu | fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Mono | fonts-noto-mono | 20201225-2 | OFL-1.1, GPL-3+ | 1 |
| Noto Sans Mono | fonts-noto-mono | 20201225-2 | OFL-1.1, GPL-3+ | 2 |
| OpenSymbol | fonts-opensymbol | 4:102.13+LibO26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... | 1 |
| C059 | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 12 |
| D050000L | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 3 |
| Nimbus Mono PS | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 12 |
| Nimbus Roman | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 12 |
| Nimbus Sans | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 12 |
| Nimbus Sans Narrow | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 12 |
| P052 | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 12 |
| Standard Symbols PS | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 3 |
| URW Bookman | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 12 |
| URW Gothic | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 12 |
| Z003 | fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 | 3 |

## System packages (414)

| Package | Version | Licence |
|---|---|---|
| adduser | 3.152 | GPL-2+ |
| adwaita-icon-theme | 48.1-1 | CC-BY-SA-3.0, LGPL-3, and CC-BY-SA-4.0, CC-BY-SA-3.0-US, GPL-unspecified, CC-BY-SA-4.0, ... |
| apt | 3.0.3 | GPL-2+, curl, BSD-3-clause, Expat, GPL-2 |
| at-spi2-common | 2.56.2-1+deb13u2 | LGPL-2+, LGPL-2.1+, AFL-2.1, GPL-2+, GPL-2, public-domain |
| base-files | 13.8+deb13u7 | GPL-2+, verbatim |
| base-passwd | 3.6.7 | GPL-2, public-domain |
| bash | 5.2.37-2+b10 | GPL-3+, GPL-3+ with Bison exception, GPL-2+, GFDL-NIV-1.3, Latex2e, BSD-4-clause-UC, ... |
| bsdutils | 1:2.41.5-0+deb13u1 | GPL-2+, GPL-2, GPL-3+, LGPL-2.1+, public-domain, BSD-4-clause, ... |
| ca-certificates | 20250419+deb13u1 | GPL-2+, MPL-2.0 |
| ca-certificates-java | 20240118 | The Debian package is (C) 2008, Canonical Ltd, (C) 2011, Torsten Werner |
| chromium | 156.0.8078.79-1~deb13u1 | BSD-3-clause, Unicode, MIT, ICU, LGPL-2.0+, MPL-1.1, ... |
| chromium-common | 156.0.8078.79-1~deb13u1 | BSD-3-clause, Unicode, MIT, ICU, LGPL-2.0+, MPL-1.1, ... |
| coinor-libcbc3.1 | 2.10.12+ds-1 | EPL-2.0, FSFUL, GPL-2+ with Autoconf-data exception, Expat-X, LUCENT, EPL-1, ... |
| coinor-libcgl1 | 0.60.9+ds-1 | EPL-2.0, FSFULLR, GPL-2+ with Autoconf-data exception, FSFUL, X11, EPL-1, ... |
| coinor-libclp1 | 1.17.10+ds-1 | EPL-2.0, FSFULLR, GPL-2+ with Autoconf-data exception, FSFUL, X11, Expat-CMU~warranty, ... |
| coinor-libcoinmp0 | 1.8.4+dfsg-2 | CPL-1, EPL-1, GPL-2+ |
| coinor-libcoinutils3v5 | 2.11.11+ds-5 | EPL-1, GPL-3 |
| coinor-libosi1v5 | 0.108.10+ds-2 | EPL-2.0, FSFULLR, GPL-2+ with Autoconf-data exception, FSFUL, X11, EPL-1, ... |
| coreutils | 9.7-3 | GPL-3+, BSD-4-clause-UC, ISC, FSFULLR, GFDL-NIV-1.3 |
| dash | 0.5.12-12 | BSD-3-Clause, public-domain, GPL-2+, BSD-3-clause |
| dbus | 1.16.2-2 | GPL-2+, AFL-2.1, and Expat, Tcl-BSDish, BSD-3-clause, BSD-3-clause-generic, ... |
| dbus-bin | 1.16.2-2 | GPL-2+, AFL-2.1, and Expat, Tcl-BSDish, BSD-3-clause, BSD-3-clause-generic, ... |
| dbus-daemon | 1.16.2-2 | GPL-2+, AFL-2.1, and Expat, Tcl-BSDish, BSD-3-clause, BSD-3-clause-generic, ... |
| dbus-session-bus-common | 1.16.2-2 | GPL-2+, AFL-2.1, and Expat, Tcl-BSDish, BSD-3-clause, BSD-3-clause-generic, ... |
| dbus-system-bus-common | 1.16.2-2 | GPL-2+, AFL-2.1, and Expat, Tcl-BSDish, BSD-3-clause, BSD-3-clause-generic, ... |
| dbus-user-session | 1.16.2-2 | GPL-2+, AFL-2.1, and Expat, Tcl-BSDish, BSD-3-clause, BSD-3-clause-generic, ... |
| dconf-gsettings-backend | 0.40.0-5 | LGPL-2+, GPL-3 |
| dconf-service | 0.40.0-5 | LGPL-2+, GPL-3 |
| debconf | 1.5.91 | BSD-2-clause |
| debian-archive-keyring | 2025.1 | see copyright file |
| debianutils | 5.23.2 | GPL-2+, public-domain, SMAIL-GPL |
| diffutils | 1:3.10-4 | GPL-3+, FSFULLR, LGPL-2.1+, GPL-3+ with autoconf exception, GPL-3+ with texinfo exception, LGPL-2.0+, ... |
| dirmngr | 2.4.7-21+deb13u1+b5 | GPL-3+, permissive, LGPL-2.1+, LGPL-3+, GPL-2+, Expat, ... |
| dpkg | 1.22.22 | GPL-2+, public-domain-s-s-d |
| findutils | 4.10.0-3 | GFDL-NIV-1.3+, GPL-3+, FSFAP, GPL-2+ with Autoconf-data exception, GPL-3+ with Autoconf-data exception, FSFULLR, ... |
| fontconfig | 2.15.0-2.3 | see copyright file |
| fontconfig-config | 2.15.0-2.3 | see copyright file |
| fonts-crosextra-caladea | 20200211-2 | OFL-1.1, Apache-2.0 |
| fonts-crosextra-carlito | 20230309-2 | OFL-1.1, GPL-2+ |
| fonts-dejavu-core | 2.37-8 | bitstream-vera, GPL-2+ |
| fonts-dejavu-extra | 2.37-8 | bitstream-vera, GPL-2+ |
| fonts-dejavu-mono | 2.37-8 | bitstream-vera, GPL-2+ |
| fonts-liberation | 1:2.1.5-3 | SIL-OFL-1.1, GPL-2+ |
| fonts-noto-cjk | 1:20240730+repack1-1 | SIL-1.1, GPL-3+ |
| fonts-noto-core | 20201225-2 | OFL-1.1, GPL-3+ |
| fonts-noto-mono | 20201225-2 | OFL-1.1, GPL-3+ |
| fonts-opensymbol | 4:102.13+LibO26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| fonts-urw-base35 | 20200910-8 | AGPL-3 with Font exception, CC-BY-4.0, GPL-2+, AGPL-3 |
| gcc-14-base | 14.2.0-19 | GPL-3, LGPL, MIT, BSD |
| ghostscript | 10.05.1~dfsg-1+deb13u3 | AGPL-3+, FTL, none, BSD-3-Clause~Adobe, GPL-2, LGPL-2.1, ... |
| gnupg | 2.4.7-21+deb13u1 | GPL-3+, permissive, LGPL-2.1+, LGPL-3+, GPL-2+, Expat, ... |
| gnupg-l10n | 2.4.7-21+deb13u1 | GPL-3+, permissive, LGPL-2.1+, LGPL-3+, GPL-2+, Expat, ... |
| gpg | 2.4.7-21+deb13u1+b5 | GPL-3+, permissive, LGPL-2.1+, LGPL-3+, GPL-2+, Expat, ... |
| gpg-agent | 2.4.7-21+deb13u1+b5 | GPL-3+, permissive, LGPL-2.1+, LGPL-3+, GPL-2+, Expat, ... |
| gpgconf | 2.4.7-21+deb13u1+b5 | GPL-3+, permissive, LGPL-2.1+, LGPL-3+, GPL-2+, Expat, ... |
| gpgsm | 2.4.7-21+deb13u1+b5 | GPL-3+, permissive, LGPL-2.1+, LGPL-3+, GPL-2+, Expat, ... |
| grep | 3.11-4+b1 | GPL-3+ |
| gtk-update-icon-cache | 4.18.6+ds-2 | LGPL-2.1+, LGPL-2+, sun-permissive, lcs-telegraphics-permissive, X11R5-permissive, Expat, ... |
| gzip | 1.13-1+deb13u1 | GPL-3+, GFDL-1.3+-no-invariant, FSF-manpages |
| hicolor-icon-theme | 0.18-2 | GPL-2+ |
| hostname | 3.25 | GPL-2 |
| init-system-helpers | 1.69~deb13u1 | BSD-3-clause, GPL-2+ |
| java-common | 0.76 | GPL-2+ |
| libabsl20240722 | 20240722.0-4 | Apache-2.0 |
| libabw-0.1-1 | 0.1.3-1+b2 | MPL-2.0, MPL-1.1 \| GPL-3 \| LGPL-3 |
| libacl1 | 2.3.2-2+b1 | GPL-2+, LGPL-2+ |
| libapparmor1 | 4.1.0-1 | GPL-2+, BSD-3-clause, LGPL-2.1+, GPL-2 |
| libapt-pkg7.0 | 3.0.3 | GPL-2+, curl, BSD-3-clause, Expat, GPL-2 |
| libargon2-1 | 0~20190702+dfsg-4+b2 | CC0, Apache-2.0 |
| libasound2-data | 1.2.14-1+deb13u1 | LGPL-2.1+ |
| libasound2t64 | 1.2.14-1+deb13u1 | LGPL-2.1+ |
| libassuan9 | 3.0.2-2 | LGPL-2.1+, FSFULLR, FSFULLRWD, GPL-2+ with Autoconf-data exception, GPL-3+ with Autoconf-data exception, X11, ... |
| libasyncns0 | 0.8-6+b5 | LGPL-2.1+ |
| libatk-bridge2.0-0t64 | 2.56.2-1+deb13u2 | LGPL-2+, LGPL-2.1+, AFL-2.1, GPL-2+, GPL-2, public-domain |
| libatk1.0-0t64 | 2.56.2-1+deb13u2 | LGPL-2+, LGPL-2.1+, AFL-2.1, GPL-2+, GPL-2, public-domain |
| libatomic1 | 14.2.0-19 | GPL-3, LGPL, MIT, BSD |
| libatspi2.0-0t64 | 2.56.2-1+deb13u2 | LGPL-2+, LGPL-2.1+, AFL-2.1, GPL-2+, GPL-2, public-domain |
| libattr1 | 1:2.5.2-3 | GPL-2+, LGPL-2+ |
| libaudit-common | 1:4.0.2-2+deb13u1 | GPL-2, LGPL-2.1 |
| libaudit1 | 1:4.0.2-2+deb13u1 | GPL-2, LGPL-2.1 |
| libavahi-client3 | 0.8-16 | GPL-2, BSD |
| libavahi-common-data | 0.8-16 | GPL-2, BSD |
| libavahi-common3 | 0.8-16 | GPL-2, BSD |
| libblas3 | 3.12.1-6 | BSD-3-clause, BSD-3-clause-intel |
| libblkid1 | 2.41.5-0+deb13u1 | GPL-2+, GPL-2, GPL-3+, LGPL-2.1+, public-domain, BSD-4-clause, ... |
| libboost-iostreams1.83.0 | 1.83.0-4.2 | BSL-1.0, Apache-2.0, Zlib, OldBoost1, OldBoost2, Jam, ... |
| libboost-locale1.83.0 | 1.83.0-4.2 | BSL-1.0, Apache-2.0, Zlib, OldBoost1, OldBoost2, Jam, ... |
| libboost-thread1.83.0 | 1.83.0-4.2 | BSL-1.0, Apache-2.0, Zlib, OldBoost1, OldBoost2, Jam, ... |
| libbox2d2 | 2.4.1-3+b3 | Expat, Apache-2.0, Zlib |
| libbrotli1 | 1.1.0-2+deb13u1 | MIT |
| libbsd0 | 0.12.2-2 | BSD-3-clause, BSD-3-clause-Regents, BSD-2-clause-NetBSD, BSD-3-clause-author, BSD-3-clause-John-Birrell, BSD-5-clause-Peter-Wemm, ... |
| libbz2-1.0 | 1.0.8-6 | BSD-variant, GPL-2 |
| libc-bin | 2.41-12+deb13u4 | LGPL-2.1+, LGPL-2+, LGPL-2.1+-with-link-exception, LGPL-3+, GPL-2+, GPL-2+-with-link-exception, ... |
| libc6 | 2.41-12+deb13u4 | LGPL-2.1+, LGPL-2+, LGPL-2.1+-with-link-exception, LGPL-3+, GPL-2+, GPL-2+-with-link-exception, ... |
| libcairo-gobject2 | 1.18.4-1+b1 | see copyright file |
| libcairo2 | 1.18.4-1+b1 | see copyright file |
| libcap-ng0 | 0.8.5-4+b1 | LGPL-2.1+, GPL-2+, GPL-3 |
| libcap2 | 1:2.75-10+deb13u1+b3 | BSD-3-clause, GPL-2, GPL-2+ |
| libcdr-0.1-1 | 0.1.7-1+b3 | MPL-2.0 |
| libcloudproviders0 | 0.3.6-2 | LGPL-3+ |
| libclucene-contribs1t64 | 2.3.3.4+dfsg-1.2+b1 | LGPL-2.1, Apache-2.0, Reuters-21578 - Distribution 1.0 |
| libclucene-core1t64 | 2.3.3.4+dfsg-1.2+b1 | LGPL-2.1, Apache-2.0, Reuters-21578 - Distribution 1.0 |
| libcmis-0.6-6t64 | 0.6.2-2.1+b2 | MPL \| GPL2+ \| LGPL2+ |
| libcolamd3 | 1:7.10.1+dfsg-1 | LGPL-2.1+, BSD-3-clause, GPL-2+, Apache-2.0, BSD-2-clause, LPPL-1.0+, ... |
| libcolord2 | 1.4.7-3 | GPL-2+, LGPL-2.1+, GFDL-NIV, CC0-1.0, NPES |
| libcom-err2 | 1.47.2-3+b12 | GPL-2, GPL-2+, 0BSD, Expat, BSD-3-Clause-Variant, BSD-3-Clause, ... |
| libcrypt1 | 1:4.4.38-1 | see copyright file |
| libcups2t64 | 2.4.10-3+deb13u2 | Apache-2.0-with-GPL2-LGPL2-Exception, FSFUL, Zlib, Apache-2.0, BSD-2-clause, BSD-2-Clause |
| libcurl3t64-gnutls | 8.21.0-2~bpo13+1 | curl, OLDAP-2.8, ISC, GPL-2+ with Autoconf-data exception, FSFUL, GPL-3+ with Autoconf-data exception, ... |
| libcurl4-gnutls | 8.21.0-2~bpo13+1 | curl, OLDAP-2.8, ISC, GPL-2+ with Autoconf-data exception, FSFUL, GPL-3+ with Autoconf-data exception, ... |
| libcurl4t64 | 8.21.0-2~bpo13+1 | curl, OLDAP-2.8, ISC, GPL-2+ with Autoconf-data exception, FSFUL, GPL-3+ with Autoconf-data exception, ... |
| libdatrie1 | 0.2.13-3+b1 | LGPL-2.1+, GPL-2+ |
| libdav1d7 | 1.5.1-1 | BSD-2-clause, public-domain, ISC |
| libdb5.3t64 | 5.3.28+dfsg2-9 | Sleepycat, BSD-3-clause, Ms-PL, GPL, Artistic, X11, ... |
| libdbus-1-3 | 1.16.2-2 | GPL-2+, AFL-2.1, and Expat, Tcl-BSDish, BSD-3-clause, BSD-3-clause-generic, ... |
| libdconf1 | 0.40.0-5 | LGPL-2+, GPL-3 |
| libde265-0 | 1.0.15-1+deb13u2 | LGPL-3+, GPL-3+, BSD-4-clause, public-domain-1, other-1 |
| libdebconfclient0 | 0.280 | BSD-2-Clause, GPL-2+, BSD-2-clause |
| libdeflate0 | 1.23-2 | Expat |
| libdouble-conversion3 | 3.3.1-1 | BSD-3-clause |
| libdrm-amdgpu1 | 2.4.124-2 | MIT |
| libdrm-common | 2.4.124-2 | MIT |
| libdrm2 | 2.4.124-2 | MIT |
| libe-book-0.1-1 | 0.1.3-2+b4 | MPL-2.0 |
| libedit2 | 3.1-20250104-1 | BSD-3-clause |
| libelf1t64 | 0.192-4 | GPL-3+, LGPL-3+, GPL-2+, BSD-2-clause, GFDL-NIV-1.3, LGPL-2.1+, ... |
| libeot0 | 0.01-5+b2 | MPL-2.0, GPL-2+, other |
| libepoxy0 | 1.5.10-2 | Expat |
| libepubgen-0.1-1 | 0.1.1-1+b2 | MPL-2.0, other |
| libetonyek-0.1-1 | 0.1.12-1 | MPL 2.0 |
| libexpat1 | 2.9.0-1~deb13u1 | MIT |
| libexttextcat-2.0-0 | 3.4.7-1+b1 | All rights reserved. |
| libexttextcat-data | 3.4.7-1 | All rights reserved. |
| libffi8 | 3.4.8-2 | Expat, X11, GPL-2+, GPL-3+, MPL-1.1, LGPL-2.1+, ... |
| libflac14 | 1.5.0+ds-2 | GPL-2+, LGPL-2.1+, GFDL-1.1+, BSD-3-clause, LGPL-2+, Public-domain, ... |
| libfontconfig1 | 2.15.0-2.3 | see copyright file |
| libfontenc1 | 1:1.1.8-1+b2 | MIT |
| libfreehand-0.1-1 | 0.1.2-3+b1 | MPL-2.0, MPL-1.1 \| GPL-3+ \| LGPL-3+ |
| libfreetype6 | 2.13.3+dfsg-1+deb13u1 | FTL, Expat, BSD-3-Clause, FSFAP, GPL-3+, GPL-2+, ... |
| libfribidi0 | 1.0.16-1 | LGPL-2.1+ |
| libgbm1 | 25.0.7-2+deb13u1 | MIT, GPL-2, GPL-1+, BSD-3-google, Khronos, Apache-2.0, ... |
| libgcc-s1 | 14.2.0-19 | GPL-3, LGPL, MIT, BSD |
| libgcrypt20 | 1.11.0-7+deb13u1 | GPL-2, LGPL, MIT, BSD |
| libgdbm6t64 | 1.24-2 | GPL-3+, GPL-2+, GFDL-NIV-1.3+ |
| libgdk-pixbuf-2.0-0 | 2.42.12+dfsg-4+deb13u1 | LGPL-2+, LGPL-2.1+, CC0-1.0, GPL-2+ |
| libgdk-pixbuf2.0-common | 2.42.12+dfsg-4+deb13u1 | LGPL-2+, LGPL-2.1+, CC0-1.0, GPL-2+ |
| libgfortran5 | 14.2.0-19 | GPL-3, LGPL, MIT, BSD |
| libgl1 | 1.7.0-1+b2 | MIT, Apache-2.0, public-domain, GPL-3+, BSD-1-clause, GPL |
| libgl1-mesa-dri | 25.0.7-2+deb13u1 | MIT, GPL-2, GPL-1+, BSD-3-google, Khronos, Apache-2.0, ... |
| libglib2.0-0t64 | 2.84.4-3~deb13u5 | LGPL-2.1+, old-glib-tests, AFL-2.0, Janik-permissive, LGPL-2+, CC0-1.0, ... |
| libglvnd0 | 1.7.0-1+b2 | MIT, Apache-2.0, public-domain, GPL-3+, BSD-1-clause, GPL |
| libglx-mesa0 | 25.0.7-2+deb13u1 | MIT, GPL-2, GPL-1+, BSD-3-google, Khronos, Apache-2.0, ... |
| libglx0 | 1.7.0-1+b2 | MIT, Apache-2.0, public-domain, GPL-3+, BSD-1-clause, GPL |
| libgmp10 | 2:6.3.0+dfsg-3 | GPL-2+, LGPL-3+, GPL-3+, GPL-3+ with Bison exception |
| libgnutls30t64 | 3.8.9-3+deb13u4 | * Redistribution, use in source, binary forms, with, without, Public domain., ... |
| libgomp1 | 14.2.0-19 | GPL-3, LGPL, MIT, BSD |
| libgpg-error0 | 1.51-4 | LGPL-2.1+, BSD-3-clause, g10-permissive, GPL-3+ |
| libgpgme11t64 | 1.24.2-3 | LGPL-2.1+, LGPL-3+, GPL-2+, GPL-3+, LGPL-2+ |
| libgpgmepp6t64 | 1.24.2-3 | LGPL-2.1+, LGPL-3+, GPL-2+, GPL-3+, LGPL-2+ |
| libgraphite2-3 | 1.3.14-2+deb13u1 | LGPL-2.1+, MPL-1.1, GPL-2+, public-domain, Artistic, GPL-1+, ... |
| libgs-common | 10.05.1~dfsg-1+deb13u3 | AGPL-3+, FTL, none, BSD-3-Clause~Adobe, GPL-2, LGPL-2.1, ... |
| libgs10 | 10.05.1~dfsg-1+deb13u3 | AGPL-3+, FTL, none, BSD-3-Clause~Adobe, GPL-2, LGPL-2.1, ... |
| libgs10-common | 10.05.1~dfsg-1+deb13u3 | AGPL-3+, FTL, none, BSD-3-Clause~Adobe, GPL-2, LGPL-2.1, ... |
| libgssapi-krb5-2 | 1.21.3-5+deb13u1 | GPL-2, MIT, BSD |
| libgtk-3-0t64 | 3.24.49-3 | LGPL-2+, LGPL-2.1+, Expat, GPL-3+, CC-BY-SA-4.0, unencumbered, ... |
| libgtk-3-common | 3.24.49-3 | LGPL-2+, LGPL-2.1+, Expat, GPL-3+, CC-BY-SA-4.0, unencumbered, ... |
| libharfbuzz-icu0 | 10.2.0-1+deb13u1 | MIT, Unicode, ISC, Apache-2.0, OFL-1.1, Monotype, ... |
| libharfbuzz-subset0 | 10.2.0-1+deb13u1 | MIT, Unicode, ISC, Apache-2.0, OFL-1.1, Monotype, ... |
| libharfbuzz0b | 10.2.0-1+deb13u1 | MIT, Unicode, ISC, Apache-2.0, OFL-1.1, Monotype, ... |
| libheif-plugin-dav1d | 1.23.6-2~deb13u1 | LGPL-3+, BSD-2-clause, GPL-3+, Expat, BSD-4-Clause-UC, BSD-3-clause, ... |
| libheif-plugin-libde265 | 1.23.6-2~deb13u1 | LGPL-3+, BSD-2-clause, GPL-3+, Expat, BSD-4-Clause-UC, BSD-3-clause, ... |
| libheif1 | 1.23.6-2~deb13u1 | LGPL-3+, BSD-2-clause, GPL-3+, Expat, BSD-4-Clause-UC, BSD-3-clause, ... |
| libhogweed6t64 | 3.10.1-1 | LGPL-3+, GPL-2+, LGPL-2+, Expat, GPL-3+ with Autoconf exception, public-domain, ... |
| libhunspell-1.7-0 | 1.7.2+really1.7.2-10+b4 | MPL 1.1/GPL 2.0/LGPL 2.1 |
| libhyphen0 | 2.8.8-7+b2 | GPL-2+, LGPL-2.1+, MPL-1.1+ |
| libice6 | 2:1.1.1-1 | see copyright file |
| libicu76 | 76.1-4 | MIT, GPL-3 |
| libidn12 | 1.43-1 | GPL-3+, LGPL-3+, GPL-2+, GFDL-NIV-1.3+, FSFAP, Expat, ... |
| libidn2-0 | 2.3.8-2 | GPL-3+, LGPL-3+, GPL-2+, Expat, Unicode |
| libijs-0.35 | 0.35-15.2 | Expat, GPL-2+ with Autoconf exception, GAP~configure, GAP, Expat~X with X exception, GAP~Makefile.in, ... |
| libjbig0 | 2.1-6.1+b2 | GPL-2+ |
| libjbig2dec0 | 0.20-1+deb13u1 | AGPL-3+, LGPL-2.1+, BSD-2-clause, public-domain, pubic-domain, GPL-3+ |
| libjpeg62-turbo | 1:2.1.5-4 | BSD-BY-LC-NE, Zlib, BSD-3-clause, Expat, NTP, zlib |
| libk5crypto3 | 1.21.3-5+deb13u1 | GPL-2, MIT, BSD |
| libkeyutils1 | 1.6.3-6 | GPL-2+, LGPL-2+ |
| libkrb5-3 | 1.21.3-5+deb13u1 | GPL-2, MIT, BSD |
| libkrb5support0 | 1.21.3-5+deb13u1 | GPL-2, MIT, BSD |
| libksba8 | 1.6.7-2+b1 | FSFUL, LGPL-2.1-or-later |
| liblangtag-common | 0.6.7-1 | LGPL \| MPL, GPL-2+ |
| liblangtag1 | 0.6.7-1+b2 | LGPL \| MPL, GPL-2+ |
| liblapack3 | 3.12.1-6 | BSD-3-clause, BSD-3-clause-intel |
| liblastlog2-2 | 2.41.5-0+deb13u1 | GPL-2+, GPL-2, GPL-3+, LGPL-2.1+, public-domain, BSD-4-clause, ... |
| liblcms2-2 | 2.16-2+deb13u2 | MIT, GPL-3, IJG, GPL-2+ |
| libldap2 | 2.6.10+dfsg-1 | OpenLDAP-2.8, FSF-unlimited, GPL-2+ with Autoconf exception, GPL-3+ with Autoconf exception, GPL-2+ with Libtool exception, GPL-3+ with Libtool exception, ... |
| liblerc4 | 4.0.0+ds-5 | Apache-2.0 |
| libllvm19 | 1:19.1.7-3+b1 | APACHE-2-LLVM-EXCEPTIONS, MIT, BSD-3-clause, solar-public-domain, Python, BSD-3-Clause |
| libltdl7 | 2.5.4-4 | GPL-2+, GFDL-NIV-1.3+ |
| liblz4-1 | 1.10.0-4 | GPL-2+, BSD-2-clause |
| liblzma5 | 5.8.1-1+deb13u2 | 0BSD, GPL-2+, LGPL-2.1+, FSFULLR, none, PD, ... |
| libmagic-mgc | 1:5.46-5 | BSD-2-Clause-alike, public-domain, BSD-2-Clause-netbsd, BSD-2-Clause-regents, MIT-Old-Style-with-legal-disclaimer-2 |
| libmagic1t64 | 1:5.46-5 | BSD-2-Clause-alike, public-domain, BSD-2-Clause-netbsd, BSD-2-Clause-regents, MIT-Old-Style-with-legal-disclaimer-2 |
| libmd0 | 1.1.0-2+b1 | BSD-3-clause, BSD-3-clause-Aaron-D-Gifford, BSD-2-clause, BSD-2-clause-NetBSD, ISC, Beerware, ... |
| libmd4c-html0 | 0.5.2-2+b1 | Expat, BSD-2-clause, CC-BY-SA-4.0 |
| libmd4c0 | 0.5.2-2+b1 | Expat, BSD-2-clause, CC-BY-SA-4.0 |
| libmhash2 | 0.9.9.9-10 | see copyright file |
| libminizip1t64 | 1:1.3.dfsg+really1.3.1-1+b1 | Zlib |
| libmount1 | 2.41.5-0+deb13u1 | GPL-2+, GPL-2, GPL-3+, LGPL-2.1+, public-domain, BSD-4-clause, ... |
| libmp3lame0 | 3.100-6+b3 | LGPL-2+, LGPL-2.1+, zlib/libpng, BSD-3-clause, GPL-1+ |
| libmpg123-0t64 | 1.32.10-1+deb13u1 | LGPL-2.1 |
| libmspub-0.1-1 | 0.1.4-3+b5 | MPL-2.0 |
| libmwaw-0.3-3 | 0.3.22-1+b2 | MPL2.0 \| LGPL-2+, BSD |
| libmythes-1.2-0 | 2:1.2.5-1+b2 | /* |
| libncursesw6 | 6.5+20250216-2 | MIT/X11, X11, BSD-3-clause |
| libnettle8t64 | 3.10.1-1 | LGPL-3+, GPL-2+, LGPL-2+, Expat, GPL-3+ with Autoconf exception, public-domain, ... |
| libnghttp2-14 | 1.64.0-1.1+deb13u1 | Expat, all-permissive, GPL-3+ with autoconf exception, MIT, BSD-2-clause |
| libnghttp3-9 | 1.15.0-1~bpo13+1 | MIT, FSFULLR, GPL-3+ with Autoconf generic exception, FSFUL, GPL-2+ with Autoconf generic exception, FSFAP, ... |
| libngtcp2-16 | 1.22.1-1~bpo13+1 | MIT, FSFULLR, GPL-3+ with Autoconf generic exception, FSFUL, GPL-2+ with Autoconf generic exception, ISC, ... |
| libngtcp2-crypto-gnutls8 | 1.22.1-1~bpo13+1 | MIT, FSFULLR, GPL-3+ with Autoconf generic exception, FSFUL, GPL-2+ with Autoconf generic exception, ISC, ... |
| libngtcp2-crypto-ossl0 | 1.22.1-1~bpo13+1 | MIT, FSFULLR, GPL-3+ with Autoconf generic exception, FSFUL, GPL-2+ with Autoconf generic exception, ISC, ... |
| libnpth0t64 | 1.8-3 | LGPL-2.1+ |
| libnspr4 | 2:4.36-1 | MPL-2.0 |
| libnss3 | 2:3.110-1+deb13u5 | MPL-2.0, Zlib, BSD-3, public-domain |
| libnumbertext-1.0-0 | 1.0.11-4+b2 | LGPL-3+, BSD-3-clause, CC-BY-SA-3.0, GPL-2+ |
| libnumbertext-data | 1.0.11-4 | LGPL-3+, BSD-3-clause, CC-BY-SA-3.0, GPL-2+ |
| libodfgen-0.1-1 | 0.1.8-2+b2 | MPL-2.0 \| LGPL-2+ |
| libogg0 | 1.3.5-3+b2 | BSD-3-clause, rfc3533-license, rfc5334-license |
| libopenh264-8 | 2.6.0+dfsg-2 | BSD-2-clause, Expat, Apache-2.0, MPL-2.0 |
| libopenjp2-7 | 2.5.3-2.1~deb13u2 | BSD-2, MIT, BSD-3, LIBPNG, ZLIB, LIBTIFF, ... |
| libopus0 | 1.5.2-2 | BSD-3-clause, BSD-2-clause |
| liborcus-0.21-0 | 0.21.0-4~bpo13+1 | MPL-2.0, MIT, GPL-2, GPL-3, other, GPL-3+ with autoconf exception, ... |
| liborcus-parser-0.21-0 | 0.21.0-4~bpo13+1 | MPL-2.0, MIT, GPL-2, GPL-3, other, GPL-3+ with autoconf exception, ... |
| libp11-kit0 | 0.25.5-3 | BSD-3-clause, FSFULLR, GPL-2+ with Autoconf-data exception, GPL-3+ with Autoconf-data exception, X11, ISC, ... |
| libpagemaker-0.0-0 | 0.0.4-1+b2 | MPL-2.0 |
| libpam-modules | 1.7.0-5 | BSD-3-clause, GPL, GPL-2, GPL-2+, GPL-3, GPL-3+ with Bison exception, ... |
| libpam-modules-bin | 1.7.0-5 | BSD-3-clause, GPL, GPL-2, GPL-2+, GPL-3, GPL-3+ with Bison exception, ... |
| libpam-runtime | 1.7.0-5 | BSD-3-clause, GPL, GPL-2, GPL-2+, GPL-3, GPL-3+ with Bison exception, ... |
| libpam-systemd | 257.13-1~deb13u1 | LGPL-2.1+, CC0-1.0, GPL-2 with Linux-syscall-note exception, Expat, public-domain, GPL-2+ |
| libpam0g | 1.7.0-5 | BSD-3-clause, GPL, GPL-2, GPL-2+, GPL-3, GPL-3+ with Bison exception, ... |
| libpango-1.0-0 | 1.56.3-1 | LGPL-2+, LGPL-2.1+, Example, TCL, Unicode, ICU, ... |
| libpangocairo-1.0-0 | 1.56.3-1 | LGPL-2+, LGPL-2.1+, Example, TCL, Unicode, ICU, ... |
| libpangoft2-1.0-0 | 1.56.3-1 | LGPL-2+, LGPL-2.1+, Example, TCL, Unicode, ICU, ... |
| libpaper2 | 2.2.5-0.3+b2 | Expat, public-domain, GPL-3+, GPL-2, GPL-2+, X11 |
| libpcre2-8-0 | 10.46-1~deb13u3 | BSD-3-clause, X11, BSD-2-clause, public-domain |
| libpcsclite1 | 2.3.3-1 | BSD-3-clause, ISC, MIT, GPL-3+ |
| libpixman-1-0 | 0.44.0-3 | MIT |
| libpng16-16t64 | 1.6.48-1+deb13u6 | libpng, expat, GPL-2+, BSD-like-with-advertising-clause, libpng OR Apache-2.0 OR BSD-3-clause, Apache-2.0, ... |
| libpoppler147 | 25.03.0-5+deb13u4 | GPL-2, GPL-3, Apache-2.0 |
| libproc2-0 | 2:4.0.4-9 | LGPL-2.1+, LGPL-2.0+, GPL-2.0+ |
| libpsl5t64 | 0.21.2-1.1+b1 | MIT, gnulib, Chromium |
| libpulse0 | 17.0+dfsg1-2+b1 | LGPL-2.1+, other, GPL-2+, LGPL-2+ |
| libpython3-stdlib | 3.13.5-1 | MIT |
| libpython3.13 | 3.13.5-2+deb13u5 | licenses and, Redistribution, use in source, binary forms, with, without, ... |
| libpython3.13-minimal | 3.13.5-2+deb13u5 | licenses and, Redistribution, use in source, binary forms, with, without, ... |
| libpython3.13-stdlib | 3.13.5-2+deb13u5 | licenses and, Redistribution, use in source, binary forms, with, without, ... |
| libqxp-0.0-0 | 0.0.2-1+b5 | MPL-2.0, other, GPL-2+ |
| libraptor2-0 | 2.0.16-6 | LGPL-2.1+, GPL-3+, GPL-2+, Apache-2.0, public-domain |
| librasqal3t64 | 0.9.33-2.1+b2 | LGPL-2.1+, GPL-2+, Apache-2.0+, public-domain |
| librdf0t64 | 1.0.17-4+b1 | LGPL, Apache-2.0 |
| libreadline8t64 | 8.2-6 | GPL-3+, GPL-2+, GFDL-NIV-1.3+, ISC-no-attribution, GPL-3 |
| libreoffice-base-core | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-calc-nogui | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-common | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-core-nogui | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-draw-nogui | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-impress-nogui | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-math-nogui | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-style-colibre | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-uiconfig-calc | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-uiconfig-common | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-uiconfig-draw | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-uiconfig-impress | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-uiconfig-math | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libreoffice-writer-nogui | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| librevenge-0.0-0 | 0.0.5-3+b2 | MPL-2.0, MPL-1.1 \| GPL-3+ \| LGPL-3+ |
| libsasl2-2 | 2.1.28+dfsg1-9 | BSD-3-Clause-Attribution, BSD-3-clause, BSD-2-clause, GPL-3+, GPL-3, BSD-4-clause-UC, ... |
| libsasl2-modules-db | 2.1.28+dfsg1-9 | BSD-3-Clause-Attribution, BSD-3-clause, BSD-2-clause, GPL-3+, GPL-3, BSD-4-clause-UC, ... |
| libseccomp2 | 2.6.0-2 | LGPL-2.1 |
| libselinux1 | 3.8.1-1 | public-domain, GPL-2 |
| libsemanage-common | 3.8.1-1 | LGPL-2.1+, GPL-2 |
| libsemanage2 | 3.8.1-1 | LGPL-2.1+, GPL-2 |
| libsensors-config | 1:3.6.2-2 | GPL-2+, LGPL-2.1+, GPL-2, Linux-man-pages-copyleft |
| libsensors5 | 1:3.6.2-2 | GPL-2+, LGPL-2.1+, GPL-2, Linux-man-pages-copyleft |
| libsepol2 | 3.8.1-1 | LGPL-2.1+, Zlib, GPL-2, GPL-2+ |
| libsharpyuv0 | 1.5.0-0.1 | BSD-3-Clause, Apache-2.0 |
| libsm6 | 2:1.2.6-1 | see copyright file |
| libsmartcols1 | 2.41.5-0+deb13u1 | GPL-2+, GPL-2, GPL-3+, LGPL-2.1+, public-domain, BSD-4-clause, ... |
| libsndfile1 | 1.2.2-2+deb13u1 | LGPL-2.1+, gsm, Apache-2.0, sun, GPL-2+, LGPL-2+, ... |
| libsqlite3-0 | 3.46.1-7+deb13u2 | public-domain, GPL-2+ |
| libssh2-1t64 | 1.11.1-1+deb13u2 | BSD3, ISC |
| libssl3t64 | 3.5.7-1~deb13u3 | Apache-2.0, Artistic, GPL-1+ |
| libstaroffice-0.0-0 | 0.0.7-1+b2 | MPL2.0 \| LGPL-2+, BSD |
| libstdc++6 | 14.2.0-19 | GPL-3, LGPL, MIT, BSD |
| libsuitesparseconfig7 | 1:7.10.1+dfsg-1 | LGPL-2.1+, BSD-3-clause, GPL-2+, Apache-2.0, BSD-2-clause, LPPL-1.0+, ... |
| libsystemd-shared | 257.13-1~deb13u1 | LGPL-2.1+, CC0-1.0, GPL-2 with Linux-syscall-note exception, Expat, public-domain, GPL-2+ |
| libsystemd0 | 257.13-1~deb13u1 | LGPL-2.1+, CC0-1.0, GPL-2 with Linux-syscall-note exception, Expat, public-domain, GPL-2+ |
| libtasn1-6 | 4.20.0-2+deb13u1 | GPL-3, LGPL |
| libtext-charwidth-perl | 0.04-11+b4 | Artistic, GPL-1+ |
| libtext-wrapi18n-perl | 0.06-10 | Artistic, GPL-1+ |
| libthai-data | 0.1.29-2 | LGPL-2.1+, GPL-2+ |
| libthai0 | 0.1.29-2+b1 | LGPL-2.1+, GPL-2+ |
| libtiff6 | 4.7.0-3+deb13u3 | Hylafax |
| libtinfo6 | 6.5+20250216-2 | MIT/X11, X11, BSD-3-clause |
| libudev1 | 257.13-1~deb13u1 | LGPL-2.1+, CC0-1.0, GPL-2 with Linux-syscall-note exception, Expat, public-domain, GPL-2+ |
| libunistring5 | 1.3-2 | GPL-3+, LGPL-3+, LGPL-2+, GFDL-1.3+, GFDL-1.2+, LGPL-3, ... |
| libuno-cppu3t64 | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libuno-cppuhelpergcc3-3t64 | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libuno-purpenvhelpergcc3-3t64 | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libuno-sal3t64 | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libuno-salhelpergcc3-3t64 | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| libuuid1 | 2.41.5-0+deb13u1 | GPL-2+, GPL-2, GPL-3+, LGPL-2.1+, public-domain, BSD-4-clause, ... |
| libvisio-0.1-1 | 0.1.7-1+b5 | MPL-2.0, MIT \| GPL-2 |
| libvorbis0a | 1.3.7-3 | BSD-3-Clause, RFC-special |
| libvorbisenc2 | 1.3.7-3 | BSD-3-Clause, RFC-special |
| libvulkan1 | 1.4.309.0-1 | Apache-2.0, MIT |
| libwayland-client0 | 1.23.1-3 | X11 |
| libwayland-cursor0 | 1.23.1-3 | X11 |
| libwayland-egl1 | 1.23.1-3 | X11 |
| libwayland-server0 | 1.23.1-3 | X11 |
| libwebp7 | 1.5.0-0.1 | BSD-3-Clause, Apache-2.0 |
| libwpd-0.10-10 | 0.10.3-2+b2 | MPL-2.0 \| LGPL-2+ |
| libwpg-0.3-3 | 0.3.4-3+b2 | MPL-2.0 \| LGPL-2.1+ |
| libwps-0.4-4 | 0.4.14-2+b2 | MPL-2.0, LGPL-2.1+ |
| libx11-6 | 2:1.8.12-1 | MIT, BSD |
| libx11-data | 2:1.8.12-1 | MIT, BSD |
| libx11-xcb1 | 2:1.8.12-1 | MIT, BSD |
| libxau6 | 1:1.0.11-1 | see copyright file |
| libxaw7 | 2:1.0.16-1 | MIT |
| libxcb-dri3-0 | 1.17.0-2+b1 | MIT |
| libxcb-glx0 | 1.17.0-2+b1 | MIT |
| libxcb-present0 | 1.17.0-2+b1 | MIT |
| libxcb-randr0 | 1.17.0-2+b1 | MIT |
| libxcb-render0 | 1.17.0-2+b1 | MIT |
| libxcb-shape0 | 1.17.0-2+b1 | MIT |
| libxcb-shm0 | 1.17.0-2+b1 | MIT |
| libxcb-sync1 | 1.17.0-2+b1 | MIT |
| libxcb-xfixes0 | 1.17.0-2+b1 | MIT |
| libxcb1 | 1.17.0-2+b1 | MIT |
| libxcomposite1 | 1:0.4.6-1 | MIT |
| libxcursor1 | 1:1.2.3-1 | see copyright file |
| libxdamage1 | 1:1.1.6-1+b2 | see copyright file |
| libxdmcp6 | 1:1.1.5-1 | see copyright file |
| libxext6 | 2:1.3.4-1+b3 | MIT |
| libxfixes3 | 1:6.0.0-2+b4 | MIT |
| libxft2 | 2.3.6-1+b4 | see copyright file |
| libxi6 | 2:1.8.2-1 | MIT |
| libxinerama1 | 2:1.1.4-3+b4 | MIT |
| libxkbcommon0 | 1.7.0-2 | MIT |
| libxkbfile1 | 1:1.1.0-1+b4 | see copyright file |
| libxml2 | 2.12.7+dfsg+really2.9.14-2.1+deb13u3 | MIT-1, ISC |
| libxmlsec1t64 | 1.2.41-1+b1 | MIT |
| libxmlsec1t64-nss | 1.2.41-1+b1 | MIT |
| libxmu6 | 2:1.1.3-3+b4 | MIT |
| libxmuu1 | 2:1.1.3-3+b4 | MIT |
| libxnvctrl0 | 535.171.04-1+b2 | GPL-2, Expat, other-MetroLink, other-XFree, Expat-Precision, Expat-RedHat |
| libxpm4 | 1:3.5.17-1+deb13u1 | MIT |
| libxrandr2 | 2:1.5.4-1+b3 | see copyright file |
| libxrender1 | 1:0.9.12-1 | see copyright file |
| libxshmfence1 | 1.3.3-1 | see copyright file |
| libxslt1.1 | 1.1.35-1.2+deb13u3 | MIT |
| libxt6t64 | 1:1.2.1-1.2+b2 | MIT |
| libxtst6 | 2:1.2.5-1 | MIT |
| libxv1 | 2:1.0.11-1.1+b3 | All Rights Reserved |
| libxxf86dga1 | 2:1.1.5-1+b3 | MIT |
| libxxf86vm1 | 1:1.1.4-1+b4 | MIT |
| libxxhash0 | 0.8.3-2 | BSD-2-clause, GPL-2+ |
| libyajl2 | 2.1.0-5+b2 | ISC |
| libz3-4 | 4.13.3-1 | Expat, GPL-2+ |
| libzmf-0.0-0 | 0.0.2-1+b9 | MPL-2.0, other, GPL-2+ |
| libzstd1 | 1.5.7+dfsg-1 | BSD-3-clause, GPL-2, zlib, Expat |
| libzxcvbn0 | 2.5+dfsg-2+b2 | Expat, BSD-3-clause, CC-BY-SA-3.0, public-domain |
| login | 1:4.16.0-2+really2.41.5-0+deb13u1 | GPL-2+, GPL-2, GPL-3+, LGPL-2.1+, public-domain, BSD-4-clause, ... |
| login.defs | 1:4.17.4-2 | BSD-3-clause, GPL-1, GPL-2+ |
| mawk | 1.3.4.20250131-1 | GPL-2.0-only, X11, CC-BY-3.0 |
| media-types | 13.0.0 | ad-hoc |
| mesa-libgallium | 25.0.7-2+deb13u1 | MIT, GPL-2, GPL-1+, BSD-3-google, Khronos, Apache-2.0, ... |
| mount | 2.41.5-0+deb13u1 | GPL-2+, GPL-2, GPL-3+, LGPL-2.1+, public-domain, BSD-4-clause, ... |
| ncurses-base | 6.5+20250216-2 | MIT/X11, X11, BSD-3-clause |
| ncurses-bin | 6.5+20250216-2 | MIT/X11, X11, BSD-3-clause |
| netbase | 6.5 | GPL-2 |
| openjdk-21-jre-headless | 21.0.13+9-1~deb13u2 | GPL2 with Classpath exception, BSD-3-Clause, MIT, LGPL-2.1 |
| openssl | 3.5.7-1~deb13u3 | Apache-2.0, Artistic, GPL-1+ |
| openssl-provider-legacy | 3.5.7-1~deb13u3 | Apache-2.0, Artistic, GPL-1+ |
| passwd | 1:4.17.4-2 | BSD-3-clause, GPL-1, GPL-2+ |
| perl-base | 5.40.1-6+deb13u1 | GPL-1+, Artistic, Expat, REGCOMP, and GPL-1+, GPL-3+-WITH-BISON-EXCEPTION, ... |
| pinentry-curses | 1.3.1-2 | GPL-2+, GPL-2, X11, LGPL-3+ |
| poppler-data | 0.4.12-1 | BSD-3-cluase, MIT, GPL-2, AGPL-3+ |
| procps | 2:4.0.4-9 | LGPL-2.1+, LGPL-2.0+, GPL-2.0+ |
| python3 | 3.13.5-1 | MIT |
| python3-minimal | 3.13.5-1 | MIT |
| python3-uno | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| python3.13 | 3.13.5-2+deb13u5 | licenses and, Redistribution, use in source, binary forms, with, without, ... |
| python3.13-minimal | 3.13.5-2+deb13u5 | licenses and, Redistribution, use in source, binary forms, with, without, ... |
| readline-common | 8.2-6 | GPL-3+, GPL-2+, GFDL-NIV-1.3+, ISC-no-attribution, GPL-3 |
| sed | 4.9-2+deb13u1 | GPL-3+, X11, GFDL-NIV-1.3+, ISC, BSD-4-clause-UC, BSL-1, ... |
| sensible-utils | 0.0.25 | GPL-2+, All-permissive, configure, installsh |
| shared-mime-info | 2.4-5+b2 | GPL-2 |
| sqv | 1.3.0-3+b2 | LGPL-2.0-or-later |
| systemd | 257.13-1~deb13u1 | LGPL-2.1+, CC0-1.0, GPL-2 with Linux-syscall-note exception, Expat, public-domain, GPL-2+ |
| systemd-sysv | 257.13-1~deb13u1 | LGPL-2.1+, CC0-1.0, GPL-2 with Linux-syscall-note exception, Expat, public-domain, GPL-2+ |
| sysvinit-utils | 3.14-4 | GPL-2.0+, LGPL-2.1+, GPL-3.0, GPL-2.0 |
| tar | 1.35+dfsg-3.1 | GPL-3+, GPL-3+ with Bison exception, LGPL-2.1+, LGPL-3+, GPL-2+ |
| tini | 0.19.0-3+b8 | Expat |
| tzdata | 2026e-0+deb13u1 | public-domain |
| ucf | 3.0052 | GPL-2 |
| uno-libs-private | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| ure | 4:26.8.2.2-2~bpo13+1 | MPL-2.0, Apache-2.0, CC0-1.0, GPL-2+, CC-BY-SA-3.0, GPL-3+, ... |
| util-linux | 2.41.5-0+deb13u1 | GPL-2+, GPL-2, GPL-3+, LGPL-2.1+, public-domain, BSD-4-clause, ... |
| x11-common | 1:7.7+24+deb13u1 | GPL-2, MIT |
| x11-utils | 7.7+7 | MIT |
| xdg-utils | 1.2.1-2 | Expat |
| xfonts-encodings | 1:1.0.4-2.2 | see copyright file |
| xfonts-utils | 1:7.7+7 | MIT, BSD |
| xkb-data | 2.42-1 | MIT |
| zlib1g | 1:1.3.dfsg+really1.3.1-1+b1 | Zlib |
