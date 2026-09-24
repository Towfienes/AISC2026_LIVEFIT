"""Artifact ý định hỏng/lệch phiên bản ⇒ bộ từ khoá, VÀ ``/health`` phải nói thật.

Kiểm toán 25/09/2026 (docker.md P0-1, clean-clone.md §3). ``pyproject.toml`` ghim
``scikit-learn>=1.5,<1.8`` trong khi cả hai artifact được huấn luyện bằng 1.9.0.
Ảnh Docker và CI (Python 3.11) vì thế cài 1.7.2: ``joblib.load`` vẫn thành công
(chỉ kèm ``InconsistentVersionWarning``) nhưng ``predict_proba`` ném
``AttributeError: 'LogisticRegression' object has no attribute 'multi_class'``.
``classify_with_confidence`` nuốt lỗi đó và rơi về bộ từ khoá cho 393/393 bình
luận, trong khi ``classifier_info()`` — và ``/health`` — vẫn khai
``tfidf_logreg`` vì chỉ xét "đã load được hay chưa". Đúng loại tuyên bố không
kiểm chứng mà sổ sự cố 13/09 đã cấm.

Luật từ nay:

* nạp artifact xong phải TỰ KIỂM bằng một lần ``predict_proba`` thật; hỏng là
  chuyển HẲN sang bộ từ khoá và ``classifier_info()`` báo ``keyword_fallback``
  kèm lý do (khoá mới ``intent_fallback_reason`` trên ``/health`` — hợp đồng C-4
  chỉ THÊM khoá);
* dự đoán lỗi giữa chừng cũng chuyển hẳn, không để một luồng nhãn trộn hai bộ
  phân loại mà nhãn nguồn chỉ nói một;
* ``pyproject.toml`` ghim ĐÚNG bản sklearn mà artifact ghi trong ``*.meta.json``
  (``>=1.9,<1.10`` chưa đủ: pip chọn 1.9.1 và test so phiên bản vẫn đỏ —
  clean-clone.md §4).
"""

from __future__ import annotations

import json
import re
import threading
import time
import tomllib
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore
from livelift.nlp import intent as intent_mod

ROOT = Path(__file__).resolve().parents[1]
CAU = "giá bao nhiêu vậy shop"


class MoHinhLechPhienBan:
    """Nạp được nhưng không dự đoán được — đúng dáng lỗi sklearn 1.9.0 → 1.7.2."""

    classes_ = np.array(["hoi_gia", "khac"])

    def predict_proba(self, texts):
        raise AttributeError("'LogisticRegression' object has no attribute 'multi_class'")


class MoHinhHongGiuaChung:
    """Qua được lần tự kiểm lúc nạp, rồi hỏng ở lần dự đoán sau."""

    classes_ = np.array(["hoi_gia", "khac"])

    def __init__(self) -> None:
        self.so_lan = 0

    def predict_proba(self, texts):
        self.so_lan += 1
        if self.so_lan > 1:
            raise ValueError("hỏng giữa chừng")
        return np.array([[0.9, 0.1]] * len(texts))


@pytest.fixture
def artifact_gia(monkeypatch, tmp_path):
    """Trỏ bộ phân loại vào một artifact giả; monkeypatch trả mô hình thật về sau test."""
    joblib = pytest.importorskip("joblib")

    def _dat(noi_dung) -> Path:
        path = tmp_path / "intent_clf.joblib"
        if isinstance(noi_dung, bytes):
            path.write_bytes(noi_dung)
        else:
            joblib.dump(noi_dung, path)
        monkeypatch.setattr(intent_mod, "_MODEL_PATH", path)
        monkeypatch.setattr(intent_mod, "_META_PATH", path.with_suffix(".meta.json"))
        monkeypatch.setattr(intent_mod, "_model", None)
        monkeypatch.setattr(intent_mod, "_model_tried", False)
        monkeypatch.setattr(intent_mod, "_model_fallback_reason", None, raising=False)
        return path

    return _dat


