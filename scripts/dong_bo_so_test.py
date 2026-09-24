"""Đếm test thật rồi ghi lại con số vào mọi nơi đang trích nó.

Vì sao có tệp này: hồ sơ dự án tuyên bố số kiểm thử "hợp nhất về một nguồn duy
nhất". Trước 14/09/2026 lời ấy không đúng — badge README ghi 249, trang chủ web
ghi 735, còn pytest chạy ra 990. Ba con số, ba chỗ, không chỗ nào sai lúc viết
nhưng cả ba cùng cũ đi theo những nhịp khác nhau. Một đề tài lấy kỷ luật bằng
chứng làm bản sắc mà để badge nói dối thì tự bắn vào chân mình.

Nguồn duy nhất là chính pytest. Script gọi ``--collect-only`` cho ba nhóm rồi
ghi con số vào:

  - README.md                       badge Tests, dòng lệnh mẫu, "Quality gates"
  - web/src/app/page.tsx            hằng PROOF của trang chủ
  - docs/competition/FACT-SHEET.md  dòng "Bộ kiểm thử" (kèm ngày đếm)

Kiểm toán 25/09/2026 sửa ba lỗ của bản trước:

  - nhóm ``slow and not browser`` từng được gọi là "17 cổng Monte-Carlo", nhưng
    trong đó chỉ 13 test là mô phỏng/thống kê; 1 test đánh giá NLP trên chat
    thật và 3 cổng dựng bản build CSS. Nay gọi là "cổng chậm" và tách số theo
    TỆP test thu thập được (không chép tay);
  - FACT-SHEET không nằm trong phạm vi quét nên script báo "mọi nơi đã đúng"
    trong khi FACT-SHEET còn số của 17/09;
  - mẫu không tìm thấy từng bị bỏ qua im lặng (một nhánh đổi chữ badge là
    script ngừng đồng bộ mà vẫn báo đúng). Nay mẫu BẮT BUỘC vắng mặt là lỗi,
    thoát mã 1.

Con số là số test pytest THU THẬP được, không phải số đã chạy xanh hôm đó.

Chạy:

    .venv/Scripts/python scripts/dong_bo_so_test.py --xem-truoc
    .venv/Scripts/python scripts/dong_bo_so_test.py --ghi
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "src"))

from livelift.console import configure  # noqa: E402

#: Hai tệp của nhóm chậm KHÔNG phải mô phỏng/thống kê (so-chuan.md §3.3).
TEP_NLP = "tests/test_nlp_eval_harness.py"
TEP_CSS = "tests/test_web_css_gate.py"


@dataclass(frozen=True)
class SoTest:
    """Bộ số test thu thập được. Nhóm chậm tách theo loại cổng."""

    nhanh: int
    thong_ke: int
    nlp: int
    css: int
    trinh_duyet: int

    @property
    def cham(self) -> int:
        return self.thong_ke + self.nlp + self.css

    @property
    def tong(self) -> int:
        return self.nhanh + self.cham + self.trinh_duyet


def vi(n: int) -> str:
    """1830 → "1.830" (vi-VN, dùng trong tài liệu hồ sơ)."""
    return f"{n:,}".replace(",", ".")


def cum_cham(so: SoTest) -> str:
    """Cụm chữ chuẩn cho nhóm chậm — README và FACT-SHEET dùng đúng cụm này."""
    return (
        f"{so.cham} cổng chậm ({so.thong_ke} mô phỏng/thống kê · {so.nlp} đánh giá NLP"
        f" · {so.css} cổng build CSS)"
    )


def mo_ta(so: SoTest) -> str:
    return (
        f"pytest đếm được: {so.nhanh} test nhanh · {cum_cham(so)} · "
        f"{so.trinh_duyet} test trình duyệt · tổng {so.tong}"
    )


def dem_theo_tep(marker: str) -> dict[str, int]:
    """Số test pytest THU THẬP được (không chạy) cho một marker, theo từng tệp."""
    # S603: lệnh dựng từ hằng trong tệp này cộng sys.executable, không có
    # chuỗi nào đến từ bên ngoài; `marker` chỉ nhận các hằng gọi ở dưới.
    r = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "-m", marker, "-q", "-p", "no:warnings", "--collect-only"],
        cwd=GOC,
        capture_output=True,
        text=True,
        errors="replace",
    )
    theo_tep = {t: int(n) for t, n in re.findall(r"^(tests/\S+): (\d+)$", r.stdout, re.M)}
    # Phản biện 25/09/2026: một tệp test lỗi import thì pytest vẫn in số của các
    # tệp còn lại (mã thoát 2) — cộng số đó là đếm THIẾU mà vẫn báo "đúng".
    if r.returncode != 0:
        print(r.stdout[-1500:], r.stderr[-500:], file=sys.stderr)
        raise SystemExit(
            f"pytest --collect-only thoát mã {r.returncode} cho marker {marker!r} — "
            "có tệp test không thu thập được, không ghi con số thiếu"
        )
    if not sum(theo_tep.values()):
        print(r.stdout[-1500:], file=sys.stderr)
        raise SystemExit(f"Không đếm được test cho marker {marker!r}")
    return theo_tep


def phan_loai_cham(theo_tep: dict[str, int]) -> tuple[int, int, int]:
    """(mô phỏng/thống kê, đánh giá NLP, build CSS) của nhóm chậm, theo tệp."""
    chuan = {t.replace("\\", "/"): n for t, n in theo_tep.items()}
    nlp = sum(n for t, n in chuan.items() if t.endswith(TEP_NLP))
    css = sum(n for t, n in chuan.items() if t.endswith(TEP_CSS))
    return sum(chuan.values()) - nlp - css, nlp, css


# ---------------------------------------------------------------------------
# Luật thay chữ — hàm thuần, test được trên tệp thật (tests/test_web_dong_bo_so.py)
# ---------------------------------------------------------------------------

Thay = Callable[[re.Match[str], SoTest, str], str]


@dataclass(frozen=True)
class Luat:
    ten: str
    mau: re.Pattern[str]
    thay: Thay
    #: Mẫu vắng mặt = script không đồng bộ được chỗ đó ⇒ lỗi, không im lặng.
    bat_buoc: bool = True
    #: Luật NGÀY chỉ áp khi các con số trong tệp thực sự đổi.
    la_ngay: bool = False


def _badge(m: re.Match[str], so: SoTest, _ngay: str) -> str:
    chu = quote(f"{so.nhanh} nhanh + {so.cham} cổng chậm", safe="")
    return f"badge/tests-{chu}-{m.group(1)}"


CUM_CHAM_RE = r"\d+ cổng chậm \(\d+ mô phỏng/thống kê · \d+ đánh giá NLP · \d+ cổng build CSS\)"

LUAT: dict[str, list[Luat]] = {
    "README.md": [
        # Màu badge giữ nguyên (không khoá vào brightgreen — sự cố T1 25/09).
        Luat("badge Tests", re.compile(r"badge/tests-[^)\]\s]*?-([a-z]+)(?=\))"), _badge),
        Luat(
            'dòng lệnh pytest -m "not slow"',
            re.compile(r'(pytest -m "not slow"\s+# )\d+ test nhanh'),
            lambda m, so, _: f"{m.group(1)}{so.nhanh} test nhanh",
        ),
        Luat(
            "dòng lệnh pytest -m browser",
            re.compile(r"(pytest -m browser\s+# )\d+ test trình duyệt"),
            lambda m, so, _: f"{m.group(1)}{so.trinh_duyet} test trình duyệt",
        ),
        Luat(
            "Quality gates",
            re.compile(r"Quality gates: \d+ test nhanh"),
            lambda m, so, _: f"Quality gates: {so.nhanh} test nhanh",
        ),
        Luat("cụm cổng chậm", re.compile(CUM_CHAM_RE), lambda m, so, _: cum_cham(so)),
    ],
    "web/src/app/page.tsx": [
        Luat(
            "hằng PROOF",
            re.compile(r'(\{ value: ")\d+(", label: "kiểm thử tự động đang xanh" \})'),
            lambda m, so, _: f"{m.group(1)}{so.nhanh}{m.group(2)}",
        ),
        Luat(
            "chú thích nguồn số test",
            re.compile(r"(\*\s+)\d+( kiểm thử\s+— `pytest)"),
            lambda m, so, _: f"{m.group(1)}{so.nhanh}{m.group(2)}",
            bat_buoc=False,
        ),
    ],
    "docs/competition/FACT-SHEET.md": [
        Luat(
            "dòng Bộ kiểm thử",
            re.compile(
                r"\*\*[\d.]+ test nhanh \+ "
                + CUM_CHAM_RE
                + r" \+ \d+ test trình duyệt = [\d.]+ test thu thập được\*\*"
            ),
            lambda m, so, _: (
                f"**{vi(so.nhanh)} test nhanh + {cum_cham(so)} + {so.trinh_duyet} "
                f"test trình duyệt = {vi(so.tong)} test thu thập được**"
            ),
        ),
        Luat(
            "ngày đếm",
            re.compile(r"(thu thập ngày )\d{2}/\d{2}/\d{4}( bằng `scripts/dong_bo_so_test\.py)"),
            lambda m, _so, ngay: f"{m.group(1)}{ngay}{m.group(2)}",
            la_ngay=True,
        ),
    ],
}


def ap_dung(t: str, luat: list[Luat], so: SoTest, ngay: str) -> tuple[str, list[str]]:
    """Áp luật lên một tệp. Trả (nội dung mới, tên các mẫu bắt buộc KHÔNG tìm thấy)."""
    thieu = [lu.ten for lu in luat if lu.bat_buoc and not lu.mau.search(t)]
    moi = t
    for lu in luat:
        if not lu.la_ngay:
            moi = lu.mau.sub(lambda m, lu=lu: lu.thay(m, so, ngay), moi)
    if moi != t:
        for lu in luat:
            if lu.la_ngay:
                moi = lu.mau.sub(lambda m, lu=lu: lu.thay(m, so, ngay), moi)
    return moi, thieu


def main() -> int:
    # Sự cố 27/08 lặp lại ở tệp này: console Windows mặc định cp1252 nên mọi
    # dòng tiếng Việt bên dưới (kể cả `--help`, vốn in chính docstring này)
    # ném UnicodeEncodeError và script chết trước khi báo được con số. Đây là
    # bước (2) của checklist 15 phút trước hội đồng
    # (docs/competition/kich-ban-demo-7-phut.md) — nó chết là hội đồng thấy
    # traceback. Gọi TRƯỚC parse_args, đúng quy ước của chay_local.py.
    configure()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ghi", action="store_true", help="ghi đè các tệp")
    ap.add_argument("--xem-truoc", action="store_true", help="chỉ in ra")
    a = ap.parse_args()
    if not a.ghi and not a.xem_truoc:
        ap.error("chọn --xem-truoc hoặc --ghi")

    nhanh = sum(dem_theo_tep("not slow").values())
    # Test trình duyệt (marker `browser`, 17/09/2026) cũng mang dấu slow nhưng
    # không phải cổng chậm của lõi — đếm riêng, không gộp.
    thong_ke, nlp, css = phan_loai_cham(dem_theo_tep("slow and not browser"))
    trinh_duyet = sum(dem_theo_tep("browser").values())
    so = SoTest(nhanh, thong_ke, nlp, css, trinh_duyet)
    print(mo_ta(so))

    ngay = dt.date.today().strftime("%d/%m/%Y")
    sua: list[tuple[Path, str, str]] = []
    loi: list[str] = []
    for rel, luat in LUAT.items():
        f = GOC / rel
        cu = f.read_text(encoding="utf-8")
        moi, thieu = ap_dung(cu, luat, so, ngay)
        loi += [f"{rel}: không tìm thấy mẫu “{ten}” — chỗ này KHÔNG được đồng bộ" for ten in thieu]
        if moi != cu:
            sua.append((f, cu, moi))

    for dong in loi:
        print(f"LỖI  {dong}")
    if not sua and not loi:
        print("Mọi nơi đã ghi đúng con số — không phải sửa gì.")
        return 0

    for f, cu, moi in sua:
        print(f"\n{f.relative_to(GOC).as_posix()}: cần sửa")
        for dong_cu, dong_moi in zip(cu.split("\n"), moi.split("\n"), strict=True):
            if dong_cu != dong_moi:
                print(f"    cũ: {dong_cu.strip()[:110]}")
                print(f"    mới: {dong_moi.strip()[:110]}")

    if a.xem_truoc:
        print("\n(--xem-truoc: chưa ghi gì cả)")
        return 1

    for f, _, moi_nd in sua:
        f.write_text(moi_nd, encoding="utf-8")
        print(f"Đã ghi {f.relative_to(GOC).as_posix()}")
    return 1 if loi else 0


if __name__ == "__main__":
    raise SystemExit(main())
