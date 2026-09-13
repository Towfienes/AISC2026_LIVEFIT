#!/usr/bin/env python3
"""Seed BỘ PHIÊN DEMO VÀNG — tất định, gọi đủ cả ba trạng thái kết quả.

Vì sao có tệp này (gói DEMO-THẬT, yêu cầu phản biện #2–3 cả hai vòng): một
công tắc DEMO/THẬT mà không có nội dung demo tốt là công tắc rỗng. Bộ phiên
vàng là nội dung đó — sáu phiên mô phỏng ``is_demo=true`` với seed CỐ ĐỊNH,
phủ đủ ba trạng thái của màn kết quả:

* cụm **DƯƠNG rõ** (3 phiên, hiệu ứng bơm 0.8) — KTC loại 0 về phía dương;
* cụm **NULL** (2 phiên, hiệu ứng bơm 0.0) — ước lượng được, KTC chứa 0;
* một phiên **CHƯA ĐỦ ĐIỀU KIỆN** (15 phút → 3 khối đo) — estimable=false.

Nhờ đó demo và ảnh chụp cho TỪNG trạng thái có ngay, không phải chờ dữ liệu
thật — và cả ba trạng thái được dàn dựng công phu ngang nhau (không tôn vinh
riêng kết quả đẹp). Logic seed + kiểm trạng thái nằm ở
:func:`livelift.api.routes.demo.seed_demo_vang`; tệp này chỉ là CLI mỏng.

Chạy:

    # kho memory (xem thử / kiểm định tất định — dữ liệu mất khi tiến trình tắt)
    .venv/Scripts/python scripts/seed_demo_vang.py

    # kho bền vững (đúng kho mà API docker đang dùng), rồi ghi docs/demo-vang.md
    .venv/Scripts/python scripts/seed_demo_vang.py --backend postgres --ghi-doc

Tất định: chạy hai lần cùng seed ⇒ cùng ước lượng/KTC/trạng thái (session_id
là UUID nên khác nhau — định danh không phải kết quả). Gate:
``tests/test_demo_that.py``.

Yêu cầu với ``--backend postgres``: migration 0009 (cột ``is_demo``) đã áp —
``.venv/Scripts/livelift-migrate up`` (hoặc để docker compose service
``migrate`` chạy bản mã mới).
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from livelift.console import configure  # noqa: E402

DOC_PATH = REPO_ROOT / "docs" / "demo-vang.md"

TEN_NHOM = {
    "duong": "DƯƠNG rõ (KTC loại 0)",
    "null": "NULL (KTC chứa 0)",
    "thieu": "CHƯA ĐỦ ĐIỀU KIỆN (estimable=false)",
}


def _fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:+.3f}"


def _bang_markdown(result: dict) -> str:
    """Bảng Markdown ghi vào docs/demo-vang.md — sinh từ kết quả chạy THẬT."""
    lines = [
        "| Trạng thái | Phiên (title) | session_id | n khối | Ước lượng | KTC 95% | Ghi chú |",
        "|---|---|---|---|---|---|---|",
    ]
    for nhom in ("duong", "null", "thieu"):
        for sid in result["nhom"][nhom]:
            kq = result["ket_qua"][sid]
            ktc = (
                f"[{_fmt(kq['ci_low'])}, {_fmt(kq['ci_high'])}]"
                if kq["ci_low"] is not None
                else "—"
            )
            ghi_chu = kq["message"] if nhom == "thieu" else ""
            lines.append(
                f"| {TEN_NHOM[nhom]} | {kq['title']} | `{sid}` | {kq['n_blocks']} "
                f"| {_fmt(kq['estimate'])} | {ktc} | {ghi_chu or ''} |"
            )
    return "\n".join(lines)


def _noi_dung_doc(result: dict, backend: str) -> str:
    from livelift.api.routes.demo import VANG_DUONG, VANG_NULL, VANG_THIEU

    seeds = [s for s, _, _ in VANG_DUONG] + [s for s, _, _ in VANG_NULL] + [VANG_THIEU[0]]
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"""# Bộ phiên DEMO VÀNG

