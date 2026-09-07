"""Vietnamese NLP for livestream comments.

Currently a keyword baseline (:mod:`livelift.nlp.intent`); the ViSoBERT
fine-tune replaces it later behind the same ``classify`` signature
(docs/research/2026-08-24-vietnamese-nlp.md).
"""

from livelift.nlp.intent import (
    INTENT_LABELS,
    classify,
    classify_with_confidence,
    strip_diacritics,
)

__all__ = ["INTENT_LABELS", "classify", "classify_with_confidence", "strip_diacritics"]
