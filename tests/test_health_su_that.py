"""/health phải NÓI SỰ THẬT, và API không được treo khi kho chết.

Sự cố 13/09/2026 (gói A-HEALTH). PostgreSQL chết hoàn toàn — không còn ai nghe
ở cổng 5432 — trong lúc hệ thống đang chạy. Ba thứ hỏng cùng lúc, và cả ba đều
là hỏng kiểu *nói dối*, nguy hiểm hơn hỏng kiểu sập:

1. ``GET /health`` trả 200 trong 0,002 giây với ``storage_mode=postgres``,
   ``durable=true`` và câu "Dữ liệu nằm trong PostgreSQL — khởi động lại không
   mất gì". Nó chưa bao giờ hỏi cơ sở dữ liệu lấy một câu; nó chỉ đọc TÊN
   backend rồi khẳng định. Người vận hành nhìn thấy màu xanh trong khi hệ thống
   không ghi nổi một dòng.
2. ``GET /sessions`` treo ĐÚNG 30 GIÂY (``ConnectionPool.timeout`` mặc định của
   psycopg_pool) rồi trả ``Internal Server Error`` trần — không một chữ nào nói
   rằng thứ chết là cơ sở dữ liệu.
3. Vì (2), phép thăm dò 2,5 giây của trang chủ luôn thất bại nên trang báo
   "Chưa kết nối được máy chủ" NGAY CẢ KHI API còn sống.

Nguyên tắc cốt lõi của dự án: thiếu nguồn thì TUYÊN BỐ thiếu, không bịa. Một
trường ``durable=true`` chưa hề kiểm chứng đúng là bịa. Các test dưới đây là
cổng chặn cho cả ba, và chúng cố tình đo CẢ THỜI GIAN: "đúng nhưng sau 30 giây"
là một dạng sai khác.

Cách giả lập cái chết: trỏ ``DATABASE_URL`` tới một cổng localhost không ai
nghe. Không cần Docker, không cần PostgreSQL — và đó chính là điều kiện của
ngày 13/09.
"""

from __future__ import annotations

import re
import socket
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import (
    DEFAULT_PING_CACHE_S,
    DEFAULT_PING_TIMEOUT_S,
    DEFAULT_POOL_TIMEOUT_S,
    STORE_DOWN_CORE,
    STORE_DOWN_DETAIL,
    InMemoryStore,
    PostgresStore,
    StoreUnavailableError,
    _connect_kwargs,
    durability_info,
    reset_store_ping_cache,
    storage_health,
    store_ping,
)

ROOT = Path(__file__).resolve().parents[1]

# Ngân sách thời gian — chính là điều sự cố 13/09 vi phạm.
HAN_HEALTH_S = 3.0  # /health phải trả lời dù kho đã chết
HAN_ROUTE_S = 5.0  # một route đọc kho phải hỏng NHANH, không treo 30 giây


@pytest.fixture(autouse=True)
def _xoa_dem_ping():
    """Mỗi test bắt đầu với bộ đệm ping sạch — kết quả của test trước không
    được phép trả lời thay cho test sau (đó lại là một kiểu nói dối)."""
    reset_store_ping_cache()
    yield
    reset_store_ping_cache()


def cong_khong_ai_nghe() -> int:
    """Một cổng localhost chắc chắn không có dịch vụ nào đang nghe."""
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])
    finally:
        s.close()


def url_db_chet() -> str:
    return f"postgresql://livelift:livelift@127.0.0.1:{cong_khong_ai_nghe()}/livelift"


@pytest.fixture
def client_db_chet():
    """Ứng dụng thật + kho Postgres thật trỏ vào hư không, hạn giờ MẶC ĐỊNH.

    Cố tình dùng mặc định: nếu ai đó nới các hằng số trở lại 30 giây thì đúng
    những test này phải đỏ, chứ không phải được cứu bởi tham số riêng của test.
    """
    # Nạp sẵn bộ phân loại ý định: lần gọi /health đầu tiên của cả tiến trình
    # phải đọc mô hình từ đĩa (~1 giây). Đó là chi phí MỘT LẦN, không liên quan
    # gì tới kho dữ liệu; để nó lẫn vào phép đo là biến cổng "kho chết có làm
    # /health chậm không" thành cổng đo tốc độ đọc đĩa.
    from livelift.nlp.intent import classifier_info

    classifier_info()
    store = PostgresStore(url_db_chet())
    with TestClient(create_app(store=store)) as c:
        yield c


