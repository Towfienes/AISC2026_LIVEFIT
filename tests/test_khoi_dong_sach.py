"""Gói C — lệnh khởi động sạch và cổng chống "trang vỡ vì thiếu CSS".

Sự cố 13/09/2026, ba lỗi cùng một buổi, tất cả đều lọt qua 894 test nhanh +
13 gate chậm + ``tsc --noEmit`` + ``ruff``:

1. **Trang chủ render thành HTML thô.** ``/_next/static/css/app/layout.css``
   trả 404 vì nhiều tiến trình ``next dev``/``next build`` chạy song song cùng
   ghi một thư mục ``.next`` (``.next/static/css`` rỗng), lại thêm một tiến
   trình ``next`` cũ vẫn giữ cổng 3000 và phục vụ từ thư mục đã bị xoá.
2. **Cổng bị chiếm im lặng** — không lệnh nào nói PID nào đang giữ 3000/8000.
3. **Kho chết mà không ai biết** — PostgreSQL tắt hẳn, không ai nghe 5432.

Tệp này khoá phần RẺ và TẤT ĐỊNH của gói C: các hàm thuần mà cả
``scripts/chay_local.py`` (lệnh chạy hằng ngày) lẫn ``scripts/gate_css_web.py``
(cổng CSS) đều đứng lên, cộng với các bất biến cấu hình mà sự cố đã chứng minh
là cần thiết. Phần ĐẮT — dựng ``next build`` thật rồi tải tệp CSS về cân — nằm
ở ``tests/test_web_css_gate.py`` (đánh dấu ``slow``, ~60 giây).

Ranh giới cố ý: không test nào ở đây được mở tiến trình con hay chạm mạng.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
WEB = REPO / "web"
DOCS = REPO / "docs"
SCRIPTS = REPO / "scripts"


def _nap(ten: str, tep: Path):
    """scripts/ không phải package -> nạp module theo đường dẫn."""
    spec = importlib.util.spec_from_file_location(ten, tep)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[ten] = mod
    spec.loader.exec_module(mod)
    return mod


cl = _nap("livelift_chay_local_test", SCRIPTS / "chay_local.py")
gate = _nap("livelift_gate_css_test", SCRIPTS / "gate_css_web.py")


# ===========================================================================
# (a) Cổng bị ai giữ — phải chỉ đúng PID, và không bao giờ giết nhầm
# ===========================================================================

# Đầu ra thật của `netstat -ano -p TCP` trên máy chủ dự án (13/09/2026), đã
# thêm hai dòng bẫy: cổng 30000 (tiền tố trùng) và một kết nối ĐI RA tới cổng
# 3000 của máy khác (cổng 3000 nằm ở cột Foreign Address, không phải Local).
NETSTAT_THAT = """
Active Connections

  Proto  Local Address          Foreign Address        State           PID
  TCP    0.0.0.0:135            0.0.0.0:0              LISTENING       1124
  TCP    [::]:3000              [::]:0                 LISTENING       30060
  TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       37160
  TCP    0.0.0.0:30000          0.0.0.0:0              LISTENING       999
  TCP    127.0.0.1:55123        127.0.0.1:3000         ESTABLISHED     4242
  TCP    192.168.1.9:61003      104.18.32.7:3000       ESTABLISHED     7777
