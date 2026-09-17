"""Kho dữ liệu dưới truy cập ĐA LUỒNG — hồi quy cho kiểm toán 17/09/2026.

FastAPI chạy mọi route ``def`` đồng bộ trong threadpool, nên kho bị gọi từ
nhiều luồng cùng lúc. Hai hậu quả đã đo được trước khi sửa:

1. ``InMemoryStore`` từng tự nhận "mỗi phương thức là nguyên tử, không cần
   khoá". Phép thử 8 luồng cùng giao MỘT bình luận (cùng platform, ext_id)
   lưu ra bản TRÙNG ở 12/300 lượt — hợp đồng chống trùng mà spool của bộ thu
   dựa vào không đứng vững đúng lúc tải cao.
2. ``Broadcaster.publish`` gọi ``asyncio.Queue.put_nowait`` từ luồng phụ: tương
   lai đang chờ của WebSocket được giải quyết NGOÀI event loop, loop không bị
   đánh thức, và bàn điều khiển chỉ nhận tin khi có I/O khác tình cờ đánh thức.
"""

from __future__ import annotations

import asyncio
import sys
import threading
import uuid
from datetime import UTC, datetime

import pytest

from livelift.api.store import Broadcaster, InMemoryStore


@pytest.fixture
def chuyen_luong_day_dac():
    cu = sys.getswitchinterval()
    sys.setswitchinterval(1e-6)
    try:
        yield
    finally:
        sys.setswitchinterval(cu)


def _binh_luan(ext_id: str) -> dict:
    return {
        "comment_id": str(uuid.uuid4()),
        "platform": "youtube",
        "ext_id": ext_id,
        "ts": datetime.now(UTC),
        "text_scrubbed": "chốt đơn",
    }


def test_giao_trung_dong_thoi_chi_luu_mot_ban(chuyen_luong_day_dac):
    so_luong, so_luot = 8, 150
    for _ in range(so_luot):
        kho = InMemoryStore()
        sid = str(uuid.uuid4())
        rao = threading.Barrier(so_luong)
        ket_qua: list[str] = []

        def giao(kho=kho, sid=sid, rao=rao, ket_qua=ket_qua):
            rao.wait()
            ket_qua.append(kho.add_comment(sid, _binh_luan("cung-mot-id"))["comment_id"])

        luong = [threading.Thread(target=giao) for _ in range(so_luong)]
        for t in luong:
            t.start()
        for t in luong:
            t.join()
        assert len(kho.list_comments(sid)) == 1
        # Mọi lần giao đều nhận về CÙNG một bản ghi — đúng hợp đồng idempotent.
        assert len(set(ket_qua)) == 1


def test_anh_chup_khong_vo_khi_dang_ghi_dong_thoi(chuyen_luong_day_dac):
    kho = InMemoryStore()
    sid = str(uuid.uuid4())
    dung = threading.Event()
    loi: list[BaseException] = []

    def ghi():
        i = 0
        while not dung.is_set():
            i += 1
            kho.add_comment(sid, _binh_luan(f"id-{threading.get_ident()}-{i}"))

    luong = [threading.Thread(target=ghi) for _ in range(3)]
    for t in luong:
        t.start()
    try:
        for _ in range(200):
            try:
                kho.export_json()
            except BaseException as exc:  # noqa: BLE001 — ghi lại để assert
                loi.append(exc)
    finally:
        dung.set()
        for t in luong:
            t.join()
    assert loi == []


def test_publish_tu_luong_phu_danh_thuc_websocket_ngay():
    """Loop không có việc gì khác để làm: nếu publish không đánh thức loop,
    ``queue.get()`` sẽ nằm chờ tới hết hạn giờ."""

    async def kich_ban() -> dict:
        bc = Broadcaster()
        q = bc.subscribe("phien")
        threading.Timer(0.05, bc.publish, args=("phien", {"type": "comment"})).start()
        return await asyncio.wait_for(q.get(), timeout=1.0)

    assert asyncio.run(kich_ban()) == {"type": "comment"}


def test_publish_trong_loop_van_giao_truc_tiep():
    async def kich_ban() -> dict:
        bc = Broadcaster()
        q = bc.subscribe("phien")
        bc.publish("phien", {"type": "tick"})
        return q.get_nowait()

    assert asyncio.run(kich_ban()) == {"type": "tick"}


def test_huy_dang_ky_roi_publish_khong_loi():
    bc = Broadcaster()
    q = bc.subscribe("phien")
    bc.unsubscribe("phien", q)
    bc.publish("phien", {"type": "tick"})
    assert q.empty()
