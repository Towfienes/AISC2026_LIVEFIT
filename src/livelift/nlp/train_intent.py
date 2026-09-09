"""Train the Vietnamese comment-intent classifier and benchmark it honestly.

    python -m livelift.nlp.train_intent            # train + evaluate + save
    python -m livelift.nlp.train_intent --no-save  # evaluate only

WHAT THE TRAINING DATA IS — said plainly, because the question matters:

- ``data/intent_dataset.jsonl`` is an AUTHORED dataset (~360 comments, 6
  classes, mixed diacritics/teencode/typos) written to mirror real Vietnamese
  shopping-live chat. It is a bootstrap set, not scraped production data.
- This is the correct scale for this component, not a shortcut. The intent
  radar is a UI aid and an exploratory covariate — it is NOT part of the
  causal estimate, so it does not need (and could not honestly claim) SOTA
  benchmark numbers. What it needs is: measurably better than the keyword
  baseline, calibrated expectations, and a clean upgrade path.
- The upgrade path is pre-planned: every real Live Lab comment lands in the DB
  already scrubbed; the team labels a few hundred per week (active learning:
  label the ones this model is least sure about first), re-runs this script,
  and the benchmark below re-computes on real data. When 2-3k real labels
  exist, fine-tune ViSoBERT (EMNLP 2023) and compare against THIS model as
  the ablation. Wherever the numbers appear they carry their provenance.

MODEL: TF-IDF over character 2-5-grams (robust to missing diacritics and
teencode, no tokenizer needed) + word 1-2-grams, into a linear classifier.
CPU inference is sub-millisecond; the API loads the saved pipeline lazily and
falls back to the keyword baseline when the artifact or sklearn is absent.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from livelift.console import configure as _configure_console
from livelift.nlp.intent import classify_keywords
from livelift.nlp.labels import INTENT_LABELS, TRAINED_LABELS

DATA = Path(__file__).parent / "data" / "intent_dataset.jsonl"
MODEL_PATH = Path(__file__).parent / "model" / "intent_clf.joblib"
# Sidecar metadata: which sklearn produced the artifact. intent.py compares
# it against the running sklearn and warns loudly on mismatch (joblib
# pipelines are not guaranteed portable across sklearn versions).
META_PATH = MODEL_PATH.with_suffix(".meta.json")
LABELS = list(TRAINED_LABELS)  # nguồn duy nhất: livelift.nlp.labels
SEED = 2026


def labels_present(labels: list[str]) -> list[str]:
    """Các lớp THỰC SỰ có mẫu trong dataset, theo thứ tự chuẩn của bộ nhãn.

    macro-F1 phải tính trên những lớp có dữ liệu: kéo vào một lớp 0 mẫu sẽ cộng
    thêm một số 0 và bóp méo con số công bố. Hôm nay dataset chỉ có
    ``TRAINED_LABELS`` nên kết quả trùng khít với trước; khi nhãn thật của các
    lớp mới về (docs/benchmarks/live-fire-achan.md) script tự mở rộng theo.
    """
    have = set(labels)
    return [lb for lb in INTENT_LABELS if lb in have]


def load_dataset() -> tuple[list[str], list[str]]:
    texts, labels = [], []
    with open(DATA, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            texts.append(row["text"])
            labels.append(row["label"])
    return texts, labels


def build_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline

    return Pipeline(
        [
            (
                "features",
                FeatureUnion(
                    [
                        # char n-grams survive teencode + dropped diacritics
                        (
                            "char",
                            TfidfVectorizer(
                                analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True
                            ),
                        ),
                        (
                            "word",
                            TfidfVectorizer(
                                analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True
                            ),
                        ),
                    ]
                ),
            ),
            (
                "clf",
                LogisticRegression(
                    max_iter=2000, C=4.0, class_weight="balanced", random_state=SEED
                ),
            ),
        ]
    )


def evaluate(
    y_true: list[str], y_pred: list[str], name: str, labels: list[str] | None = None
) -> dict:
    from sklearn.metrics import classification_report, f1_score

    labels = labels or LABELS
    macro = f1_score(y_true, y_pred, average="macro", labels=labels, zero_division=0)
    acc = sum(a == b for a, b in zip(y_true, y_pred, strict=True)) / len(y_true)
    report = classification_report(y_true, y_pred, labels=labels, zero_division=0, output_dict=True)
    per_class = {lb: round(report[lb]["f1-score"], 3) for lb in labels}
    return {
        "name": name,
        "macro_f1": round(macro, 3),
        "accuracy": round(acc, 3),
        "per_class_f1": per_class,
    }


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--test-size", type=float, default=0.3)
    args = parser.parse_args(argv)

    from sklearn.model_selection import cross_val_predict, train_test_split

    texts, labels = load_dataset()
    present = labels_present(labels)
    print(f"dataset: {len(texts)} mẫu — {dict(Counter(labels))}")
    print(f"lớp có dữ liệu: {present}")
    missing = [lb for lb in INTENT_LABELS if lb not in present]
    if missing:
        print(f"lớp trong guideline nhưng CHƯA có nhãn thật: {missing} — model không dự đoán được")

    x_tr, x_te, y_tr, y_te = train_test_split(
        texts, labels, test_size=args.test_size, stratify=labels, random_state=SEED
    )

    pipe = build_pipeline()
    pipe.fit(x_tr, y_tr)
    ml_holdout = evaluate(y_te, list(pipe.predict(x_te)), "TF-IDF+LogReg (holdout 30%)", present)

    # 5-fold CV on the full set — steadier than one split at this size
    cv_pred = cross_val_predict(build_pipeline(), texts, labels, cv=5)
    ml_cv = evaluate(labels, list(cv_pred), "TF-IDF+LogReg (5-fold CV)", present)

    kw = evaluate(labels, [classify_keywords(t) for t in texts], "keyword baseline", present)

    for r in (kw, ml_holdout, ml_cv):
        print(f"\n== {r['name']} ==")
        print(f"   macro-F1 {r['macro_f1']:.3f} | accuracy {r['accuracy']:.3f}")
        for lb, f1 in r["per_class_f1"].items():
            print(f"   {lb:<12} F1 {f1:.3f}")

    if not args.no_save:
        # retrain on ALL data before shipping (holdout was for honest eval)
        final = build_pipeline()
        final.fit(texts, labels)
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        import joblib
        import sklearn

        joblib.dump(final, MODEL_PATH, compress=9)
        meta = {
            "sklearn_version": sklearn.__version__,
            "trained_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "n_samples": len(texts),
            # đúng những lớp artifact dự đoán được, không phải cả bộ guideline
            "labels": present,
            "seed": SEED,
        }
        META_PATH.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        size_kb = MODEL_PATH.stat().st_size / 1024
        print(f"\nmodel saved: {MODEL_PATH.name} ({size_kb:.0f} KB)")
        print(f"metadata saved: {META_PATH.name} (sklearn {meta['sklearn_version']})")

    print("\nGhi các con số này vào docs/benchmarks/intent-classifier.md kèm nguồn gốc dữ liệu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
