"""Console output that survives a Windows terminal.

Windows consoles default to a legacy code page (cp1252 here), so printing any
Vietnamese character raises UnicodeEncodeError and the CLI dies mid-report —
`livelift-qc` crashed on its own PASS/FAIL lines (incident 27/08). Every CLI
calls :func:`configure` before printing.

We reconfigure stdout/stderr to UTF-8 rather than stripping diacritics: the
output is Vietnamese by design, and a mangled quality report is worse than
none. If the stream cannot be reconfigured (a pipe on an exotic platform), we
fall back to replacing unencodable characters so the process still finishes.
"""

from __future__ import annotations

import contextlib
import sys


def configure() -> None:
    """Make stdout/stderr able to carry Vietnamese text. Safe to call twice."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        # Detached or already-wrapped stream — nothing safe to do there.
        with contextlib.suppress(ValueError, OSError):
            reconfigure(encoding="utf-8", errors="replace")
