"""Cổng chống trôi giữa cổng Monte-Carlo và bộ đo lại số công bố.

Vì sao tệp này tồn tại. Ngày 14/09/2026 kiểm toán phát hiện tài liệu đang công
bố A/A 4,5% trong khi chạy lại ra 3,50%: con số 4,5% đo ngày 30/08, mã đổi nhiều
lần sau đó, không ai đo lại. Cách chữa là ``scripts/do_lai_so_hieu_chuan.py`` —
nó chạy lại nghiên cứu Monte-Carlo bằng **đúng tham số của cổng** rồi ghi ra
``docs/benchmarks/so-hieu-chuan.json``.

Nhưng "đúng tham số của cổng" hiện đang được bảo đảm bằng việc chép tay từ
``tests/test_sim_validation.py`` sang script. Chép tay là một điểm trôi mới:
sửa cổng mà quên sửa script thì script đo một thứ khác, và sự cố 14/09 lặp lại
dưới dạng tinh vi hơn.

Tệp này đọc CẢ HAI nguồn bằng ``ast`` rồi so từng tham số. Không chạy mô phỏng,
không mạng, không tiến trình con — chạy trong bộ test nhanh.
"""

from __future__ import annotations

import ast
import contextlib
import json
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
CONG = GOC / "tests" / "test_sim_validation.py"
BO_DO = GOC / "scripts" / "do_lai_so_hieu_chuan.py"
KET_QUA = GOC / "docs" / "benchmarks" / "so-hieu-chuan.json"

# Tham số nào của run_validation ảnh hưởng tới con số công bố. `design` và
# `burn_in_s` để mặc định ở cả hai nơi nên không liệt kê — nếu sau này một bên
# đặt tường minh, test `test_khong_co_tham_so_la` bên dưới sẽ bắt được.
THAM_SO_QUAN_TRONG = (
    "n_reps",
    "n_sessions_per_rep",
    "session_minutes",
    "n_draws",
    "master_seed",
)


def _hang_cuc_bo(ham):
    """Các gán hằng đơn giản trong thân hàm: ``n_reps = 200`` → {'n_reps': 200}.

    Cổng A/A viết ``n_reps = 200`` rồi truyền ``n_reps=n_reps`` (vì nó còn dùng
    lại biến đó để tính ``round(rejection_rate * n_reps)``). Không giải biến thì
    test này so một con số với chuỗi 'n_reps' và báo lệch giả.
    """
    ra = {}
    for nut in ham.body:
        if not isinstance(nut, ast.Assign):
            continue
        for dich in nut.targets:
            if not isinstance(dich, ast.Name):
                continue
            with contextlib.suppress(ValueError):
                ra[dich.id] = ast.literal_eval(nut.value)
    return ra


def _doc_loi_goi_run_validation(duong_dan, ten_ham):
    """Lấy tham số của lời gọi ``run_validation`` bên trong một hàm cụ thể."""
    cay = ast.parse(duong_dan.read_text(encoding="utf-8"))
    for nut in ast.walk(cay):
        if not isinstance(nut, ast.FunctionDef) or nut.name != ten_ham:
            continue
        hang = _hang_cuc_bo(nut)
        for con in ast.walk(nut):
            if (
                isinstance(con, ast.Call)
                and isinstance(con.func, ast.Name)
                and con.func.id == "run_validation"
            ):
                ra = {}
                for kw in con.keywords:
                    if kw.arg is None:
                        continue
                    if isinstance(kw.value, ast.Name) and kw.value.id in hang:
                        ra[kw.arg] = hang[kw.value.id]
                        continue
                    try:
                        ra[kw.arg] = ast.literal_eval(kw.value)
                    except ValueError:
                        # SimParams(...) và bạn bè: giữ lại dạng mã nguồn.
                        ra[kw.arg] = ast.unparse(kw.value)
                return ra
    return None


