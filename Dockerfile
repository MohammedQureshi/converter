# syntax=docker/dockerfile:1.7
#
# PDF/A-1b conversion service. Everything the service needs at runtime (engines, fonts, ICC
# profile, browser, JRE, validator) is baked in here. Nothing is downloaded when it runs.
#
#   docker build -t pdfa-converter .                         # production image (default target)
#   docker build --target test -t pdfa-converter:test .      # adds tests and test dependencies
#
# Internal mirrors, for builds with no internet access:
#
#   docker build \
#     --build-arg PYTHON_IMAGE=registry.internal/python:3.12.16-slim-trixie \
#     --build-arg APT_MIRROR=https://apt.internal \
#     --build-arg PIP_INDEX_URL=https://pypi.internal/simple \
#     --build-arg PIP_TRUSTED_HOST=pypi.internal \
#     --build-arg VERAPDF_URL=https://files.internal/verapdf-greenfield-1.30.3-installer.zip \
#     -t pdfa-converter .
#
# APT_MIRROR replaces http://deb.debian.org, so it must serve both /debian and /debian-security.
#
# Debian removes superseded versions from its mirrors, so an "apt version not found" build
# error means a pin needs bumping, usually for a security update. See "Monthly patching" in
# the README. For repeatable deployments, build once and promote the image by digest.

# 3.12.16-slim-trixie, multi-arch index digest (linux/amd64 and linux/arm64).
ARG PYTHON_IMAGE=python:3.12.16-slim-trixie@sha256:b18b261e1b4974b4f321451ad5251ded85abb22c2b8b262da527dda1d031ab30
ARG APT_MIRROR=http://deb.debian.org
ARG PIP_INDEX_URL=https://pypi.org/simple
ARG PIP_TRUSTED_HOST=
ARG LIBHEIF_VERSION=1.23.6-2~deb13u1
ARG JRE_VERSION=21.0.13+9-1~deb13u2

# ---------------------------------------------------------------------------
# python-deps: application venv and unoserver.
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS python-deps
ARG APT_MIRROR
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
ARG LIBHEIF_VERSION
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
COPY docker/use-mirror.sh /usr/local/bin/use-mirror.sh
COPY requirements.lock requirements-tools.lock /tmp/
# pillow-heif is compiled against Debian's libheif, because its wheel bundles an x265 HEVC
# encoder. The runtime image ships decoders only (libheif + libde265).
RUN sh /usr/local/bin/use-mirror.sh "$APT_MIRROR" \
    && apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
        gcc libc6-dev pkg-config "libheif-dev=${LIBHEIF_VERSION}" >/dev/null \
    && if [ -z "$PIP_TRUSTED_HOST" ]; then unset PIP_TRUSTED_HOST; fi \
    && python -m venv /opt/venv \
    && /opt/venv/bin/pip install --quiet --require-hashes --prefer-binary --no-binary pillow-heif -r /tmp/requirements.lock \
    # unoserver runs under Debian's /usr/bin/python3, the only interpreter that can import
    # LibreOffice's `uno` module, so it lives outside the 3.12 venv.
    && pip install --quiet --no-deps --target=/opt/unoserver unoserver==3.7 \
    # Only used to generate THIRD_PARTY_LICENSES.md; never reaches the final image.
    && python -m venv /opt/tools \
    && /opt/tools/bin/pip install --quiet --require-hashes -r /tmp/requirements-tools.lock \
    && find /opt/venv /opt/unoserver -type d -name __pycache__ -prune -exec rm -rf {} +

# ---------------------------------------------------------------------------
# verapdf: installed with a throwaway JRE; only the result is copied forward.
# Used under the MPL-2.0 option of its GPL-3.0+ / MPL-2.0 dual licence.
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS verapdf
ARG APT_MIRROR
ARG JRE_VERSION
ARG VERAPDF_VERSION=1.30.3
ARG VERAPDF_URL=https://software.verapdf.org/rel/1.30/verapdf-greenfield-1.30.3-installer.zip
ARG VERAPDF_SHA256=b512bf24945503a33fc10738ecffc1f2dccaaf8593a448e94ee9ac86a9559a59
COPY docker/use-mirror.sh /usr/local/bin/use-mirror.sh
COPY docker/verapdf-auto-install.xml /tmp/auto-install.xml
RUN sh /usr/local/bin/use-mirror.sh "$APT_MIRROR" \
    && apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
        curl unzip "openjdk-21-jre-headless=${JRE_VERSION}" >/dev/null \
    && curl -fsSL -o /tmp/verapdf.zip "$VERAPDF_URL" \
    && echo "${VERAPDF_SHA256}  /tmp/verapdf.zip" | sha256sum -c - \
    && unzip -q /tmp/verapdf.zip -d /tmp/vp \
    && java -jar "/tmp/vp/verapdf-greenfield-${VERAPDF_VERSION}/verapdf-izpack-installer-${VERAPDF_VERSION}.jar" /tmp/auto-install.xml \
    && test -x /opt/verapdf/verapdf \
    && rm -rf /opt/verapdf/Uninstaller

