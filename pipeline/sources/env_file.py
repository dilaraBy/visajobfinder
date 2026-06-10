"""Minimal, dependency-free .env loader for local credential loading.

The source adapters read API credentials from ``os.environ`` (for example
``REED_API_KEY`` and ``ADZUNA_APP_ID`` / ``ADZUNA_APP_KEY``). For local runs we
load a gitignored ``.env`` file into the environment before the adapters run.
No third-party dependency is used so the pipeline stays transparent and easy to
audit. Secrets are never written to disk by this module and never logged.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, MutableMapping, Optional


def parse_env_text(text: str) -> Dict[str, str]:
    """Parse ``KEY=VALUE`` lines from .env-style text.

    Blank lines and ``#`` comments are ignored. A leading ``export`` is
    allowed. Surrounding single or double quotes are stripped from values.
    """

    values: Dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        values[key] = value
    return values


def load_env_file(
    path: Path,
    *,
    override: bool = False,
    environ: Optional[MutableMapping[str, str]] = None,
) -> Dict[str, str]:
    """Load ``KEY=VALUE`` pairs from ``path`` into the environment.

    Existing environment variables are preserved unless ``override`` is True, so
    real shell/CI environment variables take precedence over the file. A missing
    file is not an error and returns an empty mapping. Returns the keys that were
    applied (values included for the caller's own diagnostics; do not log them).
    """

    env = os.environ if environ is None else environ
    if not path.exists():
        return {}

    values = parse_env_text(path.read_text(encoding="utf-8"))
    applied: Dict[str, str] = {}
    for key, value in values.items():
        if override or key not in env:
            env[key] = value
            applied[key] = value
    return applied
