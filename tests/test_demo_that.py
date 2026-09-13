"""Gói DEMO-THẬT — công tắc dữ liệu mẫu / dữ liệu thật cấp ứng dụng.

Yêu cầu từ cả hai vòng phản biện (ưu tiên #2–3): người dùng phải LUÔN biết
mình đang nhìn dữ liệu mẫu hay dữ liệu thật, và dữ liệu demo KHÔNG BAO GIỜ
lọt vào kết quả thật. Bốn cụm chốt chặn:

* **Đánh dấu từ lúc sinh** — mọi phiên từ ``/demo/seed`` và bộ demo vàng mang
  ``is_demo=true`` ngay khi tạo; ``POST /sessions`` không có đường đặt cờ này
  (không ai dán nhầm nhãn demo lên phiên thật), và cờ bất biến về sau.
* **Gate không trộn** — ``/experiment/summary`` mặc định (env=real) loại demo
  như ``dry_run`` và ĐẾM số phiên bị loại; ``?env=demo`` là bản gộp gương —
  chỉ demo, nhãn MÔ PHỎNG; export lô gán nhãn NLP từ chối phiên demo.
* **Khóa §7 chỉ canh kết quả THẬT** — bản gộp demo và bao-cao của phiên demo
  vẫn phục vụ trong cửa sổ khóa (không có gì thật để nhìn trộm; đây là bảo
  hiểm demo trong chiến dịch), trong khi đường thật vẫn khóa chặt.
* **Bộ phiên demo VÀNG tất định** — seed cố định, đủ CẢ BA trạng thái kết quả
  (DƯƠNG rõ / NULL / CHƯA ĐỦ ĐIỀU KIỆN), hai lần chạy cùng seed ra cùng số.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.routes.demo import seed_demo_vang
from livelift.api.store import InMemoryStore
from tests.conftest import seed_phien_that_mo_phong


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def client(store):
    app = create_app(store=store)
    with TestClient(app) as c:
        yield c


def _with_freeze(client, monkeypatch, path: str, value: str):
    from livelift.config import get_settings

    monkeypatch.setenv("RESULTS_FREEZE_UNTIL", value)
    get_settings.cache_clear()
    try:
        return client.get(path).json()
    finally:
        monkeypatch.delenv("RESULTS_FREEZE_UNTIL", raising=False)
        get_settings.cache_clear()


# ===========================================================================
# Đánh dấu từ lúc sinh
# ===========================================================================


def test_every_seeded_session_is_marked_is_demo_from_creation(client):
    seeded = client.post("/demo/seed", json={"n_sessions": 2, "duration_min": 40}).json()
    rows = {s["session_id"]: s for s in client.get("/sessions").json()}
    for sid in [*seeded["session_ids"], seeded["replay_session_id"]]:
        assert rows[sid]["is_demo"] is True, f"phiên seed {sid} không được đánh dấu is_demo"
        assert rows[sid]["dry_run"] is False, "demo ≠ chạy thử: hai cờ hai nghĩa"


def test_post_sessions_has_no_path_to_set_is_demo(client, store):
    """Dữ liệu mẫu chỉ sinh từ máy sinh demo phía server — client gửi is_demo
    thì bị bỏ qua, và schema công bố cũng không nhận trường này."""
    r = client.post(
        "/sessions",
        json={
            "platform": "youtube",
            "mode": "auto",
            "planned_duration_min": 30,
            "is_demo": True,  # cố tình — phải bị lờ đi
        },
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_demo"] is False

    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    assert "is_demo" not in schemas["SessionCreate"].get("properties", {})
    # ...nhưng payload trả về thì PHẢI công bố cờ để UI vẽ nhãn.
    assert "is_demo" in schemas["SessionOut"]["properties"]


def test_is_demo_is_write_once_in_both_directions(client, store):
    that = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 30}
    ).json()["session_id"]
    demo = client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 40}).json()[
        "session_ids"
    ][0]

    # Cả hai chiều đều nguy hiểm: rửa demo thành thật, hay giấu phiên thật
    # dưới nhãn demo sau khi thấy số liệu.
    store.update_session(that, {"is_demo": True})
    store.update_session(demo, {"is_demo": False})
    assert store.get_session(that)["is_demo"] is False
    assert store.get_session(demo)["is_demo"] is True


# ===========================================================================
# Gate không trộn — hai bể dữ liệu rời nhau, loại thì phải đếm
# ===========================================================================


def test_real_and_demo_pools_never_mix(client, store):
    real_ids = set(seed_phien_that_mo_phong(store, n_sessions=2))
    client.post("/demo/seed", json={"n_sessions": 2, "duration_min": 40})

    real = client.get("/experiment/summary").json()
    assert real["env"] == "real"
    assert real["n_sessions"] == 2
    # 2 phiên demo đã kết thúc + 1 phiên replay demo đang phát = 3 phiên mẫu
    demo_reason = next(r for r in real["sessions_excluded"] if "DEMO" in r)
    assert real["sessions_excluded"][demo_reason] == 3

    demo = client.get("/experiment/summary?env=demo").json()
    assert demo["env"] == "demo"
    assert "MÔ PHỎNG" in demo["label"]
    assert demo["n_sessions"] == 2  # replay demo còn đang phát — chưa kết thúc
    that_reason = next(r for r in demo["sessions_excluded"] if "THẬT" in r)
    assert demo["sessions_excluded"][that_reason] == 2

    # /sessions lọc được theo env và mọi dòng đều mang cờ
    demo_rows = client.get("/sessions?env=demo").json()
    real_rows = client.get("/sessions?env=real").json()
    assert {s["session_id"] for s in real_rows} == real_ids
    assert all(s["is_demo"] for s in demo_rows)
    assert not any(s["is_demo"] for s in real_rows)


def test_seeding_demo_does_not_move_the_real_summary(client, store):
    """Gate UX-FLOW L-B: env=real KHÔNG ĐƯỢC đổi kết quả khi seed demo chạy."""
    seed_phien_that_mo_phong(store, n_sessions=2)
    before = client.get("/experiment/summary").json()
    client.post("/demo/seed", json={"n_sessions": 3, "effect": 5.0, "duration_min": 40})
    after = client.get("/experiment/summary").json()
    for field in ("n_sessions", "n_blocks", "estimate", "ci_low", "ci_high", "p_value"):
        assert after[field] == before[field], f"seed demo làm xê dịch {field} của kết quả thật"


def test_session_payloads_carry_the_demo_flag_for_ui_labels(client):
    seeded = client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 40}).json()
    sid = seeded["session_ids"][0]
    assert client.get(f"/sessions/{sid}").json()["is_demo"] is True
    assert client.get(f"/sessions/{sid}/state").json()["is_demo"] is True
    assert client.get(f"/sessions/{sid}/report").json()["is_demo"] is True
    assert client.get(f"/sessions/{sid}/bao-cao").json()["is_demo"] is True
    # Màn host bị đóng băng ở đúng 4 trường (làm mù L6) — không thêm cờ nào.
    host = client.get(f"/sessions/{seeded['replay_session_id']}/state?role=host").json()
    assert set(host) == {"pinned_product", "price", "stock", "elapsed_s"}


def test_label_export_refuses_demo_sessions(client, store):
    """Bình luận demo là văn mẫu của chính mình — lọt vào lô gán nhãn là tự
    đầu độc bộ huấn luyện (phản biện khoa học: refuse-by-default)."""
    from livelift.nlp.label_llm import LabelPipelineError, collect_from_store

    client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 40})
    real_sid = client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 30}
    ).json()["session_id"]
    client.post(f"/sessions/{real_sid}/comments", json={"text": "chốt 1 đơn nha shop"})

    items = collect_from_store(store)
    assert len(items) == 1, "quét toàn kho phải bỏ qua mọi bình luận demo"

    demo_sid = next(s["session_id"] for s in store.list_sessions() if s.get("is_demo"))
    with pytest.raises(LabelPipelineError, match="DỮ LIỆU MẪU"):
        collect_from_store(store, session_id=demo_sid)


# ===========================================================================
# Khóa §7 chỉ canh kết quả thật
# ===========================================================================


def test_freeze_locks_real_summary_but_not_the_labeled_demo_view(client, store, monkeypatch):
    seed_phien_that_mo_phong(store, n_sessions=2)
    client.post("/demo/seed", json={"n_sessions": 3, "effect": 0.5, "duration_min": 40})

    real = _with_freeze(client, monkeypatch, "/experiment/summary", "2999-01-01")
    assert real["estimable"] is False
    assert real["estimate"] is None
    assert "§7" in real["message"]

    demo = _with_freeze(client, monkeypatch, "/experiment/summary?env=demo", "2999-01-01")
    assert demo["env"] == "demo"
    assert "MÔ PHỎNG" in demo["label"]
    assert demo["estimable"] is True, (
        "bản gộp demo là bảo hiểm trình diễn trong cửa sổ khóa — §7 chỉ canh kết quả thật"
    )
    assert demo["estimate"] is not None


def test_freeze_does_not_lock_a_demo_sessions_bao_cao(client, monkeypatch):
    sid = client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 40}).json()[
        "session_ids"
    ][0]
    body = _with_freeze(client, monkeypatch, f"/sessions/{sid}/bao-cao", "2999-01-01")
    kq = body["ket_qua_thi_nghiem"]
    assert body["is_demo"] is True
    assert kq["khoa"] is False, "phiên demo không có gì thật để nhìn trộm — không khóa"
    # ...phiên THẬT thì vẫn khóa — test ở tests/test_bao_cao.py.


# ===========================================================================
# Chip DEMO/THẬT — trường mode tổng hợp trên /health
# ===========================================================================


def test_health_mode_reflects_what_the_store_holds(client, store):
    empty = client.get("/health").json()
    assert empty["mode"] == "real"
    assert empty["mode_counts"] == {"demo": 0, "real": 0}

    client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 40})
    demo_only = client.get("/health").json()
    assert demo_only["mode"] == "demo"
    assert demo_only["mode_counts"]["demo"] == 2  # 1 phiên kết thúc + 1 replay đang phát
    assert demo_only["mode_counts"]["real"] == 0

    client.post(
        "/sessions", json={"platform": "youtube", "mode": "auto", "planned_duration_min": 30}
    )
    mixed = client.get("/health").json()
    assert mixed["mode"] == "mixed"
    assert mixed["mode_counts"] == {"demo": 2, "real": 1}
    assert mixed["mode_note"], "mode phải kèm câu giải thích tiếng Việt"


# ===========================================================================
# Bộ phiên demo VÀNG — tất định, đủ cả ba trạng thái
# ===========================================================================


def test_demo_vang_covers_all_three_result_states_and_is_marked():
    store = InMemoryStore()
    result = seed_demo_vang(store)

    assert len(result["nhom"]["duong"]) == 3
    assert len(result["nhom"]["null"]) == 2
    assert len(result["nhom"]["thieu"]) == 1
    for sid, kq in result["ket_qua"].items():
        assert store.get_session(sid)["is_demo"] is True
        if kq["nhom"] == "duong":
            assert kq["estimable"]
            assert kq["ci_low"] > 0, "cụm DƯƠNG phải có KTC loại 0"
        elif kq["nhom"] == "null":
            assert kq["estimable"], "cụm NULL vẫn phải ước lượng được"
            assert kq["ci_low"] <= 0 <= kq["ci_high"], "cụm NULL phải có KTC chứa 0"
        else:
            assert not kq["estimable"]
            assert kq["message"], "từ chối kết luận thì phải nói lý do tiếng Việt"


def test_demo_vang_is_deterministic_across_runs():
    """Chạy 2 lần cùng seed ⇒ cùng ước lượng/KTC/p/trạng thái (session_id là
    UUID nên khác nhau — định danh không phải kết quả)."""

    def _fingerprint(result):
        return sorted(
            (
                kq["nhom"],
                kq["title"],
                kq["n_blocks"],
                kq["estimate"],
                kq["ci_low"],
                kq["ci_high"],
                kq["p_value"],
            )
            for kq in result["ket_qua"].values()
        )

    assert _fingerprint(seed_demo_vang(InMemoryStore())) == _fingerprint(
        seed_demo_vang(InMemoryStore())
    )


def test_demo_vang_seeds_into_the_running_api_store(client):
    """Bộ demo vàng phải gieo được qua HTTP vào kho của chính API đang chạy.

    Hồi quy cho sự cố 14/09/2026: bộ vàng chỉ có bản CLI, mà CLI dựng store
    trong tiến trình của nó. Với kho ``memory`` (mặc định khi chưa có
    PostgreSQL) nó gieo vào một kho rời rồi thoát, nên API đang chạy vẫn
    trống — mở buổi demo ra là không có phiên nào. Cổng này buộc phải tồn tại
    một đường HTTP gieo vào đúng kho đang phục vụ.
    """
    truoc = {s["session_id"] for s in client.get("/sessions?env=demo").json()}

    r = client.post("/demo/seed-vang")
    assert r.status_code == 200, r.text
    ket_qua = r.json()["ket_qua"]
    assert len(ket_qua) == 6

    sau = {s["session_id"] for s in client.get("/sessions?env=demo").json()}
    assert set(ket_qua) <= sau - truoc, "phiên vàng phải xuất hiện trong kho của API"

    # Và phải đọc được báo cáo đúng trạng thái qua chính đường người dùng đi.
    for sid, kq in ket_qua.items():
        bao_cao = client.get(f"/sessions/{sid}/bao-cao").json()
        assert bao_cao["ket_qua_thi_nghiem"]["estimable"] is kq["estimable"]


def test_seeding_sample_sessions_twice_gives_distinguishable_titles(client):
    """Bấm "Xem thử ngay" hai lần không được sinh các dòng trùng tên y hệt.

    Hồi quy 14/09/2026: mỗi lần gieo đều đặt cùng một tên cố định theo seed,
    nên sau bốn lần bấm màn kết quả có bốn dòng "Phiên mô phỏng seed=1000".
    Người dùng không biết dòng nào vừa tạo. Mã link đã có nhãn riêng mỗi lần
    gieo từ sự cố 27/08 — tên phiên phải theo cùng lý lẽ đó.
    """
    body = {"n_sessions": 2, "duration_min": 40}
    lan_1 = client.post("/demo/seed", json=body).json()
    lan_2 = client.post("/demo/seed", json=body).json()

    rows = {s["session_id"]: s["title"] for s in client.get("/sessions?env=demo").json()}
    ten_1 = [rows[sid] for sid in lan_1["session_ids"]]
    ten_2 = [rows[sid] for sid in lan_2["session_ids"]]

    assert all(ten_1), "phiên mẫu phải có tên"
    assert len(set(ten_1)) == len(ten_1), "trong cùng một lần gieo, tên phải khác nhau"
    assert not set(ten_1) & set(ten_2), f"hai lần gieo không được trùng tên: {ten_1} vs {ten_2}"


def test_seed_vang_twice_does_not_duplicate_the_golden_set(client):
    """Gieo lại bộ vàng không được sinh bản trùng tên.

    Hồi quy cho lỗi thấy trên ảnh chụp 14/09/2026: gọi endpoint lần hai thì
    màn kết quả hiện 12 dòng mang đúng 6 cái tên, mỗi tên hai lần — giám khảo
    không biết dòng nào là dòng nào. Bấm gieo lại trước buổi demo là thao tác
    bình thường, nên mặc định phải bất biến.
    """
    lan_1 = client.post("/demo/seed-vang").json()
    assert lan_1["da_co_san"] is False

    lan_2 = client.post("/demo/seed-vang").json()
    assert lan_2["da_co_san"] is True
    assert set(lan_2["ket_qua"]) == set(lan_1["ket_qua"]), "phải trả đúng bộ cũ"
    assert lan_2["ghi_chu"], "trả bộ cũ thì phải nói rõ vì sao, bằng tiếng Việt"

    vang = [
        s
        for s in client.get("/sessions?env=demo").json()
        if str(s.get("title") or "").startswith("Demo vàng · ")
    ]
    assert len(vang) == 6, f"kho phải còn đúng 6 phiên vàng, đang có {len(vang)}"

    # Cửa thoát vẫn mở khi người dùng CỐ Ý muốn bộ mới.
    lan_3 = client.post("/demo/seed-vang?gieo_lai=true").json()
    assert lan_3["da_co_san"] is False
    assert not set(lan_3["ket_qua"]) & set(lan_1["ket_qua"])
