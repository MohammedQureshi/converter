"""Generates THIRD_PARTY_LICENSES.md at image build time.

Lists every Python package (pip-licenses), system package and font (dpkg data), plus the
components installed by other means. Debian's copyright files are free text in places, so
a package whose licence cannot be read is listed as "see copyright file", never guessed.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections import defaultdict
from importlib import metadata
from pathlib import Path

VENV_PYTHON = "/opt/venv/bin/python"
UNOSERVER_PATH = "/opt/unoserver"
LICENSE_LINE = re.compile(r"^License:\s*(\S.*)$", re.MULTILINE)
_NAMED_LICENSES = (
    ("GPL-3", re.compile(r"GNU General Public License.{0,60}version 3", re.I | re.S)),
    ("GPL-2", re.compile(r"GNU General Public License.{0,60}version 2", re.I | re.S)),
    ("LGPL", re.compile(r"GNU (Lesser|Library) General Public License", re.I)),
    ("MIT", re.compile(r"\bMIT License\b|Permission is hereby granted, free of charge", re.I)),
    ("BSD", re.compile(r"Redistribution and use in source and binary forms", re.I)),
    ("Apache-2.0", re.compile(r"Apache License,? Version 2", re.I)),
    ("OFL-1.1", re.compile(r"SIL Open Font License", re.I)),
)


def run(*argv: str) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def cell(text: object) -> str:
    return " ".join(str(text).split()).replace("|", "\\|")


def python_packages() -> list[dict]:
    raw = run(
        "/opt/tools/bin/pip-licenses",
        f"--python={VENV_PYTHON}",
        "--format=json",
        "--with-urls",
        "--from=mixed",
    )
    rows = [
        {"name": row["Name"], "version": row["Version"], "license": row["License"], "url": row["URL"]}
        for row in json.loads(raw)
        if row["Name"].lower() not in {"pip", "setuptools", "wheel"}
    ]
    # unoserver is installed outside the venv, for Debian's Python.
    for dist in metadata.distributions(path=[UNOSERVER_PATH]):
        info = dist.metadata
        license_text = info.get("License-Expression") or info.get("License") or ""
        if not license_text or len(license_text) > 60:
            classifiers = [c.split("::")[-1].strip() for c in info.get_all("Classifier", []) if c.startswith("License")]
            license_text = "; ".join(classifiers) or "UNKNOWN"
        rows.append({"name": info["Name"], "version": info["Version"], "license": license_text, "url": info.get("Home-page") or ""})
    return sorted(rows, key=lambda row: row["name"].lower())


def package_license(package: str) -> str:
    path = Path(f"/usr/share/doc/{package}/copyright")
    if not path.exists():
        # Binary packages built from one source sometimes share a copyright file by symlink;
        # otherwise there is nothing on disk to read.
        return "see Debian package"
    text = path.read_text(errors="replace")
    declared = []
    for value in LICENSE_LINE.findall(text):
        for name in re.split(r"\s+(?:or|and)\s+|,\s*", value.strip()):
            name = name.strip()
            if name and len(name) < 40 and name not in declared:
                declared.append(name)
    if declared:
        return ", ".join(declared[:6]) + (", ..." if len(declared) > 6 else "")
    found = [label for label, pattern in _NAMED_LICENSES if pattern.search(text)]
    return ", ".join(found) if found else "see copyright file"


def system_packages() -> list[dict]:
    rows = []
    for line in run("dpkg-query", "-W", "-f=${Package}\t${Version}\t${db:Status-Abbrev}\n").splitlines():
        package, version, status = line.split("\t")
        if status.startswith("ii"):
            rows.append({"name": package, "version": version, "license": package_license(package)})
    return rows


def fonts(packages: dict[str, dict]) -> list[dict]:
    entries = set()
    for line in run("fc-list", "--format=%{file}\t%{family}\n").splitlines():
        path, _, family = line.partition("\t")
        entries.add((path, family.split(",")[0]))
    owners: dict[str, str] = {}
    paths = sorted({path for path, _ in entries})
    for start in range(0, len(paths), 200):
        result = subprocess.run(["dpkg", "-S", *paths[start:start + 200]], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            owner, _, path = line.partition(": ")
            owners[path.strip()] = owner.split(":")[0].split(",")[0].strip()

    families: dict[tuple[str, str], int] = defaultdict(int)
    for path, family in entries:
        families[(owners.get(path, "unpackaged"), family)] += 1
    rows = []
    for (owner, family), count in sorted(families.items()):
        package = packages.get(owner, {})
        rows.append({"family": family, "package": owner, "version": package.get("version", ""), "license": package.get("license", ""), "files": count})
    return rows


OTHER_COMPONENTS = [
    (
        "veraPDF",
        "1.30.3",
        "MPL-2.0 (the MPL-2.0 option of its dual GPL-3.0+ / MPL-2.0 licence is chosen)",
        "https://verapdf.org",
    ),
]

HEADER = """# Third-party licences

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
"""


def main(out: str) -> None:
    system = system_packages()
    by_name = {row["name"]: row for row in system}
    python = python_packages()
    font_rows = fonts(by_name)

    lines = [HEADER]
    lines += ["## Other components", "", "| Component | Version | Licence | URL |", "|---|---|---|---|"]
    lines += [f"| {cell(n)} | {cell(v)} | {cell(l)} | {cell(u)} |" for n, v, l, u in OTHER_COMPONENTS]
    lines += ["", f"## Python packages ({len(python)})", "", "| Package | Version | Licence | URL |", "|---|---|---|---|"]
    lines += [f"| {cell(r['name'])} | {cell(r['version'])} | {cell(r['license'])} | {cell(r['url'])} |" for r in python]
    lines += ["", f"## Fonts ({len(font_rows)} families)", "", "| Family | Package | Version | Licence | Files |", "|---|---|---|---|---|"]
    lines += [f"| {cell(r['family'])} | {cell(r['package'])} | {cell(r['version'])} | {cell(r['license'])} | {r['files']} |" for r in font_rows]
    lines += ["", f"## System packages ({len(system)})", "", "| Package | Version | Licence |", "|---|---|---|"]
    lines += [f"| {cell(r['name'])} | {cell(r['version'])} | {cell(r['license'])} |" for r in system]
    Path(out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{out}: {len(python)} Python packages, {len(system)} system packages, {len(font_rows)} font families")


if __name__ == "__main__":
    main(sys.argv[1])
