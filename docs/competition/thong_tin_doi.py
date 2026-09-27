"""Thông tin cá nhân của đội thi — đọc từ tệp CỤC BỘ, không bao giờ vào git.

Vì sao có tệp này: kho mã phải mở công khai cho hội đồng chấm, nhưng ngày sinh,
mã số sinh viên, số điện thoại của từng thành viên là dữ liệu cá nhân theo Luật
Bảo vệ dữ liệu cá nhân 91/2025/QH15, và không có lý do gì để chúng nằm trong một
kho mã công khai. Trước 15/09/2026 chúng bị chép cứng vào hai bộ dựng hồ sơ và
script xuất Prompt Log; từ nay cả ba đọc từ đây.

Tệp thật là ``thong-tin-doi.local.json`` cạnh tệp này, đã nằm trong .gitignore.
Máy chưa có tệp đó thì chép ``thong-tin-doi.example.json`` thành tên ấy rồi điền.
Thiếu tệp thật thì mọi hàm vẫn chạy, nhưng trả toàn ô ``⬜`` — bộ dựng hồ sơ sẽ
báo "CHƯA NỘP ĐƯỢC" chứ không lặng lẽ dựng ra bản thiếu tên.

Chỉ dùng thư viện chuẩn: tệp này được nhập từ cả ``.venv`` lẫn ``.venv-docx``.

Khoá của mỗi thành viên: ``ho_ten``, ``ngay_sinh``, ``mssv``, ``lop_hanh_chinh``
(thêm 25/09/2026 — MẪU 3 hỏi "Lớp hành chính, ngành, khoa, trường"; tệp cũ
thiếu khoá này thì bộ dựng coi là ô ``⬜``), ``nganh``, ``khoa``, ``truong``,
``noi_o``, ``dien_thoai``, ``email``.
"""

from __future__ import annotations

import json
from pathlib import Path

DAY = Path(__file__).resolve().parent
TEP_THAT = DAY / "thong-tin-doi.local.json"
TEP_MAU = DAY / "thong-tin-doi.example.json"
CHO_TRONG = "⬜"


def doc() -> dict:
    """Trả thông tin đội. Khoá ``thieu_tep_that`` = True khi đang dùng tệp mẫu."""
    nguon = TEP_THAT if TEP_THAT.exists() else TEP_MAU
    d = json.loads(nguon.read_text(encoding="utf-8"))
    d["thieu_tep_that"] = not TEP_THAT.exists()
    return d


def gia_tri_nhay_cam() -> list[str]:
    """Mọi giá trị cần che khi công bố, bỏ qua ô còn trống.

    Email, SĐT, MSSV luôn che. Lớp hành chính (thêm 25/09/2026) che khi dài từ
    6 ký tự: mã lớp đầy đủ cùng họ tên định danh được một sinh viên, còn chuỗi
    quá ngắn thì thay thế toàn văn sẽ xoá nhầm chữ thường.
    """
    ra = []
    for tv in doc()["thanh_vien"]:
        for khoa in ("email", "dien_thoai", "mssv", "lop_hanh_chinh"):
            v = (tv.get(khoa) or "").strip()
            if not v or CHO_TRONG in v:
                continue
            if khoa == "lop_hanh_chinh" and len(v) < 6:
                continue
            ra.append(v)
    return ra
