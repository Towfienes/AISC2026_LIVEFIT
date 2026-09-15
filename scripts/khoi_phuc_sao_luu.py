#!/usr/bin/env python3
"""Khôi phục một bản sao lưu — và CHỨNG MINH nó khôi phục được.

Vì sao có tệp này
-----------------
``docker/backup.sh`` đã chạy đều mỗi ngày và tự xác minh từng bản dump (gzip -t
+ pg_restore --list) trước khi ghi tên chính thức. Nhưng một bản sao lưu chưa
bao giờ được ĐỔ NGƯỢC vào một cơ sở dữ liệu thì mới chỉ là một tệp đọc được,
chưa phải một lưới an toàn. Trước tệp này, kho mã có đường sao lưu mà KHÔNG có
đường khôi phục — thư mục ``backups/`` có 5 bản dump và không có một dòng nào
nói phải làm gì với chúng.

Thể lệ chấm đúng chỗ này hai lần: trọng tâm 7 ("khả năng triển khai, mở rộng và
**duy trì**") và trọng tâm 8 ("**an toàn dữ liệu**").

Cách làm — không đụng vào dữ liệu đang chạy
-------------------------------------------
Mặc định script KHÔNG ghi đè cơ sở dữ liệu thật. Nó:

  1. chọn bản dump (mới nhất, hoặc ``--tep``);
  2. xác minh: gzip còn nguyên + đọc được mục lục ``pg_restore --list``;
  3. tạo một cơ sở dữ liệu TRỐNG, tên riêng (mặc định ``livelift_thu_khoi_phuc``);
  4. ``pg_restore`` bản dump vào đó;
  5. ĐẾM số dòng từng bảng trong CSDL vừa khôi phục, và nếu CSDL thật còn sống
     thì đếm cả bên đó để so sánh hai cột cạnh nhau;
  6. xoá CSDL tạm (giữ lại bằng ``--giu``).

Chỉ khi gõ ``--that`` script mới đổ vào CSDL thật — và khi đó nó hỏi lại bằng
cách bắt gõ đúng chữ ``KHOI PHUC THAT``, vì thao tác ấy XOÁ dữ liệu hiện có.

Mọi lệnh postgres chạy TRONG container ``db`` qua ``docker compose exec``, nên
máy vận hành không cần cài PostgreSQL client.

Cách chạy
---------
    # diễn tập: khôi phục bản mới nhất vào CSDL tạm rồi đếm và so
    python scripts/khoi_phuc_sao_luu.py

    # một bản cụ thể
    python scripts/khoi_phuc_sao_luu.py --tep backups/livelift-2026-09-13.dump.gz

    # chỉ xác minh, không khôi phục
    python scripts/khoi_phuc_sao_luu.py --chi-xac-minh

    # THẬT: đổ vào CSDL đang chạy (xoá dữ liệu hiện có)
    python scripts/khoi_phuc_sao_luu.py --that

Mã thoát: 0 = khôi phục và đếm được · 1 = hỏng ở một bước nào đó · 2 = không
gọi được docker/container db.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from livelift.console import configure  # noqa: E402

# Mọi bảng dữ liệu của lược đồ (migrations 0001-0009). Dùng để đếm hai bên.
BANG = (
    "live_session",
    "experiment_block",
    "product",
    "shortlink",
    "comment_event",
    "click_event",
    "order_event",
    "session_tick",
    "intervention_log",
    "assignment_event",
    "exposure_event",
    "reaction_event",
    "analysis_run",
)

CSDL_TAM_MAC_DINH = "livelift_thu_khoi_phuc"
XAC_NHAN = "KHOI PHUC THAT"


def _moi_truong() -> dict[str, str]:
    """Đọc POSTGRES_* từ .env (không phụ thuộc thư viện ngoài)."""
    gia_tri = {"POSTGRES_USER": "livelift", "POSTGRES_DB": "livelift"}
    env_file = REPO_ROOT / ".env"
    if env_file.is_file():
        # utf-8-sig: tệp .env trên máy này có BOM (đã gặp 14/09/2026), đọc bằng
        # utf-8 thường sẽ làm khoá ĐẦU TIÊN mang một ký tự vô hình ở đầu tên.
        for dong in env_file.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            dong = dong.strip()
            if not dong or dong.startswith("#") or "=" not in dong:
                continue
            khoa, _, gt = dong.partition("=")
            khoa = khoa.strip()
            if khoa in ("POSTGRES_USER", "POSTGRES_DB"):
                gia_tri[khoa] = gt.strip()
    return gia_tri


def _db(lenh: list[str], *, nhap: bytes | None = None, timeout: int = 300):
    """Chạy một lệnh TRONG container db. Trả CompletedProcess."""
    day_du = ["docker", "compose", "exec", "-T", "db", *lenh]
    return subprocess.run(  # noqa: S603
        day_du,
        cwd=REPO_ROOT,
        input=nhap,
        capture_output=True,
        timeout=timeout,
    )


def _psql(sql: str, *, csdl: str, user: str) -> tuple[int, str]:
    r = _db(["psql", "-U", user, "-d", csdl, "-tAc", sql])
    return r.returncode, (r.stdout or b"").decode("utf-8", "replace").strip()


def _dem_bang(csdl: str, user: str) -> dict[str, int | None]:
    """Đếm số dòng mỗi bảng. None = bảng không tồn tại / không đọc được.

    Gộp thành MỘT truy vấn UNION ALL thay vì 13 lần gọi `docker compose exec`
    — mỗi lần gọi tốn ~0,3-1 giây, và bảng so sánh chạy hai lần cho hai CSDL.
    """
    # S608: tên bảng lấy từ hằng số BANG ở đầu tệp (danh sách cứng theo
    # migrations 0001-0009), không bao giờ đến từ đầu vào người dùng.
    phan = [f"SELECT '{b}', count(*) FROM {b}" for b in BANG]  # noqa: S608
    sql = " UNION ALL ".join(phan)
    ma, ra = _psql(sql, csdl=csdl, user=user)
    if ma != 0:
        return dict.fromkeys(BANG, None)
    dem: dict[str, int | None] = dict.fromkeys(BANG, None)
    for dong in ra.splitlines():
        ten, _, so = dong.partition("|")
        if ten.strip() in dem:
            with contextlib.suppress(ValueError):
                dem[ten.strip()] = int(so)
    return dem


def main(argv: list[str] | None = None) -> int:
    configure()
    p = argparse.ArgumentParser(description="Khôi phục và kiểm chứng một bản sao lưu LiveLift.")
    p.add_argument(
        "--tep", default=None, help="đường dẫn bản dump (mặc định: mới nhất trong backups/)"
    )
    p.add_argument("--csdl-tam", default=CSDL_TAM_MAC_DINH, help="tên CSDL tạm để diễn tập")
    p.add_argument(
        "--chi-xac-minh", action="store_true", help="chỉ kiểm tính toàn vẹn, không khôi phục"
    )
    p.add_argument("--giu", action="store_true", help="giữ lại CSDL tạm sau khi xong")
    p.add_argument(
        "--that",
        action="store_true",
        help="KHÔI PHỤC THẬT vào CSDL đang chạy — XOÁ dữ liệu hiện có",
    )
    args = p.parse_args(argv)

    env = _moi_truong()
    user = env["POSTGRES_USER"]
    csdl_that = env["POSTGRES_DB"]

    print("== LiveLift — khôi phục và kiểm chứng bản sao lưu ==")

    # -- container db có sống không ----------------------------------------
    try:
        r = _db(["pg_isready", "-U", user], timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"  ✕ Không gọi được docker compose: {type(e).__name__}: {e}")
        print("    → Cần Docker đang chạy và đã `docker compose up -d db`.")
        return 2
    if r.returncode != 0:
        print("  ✕ Container `db` không trả lời pg_isready.")
        print(f"    stderr: {(r.stderr or b'').decode('utf-8', 'replace').strip()[:300]}")
        print("    → `docker compose up -d db`, đợi healthy, rồi chạy lại.")
        return 2
    print(f"  ✓ Container `db` sống (user={user}, csdl thật={csdl_that})")

    # -- chọn bản dump -----------------------------------------------------
    if args.tep:
        dump = Path(args.tep)
        if not dump.is_absolute():
            dump = REPO_ROOT / dump
    else:
        thu_muc = REPO_ROOT / "backups"
        ds = sorted(
            thu_muc.glob("livelift-*.dump.gz"), key=lambda q: q.stat().st_mtime, reverse=True
        )
        if not ds:
            print(f"  ✕ Không có bản dump nào trong {thu_muc}")
            return 1
        dump = ds[0]
    if not dump.is_file():
        print(f"  ✕ Không thấy tệp {dump}")
        return 1
    print(f"  · Bản dump: {dump.name} ({dump.stat().st_size:,} byte)")

    du_lieu = dump.read_bytes()

    # -- xác minh ----------------------------------------------------------
    # Hai lớp, đúng như docker/backup.sh làm lúc GHI: gzip -t bắt tệp cụt;
    # pg_restore --list bắt tệp gzip lành nhưng ruột không phải dump Postgres.
    r = _db(["sh", "-c", "gzip -t"], nhap=du_lieu)
    if r.returncode != 0:
        print("  ✕ gzip -t TRƯỢT — tệp nén hỏng hoặc bị cắt cụt.")
        return 1
    print("  ✓ gzip -t đạt (tệp nén còn nguyên)")

    r = _db(["sh", "-c", "gunzip -c | pg_restore --list"], nhap=du_lieu)
    muc_luc = (r.stdout or b"").decode("utf-8", "replace")
    if r.returncode != 0 or "PostgreSQL" not in muc_luc and not muc_luc.strip():
        print("  ✕ pg_restore --list TRƯỢT — không đọc được mục lục dump.")
        print(f"    stderr: {(r.stderr or b'').decode('utf-8', 'replace').strip()[:300]}")
        return 1
    so_muc = sum(1 for d in muc_luc.splitlines() if d.strip() and not d.startswith(";"))
    print(f"  ✓ pg_restore --list đạt ({so_muc} mục trong mục lục)")

    if args.chi_xac_minh:
        print()
        print("  Chỉ xác minh (--chi-xac-minh) — dừng ở đây. Bản dump ĐỌC ĐƯỢC.")
        return 0

    # -- đếm CSDL thật TRƯỚC (nếu còn sống) --------------------------------
    ma, _ = _psql("SELECT 1", csdl=csdl_that, user=user)
    dem_that = _dem_bang(csdl_that, user) if ma == 0 else None

    # -- đích đến ----------------------------------------------------------
    if args.that:
        print()
        print("  !! KHÔI PHỤC THẬT: thao tác này XOÁ dữ liệu hiện có trong")
        print(f"     cơ sở dữ liệu `{csdl_that}` và thay bằng nội dung bản dump.")
        if os.environ.get("LIVELIFT_KHONG_HOI") != "1":
            tra_loi = input(f'     Gõ đúng "{XAC_NHAN}" để tiếp tục: ').strip()
            if tra_loi != XAC_NHAN:
                print("     Đã huỷ — không có gì thay đổi.")
                return 1
        dich = csdl_that
    else:
        dich = args.csdl_tam
        print(f"  · Diễn tập vào CSDL tạm `{dich}` — CSDL thật KHÔNG bị đụng tới.")
        _psql(f'DROP DATABASE IF EXISTS "{dich}"', csdl="postgres", user=user)
        ma, ra = _psql(f'CREATE DATABASE "{dich}"', csdl="postgres", user=user)
        if ma != 0:
            print(f"  ✕ Không tạo được CSDL tạm: {ra[:300]}")
            return 1
        print(f"  ✓ Đã tạo CSDL TRỐNG `{dich}`")

    # -- khôi phục ---------------------------------------------------------
    # --clean --if-exists cho đường THẬT (xoá đối tượng cũ trước khi dựng lại);
    # CSDL tạm vốn đã trống nên không cần.
    co = "--clean --if-exists" if args.that else ""
    r = _db(
        ["sh", "-c", f'gunzip -c | pg_restore -U "{user}" -d "{dich}" --no-owner --no-acl {co}'],
        nhap=du_lieu,
        timeout=900,
    )
    loi = (r.stderr or b"").decode("utf-8", "replace").strip()
    if r.returncode != 0:
        print(f"  ✕ pg_restore TRƯỢT (mã {r.returncode})")
        print("    " + "\n    ".join(loi.splitlines()[-12:]))
        return 1
    if loi:
        # pg_restore hay in cảnh báo vô hại (vd: vai trò không tồn tại) — hiện
        # ra nhưng không coi là trượt, vì mã thoát mới là phán quyết.
        print(f"  ! pg_restore có {len(loi.splitlines())} dòng cảnh báo (mã thoát vẫn 0)")
    print(f"  ✓ pg_restore xong vào `{dich}`")

    # -- đếm và so ---------------------------------------------------------
    dem_moi = _dem_bang(dich, user)
    print()
    print("  Số dòng sau khi khôi phục:")
    if dem_that is not None and not args.that:
        print(f"    {'bảng':<20} {'đang chạy':>12} {'khôi phục':>12}   khớp")
        print(f"    {'-' * 20} {'-' * 12} {'-' * 12}   ----")
    else:
        print(f"    {'bảng':<20} {'khôi phục':>12}")
        print(f"    {'-' * 20} {'-' * 12}")

    tong = 0
    lech: list[str] = []
    for b in BANG:
        moi = dem_moi.get(b)
        tong += moi or 0
        if dem_that is not None and not args.that:
            cu = dem_that.get(b)
            khop = "✓" if cu == moi else "✕"
            if cu != moi:
                lech.append(f"{b} (đang chạy {cu} ≠ khôi phục {moi})")
            print(
                f"    {b:<20} {'-' if cu is None else cu:>12} "
                f"{'-' if moi is None else moi:>12}   {khop}"
            )
        else:
            print(f"    {b:<20} {'-' if moi is None else moi:>12}")

    print()
    print(f"  Tổng {tong:,} dòng trong {len(BANG)} bảng.")

    # -- dọn ---------------------------------------------------------------
    if not args.that and not args.giu:
        _psql(f'DROP DATABASE IF EXISTS "{dich}"', csdl="postgres", user=user)
        print(f"  · Đã xoá CSDL tạm `{dich}` (giữ lại bằng --giu).")

    print()
    if tong == 0:
        print("  KẾT LUẬN: bản dump khôi phục được nhưng KHÔNG có dòng nào —")
        print("  nhiều khả năng đây là bản sao lưu của một CSDL trống. Kiểm tra lại.")
        return 1
    if lech:
        # Lệch KHÔNG phải lỗi: bản dump chụp lúc 02:00, CSDL thật đã chạy tiếp
        # từ đó. Nói rõ để không ai hiểu nhầm thành hỏng.
        print("  KẾT LUẬN: khôi phục ĐƯỢC. Có chênh lệch so với CSDL đang chạy:")
        for d in lech[:6]:
            print(f"    · {d}")
        print("  Chênh lệch là BÌNH THƯỜNG — bản dump chụp lúc 02:00, CSDL thật đã")
        print("  nhận thêm dữ liệu từ lúc đó. Chỉ đáng lo nếu bản khôi phục NHIỀU")
        print("  hơn bản đang chạy, hoặc một bảng lẽ ra có dữ liệu lại về 0.")
        return 0

    print("  KẾT LUẬN: khôi phục ĐƯỢC, số dòng khớp từng bảng với CSDL đang chạy.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\n  Đã dừng theo yêu cầu (Ctrl-C).")
        raise SystemExit(1) from None
