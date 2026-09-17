"""Bí mật trong URL không được ra log ``httpx`` — mọi nền tảng.

Hồi quy kiểm toán 17/09/2026. Bộ lọc log đầu tiên nằm trong ``shopee.py`` và chỉ
che ``access_token``/``refresh_token``/``sign``. YouTube Data API đặt khoá vào
tham số ``key=`` (``youtube.py``), nên runner CLI (mức INFO) vẫn in nguyên
``key=AIza...`` ra terminal mỗi lần poll — đúng loại rò mà bộ lọc sinh ra để chặn.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys

import httpx

from livelift.ingest.youtube import YouTubeLiveChatClient

KHOA_GIA = "AIzaSyFAKE_SECRET_KEY_123"


def _dong_httpx(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "httpx"]


def test_khoa_youtube_bi_che_trong_log_httpx(caplog):
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"items": [{"liveStreamingDetails": {"activeLiveChatId": "abc"}}]}
        )

    async def goi() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as hc:
            yt = YouTubeLiveChatClient(api_key=KHOA_GIA, client=hc)
            await yt.get_active_live_chat_id("dQw4w9WgXcQ")

    with caplog.at_level(logging.INFO, logger="httpx"):
        asyncio.run(goi())

    dong = _dong_httpx(caplog)
    assert dong, "httpx phải ghi dòng HTTP Request ở mức INFO (điều kiện của phép thử)"
    assert all(KHOA_GIA not in d for d in dong)
    assert any("key=***" in d for d in dong)
    assert all(KHOA_GIA not in r.getMessage() for r in caplog.records)


def test_bo_loc_che_token_shopee_nhung_khong_dung_page_token(caplog):
    async def goi() -> None:
        transport = httpx.MockTransport(lambda req: httpx.Response(200, json={}))
        async with httpx.AsyncClient(transport=transport) as hc:
            await hc.get(
                "https://partner.shopeemobile.com/api/v2/livestream/get_latest_comment_list",
                params={
                    "access_token": "TOKEN_BI_MAT",
                    "sign": "CHU_KY_BI_MAT",
                    "api_key": "KHOA_BI_MAT",
                    "pageToken": "trang-2",
                },
            )

    with caplog.at_level(logging.INFO, logger="httpx"):
        asyncio.run(goi())
    dong = " ".join(_dong_httpx(caplog))
    for bi_mat in ("TOKEN_BI_MAT", "CHU_KY_BI_MAT", "KHOA_BI_MAT"):
        assert bi_mat not in dong
    assert "pageToken=trang-2" in dong, "tham số không bí mật phải giữ nguyên để còn gỡ lỗi"


def test_chi_nhap_client_youtube_cung_da_cai_bo_loc():
    """Runner chỉ chạy YouTube thì không có lý do gì phải import shopee: bộ lọc
    phải được cài bởi mô-đun chung mà mọi client đều import."""
    ma = (
        "import logging, sys\n"
        "import livelift.ingest.youtube\n"
        "assert 'livelift.ingest.shopee' not in sys.modules\n"
        "print(len(logging.getLogger('httpx').filters))\n"
    )
    kq = subprocess.run(
        [sys.executable, "-c", ma], capture_output=True, text=True, timeout=60, check=False
    )
    assert kq.returncode == 0, kq.stderr
    assert int(kq.stdout.strip().splitlines()[-1]) >= 1
