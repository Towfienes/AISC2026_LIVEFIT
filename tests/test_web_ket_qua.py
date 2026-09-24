"""Gói KẾT-QUẢ v2 — gate cho màn /ket-qua verdict-first + tóm tắt 3 câu.

Điều kiện bắt buộc từ phản biện khoa học (ưu tiên #6): CẢ BA trạng thái kết
quả — DƯƠNG/ÂM, NULL, CHƯA ĐỦ ĐIỀU KIỆN — được thiết kế RIÊNG với mức công
phu NGANG NHAU; và từ phản biện #1: con dấu "TÁC ĐỘNG THẬT" chỉ tồn tại khi
KTC 95% loại 0, KHÔNG count-up cho ước lượng nhân quả. Các gate ở đây đọc
thẳng mã render để giữ những lời hứa đó không bị "tiện tay" gỡ mất:

1. ba (bốn, tính quan sát) khối verdict tồn tại và đều là Card padding="lg";
2. con dấu TÁC ĐỘNG THẬT bị nhốt trong đúng nhánh KTC-loại-0;
3. không cơ chế count-up/tween nào trên trang kết quả;
4. trạng thái NULL mang huy hiệu "KẾT QUẢ TRUNG THỰC" + bảng "cần thêm bao
   nhiêu phiên"; trạng thái CHƯA ĐỦ in nguyên văn lý do máy chủ + checklist
   ngưỡng thiết kế; khóa §7 có mặt chữ;
5. tóm tắt 3 câu render nguyên văn từ server (không .toFixed nào trong
   component — client không được chế lại số) trên CẢ /ket-qua và /bao-cao;
6. chip DEMO đi theo cờ is_demo ở mọi chỗ số liệu demo xuất hiện.
"""

from __future__ import annotations

import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"
SRC = WEB / "src"
KET_QUA = SRC / "app" / "ket-qua" / "page.tsx"
BAO_CAO = SRC / "app" / "bao-cao" / "[id]" / "page.tsx"
TOM_TAT = SRC / "components" / "TomTat3Cau.tsx"
TYPES = SRC / "lib" / "types.ts"


def _read(p: Path) -> str:
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Ba trạng thái — ba thiết kế riêng, cùng mức công phu
# ---------------------------------------------------------------------------


def test_ca_ba_trang_thai_verdict_deu_ton_tai():
    src = _read(KET_QUA)
    for comp in ("VerdictCoTacDong", "VerdictNull", "VerdictChuaDu", "VerdictQuanSat"):
        assert f"function {comp}" in src, f"thiếu khối verdict {comp}"
        assert re.search(rf"<{comp}\b", src), f"{comp} được định nghĩa nhưng không render"


def test_ba_trang_thai_cung_muc_cong_phu_card_lg():
    """Mỗi trạng thái là một Card padding='lg' có huy hiệu nhận diện — NULL và
    CHƯA ĐỦ không được là một dòng chữ xám lép vế cạnh trạng thái dương."""
    src = _read(KET_QUA)
    for comp, badge in [
        ("VerdictCoTacDong", "TÁC ĐỘNG THẬT"),
        ("VerdictNull", "KẾT QUẢ TRUNG THỰC"),
        ("VerdictChuaDu", "CHƯA ĐỦ ĐIỀU KIỆN"),
    ]:
        body = src.split(f"function {comp}")[1].split("\nfunction ")[0]
        assert 'padding="lg"' in body, f"{comp} phải là Card padding='lg'"
        assert badge in body, f"{comp} thiếu huy hiệu nhận diện {badge!r}"
        assert "<Badge" in body


def test_verdict_state_theo_dung_luat_ktc_loai_0():
    """Cùng luật phân loại với analysis/narrate.trang_thai_ket_luan."""
    src = _read(KET_QUA)
    assert "ciLow != null && ciLow > 0" in src
    assert "ciHigh != null && ciHigh < 0" in src


