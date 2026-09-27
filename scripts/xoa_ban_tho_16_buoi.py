"""Liệt kê — và CHỈ khi được lệnh rõ ràng thì xoá — bản thô còn định danh của tập 16 buổi.

Vì sao có tệp này (27/09/2026): hồ sơ dự án mục 3.3 (phương án A) cam kết chậm nhất
29/09/2026 xoá an toàn bản sao lưu dữ liệu gán nhãn TRƯỚC khi lọc lại (còn tên tài khoản
người bình luận — những người chưa đồng ý) và che tên tài khoản trong bản lưu nhật ký gốc
của công cụ AI. Việc xoá là không đảo ngược, nên mặc định tệp này chỉ LIỆT KÊ: đường dẫn,
số tệp, dung lượng — không mở, không in nội dung tệp nào.

    .venv/Scripts/python scripts/xoa_ban_tho_16_buoi.py              # chỉ liệt kê
    .venv/Scripts/python scripts/xoa_ban_tho_16_buoi.py --thuc-hien  # xoá, phải gõ xác nhận

Danh mục theo bảng kiểm kê ngày 25/09/2026 (hồ sơ mục 3.3):

- XOÁ: ``backup-labeling-2509/`` — bản thô duy nhất còn định danh ở dạng dữ liệu. Giữ lại
  ``_SHA256SUMS.txt`` (chỉ có băm, chứng minh từng có bản sao và bản nào đã bị xoá).
- CHE (tệp này KHÔNG đụng): ``prompt-log-goc/2026-09-15/``, ``prompt-log-goc/2026-09-25/``
  — bản lưu nhật ký gốc; phương án A che tên tài khoản bằng bộ lọc đã vá, không xoá (mất
  nguồn đối chiếu Prompt Log). Chỉ in số tệp, dung lượng để người làm biết phạm vi.
- KHÔNG BAO GIỜ XOÁ: ``dinh-danh-da-biet.sha256`` (băm tên tài khoản đã biết — công cụ kiểm
  mà ``xuat_prompt_log.py --doi-chieu`` cần), dữ liệu đã lọc ``livelift/data/labeling/``,
  bảng gán mù ``gan-mu-2509/`` (phương án A giữ phần đã lọc).

Xoá an toàn: ghi đè mỗi tệp bằng byte ngẫu nhiên cùng độ dài, ``fsync``, rồi xoá (không qua
Thùng rác); ghi nhật ký tên tệp + kích thước + SHA-256 trước khi xoá (không có nội dung).
Trên SSD ghi đè không bảo đảm tuyệt đối — chạy thêm ``cipher /w:D:\\`` sau khi xoá.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

GOC_KHO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC_KHO / "src"))

from livelift.console import configure  # noqa: E402

GOC_MAC_DINH = Path("D:/AISC2026")
CAU_XAC_NHAN = "XOA BAN THO"


@dataclass(frozen=True)
class MucTieu:
    duong_dan: str  # tương đối với --goc
    hanh_dong: str  # "xoa" | "che"
    ly_do: str


MUC_TIEU: tuple[MucTieu, ...] = (
    MucTieu(
        "backup-labeling-2509",
        "xoa",
        "bản sao dữ liệu gán nhãn TRƯỚC khi lọc lại (25/09): còn tên tài khoản người bình luận",
    ),
    MucTieu(
        "prompt-log-goc/2026-09-15",
        "che",
        "bản lưu nhật ký gốc Claude Code: kết quả công cụ trích bình luận còn tên tài khoản",
    ),
    MucTieu("prompt-log-goc/2026-09-25", "che", "như trên (bản lưu thứ hai)"),
)
#: Tên tệp trong mục "xoa" được GIỮ LẠI (chỉ chứa băm, không chứa dữ liệu).
GIU_LAI = frozenset({"_SHA256SUMS.txt"})
#: Không bao giờ xoá, kể cả khi ai đó thêm nhầm vào MUC_TIEU.
KHONG_BAO_GIO_XOA = frozenset({"dinh-danh-da-biet.sha256"})


@dataclass
class KiemKe:
    muc: MucTieu
    thu_muc: Path
    ton_tai: bool
    tep: list[Path]  # tệp sẽ xoá (mục "xoa") hoặc thuộc phạm vi che (mục "che")
    giu: list[Path]
    loi: list[str]

    @property
    def dung_luong(self) -> int:
        return sum(p.stat().st_size for p in self.tep)


def _la_lien_ket(p: Path) -> bool:
    return p.is_symlink() or bool(getattr(os.path, "isjunction", lambda _x: False)(p))


def kiem_ke(goc: Path, muc_tieu: tuple[MucTieu, ...] = MUC_TIEU) -> list[KiemKe]:
    """Đếm tệp từng mục. Không mở tệp nào. Mục nguy hiểm (liên kết, nằm trong kho mã, trỏ ra
    ngoài gốc) được ghi lỗi và sẽ bị từ chối khi xoá."""
    goc = goc.resolve()
    ra = []
    for m in muc_tieu:
        tm = goc / m.duong_dan
        loi: list[str] = []
        tep: list[Path] = []
        giu: list[Path] = []
        if not tm.exists():
            ra.append(KiemKe(m, tm, False, [], [], []))
            continue
        if _la_lien_ket(tm):
            loi.append("là liên kết (symlink/junction) — từ chối")
        thuc = tm.resolve()
        if thuc == goc or goc not in thuc.parents:
            loi.append("không nằm trong thư mục gốc — từ chối")
        if thuc == GOC_KHO or GOC_KHO in thuc.parents:
            loi.append("nằm trong kho mã — từ chối")
        for dp, dns, fns in os.walk(tm, followlinks=False):
            for dn in list(dns):
                if _la_lien_ket(Path(dp) / dn):
                    loi.append(f"có liên kết bên trong: {dn}")
                    dns.remove(dn)
            for fn in fns:
                p = Path(dp) / fn
                if _la_lien_ket(p):
                    loi.append(f"có liên kết bên trong: {fn}")
                    continue
                if fn in KHONG_BAO_GIO_XOA:
                    loi.append(f"chứa {fn} (không bao giờ xoá) — từ chối")
                    continue
                (
                    giu if (m.hanh_dong == "xoa" and fn in GIU_LAI and Path(dp) == tm) else tep
                ).append(p)
        ra.append(KiemKe(m, tm, True, sorted(tep), sorted(giu), loi))
    return ra


def _mb(n: int) -> str:
    return f"{n / 1_000_000:.2f} MB".replace(".", ",")


def in_kiem_ke(ds: list[KiemKe]) -> None:
    for k in ds:
        nhan = "XOÁ" if k.muc.hanh_dong == "xoa" else "CHE (không xoá ở đây)"
        print(f"[{nhan}] {k.thu_muc}")
        print(f"    {k.muc.ly_do}")
        if not k.ton_tai:
            print("    không tồn tại — không có gì để làm")
            continue
        print(f"    {len(k.tep)} tệp · {_mb(k.dung_luong)}", end="")
        print(f" · giữ lại: {', '.join(p.name for p in k.giu)}" if k.giu else "")
        for x in k.loi:
            print(f"    LỖI: {x}")


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for khoi in iter(lambda: f.read(1 << 20), b""):
            h.update(khoi)
    return h.hexdigest()


def xoa_an_toan(p: Path) -> None:
    """Ghi đè bằng byte ngẫu nhiên cùng độ dài, fsync, rồi xoá."""
    n = p.stat().st_size
    with p.open("r+b") as f:
        con = n
        while con > 0:
            k = min(con, 1 << 20)
            f.write(os.urandom(k))
            con -= k
        f.flush()
        os.fsync(f.fileno())
    p.unlink()


def thuc_hien(ds: list[KiemKe], goc: Path, nhat_ky: Path) -> int:
    """Xoá mọi tệp của mục "xoa" (trừ GIU_LAI), dọn thư mục rỗng; trả số tệp đã xoá."""
    dong = [f"# Xoá bản thô tập 16 buổi — {dt.datetime.now().isoformat(timespec='seconds')}"]
    da_xoa = 0
    for k in ds:
        if k.muc.hanh_dong != "xoa" or not k.ton_tai:
            continue
        for p in k.tep:
            dong.append(f"{p.relative_to(goc).as_posix()}\t{p.stat().st_size}\t{_sha256(p)}")
            xoa_an_toan(p)
            da_xoa += 1
        for dp, _dns, _fns in sorted(os.walk(k.thu_muc), key=lambda x: -len(x[0])):
            d = Path(dp)
            if d != k.thu_muc and not any(d.iterdir()):
                d.rmdir()
        if not k.giu and not any(k.thu_muc.iterdir()):
            k.thu_muc.rmdir()
    nhat_ky.write_text("\n".join(dong) + "\n", encoding="utf-8")
    return da_xoa


def main(argv: list[str] | None = None, *, hoi: Callable[[str], str] = input) -> int:
    configure()
    ap = argparse.ArgumentParser(description="Liệt kê / xoá bản thô còn định danh (hồ sơ 3.3)")
    ap.add_argument("--goc", type=Path, default=GOC_MAC_DINH, help="thư mục gốc (D:/AISC2026)")
    ap.add_argument("--thuc-hien", action="store_true", help=f'xoá thật; phải gõ "{CAU_XAC_NHAN}"')
    a = ap.parse_args(argv)
    ds = kiem_ke(a.goc)
    in_kiem_ke(ds)
    xoa = [k for k in ds if k.muc.hanh_dong == "xoa" and k.ton_tai]
    tong = sum(len(k.tep) for k in xoa)
    if not a.thuc_hien:
        print(f"CHỈ LIỆT KÊ: {tong} tệp sẽ bị xoá khi chạy với --thuc-hien. Không tệp nào bị đụng.")
        return 0
    loi = [x for k in ds for x in k.loi]
    if loi:
        print("TỪ CHỐI XOÁ — có mục nguy hiểm (xem LỖI ở trên).")
        return 1
    if not tong:
        print("Không có tệp nào để xoá.")
        return 0
    tra_loi = hoi(f'Xoá VĨNH VIỄN {tong} tệp ở trên? Gõ đúng "{CAU_XAC_NHAN}" để xoá: ')
    if tra_loi.strip() != CAU_XAC_NHAN:
        print("Không khớp câu xác nhận — không xoá gì.")
        return 1
    ngay = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    nhat_ky = a.goc / f"nhat-ky-xoa-ban-tho-{ngay}.tsv"
    n = thuc_hien(ds, a.goc.resolve(), nhat_ky)
    print(f"Đã ghi đè và xoá {n} tệp. Nhật ký (tên tệp, kích thước, SHA-256): {nhat_ky}")
    print("Tiếp theo: chạy cipher /w:D:\\ (dọn vùng trống), rồi ghi ngày thật vào hồ sơ mục 3.3.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
