"""Gate gói B-PROBE: trang web phải phân biệt MÁY CHỦ CHẾT với MÁY CHỦ CHẬM /
KHO SUY GIẢM — và không bao giờ được nói sai trạng thái.

SỰ CỐ 13/09/2026 (ba lỗi chồng nhau, cùng một gốc "hỏi sai câu hỏi"):

1. Trang chủ thăm dò máy chủ bằng ``listSessions(2500)`` — một truy vấn ĐỌC KHO.
   Khi PostgreSQL chết, ``GET /sessions`` treo 30 giây rồi trả 500, nên probe
   2,5 giây LUÔN hết giờ và trang in *"Chưa kết nối được máy chủ"* TRONG KHI API
   vẫn đang chạy và trả lời ``/health`` trong 2 mili giây.
2. Probe chỉ có hai trạng thái (sống / chết) cho một thế giới có ba: máy chủ
   chạy nhưng kho không lưu được là trạng thái RIÊNG và phải nói riêng.
3. 2,5 giây quá ngắn cho một máy dev lạnh, nên CHẬM bị kết luận nhầm là CHẾT.

Gate này đọc thẳng mã nguồn web (tiền lệ ``test_web_api_contract.py``) và khoá
lại bốn bất biến:

* probe hỏi ``/health``, KHÔNG hỏi ``/sessions``;
* ba trạng thái, ba câu tiếng Việt KHÁC NHAU;
* câu "Chưa kết nối" chỉ tồn tại ở nhánh CHẾT — không bao giờ khi máy chủ trả
  lời (kể cả khi nó trả 5xx: trả lời được nghĩa là đang sống);
* thời gian chờ ≥ 4 giây và có đúng một lần thử lại trước khi tuyên bố chết.

Kèm một bài kiểm tra hai đầu: ``/health`` của API thật phải mang đúng các trường
mà bộ phân loại phía web đọc — nếu hợp đồng lệch, phân loại sẽ sai âm thầm.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore

ROOT = Path(__file__).resolve().parents[1]
WEB_SRC = ROOT / "web" / "src"
API_TS = WEB_SRC / "lib" / "api.ts"
HOME_TSX = WEB_SRC / "app" / "page.tsx"
MODECHIP_TSX = WEB_SRC / "components" / "ModeChip.tsx"
KETQUA_TSX = WEB_SRC / "app" / "ket-qua" / "page.tsx"
REPLAY_TSX = WEB_SRC / "app" / "replay" / "page.tsx"
BATDAU_TSX = WEB_SRC / "app" / "bat-dau" / "page.tsx"
BATDAUVOD_TSX = WEB_SRC / "components" / "BatDauVod.tsx"
GUIDE = ROOT / "docs" / "HUONG-DAN-SU-DUNG.md"

#: Câu đã nói dối ngày 13/09: chỉ được phép xuất hiện ở nhánh CHẾT.
CAU_CHUA_KET_NOI = "Chưa kết nối được máy chủ"


def read(path: Path) -> str:
    assert path.exists(), f"không tìm thấy {path}"
    return path.read_text(encoding="utf-8")


def block(src: str, start: str, end: str = "\n}") -> str:
    """Cắt khối mã bắt đầu từ ``start`` tới dấu đóng ``end`` đầu tiên."""
    i = src.index(start)
    j = src.index(end, i)
    return src[i : j + len(end)]


_COMMENT_RE = re.compile(r"/\*[\s\S]*?\*/|(?<![:\w])//[^\n]*")


def strip_comments(src: str) -> str:
    """Bỏ chú thích: một câu nằm trong chú thích không bao giờ hiện lên màn
    hình, nên nó không được tính khi ta hỏi 'trang có in câu này không'."""
    return _COMMENT_RE.sub("", src)


@pytest.fixture(scope="module")
def api_ts() -> str:
    return read(API_TS)


@pytest.fixture(scope="module")
def home_tsx() -> str:
    return read(HOME_TSX)


# ---------------------------------------------------------------------------
# 1. Probe hỏi /health, KHÔNG hỏi /sessions
# ---------------------------------------------------------------------------


def test_probe_ton_tai_va_hoi_health(api_ts: str) -> None:
    assert "export async function probeServer" in api_ts, (
        "api.ts phải có `probeServer()` — điểm hỏi duy nhất về sức khoẻ máy chủ"
    )
    probe_once = block(api_ts, "async function probeOnce")
    assert "/health" in probe_once, "probe phải gọi `/health` — endpoint rẻ, không đọc kho"
    assert "/sessions" not in probe_once, (
        "probe KHÔNG được hỏi `/sessions`: đó là truy vấn đọc kho, nó treo 30 giây "
        "khi database chết và biến một máy chủ đang sống thành 'chưa kết nối' (13/09/2026)"
    )


def test_trang_chu_tham_do_bang_probe_chu_khong_phai_list_sessions(home_tsx: str) -> None:
    assert "probeServer()" in home_tsx, "trang chủ phải thăm dò bằng probeServer()"
    # `listSessions` vẫn được dùng SAU khi seed dữ liệu demo (đó là đọc dữ liệu
    # thật, không phải thăm dò) — điều bị cấm là dùng nó làm probe.
    assert "listSessions(2500)" not in home_tsx, (
        "trang chủ quay lại thăm dò bằng listSessions(2500) — chính lỗi 13/09/2026"
    )
    effect = block(home_tsx, "void probeServer", "}, []);")
    assert "listSessions" not in effect, "vòng thăm dò không được gọi listSessions"
    assert "/sessions" not in effect


def test_probe_khong_bao_gio_nem(api_ts: str) -> None:
    """Probe phải LUÔN trả về một trạng thái: một exception lọt ra ngoài sẽ để
    giao diện kẹt ở 'đang kiểm tra' vĩnh viễn."""
    probe_once = block(api_ts, "async function probeOnce")
    assert "} catch {" in probe_once, "probeOnce phải bắt mọi lỗi"
    assert '"down"' in probe_once, "lỗi phải được quy về trạng thái CHẾT, không ném ra ngoài"


# ---------------------------------------------------------------------------
# 2. BA trạng thái, BA câu khác nhau
# ---------------------------------------------------------------------------


def test_ba_trang_thai_duoc_khai_bao(api_ts: str) -> None:
    m = re.search(r"export type ServerStatus = ([^;]+);", api_ts)
    assert m, "api.ts không còn khai báo ServerStatus"
    assert {s.strip().strip('"') for s in m.group(1).split("|")} == {"ok", "degraded", "down"}, (
        "phải đúng ba trạng thái: ok (SỐNG) / degraded (SUY GIẢM) / down (CHẾT)"
    )


def messages(api_ts: str) -> dict[str, str]:
    """Trích ba câu trong SERVER_STATUS_MESSAGE (chuỗi có thể nối bằng `+` và
    trải nhiều dòng, nên cắt theo nhãn khoá chứ không theo dấu phẩy)."""
    body = block(api_ts, "export const SERVER_STATUS_MESSAGE", "\n};")
    keys = ("ok", "degraded", "down")
    starts: dict[str, int] = {}
    for key in keys:
        m = re.search(rf"\n  {key}:", body)
        assert m, f"SERVER_STATUS_MESSAGE thiếu nhánh '{key}'"
        starts[key] = m.start()
    cuts = sorted(starts.values()) + [len(body)]
    out: dict[str, str] = {}
    for key in keys:
        begin = starts[key]
        end = next(c for c in cuts if c > begin)
        out[key] = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', body[begin:end]))
    return out


def test_ba_cau_khac_nhau_va_khong_rong(api_ts: str) -> None:
    msg = messages(api_ts)
    assert len(set(msg.values())) == 3, f"ba trạng thái phải có ba câu KHÁC NHAU: {msg}"
    for key, text in msg.items():
        assert len(text.strip()) >= 20, f"câu cho '{key}' quá ngắn để nói được điều gì: {text!r}"


def test_cau_suy_giam_noi_ro_kho_va_van_cho_doc(api_ts: str) -> None:
    degraded = messages(api_ts)["degraded"]
    assert "SUY GIẢM" in degraded, "câu SUY GIẢM phải nói thẳng kho đang suy giảm"
    assert "KHÔNG LƯU" in degraded.upper(), "phải nói rõ dữ liệu mới có thể không lưu được"
    assert CAU_CHUA_KET_NOI not in degraded, (
        "máy chủ đang TRẢ LỜI mà nói 'chưa kết nối' là đúng lời nói dối của 13/09"
    )


def test_trang_chu_ve_du_ba_nhanh(home_tsx: str) -> None:
    for cond in ('api === "ok"', 'api === "degraded"', 'api === "down"'):
        assert cond in home_tsx, f"trang chủ thiếu nhánh hiển thị cho {cond}"
    assert 'api === "checking"' in home_tsx, (
        "trạng thái 'đang kiểm tra' phải được xử lý riêng — chưa biết thì chưa kết luận"
    )


# ---------------------------------------------------------------------------
# 3. "Chưa kết nối" CHỈ ở nhánh CHẾT
# ---------------------------------------------------------------------------


def test_cau_chua_ket_noi_chi_nam_o_nhanh_down(api_ts: str) -> None:
    msg = messages(api_ts)
    assert CAU_CHUA_KET_NOI in msg["down"], "nhánh CHẾT phải giữ nguyên câu quen thuộc"
    assert CAU_CHUA_KET_NOI not in msg["ok"]
    assert CAU_CHUA_KET_NOI not in msg["degraded"]


def test_trang_chu_khong_tu_viet_lai_cau_chua_ket_noi(home_tsx: str) -> None:
    """Trang chỉ được dùng câu từ SERVER_STATUS_MESSAGE; một dị bản viết tay là
    một chỗ nữa có thể hiện nhầm lúc máy chủ đang sống."""
    render = strip_comments(home_tsx)
    assert CAU_CHUA_KET_NOI not in render, (
        "page.tsx tự viết lại câu 'Chưa kết nối…' — phải dùng SERVER_STATUS_MESSAGE.down"
    )
    for m in re.finditer(r"SERVER_STATUS_MESSAGE\.down", render):
        truoc = render[max(0, m.start() - 300) : m.start()]
        assert 'api === "down"' in truoc, (
            "SERVER_STATUS_MESSAGE.down được vẽ ngoài nhánh CHẾT — trang có thể in "
            "'chưa kết nối' trong khi máy chủ đang trả lời"
        )


def test_may_chu_tra_loi_thi_khong_bao_gio_la_down(api_ts: str) -> None:
    """`serverStatusOf` chạy SAU khi đã nhận được câu trả lời, nên nó chỉ được
    phép trả 'ok' hoặc 'degraded'. Kể cả HTTP 5xx: trả 500 vẫn là đang sống."""
    fn = block(api_ts, "export function serverStatusOf")
    assert '"down"' not in fn, (
        "serverStatusOf không được trả 'down': máy chủ đã trả lời thì nó đang sống"
    )
    assert "httpStatus >= 400" in fn, "HTTP 4xx/5xx phải rơi vào SUY GIẢM, không phải CHẾT"
    probe_once = block(api_ts, "async function probeOnce")
    # Dùng `getHealth` ở đây sẽ ném ở 5xx và biến một máy chủ ốm thành máy chủ chết.
    assert "res.json()" in probe_once, "probe phải đọc THÂN câu trả lời"
    assert "res.status" in probe_once, "probe phải đọc MÃ HTTP, không chỉ dựa vào ném/không ném"


# ---------------------------------------------------------------------------
# 4. Thời gian chờ đủ dài + đúng một lần thử lại
# ---------------------------------------------------------------------------


def test_timeout_va_so_lan_thu_lai(api_ts: str) -> None:
    timeout = re.search(r"export const PROBE_TIMEOUT_MS = (\d+);", api_ts)
    attempts = re.search(r"export const PROBE_ATTEMPTS = (\d+);", api_ts)
    assert timeout, "api.ts phải khai báo PROBE_TIMEOUT_MS"
    assert attempts, "api.ts phải khai báo PROBE_ATTEMPTS"
    assert int(timeout.group(1)) >= 4000, (
        "2,5 giây từng cắt nhầm máy chủ khoẻ trên máy dev lạnh — tối thiểu 4 giây"
    )
    assert int(attempts.group(1)) >= 2, "phải thử lại ít nhất một lần trước khi tuyên bố CHẾT"
    server = block(api_ts, "export async function probeServer")
    assert 'result.status === "down"' in server, (
        "probeServer phải thử lại khi lần đầu kết luận CHẾT"
    )
    assert "used < maxAttempts" in server, "vòng thử lại phải bị chặn bởi số lần tối đa"


def test_phan_biet_cham_voi_chet(api_ts: str, home_tsx: str) -> None:
    assert re.search(r"export const PROBE_SLOW_MS = (\d+);", api_ts), (
        "thiếu ngưỡng CHẬM — probe sẽ không phân biệt được 'API chậm' với 'API chết'"
    )
    assert '"timeout" | "error"' in api_ts, (
        "phải phân biệt CHẾT vì hết giờ với CHẾT vì không nối được"
    )
    assert "probe?.slow" in home_tsx, "trang chủ phải nói ra khi máy chủ SỐNG nhưng chậm"
    assert 'probe?.downKind === "timeout"' in home_tsx, (
        "trang chủ phải nói rõ vì sao kết luận là CHẾT"
    )


# ---------------------------------------------------------------------------
# 5. Chip chế độ không được im lặng khi kho suy giảm
# ---------------------------------------------------------------------------


def test_modechip_doc_cung_mot_probe_va_keu_khi_suy_giam() -> None:
    src = read(MODECHIP_TSX)
    assert "probeServer()" in src, "ModeChip phải dùng chung một probe với trang chủ"
    assert 'server === "degraded"' in src, (
        "ModeChip im lặng khoe DEMO/THẬT khi kho suy giảm — đúng cảnh người vận hành "
        "nhìn thanh nav thấy bình thường trong khi hệ thống không lưu được gì (13/09)"
    )
    assert "KHO SUY GIẢM" in src, "chip phải nói thẳng bằng chữ, không chỉ đổi màu"
    assert 'server === "down"' in src, "ModeChip phải nói khi nhãn chế độ chỉ là mặc định an toàn"


# ---------------------------------------------------------------------------
# 6. Các trang khác: RỖNG khác LỖI
# ---------------------------------------------------------------------------


def test_ket_qua_phan_biet_rong_voi_loi() -> None:
    src = read(KETQUA_TSX)
    assert "sessionsErr" in src, (
        "/ket-qua nuốt lỗi listSessions rồi để danh sách trống — người đọc hiểu thành "
        "'chưa có phiên nào' trong khi sự thật là không đọc được"
    )
    assert "LỖI TẢI DỮ LIỆU" in src, "phải nói thẳng đây là lỗi tải, không phải rỗng"


def test_bat_dau_cung_tham_do_bang_health() -> None:
    """`/bat-dau` mang y hệt lỗi của trang chủ (cùng một đoạn probe chép tay).
    Sửa một chỗ mà bỏ chỗ kia là để nguyên lời nói dối ở một màn hình khác."""
    src = read(BATDAU_TSX)
    assert "probeServer()" in src, "/bat-dau phải thăm dò bằng probeServer()"
    assert "listSessions(2500)" not in strip_comments(src), (
        "/bat-dau vẫn thăm dò bằng listSessions(2500) — cùng lỗi 13/09/2026"
    )


def test_o_dan_link_vod_noi_dung_ly_do_bi_khoa() -> None:
    src = read(BATDAUVOD_TSX)
    assert 'server === "degraded"' in src, (
        "ô dán link VOD in cùng một câu 'chưa kết nối' cho MỌI lý do khoá — "
        "kể cả khi máy chủ đang chạy và chỉ có kho suy giảm"
    )
    assert "VẪN CHẠY" in src, "nhánh SUY GIẢM phải nói rõ máy chủ vẫn đang chạy"


def test_replay_khong_goi_du_lieu_mo_phong_la_du_lieu_that() -> None:
    """Trang chủ đẩy người dùng sang /replay mô phỏng khi máy chủ chết hoặc kho
    suy giảm — dải băng ở đó phải nói đúng loại dữ liệu đang nằm trên màn hình."""
    src = read(REPLAY_TSX)
    assert "PHÁT LẠI DỮ LIỆU MÔ PHỎNG" in src, (
        "dải băng vẫn in 'PHÁT LẠI DỮ LIỆU THẬT' trên bản ghi mô phỏng"
    )
    assert "PHÁT LẠI DỮ LIỆU THẬT" in src, "phải giữ CẢ HAI câu, không xoá câu dữ liệu thật"
    assert "isMock" in src, "hai câu phải được chọn theo nguồn dữ liệu thật sự đang hiển thị"


# ---------------------------------------------------------------------------
# 7. Hợp đồng hai đầu: /health mang đúng các trường bộ phân loại web đọc
# ---------------------------------------------------------------------------


def test_health_mang_du_truong_ma_web_phan_loai() -> None:
    app = create_app(store=InMemoryStore())
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200, r.text
        body = r.json()
    # Bốn trường `serverStatusOf` đọc. Thiếu một trường là phân loại sai âm thầm.
    for field in ("status", "storage_mode", "durable", "snapshot"):
        assert field in body, f"/health thiếu trường '{field}' mà web dùng để phân loại"
    assert body["status"] == "ok", "kho trong RAM lành mạnh phải tự khai 'ok'"


def test_health_khong_doc_kho_nang() -> None:
    """Probe chọn `/health` vì nó rẻ. Nếu ai đó nhét một truy vấn nặng vào đây,
    probe lại trở thành thứ treo cùng database — đúng lỗi cũ ở một chỗ mới."""
    src = (ROOT / "src" / "livelift" / "api" / "main.py").read_text(encoding="utf-8")
    health = block(src, '@app.get("/health")', "\n\n")
    for nang in ("list_sessions", "list_comments", "list_ticks", "list_clicks"):
        assert nang not in health, (
            f"/health gọi {nang}() — endpoint thăm dò không được đọc kho nặng"
        )


def test_huong_dan_mo_ta_dung_ba_trang_thai(api_ts: str) -> None:
    guide = read(GUIDE)
    msg = messages(api_ts)
    assert msg["down"].rstrip(".") in guide, (
        "docs/HUONG-DAN-SU-DUNG.md trích câu CHẾT không còn khớp mã — sửa lời trên "
        "giao diện thì phải sửa hướng dẫn cùng lúc"
    )
    for tu in ("SUY GIẢM", "KHO SUY GIẢM", "MẤT KẾT NỐI"):
        assert tu in guide, f"hướng dẫn chưa mô tả trạng thái '{tu}'"
