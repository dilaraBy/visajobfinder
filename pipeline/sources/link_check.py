"""Optional dead-link checking for public job listings.

Phase 4 requires dead/stale links to be tracked. This is opt-in (it makes one
network request per job) and is injected into the build as a callable so it can
be mocked in tests and disabled by default. Failures never raise: an unreachable
URL is recorded as ``ok: False`` so a flaky source can never break the build.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, Optional


LinkChecker = Callable[[Optional[str]], Dict[str, Any]]


def _now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def check_url(url: Optional[str], timeout: int = 10) -> Dict[str, Any]:
    """Check a single URL and return a status block.

    Tries a lightweight HEAD first; some hosts reject HEAD, so a GET fallback is
    used on 4xx/405. Any network error is captured, not raised.
    """

    checked_at = _now()
    clean = (url or "").strip()
    if not clean:
        return {
            "url": url,
            "ok": False,
            "status_code": None,
            "checked_at": checked_at,
            "error": "missing_url",
        }

    for method in ("HEAD", "GET"):
        try:
            request = urllib.request.Request(clean, method=method)
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = getattr(response, "status", None) or response.getcode()
                return {
                    "url": clean,
                    "ok": 200 <= int(status) < 400,
                    "status_code": int(status),
                    "checked_at": checked_at,
                    "error": None,
                }
        except urllib.error.HTTPError as exc:
            # HEAD rejected (e.g. 403/405) — retry with GET before giving up.
            if method == "HEAD" and exc.code in (403, 405, 400, 501):
                continue
            return {
                "url": clean,
                "ok": False,
                "status_code": int(exc.code),
                "checked_at": checked_at,
                "error": f"http_error_{exc.code}",
            }
        except Exception as exc:  # noqa: BLE001 - never break the build on a link check
            if method == "HEAD":
                continue
            return {
                "url": clean,
                "ok": False,
                "status_code": None,
                "checked_at": checked_at,
                "error": type(exc).__name__,
            }

    return {
        "url": clean,
        "ok": False,
        "status_code": None,
        "checked_at": checked_at,
        "error": "unreachable",
    }


def summarise_links(jobs: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    """Aggregate per-job link_status blocks into pipeline-level counts."""

    checked = ok = dead = 0
    for job in jobs:
        status = job.get("link_status")
        if not status:
            continue
        checked += 1
        if status.get("ok"):
            ok += 1
        else:
            dead += 1
    return {"checked": checked, "ok": ok, "dead": dead}