# ---------------------------------------------------------------------------
# 1. /health ngừng nói dối
# ---------------------------------------------------------------------------


def test_health_khong_duoc_khai_durable_khi_postgres_da_chet(client_db_chet):
    """Cổng chặn cho đúng màn hình người vận hành đã nhìn ngày 13/09/2026."""
    t0 = time.perf_counter()
    res = client_db_chet.get("/health")
    giay = time.perf_counter() - t0

    # HTTP 200 là CÓ CHỦ Ý (xem ghi chú trong main.py): thân của /health chính
    # là lời giải thích sự cố, trả 503 thì client vứt thân đi và lại không phân
    # biệt được "API chết" với "cơ sở dữ liệu chết".
    assert res.status_code == 200, res.text
    body = res.json()

    assert body["status"] == "degraded", "kho chết mà status vẫn 'ok' là nói dối"
    assert body["durable"] is False, "chưa ping được mà khai durable=true là bịa"
    assert body["storage_ok"] is False
    assert body["storage_note"] is None, (
        "câu 'khởi động lại không mất gì' phải BIẾN MẤT khi không kết nối được DB"
    )

    canh_bao = body["storage_warning"]
    assert "KHÔNG kết nối được PostgreSQL" in canh_bao
    assert "KHÔNG lưu được dữ liệu" in canh_bao
    assert "mọi ghi sẽ thất bại" in canh_bao
    # Cảnh báo mà không nói phải làm gì thì chỉ là tiếng ồn.
    assert "STORE_BACKEND=memory" in canh_bao
    assert "bat_postgres" in canh_bao or "docker compose" in canh_bao

    # Bằng chứng, không phải lời khẳng định suông: lần đo được đính kèm.
    ping = body["storage_ping"]
    assert ping["ok"] is False
    assert ping["error"], "phải giữ nguyên văn lỗi driver để gỡ rối"
    assert ping["timeout_s"] <= DEFAULT_PING_TIMEOUT_S
    assert ping["checked_at"]

    assert giay < HAN_HEALTH_S, f"/health mất {giay:.2f}s khi kho chết (hạn {HAN_HEALTH_S}s)"


def test_health_van_doc_duoc_khi_khong_dem_noi_phien(client_db_chet):
    """Kho chết thì không đếm được phiên — nói ra, đừng sập và đừng bịa số."""
    body = client_db_chet.get("/health").json()
    assert body["mode"] == "unknown"
    assert body["mode_counts"] is None, "không đếm được thì KHÔNG được trả về số nào"
    assert "kho dữ liệu không trả lời" in body["mode_note"].lower()
    # Các trường dùng để phân loại phía web vẫn còn đủ để hiển thị.
    assert body["store_backend"] == "postgres"
    assert body["storage_mode"] == "postgres"


def test_storage_health_ha_durable_xuong_khi_ping_that_bai():
    """Cùng một sự thật, kiểm ở tầng hàm: ``durability_info`` chỉ đọc cấu hình
    (postgres ⇒ durable=true), ``storage_health`` phải kiểm CHỨNG rồi mới nói."""

    class KhoChet:
        backend = "postgres"

        def ping(self, timeout_s: float = 1.5) -> None:
            raise StoreUnavailableError(STORE_DOWN_DETAIL, cause_text="connection refused")

    kho = KhoChet()
    assert durability_info(kho)["durable"] is True, "hàm thuần vẫn chỉ mô tả cấu hình"

    suc_khoe = storage_health(kho, cache_s=0)
    assert suc_khoe["durable"] is False
    assert suc_khoe["storage_ok"] is False
    assert suc_khoe["storage_note"] is None
    assert STORE_DOWN_CORE in suc_khoe["storage_warning"]


def test_storage_health_giu_nguyen_su_that_khi_ping_thanh_cong():
    class KhoSong:
        backend = "postgres"

        def ping(self, timeout_s: float = 1.5) -> None:
            return

    suc_khoe = storage_health(KhoSong(), cache_s=0)
    assert suc_khoe["durable"] is True
    assert suc_khoe["storage_ok"] is True
    assert suc_khoe["storage_warning"] is None
    assert "PostgreSQL" in suc_khoe["storage_note"]