Sáu phiên mô phỏng `is_demo=true`, seed CỐ ĐỊNH ({", ".join(str(s) for s in seeds)}),
phủ đủ **cả ba trạng thái** của màn kết quả — để demo và chụp ảnh từng trạng
thái mà không phải chờ dữ liệu thật, và để trạng thái NULL / CHƯA ĐỦ ĐIỀU KIỆN
được trình bày công phu ngang trạng thái DƯƠNG (yêu cầu phản biện khoa học).

Sinh lại (tất định — cùng seed ⇒ cùng ước lượng/KTC/trạng thái, chỉ session_id
đổi vì là UUID):

    .venv/Scripts/python scripts/seed_demo_vang.py --backend postgres --ghi-doc

Ba hàng rào đi kèm (gói DEMO-THẬT, PREREGISTRATION §8.2):

- mọi phiên dưới đây mang `is_demo=true` **từ lúc sinh**, bất biến về sau;
- chúng bị loại khỏi `/experiment/summary` mặc định (`env=real`) và mọi đầu ra
  khoa học thật (kể cả export lô gán nhãn NLP) — xem riêng từng phiên qua
  `/sessions/{{id}}/bao-cao`, luôn kèm cờ `is_demo` để UI vẽ nhãn DEMO;
- khóa §7 (`RESULTS_FREEZE_UNTIL`) KHÔNG áp cho phiên demo: hiệu ứng của chúng
  là tham số gõ vào simulator, không có gì để nhìn trộm — nhờ đó bộ demo dùng
  được ngay trong cửa sổ khóa chiến dịch.

## Phiên mẫu (lần seed gần nhất — kho `{backend}`, {now})

{_bang_markdown(result)}

Xem một trạng thái: mở `/sessions/<session_id>/bao-cao` (trường
`ket_qua_thi_nghiem`) hoặc trang kết quả của web với phiên tương ứng.
Bản gộp CHỈ-DEMO (có nhãn MÔ PHỎNG): `GET /experiment/summary?env=demo`.
"""


def main(argv: list[str] | None = None) -> int:
    configure()
    parser = argparse.ArgumentParser(prog="seed_demo_vang", description=__doc__)
    parser.add_argument(
        "--backend",
        choices=["memory", "postgres"],
        default=None,
        help="kho đích (mặc định: STORE_BACKEND trong môi trường, rơi về memory)",
    )
    parser.add_argument(
        "--ghi-doc",
        action="store_true",
        help=f"ghi bảng session_id mẫu vào {DOC_PATH.relative_to(REPO_ROOT)}",
    )
    args = parser.parse_args(argv)

    from livelift.api.routes.demo import DemoVangStateError, seed_demo_vang
    from livelift.api.store import build_store

    store = build_store(args.backend)
    if store.backend == "memory":
        print(
            "LƯU Ý: kho 'memory' — bộ phiên vàng này biến mất khi tiến trình kết thúc. "
            "Dùng --backend postgres để seed vào kho bền vững mà API đang phục vụ."
        )
    try:
        result = seed_demo_vang(store)
    except DemoVangStateError as exc:
        print(f"LỖI TRẠNG THÁI: {exc}")
        return 1
    except Exception as exc:
        if "is_demo" in str(exc):
            print(
                "LỖI: kho chưa có cột is_demo (migration 0009). Chạy "
                "'.venv/Scripts/livelift-migrate up' rồi thử lại."
            )
            return 1
        raise
    finally:
        store.close()

    print("Đã seed bộ phiên DEMO VÀNG (is_demo=true, seed cố định):\n")
    for nhom in ("duong", "null", "thieu"):
        print(f"  {TEN_NHOM[nhom]}:")
        for sid in result["nhom"][nhom]:
            kq = result["ket_qua"][sid]
            if kq["estimable"]:
                print(
                    f"    {sid}  n={kq['n_blocks']}  est={_fmt(kq['estimate'])}  "
                    f"KTC=[{_fmt(kq['ci_low'])}, {_fmt(kq['ci_high'])}]  p={kq['p_value']:.3f}"
                )
            else:
                print(f"    {sid}  n={kq['n_blocks']}  {kq['message']}")
        print()

    if args.ghi_doc:
        DOC_PATH.write_text(_noi_dung_doc(result, store.backend), encoding="utf-8")
        print(f"Đã ghi {DOC_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
