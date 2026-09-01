"""Intent classifier: trained model vs keyword baseline, and safe fallback."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from livelift.nlp import intent as intent_mod
from livelift.nlp.intent import classifier_info, classify, classify_keywords

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


def test_fallback_when_model_missing(monkeypatch):
    """A server-only install (no sklearn / no artifact) must degrade to the
    keyword baseline, never crash the ingest path."""
    monkeypatch.setattr(intent_mod, "_model", None)
    monkeypatch.setattr(intent_mod, "_model_tried", True)
    assert classify("giá bao nhiêu vậy shop") == classify_keywords("giá bao nhiêu vậy shop")
    assert classifier_info()["backend"] == "keyword_baseline"


def test_teencode_and_no_diacritics_still_classified():
    assert classify("gia bn v shop") == "hoi_gia"
    assert classify("chot 1 don di shop") == "chot_don"
    assert classify("ship cod duoc khong") == "van_chuyen"
