"""Intent classifier: trained model vs keyword baseline, and safe fallback."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from livelift.nlp import intent as intent_mod
from livelift.nlp.intent import (
    classifier_info,
    classify,
    classify_keywords,
    classify_with_confidence,
)

DATA = Path(intent_mod.__file__).parent / "data" / "intent_dataset.jsonl"


def _dataset():
    rows = [json.loads(x) for x in DATA.read_text(encoding="utf-8").splitlines() if x.strip()]
    return [r["text"] for r in rows], [r["label"] for r in rows]


def test_model_artifact_ships_and_loads():
    info = classifier_info()
    assert info["backend"] == "tfidf_logreg", (
        "artifact intent_clf.joblib phải được đóng gói cùng repo — "
        "chạy: python -m livelift.nlp.train_intent"
    )


def test_trained_model_beats_keyword_baseline_by_a_margin():
    """The whole point of training: measurably better than the ablation.

    Gate at +0.10 macro-F1 so a silently-degraded artifact (stale, wrong
    classes) fails loudly. Numbers documented in docs/benchmarks/.
    """
    pytest.importorskip("sklearn")
    from sklearn.metrics import f1_score

    texts, labels = _dataset()
    ml = [classify(t) for t in texts]
    kw = [classify_keywords(t) for t in texts]
    f1_ml = f1_score(labels, ml, average="macro")
    f1_kw = f1_score(labels, kw, average="macro")
    assert f1_ml >= f1_kw + 0.10, f"ML {f1_ml:.3f} vs keywords {f1_kw:.3f}"


def test_classify_always_returns_a_known_label():
    for text in ("xin chào", "0901234567", "", "🎉🎉🎉", "gia bn v"):
        assert classify(text) in intent_mod.INTENT_LABELS


def test_classify_with_confidence_matches_classify_and_bounds():
    """(label, confidence) must agree with classify(); confidence is the raw
    top-class probability in [0, 1] (or None on the keyword fallback) — it
    feeds the active-learning export ordering (gói F)."""
    for text in ("giá bao nhiêu vậy shop", "chốt 1 đơn", "gg that was insane", ""):
        label, confidence = classify_with_confidence(text)
        assert label == classify(text)
        assert label in intent_mod.INTENT_LABELS
        assert confidence is None or 0.0 <= confidence <= 1.0
    if classifier_info()["backend"] == "tfidf_logreg":
        _, confidence = classify_with_confidence("giá bao nhiêu vậy shop")
        assert confidence is not None, "model đã load thì phải trả confidence"


def test_classify_with_confidence_none_on_keyword_fallback(monkeypatch):
    monkeypatch.setattr(intent_mod, "_model", None)
    monkeypatch.setattr(intent_mod, "_model_tried", True)
    label, confidence = classify_with_confidence("giá bao nhiêu vậy shop")
    assert label == classify_keywords("giá bao nhiêu vậy shop")
    assert confidence is None, "baseline từ khóa không có mô hình xác suất"


def test_fallback_when_model_missing(monkeypatch):
    """A server-only install (no sklearn / no artifact) must degrade to the
    keyword baseline, never crash the ingest path."""
    monkeypatch.setattr(intent_mod, "_model", None)
    monkeypatch.setattr(intent_mod, "_model_tried", True)
    assert classify("giá bao nhiêu vậy shop") == classify_keywords("giá bao nhiêu vậy shop")
    assert classifier_info()["backend"] == "keyword_baseline"


def test_model_meta_records_sklearn_version():
    """The artifact ships with a sidecar recording the training sklearn —
    joblib pipelines are not portable across sklearn versions, so a mismatch
    must be detectable (and detected: see the warning test below)."""
    sklearn = pytest.importorskip("sklearn")
    meta = json.loads(intent_mod._META_PATH.read_text(encoding="utf-8"))
    assert meta["sklearn_version"] == sklearn.__version__, (
        "artifact được huấn luyện với sklearn khác môi trường hiện tại — "
        "chạy lại: python -m livelift.nlp.train_intent"
    )


def test_sklearn_version_mismatch_warns_loudly(monkeypatch, tmp_path, caplog):
    pytest.importorskip("sklearn")
    meta_file = tmp_path / "intent_clf.meta.json"
    meta_file.write_text(json.dumps({"sklearn_version": "0.0.1"}), encoding="utf-8")
    monkeypatch.setattr(intent_mod, "_META_PATH", meta_file)
    import logging

    with caplog.at_level(logging.WARNING, logger=intent_mod.__name__):
        intent_mod._check_artifact_sklearn_version()
    assert any(
        "CẢNH BÁO PHIÊN BẢN" in r.message and "0.0.1" in r.message for r in caplog.records
    ), "lệch phiên bản sklearn phải phát warning to, rõ ràng"


def test_missing_meta_stays_silent_and_never_raises(monkeypatch, tmp_path, caplog):
    monkeypatch.setattr(intent_mod, "_META_PATH", tmp_path / "khong_ton_tai.meta.json")
    import logging

    with caplog.at_level(logging.WARNING, logger=intent_mod.__name__):
        intent_mod._check_artifact_sklearn_version()  # artifact cũ chưa có meta
    assert not caplog.records


def test_teencode_and_no_diacritics_still_classified():
    assert classify("gia bn v shop") == "hoi_gia"
    assert classify("chot 1 don di shop") == "chot_don"
    assert classify("ship cod duoc khong") == "van_chuyen"


def test_out_of_domain_text_mostly_abstains_to_khac():
    """Real-VOD live-fire finding (02/09): English chat was mis-labeled
    che_dat 12% of the time. The confidence floor must route clearly
    non-Vietnamese text to 'khac' most of the time without hurting Vietnamese
    accuracy (checked by the benchmark test above)."""
    english = [
        "gg that was insane",
        "what an opening",
        "rook takes rook",
        "chat is this real",
        "top engine move",
        "blunder??",
        "the price of that pawn grab",
        "queen trade incoming",
        "im calling it now",
        "he sacrificed THE ROOK",
    ]
    khac_share = sum(classify(t) == "khac" for t in english) / len(english)
    assert khac_share >= 0.7, f"chỉ {khac_share:.0%} tiếng Anh về 'khac'"
