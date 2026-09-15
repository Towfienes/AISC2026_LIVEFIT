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
    """Mọi giá trị cần che khi công bố (email, SĐT, MSSV), bỏ qua ô còn trống."""
    ra = []
    for tv in doc()["thanh_vien"]:
        for khoa in ("email", "dien_thoai", "mssv"):
            v = (tv.get(khoa) or "").strip()
            if v and CHO_TRONG not in v:
                ra.append(v)
    return ra
