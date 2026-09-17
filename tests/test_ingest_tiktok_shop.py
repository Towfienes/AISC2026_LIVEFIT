"""TikTok Shop LIVE analytics (API chính thức): ký, phân trang, lỗi, bí mật, gộp khối.

Không chạm mạng: mọi lời gọi đi qua ``httpx.MockTransport``; coroutine chạy bằng
``asyncio.run`` (repo không có pytest-asyncio), đúng như ``test_ingest_shopee.py``.

Giới hạn ghi rõ: nhóm CHƯA có app/shop TikTok Shop thật, nên đây là test hành vi
trên phản hồi dựng theo đúng "Response Sample" của tài liệu chính thức — **không
phải** live-fire. Fixture JSON nằm ở ``tests/data/tiktok_shop/`` (mỗi tệp có khóa
``_nguon`` ghi URL + ngày truy cập; bộ nạp bỏ khóa đó trước khi phục vụ).

Nguồn thuật toán ký (truy cập 17/09/2026):
https://partner.tiktokshop.com/docv2/page/sign-your-api-request (update 06/07/2026).
Công thức, viết lại độc lập trong :func:`_ky_doc_lap`::

    chuoi = path + Σ_{k sắp theo chữ cái, k ∉ {sign, access_token}} (k + v) + body
    sign  = hex(HMAC-SHA256(khóa = app_secret, thông điệp = app_secret + chuoi + app_secret))
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import importlib.util
import json
import logging
import sys
import time
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import yaml

from livelift.config import Settings
from livelift.core.assigner.outer import Block
from livelift.ingest import tiktok_shop as tts
from livelift.ingest.tiktok_shop import (
    PATH_LIVE_LIST,
    RATE_LIMIT_MAX_RETRIES,
    TRANSIENT_MAX_RETRIES,
    TRUONG_CONG_DON,
    TikTokShopApiError,
    TikTokShopAuthError,
    TikTokShopConfigError,
    TikTokShopLiveAnalyticsClient,
    TikTokShopPermissionError,
    TikTokShopRateLimitError,
    build_signed_query,
    chuoi_can_ky,
    gop_theo_khoi,
    phan_loai_loi,
    phien_moi_nhat,
    tao_chu_ky,
)

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "tests" / "data" / "tiktok_shop"

APP_KEY = "38abcd"
APP_SECRET = "bi-mat-ung-dung-gia"
TOKEN = "TTP_token-nguoi-ban-gia-song-7-ngay"
SHOP_CIPHER = "GCP_XF90igAAAABh00qsWgtvOiGFNqyubMt3"
TS = 1789105000
LIVE_ID = "7512345678901234567"
PATH_PHUT = f"/analytics/202510/shop_lives/{LIVE_ID}/performance_per_minutes"
PATH_SAN_PHAM = f"/analytics/202512/shop/{LIVE_ID}/products_performance"

#: Ví dụ CHÍNH THỨC của tài liệu (app_secret e59af819cc). Chạy lại bằng OpenSSL:
#:   printf '%s' 'e59af819cc/authorization/202309/shopsapp_key29a39dtimestamp1623812664e59af819cc' \
#:     | openssl dgst -sha256 -hmac 'e59af819cc'
SIGN_CHINH_THUC = "b596b73e0cc6de07ac26f036364178ab16b0a907af13d43f0a0cd2345f582dc8"

#: Vector TỰ TÍNH bằng OpenSSL 3.5.5 (Git Bash), độc lập với mã Python:
#:   S='bi-mat-ung-dung-gia'
#:   P='/analytics/202510/shop_lives/7512345678901234567/performance_per_minutes'
#:   C='GCP_XF90igAAAABh00qsWgtvOiGFNqyubMt3'
#:   printf '%s' "${S}${P}app_key38abcdcurrencyLOCALshop_cipher${C}timestamp1789105000${S}" \
#:     | openssl dgst -sha256 -hmac "$S"
SIGN_PHUT_TRANG_1 = "1a162e4c2ef1000bff7b1579e899a953fb69ee127b5d11b05325eb590bd5eaf2"
#: như trên, chèn 'page_tokencGFnZV9udW1iZXI9Mg==' giữa 'currencyLOCAL' và 'shop_cipher'
SIGN_PHUT_TRANG_2 = "518889f58be75b5330976bd8284e1e6305ef69a53ffac6c493ab47173e461896"
#: như trên, chèn 'page_tokencGFnZV9udW1iZXI9MQ=='
SIGN_PHUT_TOKEN_MQ = "30a273bb12eba1e39455dab226e59c54d6b682326eb61f8ec8a343bb557f0d0d"
#: L='/analytics/202509/shop_lives/performance'; thông điệp
#: "${S}${L}account_typeOFFICIAL_ACCOUNTSapp_key38abcdcurrencyLOCALend_date_lt2026-09-18"
#: "page_size100shop_cipher${C}start_date_ge2026-09-11timestamp1789105000${S}"
SIGN_DANH_SACH = "36e9dcf16389cece6e9b1643a89d4ab997a321bebcbb705831912f3411dc7c0c"
#: Chuỗi ví dụ có THÂN yêu cầu, chép nguyên văn từ tài liệu (Update Shop Webhook) — lưu ý
#: shop_cipher ở đó kết thúc bằng "aIK" rồi mới tới "timestamp". Bọc S rồi ký:
#:   printf '%s' "${S}${W}${S}" | openssl dgst -sha256 -hmac "$S"
CHUOI_WEBHOOK_TAI_LIEU = (
    "/event/202309/webhooksapp_key68xu9ks5p4i8shop_cipherROW_xkMbgAAAeVAQra0eZWebFQq5aIK"
    'timestamp1696909648{"address":"https://partner.tiktokshop.com","event_type":"PACKAGE_UPDATE"}'
)
SIGN_WEBHOOK = "e3fd8a3c0a1772c757f89a3a3120ed6f891197935001e0a5ad9c99963fb8c88d"


def _ky_doc_lap(request: httpx.Request, secret: str = APP_SECRET) -> str:
    """Tính lại chữ ký từ CHÍNH yêu cầu đã gửi — không dùng mã của mô-đun."""
    q = {k: v for k, v in request.url.params.items() if k not in ("sign", "access_token")}
    chuoi = request.url.path + "".join(k + q[k] for k in sorted(q)) + request.content.decode()
    thong_diep = secret + chuoi + secret
    return hmac.new(secret.encode(), thong_diep.encode(), hashlib.sha256).hexdigest()


def _fixture(ten: str) -> dict[str, Any]:
    data = json.loads((DATA / ten).read_text(encoding="utf-8"))
    data.pop("_nguon", None)
    return data


def _json(payload: dict[str, Any], status: int = 200, headers: dict[str, str] | None = None):
    return httpx.Response(status, json=payload, headers=headers)


def _loi(code: int | str, message: str, status: int = 200, **headers: str) -> httpx.Response:
    return httpx.Response(
        status,
        json={"code": code, "message": message, "request_id": "rq-loi-1", "data": {}},
        headers=headers or None,
    )


@pytest.fixture
def sleeps(monkeypatch):
    """Ghi lại thời gian ngủ; không có gì thật sự chờ."""
    recorded: list[float] = []

    async def fake_sleep(delay: float) -> None:
        recorded.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)
    return recorded


def _client(handler, **overrides) -> TikTokShopLiveAnalyticsClient:
    kwargs: dict[str, Any] = {
        "app_key": APP_KEY,
        "app_secret": APP_SECRET,
        "access_token": TOKEN,
        "shop_cipher": SHOP_CIPHER,
        "client": httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        "min_interval_s": 0,
        "clock": lambda: TS,
    }
    kwargs.update(overrides)
    return TikTokShopLiveAnalyticsClient(**kwargs)


def _chay(coro_factory):
    async def run():
        return await coro_factory()

    return asyncio.run(run())


def _handler_phut(requests: list[httpx.Request]):
    trang = {
        None: "performance_per_minutes_trang_1.json",
        "cGFnZV9udW1iZXI9Mg==": "performance_per_minutes_trang_2.json",
        "cGFnZV9udW1iZXI9Mw==": "performance_per_minutes_trang_3.json",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == PATH_PHUT
        return _json(_fixture(trang[request.url.params.get("page_token")]))

    return handler


# ---------------------------------------------------------------------------
# 1. Ký yêu cầu
# ---------------------------------------------------------------------------


def test_tai_lap_dung_vi_du_chinh_thuc_cua_tai_lieu():
    query = {"app_key": "29a39d", "timestamp": "1623812664"}
    assert tao_chu_ky("/authorization/202309/shops", query, "e59af819cc") == SIGN_CHINH_THUC
    assert (
        chuoi_can_ky("/authorization/202309/shops", query).decode()
        == "/authorization/202309/shopsapp_key29a39dtimestamp1623812664"
    )


def test_sign_va_access_token_khong_bao_gio_vao_chuoi_ky():
    query = {
        "timestamp": "1623812664",
        "sign": "gia-tri-cu",
        "access_token": "token-kieu-cu",
        "app_key": "29a39d",
    }
    assert tao_chu_ky("/authorization/202309/shops", query, "e59af819cc") == SIGN_CHINH_THUC


def test_chuoi_co_than_yeu_cau_khop_nguyen_van_tai_lieu():
    body = b'{"address":"https://partner.tiktokshop.com","event_type":"PACKAGE_UPDATE"}'
    query = {
        "timestamp": "1696909648",
        "shop_cipher": "ROW_xkMbgAAAeVAQra0eZWebFQq5aIK",
        "app_key": "68xu9ks5p4i8",
    }
    assert chuoi_can_ky("/event/202309/webhooks", query, body).decode() == CHUOI_WEBHOOK_TAI_LIEU
    assert tao_chu_ky("/event/202309/webhooks", query, APP_SECRET, body) == SIGN_WEBHOOK
    # multipart/form-data: tài liệu bảo KHÔNG nối thân yêu cầu.
    khong_than = chuoi_can_ky("/event/202309/webhooks", query, body, "multipart/form-data; b=x")
    assert not khong_than.endswith(body)


@pytest.mark.parametrize(
    ("page_token", "expected"),
    [(None, SIGN_PHUT_TRANG_1), ("cGFnZV9udW1iZXI9MQ==", SIGN_PHUT_TOKEN_MQ)],
)
def test_vector_openssl_cho_endpoint_theo_phut(page_token, expected):
    query = {"currency": "LOCAL", "page_token": page_token}
    params = build_signed_query(PATH_PHUT, query, APP_KEY, APP_SECRET, SHOP_CIPHER, TS)
    assert params["sign"] == expected


def test_bo_tham_so_da_ky_dung_bo_khoa_va_khong_co_token():
    params = build_signed_query(
        PATH_PHUT,
        {"currency": "LOCAL", "page_token": "", "x": None},
        APP_KEY,
        APP_SECRET,
        SHOP_CIPHER,
        TS,
    )
    assert set(params) == {"app_key", "currency", "shop_cipher", "timestamp", "sign"}
    assert TOKEN not in json.dumps(params)
    assert APP_SECRET not in json.dumps(params)
    with pytest.raises(ValueError, match="10 chữ số"):
        build_signed_query(PATH_PHUT, {}, APP_KEY, APP_SECRET, SHOP_CIPHER, TS * 1000)


# ---------------------------------------------------------------------------
# 2. Yêu cầu thật sự gửi đi + phân trang
# ---------------------------------------------------------------------------


def test_phan_trang_theo_phut_doc_du_ba_trang_va_moi_trang_ky_dung():
    requests: list[httpx.Request] = []
    client = _client(_handler_phut(requests))
    hs = _chay(lambda: client.performance_per_minutes(LIVE_ID))

    assert [r.url.params.get("page_token") for r in requests] == [
        None,
        "cGFnZV9udW1iZXI9Mg==",
        "cGFnZV9udW1iZXI9Mw==",
    ]
    assert requests[0].url.params["sign"] == SIGN_PHUT_TRANG_1
    assert requests[1].url.params["sign"] == SIGN_PHUT_TRANG_2
    for r in requests:
        assert r.url.host == "open-api.tiktokglobalshop.com"
        assert r.method == "GET"
        assert r.headers["x-tts-access-token"] == TOKEN
        assert r.headers["content-type"] == "application/json"
        assert r.url.params["shop_cipher"] == SHOP_CIPHER
        assert r.url.params["currency"] == "LOCAL"
        assert len(r.url.params["timestamp"]) == 10
        assert r.url.params["sign"] == _ky_doc_lap(r)
        assert TOKEN not in str(r.url)
        assert APP_SECRET not in str(r.url)
        assert "access_token" not in r.url.params
    assert hs.so_trang == 3
    assert len(hs.intervals) == 5
    assert hs.total_count == 5
    assert hs.canh_bao == []
    assert hs.overall["duration"] == 1800
    assert [i["start_time"] for i in hs.intervals] == [1789477200 + 60 * k for k in range(5)]
    assert len(hs.request_ids) == 3


def test_dong_ho_that_van_ky_dung_voi_cong_thuc_doc_lap():
    requests: list[httpx.Request] = []
    client = _client(_handler_phut(requests), clock=time.time)
    _chay(lambda: client.performance_per_minutes(LIVE_ID))
    assert all(r.url.params["sign"] == _ky_doc_lap(r) for r in requests)


def test_total_count_lech_thi_canh_bao_khong_tu_sua():
    trang = _fixture("performance_per_minutes_trang_3.json")
    trang["data"]["total_count"] = 9

    client = _client(lambda request: _json(trang))
    hs = _chay(lambda: client.performance_per_minutes(LIVE_ID))
    assert len(hs.intervals) == 1
    assert any("total_count=9" in c for c in hs.canh_bao)


def test_page_token_lap_lai_thi_bao_loi_khong_lap_vo_han():
    trang = _fixture("performance_per_minutes_trang_1.json")
    trang["data"]["total_count"] = 100  # còn thiếu, và token luôn giống nhau
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _json(trang)

    client = _client(handler)
    with pytest.raises(TikTokShopApiError, match="page_token đã dùng"):
        _chay(lambda: client.performance_per_minutes(LIVE_ID))
    assert len(calls) == 2


def test_qua_so_trang_thi_bao_loi_chu_khong_cat_am_tham():
    client = _client(_handler_phut([]))
    with pytest.raises(TikTokShopApiError, match="vẫn còn trang sau") as excinfo:
        _chay(lambda: client.performance_per_minutes(LIVE_ID, max_pages=2))
    assert excinfo.value.code == "qua_so_trang"


def test_danh_sach_phien_gui_dung_tham_so_va_gop_hai_trang():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.path == PATH_LIVE_LIST
        if request.url.params.get("page_token") == "cGFnZV9udW1iZXI9Mg==":
            return _json(_fixture("shop_lives_performance_trang_2.json"))
        return _json(_fixture("shop_lives_performance_trang_1.json"))

    client = _client(handler)
    ds = _chay(lambda: client.list_live_sessions(date(2026, 9, 11), "2026-09-18"))
    dau = requests[0].url.params
    assert dau["start_date_ge"] == "2026-09-11"
    assert dau["end_date_lt"] == "2026-09-18"
    assert dau["account_type"] == "OFFICIAL_ACCOUNTS"
    assert dau["page_size"] == "100"
    assert dau["currency"] == "LOCAL"
    assert "sort_field" not in dau
    assert dau["sign"] == SIGN_DANH_SACH
    assert len(requests) == 2
    assert [p["id"] for p in ds.phien] == [
        "7512345678901234567",
        "7512345678901234568",
        "7512345678901234569",
    ]
    assert ds.total_count == 3
    assert ds.latest_available_date == "2026-09-16"
    assert ds.so_trang == 2
    assert phien_moi_nhat(ds.phien)["id"] == "7512345678901234567"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"start_date_ge": "2026-09-18", "end_date_lt": "2026-09-11"},
        {"start_date_ge": "11/09/2026", "end_date_lt": "2026-09-18"},
        {"start_date_ge": "2026-09-11", "end_date_lt": "2026-09-18", "page_size": 101},
        {"start_date_ge": "2026-09-11", "end_date_lt": "2026-09-18", "account_type": "CREATOR"},
        {"start_date_ge": "2026-09-11", "end_date_lt": "2026-09-18", "currency": "VND"},
    ],
)
def test_danh_sach_phien_kiem_tham_so_truoc_khi_goi_mang(kwargs):
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("không được gọi mạng khi tham số sai")

    client = _client(handler)
    with pytest.raises(ValueError):
        _chay(lambda: client.list_live_sessions(**kwargs))


def test_hieu_suat_san_pham_mot_loi_goi_giu_nguyen_ten_truong_tai_lieu():
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _json(_fixture("products_performance.json"))

    client = _client(handler)
    products = _chay(lambda: client.products_performance(LIVE_ID, sort_order="DESC"))
    assert len(requests) == 1
    assert requests[0].url.path == PATH_SAN_PHAM
    assert requests[0].url.params["sort_order"] == "DESC"
    assert "page_token" not in requests[0].url.params
    assert requests[0].url.params["sign"] == _ky_doc_lap(requests[0])
    assert len(products) == 2
    assert products[0]["traffic"]["produt_clicks"] == 80  # sai chính tả NGUYÊN VĂN tài liệu


@pytest.mark.parametrize("live_id", ["../7512", "7512/abc", "7512?x=1", "", "a" * 65])
def test_live_id_co_ky_tu_doi_duong_dan_bi_tu_choi(live_id):
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("không được gọi mạng với live_id lạ")

    client = _client(handler)
    with pytest.raises(ValueError, match="live_id"):
        _chay(lambda: client.performance_per_minutes(live_id))
    with pytest.raises(ValueError, match="live_id"):
        _chay(lambda: client.products_performance(live_id))


def test_thieu_bien_bao_ten_bien_va_khong_goi_mang():
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("không được gọi mạng khi thiếu biến")

    client = _client(handler, app_secret="", shop_cipher="  ")
    with pytest.raises(ValueError) as excinfo:
        _chay(lambda: client.performance_per_minutes(LIVE_ID))
    text = str(excinfo.value)
    assert "TIKTOK_SHOP_APP_SECRET" in text
    assert "TIKTOK_SHOP_SHOP_CIPHER" in text
    assert "TIKTOK_SHOP_ACCESS_TOKEN" not in text
    assert TOKEN not in text


# ---------------------------------------------------------------------------
# 3. Phân loại lỗi
# ---------------------------------------------------------------------------

LOI_TAI_LIEU = json.loads((DATA / "loi_chung.json").read_text(encoding="utf-8"))["loi"]
LOP_THEO_LOAI = {
    "auth": TikTokShopAuthError,
    "permission": TikTokShopPermissionError,
    "rate_limit": TikTokShopRateLimitError,
    "config": TikTokShopConfigError,
    "transient": TikTokShopApiError,
}


@pytest.mark.parametrize("loi", LOI_TAI_LIEU, ids=lambda d: f"{d['code']}-{d['loai']}")
def test_moi_ma_loi_trong_tai_lieu_ra_dung_lop_va_co_cau_tieng_viet(loi, sleeps):
    status = loi.get("http_status", loi.get("http_status_gia", 200))
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _loi(loi["code"], loi["message"], status)

    client = _client(handler)
    with pytest.raises(TikTokShopApiError) as excinfo:
        _chay(lambda: client.performance_per_minutes(LIVE_ID))
    err = excinfo.value
    assert err.loai == loi["loai"]
    assert isinstance(err, LOP_THEO_LOAI[loi["loai"]])
    assert err.code == str(loi["code"])
    assert err.request_id == "rq-loi-1"
    assert err.giai_thich
    assert str(err).startswith(err.giai_thich)
    if loi["code"] == 36009037:
        assert len(calls) == 1, "hạn mức theo giờ của shop thử: thử lại chỉ đốt thêm hạn mức"
    elif loi["loai"] == "rate_limit":
        assert len(calls) == RATE_LIMIT_MAX_RETRIES + 1
    elif loi["loai"] == "transient":
        assert len(calls) == TRANSIENT_MAX_RETRIES + 1
    else:
        assert len(calls) == 1, "lỗi danh tính/quyền/cấu hình không được thử lại"


@pytest.mark.parametrize(
    "message",
    [
        "Invalid credentials. The access_token header is invalid.",
        "Invalid credentials. The `access_token` header is invalid.",
        # Cổng API thật dùng nháy đơn (phản hồi 17/09/2026: "Invalid 'app_key' query parameter").
        "Invalid credentials. The 'access_token' header is invalid. For more details: https://x",
        'Invalid credentials. The "access_token" header is invalid.',
        "Invalid credentials. The ‘access_token’ header is invalid.",
    ],
)
def test_36009004_access_token_la_loi_danh_tinh_voi_moi_kieu_dau_nhay(message):
    assert phan_loai_loi("36009004", message, 400) == "auth"
    assert isinstance(tts.tao_loi("36009004", message, 400), TikTokShopAuthError)
    assert "TIKTOK_SHOP_ACCESS_TOKEN" in tts.giai_thich_loi("36009004", message, 400)


def test_36009003_loi_noi_bo_duoc_thu_lai_va_noi_cach_lien_he_ho_tro(sleeps):
    thong_diep = (
        "Internal error. Please try again. If the issue persists after multiple attempts, "
        "please contact platform support."
    )
    assert phan_loai_loi("36009003", thong_diep, 200) == "transient"
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) <= 2:
            return _loi(36009003, thong_diep)
        return _json(_fixture("products_performance.json"))

    client = _client(handler)
    assert len(_chay(lambda: client.products_performance(LIVE_ID))) == 2
    assert len(calls) == 3
    assert "request_id" in tts.giai_thich_loi("36009003", thong_diep)
    assert "chưa phân loại" not in tts.giai_thich_loi("36009003", thong_diep)


def test_bang_tu_khoa_36009004_cac_nhanh_con_lai():
    assert "Đồng hồ" in tts.giai_thich_loi("36009004", "Invalid timestamp. lesser than 0")
    assert phan_loai_loi("36009004", "một thông điệp lạ") == "other"
    assert phan_loai_loi("99999999", "", 401) == "auth"
    assert phan_loai_loi("99999999", "", 403) == "permission"
    assert phan_loai_loi("", "", 429) == "rate_limit"


def test_thieu_quyen_noi_ro_goi_can_bat_va_phai_uy_quyen_lai():
    text = tts.giai_thich_loi("105005")
    assert "TikTok Shop Analytics" in text
    assert "data.shop_analytics.public.read" in text
    assert "ỦY QUYỀN LẠI" in text
    assert "tài khoản CHÍNH THỨC" in tts.giai_thich_loi("66009315")
    assert "user_type = 0" in tts.giai_thich_loi("101000")


THAM_DO_THAT = json.loads((DATA / "loi_tham_do_that_17092026.json").read_text(encoding="utf-8"))[
    "phan_hoi"
]


@pytest.mark.parametrize(
    "mau", THAM_DO_THAT, ids=lambda d: f"{d['http_status']}-{d['body']['code']}"
)
def test_phong_bi_loi_that_cua_cong_api_duoc_phan_loai_dung(mau, sleeps):
    """Phản hồi THẬT (17/09/2026, danh tính giả): 'data': null, HTTP 400/404, nháy đơn."""
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(mau["http_status"], json=mau["body"])

    client = _client(handler)
    with pytest.raises(TikTokShopApiError) as excinfo:
        _chay(lambda: client.performance_per_minutes(LIVE_ID))
    assert excinfo.value.loai == mau["loai_mong_doi"]
    assert excinfo.value.status == mau["http_status"]
    assert len(calls) == 1
    if mau["body"]["code"] == 36009004:
        assert isinstance(excinfo.value, TikTokShopAuthError)
        assert str(excinfo.value).startswith("TIKTOK_SHOP_APP_KEY không hợp lệ")


def test_gioi_han_nhip_ton_trong_retry_after_roi_thanh_cong(sleeps):
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) <= 2:
            return _loi(36009002, "Too many requests.", 429, **{"Retry-After": "7"})
        return _json(_fixture("products_performance.json"))

    client = _client(handler)
    products = _chay(lambda: client.products_performance(LIVE_ID))
    assert len(products) == 2
    assert len(calls) == 3
    assert len(sleeps) == 2
    assert all(s >= 7 for s in sleeps)


def test_gioi_han_nhip_het_luot_thi_noi_token_van_tot(sleeps):
    client = _client(lambda request: _loi(36009002, "Too many requests.", 429))
    with pytest.raises(TikTokShopRateLimitError) as excinfo:
        _chay(lambda: client.products_performance(LIVE_ID))
    assert "token VẪN TỐT" in str(excinfo.value)
    # Backoff mũ: 1, 2, 4, 8, 16 (+ jitter ≤ 0,5 s).
    assert [int(s) for s in sleeps] == [1, 2, 4, 8, 16]


def test_retry_after_qua_dai_thi_bao_ngay_khong_treo(sleeps):
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return _loi(36009002, "Too many requests.", 429, **{"Retry-After": "3600"})

    client = _client(handler)
    with pytest.raises(TikTokShopRateLimitError):
        _chay(lambda: client.products_performance(LIVE_ID))
    assert len(calls) == 1
    assert sleeps == []


def test_retry_after_dang_ngay_http():
    now = datetime(2015, 10, 21, 7, 27, 50, tzinfo=UTC)
    assert tts._retry_after_s("Wed, 21 Oct 2015 07:28:00 GMT", now=now) == 10.0
    assert tts._retry_after_s("12", now=now) == 12.0
    assert tts._retry_after_s("không phải ngày", now=now) is None


def test_loi_5xx_khong_phai_json_thu_lai_co_gioi_han(sleeps):
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(503, text="<html>Service Unavailable</html>")

    client = _client(handler)
    with pytest.raises(TikTokShopApiError) as excinfo:
        _chay(lambda: client.products_performance(LIVE_ID))
    assert excinfo.value.loai == "transient"
    assert excinfo.value.status == 503
    assert len(calls) == TRANSIENT_MAX_RETRIES + 1


# ---------------------------------------------------------------------------
# 4. Bí mật không lọt ra lỗi hay log
# ---------------------------------------------------------------------------


def test_loi_khong_lo_token_va_secret_ke_ca_khi_may_chu_doi_lai(sleeps):
    def handler(request: httpx.Request) -> httpx.Response:
        return _loi(
            36009004,
            f"Invalid credentials. The x-tts-access-token header is invalid: {TOKEN} "
            f"/ {APP_SECRET}",
        )

    client = _client(handler)
    with pytest.raises(TikTokShopAuthError) as excinfo:
        _chay(lambda: client.performance_per_minutes(LIVE_ID))
    text = str(excinfo.value) + repr(excinfo.value.args) + excinfo.value.api_message
    assert TOKEN not in text
    assert APP_SECRET not in text
    assert "***" in text
    assert "open-api.tiktokglobalshop.com" not in text


def test_loi_mang_khong_lo_url(sleeps):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"connect failed {request.url}", request=request)

    client = _client(handler)
    with pytest.raises(TikTokShopApiError) as excinfo:
        _chay(lambda: client.performance_per_minutes(LIVE_ID))
    text = str(excinfo.value)
    assert excinfo.value.code == "network"
    assert "open-api.tiktokglobalshop.com" not in text
    assert "sign=" not in text
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__context__ is None


def test_log_khong_lo_token_hay_secret(sleeps, caplog):
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return _loi(36009002, f"Too many requests {TOKEN}", 429)
        if len(calls) == 2:
            return _loi(105005, f"Access denied {APP_SECRET}")
        return _json({})  # pragma: no cover

    caplog.set_level(logging.DEBUG)
    client = _client(handler)
    with pytest.raises(TikTokShopPermissionError):
        _chay(lambda: client.performance_per_minutes(LIVE_ID))
    assert caplog.records, "tiền đề: có dòng log (thử lại + httpx)"
    for record in caplog.records:
        message = record.getMessage()
        assert TOKEN not in message
        assert APP_SECRET not in message


# ---------------------------------------------------------------------------
# 5. gop_theo_khoi — quy chuỗi theo phút về khối switchback
# ---------------------------------------------------------------------------

T0 = datetime(2026, 9, 15, 13, 0, 0, tzinfo=UTC)  # 20:00 giờ VN
T0_S = 1789477200


def _phut(offset_s: int, clicks: int = 1, gmv: str | None = "1000.50", do_dai: int = 60, **extra):
    st = T0_S + offset_s
    interval: dict[str, Any] = {
        "start_time": st,
        "end_time": st + do_dai,
        "sales": {"items_sold": 1, "customers": 1, "sku_orders": 1, "main_orders": 1},
        "traffic": {
            "viewers": 10,
            "views": 12,
            "product_impressions": 30,
            "ctr": "0.1",
            "product_clicks": clicks,
            "impressions": 50,
        },
        "interactions": {
            "new_followers": 0,
            "shares": 0,
            "comments": 2,
            "likes": 5,
            "comment_rate": "0.1",
        },
        "conversion": {"created_sku_orders": 1, "sku_order_rate": "0.02"},
    }
    if gmv is not None:
        interval["sales"]["gmv"] = {"amount": gmv, "currency": "VND"}
    interval.update(extra)
    return interval


def _khoi(*bien: int) -> list[dict[str, Any]]:
    out = []
    for i, (s, e) in enumerate(zip(bien, bien[1:], strict=False)):
        out.append(
            {
                "block_index": i,
                "assignment": "ON" if i % 2 == 0 else "OFF",
                "is_washout": False,
                "start_offset_s": s,
                "end_offset_s": e,
            }
        )
    return out


def test_ranh_gioi_trung_phut_thi_moi_phut_vao_dung_mot_khoi():
    intervals = [_phut(60 * k, clicks=k) for k in range(30)]
    kq = gop_theo_khoi(intervals, _khoi(0, 600, 1200, 1800), T0)
    assert [k.so_phut for k in kq.khoi] == [10, 10, 10]
    assert kq.so_phut_cat_ngang == 0
    assert [k.tong["product_clicks"] for k in kq.khoi] == [
        sum(range(0, 10)),
        sum(range(10, 20)),
        sum(range(20, 30)),
    ]
    assert [k.assignment for k in kq.khoi] == ["ON", "OFF", "ON"]
    assert kq.khoi[0].gmv == Decimal("10005.00")
    assert kq.khoi[0].tien_te == "VND"


def test_phut_cat_ngang_ranh_gioi_bi_loai_va_duoc_dem():
    """Ranh giới có jitter (630 s, 1230 s): phút [600,660) và [1200,1260) chạm hai khối."""
    intervals = [_phut(60 * k, clicks=k) for k in range(30)]
    kq = gop_theo_khoi(intervals, _khoi(0, 630, 1230, 1800), T0)
    assert [k.so_phut for k in kq.khoi] == [10, 9, 9]
    assert kq.so_phut_cat_ngang == 2
    assert kq.phut_cat_ngang == [(T0_S + 600, T0_S + 660), (T0_S + 1200, T0_S + 1260)]
    assert sum(k.so_phut for k in kq.khoi) + kq.so_phut_cat_ngang == 30
    assert kq.khoi[1].tong["product_clicks"] == sum(range(11, 20))


def test_burn_in_bo_phut_dau_khoi_va_dem_rieng():
    intervals = [_phut(60 * k) for k in range(30)]
    kq = gop_theo_khoi(intervals, _khoi(0, 630, 1230, 1800), T0, burn_in_s=60)
    assert [k.so_phut_bo_burn_in for k in kq.khoi] == [1, 1, 1]
    assert [k.so_phut for k in kq.khoi] == [9, 8, 8]


@pytest.mark.parametrize("do_dai", [60, 59, 0], ids=["end-mo", "end-dong", "end-bang-start"])
def test_end_time_mo_dong_hay_bang_start_deu_xu_ly_nhu_nhau(do_dai):
    blocks = _khoi(0, 600, 1200)
    kq = gop_theo_khoi([_phut(540, do_dai=do_dai), _phut(600, do_dai=do_dai)], blocks, T0)
    assert [k.so_phut for k in kq.khoi] == [1, 1]
    assert kq.so_phut_cat_ngang == 0
    assert kq.so_phut_gia_dinh_60s == (0 if do_dai == 60 else 2)


@pytest.mark.parametrize("do_dai", [60, 59, 0], ids=["end-mo", "end-dong", "end-bang-start"])
def test_ranh_gioi_lech_giay_cat_ngang_voi_moi_kieu_end_time(do_dai):
    """Ranh giới 630 s / 1230 s (jitter): phút [600,660) và [1200,1260) phải bị loại.

    Mẫu chính thức để start_time == end_time; nếu chỉ so end_time thì phút 600 bị
    cộng trọn vào khối BẬT dù 30 giây cuối thuộc khối TẮT.
    """
    intervals = [_phut(60 * k, clicks=k, do_dai=do_dai) for k in range(30)]
    kq = gop_theo_khoi(intervals, _khoi(0, 630, 1230, 1800), T0)
    assert [k.so_phut for k in kq.khoi] == [10, 9, 9]
    assert kq.so_phut_cat_ngang == 2
    assert [st for st, _ in kq.phut_cat_ngang] == [T0_S + 600, T0_S + 1200]
    assert [k.tong["product_clicks"] for k in kq.khoi] == [
        sum(range(0, 10)),
        sum(range(11, 20)),
        sum(range(21, 30)),
    ]
    assert sum(k.so_phut for k in kq.khoi) + kq.so_phut_cat_ngang == 30


def test_phut_do_dai_0_bat_dau_trong_khoang_trong_ma_cham_khoi_la_cat_ngang():
    # Khoảng trống [600, 630): phút bắt đầu 600 chạm khối [630, 1200) → cắt ngang, không
    # phải "ngoài lịch".
    blocks = [*_khoi(0, 600), {"start_offset_s": 630, "end_offset_s": 1200}]
    kq = gop_theo_khoi([_phut(600, do_dai=0), _phut(1200, do_dai=0)], blocks, T0)
    assert kq.so_phut_cat_ngang == 1
    assert kq.so_phut_ngoai_lich == 1
    assert [k.so_phut for k in kq.khoi] == [0, 0]


def test_phut_ngoai_lich_hong_va_trung_lap_deu_duoc_dem():
    intervals = [
        _phut(-120),  # trước giờ lên sóng, không chạm khối
        _phut(-30),  # [-30, 30): cắt ngang lúc lên sóng
        _phut(0),
        _phut(0),  # trùng start_time
        _phut(660),  # nằm trong khoảng trống [600, 720)
        _phut(1800),  # sau khối cuối
        {"start_time": T0_S + 60},  # thiếu end_time
        {"start_time": T0_S + 120, "end_time": T0_S + 60},  # end < start
    ]
    blocks = [*_khoi(0, 600), {"start_offset_s": 720, "end_offset_s": 1800}]
    kq = gop_theo_khoi(intervals, blocks, T0_S)
    assert [k.so_phut for k in kq.khoi] == [1, 0]
    assert kq.so_phut_ngoai_lich == 3
    assert kq.so_phut_cat_ngang == 1
    assert kq.so_phut_trung_lap == 1
    assert kq.so_phut_hong == 2
    assert kq.khoi[1].block_index is None
    assert kq.khoi[1].tong["product_clicks"] is None
    assert kq.khoi[1].gmv is None


def test_chi_cong_truong_cong_duoc_va_ghi_so_phut_thieu():
    assert "customers" not in TRUONG_CONG_DON
    assert not any(t.endswith(("_rate", "ctr")) for _, t in TRUONG_CONG_DON.values())
    thieu_traffic = _phut(60, gmv=None)
    del thieu_traffic["traffic"]
    kq = gop_theo_khoi([_phut(0, gmv="0.50"), thieu_traffic], _khoi(0, 600), T0)
    khoi = kq.khoi[0]
    assert khoi.so_phut == 2
    assert khoi.tong["product_clicks"] == 1
    assert khoi.tong["comments"] == 4
    assert khoi.tong["viewers_cong_moi_phut"] == 10
    assert khoi.so_phut_thieu["product_clicks"] == 1
    assert khoi.so_phut_thieu["gmv"] == 1
    assert khoi.gmv == Decimal("0.50")


def test_gop_tu_fixture_chinh_thuc():
    intervals = []
    for so in (1, 2, 3):
        intervals += _fixture(f"performance_per_minutes_trang_{so}.json")["data"]["performance"][
            "intervals"
        ]
    kq = gop_theo_khoi(intervals, _khoi(0, 120, 300), T0)
    assert [k.so_phut for k in kq.khoi] == [2, 3]
    assert [k.tong["product_clicks"] for k in kq.khoi] == [21, 43]
    assert [k.tong["comments"] for k in kq.khoi] == [12, 19]
    assert [k.gmv for k in kq.khoi] == [Decimal("150000.00"), Decimal("750000.50")]


def test_nhan_block_cua_bo_lap_lich_va_timestamp_so():
    blocks = [
        Block(
            index=0,
            phase="early",
            start_offset_s=0,
            end_offset_s=600,
            is_washout=False,
            assignment="ON",
            propensity=0.5,
        ),
        Block(
            index=1,
            phase="early",
            start_offset_s=600,
            end_offset_s=1200,
            is_washout=True,
            assignment=None,
            propensity=None,
        ),
    ]
    kq = gop_theo_khoi([_phut(0), _phut(600)], blocks, T0_S)
    assert [(k.block_index, k.assignment, k.is_washout, k.so_phut) for k in kq.khoi] == [
        (0, "ON", False, 1),
        (1, None, True, 1),
    ]


@pytest.mark.parametrize(
    ("intervals", "blocks", "start_ts", "match"),
    [
        ([], _khoi(0, 600), datetime(2026, 9, 15, 13, 0), "múi giờ"),
        ([], [*_khoi(0, 600), {"start_offset_s": 500, "end_offset_s": 900}], T0, "chồng"),
        ([], [{"start_offset_s": 600, "end_offset_s": 600}], T0, "rỗng"),
        ([], [{"start_offset_s": 0}], T0, "end_offset_s"),
        (
            [_phut(0), {**_phut(60), "sales": {"gmv": {"amount": "1", "currency": "USD"}}}],
            _khoi(0, 600),
            T0,
            "tiền tệ",
        ),
    ],
)
def test_dau_vao_mo_ho_bi_tu_choi(intervals, blocks, start_ts, match):
    with pytest.raises(ValueError, match=match):
        gop_theo_khoi(intervals, blocks, start_ts)


# ---------------------------------------------------------------------------
# 6. Cấu hình, .env.example, compose
# ---------------------------------------------------------------------------

BON_BIEN = (
    "TIKTOK_SHOP_APP_KEY",
    "TIKTOK_SHOP_APP_SECRET",
    "TIKTOK_SHOP_ACCESS_TOKEN",
    "TIKTOK_SHOP_SHOP_CIPHER",
)


def test_settings_doc_bon_bien_tu_moi_truong(monkeypatch):
    for ten in BON_BIEN:
        monkeypatch.setenv(ten, f"gia-tri-{ten.lower()}")
    s = Settings(_env_file=None)
    for ten in BON_BIEN:
        assert getattr(s, ten.lower()) == f"gia-tri-{ten.lower()}"
    assert tts.REQUIRED_ENV == BON_BIEN


def test_env_example_co_du_bon_bien():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    for ten in BON_BIEN:
        assert f"\n{ten}=\n" in text, f".env.example thiếu {ten}"
    assert "scripts/kiem_tra_tiktok_shop.py" in text


@pytest.mark.parametrize("ten_tep", ["docker-compose.yml", "docker-compose.prod.yml"])
def test_compose_truyen_bon_bien_vao_api(ten_tep):
    compose = yaml.safe_load((ROOT / ten_tep).read_text(encoding="utf-8"))
    env = compose["services"]["api"]["environment"]
    for ten in BON_BIEN:
        assert env.get(ten) == f"${{{ten}:-}}", f"{ten_tep}: api thiếu {ten}"


# ---------------------------------------------------------------------------
# 7. scripts/kiem_tra_tiktok_shop.py
# ---------------------------------------------------------------------------

_SCRIPT = ROOT / "scripts" / "kiem_tra_tiktok_shop.py"
_spec = importlib.util.spec_from_file_location("kiem_tra_tiktok_shop", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
ktt = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = ktt
_spec.loader.exec_module(ktt)


def _settings(**overrides) -> SimpleNamespace:
    values = {
        "tiktok_shop_app_key": APP_KEY,
        "tiktok_shop_app_secret": APP_SECRET,
        "tiktok_shop_access_token": TOKEN,
        "tiktok_shop_shop_cipher": SHOP_CIPHER,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _chay_script(handler, **overrides):
    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return asyncio.run(
        ktt.kiem_tra(
            settings=_settings(**overrides), http=http, hom_nay=date(2026, 9, 17), nhip_s=0
        )
    )


def _handler_script(requests: list[httpx.Request], phut_rong: bool = False):
    phut = _handler_phut([])

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.method == "GET"
        if request.url.path == PATH_LIVE_LIST:
            if request.url.params["account_type"] == "MARKETING_ACCOUNTS":
                trang = _fixture("shop_lives_performance_trang_2.json")
                trang["data"].update(live_stream_sessions=[], total_count=0)
                return _json(trang)
            if request.url.params.get("page_token"):
                return _json(_fixture("shop_lives_performance_trang_2.json"))
            return _json(_fixture("shop_lives_performance_trang_1.json"))
        if phut_rong:
            return _json(
                {
                    "code": 0,
                    "message": "Success",
                    "request_id": "rq",
                    "data": {
                        "performance": {"overall": {}, "intervals": []},
                        "next_page_token": "",
                        "total_count": 0,
                    },
                }
            )
        return phut(request)

    return handler


def test_script_thieu_bien_thi_chan_va_khong_goi_mang(capsys):
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
        raise AssertionError("không được gọi TikTok khi thiếu biến")

    kq = _chay_script(handler, tiktok_shop_access_token="")
    out = capsys.readouterr().out
    assert kq.dung_duoc is False
    assert any("TIKTOK_SHOP_ACCESS_TOKEN" in dong for dong in kq.chan)
    assert APP_SECRET not in out
    assert SHOP_CIPHER not in out


def test_script_duong_di_day_du_in_so_phien_va_so_phut_khong_in_bi_mat(capsys):
    requests: list[httpx.Request] = []
    kq = _chay_script(_handler_script(requests))
    out = capsys.readouterr().out
    assert kq.dung_duoc is True, kq.chan
    assert kq.ket_luan == "DÙNG ĐƯỢC"
    assert kq.ma_thoat == 0
    assert kq.so_phien == 3
    assert kq.so_phut_phien_moi_nhat == 5
    danh_sach = [r for r in requests if r.url.path == PATH_LIVE_LIST]
    assert {r.url.params["account_type"] for r in danh_sach} == {
        "OFFICIAL_ACCOUNTS",
        "MARKETING_ACCOUNTS",
    }
    assert all(r.url.params["start_date_ge"] == "2026-09-11" for r in danh_sach)
    assert all(r.url.params["end_date_lt"] == "2026-09-18" for r in danh_sach)
    assert sum(r.url.path == PATH_PHUT for r in requests) == 3
    assert all(r.url.params["sign"] == _ky_doc_lap(r) for r in requests)
    assert "Tổng số phiên        : 3" in out
    assert "Số phút dữ liệu      : 5" in out
    for bi_mat in (TOKEN, APP_SECRET, SHOP_CIPHER, APP_KEY):
        assert bi_mat not in out
    # Không in tiêu đề phiên, tên tài khoản hay tên sản phẩm.
    assert "Phiên thử (dữ liệu giả)" not in out
    assert "tai_khoan_shop_gia" not in out


def _handler_khong_co_phien(request: httpx.Request) -> httpx.Response:
    assert request.url.path == PATH_LIVE_LIST, "không có phiên thì không được gọi theo phút"
    trang = _fixture("shop_lives_performance_trang_2.json")
    trang["data"].update(live_stream_sessions=[], total_count=0)
    return _json(trang)


def test_script_khong_co_phien_la_chua_kiem_duoc_theo_phut_khong_phai_dung_duoc():
    kq = _chay_script(_handler_khong_co_phien)
    assert kq.chan == []
    assert kq.so_phien == 0
    assert kq.so_phut_phien_moi_nhat is None
    assert kq.dung_duoc is False
    assert kq.ket_luan == "CHƯA KIỂM ĐƯỢC THEO PHÚT"
    assert kq.ma_thoat == ktt.MA_THOAT_CHUA_KIEM_THEO_PHUT == 2
    assert any("Không có phiên LIVE" in c for c in kq.canh_bao)
    assert "CHƯA được chứng minh" in kq.giai_thich_ket_luan()


def test_script_phien_chua_co_so_lieu_theo_phut_la_chua_kiem_duoc():
    kq = _chay_script(_handler_script([], phut_rong=True))
    assert kq.so_phut_phien_moi_nhat == 0
    assert kq.dung_duoc is False
    assert kq.ket_luan == "CHƯA KIỂM ĐƯỢC THEO PHÚT"
    assert kq.ma_thoat == 2
    assert any("chưa có dữ liệu theo phút" in c for c in kq.canh_bao)
    assert "0 phút" in kq.giai_thich_ket_luan()


@pytest.mark.parametrize(
    ("kq", "ma", "nhan"),
    [
        (ktt.KetQua(so_phien=0), 2, "CHƯA KIỂM ĐƯỢC THEO PHÚT"),
        (ktt.KetQua(so_phien=1, so_phut_phien_moi_nhat=0), 2, "CHƯA KIỂM ĐƯỢC THEO PHÚT"),
        (ktt.KetQua(so_phien=1, so_phut_phien_moi_nhat=30), 0, "DÙNG ĐƯỢC"),
        (ktt.KetQua(chan=["x → y"], so_phut_phien_moi_nhat=30), 1, "CHƯA DÙNG ĐƯỢC"),
    ],
)
def test_script_main_ma_thoat_theo_ba_trang_thai(monkeypatch, capsys, kq, ma, nhan):
    async def gia_kiem_tra(**_kwargs):
        return kq

    monkeypatch.setattr(ktt, "kiem_tra", gia_kiem_tra)
    assert ktt.main([]) == ma
    out = capsys.readouterr().out
    assert f"KẾT LUẬN: {nhan} (mã thoát {ma})" in out
    if ma != 0:
        assert "KẾT LUẬN: DÙNG ĐƯỢC" not in out


def test_script_thieu_quyen_thi_chan_kem_cach_sua():
    kq = _chay_script(lambda request: _loi(105005, "Access denied."))
    assert kq.dung_duoc is False
    assert any("TikTok Shop Analytics" in dong for dong in kq.chan)
    assert any("Cách sửa" in dong or "→" in dong for dong in kq.chan)


def test_script_main_tra_ma_thoat_1_khi_thieu_bien(monkeypatch, capsys):
    monkeypatch.setattr(ktt, "get_settings", lambda: _settings(tiktok_shop_app_key=""))
    assert ktt.main([]) == 1
    out = capsys.readouterr().out
    assert "CHƯA DÙNG ĐƯỢC" in out
    assert "TIKTOK_SHOP_APP_KEY" in out
