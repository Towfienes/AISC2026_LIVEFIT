"""Dọn các phiên DEMO trùng tên trong ảnh chụp kho memory.

Vì sao có tệp này (14/09/2026): bộ phiên demo vàng từng gieo được nhiều lần
vào cùng một kho, nên màn kết quả hiện 12 dòng mang đúng 6 cái tên. Endpoint
``POST /demo/seed-vang`` nay đã bất biến nên lỗi không tái diễn, nhưng những
kho đã lỡ nhân bản thì vẫn cần dọn.

HAI RÀNG BUỘC CỨNG, và lý do:

* Chỉ đụng phiên có ``is_demo=true``. Phiên thật là số đo, và số đo hỏng thì
  đánh dấu ``excluded_reason`` chứ không bao giờ xoá (HARNESS §3). Dữ liệu
  demo thì ngược lại: nó là dữ liệu mẫu sinh ra từ seed cố định, gieo lại lúc
  nào cũng được, nên dọn bản thừa không mất gì.
* Với mỗi tên trùng, GIỮ bản tạo sớm nhất và bỏ các bản sau. Bản sớm nhất là
  bản mà mọi ảnh chụp và tài liệu đang trỏ tới.

Chạy (phải TẮT API trước, không thì tiến trình đang chạy ghi đè lại ảnh chụp):

    .venv/Scripts/python scripts/don_phien_demo_trung.py --xem-truoc
    .venv/Scripts/python scripts/don_phien_demo_trung.py --lam-that
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from collections import defaultdict
from pathlib import Path

MAC_DINH = Path("data/snapshot/livelift-store.json")
LA_TEN_MAC_DINH = re.compile(r"^Live \d{2}/\d{2} \d{2}:\d{2} · ")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from livelift.console import configure  # noqa: E402

#: Các bộ sưu tập trong ảnh chụp được khoá theo ``session_id``.
THEO_PHIEN = (
    "sessions",
    "blocks",
    "ticks",
    "comments",
    "reactions",
    "clicks",
    "interventions",
    "orders",
    "assignment_events",
    "exposure_events",
)


def tim_ban_trung(sessions: dict) -> dict[str, list[str]]:
    """Gom session_id theo tên, chỉ trong nhóm is_demo, giữ nhóm có ≥ 2 bản."""
    theo_ten: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for sid, s in sessions.items():
        if not s.get("is_demo"):
            continue
        ten = str(s.get("title") or "").strip()
        if not ten or LA_TEN_MAC_DINH.match(ten):
            # Tên mặc định "Live dd/mm HH:MM · <Nền tảng> · <N> phút" (máy chủ và
            # wizard đặt từ 17/09/2026) chỉ chính xác tới PHÚT: hai phiên khách
            # tạo trong cùng phút là hai phiên khác nhau, không phải bản nhân.
            continue
        theo_ten[ten].append((str(s.get("created_at") or ""), sid))

    thua: dict[str, list[str]] = {}
    for ten, ds in theo_ten.items():
        if len(ds) < 2:
            continue
        ds.sort()  # created_at tăng dần: phần tử đầu là bản sớm nhất — bản giữ
        thua[ten] = [sid for _, sid in ds[1:]]
    return thua


def main() -> int:
    # Sự cố 27/08 (sổ sự cố): console Windows mặc định cp1252, mọi dòng
    # tiếng Việt bên dưới — kể cả `--help` và thông báo lỗi của argparse —
    # ném UnicodeEncodeError và script chết. Gọi TRƯỚC parse_args, đúng quy
    # ước của scripts/chay_local.py.
    configure()
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anh-chup", type=Path, default=MAC_DINH)
    ap.add_argument("--lam-that", action="store_true", help="ghi đè ảnh chụp")
    ap.add_argument("--xem-truoc", action="store_true", help="chỉ in ra, không ghi")
    a = ap.parse_args()

    if not a.lam_that and not a.xem_truoc:
        ap.error("chọn --xem-truoc hoặc --lam-that")
    if not a.anh_chup.exists():
        print(f"Không thấy ảnh chụp: {a.anh_chup}", file=sys.stderr)
        return 1

    d = json.loads(a.anh_chup.read_text(encoding="utf-8"))
    sessions = d.get("sessions", {})
    thua = tim_ban_trung(sessions)

    if not thua:
        print("Không có phiên demo nào trùng tên — không phải dọn gì.")
        return 0

    can_bo = {sid for ds in thua.values() for sid in ds}
    print(f"Tìm thấy {len(thua)} tên bị nhân bản, tổng {len(can_bo)} phiên thừa:")
    for ten, ds in sorted(thua.items()):
        print(f"  {ten!r}: giữ 1, bỏ {len(ds)}")

    # Chặn cuối: không bao giờ đụng phiên thật.
    for sid in can_bo:
        if not sessions[sid].get("is_demo"):
            print(f"DỪNG: {sid} không phải phiên demo", file=sys.stderr)
            return 2

    if a.xem_truoc:
        print("\n(--xem-truoc: chưa ghi gì cả)")
        return 0

    luu = a.anh_chup.with_suffix(a.anh_chup.suffix + ".truoc-khi-don")
    shutil.copy2(a.anh_chup, luu)

    da_bo = 0
    for ten_bo in THEO_PHIEN:
        bo = d.get(ten_bo)
        if not isinstance(bo, dict):
            continue
        for sid in can_bo:
            if bo.pop(sid, None) is not None:
                da_bo += 1

    a.anh_chup.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    print(f"\nĐã bỏ {len(can_bo)} phiên ({da_bo} mục qua {len(THEO_PHIEN)} bộ).")
    print(f"Bản trước khi dọn: {luu}")
    print("Bật lại API: .venv/Scripts/python scripts/chay_local.py --force --tach")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
