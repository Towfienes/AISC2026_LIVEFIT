"""Cổng bảo vệ ĐƯỜNG GHI (gói VÁ-XÁC-THỰC, 14/09/2026).

Sự cố gốc: kiểm toán trước khi mở địa chỉ công khai cho hội đồng chấm phát
hiện **12 trong 15 endpoint ghi hoàn toàn không có xác thực**. Chỉ ba đường
nạp của bộ thu (``comments``/``ticks``/``reactions``) tham chiếu ``IngestAuth``
— dán tay trên từng route, nên quên dán là một lỗ hổng IM LẶNG: không có một
dòng mã, một test hay một dòng log nào nói rằng 12 đường kia đang mở. Người lạ
biết URL kết thúc được một phiên thí nghiệm đang chạy.

Tệp này khoá lại cả CƠ CHẾ lẫn CHÍNH SÁCH:

1. **Cơ chế** — dependency :func:`~livelift.api.auth.require_write_auth` phải
   được gắn ở CẤP ỨNG DỤNG, và MỌI route ghi trong bảng định tuyến thật phải
   khai báo mức bảo vệ. Thêm một route ghi mà quên gắn ⇒ bộ test này đỏ
   (:func:`test_route_ghi_moi_quen_khai_bao_thi_bo_test_do`).
2. **Chính sách** — bảng 15 endpoint × mức bảo vệ, và hành vi thật của từng
   mức: không token ⇒ bị chặn, có token ⇒ qua, khách của bản trưng bày chỉ
   chạm được vào dữ liệu MẪU, đường tốn tài nguyên luôn đóng.
3. **Không phá chế độ phát triển cục bộ** — ``INGEST_TOKEN`` rỗng ⇒ mở hết,
   đúng như trước; đó là điều giữ cho phần còn lại của bộ kiểm thử chạy được
   mà không phải đính header ở hàng nghìn chỗ.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from livelift.api.auth import (
    MUC_DEMO,
    MUC_TOKEN,
    GioiHanTanSuat,
    liet_ke_route_ghi,
    require_write_auth,
)
from livelift.api.main import create_app
from livelift.api.routes import demo as demo_routes
from livelift.api.routes import replays as replay_routes
from livelift.api.store import InMemoryStore
from livelift.config import get_settings

TOKEN = "token-kiem-thu-rat-dai-va-ngau-nhien"
HEADER_DUNG = {"Authorization": f"Bearer {TOKEN}"}


# ---------------------------------------------------------------------------
# 1. BẢNG CHÍNH SÁCH — sự thật duy nhất, đối chiếu với bảng định tuyến thật
# ---------------------------------------------------------------------------

BANG_MUC_BAO_VE: dict[tuple[str, str], str] = {
    # Đường nạp của bộ thu: LUÔN cần token, không có ngoại lệ "phiên demo".
    # Một bình luận giả bơm vào phiên thật là một điểm dữ liệu sai trong bài
    # báo, không phải một trò nghịch vô hại.
    ("POST", "/sessions/{session_id}/comments"): MUC_TOKEN,
    ("POST", "/sessions/{session_id}/ticks"): MUC_TOKEN,
    ("POST", "/sessions/{session_id}/reactions"): MUC_TOKEN,
    # Tốn tài nguyên: máy chủ tải video theo địa chỉ người gọi đưa.
    ("POST", "/replays/youtube"): MUC_TOKEN,
    # Bộ thu chạy nền (17/09/2026): mở kết nối tới nền tảng và đốt quota của
    # khoá thật — cùng lý do với /replays/youtube.
    ("POST", "/sessions/{session_id}/ingest"): MUC_TOKEN,
    ("POST", "/sessions/{session_id}/ingest/stop"): MUC_TOKEN,
    # Vòng đời phiên + can thiệp + danh mục: khách của bản trưng bày được
    # dùng, nhưng CHỈ trên dữ liệu mẫu, và có trần tần suất.
    ("POST", "/products"): MUC_DEMO,
    ("POST", "/shortlinks"): MUC_DEMO,
    ("POST", "/sessions"): MUC_DEMO,
    ("POST", "/sessions/{session_id}/schedule"): MUC_DEMO,
    ("POST", "/sessions/{session_id}/start"): MUC_DEMO,
    ("POST", "/sessions/{session_id}/end"): MUC_DEMO,
    ("POST", "/sessions/{session_id}/cancel"): MUC_DEMO,
    ("POST", "/sessions/{session_id}/actions/execute"): MUC_DEMO,
    ("POST", "/sessions/{session_id}/actions/override"): MUC_DEMO,
    # Đơn hàng (17/09/2026): phiên thật cần token, khách chỉ ghi vào phiên mẫu.
    ("POST", "/sessions/{session_id}/orders"): MUC_DEMO,
    ("POST", "/sessions/{session_id}/orders/import"): MUC_DEMO,
    ("POST", "/demo/seed"): MUC_DEMO,
    ("POST", "/demo/seed-vang"): MUC_DEMO,
}


# ---------------------------------------------------------------------------
# Đồ nghề
# ---------------------------------------------------------------------------


@pytest.fixture
def bat_token(monkeypatch):
    """Bật xác thực: đặt INGEST_TOKEN và dọn bộ nhớ đệm cấu hình hai đầu."""
    monkeypatch.setenv("INGEST_TOKEN", TOKEN)
    get_settings.cache_clear()
    yield TOKEN
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()


@pytest.fixture
def khoa_sach(monkeypatch, bat_token):
    """Hồ sơ "máy chủ thí nghiệm thật": tắt luôn chế độ trưng bày công khai."""
    monkeypatch.setenv("PUBLIC_DEMO_WRITES", "false")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("PUBLIC_DEMO_WRITES", raising=False)
    get_settings.cache_clear()


@pytest.fixture
def app_store():
    store = InMemoryStore()
    app = create_app(store=store)
    with TestClient(app) as c:
        yield app, store, c


@pytest.fixture
def khong_tai_video(monkeypatch):
    """Chặn yt-dlp: /replays/youtube chạy tác vụ nền THẬT sau khi trả 202."""
    monkeypatch.setattr(replay_routes, "_run_job", lambda *a, **k: None)


@pytest.fixture
def gieo_vang_gia(monkeypatch):
    """Bộ vàng thật mô phỏng 6 phiên 90 phút — quá chậm cho một test cổng."""
    monkeypatch.setattr(
        demo_routes,
        "seed_demo_vang",
        lambda store: {"nhom": {}, "ket_qua": {}, "product_ids": [], "shortlink_codes": []},
    )


def _tao_phien(client: TestClient, headers: dict[str, str] | None = None) -> str:
    r = client.post(
        "/sessions",
        json={"platform": "youtube", "title": "phiên kiểm thử", "planned_duration_min": 90},
        headers=headers or {},
    )
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def _phien_dang_phat(client: TestClient, headers: dict[str, str]) -> str:
    sid = _tao_phien(client, headers)
    assert client.post(f"/sessions/{sid}/schedule", json={}, headers=headers).status_code == 200
    assert client.post(f"/sessions/{sid}/start", headers=headers).status_code == 200
    return sid


def _yeu_cau_ghi(sid: str) -> dict[tuple[str, str], tuple[str, dict[str, Any] | None]]:
    """Một lời gọi HỢP LỆ cho mỗi endpoint ghi, khoá theo (method, mẫu đường).

    Khoá dùng ĐÚNG mẫu đường của bảng định tuyến nên bảng này và
    :data:`BANG_MUC_BAO_VE` luôn phải khớp nhau — thiếu một dòng là đỏ.
    """
    return {
        ("POST", "/products"): (
            "/products",
            {"product_id": "P-TEST", "name": "Sản phẩm thử", "cost": 1.0, "price": 2.0, "stock": 5},
        ),
        ("POST", "/shortlinks"): (
            "/shortlinks",
            {"product_id": "P-TEST", "target_url": "https://shop.example/p"},
        ),
        ("POST", "/sessions"): (
            "/sessions",
            {"platform": "youtube", "planned_duration_min": 90},
        ),
        ("POST", "/sessions/{session_id}/schedule"): (f"/sessions/{sid}/schedule", {}),
        ("POST", "/sessions/{session_id}/start"): (f"/sessions/{sid}/start", None),
        ("POST", "/sessions/{session_id}/end"): (f"/sessions/{sid}/end", None),
        ("POST", "/sessions/{session_id}/cancel"): (f"/sessions/{sid}/cancel", None),
        ("POST", "/sessions/{session_id}/actions/execute"): (
            f"/sessions/{sid}/actions/execute",
            {"product_id": "P-TEST"},
        ),
        ("POST", "/sessions/{session_id}/actions/override"): (
            f"/sessions/{sid}/actions/override",
            {"product_id": "P-TEST", "reason": "hết hàng"},
        ),
        ("POST", "/sessions/{session_id}/comments"): (
            f"/sessions/{sid}/comments",
            {"text": "giá bao nhiêu shop", "platform": "youtube", "ext_id": "c-1"},
        ),
        ("POST", "/sessions/{session_id}/ticks"): (f"/sessions/{sid}/ticks", {"viewers": 12.0}),
        ("POST", "/sessions/{session_id}/reactions"): (
            f"/sessions/{sid}/reactions",
            {"kind": "like", "platform": "youtube", "ext_id": "r-1"},
        ),
        # Nền tảng không tồn tại ⇒ 422 ở tầng kiểm tra dữ liệu: cổng xác thực
        # vẫn được kiểm, mà bộ test không bao giờ mở kết nối thật tới YouTube
        # trên một máy tình cờ có khoá trong .env.
        ("POST", "/sessions/{session_id}/ingest"): (
            f"/sessions/{sid}/ingest",
            {"platform": "khong-co", "source": ""},
        ),
        ("POST", "/sessions/{session_id}/ingest/stop"): (f"/sessions/{sid}/ingest/stop", None),
        ("POST", "/sessions/{session_id}/orders"): (
            f"/sessions/{sid}/orders",
            {"order_id": "DH-TEST", "gross": 1000},
        ),
        ("POST", "/sessions/{session_id}/orders/import"): (
            f"/sessions/{sid}/orders/import",
            {"csv": "order_id,ts,gross\nDH-CSV,2026-09-17T12:00:00+00:00,1000\n"},
        ),
        ("POST", "/demo/seed"): ("/demo/seed", {"n_sessions": 1, "duration_min": 30}),
        ("POST", "/demo/seed-vang"): ("/demo/seed-vang", None),
        ("POST", "/replays/youtube"): (
            "/replays/youtube",
            {"url": "https://www.youtube.com/watch?v=khong-tai-that"},
        ),
    }


MOI_DUONG_GHI = sorted(BANG_MUC_BAO_VE)


# ---------------------------------------------------------------------------
# 2. CƠ CHẾ — quên gắn phải là lỗi an toàn, không phải lỗi im lặng
# ---------------------------------------------------------------------------


def test_bang_dinh_tuyen_that_khop_bang_chinh_sach():
    """15 endpoint ghi, mỗi cái một mức bảo vệ ĐÃ KHAI BÁO — đọc app.routes.

    Thêm một route ghi mới mà quên khai báo ⇒ giá trị ``None`` xuất hiện và
    test đỏ. Thêm route ghi mới có khai báo nhưng chưa được ai xem xét ⇒ khoá
    thừa so với bảng chính sách và test cũng đỏ: mỗi đường ghi mới phải có một
    con người quyết định nó thuộc mức nào.
    """
    app = create_app(store=InMemoryStore())
    thuc_te = {(m, r["path"]): r["muc"] for r in liet_ke_route_ghi(app) for m in r["methods"]}
    assert thuc_te == BANG_MUC_BAO_VE


def test_moi_endpoint_ghi_deu_co_mot_loi_goi_trong_bo_kiem_thu():
    """Bảng lời gọi phải phủ đúng 15 endpoint — không endpoint nào được kiểm
    thử "bằng cách bỏ qua"."""
    assert set(_yeu_cau_ghi("sid")) == set(BANG_MUC_BAO_VE)


def test_cong_xac_thuc_gan_o_cap_ung_dung():
    """Gỡ ``dependencies=[Depends(require_write_auth)]`` khỏi create_app ⇒ đỏ."""
    app = create_app(store=InMemoryStore())
    assert any(d.dependency is require_write_auth for d in app.router.dependencies)


def test_route_ghi_moi_quen_khai_bao_thi_bo_test_do(bat_token, app_store):
    """Hai lớp phòng thủ cho một route ghi thêm sau này mà quên gắn xác thực.

    Lớp tĩnh: cổng ở trên thấy ngay một mức ``None``. Lớp động: lúc chạy nó
    rơi về mức NGẶT NHẤT (đòi token) chứ không mở toang — quên là lỗi an
    toàn.
    """
    app, _, client = app_store

    @app.post("/duong-ghi-quen-gan")
    def duong_ghi_quen_gan() -> dict[str, bool]:
        return {"ok": True}

    quen = [r for r in liet_ke_route_ghi(app) if r["muc"] is None]
    assert [r["path"] for r in quen] == ["/duong-ghi-quen-gan"]

    assert client.post("/duong-ghi-quen-gan").status_code == 401
    assert client.post("/duong-ghi-quen-gan", headers=HEADER_DUNG).status_code == 200


# ---------------------------------------------------------------------------
# 3. KHÔNG TOKEN ⇒ BỊ CHẶN · CÓ TOKEN ⇒ QUA (từng endpoint một)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("method", "mau"), MOI_DUONG_GHI)
def test_khong_token_thi_bi_chan_o_moi_duong_ghi(
    method, mau, khoa_sach, app_store, khong_tai_video, gieo_vang_gia
):
    """Hồ sơ khoá sạch (PUBLIC_DEMO_WRITES=false): 15/15 đường ghi trả 401."""
    _, _, client = app_store
    sid = _tao_phien(client, HEADER_DUNG)
    duong, body = _yeu_cau_ghi(sid)[(method, mau)]
    r = client.request(method, duong, json=body)
    assert r.status_code == 401, f"{method} {duong} KHÔNG được để mở: {r.status_code}"
    assert "token" in r.json()["detail"].lower()


@pytest.mark.parametrize(("method", "mau"), MOI_DUONG_GHI)
def test_co_token_thi_qua_o_moi_duong_ghi(
    method, mau, bat_token, app_store, khong_tai_video, gieo_vang_gia
):
    """Token đúng ⇒ cổng không chặn.

    Chỉ khẳng định "cổng cho qua" (không 401/403/429), không khẳng định thành
    công nghiệp vụ: một vài lời gọi ở đây cố tình sai ngữ cảnh (ghim khi chưa
    phát sóng) và trả 409 — đó là câu trả lời của LOGIC NGHIỆP VỤ, đúng như
    trước khi có tầng xác thực, và tầng này không được đụng vào nó.
    """
    _, _, client = app_store
    sid = _phien_dang_phat(client, HEADER_DUNG)
    client.post(
        "/products",
        json={"product_id": "P-TEST", "name": "Sản phẩm thử", "cost": 1, "price": 2, "stock": 5},
        headers=HEADER_DUNG,
    )
    duong, body = _yeu_cau_ghi(sid)[(method, mau)]
    r = client.request(method, duong, json=body, headers=HEADER_DUNG)
    assert r.status_code not in (401, 403, 429), f"{method} {duong}: {r.status_code} {r.text[:200]}"


@pytest.mark.parametrize(("method", "mau"), MOI_DUONG_GHI)
def test_token_sai_bi_tu_choi_giong_het_khong_co_token(
    method, mau, khoa_sach, app_store, khong_tai_video, gieo_vang_gia
):
    """Token sai không được ưu ái hơn không token — và câu trả lời không nói
    gì về token thật (độ dài, tiền tố, có tồn tại hay không)."""
    _, _, client = app_store
    sid = _tao_phien(client, HEADER_DUNG)
    duong, body = _yeu_cau_ghi(sid)[(method, mau)]
    r = client.request(method, duong, json=body, headers={"Authorization": "Bearer sai-be-bet"})
    assert r.status_code == 401
    assert TOKEN not in r.text


# ---------------------------------------------------------------------------
# 4. CHẾ ĐỘ TRƯNG BÀY — giám khảo dùng thử được, mà không chạm vào dữ liệu thật
# ---------------------------------------------------------------------------


def test_khach_tao_phien_thi_phien_do_la_phien_demo(bat_token, app_store):
    """Khách không token tạo được phiên — và phiên đó là dữ liệu MẪU.

    Đây là bản lề của cả thiết kế: nhờ nó giám khảo chạy trọn wizard trên
    phiên của chính mình mà dữ liệu ấy không bao giờ lọt vào kết quả khoa học
    thật.
    """
    _, store, client = app_store
    sid_khach = _tao_phien(client)
    assert store.get_session(sid_khach)["is_demo"] is True

    sid_van_hanh = _tao_phien(client, HEADER_DUNG)
    assert store.get_session(sid_van_hanh)["is_demo"] is False


def test_khach_chay_tron_wizard_tren_phien_cua_minh(bat_token, app_store):
    """Tạo → lịch gán → phát → ghim → kết thúc, KHÔNG một header nào."""
    _, store, client = app_store
    client.post(
        "/products",
        json={"product_id": "P-DEMO", "name": "Sản phẩm demo", "cost": 1, "price": 9, "stock": 20},
    )
    sid = _tao_phien(client)
    assert client.post(f"/sessions/{sid}/schedule", json={}).status_code == 200
    assert client.post(f"/sessions/{sid}/start").status_code == 200
    r = client.post(f"/sessions/{sid}/actions/execute", json={"product_id": "P-DEMO"})
    assert r.status_code in (200, 409), r.text  # 409 = đang ở khối TẮT, hợp lệ
    assert client.post(f"/sessions/{sid}/end").status_code == 200
    assert store.get_session(sid)["status"] == "ended"


@pytest.mark.parametrize(
    "duong",
    ["schedule", "start", "end", "cancel", "actions/execute", "actions/override"],
)
def test_khach_khong_cham_duoc_vao_phien_that(duong, bat_token, app_store):
    """Thiệt hại nguy hiểm nhất — kết thúc một phiên thí nghiệm đang chạy —
    bị chặn ở đúng chỗ: phiên THẬT thì khách không ghi được gì."""
    _, _, client = app_store
    sid = _phien_dang_phat(client, HEADER_DUNG)
    body = {"product_id": "P", "reason": "hết hàng"} if duong.endswith("override") else {}
    r = client.post(f"/sessions/{sid}/{duong}", json=body)
    assert r.status_code == 403
    assert "dữ liệu THẬT" in r.json()["detail"]


def test_phien_that_van_song_sau_khi_khach_thu_ket_thuc(bat_token, app_store):
    """Không chỉ trả 403 — trạng thái phiên phải KHÔNG đổi một ly."""
    _, store, client = app_store
    sid = _phien_dang_phat(client, HEADER_DUNG)
    truoc = dict(store.get_session(sid))
    assert client.post(f"/sessions/{sid}/end").status_code == 403
    sau = store.get_session(sid)
    assert sau["status"] == truoc["status"] == "live"
    assert sau["end_ts"] is None


def test_duong_ton_tai_nguyen_dong_ca_trong_che_do_trung_bay(bat_token, app_store):
    """``/replays/youtube`` bắt máy chủ tải video theo địa chỉ người lạ đưa —
    mức token, không có ngoại lệ demo, và câu từ chối nói rõ vì sao."""
    _, _, client = app_store
    r = client.post("/replays/youtube", json={"url": "https://www.youtube.com/watch?v=abc"})
    assert r.status_code == 401
    assert "tốn tài nguyên" in r.json()["detail"]


@pytest.mark.parametrize("duong", ["comments", "ticks", "reactions"])
def test_duong_nap_du_lieu_dong_ke_ca_tren_phien_demo(duong, bat_token, app_store):
    """Bộ thu là đường dữ liệu, không phải đồ chơi: mức token áp cả trên phiên
    demo, nên không ai bơm được bản ghi giả vào bất kỳ phiên nào."""
    _, _, client = app_store
    sid = _tao_phien(client)  # phiên DEMO của khách
    body = {
        "comments": {"text": "xin chào"},
        "ticks": {"viewers": 1.0},
        "reactions": {"kind": "like"},
    }
    r = client.post(f"/sessions/{sid}/{duong}", json=body[duong])
    assert r.status_code == 401
    r2 = client.post(f"/sessions/{sid}/{duong}", json=body[duong], headers=HEADER_DUNG)
    assert r2.status_code == 200, r2.text


def test_ma_phien_khong_ton_tai_van_tra_404_chu_khong_phai_403(bat_token, app_store):
    """Cổng xác thực không được biến 404 thành 403: làm vậy là biến chính nó
    thành một máy dò mã phiên (ai đoán đúng id thì nhận mã lỗi khác)."""
    _, _, client = app_store
    khong_co = "00000000-0000-4000-8000-000000000000"
    assert client.post(f"/sessions/{khong_co}/end").status_code == 404
    assert client.post("/sessions/khong-phai-uuid/end").status_code == 404


# ---------------------------------------------------------------------------
# 5. GIỚI HẠN TẦN SUẤT
# ---------------------------------------------------------------------------


def test_khach_bi_chan_khi_gui_qua_nhanh(bat_token, monkeypatch, app_store):
    monkeypatch.setenv("WRITE_RATE_LIMIT_PER_MIN", "5")
    get_settings.cache_clear()
    _, _, client = app_store
    phien = {"platform": "youtube", "planned_duration_min": 90}
    ma = [client.post("/sessions", json=phien).status_code for _ in range(9)]
    assert ma[:5] == [200] * 5
    assert ma[5:] == [429] * 4
    cuoi = client.post("/sessions", json=phien)
    assert cuoi.headers["Retry-After"].isdigit()
    assert "quá nhanh" in cuoi.json()["detail"]


def test_nguoi_van_hanh_co_token_khong_bao_gio_bi_chan(bat_token, monkeypatch, app_store):
    """Bộ thu bắn một bình luận mỗi giây suốt 90 phút — trần tần suất của bản
    trưng bày không được đụng tới nó."""
    monkeypatch.setenv("WRITE_RATE_LIMIT_PER_MIN", "2")
    get_settings.cache_clear()
    _, _, client = app_store
    ma = [
        client.post(
            "/sessions",
            json={"platform": "youtube", "planned_duration_min": 90},
            headers=HEADER_DUNG,
        ).status_code
        for _ in range(8)
    ]
    assert ma == [200] * 8


def test_duong_gieo_du_lieu_co_tran_rieng_theo_gio(bat_token, monkeypatch, app_store):
    """``/demo/seed`` sinh hàng nghìn bản ghi mỗi lần gọi nên trần của nó tính
    theo GIỜ, tách khỏi trần theo phút của các đường ghi thường."""
    monkeypatch.setenv("DEMO_SEED_RATE_LIMIT_PER_HOUR", "1")
    get_settings.cache_clear()
    _, _, client = app_store
    assert client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 30}).status_code == 200
    lan_hai = client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 30})
    assert lan_hai.status_code == 429
    # Trần theo giờ đã cạn, nhưng đường ghi thường vẫn đi được.
    thuong = client.post("/sessions", json={"platform": "youtube", "planned_duration_min": 90})
    assert thuong.status_code == 200


def test_dia_chi_lay_phan_tu_cuoi_cua_x_forwarded_for(bat_token, monkeypatch, app_store):
    """Caddy NỐI THÊM địa chỉ thật vào cuối header. Lấy phần tử đầu thì ai
    cũng tự bịa được một địa chỉ mới mỗi lần gọi và trần tần suất thành đồ
    trang trí — test này là đối chứng cho đúng chỗ ấy."""
    monkeypatch.setenv("WRITE_RATE_LIMIT_PER_MIN", "3")
    get_settings.cache_clear()
    _, _, client = app_store
    phien = {"platform": "youtube", "planned_duration_min": 90}
    ma = [
        client.post(
            "/sessions", json=phien, headers={"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.9"}
        ).status_code
        for i in range(6)
    ]
    assert ma == [200, 200, 200, 429, 429, 429], "địa chỉ bịa ở đầu header không được phá trần"


def test_bo_dem_tan_suat_rieng_cho_tung_ung_dung():
    """Hai ứng dụng trong cùng tiến trình không dùng chung hạn mức của nhau."""
    a, b = create_app(store=InMemoryStore()), create_app(store=InMemoryStore())
    assert isinstance(a.state.gioi_han_ghi, GioiHanTanSuat)
    assert a.state.gioi_han_ghi is not b.state.gioi_han_ghi


def test_tran_bang_khong_la_tat_gioi_han():
    bo = GioiHanTanSuat()
    assert all(bo.xin_luot(("ai-do", "ghi"), 0, 60.0, 1000.0) == 0 for _ in range(100))


def test_cua_so_truot_mo_lai_sau_khi_het_han():
    bo = GioiHanTanSuat()
    assert bo.xin_luot(("ai-do", "ghi"), 2, 60.0, 1000.0) == 0
    assert bo.xin_luot(("ai-do", "ghi"), 2, 60.0, 1001.0) == 0
    assert bo.xin_luot(("ai-do", "ghi"), 2, 60.0, 1002.0) == 58  # còn phải chờ hết cửa sổ
    assert bo.xin_luot(("ai-do", "ghi"), 2, 60.0, 1061.0) == 0  # cửa sổ đã trượt qua


# ---------------------------------------------------------------------------
# 6. KHÔNG PHÁ CHẾ ĐỘ PHÁT TRIỂN CỤC BỘ · KHÔNG LỘ THÔNG TIN HỆ THỐNG
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(("method", "mau"), MOI_DUONG_GHI)
def test_token_rong_thi_moi_duong_ghi_van_mo(
    method, mau, app_store, khong_tai_video, gieo_vang_gia, monkeypatch
):
    """``INGEST_TOKEN`` rỗng = không có bí mật nào = không có cổng nào.

    Đây là hợp đồng giữ cho toàn bộ bộ kiểm thử (và một máy lạ vừa `git clone`
    xong) chạy được mà không phải đính header ở hàng nghìn chỗ.
    """
    monkeypatch.delenv("INGEST_TOKEN", raising=False)
    get_settings.cache_clear()
    _, _, client = app_store
    sid = _tao_phien(client)
    duong, body = _yeu_cau_ghi(sid)[(method, mau)]
    r = client.request(method, duong, json=body)
    assert r.status_code not in (401, 403, 429), f"{method} {duong} bị chặn ở chế độ dev"
    get_settings.cache_clear()


def test_moi_duong_doc_van_mo_khi_da_bat_xac_thuc(khoa_sach, app_store):
    """Cổng chỉ chặn ghi. Mọi đường đọc để mở là ĐÁNH ĐỔI CÓ CHỦ Ý (mã nguồn
    AGPL công khai, giám khảo phải tự kiểm chứng được) — khoá nó lại ở đây sẽ
    là một thay đổi có chủ ý, không phải một tác dụng phụ."""
    _, _, client = app_store
    sid = _phien_dang_phat(client, HEADER_DUNG)
    for duong in (
        "/health",
        "/sessions",
        f"/sessions/{sid}",
        f"/sessions/{sid}/state",
        f"/sessions/{sid}/comments",
        f"/sessions/{sid}/schedule",
        "/openapi.json",
    ):
        assert client.get(duong).status_code == 200, duong


def test_cau_tu_choi_khong_lo_thong_tin_he_thong(khoa_sach, app_store):
    """Thông báo lỗi nói ĐỦ để sửa (tên biến môi trường, tên header) và không
    một chữ nào về bên trong máy chủ."""
    _, _, client = app_store
    r = client.post("/sessions", json={"platform": "youtube", "planned_duration_min": 90})
    than = r.text
    assert r.status_code == 401
    for cam in ("Traceback", "livelift.api", "InMemoryStore", "/src/", 'File "', TOKEN):
        assert cam not in than, f"phản hồi lộ «{cam}»"


def test_openapi_khong_them_truong_is_demo_cho_client(bat_token, app_store):
    """Hợp đồng OpenAPI không đổi: client vẫn KHÔNG có đường tự nhận mình là
    demo (hay là thật) — máy chủ quyết, đúng như gate test_demo_that."""
    _, _, client = app_store
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "is_demo" not in schemas["SessionCreate"].get("properties", {})