# ---------------------------------------------------------------------------
# system: pinned Debian packages. Everything comes from one apt mirror, including Chromium.
# ---------------------------------------------------------------------------
FROM ${PYTHON_IMAGE} AS system
ARG APT_MIRROR
ARG LIBHEIF_VERSION
ARG JRE_VERSION
# LibreOffice is pinned to a release series, not an exact version. Debian keeps only the
# latest backport in its index and uploads reach each architecture at different times, so an
# exact pin stops building within hours of an upload (this happened during development).
# The exact version installed is recorded in /srv/versions.txt and the SBOM.
ARG LO_SERIES=4:26.8.*
ARG CHROMIUM_VERSION=156.0.8078.79-1~deb13u1
COPY docker/use-mirror.sh /usr/local/bin/use-mirror.sh
# --no-install-recommends also keeps out libheif-plugin-x265, which libheif only recommends.
RUN sh /usr/local/bin/use-mirror.sh "$APT_MIRROR" \
    && printf 'path-exclude=/usr/share/doc/*\npath-include=/usr/share/doc/*/copyright\npath-exclude=/usr/share/man/*\npath-exclude=/usr/share/locale/*\npath-include=/usr/share/locale/en*\n' > /etc/dpkg/dpkg.cfg.d/01-slim \
    && mkdir -p /usr/share/man/man1 \
    && apt-get update -qq \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends -t trixie-backports \
        "libreoffice-writer-nogui=${LO_SERIES}" \
        "libreoffice-calc-nogui=${LO_SERIES}" \
        "libreoffice-impress-nogui=${LO_SERIES}" \
        "libreoffice-draw-nogui=${LO_SERIES}" \
        "libreoffice-math-nogui=${LO_SERIES}" \
        "python3-uno=${LO_SERIES}" \
        >/dev/null \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq --no-install-recommends \
        "chromium=${CHROMIUM_VERSION}" \
        ghostscript=10.05.1~dfsg-1+deb13u3 \
        libmagic1t64=1:5.46-5 \
        "libheif1=${LIBHEIF_VERSION}" \
        "libheif-plugin-libde265=${LIBHEIF_VERSION}" \
        "libheif-plugin-dav1d=${LIBHEIF_VERSION}" \
        libcairo2=1.18.4-1+b1 \
        "openjdk-21-jre-headless=${JRE_VERSION}" \
        tini=0.19.0-3+b8 \
        fontconfig=2.15.0-2.3 \
        fonts-liberation=1:2.1.5-3 \
        fonts-crosextra-carlito=20230309-2 \
        fonts-crosextra-caladea=20200211-2 \
        fonts-dejavu-core=2.37-8 \
        fonts-dejavu-extra=2.37-8 \
        fonts-noto-core=20201225-2 \
        fonts-noto-cjk=1:20240730+repack1-1 \
        >/dev/null \
    && ! dpkg-query -W -f='${Package}\n' | grep -E 'x265|mscorefonts' \
    && rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# ---------------------------------------------------------------------------
# app-core: everything except test tooling and the generated licence file.
# ---------------------------------------------------------------------------
FROM system AS app-core
COPY --from=python-deps /opt/venv /opt/venv
COPY --from=python-deps /opt/unoserver /opt/unoserver
COPY --from=verapdf /opt/verapdf /opt/verapdf
COPY docker/ /srv/docker/

ENV PATH=/opt/venv/bin:/opt/verapdf:$PATH \
    PYTHONPATH=/srv \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

