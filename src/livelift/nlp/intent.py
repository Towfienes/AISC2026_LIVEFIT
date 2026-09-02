"""Keyword-baseline intent classifier for Vietnamese livestream comments.

This is the PRE-REGISTERED ABLATION BASELINE: a transparent keyword matcher
whose numbers anchor the comparison against the ViSoBERT fine-tune that
replaces it later behind the same ``classify`` signature
(docs/research/2026-08-24-vietnamese-nlp.md). Do not "improve" it silently —
its simplicity is the point.

Matching is case- and diacritics-insensitive: both the comment and the keyword
sets are lowercased and stripped of diacritics before matching, so "GIÁ", "gia"
and "giá" all hit the same keyword. Labels are checked in a fixed priority
order (closing a sale beats asking about it); the first label whose keyword set
matches wins, otherwise ``khac``.

Only scrubbed text should ever reach this function in the ingest path — the
classifier itself never stores or logs its input.
"""

from __future__ import annotations

import re
import unicodedata

INTENT_LABELS = ("hoi_gia", "hoi_size", "che_dat", "chot_don", "van_chuyen", "khac")


def strip_diacritics(text: str) -> str:
    """Lowercase and remove Vietnamese diacritics ("Gò Vấp" -> "go vap")."""
    text = text.lower().replace("đ", "d")  # đ has no combining-mark decomposition
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


# Keyword phrases per label, written with diacritics for readability; they are
# diacritics-stripped at compile time so matching is accent-insensitive on both
# sides. Phrases (not single risky tokens) are used where stripping collides:
# "đắt" (expensive) and "đặt" (to order) both strip to "dat", so ``che_dat``
# only uses phrases like "đắt quá" while ``chot_don`` uses "đặt hàng".
_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "chot_don",
        (
            "chốt",
            "chốt đơn",
            "lấy 1",
            "lấy một",
            "em lấy",
            "order",
            "mua",
            "đặt hàng",
            "đặt mua",
            "cho em 1",
            "cho mình 1",
        ),
    ),
    (
        "hoi_size",
        (
            "size",
            "sz",
            "bao ký",
            "bao nhiêu ký",
            "mấy ký",
            "bao kg",
            "cân nặng",
            "chiều cao",
            "form",
            "mặc vừa",
            "xl",
            "xxl",
        ),
    ),
    (
        "van_chuyen",
        (
            "ship",
            "giao",
            "giao hàng",
            "vận chuyển",
            "phí ship",
            "freeship",
            "cod",
            "bao lâu tới",
            "bao lâu nhận",
            "khi nào nhận",
            "khi nào tới",
        ),
    ),
    (
        "hoi_gia",
        (
            "bao nhiêu",
            "bn",
            "giá",
            "nhiêu tiền",
            "bao tiền",
            "giá nhiêu",
            "nhiu tiền",
        ),
    ),
    (
        "che_dat",
        (
            "đắt quá",
            "đắt thế",
            "đắt vậy",
            "mắc quá",
            "mắc thế",
            "mắc vậy",
            "quá đắt",
            "quá mắc",
            "cao thế",
            "cao vậy",
            "hố quá",
            "chát quá",
        ),
    ),
)


def _compile(phrases: tuple[str, ...]) -> re.Pattern[str]:
    stripped = sorted({strip_diacritics(p) for p in phrases}, key=len, reverse=True)
    alternation = "|".join(re.escape(p) for p in stripped)
    return re.compile(rf"\b(?:{alternation})\b")


_MATCHERS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (label, _compile(phrases)) for label, phrases in _KEYWORDS
)


def classify_keywords(text: str) -> str:
    """The keyword baseline: first matching label in priority order
    (chot_don > hoi_size > van_chuyen > hoi_gia > che_dat), else ``khac``.

    Kept verbatim as the pre-registered ablation baseline — every trained
    model is benchmarked against THIS function.
    """
    normalized = strip_diacritics(text)
    for label, pattern in _MATCHERS:
        if pattern.search(normalized):
            return label
    return "khac"


# ---------------------------------------------------------------------------
# Trained model (TF-IDF char/word n-grams + logistic regression)
# ---------------------------------------------------------------------------

MIN_CONFIDENCE = 0.45
"""Below this the model abstains to "khac" — out-of-domain guard (see classify)."""

_MODEL_PATH = __import__("pathlib").Path(__file__).parent / "model" / "intent_clf.joblib"
_model = None
_model_tried = False


def _load_model():
    """Lazily load the trained pipeline; never raises.

    sklearn/joblib live in the [ml] extra — a server-only install, or a
    missing artifact, must degrade to the keyword baseline instead of taking
    the ingest path down.
    """
    global _model, _model_tried
    if _model_tried:
        return _model
    _model_tried = True
    try:
        import joblib

        if _MODEL_PATH.exists():
            _model = joblib.load(_MODEL_PATH)
    except Exception:  # noqa: BLE001 — any failure means "use the baseline"
        _model = None
    return _model


_model_failure_logged = False


def _log_once_model_failure() -> None:
    """Log the first prediction failure (not every comment) then stay quiet."""
    global _model_failure_logged
    if not _model_failure_logged:
        _model_failure_logged = True
        import logging

        logging.getLogger(__name__).warning(
            "intent model prediction failed — falling back to keyword baseline"
        )


def classifier_info() -> dict:
    """Which classifier is live — surfaced in reports so numbers carry their
    provenance (trained model vs keyword baseline)."""
    model = _load_model()
    return {
        "backend": "tfidf_logreg" if model is not None else "keyword_baseline",
        "model_file": _MODEL_PATH.name if model is not None else None,
    }


def classify(text: str) -> str:
    """Classify one comment into an intent label.

    Uses the trained model when its artifact is available (benchmarked at
    ~0.9 macro-F1 on the authored dataset vs ~0.7 for keywords — see
    docs/benchmarks/intent-classifier.md for the honest caveats), otherwise
    the keyword baseline. Both are diacritics/teencode tolerant.
    """
    model = _load_model()
    if model is not None:
        try:
            proba = model.predict_proba([text])[0]
            i = int(proba.argmax())
            label = str(model.classes_[i])
            # Confidence floor, calibrated on the 02/09 real-VOD live-fire: an
            # English chess-stream chat pushed 12% of messages into che_dat —
            # the model is Vietnamese-specific and must say "khac" instead of
            # guessing on out-of-domain text. At 0.45 the Vietnamese dataset
            # loses nothing (in-sample acc 1.000) while English text routed to
            # khac rises 62% -> 81%.
            if proba[i] >= MIN_CONFIDENCE and label in INTENT_LABELS:
                return label
            return "khac"
        except Exception:  # noqa: BLE001, S110 — any failure -> keyword baseline
            _log_once_model_failure()
    return classify_keywords(text)
