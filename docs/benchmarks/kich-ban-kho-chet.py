"""Kịch bản kiểm chứng: kho dữ liệu chết giữa một phiên live đang phát.

    .venv/Scripts/python docs/benchmarks/kich-ban-kho-chet.py      (Windows)
    .venv/bin/python     docs/benchmarks/kich-ban-kho-chet.py      (Linux/macOS)

Kết quả đo thật của kịch bản này nằm ở ``docs/benchmarks/kho-chet-giua-phien.md``.

Không cần PostgreSQL và KHÔNG cần Docker: store thật (``InMemoryStore``) bị bọc
bởi :class:`KhoCoTheChet` — một lớp cho phép "rút dây" giữa chừng và ném đúng
lớp lỗi psycopg ném khi mất kết nối. Mọi thứ còn lại là hàng thật: app FastAPI
thật, :class:`~livelift.ingest.base.ApiSink` thật, bộ thực thi tự động thật, và
lệnh nạp bù ``spool_replay`` thật.

Kịch bản trả lời đúng ba câu hỏi của một phiên 90 phút đang phát khi kho chết:
bình luận có mất không, người vận hành có biết không, và sau khi kho sống lại
thì nạp bù được không mà không nhân đôi dữ liệu.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from livelift.api import autopilot, service
from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.ingest.base import ApiSink, RawComment
from livelift.ingest.spool_replay import replay_file

API_BASE = "http://api.test"
SPOOL_DIR = Path("data/spool/kiem-chung-kho-chet")
SO_BINH_LUAN = 20


class OperationalError(Exception):
    """Cùng tên lớp mà psycopg / sqlite3 ném khi kết nối đứt."""


class KhoCoTheChet:
    """Bọc một store thật; bật ``chet`` là rút dây giữa phiên."""

    def __init__(self, inner):
        self._inner = inner
        self.chet = False

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if not callable(attr):
            return attr

        def goi(*a, **k):
            if self.chet:
                raise OperationalError("server closed the connection unexpectedly")
            return attr(*a, **k)

        return goi


def muc(tieu_de: str) -> None:
    print(f"\n{'=' * 78}\n{tieu_de}\n{'=' * 78}")


def main() -> int:
    logging.basicConfig(level=logging.CRITICAL)  # log của sink in riêng bên dưới
    # Tắt tác vụ nền để mỗi vòng quét đều do kịch bản gọi tay — có vậy mới đo
    # được "vòng quét nào bị chặn", thay vì đợi may rủi.
    os.environ["LIVELIFT_AUTOPILOT"] = "0"
    shutil.rmtree(SPOOL_DIR, ignore_errors=True)

    kho = KhoCoTheChet(InMemoryStore())
    app = create_app(store=kho)

    with TestClient(app) as tc:
        for i in range(3):
            tc.post(
                "/products",
                json={
                    "product_id": f"SP{i}",
                    "name": f"Sản phẩm {i}",
                    "category": "test",
                    "cost": 10_000,
                    "price": 40_000,
                    "stock": 25,
                },
            )
        sid = tc.post(
            "/sessions",
            json={"platform": "youtube", "mode": "auto", "planned_duration_min": 60},
        ).json()["session_id"]
        blocks = tc.post(
            f"/sessions/{sid}/schedule",
            json={"block_min": 5, "washout_min": 0, "jitter_s": 0, "seed": 2026},
        ).json()["blocks"]
        tc.post(f"/sessions/{sid}/start")

        on_blocks = [b for b in blocks if b["assignment"] == "ON" and not b["is_washout"]]
        t0 = datetime.now(UTC)

        async def gui(comments, **kw) -> ApiSink:
            client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url=API_BASE)
            sink = ApiSink(
                api_url=API_BASE,
                session_id=sid,
                client=client,
                token="",
                spool_dir=SPOOL_DIR,
                **kw,
            )
            try:
                for c in comments:
                    await sink.post_comment(c)
                return sink
            finally:
                await client.aclose()

        muc("1. Kho còn sống — bình luận vào thẳng cơ sở dữ liệu")
        asyncio.run(gui([RawComment("youtube", "truoc-1", t0, "áo còn size M không")]))
        print(f"bình luận trong kho: {len(kho.list_comments(sid))}")

        muc("2. RÚT DÂY giữa phiên (docker stop db) — đường ghi sự kiện nói gì?")
        kho.chet = True
        r = tc.post(
            f"/sessions/{sid}/comments",
            json={"platform": "youtube", "ext_id": "thu-tay", "text": "chốt đơn"},
        )
        print(f"POST /sessions/<id>/comments -> HTTP {r.status_code}")
        print(f"Retry-After: {r.headers.get('Retry-After')}")
        print(f"X-LiveLift-Storage: {r.headers.get('X-LiveLift-Storage')}")
        print("detail:")
        print("  " + r.json()["detail"])
        rg = tc.get(f"/sessions/{sid}/comments")
        print(
            f"\nGET /sessions/<id>/comments -> HTTP {rg.status_code} (không treo, không 500 trống)"
        )

        muc(f"3. Bộ thu: {SO_BINH_LUAN} bình luận tới trong lúc kho chết")
        binh_luan = [
            RawComment("youtube", f"chet-{i}", t0 + timedelta(seconds=i), f"chốt đơn {i}")
            for i in range(SO_BINH_LUAN)
        ]

        # (a) cách CŨ: mọi bản ghi đều thử đủ max_tries lần rồi mới spool. Đặt
        #     ngưỡng chế độ spool cao hơn số bản ghi là tắt hẳn cơ chế mới.
        shutil.rmtree(SPOOL_DIR, ignore_errors=True)
        t = time.perf_counter()
        asyncio.run(gui(binh_luan, spool_mode_after=10**6))
        giay_cu = time.perf_counter() - t
        spool_cu = (SPOOL_DIR / f"{sid}.jsonl").read_text(encoding="utf-8").splitlines()

        # (b) cách MỚI (mặc định): 2 POST hỏng liên tiếp -> ghi thẳng vào spool.
        shutil.rmtree(SPOOL_DIR, ignore_errors=True)
        t = time.perf_counter()
        sink_moi = asyncio.run(gui(binh_luan))
        giay_moi = time.perf_counter() - t
        spool_moi = (SPOOL_DIR / f"{sid}.jsonl").read_text(encoding="utf-8").splitlines()

        print(
            f"cách cũ  : {giay_cu:7.3f} giây cho {SO_BINH_LUAN} bình luận, "
            f"spool {len(spool_cu)} bản ghi"
        )
        print(
            f"cách mới : {giay_moi:7.3f} giây cho {SO_BINH_LUAN} bình luận, "
            f"spool {len(spool_moi)} bản ghi"
        )
        print(
            f"nhanh hơn: {giay_cu / max(giay_moi, 1e-9):.1f}×  (mới chỉ tính backoff 0,5s + 1,0s;"
        )
        print("           với timeout kết nối Postgres thật, khoảng cách còn lớn hơn nhiều)")
        print(
            f"sink: spool_mode={sink_moi.spool_mode}  spooled={sink_moi.spooled}  "
            f"dropped={sink_moi.dropped}"
        )
        print(f"last_error: {sink_moi.last_error}")
        mau = json.loads(spool_moi[0])
        print(
            f"dòng spool đầu tiên: kind={mau['kind']} ext_id={mau['payload']['ext_id']} "
            f"text={mau['payload']['text']!r}"
        )

        muc("4. Bộ thực thi tự động trong lúc kho chết")
        autopilot.reset_heartbeats()
        giua_khoi = (on_blocks[0]["start_offset_s"] + on_blocks[0]["end_offset_s"]) / 2
        kho.chet = False
        kho.update_session(sid, {"start_ts": service.now_utc() - timedelta(seconds=giua_khoi)})
        kho.chet = True
        ket_qua = autopilot.step_all(kho)
        su_co = autopilot.storage_outage()
        print(f"step_all() trả về: {ket_qua}  (không ghim gì — đúng)")
        print(
            f"storage_outage(): active={su_co.active} error={su_co.error} "
            f"sweeps_blocked={su_co.sweeps_blocked}"
        )
        kho.chet = False
        print(f"exposure_event đã ghi: {len(kho.list_exposure_events(sid))}")

        muc("5. Người vận hành nhìn thấy gì trên bàn điều khiển?")
        st = tc.get(f"/sessions/{sid}/state", params={"role": "operator"})
        auto = st.json()["autopilot"]
        print(f"GET /sessions/<id>/state?role=operator -> HTTP {st.status_code}")
        print(f"autopilot.last_error: {auto['last_error']}")
        print("autopilot.alarm:")
        print("  " + (auto["alarm"] or "(không có)"))

        muc("6. Kho sống lại — nạp bù bằng spool_replay")
        spool_file = SPOOL_DIR / f"{sid}.jsonl"
        print(f"bình luận trong kho TRƯỚC khi nạp bù: {len(kho.list_comments(sid))}")

        async def nap_bu():
            client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app))
            try:
                return await replay_file(spool_file, API_BASE, client=client)
            finally:
                await client.aclose()

        n_ok, n_fail = asyncio.run(nap_bu())
        print(
            f"lần 1: thành công={n_ok} thất bại={n_fail} -> "
            f"bình luận trong kho: {len(kho.list_comments(sid))}"
        )
        n_ok2, n_fail2 = asyncio.run(nap_bu())
        print(
            f"lần 2: thành công={n_ok2} thất bại={n_fail2} -> "
            f"bình luận trong kho: {len(kho.list_comments(sid))} (không nhân đôi)"
        )

        muc("7. Bộ thực thi chạy lại, nhưng sự cố KHÔNG bị xóa khỏi báo cáo")
        giua_khoi_2 = (on_blocks[1]["start_offset_s"] + on_blocks[1]["end_offset_s"]) / 2
        kho.update_session(sid, {"start_ts": service.now_utc() - timedelta(seconds=giua_khoi_2)})
        lines = autopilot.step_all(kho)
        print(f"step_all() sau khi kho sống: {len(lines)} hành động")
        for line in lines:
            print("  " + line)
        print("storage_alarm() vẫn khai báo sự cố:")
        print("  " + (autopilot.storage_alarm() or "(không có)"))

    shutil.rmtree(SPOOL_DIR, ignore_errors=True)  # dọn spool của kịch bản
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