"""


def test_netstat_chi_bat_tien_trinh_dang_nghe_dung_cong():
    assert cl.phan_tich_netstat(NETSTAT_THAT, 3000) == [30060]
    assert cl.phan_tich_netstat(NETSTAT_THAT, 8000) == [37160]
    assert cl.phan_tich_netstat(NETSTAT_THAT, 30000) == [999]


def test_netstat_khong_nham_cong_tien_to_trung_hay_cong_doi_tac():
    """3000 không được kéo theo 30000, và cột Foreign Address không tính.

    Cả hai nhầm lẫn này đều kết thúc bằng việc giết nhầm một tiến trình đang
    làm việc khác — đắt hơn nhiều so với sự cố ban đầu.
    """
    pids_3000 = cl.phan_tich_netstat(NETSTAT_THAT, 3000)
    assert 999 not in pids_3000, "cổng 30000 bị nhận nhầm thành 3000"
    assert 4242 not in pids_3000, "kết nối ĐI RA tới cổng 3000 bị nhận nhầm là đang nghe"
    assert 7777 not in pids_3000


def test_netstat_bo_qua_dong_rac():
    assert cl.phan_tich_netstat("", 3000) == []
    assert cl.phan_tich_netstat("rác rưởi\nlinh tinh\n", 3000) == []
    assert cl.phan_tich_netstat("  TCP  0.0.0.0:3000  0.0.0.0:0  LISTENING  x\n", 3000) == []


def test_doc_dong_pid_cua_powershell():
    ra = cl.phan_tich_dong_pid("30060\tnode\n37160\tpython\n\n30060\tnode\n")
    assert [(t.pid, t.ten) for t in ra] == [(30060, "node"), (37160, "python")]


def test_dong_pid_thieu_ten_van_dung_duoc():
    assert cl.phan_tich_dong_pid("4242\t")[0].ten == "?"


def test_khong_bao_gio_giet_tien_trinh_khi_chua_duoc_dong_y(monkeypatch, capsys):
    """Không có TTY để hỏi + không có --force => TUYỆT ĐỐI không giết.

    Đây là bất biến an toàn: lệnh này sẽ được chạy từ script và từ CI, nơi
    ``input()`` không hỏi được ai. Im lặng giết một tiến trình lạ trên máy chủ
    dự án là cái giá cao hơn nhiều so với việc dừng lại và in hướng dẫn.
    """
    da_giet: list[int] = []
    monkeypatch.setattr(cl, "tien_trinh_giu_cong", lambda _c: [cl.TienTrinh(30060, "node")])
    monkeypatch.setattr(cl, "dung_tien_trinh", lambda tt: da_giet.append(tt.pid) or True)

    ok = cl.buoc_don_cong(3000, "web", force=False)

    assert ok is False
    assert da_giet == [], "đã giết tiến trình mà chưa được phép"
    ra = capsys.readouterr().out
    assert "30060" in ra, "phải in PID của tiến trình đang giữ cổng"
    assert "node" in ra, "phải in TÊN tiến trình, không chỉ con số PID"
    assert "--force" in ra, "phải chỉ cho người dùng cách cho phép"


def test_co_force_thi_moi_duoc_giet(monkeypatch):
    da_giet: list[int] = []
    lan = {"n": 0}

    def gia_lap(_cong):
        lan["n"] += 1
        return [cl.TienTrinh(30060, "node")] if lan["n"] == 1 else []

    monkeypatch.setattr(cl, "tien_trinh_giu_cong", gia_lap)
    monkeypatch.setattr(cl, "dung_tien_trinh", lambda tt: da_giet.append(tt.pid) or True)
    monkeypatch.setattr(cl.time, "sleep", lambda _s: None)

    assert cl.buoc_don_cong(3000, "web", force=True) is True
    assert da_giet == [30060]


def test_hoi_dong_y_tra_ve_false_khi_khong_co_tty():
    """pytest chạy không có stdin tương tác -> mặc định là KHÔNG."""
    assert cl._hoi_dong_y("dừng chứ?") is False


# ===========================================================================
# (b) Thư mục build rác — nguyên nhân gốc của trang vỡ
# ===========================================================================


def test_chi_xoa_thu_muc_next_gach_ngang_thua():
    ten = [
        ".next",  # của người gõ `npm run dev` bằng tay — GIỮ
        ".next-chay-local",  # thư mục lệnh này sắp dùng — GIỮ
        ".next-kiemchung",  # rác của một tác tử đã chết — XOÁ
        ".next-gate-css",  # rác của cổng CSS lần chạy trước — XOÁ
        "node_modules",
        "src",
    ]
    assert cl.chon_thu_muc_rac(ten, dang_dung=".next-chay-local") == [
        ".next-gate-css",
        ".next-kiemchung",
    ]


def test_khong_bao_gio_xoa_thu_muc_next_goc():
    """`.next` là của người khác. Xoá nó giữa phiên = tái diễn đúng sự cố."""
    assert cl.chon_thu_muc_rac([".next"], dang_dung=".next-chay-local") == []
    assert ".next" not in cl.chon_thu_muc_rac([".next", ".next-a"], dang_dung=".next")


def test_khong_xoa_thu_muc_build_vua_duoc_ghi():
    """Thư mục mới nguyên nhiều khả năng đang có tiến trình khác dùng.

    Xoá thư mục build của một tiến trình đang sống là tái tạo ĐÚNG sự cố
    13/09 cho người khác, chỉ đổi vai. Ngưỡng 300 giây: một `next build`
    đo được ~51 giây, nên thư mục im lặng suốt 5 phút gần như chắc chắn là
    của một tiến trình đã chết.
    """
    ten = [".next-dang-chay", ".next-da-chet"]
    tuoi = {".next-dang-chay": 12.0, ".next-da-chet": 9_000.0}
    assert cl.chon_thu_muc_rac(ten, dang_dung=".next-chay-local", tuoi_giay=tuoi) == [
        ".next-da-chet"
    ]


def test_khong_biet_tuoi_thi_van_coi_la_rac():
    """Không đọc được mtime -> mặc định vẫn dọn; đây là rác của lần chạy trước."""
    assert cl.chon_thu_muc_rac([".next-la"], dang_dung=".next-chay-local") == [".next-la"]


def test_lenh_chay_hang_ngay_khong_dung_chung_thu_muc_next():
    """Bất biến chống tranh chấp: mặc định phải KHÁC `.next` và khác cổng CSS."""
    assert cl.DIST_DIR_MAC_DINH != ".next"
    assert cl.DIST_DIR_MAC_DINH.startswith(".next-")
    assert gate.DIST_DIR_GATE.startswith(".next-")
    assert gate.DIST_DIR_GATE != cl.DIST_DIR_MAC_DINH


# ===========================================================================
# (c) Kho dữ liệu — thiếu nguồn thì TUYÊN BỐ thiếu, không bịa
# ===========================================================================


def _kho(song: bool, muc_do: str, chi_tiet: str = "127.0.0.1:5432"):
    return cl.chon_che_do_kho(song, muc_do, chi_tiet, "data/snapshot/livelift-store.json", 30.0)


def test_postgres_tra_loi_truy_van_thi_dung_kho_ben_vung():
    kq = _kho(True, "truy-van")
    assert kq.backend == "postgres"
    assert kq.ben_vung is True


def test_postgres_chet_thi_tu_chon_memory_va_noi_ro_du_lieu_nam_trong_ram():
    """Đúng tình huống 13/09: 5432 không ai nghe.

    Không được im lặng rơi về RAM. Câu thông báo phải nói đủ ba điều người
    vận hành cần: nằm ở RAM, chụp lại bao lâu một lần, và chụp vào đâu.
    """
    kq = _kho(False, "tat-cong", "không ai nghe 127.0.0.1:5432")
    assert kq.backend == "memory"
    assert kq.ben_vung is False
    assert "RAM" in kq.thong_diep
    assert "30 giây" in kq.thong_diep
    assert "data/snapshot/livelift-store.json" in kq.thong_diep


def test_cong_mo_nhung_truy_van_hong_van_bi_coi_la_kho_chet():
    """Cổng mở KHÔNG phải bằng chứng kho sống — /health ngày 13/09 đã tin nhầm."""
    kq = _kho(False, "khong-noi-duoc", "127.0.0.1:5432 mở nhưng truy vấn hỏng")
    assert kq.backend == "memory"
    assert kq.ben_vung is False
    assert "RAM" in kq.thong_diep


def test_cong_mo_ma_khong_kiem_sau_duoc_thi_phai_noi_la_chua_kiem():
    """Không có psycopg: vẫn dùng postgres theo cấu hình, nhưng NÓI RÕ là chưa đo."""
    kq = _kho(True, "cong-mo", "127.0.0.1:5432 mở, nhưng máy này chưa cài psycopg")
    assert kq.backend == "postgres"
    assert "CHƯA kiểm" in kq.thong_diep


def test_ep_kho_postgres_thi_phai_ra_postgres_chu_khong_am_tham_ra_memory():
    """`--kho postgres` mà lại chạy RAM là đúng cái bẫy dự án đang chống.

    Hồi quy: nhánh "ép buộc" ban đầu rơi thẳng xuống nhánh memory vì nó không
    khớp mức độ đo nào — lệnh sẽ nhận `--kho postgres` rồi lặng lẽ chạy RAM.
    """
    kq = _kho(True, "ep-buoc", "do người dùng ép bằng --kho postgres")
    assert kq.backend == "postgres"
    assert "ÉP" in kq.thong_diep
    assert "KHÔNG đo" in kq.thong_diep, "bị ép thì phải nói rõ là chưa đo gì"


def test_ep_kho_memory_van_phai_nhac_du_lieu_nam_trong_ram():
    kq = _kho(False, "ep-buoc", "do người dùng ép bằng --kho memory")
    assert kq.backend == "memory"
    assert kq.ben_vung is False
    assert "RAM" in kq.thong_diep


def test_tach_host_cong_tu_database_url():
    assert cl.tach_host_cong("postgresql://u:p@127.0.0.1:5432/livelift") == ("127.0.0.1", 5432)
    assert cl.tach_host_cong("postgresql://u:p@db.local/livelift") == ("db.local", 5432)


def test_do_postgres_that_khi_khong_ai_nghe_cong(monkeypatch):
    """Cổng đóng -> trả 'tat-cong' NGAY, không chờ psycopg hết giờ.

    Sự cố 13/09 còn có một nhánh nữa: `/sessions` treo 30 giây khi DB chết.
    Lệnh khởi động không được phép rơi vào cùng cái bẫy ấy.
    """
    monkeypatch.setattr(cl, "cong_dang_mo", lambda *_a, **_k: False)
    song, muc_do, chi_tiet = cl.kiem_tra_postgres("postgresql://u:p@127.0.0.1:5432/x")
    assert (song, muc_do) == (False, "tat-cong")
    assert "5432" in chi_tiet


# ===========================================================================
# (e) Phép thử CSS — hạt nhân của cổng chống tái diễn
# ===========================================================================

# Thẻ link thật mà `next dev` sinh ra (13/09/2026) — thứ VẪN nằm đúng chỗ
# trong lúc trang vỡ.
HTML_DEV = (
    '<!DOCTYPE html><html lang="vi"><head>'
    '<link rel="stylesheet" href="/_next/static/css/app/layout.css?v=1789314446162" '
    'data-precedence="next_static/css/app/layout.css"/>'
    "</head><body>bàn điều khiển</body></html>"
)
# Thẻ link thật của bản `next build` (đo lại 13/09/2026).
HTML_BUILD = (
    '<!DOCTYPE html><html lang="vi"><head>'
    '<link rel="preload" as="style" href="/_next/static/css/f721f4d3.css"/>'
    '<link rel="stylesheet" href="/_next/static/css/f721f4d3.css" data-precedence="next"/>'
    "</head><body></body></html>"
)


def test_tim_thay_the_stylesheet_o_ca_hai_dang_dev_va_build():
    assert cl.tim_link_css(HTML_DEV) == ["/_next/static/css/app/layout.css?v=1789314446162"]
    assert cl.tim_link_css(HTML_BUILD) == ["/_next/static/css/f721f4d3.css"]


def test_the_preload_khong_duoc_tinh_la_co_css():
    """`rel=preload as=style` chỉ là gợi ý tải trước; thiếu stylesheet vẫn trắng."""
    assert cl.tim_link_css('<link rel="preload" as="style" href="/a.css"/>') == []


def test_tim_link_css_khong_phu_thuoc_thu_tu_thuoc_tinh_hay_kieu_nhay():
    assert cl.tim_link_css("<link href='/a.css' rel='stylesheet'>") == ["/a.css"]
    assert cl.tim_link_css('<LINK REL="STYLESHEET" HREF="/b.css">') == ["/b.css"]


def test_trang_khong_co_the_stylesheet_nao_la_hong():
    assert cl.tim_link_css("<html><head><title>x</title></head></html>") == []


def _css_gia(byte: int, token: tuple[str, ...] = cl.CSS_TOKEN_BAT_BUOC) -> bytes:
    dau = ":root{" + ";".join(f"{t}:#07080d" for t in token) + "}"
    return (dau + "/*" + "đ" * byte + "*/").encode("utf-8")


def test_css_that_thi_dat():
    assert cl.kiem_tra_noi_dung_css(_css_gia(20_000)) == []


def test_hoi_quy_su_co_1309_tep_css_tra_404_phai_bi_bat():
    """CHÍNH sự cố: trang chủ 200, thẻ <link> còn nguyên, tệp CSS trả 404.

    Trang lỗi 404 của Next đo được 7.083 byte HTML (13/09/2026) — đây là bản
    tái hiện thu nhỏ của nó. Phép thử phải đỏ vì ÍT NHẤT bốn lẽ độc lập, để
    một thay đổi nhỏ của Next không làm cổng câm.
    """
    trang_404 = b"<!DOCTYPE html><html><head><title>404</title></head><body>404</body></html>"
    loi = cl.kiem_tra_noi_dung_css(trang_404, ma_http=404, kieu_noi_dung="text/html; charset=utf-8")
    assert len(loi) >= 4
    assert any("404" in x for x in loi)
    assert any("HTML" in x for x in loi)
    assert any("byte" in x for x in loi)
    assert any("--canvas" in x for x in loi)


def test_tep_css_qua_nho_bi_bat_du_tra_200():
    """Build dở dang trả một tệp CSS cụt — vẫn là trang vỡ."""
    loi = cl.kiem_tra_noi_dung_css(_css_gia(10), ma_http=200, kieu_noi_dung="text/css")
    assert any("byte" in x for x in loi)


def test_css_du_to_nhung_khong_phai_cua_du_an_bi_bat():
    """Một tệp reset/vendor to đùng không phải là giao diện LiveLift."""
    thua = b"/*" + b"a" * 30_000 + b"*/ body{margin:0}"
    loi = cl.kiem_tra_noi_dung_css(thua, ma_http=200, kieu_noi_dung="text/css")
    assert any("--canvas" in x and "--brand" in x for x in loi)


def test_nguong_va_token_phai_khop_voi_nguon_that():
    """Cổng không được đo bằng hằng số bịa: đối chiếu với globals.css.

    Nếu ai đó đổi tên token thiết kế, test này đỏ TRƯỚC khi cổng CSS âm thầm
    trở nên vô dụng (nó vẫn xanh trên một tệp CSS bất kỳ).
    """
    globals_css = (WEB / "src" / "app" / "globals.css").read_text(encoding="utf-8")
    for token in cl.CSS_TOKEN_BAT_BUOC:
        assert f"{token}:" in globals_css, f"{token} không còn được khai báo trong globals.css"
    assert cl.CSS_TOI_THIEU_BYTE == 10 * 1024
    assert len(globals_css.encode("utf-8")) > cl.CSS_TOI_THIEU_BYTE, (
        "ngưỡng 10 KB phải thấp hơn chính tệp nguồn, nếu không cổng sẽ báo động giả"
    )


def test_cong_css_dung_chung_dung_mot_phep_do_voi_lenh_chay_hang_ngay():
    """Cổng và lệnh chạy tay phải đo CÙNG một thứ, không phải hai bản sao.

    Hai bản sao của cùng một phép thử là cách chắc chắn nhất để cổng xanh mà
    sản phẩm vẫn vỡ: người ta sửa một bên và quên bên kia.
    """
    assert gate.chay_local.CSS_TOI_THIEU_BYTE == cl.CSS_TOI_THIEU_BYTE
    assert gate.chay_local.CSS_TOKEN_BAT_BUOC == cl.CSS_TOKEN_BAT_BUOC
    ma_nguon = (SCRIPTS / "gate_css_web.py").read_text(encoding="utf-8")
    assert "chay_local.kiem_tra_css_cua_trang" in ma_nguon, (
        "cổng phải GỌI hàm đo của chay_local, không được chép lại logic"
    )


# ===========================================================================
# Chống tranh chấp thư mục build — cấu hình phải nói ra luật
# ===========================================================================


def test_next_config_doc_bien_livelift_dist_dir():
    cfg = (WEB / "next.config.mjs").read_text(encoding="utf-8")
    assert "process.env.LIVELIFT_DIST_DIR" in cfg
    assert "distDir" in cfg


def test_next_config_ghi_ro_luat_moi_tien_trinh_song_song_mot_thu_muc():
    """Luật phải nằm ngay chỗ người ta đọc khi định chạy máy chủ thứ hai."""
    cfg = (WEB / "next.config.mjs").read_text(encoding="utf-8")
    assert "song song" in cfg, "next.config.mjs phải nêu luật cho tiến trình chạy song song"
    assert "13/09" in cfg, "phải dẫn sự cố để người sau biết luật này không phải tuỳ hứng"


def test_gitignore_web_bo_qua_moi_thu_muc_build_phu():
    gi = (WEB / ".gitignore").read_text(encoding="utf-8")
    assert "/.next-*/" in gi


def test_makefile_co_muc_chay_local_va_cong_css():
    mk = (REPO / "Makefile").read_text(encoding="utf-8")
    assert "chay-local:" in mk
    assert "gate-css:" in mk
    assert "scripts/chay_local.py" in mk
    assert "scripts/gate_css_web.py" in mk


# ===========================================================================
# Tài liệu — người không chuyên phải tự sửa được
# ===========================================================================

SO_TAY = DOCS / "khoi-dong-va-su-co.md"


def test_so_tay_su_co_ton_tai_va_co_bang_trieu_chung():
    assert SO_TAY.is_file(), "thiếu docs/khoi-dong-va-su-co.md"
    van = SO_TAY.read_text(encoding="utf-8")
    assert "| Triệu chứng | Nguyên nhân | Lệnh sửa |" in van


@pytest.mark.parametrize(
    "trieu_chung",
    [
        "HTML thô",  # trang vỡ vì thiếu CSS
        "cổng 3000",  # cổng bị chiếm
        "PostgreSQL",  # kho chết
        "/health",  # health nói dối
    ],
)
def test_so_tay_co_du_bon_su_co_da_gap(trieu_chung):
    assert trieu_chung in SO_TAY.read_text(encoding="utf-8")


def test_so_tay_chi_ro_cach_chay_cong_css_truoc_khi_demo():
    van = SO_TAY.read_text(encoding="utf-8")
    assert "scripts/gate_css_web.py" in van
    assert "giám khảo" in van, "phải nói rõ chạy cổng này TRƯỚC khi demo cho giám khảo"
    assert "scripts/chay_local.py" in van


def test_so_tay_khong_hua_docker_dang_song():
    """Ngày 13/09 Docker đã chết hẳn. Tài liệu không được giả vờ ngược lại."""
    van = SO_TAY.read_text(encoding="utf-8")
    assert "docker" in van.lower(), "phải nói tới Docker vì đó là điều kiện của kho bền vững"
    assert "RAM" in van


def test_so_su_co_co_dong_cho_su_co_1309():
    """HARNESS §3: mỗi lỗi một dòng, đúng định dạng bảng hiện có."""
    van = (DOCS / "incident-log.md").read_text(encoding="utf-8")
    dong = [d for d in van.splitlines() if d.startswith("| 13/09/2026") and "gói C" in d]
    assert len(dong) >= 2, "thiếu dòng sổ sự cố 13/09/2026 cho gói C (trang vỡ + cổng bị chiếm)"
    for d in dong:
        assert len(re.findall(r"(?<!\\)\|", d)) == 6, "phải đủ 5 cột như bảng hiện có"
    assert any("gate_css_web" in d for d in dong), "cột gate mới phải trỏ tới cổng thật"
    assert any("HTML THÔ" in d for d in dong), "phải ghi triệu chứng người dùng thật sự thấy"