def _bang_nghien_cuu():
    """Đọc hằng NGHIEN_CUU của script mà không import (script kéo theo scipy)."""
    cay = ast.parse(BO_DO.read_text(encoding="utf-8"))
    for nut in cay.body:
        if isinstance(nut, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "NGHIEN_CUU" for t in nut.targets
        ):
            return ast.literal_eval(nut.value)
    pytest.fail("không tìm thấy hằng NGHIEN_CUU trong scripts/do_lai_so_hieu_chuan.py")
    return None


@pytest.mark.parametrize("khoa", ["aa", "thu_hoi"])
def test_tham_so_do_lai_trung_cong(khoa):
    """Script đo lại phải dùng ĐÚNG tham số của cổng nó nói là đang chạy lại."""
    bang = _bang_nghien_cuu()
    assert khoa in bang, f"NGHIEN_CUU thiếu khoá {khoa!r}"
    cau_hinh = bang[khoa]

    cua_cong = _doc_loi_goi_run_validation(CONG, cau_hinh["cong"])
    assert cua_cong is not None, (
        f"không tìm thấy lời gọi run_validation trong {cau_hinh['cong']} — "
        "cổng đã đổi tên? Sửa trường 'cong' trong NGHIEN_CUU"
    )

    cua_script = cau_hinh["tham_so"]
    lech = [
        f"{ten}: cổng={cua_cong.get(ten)!r} ≠ script={cua_script.get(ten)!r}"
        for ten in THAM_SO_QUAN_TRONG
        if cua_cong.get(ten) != cua_script.get(ten)
    ]
    assert not lech, (
        f"scripts/do_lai_so_hieu_chuan.py đang đo KHÁC cổng {cau_hinh['cong']}:\n"
        + "\n".join(lech)
        + "\n\nCon số công bố sẽ không tái lập được. Sửa cho hai bên trùng nhau."
    )

    # treatment_effect nằm trong SimParams(...) ở cổng, tách riêng ở script.
    sim = cua_cong.get("sim_params", "")
    mong_doi = f"treatment_effect={cau_hinh['treatment_effect']}"
    assert mong_doi in sim.replace(" ", ""), (
        f"cổng {cau_hinh['cong']} dùng {sim!r}, script khai "
        f"treatment_effect={cau_hinh['treatment_effect']}"
    )


@pytest.mark.parametrize("khoa", ["aa", "thu_hoi"])
def test_khong_co_tham_so_la(khoa):
    """Cổng đặt tường minh một tham số mà script không biết ⇒ script đo lệch."""
    cau_hinh = _bang_nghien_cuu()[khoa]
    cua_cong = _doc_loi_goi_run_validation(CONG, cau_hinh["cong"])
    biet = set(THAM_SO_QUAN_TRONG) | {"sim_params"}
    la = sorted(set(cua_cong) - biet)
    assert not la, (
        f"cổng {cau_hinh['cong']} đặt tham số mà bộ đo lại không sao chép: {la}. "
        "Thêm vào THAM_SO_QUAN_TRONG và vào NGHIEN_CUU, rồi đo lại."
    )


@pytest.mark.skipif(not KET_QUA.exists(), reason="chưa chạy do_lai_so_hieu_chuan.py lần nào")
def test_ket_qua_da_ghi_co_du_truong():
    """Tệp kết quả phải tự nói nó đo khi nào, trên bản mã nào."""
    d = json.loads(KET_QUA.read_text(encoding="utf-8"))
    for truong in ("ngay_do", "ban_git", "alpha", "nghien_cuu"):
        assert truong in d, f"so-hieu-chuan.json thiếu trường {truong!r}"
    for khoa in ("aa", "thu_hoi"):
        assert khoa in d["nghien_cuu"], f"so-hieu-chuan.json thiếu nghiên cứu {khoa!r}"
        for truong in ("ty_le_bac_bo", "do_phu_ktc", "do_lech_tuong_doi", "tham_so"):
            assert truong in d["nghien_cuu"][khoa], f"{khoa} thiếu {truong!r}"
