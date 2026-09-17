"""Đếm test thật rồi ghi lại con số vào mọi nơi đang trích nó.

Vì sao có tệp này: hồ sơ dự án tuyên bố số kiểm thử "hợp nhất về một nguồn duy
nhất". Trước 14/09/2026 lời ấy không đúng — badge README ghi 249, trang chủ web
ghi 735, còn pytest chạy ra 990. Ba con số, ba chỗ, không chỗ nào sai lúc viết
nhưng cả ba cùng cũ đi theo những nhịp khác nhau. Một đề tài lấy kỷ luật bằng
chứng làm bản sắc mà để badge nói dối thì tự bắn vào chân mình.

Nguồn duy nhất là chính pytest. Script gọi ``--collect-only`` cho cả hai nhóm
rồi ghi con số vào:

  - README.md          badge Tests, dòng lệnh mẫu, đoạn "Quality gates"
  - web/src/app/page.tsx   hằng PROOF của trang chủ

Chạy:

    .venv/Scripts/python scripts/dong_bo_so_test.py --xem-truoc
    .venv/Scripts/python scripts/dong_bo_so_test.py --ghi
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC / "src"))

from livelift.console import configure  # noqa: E402


def dem(marker: str) -> int:
    """Số test pytest THU THẬP được cho một marker (không chạy chúng)."""
    # S603: lệnh dựng từ hằng trong tệp này cộng sys.executable, không có
    # chuỗi nào đến từ bên ngoài; `marker` chỉ nhận các hằng gọi ở dưới.
    r = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "pytest", "-m", marker, "-q", "-p", "no:warnings", "--collect-only"],
        cwd=GOC,
        capture_output=True,
        text=True,
        errors="replace",
    )
    tong = sum(int(m) for m in re.findall(r"^tests/\S+: (\d+)$", r.stdout, re.M))
    if not tong:
        print(r.stdout[-1500:], file=sys.stderr)
        raise SystemExit(f"Không đếm được test cho marker {marker!r}")
    return tong


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

    nhanh = dem("not slow")
    # Badge README gọi nhóm chậm là "Monte-Carlo": chỉ đếm cổng thống kê thật.
    # Test trình duyệt (marker `browser`, 17/09/2026) cũng chạy trong nhóm chậm
    # nhưng KHÔNG phải cổng Monte-Carlo — gộp vào là khai sai con số công bố.
    cham = dem("slow and not browser")
    trinh_duyet = dem("browser")
    print(
        f"pytest đếm được: {nhanh} test nhanh · {cham} cổng Monte-Carlo · "
        f"{trinh_duyet} test trình duyệt · tổng {nhanh + cham + trinh_duyet}"
    )

    sua: list[tuple[Path, str, str]] = []

    readme = GOC / "README.md"
    t = readme.read_text(encoding="utf-8")
    moi = re.sub(
        r"badge/tests-[^)\]]*-brightgreen",
        f"badge/tests-{nhanh}%20nhanh%20%2B%20{cham}%20Monte--Carlo-brightgreen",
        t,
    )
    moi = re.sub(r'(pytest -m "not slow"\s+# )\d+ test nhanh', rf"\g<1>{nhanh} test nhanh", moi)
    moi = re.sub(r"Quality gates: \d+ test nhanh", f"Quality gates: {nhanh} test nhanh", moi)
    if moi != t:
        sua.append((readme, t, moi))

    trang = GOC / "web" / "src" / "app" / "page.tsx"
    t2 = trang.read_text(encoding="utf-8")
    moi2 = re.sub(
        r'(\{ value: ")\d+(", label: "kiểm thử tự động đang xanh" \})',
        rf"\g<1>{nhanh}\g<2>",
        t2,
    )
    moi2 = re.sub(r"(\*\s+)\d+( kiểm thử\s+— `pytest)", rf"\g<1>{nhanh}\g<2>", moi2)
    if moi2 != t2:
        sua.append((trang, t2, moi2))

    if not sua:
        print("Mọi nơi đã ghi đúng con số — không phải sửa gì.")
        return 0

    for f, cu, _ in sua:
        print(f"\n{f.relative_to(GOC)}: cần sửa")
        for dong_cu in cu.split("\n"):
            if re.search(r"tests-\d+|test nhanh|kiểm thử tự động", dong_cu):
                print(f"    cũ: {dong_cu.strip()[:96]}")

    if a.xem_truoc:
        print("\n(--xem-truoc: chưa ghi gì cả)")
        return 1 if sua else 0

    for f, _, moi_nd in sua:
        f.write_text(moi_nd, encoding="utf-8")
        print(f"Đã ghi {f.relative_to(GOC)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
