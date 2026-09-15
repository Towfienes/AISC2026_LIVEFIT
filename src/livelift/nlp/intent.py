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

The keyword baseline and the DEFAULT artifact emit only
:data:`~livelift.nlp.labels.TRAINED_LABELS` (the six pre-registered classes).

Since 14/09/2026 there is a second artifact, ``intent_clf_v2.joblib``, trained on
2,513 rows (393 human-labelled real comments + 320 re-labelled authored rows +
1,800 LLM-labelled real comments) that DOES produce all eleven annotation
classes. It is selected with ``LIVELIFT_INTENT_MODEL=v2`` and is deliberately
not the default yet — promoting it changes ``TRAINED_LABELS`` from 6 to 11,
which several gates still encode. Honest measurement on real chat
(leave-one-session-out over three live sessions): macro-F1 0.211 -> 0.565,
accuracy 0.338 -> 0.741, action-label precision 23.0% -> 66.7%. Method,
ablation and remaining limitations:
docs/competition/sang-tao-tre-2026/03-NLP-NANG-CAP.md.
"""

from __future__ import annotations

import re
import unicodedata

from livelift.nlp.labels import INTENT_LABELS, TRAINED_LABELS

__all__ = [
    "INTENT_LABELS",
    "TRAINED_LABELS",
    "classifier_info",
    "classify",
    "classify_keywords",
    "classify_with_confidence",
    "strip_diacritics",
]


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

INTENT_MODEL_ENV = "LIVELIFT_INTENT_MODEL"
"""Chọn artifact khi khởi động: ``v1`` (mặc định) hay ``v2``.

``v1`` — ``intent_clf.joblib``, 6 lớp, huấn luyện trên 320 câu tự biên soạn. Đây là
**baseline tiền đăng ký**: mọi con số cũ đo trên nó, nên nó vẫn là mặc định và
không bao giờ bị ghi đè.

``v2`` — ``intent_clf_v2.joblib``, **11 lớp**, huấn luyện trên 2.513 mẫu (393 nhãn
người gán + 320 câu biên soạn đã gán lại + 1.800 nhãn LLM trên bình luận thật).
Đo bằng leave-one-session-out trên chat thật: macro-F1 **0,211 → 0,565**, accuracy
**0,338 → 0,741**, precision nhãn hành động **23,0% → 66,7%**
(``docs/competition/sang-tao-tre-2026/03-NLP-NANG-CAP.md``).

Vì sao là **cờ bật tay** chứ không phải mặc định: đổi mặc định kéo theo đổi
``TRAINED_LABELS`` (6 → 11) và mọi cổng đang khoá con số cũ theo bộ 6 lớp. Đó là
một lần thăng cấp có chủ ý, làm trong một thay đổi riêng, không phải tác dụng phụ
của việc thêm một artifact. Quy trình thăng cấp đầy đủ ghi ở §11 của tài liệu trên.
"""

_VARIANT = __import__("os").getenv(INTENT_MODEL_ENV, "v1").strip().lower()
_MODEL_FILENAME = "intent_clf_v2.joblib" if _VARIANT == "v2" else "intent_clf.joblib"
_MODEL_PATH = __import__("pathlib").Path(__file__).parent / "model" / _MODEL_FILENAME
_META_PATH = _MODEL_PATH.with_suffix(".meta.json")
_model = None
_model_tried = False


def _check_artifact_sklearn_version() -> None:
    """Warn LOUDLY when the artifact was trained with a different sklearn.

    joblib pipelines are not guaranteed portable across sklearn versions —
    a silently mis-deserialized model is worse than the keyword baseline.
    The check itself never raises (missing meta file = older artifact, skip);
    the soft fallback in :func:`classify` stays in place either way.
    """
    try:
        import json

        import sklearn

        meta = json.loads(_META_PATH.read_text(encoding="utf-8"))
        trained = meta.get("sklearn_version")
        if trained and trained != sklearn.__version__:
            import logging

            logging.getLogger(__name__).warning(
                "CẢNH BÁO PHIÊN BẢN: artifact %s được huấn luyện với scikit-learn %s "
                "nhưng môi trường đang chạy scikit-learn %s — kết quả dự đoán có thể "
                "sai lệch âm thầm. Hãy huấn luyện lại artifact bằng: "
                "python -m livelift.nlp.train_intent (fallback mềm về keyword baseline "
                "vẫn được giữ nếu model lỗi khi dự đoán).",
                _MODEL_PATH.name,
                trained,
                sklearn.__version__,
            )
    except Exception:  # noqa: BLE001, S110 — the check must never take ingest down
        pass


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
            _check_artifact_sklearn_version()
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
    return classify_with_confidence(text)[0]


def classify_with_confidence(text: str) -> tuple[str, float | None]:
    """Classify one comment and return ``(label, confidence)``.

    ``confidence`` is the trained model's top-class probability BEFORE the
    abstain floor is applied — an abstained ``khac`` still carries the low
    score that caused the abstention, which is exactly the ordering the
    active-learning export wants (label the least-sure comments first, see
    ``python -m livelift.nlp.label_llm export --uncertain-first``). The
    keyword baseline has no probability model, so its confidence is ``None``.
    """
    model = _load_model()
    if model is not None:
        try:
            proba = model.predict_proba([text])[0]
            i = int(proba.argmax())
            label = str(model.classes_[i])
            confidence = float(proba[i])
            # Confidence floor, calibrated on the 02/09 real-VOD live-fire: an
            # English chess-stream chat pushed 12% of messages into che_dat —
            # the model is Vietnamese-specific and must say "khac" instead of
            # guessing on out-of-domain text. At 0.45 the Vietnamese dataset
            # loses nothing (in-sample acc 1.000) while English text routed to
            # khac rises 62% -> 81%.
            if confidence >= MIN_CONFIDENCE and label in INTENT_LABELS:
                return label, confidence
            return "khac", confidence
        except Exception:  # noqa: BLE001, S110 — any failure -> keyword baseline
            _log_once_model_failure()
    return classify_keywords(text), None