def test_kho_khong_biet_tu_kiem_tra_thi_phai_khai_la_khong_biet():
    """Không có ``ping`` ⇒ KHÔNG được mặc định coi là khỏe. Im lặng suy diễn
    đúng là cách /health đã nói dối suốt ngày 13/09."""

    class KhoCam:
        backend = "postgres"

    ket_qua = store_ping(KhoCam(), cache_s=0)
    assert ket_qua["ok"] is False
    assert "ping" in ket_qua["error"].lower()
    assert storage_health(KhoCam(), cache_s=0)["durable"] is False


# ---------------------------------------------------------------------------
# 2. Không treo 30 giây, và lỗi phải có nghĩa
# ---------------------------------------------------------------------------


def test_route_doc_kho_tra_503_tieng_viet_va_hong_nhanh(client_db_chet):
    """Đúng lời gọi đã treo 30 giây rồi trả 'Internal Server Error' trần."""
    t0 = time.perf_counter()
    res = client_db_chet.get("/sessions")
    giay = time.perf_counter() - t0

    assert res.status_code == 503, f"kho chết phải là 503, nhận {res.status_code}: {res.text[:200]}"
    body = res.json()
    detail = body["detail"]
    assert "KHÔNG kết nối được PostgreSQL" in detail
    assert "mọi ghi sẽ thất bại" in detail
    assert "STORE_BACKEND=memory" in detail
    assert "Internal Server Error" not in res.text
    # Nguyên văn lỗi driver được giữ riêng để gỡ rối, KHÔNG thay cho câu tiếng Việt.
    assert body["cause"], "phải kèm nguyên văn lỗi của driver"
    assert body["storage_ok"] is False
    assert res.headers.get("Retry-After"), "503 tạm thời phải nói khi nào thử lại"

    assert giay < HAN_ROUTE_S, f"/sessions mất {giay:.2f}s khi kho chết (hạn {HAN_ROUTE_S}s)"


def test_tang_store_nem_loi_co_nghia_chu_khong_phai_loi_driver():
    """Người gọi không qua HTTP (script, bộ thực thi tự động) cũng phải nhận
    được câu có nghĩa — 503 của route chỉ là lớp áo ngoài của ngoại lệ này."""
    store = PostgresStore(url_db_chet(), pool_timeout_s=0.3, close_timeout_s=0.2)
    try:
        t0 = time.perf_counter()
        with pytest.raises(StoreUnavailableError) as loi:
            store.list_sessions()
        giay = time.perf_counter() - t0
    finally:
        store.close()

    assert STORE_DOWN_CORE in loi.value.message
    assert loi.value.cause_text, "giữ nguyên văn lỗi driver cho log"
    assert giay < 2.0, f"hạn pool 0,3s mà mất {giay:.2f}s"


def test_han_gio_mac_dinh_khong_con_la_30_giay():
    """Cổng chặn cho chính CON SỐ đã đếm được ngày 13/09: 30 giây là mặc định
    của psycopg_pool, và mặc định ấy không bao giờ được quay lại."""
    assert DEFAULT_POOL_TIMEOUT_S < 10.0
    assert DEFAULT_PING_TIMEOUT_S < DEFAULT_POOL_TIMEOUT_S, (
        "ping của /health phải ngắn hơn hạn của route thường"
    )
    # Trang chủ bỏ cuộc sau 2,5 giây. Máy chủ trả lời sau mốc đó thì câu 503
    # tiếng Việt không đến được mắt ai — và người dùng lại không phân biệt được
    # "API chết" với "cơ sở dữ liệu chết", đúng như ngày 13/09.
    assert DEFAULT_POOL_TIMEOUT_S < 2.5, "phải hỏng TRƯỚC khi trang web hết kiên nhẫn"
    store = PostgresStore(url_db_chet(), close_timeout_s=0.2)
    try:
        assert store._pool.timeout == DEFAULT_POOL_TIMEOUT_S != 30.0
    finally:
        store.close()