def _health() -> dict:
    """/health sau khi bộ phân loại nạp xong.

    Ứng dụng nạp sẵn mô hình ở luồng phụ lúc khởi động; trong cửa sổ đó /health
    nói ``dang_nap`` (không chờ, vì có hạn giờ) — hỏi lại tới khi có câu trả lời.
    """
    with TestClient(create_app(store=InMemoryStore())) as c:
        han = time.monotonic() + 30
        while True:
            body = c.get("/health").json()
            if body["intent_backend"] != "dang_nap" or time.monotonic() > han:
                return body
            time.sleep(0.05)


@pytest.mark.parametrize(
    "artifact",
    [MoHinhLechPhienBan(), b"day khong phai tep joblib"],
    ids=["nap-duoc-khong-du-doan-duoc", "tep-hong"],
)
def test_artifact_khong_dung_duoc_thi_health_khong_khai_tfidf(artifact_gia, artifact):
    artifact_gia(artifact)

    body = _health()
    assert body["intent_backend"] != "tfidf_logreg", (
        "artifact không dự đoán được mà /health vẫn khai mô hình — tuyên bố không kiểm chứng"
    )
    assert body["intent_backend"] == "keyword_fallback"
    assert body["intent_fallback_reason"], "rơi về từ khoá thì phải nói vì sao"

    label, confidence = intent_mod.classify_with_confidence(CAU)
    assert label == intent_mod.classify_keywords(CAU)
    assert confidence is None, "đường từ khoá không có xác suất"


def test_ly_do_neu_ten_loi_ma_khong_chua_van_ban_binh_luan(artifact_gia):
    artifact_gia(MoHinhLechPhienBan())
    info = intent_mod.classifier_info()
    assert info["backend"] == "keyword_fallback"
    assert info["model_file"] is None
    assert "AttributeError" in info["fallback_reason"]
    assert CAU not in info["fallback_reason"], "quy tắc cứng 1: không log/lộ văn bản bình luận"


def test_du_doan_hong_giua_chung_chuyen_han_sang_tu_khoa(artifact_gia):
    artifact_gia(MoHinhHongGiuaChung())
    assert intent_mod.classifier_info()["backend"] == "tfidf_logreg", "tự kiểm lúc nạp phải qua"

    label, confidence = intent_mod.classify_with_confidence(CAU)
    assert (label, confidence) == (intent_mod.classify_keywords(CAU), None)
    info = intent_mod.classifier_info()
    assert info["backend"] == "keyword_fallback", (
        "sau một lần dự đoán hỏng, nhãn nguồn phải nói đúng bộ đang chạy — không trộn hai bộ"
    )
    assert "ValueError" in info["fallback_reason"]
    # Không quay lại mô hình ở câu sau: luồng nhãn nhất quán với nhãn nguồn.
    assert intent_mod.classify_with_confidence("chốt 1 đơn")[1] is None


class MoHinhNapCham:
    """Tự kiểm lúc nạp mất thời gian — giữ luồng nạp trong khoá đủ lâu để đo."""

    classes_ = np.array(["hoi_gia", "khac"])
    cho: threading.Event | None = None

    def predict_proba(self, texts):
        if MoHinhNapCham.cho is not None:
            MoHinhNapCham.cho.wait(10)
        return np.array([[0.9, 0.1]] * len(texts))


