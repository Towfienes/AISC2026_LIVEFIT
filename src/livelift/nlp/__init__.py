"""Vietnamese NLP for livestream comments.

Three layers behind one ``classify`` signature (:mod:`livelift.nlp.intent`):
the keyword baseline (pre-registered ablation), the shipped TF-IDF + logistic
regression artifact, and — opt-in via ``LIVELIFT_INTENT_MODEL=v2`` — the
eleven-class model trained on real labelled chat. Honest evaluation harness:
:mod:`livelift.nlp.eval_intent` (leave-one-session-out over live sessions,
bootstrap CIs, ablation). A ViSoBERT fine-tune remains on the roadmap and is
explicitly NOT promised for the current submission — see
docs/competition/sang-tao-tre-2026/03-NLP-NANG-CAP.md section 9.
"""

from livelift.nlp.intent import (
    INTENT_LABELS,
    classify,
    classify_with_confidence,
    strip_diacritics,
)

__all__ = ["INTENT_LABELS", "classify", "classify_with_confidence", "strip_diacritics"]
