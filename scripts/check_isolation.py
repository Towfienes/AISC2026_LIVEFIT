#!/usr/bin/env python3
"""CI gate: enforce import isolation between the core and VLiveBench collectors.

Architecture rule (README "Nguyên tắc cách ly", HARNESS §2): ``collectors/tiktok_public/``
is an independent sub-project (own requirements, own process). If the public-room reader
breaks — TikTok changing its protocol, the reverse-engineered library dying — the core
experiment system must be unaffected.

Two directional rules are enforced by scanning source text with regexes:

1. No module under ``src/`` may import ``collectors`` (``import collectors...`` or
   ``from collectors...``). The core must never depend on the collectors.
2. No module under ``collectors/`` may import ``livelift``, with ONE documented
   exception: ``livelift.ingest.pii``. The PII scrubber must run before ANY write or
   transmit, everywhere — including inside collectors (hard project rule 1). Allowing
   exactly this module keeps the PII gate single-sourced without coupling collectors
   to the rest of the core.

Exit code 0 with an OK summary when clean; exit code 1 with the offending file:line
list otherwise. A missing ``collectors/`` directory is reported as skipped, not an error.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "src"
COLLECTORS_DIR = REPO_ROOT / "collectors"

SKIP_DIR_NAMES = {".git", ".venv", "venv", "__pycache__", "node_modules", ".mypy_cache"}

# Rule 1: any import of the collectors package from core code.
RE_IMPORT_COLLECTORS = re.compile(r"^\s*(?:import\s+collectors\b|from\s+collectors\b)")

# Rule 2: any import of livelift from collectors code.
RE_IMPORT_LIVELIFT = re.compile(
    r"^\s*(?:import\s+(?P<imp>livelift[\w.]*)|from\s+(?P<frm>livelift[\w.]*)\s+import\s+(?P<names>.+))"
)

ALLOWED_MODULE = "livelift.ingest.pii"


def iter_py_files(root: Path) -> list[Path]:
    """Yield all .py files under root, skipping virtualenv/cache directories."""
    files: list[Path] = []
    for path in sorted(root.rglob("*.py")):
        if any(part in SKIP_DIR_NAMES for part in path.relative_to(root).parts):
            continue
        files.append(path)
    return files


def _livelift_import_allowed(match: re.Match[str]) -> bool:
    """Return True when a livelift import inside collectors/ is the PII exception."""
    module = match.group("imp") or match.group("frm")
    if module == ALLOWED_MODULE or module.startswith(ALLOWED_MODULE + "."):
        return True
    # `from livelift.ingest import pii` (possibly aliased) is also the PII package.
    if module == "livelift.ingest" and match.group("names") is not None:
        names = match.group("names").split("#", 1)[0]
        imported = [n.strip().split(" as ")[0].strip("() ") for n in names.split(",")]
        return all(name == "pii" for name in imported if name)
    return False


def scan_src() -> list[str]:
    """Rule 1: report core files importing the collectors package."""
    violations: list[str] = []
    for path in iter_py_files(SRC_DIR):
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if RE_IMPORT_COLLECTORS.match(line):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}:{lineno}: {line.strip()}")
    return violations


def scan_collectors() -> list[str]:
    """Rule 2: report collectors files importing livelift (except the PII filter)."""
    violations: list[str] = []
    for path in iter_py_files(COLLECTORS_DIR):
        text = path.read_text(encoding="utf-8", errors="replace")
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = RE_IMPORT_LIVELIFT.match(line)
            if match and not _livelift_import_allowed(match):
                rel = path.relative_to(REPO_ROOT)
                violations.append(f"{rel}:{lineno}: {line.strip()}")
    return violations


def main() -> int:
    if not SRC_DIR.is_dir():
        print(f"check_isolation: src/ not found under {REPO_ROOT}", file=sys.stderr)
        return 1

    src_files = iter_py_files(SRC_DIR)
    src_violations = scan_src()

    if COLLECTORS_DIR.is_dir():
        collectors_files = iter_py_files(COLLECTORS_DIR)
        collectors_violations = scan_collectors()
        collectors_note = f"{len(collectors_files)} files scanned under collectors/"
    else:
        collectors_files = []
        collectors_violations = []
        collectors_note = "collectors/ not present — rule 2 skipped"

    failed = False
    if src_violations:
        failed = True
        print("FAIL: core code imports the collectors package (rule 1):")
        for v in src_violations:
            print(f"  {v}")
    if collectors_violations:
        failed = True
        print(
            "FAIL: collectors code imports livelift beyond the allowed "
            f"{ALLOWED_MODULE} exception (rule 2):"
        )
        for v in collectors_violations:
            print(f"  {v}")

    if failed:
        return 1

    print(
        "OK: import isolation holds — "
        f"{len(src_files)} files scanned under src/ (0 collectors imports); "
        f"{collectors_note} (0 disallowed livelift imports; "
        f"allowed exception: {ALLOWED_MODULE})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