# ---------------------------------------------------------------------------
# 2. Con dấu TÁC ĐỘNG THẬT bị nhốt trong nhánh KTC-loại-0
# ---------------------------------------------------------------------------


def test_con_dau_tac_dong_that_chi_o_nhanh_co_tac_dong():
    src = _read(KET_QUA)
    # chuỗi RENDER của con dấu (không tính chú thích mã) phải xuất hiện đúng
    # MỘT chỗ — trong VerdictCoTacDong
    con_dau = "TÁC ĐỘNG THẬT · KTC 95% không chứa 0"
    assert src.count(con_dau) == 1, "con dấu render phải xuất hiện đúng MỘT chỗ"
    body = src.split("function VerdictCoTacDong")[1].split("\nfunction ")[0]
    assert con_dau in body, "con dấu phải nằm trong VerdictCoTacDong"
    # ... và VerdictCoTacDong chỉ được render khi state là duong/am
    m = re.search(r'verdict\.state === "duong" \|\| verdict\.state === "am"', src)
    assert m, "VerdictCoTacDong phải được gate bằng state duong/am"
    # con dấu luôn kèm KTC ngay trong chính nó (phản biện #1)
    assert "TÁC ĐỘNG THẬT · KTC 95% không chứa 0" in body


# ---------------------------------------------------------------------------
# 3. Không count-up cho ước lượng nhân quả
# ---------------------------------------------------------------------------


def test_khong_count_up_tren_man_ket_qua():
    src = _read(KET_QUA)
    for cam in ("countUp", "CountUp", "requestAnimationFrame", "dur-countup", "medium3"):
        assert cam not in src, f"cấm count-up/tween trên ước lượng nhân quả: tìm thấy {cam!r}"


# ---------------------------------------------------------------------------
# 4. NULL và CHƯA ĐỦ được dàn dựng thật, khóa §7 có mặt chữ
# ---------------------------------------------------------------------------


def test_null_state_noi_dung_bat_buoc():
    src = _read(KET_QUA)
    body = src.split("function VerdictNull")[1].split("\nfunction ")[0]
    assert "kết quả hợp lệ" in body, "NULL phải được tuyên bố là kết quả hợp lệ"
    assert "Cần thêm bao nhiêu phiên" in body, "NULL phải trả lời bằng bảng lực, không an ủi"
    assert "còn chứa 0" in body
    assert "CIBar" in body, "NULL vẽ thanh KTC như trạng thái dương — không lép"


def test_chua_du_in_ly_do_may_chu_va_nguong_thiet_ke():
    src = _read(KET_QUA)
    body = src.split("function VerdictChuaDu")[1].split("\nfunction ")[0]
    assert "v.lyDo" in body, "lý do từ chối phải in nguyên văn từ máy chủ"
    assert "từ chối kết luận" in body
    for nguong in ("nguong: 2", "nguong: 8", "nguong: 4"):
        assert nguong in body, f"checklist thiếu ngưỡng thiết kế {nguong!r}"
    assert "/chay-phien" in body, "CHƯA ĐỦ phải dẫn người dùng đi sửa thiết kế"
    assert "KHÓA THEO TIỀN ĐĂNG KÝ" in body, "khóa §7 là một biến thể có mặt chữ riêng"


# ---------------------------------------------------------------------------
# 5. Tóm tắt 3 câu — render nguyên văn, không chế lại số ở client
# ---------------------------------------------------------------------------


def test_tom_tat_3_cau_render_o_ca_hai_man():
    assert "tom_tat_3_cau" in _read(KET_QUA)
    assert "tom_tat_3_cau" in _read(BAO_CAO)
    for page in (KET_QUA, BAO_CAO):
        assert "TomTat3Cau" in _read(page), f"{page.name} phải dùng component chung"