def test_trong_cua_so_nap_health_noi_dang_nap_va_phan_loai_cho_mo_hinh(artifact_gia):
    """Tìm ra khi viết test trên (25/09/2026): ứng dụng nạp sẵn mô hình ở luồng
    phụ, và code cũ bật ``_model_tried`` TRƯỚC khi nạp xong — trong cửa sổ nạp,
    /health khai ``keyword_baseline`` và bình luận tới lúc đó bị gán nhãn bằng
    từ khoá. Nay: /health nói ``dang_nap`` (không chờ), còn đường phân loại chờ
    mô hình nên nhãn luôn từ đúng một bộ."""
    artifact_gia(MoHinhNapCham())
    MoHinhNapCham.cho = threading.Event()
    try:
        nap = threading.Thread(target=intent_mod.classify_with_confidence, args=("khởi động",))
        nap.start()
        # Chờ tới khi luồng nạp THỰC SỰ giữ khoá (kẹt ở lần tự kiểm) — một
        # sleep cố định chập chờn khi máy tải nặng: luồng chưa kịp lấy khoá thì
        # classifier_info() tự nạp và treo 10 s theo mô hình chậm.
        han = time.monotonic() + 10
        while not intent_mod._model_lock.locked():
            assert time.monotonic() < han, "luồng nạp không lấy được khoá"
            time.sleep(0.01)
        assert intent_mod.classifier_info()["backend"] == "dang_nap", (
            "đang nạp mà khai keyword_baseline là nói sai bộ đang chạy"
        )
        ket: list = []
        phan_loai = threading.Thread(
            target=lambda: ket.append(intent_mod.classify_with_confidence(CAU))
        )
        phan_loai.start()
        time.sleep(0.2)
        assert not ket, "bình luận trong cửa sổ nạp không được lặng lẽ đi đường từ khoá"
        MoHinhNapCham.cho.set()
        nap.join(10)
        phan_loai.join(10)
        assert ket, "câu đang chờ phải được phân loại sau khi nạp xong"
        assert ket[0][1] is not None, "sau khi nạp xong, câu đang chờ dùng mô hình"
        assert intent_mod.classifier_info()["backend"] == "tfidf_logreg"
    finally:
        MoHinhNapCham.cho.set()
        MoHinhNapCham.cho = None


def test_khong_co_artifact_van_la_baseline_im_lang(monkeypatch, tmp_path):
    """Cài server-only / không có artifact là cấu hình hợp lệ, không phải sự cố."""
    monkeypatch.setattr(intent_mod, "_MODEL_PATH", tmp_path / "khong_co.joblib")
    monkeypatch.setattr(intent_mod, "_model", None)
    monkeypatch.setattr(intent_mod, "_model_tried", False)
    monkeypatch.setattr(intent_mod, "_model_fallback_reason", None, raising=False)
    info = intent_mod.classifier_info()
    assert info["backend"] == "keyword_baseline"
    assert info.get("fallback_reason") is None


def test_artifact_that_qua_tu_kiem_va_health_giu_khoa_cu():
    """Đối chứng dương trên artifact thật đóng gói cùng repo (môi trường đúng bản)."""
    pytest.importorskip("sklearn")
    body = _health()
    assert body["intent_backend"] == "tfidf_logreg"
    assert "intent_fallback_reason" in body, "khoá mới phải luôn có mặt (C-4: chỉ thêm)"
    assert body["intent_fallback_reason"] is None


def _rang_buoc_sklearn() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ml = data["project"]["optional-dependencies"]["ml"]
    dong = [d for d in ml if re.match(r"scikit-learn\b", d)]
    assert len(dong) == 1, f"phải có đúng một ràng buộc scikit-learn trong extra ml: {ml}"
    return dong[0].replace(" ", "")


@pytest.mark.parametrize("meta", ["intent_clf.meta.json", "intent_clf_v2.meta.json"])
def test_pyproject_ghim_dung_ban_sklearn_cua_artifact(meta):
    """Ảnh Docker và CI cài theo pyproject: ghim lệch là mô hình không bao giờ chạy."""
    path = Path(intent_mod.__file__).parent / "model" / meta
    if not path.exists():
        pytest.skip(f"không có {meta}")
    trained = json.loads(path.read_text(encoding="utf-8"))["sklearn_version"]
    assert _rang_buoc_sklearn() == f"scikit-learn=={trained}", (
        f"pyproject phải ghim đúng scikit-learn=={trained} (bản huấn luyện {meta}); "
        "ràng buộc khoảng để pip chọn bản khác và predict_proba vỡ (kiểm toán 25/09)"
    )
