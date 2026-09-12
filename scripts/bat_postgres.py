#!/usr/bin/env python3
"""Bật kho bền vững (PostgreSQL) bằng MỘT lệnh, và nói rõ khi không bật được.

Vì sao có tệp này: đường Postgres đã tồn tại từ lâu nhưng phải gõ đúng ba việc
rời rạc (dựng container, chạy migrate, đặt **hai** biến môi trường khác nhau),
và biến quyết định lại không phải cái ai cũng đoán — ``DATABASE_URL`` chỉ nói
*ở đâu*, còn ``STORE_BACKEND`` mới quyết định *có dùng hay không* (sự cố
25/08/2026: API chạy trong Docker vẫn báo ``store_backend=memory`` dù đã có
``DATABASE_URL``). Bỏ sót một bước thì hệ thống vẫn chạy ngon lành và vẫn giữ
toàn bộ dữ liệu trong RAM — đúng cái bẫy đã làm mất 13 phiên live thật ngày
11/09/2026.

Chạy:

    .venv/Scripts/python scripts/bat_postgres.py

Mã thoát: 0 = kho bền vững đã sẵn sàng · 2 = không có Docker (script in sẵn
đường lui an toàn: kho memory + ảnh chụp) · 1 = có Docker nhưng dựng hỏng.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from livelift.config import get_settings  # noqa: E402
from livelift.console import configure  # noqa: E402

HEALTHY_TIMEOUT_S = 180


def _run(cmd: list[str], timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(  # noqa: S603 - lệnh cố định trong tệp này
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )


def _docker_ready() -> tuple[bool, str]:
    if shutil.which("docker") is None:
        return False, "không tìm thấy lệnh 'docker' trong PATH — Docker chưa được cài."
    probe = _run(["docker", "info", "--format", "{{.ServerVersion}}"], timeout=60)
    if probe.returncode != 0 or not probe.stdout.strip():
        return False, (
            "có lệnh 'docker' nhưng máy chủ Docker chưa chạy. Trên Windows: mở "
            "Docker Desktop và đợi biểu tượng chuyển xanh, rồi chạy lại script này."
        )
    return True, probe.stdout.strip()


def _wait_healthy(container: str, timeout_s: int) -> bool:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        probe = _run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", container], timeout=30
        )
        if probe.stdout.strip() == "healthy":
            return True
        time.sleep(2)
    return False


def _fallback_notice(interval_s: float, path: str) -> None:
    print()
    print("  ĐƯỜNG LUI AN TOÀN — kho memory + ảnh chụp định kỳ:")
    print("    Không có Postgres thì KHÔNG được chạy kho memory trần. Ảnh chụp đang")
    print(f"    bật sẵn theo mặc định: ghi {path} mỗi {interval_s:.0f} giây, tự nạp lại")
    print("    khi khởi động. Khởi động lại chỉ mất tối đa chu kỳ đó, không mất cả phiên.")
    print("    Kiểm tra bằng:  curl -s http://127.0.0.1:8000/health   → storage_mode")
    print("    Đọc thêm: docs/luu-tru-du-lieu.md")


def main(argv: list[str] | None = None) -> int:
    configure()
    parser = argparse.ArgumentParser(description="Bật PostgreSQL cho LiveLift")
    parser.add_argument("--container", default="livelift-db-1", help="tên container cơ sở dữ liệu")
    parser.add_argument("--skip-migrate", action="store_true")
    args = parser.parse_args(argv)

    settings = get_settings()
    print("== Bật kho bền vững (PostgreSQL) ==")

    ready, detail = _docker_ready()
    if not ready:
        print(f"  ✗ Docker KHÔNG dùng được: {detail}")
        _fallback_notice(settings.store_snapshot_interval_s, settings.store_snapshot_path)
        return 2
    print(f"  ✓ Docker đang chạy (máy chủ {detail})")

    up = _run(["docker", "compose", "up", "-d", "db"], timeout=600)
    if up.returncode != 0:
        print("  ✗ 'docker compose up -d db' thất bại:")
        print((up.stderr or up.stdout).strip()[:1500])
        print("    Gợi ý: .env phải có POSTGRES_PASSWORD (xem .env.example).")
        return 1
    print("  ✓ Đã dựng dịch vụ 'db'")

    if not _wait_healthy(args.container, HEALTHY_TIMEOUT_S):
        print(
            f"  ✗ Container {args.container} không đạt trạng thái healthy sau {HEALTHY_TIMEOUT_S}s"
        )
        print("    Xem nhật ký:  docker compose logs db --tail 50")
        return 1
    print(f"  ✓ {args.container} healthy — cổng 127.0.0.1:5432 đã mở")

    if not args.skip_migrate:
        migrate = _run([sys.executable, "-m", "livelift.dbops.migrate", "up"], timeout=300)
        if migrate.returncode != 0:
            print("  ✗ Chạy migrate thất bại:")
            print((migrate.stderr or migrate.stdout).strip()[:1500])
            return 1
        print(f"  ✓ Migrate xong: {migrate.stdout.strip() or 'không có migration mới'}")

    print()
    print("  Kho đã sẵn sàng. CÒN MỘT BIẾN NỮA — thiếu nó là vẫn chạy RAM:")
    print()
    print("    PowerShell:")
    print('      $env:STORE_BACKEND = "postgres"')
    print(f'      $env:DATABASE_URL  = "{settings.database_url}"')
    print("      .venv/Scripts/python -m uvicorn livelift.api.main:app --port 8000")
    print()
    print("    Bash:")
    print("      export STORE_BACKEND=postgres")
    print(f"      export DATABASE_URL='{settings.database_url}'")
    print("      .venv/Scripts/python -m uvicorn livelift.api.main:app --port 8000")
    print()
    print("  Xác nhận (đừng tin, hãy đo):")
    print("    curl -s http://127.0.0.1:8000/health    → storage_mode=postgres, durable=true")
    print("    .venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend postgres")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
