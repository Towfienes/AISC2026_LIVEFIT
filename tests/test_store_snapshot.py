"""Cổng chặn tái diễn sự cố mất dữ liệu 11/09/2026.

Hôm đó tiến trình API khởi động lại lúc 13:05:53 và **13 phiên live thật cùng
17.535 bình luận biến mất vĩnh viễn** (``docs/benchmarks/kiem-chung-van-hanh.md``
mục 0), vì ``store_backend=memory`` giữ mọi thứ trong RAM. Không khôi phục được,
và không một dòng nào trên ``/health`` nói trước rằng rủi ro đó đang bật.

Bộ test này khoá ba thứ, theo đúng thứ tự chúng đã hỏng:

1. **Khôi phục được** — ghi dữ liệu → chụp ảnh → kho MỚI đọc tệp → khớp từng
   bảng, và mốc thời gian trở lại đúng kiểu ``datetime`` (một bản khôi phục
   biến ``ts`` thành chuỗi trông như chạy được rồi nói dối ở mọi phép tính khối).
2. **Ghi nguyên tử** — tệp đích luôn là bản CŨ nguyên vẹn hoặc bản MỚI trọn vẹn,
   không bao giờ là bản cụt; hỏng giữa chừng không để lại tệp tạm làm rác.
3. **Tắt được mà không đổi hành vi** — tắt ảnh chụp thì kho chạy y như cũ,
   không đụng đĩa, và ``/health`` phải NÓI RA rằng đang ở chế độ mất dữ liệu.

Cộng thêm hai cổng cấu trúc, để lỗi tương lai không lọt qua như lỗi cũ đã lọt:
mọi phương thức ghi phải tăng ``_rev`` (không tăng ⇒ thay đổi không bao giờ được
chụp), và mọi bảng dữ liệu của kho phải nằm trong ảnh chụp (thêm bảng mà quên
xuất ⇒ mất âm thầm đúng loại bảng đó).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import (
    MEMORY_NO_SNAPSHOT_WARNING,
    InMemoryStore,
    PostgresStore,
    SnapshotError,
    SnapshotManager,
    attach_snapshot,
    build_store,
    durability_info,
    write_snapshot_atomic,
)
from livelift.config import get_settings

NOW = datetime(2026, 9, 11, 6, 5, 53, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Dựng một kho có dữ liệu ở MỌI bảng
# ---------------------------------------------------------------------------


def _populate(store: InMemoryStore) -> str:
    """Ghi ít nhất một dòng vào mọi bảng và trả về session_id."""
    sid = str(uuid.uuid4())
    store.create_product(
        {
            "product_id": "P1",
            "name": "Bình giữ nhiệt 500ml",
            "category": "gia-dung",
            "cost": 42000,
            "price": 95000,
            "stock": 10,
            "created_at": NOW,
        }
    )
    store.create_shortlink(
        {
            "code": "abc123",
            "product_id": "P1",
            "session_id": sid,
            "target_url": "https://shop.example/p1",
            "created_at": NOW,
        }
    )
    store.create_session(
        {
            "session_id": sid,
            "platform": "youtube",
            "title": "Phiên live tối thứ Sáu",
            "mode": "auto",
            "status": "live",
            "planned_duration_min": 60,
            "host_id": None,
            "created_at": NOW,
        }
    )
    store.update_session(sid, {"start_ts": NOW, "design": {"seed": 4242, "blocks": [0, 1]}})
    store.save_schedule(
        sid,
        [
            {
                "block_index": 0,
                "phase": "early",
                "assignment": "ON",
                "propensity": 0.5,
                "is_washout": False,
                "start_offset_s": 0,
                "end_offset_s": 600,
            },
            {
                "block_index": 1,
                "phase": "mid",
                "assignment": "OFF",
                "propensity": 0.5,
                "is_washout": False,
                "start_offset_s": 600,
                "end_offset_s": 1200,
            },
        ],
    )
    store.materialize_block_times(sid, NOW)
    store.increment_override(store.get_blocks(sid)[0]["block_id"])
    store.add_tick(
        sid,
        {
            "ts_bucket": NOW,
            "viewers": 340.0,
            "comment_rate": 1.5,
            "like_rate": 0.0,
            "click_count": 3,
            "pinned_product_id": "P1",
        },
    )
    store.add_comment(
        sid,
        {
            "comment_id": str(uuid.uuid4()),
            "block_id": None,
            "ts": NOW + timedelta(seconds=5),
            "platform": "youtube",
            "ext_id": "yt-1",
            "text_scrubbed": "chị ơi cái áo này còn size M không ạ [SĐT]",
            "pii_kinds": ["phone"],
            "intent_label": "hoi_size",
            "intent_confidence": 0.62,
            "sentiment": None,
        },
    )
    store.add_reaction(
        sid,
        {
            "reaction_id": str(uuid.uuid4()),
            "ts_utc": NOW + timedelta(seconds=7),
            "kind": "superchat",
            "amount": 50000.0,
            "currency": "₫",
            "platform": "youtube",
            "ext_id": "sc-1",
        },
    )
    store.add_click(
        sid,
        {
            "click_id": str(uuid.uuid4()),
            "block_id": None,
            "ts": NOW + timedelta(seconds=9),
            "product_id": "P1",
            "shortlink_code": "abc123",
            "dedup_hash": "hash-me",
        },
    )
    store.add_intervention(
        sid,
        {
            "action_id": str(uuid.uuid4()),
            "block_id": None,
            "ts": NOW + timedelta(seconds=11),
            "client_ts": None,
            "action_type": "pin",
            "product_id": "P1",
            "source": "model",
            "inner_propensity": 0.33,
            "candidates_json": {"cards": ["P1"]},
            "executed": True,
            "override_reason": None,
            "seconds_since_last_switch": 12.0,
        },
    )
    store.add_assignment_events(
        sid,
        [
            {
                "block_idx": 0,
                "assignment": "ON",
                "block_start_s": 0,
                "block_end_s": 600,
                "design_hash": "hash-a",
                "created_at": NOW,
            }
        ],
    )
    store.add_exposure_event(
        sid,
        {
            "block_idx": 0,
            "event_type": "pin",
            "product_id": "P1",
            "ts_utc": NOW + timedelta(seconds=13),
            "ack_latency_ms": 120,
            "source": "model",
        },
    )
    store.add_order(
        sid,
        {
            "order_id": str(uuid.uuid4()),
            "block_id": None,
            "ts": NOW + timedelta(seconds=15),
            "product_id": "P1",
            "qty": 2,
            "gross": 190000,
            "fees": 9000,
            "net_margin": 97000,
        },
    )
    return sid


def _reread(path: Path) -> InMemoryStore:
    """Kho hoàn toàn mới, dựng lại CHỈ từ tệp — đúng như sau khi restart."""
    fresh = InMemoryStore()
    SnapshotManager(fresh, path, 30).restore()
    return fresh


# ---------------------------------------------------------------------------
# 1. Khôi phục được
# ---------------------------------------------------------------------------


def test_snapshot_round_trip_restores_every_table(tmp_path):
    """Ghi → chụp → kho mới đọc tệp → khớp từng bảng.

    Đây là phép thử mà ngày 11/09 không ai chạy được vì cơ chế chưa tồn tại.
    """
    path = tmp_path / "store.json"
    store = InMemoryStore()
    sid = _populate(store)
    assert SnapshotManager(store, path, 30).dump_now() is True

    back = _reread(path)
    assert back.counts() == store.counts()
    assert back.get_session(sid) == store.get_session(sid)
    assert back.get_product("P1") == store.get_product("P1")
    assert back.get_shortlink("abc123") == store.get_shortlink("abc123")
    assert back.get_blocks(sid) == store.get_blocks(sid)
    assert back.list_ticks(sid) == store.list_ticks(sid)
    assert back.list_comments(sid) == store.list_comments(sid)
    assert back.list_reactions(sid) == store.list_reactions(sid)
    assert back.list_clicks(sid) == store.list_clicks(sid)
    assert back.list_interventions(sid) == store.list_interventions(sid)
    assert back.list_assignment_events(sid) == store.list_assignment_events(sid)
    assert back.list_exposure_events(sid) == store.list_exposure_events(sid)
    assert back.list_orders(sid) == store.list_orders(sid)


def test_restored_timestamps_come_back_as_datetimes(tmp_path):
    """Mốc thời gian phải trở lại đúng KIỂU, không phải chuỗi ISO.

    JSON không có kiểu thời gian. Một bản khôi phục trả về chuỗi sẽ nạp trơn
    tru rồi làm hỏng mọi phép tính phía sau (quy khối theo thời gian, độ phủ
    tick, cửa sổ phân tích) — hỏng theo kiểu im lặng, tệ hơn mất hẳn dữ liệu.
    """
    path = tmp_path / "store.json"
    store = InMemoryStore()
    sid = _populate(store)
    SnapshotManager(store, path, 30).dump_now()

    back = _reread(path)
    assert isinstance(back.get_session(sid)["created_at"], datetime)
    assert isinstance(back.get_session(sid)["start_ts"], datetime)
    assert isinstance(back.list_comments(sid)[0]["ts"], datetime)
    assert isinstance(back.list_ticks(sid)[0]["ts_bucket"], datetime)
    assert isinstance(back.get_blocks(sid)[0]["start_ts"], datetime)
    assert back.list_comments(sid)[0]["ts"].tzinfo is not None, "phải giữ múi giờ UTC"


def test_decimal_amounts_survive_as_decimal(tmp_path):
    """``Decimal`` (tiền từ driver Postgres) không được biến thành float im lặng."""
    path = tmp_path / "store.json"
    store = InMemoryStore()
    sid = _populate(store)
    store.add_order(
        sid,
        {
            "order_id": "tien-le",
            "block_id": None,
            "ts": NOW,
            "product_id": "P1",
            "qty": 1,
            "gross": Decimal("95000.50"),
            "fees": 0,
            "net_margin": None,
        },
    )
    SnapshotManager(store, path, 30).dump_now()
    restored = [o for o in _reread(path).list_orders(sid) if o["order_id"] == "tien-le"][0]
    assert restored["gross"] == Decimal("95000.50")
    assert isinstance(restored["gross"], Decimal)


def test_restored_store_still_dedups_repeated_deliveries(tmp_path):
    """Sau khôi phục, (platform, ext_id) vẫn là khóa chống trùng.

    Chỉ mục chống trùng KHÔNG nằm trong tệp — nó được dựng lại từ chính các
    dòng dữ liệu. Nếu dựng sai thì runner ingest phát lại sau restart sẽ nhân
    đôi toàn bộ bình luận, tức là hỏng số liệu thay vì mất số liệu.
    """
    path = tmp_path / "store.json"
    store = InMemoryStore()
    sid = _populate(store)
    first = store.list_comments(sid)[0]
    SnapshotManager(store, path, 30).dump_now()

    back = _reread(path)
    again = back.add_comment(
        sid,
        {
            "comment_id": str(uuid.uuid4()),
            "block_id": None,
            "ts": NOW + timedelta(minutes=5),
            "platform": "youtube",
            "ext_id": "yt-1",
            "text_scrubbed": "gửi lại sau khi restart",
            "pii_kinds": [],
            "intent_label": None,
            "intent_confidence": None,
            "sentiment": None,
        },
    )
    assert again["comment_id"] == first["comment_id"], "phải trả về dòng CŨ"
    assert len(back.list_comments(sid)) == 1, "không được nhân đôi sau restart"

    dup_reaction = back.add_reaction(
        sid,
        {
            "reaction_id": str(uuid.uuid4()),
            "ts_utc": NOW,
            "kind": "superchat",
            "platform": "youtube",
            "ext_id": "sc-1",
        },
    )
    assert dup_reaction["reaction_id"] == store.list_reactions(sid)[0]["reaction_id"]
    assert len(back.list_reactions(sid)) == 1


def test_snapshot_refuses_an_unknown_format(tmp_path):
    """Định dạng lạ phải bị TỪ CHỐI, không đoán bừa."""
    store = InMemoryStore()
    with pytest.raises(SnapshotError, match="định dạng"):
        store.import_json(json.dumps({"format": 99, "sessions": {}}))


def test_corrupt_snapshot_is_quarantined_and_the_store_starts_empty(tmp_path):
    """Tệp hỏng (mất điện giữa chừng ở phiên bản cũ, đĩa lỗi) không được làm
    chết API, cũng không được bị ghi đè âm thầm — nó là bằng chứng duy nhất."""
    path = tmp_path / "store.json"
    path.write_text('{"format": 1, "sessions": {"a": ', encoding="utf-8")
    store = InMemoryStore()
    manager = SnapshotManager(store, path, 30)

    assert manager.restore() is None
    assert store.list_sessions() == [], "kho rỗng còn hơn kho nửa vời"
    assert not path.exists(), "tệp hỏng phải được chuyển đi"
    spoiled = list(tmp_path.glob("store.json.hong-*"))
    assert len(spoiled) == 1, "bằng chứng phải được giữ lại để mổ xẻ"
    assert spoiled[0].read_text(encoding="utf-8").startswith('{"format": 1')


def test_missing_snapshot_is_a_normal_first_run(tmp_path):
    store = InMemoryStore()
    assert SnapshotManager(store, tmp_path / "chua-co.json", 30).restore() is None
    assert store.counts()["sessions"] == 0


# ---------------------------------------------------------------------------
# 2. Ghi nguyên tử
# ---------------------------------------------------------------------------


def test_atomic_write_leaves_no_temp_file_behind(tmp_path):
    path = tmp_path / "store.json"
    write_snapshot_atomic(path, '{"format": 1}')
    write_snapshot_atomic(path, '{"format": 1, "lan": 2}')
    assert sorted(p.name for p in tmp_path.iterdir()) == ["store.json"]
    assert json.loads(path.read_text(encoding="utf-8"))["lan"] == 2


def test_a_failed_write_keeps_the_previous_snapshot_and_cleans_up(tmp_path, monkeypatch):
    """Hỏng lúc đổi tên: tệp đích vẫn là bản CŨ ĐỌC ĐƯỢC, không tệp tạm nào ở lại.

    Đây là lý do phải ghi tệp tạm rồi ``os.replace`` thay vì ghi đè trực tiếp.
    Ghi đè trực tiếp mà chết giữa chừng sẽ để lại một ảnh chụp cụt — lần khởi
    động sau tưởng có dữ liệu, đọc vào thì hỏng, và bản tốt thì đã bị xoá.
    """
    import livelift.api.store as store_mod

    path = tmp_path / "store.json"
    store = InMemoryStore()
    sid = _populate(store)
    manager = SnapshotManager(store, path, 30)
    manager.dump_now()
    good = path.read_text(encoding="utf-8")

    store.add_comment(
        sid,
        {
            "comment_id": str(uuid.uuid4()),
            "block_id": None,
            "ts": NOW,
            "platform": "youtube",
            "ext_id": "yt-2",
            "text_scrubbed": "bình luận mới sẽ không kịp lưu",
            "pii_kinds": [],
            "intent_label": None,
            "intent_confidence": None,
            "sentiment": None,
        },
    )

    def _boom(src, dst):
        raise OSError("đĩa đầy")

    monkeypatch.setattr(store_mod.os, "replace", _boom)
    with pytest.raises(OSError, match="đĩa đầy"):
        manager.dump_now()

    assert path.read_text(encoding="utf-8") == good, "bản cũ phải còn nguyên vẹn"
    assert json.loads(good)["format"] == 1
    assert sorted(p.name for p in tmp_path.iterdir()) == ["store.json"], "không để lại rác"


def test_a_failed_serialization_writes_nothing_at_all(tmp_path):
    """Kiểu dữ liệu không tuần tự hoá được thì KHÔNG tạo tệp nào cả."""
    path = tmp_path / "store.json"
    store = InMemoryStore()
    sid = _populate(store)
    store.update_session(sid, {"design": {"khong_json": {1, 2, 3}}})
    with pytest.raises(TypeError, match="không tuần tự hoá được"):
        SnapshotManager(store, path, 30).dump_now()
    assert list(tmp_path.iterdir()) == [], "không tệp đích, không tệp tạm"


def test_a_dump_that_fails_inside_the_loop_does_not_kill_the_api(tmp_path, monkeypatch, caplog):
    """Vòng chụp ảnh nuốt lỗi và thử lại — cơ chế an toàn không được tự trở
    thành sự cố. Lỗi vẫn phải xuất hiện trong nhật ký, bằng tiếng Việt."""
    import asyncio

    import livelift.api.store as store_mod

    store = InMemoryStore()
    _populate(store)
    manager = SnapshotManager(store, tmp_path / "store.json", 1)
    monkeypatch.setattr(
        store_mod,
        "write_snapshot_atomic",
        lambda *a, **k: (_ for _ in ()).throw(OSError("đĩa đầy")),
    )

    async def _run():
        manager.interval_s = 0.05
        manager.start()
        await asyncio.sleep(0.25)
        manager.stop()

    with caplog.at_level("ERROR"):
        asyncio.run(_run())
    assert any(
        "Ghi ảnh chụp kho" in r.message or "ảnh chụp cuối" in r.message for r in caplog.records
    )
    assert manager.status()["last_error"] == "đĩa đầy"


def test_the_periodic_loop_writes_only_when_something_changed(tmp_path):
    """Chu kỳ chạy đều nhưng chỉ ghi khi kho ĐỔI — phiên im lặng không được
    làm đĩa quay liên tục, và đường ghi của request không đụng tệp nào."""
    import asyncio

    path = tmp_path / "store.json"
    store = InMemoryStore()
    sid = _populate(store)
    manager = SnapshotManager(store, path, 30)
    # Sàn 1 giây trong hàm dựng là để bảo vệ cấu hình thật; ở đây ta đo chính
    # cái vòng lặp nên đặt thẳng chu kỳ ngắn.
    manager.interval_s = 0.05

    async def _run():
        manager.start()
        await asyncio.sleep(0.3)
        first = path.stat().st_mtime_ns
        await asyncio.sleep(0.3)  # không ghi gì thêm
        idle = path.stat().st_mtime_ns
        store.add_tick(sid, {"ts_bucket": NOW + timedelta(minutes=1), "viewers": 999.0})
        await asyncio.sleep(0.3)
        after = path.stat().st_mtime_ns
        manager.stop()
        return first, idle, after

    first, idle, after = asyncio.run(_run())
    assert idle == first, "kho không đổi ⇒ không ghi lại"
    assert after != first, "kho đổi ⇒ phải ghi"
    assert _reread(path).list_ticks(sid)[-1]["viewers"] == 999.0


def test_an_older_write_can_never_overwrite_a_newer_snapshot(tmp_path):
    """Hai người ghi cùng lúc thì bản CŨ không được đè lên bản MỚI.

    Có đúng hai người ghi: vòng lặp định kỳ (ghi đĩa chạy ở luồng phụ) và cú
    chụp cuối của ``stop()``. Nếu bản cũ tình cờ tới đích sau, tệp sẽ LÙI lại
    và mất đúng những sự kiện mà lúc tắt đang cố cứu — một lỗi mất dữ liệu nằm
    ngay bên trong bản vá chống mất dữ liệu.
    """
    path = tmp_path / "store.json"
    store = InMemoryStore()
    sid = _populate(store)
    manager = SnapshotManager(store, path, 30)

    old_payload = store.export_json()
    old_rev = store._rev
    store.add_tick(sid, {"ts_bucket": NOW + timedelta(minutes=2), "viewers": 777.0})
    new_rev = store._rev
    assert new_rev > old_rev

    assert manager._commit(new_rev, store.export_json(), force=False) is True
    # …và giờ bản cũ (đã tuần tự hoá từ trước) mới tới đích:
    assert manager._commit(old_rev, old_payload, force=False) is False

    back = _reread(path)
    assert [t["viewers"] for t in back.list_ticks(sid)][-1] == 777.0, "tệp không được lùi"


def test_shutdown_takes_a_final_snapshot(tmp_path):
    """Tắt có trật tự thì không mất gì — kể cả sự kiện vừa tới trước lúc tắt."""
    path = tmp_path / "store.json"
    store = InMemoryStore()
    sid = _populate(store)
    manager = SnapshotManager(store, path, 3600)  # chu kỳ dài: chỉ stop() mới ghi
    manager.stop()
    assert _reread(path).counts() == store.counts()
    assert _reread(path).get_session(sid)["title"] == "Phiên live tối thứ Sáu"


# ---------------------------------------------------------------------------
# 3. Tắt được mà không đổi hành vi
# ---------------------------------------------------------------------------


def test_disabling_the_snapshot_changes_nothing_and_touches_no_disk(tmp_path):
    path = tmp_path / "store.json"
    store = InMemoryStore()
    manager = attach_snapshot(store, enabled=False, path=path, interval_s=1)

    assert manager is None
    assert store.snapshot is None
    sid = _populate(store)
    assert store.get_session(sid)["title"] == "Phiên live tối thứ Sáu"
    assert store.counts()["comments"] == 1
    assert list(tmp_path.iterdir()) == [], "tắt là thật sự không đụng đĩa"


def test_disabled_snapshot_health_says_the_data_is_at_risk():
    """Tắt thì được, IM LẶNG thì không: chế độ mất dữ liệu phải tự khai báo."""
    info = durability_info(InMemoryStore())
    assert info["storage_mode"] == "memory"
    assert info["durable"] is False
    assert info["snapshot"] is None
    assert info["storage_warning"] == MEMORY_NO_SNAPSHOT_WARNING
    assert "17.535" in info["storage_warning"], "cảnh báo phải dẫn con số đã mất thật"


def test_attach_snapshot_reports_mode_and_restores(tmp_path):
    path = tmp_path / "store.json"
    first = InMemoryStore()
    sid = _populate(first)
    SnapshotManager(first, path, 30).dump_now()

    second = InMemoryStore()
    manager = attach_snapshot(second, enabled=True, path=path, interval_s=30)
    assert manager is not None
    assert second.get_session(sid)["title"] == "Phiên live tối thứ Sáu"

    info = durability_info(second)
    assert info["storage_mode"] == "memory+snapshot"
    assert info["durable"] is False, "RAM + ảnh chụp vẫn KHÔNG phải bền vững"
    assert info["snapshot"]["restored_at_startup"]["comments"] == 1
    assert "postgres" in info["storage_warning"].lower()
    manager.stop()


def test_build_store_warns_when_a_database_is_configured_but_unused(monkeypatch, caplog):
    """Sự cố 25/08/2026 lặp lại được: đặt `DATABASE_URL` mà quên `STORE_BACKEND`
    thì API chạy RAM trong im lặng. Nay nó phải nói một câu lúc khởi động."""
    monkeypatch.delenv("STORE_BACKEND", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://ai/do/thay:doi@127.0.0.1:5432/livelift")
    get_settings.cache_clear()
    try:
        with caplog.at_level("WARNING"):
            store = build_store()
    finally:
        get_settings.cache_clear()
    assert store.backend == "memory"
    assert any("STORE_BACKEND" in r.message and "RAM" in r.message for r in caplog.records)

    # Chọn memory MỘT CÁCH CÓ Ý (truyền thẳng tham số) thì không được kêu —
    # cảnh báo kêu cả khi người ta đã quyết định rồi là cảnh báo bị bỏ qua.
    caplog.clear()
    get_settings.cache_clear()
    try:
        with caplog.at_level("WARNING"):
            build_store("memory")
    finally:
        get_settings.cache_clear()
    assert not [r for r in caplog.records if "STORE_BACKEND" in r.message]


def test_postgres_never_gets_a_snapshot_file(tmp_path):
    """Postgres đã bền vững; chụp thêm một bản JSON là tạo nguồn sự thật thứ hai."""
    fake = PostgresStore.__new__(PostgresStore)  # không mở kết nối
    assert attach_snapshot(fake, enabled=True, path=tmp_path / "x.json", interval_s=1) is None
    assert list(tmp_path.iterdir()) == []
    assert durability_info(fake) == {
        "storage_mode": "postgres",
        "durable": True,
        "storage_warning": None,
        "snapshot": None,
        "storage_note": durability_info(fake)["storage_note"],
    }
    assert "PostgreSQL" in durability_info(fake)["storage_note"]


# ---------------------------------------------------------------------------
# Cổng cấu trúc: lỗi TƯƠNG LAI cũng không được lọt
# ---------------------------------------------------------------------------


def test_every_mutating_method_bumps_the_revision_counter():
    """Phương thức ghi mà quên tăng ``_rev`` ⇒ thay đổi đó không bao giờ được
    chụp ⇒ mất dữ liệu im lặng. Kiểm từng phương thức, không tin vào mắt."""
    store = InMemoryStore()
    sid = _populate(store)
    block_id = store.get_blocks(sid)[0]["block_id"]

    calls = {
        "create_product": lambda: store.create_product(
            {
                "product_id": "P2",
                "name": "Khăn",
                "category": "x",
                "cost": 1,
                "price": 2,
                "stock": 1,
                "created_at": NOW,
            }
        ),
        "create_shortlink": lambda: store.create_shortlink(
            {
                "code": f"c-{uuid.uuid4()}",
                "product_id": "P1",
                "session_id": sid,
                "target_url": "u",
                "created_at": NOW,
            }
        ),
        "create_session": lambda: store.create_session(
            {
                "session_id": str(uuid.uuid4()),
                "platform": "tiktok",
                "title": "khác",
                "mode": "suggest",
                "status": "planned",
                "planned_duration_min": 15,
                "host_id": None,
                "created_at": NOW,
            }
        ),
        "update_session": lambda: store.update_session(sid, {"status": "ended"}),
        "save_schedule": lambda: store.save_schedule(
            sid,
            [
                {
                    "block_index": 0,
                    "phase": "early",
                    "assignment": "ON",
                    "propensity": 0.5,
                    "is_washout": False,
                    "start_offset_s": 0,
                    "end_offset_s": 60,
                }
            ],
        ),
        "materialize_block_times": lambda: store.materialize_block_times(sid, NOW),
        "increment_override": lambda: store.increment_override(
            store.get_blocks(sid)[0]["block_id"]
        ),
        "add_tick": lambda: store.add_tick(
            sid, {"ts_bucket": NOW + timedelta(minutes=9), "viewers": 1.0}
        ),
        "add_comment": lambda: store.add_comment(
            sid,
            {
                "comment_id": str(uuid.uuid4()),
                "block_id": None,
                "ts": NOW,
                "platform": None,
                "ext_id": None,
                "text_scrubbed": "x",
                "pii_kinds": [],
                "intent_label": None,
                "intent_confidence": None,
                "sentiment": None,
            },
        ),
        "add_reaction": lambda: store.add_reaction(
            sid, {"reaction_id": str(uuid.uuid4()), "ts_utc": NOW, "kind": "like"}
        ),
        "add_click": lambda: store.add_click(
            sid,
            {
                "click_id": str(uuid.uuid4()),
                "block_id": None,
                "ts": NOW,
                "product_id": "P1",
                "shortlink_code": None,
                "dedup_hash": "h",
            },
        ),
        "add_intervention": lambda: store.add_intervention(
            sid,
            {
                "action_id": str(uuid.uuid4()),
                "block_id": None,
                "ts": NOW,
                "action_type": "pin",
                "source": "human",
            },
        ),
        "add_assignment_events": lambda: store.add_assignment_events(
            sid,
            [
                {
                    "block_idx": 0,
                    "assignment": "OFF",
                    "block_start_s": 0,
                    "block_end_s": 60,
                    "design_hash": "hash-b",
                    "created_at": NOW,
                }
            ],
        ),
        "add_exposure_event": lambda: store.add_exposure_event(
            sid, {"event_type": "unpin", "ts_utc": NOW, "source": "human"}
        ),
        "add_order": lambda: store.add_order(
            sid, {"order_id": str(uuid.uuid4()), "ts": NOW, "product_id": "P1"}
        ),
    }
    assert block_id  # lịch đã tồn tại trước khi thử increment_override

    for name, call in calls.items():
        before = store._rev
        call()
        assert store._rev > before, f"{name} đổi trạng thái nhưng KHÔNG tăng _rev"


def test_every_data_table_of_the_store_is_inside_the_snapshot():
    """Thêm bảng dữ liệu mới mà quên xuất ⇒ mất đúng bảng đó, âm thầm.

    Ba chỉ mục chống trùng được miễn vì chúng được DỰNG LẠI từ dữ liệu (và
    test dedup ở trên chứng minh việc dựng lại là đúng; chỉ mục mã đơn có test
    riêng trong tests/test_don_hang.py).
    """
    store = InMemoryStore()
    _populate(store)
    exported = set(json.loads(store.export_json()))
    rebuilt = {"_comment_keys", "_reaction_keys", "_order_index"}

    for name, value in vars(store).items():
        if name in rebuilt or not name.startswith("_") or not isinstance(value, dict):
            continue
        assert name.removeprefix("_") in exported, (
            f"bảng {name} không nằm trong ảnh chụp — khởi động lại sẽ mất sạch bảng này"
        )


# ---------------------------------------------------------------------------
# Đầu-cuối qua chính ứng dụng: /health nói thật, và restart giữ được dữ liệu
# ---------------------------------------------------------------------------


def test_health_warns_loudly_when_the_store_is_only_ram():
    """Sự cố 11/09 vô hình cho tới khi có người đếm tay. Nay ``/health`` nói."""
    with TestClient(create_app(store=InMemoryStore())) as client:
        body = client.get("/health").json()
    assert body["store_backend"] == "memory"
    assert body["storage_mode"] == "memory"
    assert body["durable"] is False
    assert "NGUY HIỂM" in body["storage_warning"]
    assert "11/09/2026" in body["storage_warning"]


def test_an_injected_store_never_writes_snapshot_files(tmp_path, monkeypatch):
    """Test và script tự mang kho của mình thì ứng dụng KHÔNG được ghi đĩa —
    bộ test không có quyền rải tệp vào thư mục dữ liệu của người dùng."""
    monkeypatch.setenv("STORE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("STORE_SNAPSHOT_PATH", str(tmp_path / "khong-duoc-ghi.json"))
    get_settings.cache_clear()
    try:
        with TestClient(create_app(store=InMemoryStore())) as client:
            assert client.get("/health").status_code == 200
    finally:
        get_settings.cache_clear()
    assert list(tmp_path.iterdir()) == []


def test_the_app_restores_its_own_store_across_a_restart(tmp_path, monkeypatch):
    """Cổng đầu-cuối: hai vòng đời ứng dụng liên tiếp, đúng như tắt rồi bật lại.

    Vòng một nạp bình luận qua HTTP rồi tắt (lifespan chụp ảnh lần cuối); vòng
    hai dựng kho MỚI từ cấu hình và phải thấy lại đúng phiên đó. Chạy `livelift`
    ở chế độ memory mà không có cổng này thì lời hứa "khôi phục được" chỉ là lời.
    """
    snapshot = tmp_path / "snapshot" / "store.json"
    monkeypatch.setenv("STORE_BACKEND", "memory")
    monkeypatch.setenv("STORE_SNAPSHOT_ENABLED", "true")
    monkeypatch.setenv("STORE_SNAPSHOT_PATH", str(snapshot))
    monkeypatch.setenv("STORE_SNAPSHOT_INTERVAL_S", "3600")  # chỉ lúc tắt mới ghi
    get_settings.cache_clear()
    try:
        with TestClient(create_app()) as client:
            session = client.post(
                "/sessions",
                json={
                    "platform": "youtube",
                    "title": "Phiên KOL 90 phút",
                    "mode": "suggest",
                    "planned_duration_min": 90,
                },
            ).json()
            sid = session["session_id"]
            for i in range(5):
                r = client.post(
                    f"/sessions/{sid}/comments",
                    json={"text": f"chốt đơn ạ {i}", "platform": "youtube", "ext_id": f"e{i}"},
                )
                assert r.status_code == 200, r.text

        assert snapshot.exists(), "tắt máy phải để lại ảnh chụp"

        with TestClient(create_app()) as client2:
            health = client2.get("/health").json()
            assert health["storage_mode"] == "memory+snapshot"
            assert health["snapshot"]["restored_at_startup"]["sessions"] == 1
            back = client2.get(f"/sessions/{sid}")
            assert back.status_code == 200, "phiên phải sống sót qua restart"
            assert back.json()["title"] == "Phiên KOL 90 phút"
            assert len(client2.get(f"/sessions/{sid}/comments").json()) == 5
    finally:
        get_settings.cache_clear()
