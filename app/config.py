"""Service configuration, read from environment variables (see README for the full list)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def effective_cpus() -> int:
    """CPUs this container may actually use.

    `os.cpu_count()` reports the host's CPUs and ignores cgroup quotas, so a default
    pool size based on it can start dozens of LibreOffice instances in a 2-CPU pod.
    """
    try:
        cpus = len(os.sched_getaffinity(0))
    except AttributeError:
        cpus = os.cpu_count() or 1
    try:
        quota, period = Path("/sys/fs/cgroup/cpu.max").read_text().split()
        if quota != "max":
            cpus = min(cpus, max(1, int(int(quota) / int(period))))
    except (OSError, ValueError):
        pass
    return max(1, cpus)


# Page sizes in PDF points.
PAGE_SIZES = {
    "A3": (841.89, 1190.55),
    "A4": (595.28, 841.89),
    "A5": (419.53, 595.28),
    "LETTER": (612.0, 792.0),
    "LEGAL": (612.0, 1008.0),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", env_ignore_empty=True)

    # Spec-defined settings
    api_key: str = ""
    max_upload_bytes: int = Field(default=5_242_880, gt=0)
    lo_pool_size: int = Field(default_factory=effective_cpus, gt=0)
    gs_concurrency: int = Field(default_factory=effective_cpus, gt=0)
    conversion_timeout_seconds: float = Field(default=60, gt=0)
    max_pages: int = Field(default=500, gt=0)
    validate_default: bool = True
    strict_validation: bool = False
    log_level: str = "INFO"
    default_page_size: str = "native"
    enable_msg: bool = True

    # Additional operational settings
    work_dir: Path = Path("/tmp/work")
    lo_run_dir: Path = Path("/tmp/lo")
    lo_base_port: int = 2100
    lo_max_conversions: int = Field(default=200, gt=0)
    lo_health_interval_seconds: float = Field(default=15, gt=0)
    ready_cache_seconds: float = Field(default=5, ge=0)
    chromium_concurrency: int = Field(default_factory=effective_cpus, gt=0)
    verapdf_concurrency: int = Field(default_factory=effective_cpus, gt=0)
    max_email_depth: int = Field(default=3, ge=0)
    max_email_attachments: int = Field(default=20, ge=0)
    max_image_pixels: int = Field(default=200_000_000, gt=0)
    max_uncompressed_bytes: int = Field(default=1_073_741_824, gt=0)
    engine_memory_limit_mb: int = Field(default=2048, ge=0)
    html_allow_inline_js: bool = False
    chromium_executable: Path = Path("/usr/bin/chromium")
    pdfa_def_path: Path = Path("/opt/pdfa/PDFA_def.ps")
    pdfa_icc_path: Path = Path("/opt/pdfa/srgb.icc")
    lo_template_dir: Path = Path("/opt/lo-template")
    lo_server_script: Path = Path("/srv/docker/lo_server.py")

    @field_validator("default_page_size")
    @classmethod
    def _check_page_size(cls, value: str) -> str:
        normalised = value.strip().upper()
        if normalised != "NATIVE" and normalised not in PAGE_SIZES:
            raise ValueError(f"must be 'native' or one of {sorted(PAGE_SIZES)}")
        return normalised

    @property
    def page_size_points(self) -> tuple[float, float] | None:
        """Configured page size in points; None means keep each source's native size."""
        return PAGE_SIZES.get(self.default_page_size)

    @property
    def fallback_page_name(self) -> str:
        """Page size for sources with no intrinsic size (HTML, text, CSV) in native mode."""
        return "A4" if self.default_page_size == "NATIVE" else self.default_page_size

    @property
    def memory_limit_bytes(self) -> int | None:
        return self.engine_memory_limit_mb * 1024 * 1024 if self.engine_memory_limit_mb else None


@lru_cache
def get_settings() -> Settings:
    return Settings()