RUN set -eu; \
    # Stays empty: Playwright drives Debian's chromium and never downloads a browser.
    mkdir -p /opt/ms-playwright; \
    # The ICC profile is found at build time; the build fails rather than ship without one.
    mkdir -p /opt/pdfa; \
    icc="$(find /usr/share -type f -iname 'srgb.icc' | head -n1)"; \
    test -n "$icc"; \
    cp "$icc" /opt/pdfa/srgb.icc; \
    cp /srv/docker/PDFA_def.ps /opt/pdfa/PDFA_def.ps; \
    # Optional custom fonts are picked up from this directory (mount a volume there).
    mkdir -p /fonts/custom; \
    cp /srv/docker/99-custom-fonts.conf /etc/fonts/conf.d/99-custom-fonts.conf; \
    fc-cache -f >/dev/null; \
    # Bake a first-run LibreOffice profile so pool instances skip profile creation.
    soffice --headless --norestore --nologo --nofirststartwizard \
        --terminate_after_init -env:UserInstallation=file:///opt/lo-template >/dev/null 2>&1 || true; \
    test -d /opt/lo-template/user; \
    cp /srv/docker/registrymodifications.xcu /opt/lo-template/user/registrymodifications.xcu; \
    # Precompile so worker startup does not pay for bytecode generation.
    /opt/venv/bin/python -m compileall -q /opt/venv/lib/python3.12/site-packages >/dev/null 2>&1 || true; \
    # Archive veraPDF's loaded classes (AppCDS), which cuts each validation's JVM startup
    # from about 0.66s to 0.42s. A JVM that cannot use the archive simply ignores it.
    gs -q -dSAFER -dBATCH -dNOPAUSE -dNOOUTERSAVE --permit-file-read=/opt/pdfa/ -sDEVICE=pdfwrite -dPDFA=1 \
        -dPDFACompatibilityPolicy=1 -sColorConversionStrategy=RGB -sProcessColorModel=DeviceRGB -sOutputFile=/tmp/cds.pdf \
        /opt/pdfa/PDFA_def.ps -c "/Helvetica findfont 12 scalefont setfont 72 72 moveto (sample) show showpage"; \
    JAVA_OPTS="-XX:TieredStopAtLevel=1 -XX:+UseSerialGC -XX:ArchiveClassesAtExit=/opt/verapdf/verapdf.jsa" \
        verapdf --flavour 1b --format json /tmp/cds.pdf >/dev/null 2>&1; \
    test -s /opt/verapdf/verapdf.jsa; \
    # Non-root runtime user.
    groupadd --gid 10001 converter; \
    useradd --uid 10001 --gid 10001 --no-create-home --home-dir /tmp/home --shell /usr/sbin/nologin converter; \
    chmod +x /srv/docker/entrypoint.sh; \
    chmod -R a+rX /opt /srv /fonts; \
    # Record exact engine versions for support and audit.
    { \
        echo "libreoffice: $(dpkg-query -W -f='${Version}' libreoffice-core-nogui)"; \
        echo "chromium: $(dpkg-query -W -f='${Version}' chromium)"; \
        echo "ghostscript: $(dpkg-query -W -f='${Version}' ghostscript)"; \
        echo "libheif: $(dpkg-query -W -f='${Version}' libheif1)"; \
        echo "java: $(dpkg-query -W -f='${Version}' openjdk-21-jre-headless)"; \
        echo "verapdf: 1.30.3"; \
        echo "python: $(/opt/venv/bin/python -V | cut -d' ' -f2)"; \
        echo "playwright: $(/opt/venv/bin/playwright --version | cut -d' ' -f2)"; \
    } > /srv/versions.txt; \
    cat /srv/versions.txt; \
    # Nothing the build wrote to /tmp may survive: it would be root-owned at runtime.
    rm -rf /tmp/* /tmp/.[!.]* /root/.cache

COPY app/ /srv/app/

ENV HOME=/tmp/home \
    XDG_CACHE_HOME=/tmp/home/.cache \
    PYTHONDONTWRITEBYTECODE=1 \
    JAVA_OPTS="-XX:TieredStopAtLevel=1 -XX:+UseSerialGC -Xshare:auto -XX:SharedArchiveFile=/opt/verapdf/verapdf.jsa"

USER 10001:10001
WORKDIR /srv
EXPOSE 8080
ENTRYPOINT ["/usr/bin/tini", "--", "/srv/docker/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--timeout-graceful-shutdown", "30"]
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health/ready', timeout=8).status == 200 else 1)"]

# ---------------------------------------------------------------------------
# licenses: generates THIRD_PARTY_LICENSES.md. The tools stay in this stage.
# ---------------------------------------------------------------------------
FROM app-core AS licenses
USER root
COPY --from=python-deps /opt/tools /opt/tools
RUN HOME=/root /opt/tools/bin/python /srv/docker/generate_licenses.py /THIRD_PARTY_LICENSES.md

# ---------------------------------------------------------------------------
# test: runtime contents plus pytest and fixture generators.
# ---------------------------------------------------------------------------
FROM app-core AS test
ARG PIP_INDEX_URL
ARG PIP_TRUSTED_HOST
USER root
COPY --from=licenses /THIRD_PARTY_LICENSES.md /srv/THIRD_PARTY_LICENSES.md
COPY requirements-test.lock /tmp/requirements-test.lock
RUN if [ -z "$PIP_TRUSTED_HOST" ]; then unset PIP_TRUSTED_HOST; fi \
    && HOME=/root XDG_CACHE_HOME=/root/.cache /opt/venv/bin/pip install --quiet --disable-pip-version-check --require-hashes --prefer-binary --no-deps -r /tmp/requirements-test.lock \
    && rm -rf /tmp/* /root/.cache
COPY tests/ /srv/tests/
COPY pytest.ini /srv/pytest.ini
USER 10001:10001

# ---------------------------------------------------------------------------
# runtime: the production image. Keep this stage last so it is the default target.
# ---------------------------------------------------------------------------
FROM app-core AS runtime
USER root
COPY --from=licenses /THIRD_PARTY_LICENSES.md /srv/THIRD_PARTY_LICENSES.md
USER 10001:10001