def _render(src: str) -> str:
    """Nguồn đã bỏ chú thích (chú thích giải thích chính câu bị cấm)."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<![:\w])//.*$", " ", src)


def test_chua_du_khong_lap_thong_diep_ba_lan():
    """Đánh giá UI 17/09/2026: khi CHƯA ĐỦ ĐIỀU KIỆN, trang in cùng một thông
    điệp ba lần liền — tiêu đề khối verdict → lý do máy chủ → câu 1 của tóm tắt
    ("Thiết kế chưa đủ điều kiện…: <cùng lý do>"), rồi câu 2/3 lặp checklist và
    nút. Khối verdict đã chứa đủ ba ý, nên tóm tắt 3 câu không hiện ở trạng thái
    này; ở DƯƠNG/ÂM/NULL nó vẫn hiện vì nói thêm điều khối verdict không nói."""
    src = _render(_read(KET_QUA))
    m = re.search(r"\{([^{}]*?)\?\s*\(\s*<TomTat3Cau\b", src)
    assert m, "không đọc được điều kiện render TomTat3Cau"
    assert 'verdict?.state !== "chuadu"' in m.group(1), (
        "tóm tắt 3 câu phải bị bỏ ở trạng thái chuadu — nếu không câu 1 lặp lại lý do "
        "khối verdict vừa in nguyên văn"
    )
    assert src.count("<TomTat3Cau") == 1


def test_chua_du_an_tom_tat_nhung_khong_mat_so_luot_nhap_hop_le():
    """Phản biện gói E: ẩn tóm tắt 3 câu ở trạng thái chuadu từng làm mất số
    lượt nhấp hợp lệ — CHỈ SỐ CHÍNH — vì câu 2 của máy chủ là chỗ duy nhất in
    nó (và, khi xem ?phien=, cả tổng bình luận và thời lượng). Bỏ lặp chỉ được
    bỏ chữ trùng, không được bỏ số: khối VerdictChuaDu phải tự in các số đó,
    thiếu thì nói THIẾU chứ không in 0."""
    src = _render(_read(KET_QUA))
    body = src.split("function VerdictChuaDu")[1].split("\nfunction ")[0]
    assert "fmtNumber(v.luotNhapHopLe)" in body, "khối chưa đủ phải in số lượt nhấp hợp lệ"
    assert "Lượt nhấp hợp lệ qua link đo" in body
    assert "v.luotNhapHopLe != null" in body, "thiếu nguồn lượt nhấp phải rẽ nhánh THIẾU"
    assert "không phải bằng 0" in body, "lượt nhấp THIẾU không được đọc thành 0"
    assert "THIẾU" in body
    # Dòng lượt nhấp không bị giấu sau nhánh khóa §7: số vận hành luôn công khai.
    i = body.index("fmtNumber(v.luotNhapHopLe)")
    assert "v.khoa ?" not in body[body.rindex("<li", 0, i) : i]
    # Bản một phiên: tổng bình luận và thời lượng cũng từng chỉ nằm trong câu 2.
    for so in ("fmtNumber(v.motPhien.tongBinhLuan)", "v.motPhien.thoiLuongS"):
        assert so in body, f"khối chưa đủ (?phien=) phải in {so}"

    # Nguồn số: bản gộp đọc valid_clicks, bản một phiên đọc tong_quan.
    gop = src.split("function verdictFromSummary")[1].split("\nfunction ")[0]
    assert ".valid_clicks" in gop
    mot = src.split("function verdictFromKetQua")[1].split("\nfunction ")[0]
    for f in ("luot_nhap_hop_le", "thieu?.luot_nhap", "tong_binh_luan", "thoi_luong_s"):
        assert f in mot, f"bản một phiên phải đọc tong_quan.{f}"
    assert "baoCao.tong_quan" in src, "verdictFromKetQua phải nhận tong_quan của báo cáo"


def test_hop_dong_may_chu_tra_so_luot_nhap_o_nhanh_chua_du(monkeypatch):
    """Hai đầu không lệch: ở nhánh CHƯA ĐỦ, máy chủ vẫn trả valid_clicks (bản
    gộp) và tong_quan.luot_nhap_hop_le + lý do thiếu (báo cáo phiên) — đúng
    các trường VerdictChuaDu đọc."""
    from fastapi.testclient import TestClient

    from livelift.api.main import create_app
    from livelift.api.store import InMemoryStore
    from livelift.config import get_settings

    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    try:
        with TestClient(create_app(store=InMemoryStore())) as c:
            gop = c.get("/experiment/summary").json()
            assert gop["estimable"] is False
            assert "valid_clicks" in gop
            assert gop["valid_clicks"] is not None
            cau2 = gop["tom_tat_3_cau"][1]["text"]
            assert f"{gop['valid_clicks']} lượt nhấp hợp lệ" in cau2, (
                "câu 2 bị ẩn mang số lượt nhấp — khối verdict phải in lại đúng số này"
            )

            sid = c.post(
                "/sessions", json={"platform": "facebook", "planned_duration_min": 30}
            ).json()["session_id"]
            tq = c.get(f"/sessions/{sid}/bao-cao").json()["tong_quan"]
            for f in ("luot_nhap_hop_le", "tong_binh_luan", "thoi_luong_s", "thieu"):
                assert f in tq, f"báo cáo phiên thiếu tong_quan.{f}"
            thieu_kem_ly_do = (
                "khi chưa có link đo, máy chủ trả null + lý do — web in THIẾU kèm lý do"
            )
            assert tq["luot_nhap_hop_le"] is None, thieu_kem_ly_do
            assert tq["thieu"].get("luot_nhap"), thieu_kem_ly_do
    finally:
        get_settings.cache_clear()


def test_chua_du_khong_them_cau_ket_noi_lai_lan_thu_tu():
    body = _render(_read(KET_QUA)).split("function VerdictChuaDu")[1].split("\nfunction ")[0]
    assert "Không hạ ngưỡng, không nội suy" not in body, (
        "câu kết cũ nói lại điều checklist + nút đã nói"
    )
    # Nhánh khóa §7 vẫn giải thích VÌ SAO khóa — đó là thông tin mới, không phải lặp.
    assert "nhìn trộm hiệu ứng" in body


def test_component_tom_tat_khong_che_so_va_khai_nguon():
    src = _read(TOM_TAT)
    assert ".toFixed" not in src, "client không được định dạng lại số của narrate"
    assert "Nguồn số" in src, "mỗi câu phải khai nguồn (refs) qua tooltip"
    for badge in ("THÍ NGHIỆM", "QUAN SÁT", "THIẾU DỮ LIỆU"):
        assert badge in src, f"thiếu huy hiệu bằng chứng {badge}"
    assert "{c.text}" in src, "câu phải render nguyên văn từ server"


def test_types_khai_bao_cau_tom_tat():
    src = _read(TYPES)
    assert "CauTomTat" in src
    assert '"thi_nghiem" | "quan_sat" | "thieu_du_lieu"' in src


# ---------------------------------------------------------------------------
# 6. Chip DEMO theo cờ is_demo
# ---------------------------------------------------------------------------


def test_chip_demo_theo_co_is_demo():
    kq = _read(KET_QUA)
    # verdict + tóm tắt + danh sách phiên đều đeo chip theo cờ
    assert "isDemo" in kq
    assert kq.count("DEMO — dữ liệu mẫu") >= 4, "mọi khối số liệu demo phải đeo chip DEMO"
    assert "s.is_demo ? <Badge" in kq, "từng dòng phiên demo trong danh sách phải có chip"
    bc = _read(BAO_CAO)
    assert "data?.is_demo" in bc or "data.is_demo" in bc, "/bao-cao phải vẽ chip DEMO theo cờ"


def test_danh_sach_phien_tach_nhom_that_demo():
    """CẬP NHẬT CÓ CHỦ ĐÍCH (kiểm toán 25/09/2026, runtime.md §3.2): mục "Phiên
    thật" từ nay còn loại cả phiên CHẠY THỬ (xem test_phien_chay_thu_...); bất
    biến cũ giữ nguyên — phiên demo không bao giờ lọt vào nhóm thật."""
    src = _read(KET_QUA)
    assert "realSessions" in src
    assert "demoSessions" in src
    assert "filter((s) => !s.is_demo && s.dry_run !== true)" in src
    assert "filter((s) => s.is_demo)" in src


# ---------------------------------------------------------------------------
# 7. Chi tiết thống kê giữ nguyên (MDE/CV/tuân thủ) + p-floor trung thực
# ---------------------------------------------------------------------------


def test_chi_tiet_thong_ke_van_con_va_p_floor_trung_thuc():
    src = _read(KET_QUA)
    assert "Chi tiết thống kê cho giám khảo" in src
    for can in ("power_table", "measured_cv", "measured_compliance", "MDE"):
        assert can in src, f"chi tiết thống kê thiếu {can}"
    # sàn p của kiểm định hoán vị — không in số chính-xác-giả
    assert "p <" in src
    assert "1 / (draws + 1)" in src


def test_xem_mot_phien_qua_query_phien():
    """docs/demo-vang.md: 'trang kết quả của web với phiên tương ứng' — ba
    trạng thái demo vàng phải mở được qua /ket-qua?phien=<id>."""
    src = _read(KET_QUA)
    assert 'get("phien")' in src
    assert "getBaoCao(phien)" in src
    assert "verdictFromKetQua" in src


# ---------------------------------------------------------------------------
# 8. Kiểm toán thử thật 25/09/2026 (runtime.md §3.0, §3.2, §3.3, §3.4)
# ---------------------------------------------------------------------------
#
# Chạy THẬT các hàm thuần của trang bằng node (tách nguyên văn khỏi mã nguồn,
# node ≥ 22 tự bỏ chú thích kiểu — cùng cách tests/test_web_desk_v3.py). Gate
# đọc chữ không bắt được vụ sập 25/09: `verdictState` trả "null" khi máy chủ
# gửi estimable=true nhưng KTC null, rồi VerdictNull gọi `v.ciLow!.toFixed`.

FORMAT_TS = SRC / "lib" / "format.ts"


def _tach(src: str, ten: str) -> str:
    """Tách nguyên văn một khai báo cấp cao nhất (function/const) khỏi nguồn."""
    lines = src.replace("\r\n", "\n").split("\n")
    head = re.compile(rf"^(?:export )?(?:function|const) {re.escape(ten)}\b")
    for i, line in enumerate(lines):
        if not head.match(line):
            continue
        la_const = line.startswith(("const ", "export const "))
        if la_const and line.rstrip().endswith(";"):
            return line
        for j in range(i + 1, len(lines)):
            cuoi = lines[j].rstrip()
            # Hằng chuỗi nối nhiều dòng kết thúc ở dòng đầu tiên có dấu `;`.
            if la_const and cuoi.endswith(";"):
                return "\n".join(lines[i : j + 1])
            if not la_const and cuoi == "}":
                return "\n".join(lines[i : j + 1])
        break
    raise AssertionError(f"không tách được khai báo {ten!r}")


def _node(tmp_path: Path, khai_bao: list[tuple[Path, str]], bieu_thuc: str):
    import json
    import shutil
    import subprocess

    import pytest

    node = shutil.which("node")
    if not node:
        pytest.skip("không có node — bỏ qua phần chạy thử hàm thuần")
    mo_dun = "\n\n".join(_tach(_read(p), ten) for p, ten in khai_bao)
    tep = tmp_path / "ket_qua_thuan.mts"
    tep.write_text(mo_dun + f"\nconsole.log(JSON.stringify({bieu_thuc}));\n", encoding="utf-8")
    out = subprocess.run(
        [node, "--experimental-strip-types", "--no-warnings", str(tep)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if out.returncode != 0 and "bad option" in out.stderr:
        pytest.skip("node quá cũ, chưa bỏ được chú thích kiểu")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def _ham_verdict() -> list[tuple[Path, str]]:
    src = _read(KET_QUA)
    ten = ["verdictState", "verdictFromSummary", "verdictFromKetQua"]
    # Hằng câu lý do (nếu có) phải đi cùng các hàm dùng nó.
    ten = list(re.findall(r"(?m)^const (KTC_\w+)\b", src)) + ten
    return [(KET_QUA, t) for t in ten]


def test_ktc_null_la_chua_du_khong_phai_null(tmp_path):
    """Sự cố 25/09 (runtime.md §3.0): phiên ≥ 4 khối, 0 lượt nhấp → máy chủ trả
    {estimable: true, estimate: 0, ci_low: null, ci_high: null}; trang sập với
    `Cannot read properties of null (reading 'toFixed')`. KTC không tính được thì
    KHÔNG có kết luận nào để vẽ — trạng thái phải là CHƯA ĐỦ, kèm lý do."""
    kq = {
        "estimable": True,
        "estimate": 0.0,
        "ci_low": None,
        "ci_high": None,
        "p_value": 1.0,
        "n_draws": 999,
        "n_blocks": 4,
        "n_on": 2,
        "n_off": 2,
        "khoa": False,
        "ly_do_khoa": None,
        "message": None,
    }
    gop = {
        "env": "real",
        "estimable": True,
        "estimate": 0.0,
        "ci_low": None,
        "ci_high": None,
        "p_value": 1.0,
        "n_draws": 999,
        "n_blocks": 8,
        "n_on": 4,
        "n_off": 4,
        "n_sessions": 2,
        "message": None,
    }
    import json

    ra = _node(
        tmp_path,
        _ham_verdict(),
        "["
        "verdictState(true, null, null),"
        "verdictState(true, -0.2, null),"
        "verdictState(true, null, 0.3),"
        "verdictState(true, 0.1, 0.5),"
        "verdictState(true, -0.5, -0.1),"
        "verdictState(true, -0.1, 0.2),"
        "verdictState(false, 0.1, 0.5),"
        f"verdictFromKetQua({json.dumps(kq)}, false, null),"
        f"verdictFromSummary({json.dumps(gop)})"
        "]",
    )
    assert ra[:7] == ["chuadu", "chuadu", "chuadu", "duong", "am", "null", "chuadu"]
    for v in ra[7:]:
        assert v["state"] == "chuadu", v
        assert v["lyDo"], "CHƯA ĐỦ vì KTC null phải nói lý do, không để câu mặc định chung chung"
        assert "khoảng tin cậy" in v["lyDo"]


def test_khong_con_khang_dinh_khong_null_tren_so_nhan_qua():
    """Dấu `!` của TypeScript chỉ tắt tiếng trình biên dịch, không chặn được null
    lúc chạy — chính nó để vụ sập 25/09 lọt qua `tsc --noEmit`."""
    src = _render(_read(KET_QUA))
    con = re.findall(r"\b(?:v|verdict)\.\w+!", src)
    assert not con, f"còn khẳng định không-null trên số liệu verdict: {con}"


def test_con_dau_tren_du_lieu_mau_khong_goi_la_that():
    """Kiểm toán 25/09 (§3.3): chip xanh "TÁC ĐỘNG THẬT" đứng ngay cạnh "DEMO —
    dữ liệu mẫu" trên /ket-qua?env=demo — ảnh chụp màn hình dễ bị hiểu sai.
    Trên dữ liệu mẫu, con dấu nói đúng điều KTC nói: hiệu ứng rõ, không chứa 0."""
    body = _read(KET_QUA).split("function VerdictCoTacDong")[1].split("\nfunction ")[0]
    m = re.search(
        r'v\.isDemo\s*\?\s*"(HIỆU ỨNG RÕ[^"]*)"\s*:\s*"TÁC ĐỘNG THẬT · KTC 95% không chứa 0"',
        body,
    )
    assert m, "con dấu phải rẽ nhánh theo v.isDemo — dữ liệu mẫu không được gọi là THẬT"
    assert "KTC 95% không chứa 0" in m.group(1), "con dấu demo vẫn phải mang KTC (phản biện #1)"
    assert "THẬT" not in m.group(1)


def test_phien_chay_thu_co_muc_va_huy_hieu_rieng():
    """Kiểm toán 25/09 (§3.2): tập dượt một lần bằng "Chạy thử" là /ket-qua hiện
    "PHIÊN THẬT · 1 phiên" — trong khi hồ sơ nói 0 phiên thí nghiệm thật. Phiên
    chạy thử (dry_run) bị loại khỏi kết quả gộp (PREREGISTRATION §8.2) nên phải
    đứng ở mục riêng và đeo huy hiệu CHẠY THỬ ở mọi dòng."""
    src = _render(_read(KET_QUA))
    assert "s.dry_run !== true" in src, "mục Phiên thật phải loại phiên chạy thử"
    assert "s.dry_run === true" in src, "phải có danh sách phiên chạy thử riêng"
    assert "chayThuSessions" in src
    assert re.search(r">\s*Phiên chạy thử\s*</SectionTitle>", src), (
        "thiếu tiêu đề mục Phiên chạy thử"
    )
    rows = src.split("function SessionRows")[1].split("\nfunction ")[0]
    assert re.search(r"s\.dry_run\s*\?\s*<Badge[^>]*>\s*CHẠY THỬ\s*</Badge>", rows), (
        "từng dòng phiên chạy thử phải đeo huy hiệu CHẠY THỬ"
    )


def test_so_thap_phan_theo_vi_vn(tmp_path):
    """Kiểm toán 25/09 (§3.4): "+0.533" đứng cạnh "39.000 ₫" — người đọc Việt hiểu
    0.533 thành 533. Số nhân quả trên /ket-qua và /bao-cao đi qua một bộ định
    dạng vi-VN chung, không `toFixed` (dấu chấm thập phân kiểu Anh)."""
    for trang in (KET_QUA, BAO_CAO):
        src = _render(_read(trang))
        assert ".toFixed(" not in src, f"{trang.parent.name}: còn toFixed — in dấu chấm thập phân"
        assert "fmtThapPhan" in src
    ra = _node(
        tmp_path,
        [(FORMAT_TS, "fmtThapPhan")],
        "[fmtThapPhan(0.533, 3), fmtThapPhan(-0.49, 3), fmtThapPhan(1234.5, 1),"
        " fmtThapPhan(0.001, 4), fmtThapPhan(0, 3)]",
    )
    assert ra == ["0,533", "-0,490", "1.234,5", "0,0010", "0,000"]


def test_bao_cao_khong_in_uoc_luong_khi_thieu_ktc():
    """Kiểm toán 25/09 (runtime.md §3.0): máy chủ trả estimable=true, ước lượng 0
    và KTC null khi lượt nhấp THIẾU; /bao-cao từng in "0.000 · KTC 95% [— … —]".
    Khối số chỉ được vẽ khi có ĐỦ hai đầu KTC — gate đọc chính điều kiện render
    (phản biện 25/09: trước đó chỉ `tsc` gác, pytest không đỏ nếu điều kiện bị gỡ)."""
    src = _render(_read(BAO_CAO))
    assert re.search(
        r"kq\.estimable\s*&&\s*kq\.estimate != null\s*&&\s*kq\.ci_low != null"
        r"\s*&&\s*kq\.ci_high != null\s*\?",
        src,
    ), "khối ước lượng nhân quả trên /bao-cao phải đòi đủ ci_low và ci_high"