def test_ket_noi_mang_theo_connect_timeout_va_statement_timeout():
    """Ba pha, ba hạn giờ. Thiếu connect_timeout thì libpq chờ VÔ HẠN khi máy
    chủ nuốt gói (không refuse) — pool timeout không cứu được pha đó."""
    kwargs = _connect_kwargs(
        "postgresql://u:p@127.0.0.1:5432/db",
        row_factory=dict,
        connect_timeout_s=3,
        statement_timeout_s=8.0,
    )
    assert kwargs["connect_timeout"] == 3
    assert kwargs["options"] == "-c statement_timeout=8000"


def test_han_gio_cua_nguoi_van_hanh_thang_mac_dinh_cua_chung_ta():
    """Một mặc định an toàn được phép điền vào chỗ trống, KHÔNG được phép ghi
    đè lựa chọn có chủ ý ghi trong DATABASE_URL."""
    kwargs = _connect_kwargs(
        "postgresql://u:p@127.0.0.1:5432/db?connect_timeout=20&options=-c%20statement_timeout%3D60000",
        row_factory=dict,
        connect_timeout_s=3,
        statement_timeout_s=8.0,
    )
    assert "connect_timeout" not in kwargs
    assert "options" not in kwargs


def test_loi_kho_chet_van_duoc_bo_thu_nhan_ra():
    """Mối nối giữa hai gói: dịch lỗi KHÔNG được làm mù bộ phân loại kho chết.

    Gói "kho chết giữa phiên" nhận diện sự cố bằng TÊN lớp trên cây kế thừa
    (``OperationalError``, ``PoolClosed``…) để khỏi phải import psycopg. Gói
    A-HEALTH lại dịch chính những lỗi đó thành ``StoreUnavailableError`` để có
    câu tiếng Việt — tên cũ biến mất khỏi cây kế thừa. Không khoá lại thì một
    lần PostgreSQL chết THẬT sẽ không được nhận là "kho chết", bộ thu mất đường
    spool và bình luận của phiên live bay mất trong im lặng: đúng kiểu hỏng chỉ
    lộ ra khi đã lên sóng, và là hậu quả do CHÍNH bản vá này gây ra.
    """
    from livelift.api.routes.events import is_storage_outage

    assert is_storage_outage(StoreUnavailableError(STORE_DOWN_DETAIL)) is True
    # Và vẫn phải phân biệt được với một bug thật (lỗi vĩnh viễn, phải nổ ra).
    assert is_storage_outage(ValueError("bug thật")) is False


def test_moi_duong_ra_postgres_deu_di_qua_lop_dich_loi():
    """Cổng cấu trúc: một phương thức tương lai dùng thẳng ``self._pool`` là
    một chỗ treo 30 giây mới, không được dịch, không ai thấy cho tới lúc live.
    """
    src = (ROOT / "src" / "livelift" / "api" / "store.py").read_text(encoding="utf-8")
    tho = [
        d.strip()
        for d in re.findall(r"^.*self\._pool\.connection\(.*$", src, flags=re.MULTILINE)
        if "def _connection" not in d
    ]
    # Chỉ ĐÚNG MỘT chỗ được phép chạm vào pool: thân của _connection().
    assert len(tho) == 1, f"còn {len(tho)} chỗ mượn kết nối không qua _connection(): {tho}"


# ---------------------------------------------------------------------------
# 3. Chế độ memory không được vạ lây
# ---------------------------------------------------------------------------


def test_che_do_memory_khong_bi_anh_huong():
    """Kho RAM nằm trong chính tiến trình này: không socket, không thể chết âm
    thầm — /health của nó phải y như cũ, chỉ thêm bằng chứng."""
    with TestClient(create_app(store=InMemoryStore())) as c:
        t0 = time.perf_counter()
        body = c.get("/health").json()
        giay = time.perf_counter() - t0
        assert c.get("/sessions").status_code == 200, "kho RAM vẫn phải đọc được"

    assert body["status"] == "ok"
    assert body["store_backend"] == "memory"
    assert body["storage_mode"] == "memory"
    assert body["durable"] is False, "RAM vẫn KHÔNG bền vững — cảnh báo cũ giữ nguyên"
    assert body["storage_ok"] is True
    assert STORE_DOWN_CORE not in (body["storage_warning"] or ""), (
        "kho RAM khỏe mà bị dán cảnh báo Postgres chết là báo động giả"
    )
    assert body["mode_counts"] == {"demo": 0, "real": 0}
    assert giay < 1.0, f"/health chế độ memory mất {giay:.2f}s"


