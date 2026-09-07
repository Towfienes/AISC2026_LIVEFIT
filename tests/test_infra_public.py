"""Gate hạ tầng công khai (gói E): Caddy là cổng vào duy nhất, backup tự xác minh.

Ba lớp kiểm tra, không cần Docker daemon:

1. ``docker-compose.yml``: có service ``caddy`` publish 80/443; ``api``/``web``
   KHÔNG publish cổng ra host (chỉ expose nội bộ) — người xem đi qua Caddy nên
   shortlink ``/r/{code}`` đo được click thật (runbook §1.1, nguyên tắc 4).
2. ``docker/Caddyfile``: route ``/r/*``, ``/api/*`` (cắt tiền tố), ``/ws/*``
   về api; mặc định về web.
3. ``docker/backup.sh``: chạy THẬT script với ``pg_dump``/``pg_restore`` giả để
   chứng minh hành vi. Sự cố gốc: pipeline ``pg_dump | gzip`` không có pipefail
   — pg_dump chết nhưng gzip sống vẫn log OK với dump hỏng.
4. Runbook: lệnh ingest ghi trong tài liệu phải khớp CLI thật (cùng tinh thần
   contract test web↔API).
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "docker-compose.yml"
DEV_PORTS = ROOT / "docker-compose.dev-ports.yml"
CADDYFILE = ROOT / "docker" / "Caddyfile"
BACKUP_SH = ROOT / "docker" / "backup.sh"
RUNBOOK = ROOT / "ops" / "runbooks" / "quy-trinh-phien.md"

# ---------------------------------------------------------------------------
# 1 + 2. Topology: Caddy là cổng vào duy nhất
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


def test_caddy_publishes_80_443_and_mounts_caddyfile(compose):
    caddy = compose["services"].get("caddy")
    assert caddy is not None, "docker-compose.yml thiếu service caddy — không có cổng vào công khai"
    assert str(caddy["image"]).startswith("caddy:2"), f"image lạ: {caddy['image']}"
    published = [str(p) for p in caddy.get("ports", [])]
    assert any(p.startswith("80:") for p in published), f"caddy không mở cổng 80: {published}"
    assert any(p.startswith("443:") for p in published), f"caddy không mở cổng 443: {published}"
    volumes = [str(v) for v in caddy.get("volumes", [])]
    assert any("docker/Caddyfile" in v for v in volumes), f"caddy không mount Caddyfile: {volumes}"


def test_api_and_web_are_internal_only(compose):
    for name in ("api", "web"):
        svc = compose["services"][name]
        assert "ports" not in svc, (
            f"service {name} vẫn publish cổng ra host {svc.get('ports')} — "
            "phải đi qua caddy; cổng dev nằm trong docker-compose.dev-ports.yml"
        )
        assert svc.get("expose"), f"service {name} thiếu expose nội bộ"


def test_dev_ports_override_binds_loopback_only():
    data = yaml.safe_load(DEV_PORTS.read_text(encoding="utf-8"))
    ports = [str(p) for svc in data["services"].values() for p in svc.get("ports", [])]
    assert ports, "file DEV_PORTS không mở cổng nào — vô dụng"
    bad = [p for p in ports if not p.startswith("127.0.0.1:")]
    assert not bad, f"cổng dev phải bind 127.0.0.1, không đưa ra Internet: {bad}"


def test_caddyfile_routes_match_the_real_api_surface():
    text = CADDYFILE.read_text(encoding="utf-8")
    assert "{$DOMAIN" in text, "Caddyfile không đọc DOMAIN từ môi trường"
    # /r/{code} — biến kết quả chính — phải tới api, giữ nguyên đường dẫn.
    assert re.search(r"handle /r/\*\s*\{\s*reverse_proxy api:8000", text), (
        "Caddyfile không route /r/* về api — shortlink đo click chết"
    )
    # REST đi qua tiền tố /api và PHẢI cắt tiền tố (FastAPI phục vụ ở gốc).
    assert re.search(r"handle_path /api/\*\s*\{\s*reverse_proxy api:8000", text), (
        "Caddyfile phải dùng handle_path /api/* (cắt tiền tố) về api"
    )
    assert re.search(r"handle /ws/\*\s*\{\s*reverse_proxy api:8000", text), (
        "Caddyfile không route WebSocket /ws/* về api"
    )
    # Mặc định: giao diện Next.js.
    assert re.search(r"handle\s*\{\s*reverse_proxy web:3000", text), (
        "Caddyfile thiếu route mặc định về web:3000"
    )


def test_env_example_documents_domain():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^DOMAIN=", text, re.M), ".env.example thiếu biến DOMAIN"


# ---------------------------------------------------------------------------
# 3. backup.sh: chạy thật với pg_dump/pg_restore giả
# ---------------------------------------------------------------------------


def _find_bash() -> str | None:
    """Bash POSIX thật (Git Bash trên Windows) — bash WSL trong System32 không dùng được."""
    if os.name != "nt":
        return shutil.which("bash")
    git = shutil.which("git")
    if git:
        git_root = Path(git).resolve().parent.parent
        for cand in (git_root / "bin" / "bash.exe", git_root / "usr" / "bin" / "bash.exe"):
            if cand.exists():
                return str(cand)
    cand = shutil.which("bash")
    if cand and "system32" not in cand.lower():
        return cand
    return None


BASH = _find_bash()
needs_bash = pytest.mark.skipif(BASH is None, reason="cần bash (Git Bash) để chạy backup.sh")


def _posix(p: Path) -> str:
    """Đường dẫn kiểu POSIX cho Git Bash trên Windows (D:\\x -> /d/x)."""
    s = str(p).replace("\\", "/")
    return re.sub(r"^([A-Za-z]):/", lambda m: f"/{m.group(1).lower()}/", s)


def _write_stub(stub_dir: Path, name: str, body: str) -> None:
    f = stub_dir / name
    f.write_text("#!/bin/sh\n" + body, encoding="utf-8", newline="\n")
    f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _run_backup(
    tmp_path: Path, pg_dump_body: str, pg_restore_body: str = "exit 0"
) -> tuple[subprocess.CompletedProcess, Path]:
    """Chạy backup.sh với sleep/pg_dump/pg_restore giả; trả (proc, thư mục backup)."""
    stubs = tmp_path / "stubs"
    stubs.mkdir()
    _write_stub(stubs, "sleep", "exit 0")  # bỏ chờ tới BACKUP_HOUR
    _write_stub(stubs, "pg_dump", pg_dump_body)
    _write_stub(stubs, "pg_restore", pg_restore_body)
    backups = tmp_path / "backups"
    cmd = (
        f'PATH="{_posix(stubs)}:$PATH" BACKUP_DIR="{_posix(backups)}" '
        f'PGDATABASE=livelift_test PGHOST=stub bash "{_posix(BACKUP_SH)}"'
    )
    proc = subprocess.run(
        [BASH, "-c", cmd],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=os.environ.copy(),
    )
    return proc, backups


@needs_bash
def test_backup_dead_pg_dump_is_failed_not_ok(tmp_path):
    """Sự cố gốc: pg_dump chết giữa chừng, gzip vẫn OK → trước đây log OK."""
    proc, backups = _run_backup(tmp_path, pg_dump_body="printf half-a-dump\nexit 3\n")
    out = proc.stdout + proc.stderr
    assert proc.returncode == 3, f"phải thoát với mã lỗi của pg_dump (3), được: {proc.returncode}"
    assert "FAILED" in out, f"thiếu dòng FAILED trong log: {out!r}"
    assert "OK " not in out, f"dump hỏng mà vẫn log OK: {out!r}"
    assert not list(backups.glob("*")), "không được giữ lại file dump hỏng"


@needs_bash
def test_backup_unreadable_dump_fails_verify_and_is_removed(tmp_path):
    """pg_dump 'thành công' nhưng dump không đọc lại được → verify phải chặn."""
    proc, backups = _run_backup(
        tmp_path,
        pg_dump_body="printf not-a-real-dump\nexit 0\n",
        pg_restore_body="exit 2",
    )
    out = proc.stdout + proc.stderr
    assert proc.returncode == 2, f"phải thoát với mã lỗi verify (2), được: {proc.returncode}"
    assert "FAILED" in out, f"thiếu dòng FAILED: {out!r}"
    assert "pg_restore" in out, f"log verify không nêu pg_restore: {out!r}"
    assert "OK " not in out
    assert not list(backups.glob("*")), "file .tmp hỏng phải bị xóa"


@needs_bash
def test_backup_ok_only_after_verify_and_failure_keeps_old_dump(tmp_path):
    """Lần 1 tốt → log OK, giữ dump; lần 2 pg_dump chết → thoát, dump cũ còn nguyên."""
    marker = tmp_path / "ran_once"
    proc, backups = _run_backup(
        tmp_path,
        pg_dump_body=(
            f'if [ -e "{_posix(marker)}" ]; then exit 9; fi\n'
            f'touch "{_posix(marker)}"\n'
            "printf dump-bytes\nexit 0\n"
        ),
    )
    out = proc.stdout + proc.stderr
    assert "OK " in out, f"lần chạy tốt phải log OK: {out!r}"
    assert proc.returncode == 9, f"lần hỏng phải thoát mã 9, được: {proc.returncode}"
    dumps = list(backups.glob("livelift-*.dump.gz"))
    assert len(dumps) == 1, f"dump tốt của lần 1 phải còn nguyên: {dumps}"
    assert not list(backups.glob("*.tmp"))


# ---------------------------------------------------------------------------
# 4. Runbook: lệnh ingest trong tài liệu khớp CLI thật
# ---------------------------------------------------------------------------


def _option_strings(parser) -> set[str]:
    return {s for action in parser._actions for s in action.option_strings}


def test_runbook_documents_ingest_runner_and_spool_replay():
    text = RUNBOOK.read_text(encoding="utf-8")
    assert "python -m livelift.ingest.runner" in text, "runbook T−2h thiếu lệnh chạy runner"
    for flag in ("--platform", "--source-id", "--session-id", "--api-url"):
        assert flag in text, f"runbook thiếu tham số {flag} của runner"
    assert "heartbeat" in text, "runbook thiếu hướng dẫn kiểm tra heartbeat"
    assert "python -m livelift.ingest.spool_replay" in text, (
        "runbook thiếu lệnh spool_replay backfill khi runner chết"
    )
    assert "data/spool/" in text, "runbook không chỉ ra vị trí file spool"


def test_runbook_flags_exist_on_the_real_clis():
    from livelift.ingest.runner import build_parser as runner_parser
    from livelift.ingest.spool_replay import build_parser as replay_parser

    runner_opts = _option_strings(runner_parser())
    for flag in ("--platform", "--source-id", "--session-id", "--api-url"):
        assert flag in runner_opts, f"runbook dẫn tham số {flag} nhưng runner không có"
    assert "--api-base" in _option_strings(replay_parser()), (
        "runbook dẫn --api-base nhưng spool_replay không có"
    )