# ---------------------------------------------------------------------------
# 4. Đệm ping: đỡ đấm vào DB, nhưng KHÔNG được làm /health cũ
# ---------------------------------------------------------------------------


class KhoDemPing:
    """Kho giả đếm số lần bị ping và bật/tắt được — không cần socket nào."""

    backend = "postgres"

    def __init__(self) -> None:
        self.lan_ping = 0
        self.song = True

    def ping(self, timeout_s: float = 1.5) -> None:
        self.lan_ping += 1
        if not self.song:
            raise StoreUnavailableError(STORE_DOWN_DETAIL, cause_text="connection refused")


def test_dem_ping_khong_de_health_dam_vao_database():
    """Trang web hỏi /health liên tục; không đệm thì chính cái đồng hồ đo sức
    khỏe lại làm hỏng thứ nó đo."""
    kho = KhoDemPing()
    dau = storage_health(kho, cache_s=5.0)
    assert dau["storage_ping"]["cached"] is False
    for _ in range(19):
        lai = storage_health(kho, cache_s=5.0)
        assert lai["storage_ping"]["cached"] is True, "bản đệm phải TỰ KHAI là bản đệm"
    assert kho.lan_ping == 1, f"20 lần gọi /health mà ping {kho.lan_ping} lần"


def test_dem_ping_khong_lam_health_noi_chuyen_cu():
    """Đệm là để đỡ tải, không phải để giấu sự thật: hết hạn đệm thì trạng thái
    MỚI phải hiện ra ngay. Một /health xanh vì bản đệm 5 giây trước vẫn là một
    /health nói dối."""
    kho = KhoDemPing()
    # Hạn đệm 0,1s và ngủ 0,35s: đồng hồ đơn điệu của Windows nhảy từng nấc
    # ~15,6 ms, nên một biên hẹp (ngủ 0,06s cho hạn 0,05s) sẽ ĐỎ NGẪU NHIÊN —
    # một cổng chập chờn thì sớm muộn cũng bị người ta tắt đi.
    assert storage_health(kho, cache_s=0.1)["durable"] is True

    kho.song = False  # cơ sở dữ liệu chết ngay lúc này
    time.sleep(0.35)  # qua hạn đệm

    sau = storage_health(kho, cache_s=0.1)
    assert sau["storage_ping"]["cached"] is False
    assert sau["durable"] is False
    assert sau["storage_ok"] is False
    assert STORE_DOWN_CORE in sau["storage_warning"]
    assert kho.lan_ping == 2

    # Và hạn đệm mặc định phải đủ ngắn để "cũ nhất có thể" vẫn là vài giây.
    assert DEFAULT_PING_CACHE_S <= 5.0


def test_tat_dem_thi_ping_that_moi_lan():
    kho = KhoDemPing()
    for _ in range(3):
        storage_health(kho, cache_s=0)
    assert kho.lan_ping == 3


def test_dem_ping_khong_tron_ket_qua_giua_hai_kho():
    """Hai kho khác nhau phải có hai câu trả lời khác nhau — nếu không, đổi kho
    giữa chừng là lại tin vào số của kho cũ."""
    song, chet = KhoDemPing(), KhoDemPing()
    chet.song = False
    assert storage_health(song, cache_s=5.0)["storage_ok"] is True
    assert storage_health(chet, cache_s=5.0)["storage_ok"] is False
    assert song.lan_ping == chet.lan_ping == 1


def test_health_lan_thu_hai_nhanh_nho_dem(client_db_chet):
    """Kho đã chết: lần gọi đầu chịu hạn ping, các lần sau phải gần như tức
    thì — trang web có thể hỏi liên tục mà không nhân đôi thời gian chờ."""
    client_db_chet.get("/health")
    t0 = time.perf_counter()
    body = client_db_chet.get("/health").json()
    giay = time.perf_counter() - t0
    assert body["status"] == "degraded", "nhanh nhưng vẫn phải nói đúng sự thật"
    assert body["storage_ping"]["cached"] is True
    assert giay < 0.5, f"lần /health thứ hai mất {giay:.2f}s — đệm không có tác dụng"
