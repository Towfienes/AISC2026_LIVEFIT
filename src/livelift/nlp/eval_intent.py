"""Khung đánh giá TRUNG THỰC cho bộ phân loại ý định — chạy lại bằng MỘT lệnh.

    python -m livelift.nlp.eval_intent                   # baseline + trước/sau
    python -m livelift.nlp.eval_intent --ablation        # + bảng ablation
    python -m livelift.nlp.eval_intent --save-model      # đóng gói model thắng

Đầu ra: ``docs/benchmarks/intent-eval/results.json`` + ``results.md``.

VÌ SAO KHUNG NÀY TỒN TẠI
------------------------
Con số 0,870 của ``train_intent.py`` đo bằng 5-fold CV trên 320 câu **tự biên
soạn** — train và test cùng một người viết, cùng một ngày, cùng một phân phối.
Nó không trả lời được câu hỏi duy nhất đáng hỏi: *trên chat của một buổi live
mà mô hình chưa từng thấy, nó đúng bao nhiêu?* Lô gán nhãn tay 10/09 trả lời:
**0,271**. Khung này biến câu trả lời đó thành một quy trình chạy lại được,
thay vì một con số chép tay trong tài liệu.

BỐN QUYẾT ĐỊNH THIẾT KẾ, VÀ LÝ DO
---------------------------------
1. **Chia theo BUỔI LIVE, không theo dòng.** Bình luận trong một buổi không
   độc lập: cùng người bán, cùng mặt hàng, cùng bảng giá dán lặp lại hàng
   chục lần. Chia ngẫu nhiên theo dòng sẽ để bản sao gần-trùng của cùng một
   câu nằm cả hai bên và thổi phồng điểm. Ở đây dùng **leave-one-session-out**:
   mỗi buổi lần lượt làm tập test, hai buổi kia làm train — không có buổi nào
   xuất hiện ở cả hai phía.
2. **Nhãn test do NGƯỜI gán, nhãn train có thể do LLM gán.** Nếu cả hai do
   cùng một LLM sinh ra thì điểm đo được là "mức đồng ý với LLM đó", không
   phải độ chính xác. Vì vậy lô người gán (`lot2`, 3 buổi) **chỉ dùng để
   test**; lô LLM gán (`lot1`, buổi thứ tư) **chỉ dùng để train**.
3. **macro-F1 lấy trung bình trên hợp của nhãn thật và nhãn dự đoán.** Đây là
   mặc định của ``sklearn.f1_score(average="macro")`` và là quy ước đã dùng để
   công bố con số 0,271: một lớp mà mô hình bịa ra nhưng không hề tồn tại
   trong nhãn thật vẫn bị tính F1 = 0 và kéo trung bình xuống. Đó chính là cái
   sai cần phạt. Cột ``macro_f1_support`` (chỉ lấy lớp có nhãn thật) được in
   kèm để người đọc thấy khoảng cách giữa hai quy ước.
4. **Khoảng tin cậy bootstrap, và nói rõ nó chưa đủ.** Bootstrap lấy lại mẫu
   theo DÒNG cho KTC95 của macro-F1 — đó là bất định do cỡ mẫu. Bất định thật
   sự lớn hơn: nó nằm ở cấp **buổi live** (precision nhãn hành động đi từ 1,3%
   đến 67,9% giữa ba buổi). Ba buổi thì bootstrap theo cụm là vô nghĩa, nên
   khung này in thẳng **macro-F1 từng buổi** bên cạnh KTC theo dòng.
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from livelift.console import configure as _configure_console
from livelift.nlp.labels import INTENT_LABELS, TRAINED_LABELS
from livelift.nlp.normalize import STYLE_FEATURE_NAMES, normalize_batch, style_matrix

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD_DIR = REPO_ROOT / "data" / "labeling" / "lot2-da-nguon-10-09"
LLM_LOT_DIR = REPO_ROOT / "data" / "labeling" / "lot1-achan-b519f75c"
AUTHORED_V1 = Path(__file__).parent / "data" / "intent_dataset.jsonl"
AUTHORED_V2 = Path(__file__).parent / "data" / "intent_dataset_11.jsonl"
OUT_DIR = REPO_ROOT / "docs" / "benchmarks" / "intent-eval"
MODEL_V2 = Path(__file__).parent / "model" / "intent_clf_v2.joblib"

SEED = 2026
N_BOOTSTRAP = 2000

#: 5 lớp thêm sau live-fire 08/09 gộp ngược về ``khac`` khi đo trên bộ 6 lớp cũ.
COLLAPSE_TO_6: dict[str, str] = {
    lb: "khac" for lb in INTENT_LABELS if lb not in TRAINED_LABELS and lb != "khac"
}

#: Những lớp mà hệ thống thật sự HÀNH ĐỘNG (hiện thẻ gợi ý cho trung control).
#: Chỉ số "precision nhãn hành động" tính trên đúng tập này — sai ở đây mới là
#: sai tốn tiền; nhầm ``chao_hoi`` thành ``cam_on_khen`` không làm ai mất đơn.
ACTION_LABELS: tuple[str, ...] = ("hoi_gia", "hoi_size", "che_dat", "chot_don", "van_chuyen")


# ---------------------------------------------------------------------------
# 1. Dữ liệu
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GoldRow:
    """Một dòng nhãn THẬT do người gán, kèm xuất xứ đầy đủ."""

    uid: str
    text: str
    label: str
    session: str
    #: ``random`` = mẫu ngẫu nhiên đơn giản (ước lượng prevalence không chệch);
    #: ``predicted`` = mẫu theo nhãn model dự đoán (đo precision, KHÔNG dùng
    #: để nói "bao nhiêu phần trăm chat là hỏi giá").
    stratum: str
    predicted: str | None = None
    confidence: float | None = None


@dataclass(frozen=True)
class TrainRow:
    text: str
    label: str
    source: str
    session: str | None = None


def load_gold_lot2(directory: Path = GOLD_DIR) -> list[GoldRow]:
    """Đọc lô gán nhãn tay MÙ 10/09 (393 dòng, 3 buổi live, bộ 11 lớp).

    Ba file phải khớp nhau từng ``uid``: ``to_label.txt`` (văn bản đã lọc PII),
    ``gold.txt`` (nhãn tay) và ``key.json`` (buổi live + nhãn model dự đoán).
    Thiếu khớp là hỏng dữ liệu, không phải chuyện bỏ qua được — hàm ném lỗi.
    """
    texts: dict[str, str] = {}
    for line in (directory / "to_label.txt").read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            uid, text = line.split("\t", 1)
            texts[uid.strip()] = text
    gold: dict[str, str] = {}
    for line in (directory / "gold.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            gold[parts[0]] = parts[1]
    key = json.loads((directory / "key.json").read_text(encoding="utf-8"))

    rows: list[GoldRow] = []
    for uid, label in sorted(gold.items()):
        if uid not in texts or uid not in key:
            raise ValueError(f"uid {uid} có nhãn nhưng thiếu văn bản hoặc khoá ghép")
        if label not in INTENT_LABELS:
            raise ValueError(f"uid {uid}: nhãn {label!r} không thuộc bộ 11 lớp")
        meta = key[uid]
        rows.append(
            GoldRow(
                uid=uid,
                text=texts[uid],
                label=label,
                session=str(meta["video"]),
                stratum="random" if meta.get("set") == "B" else "predicted",
                predicted=meta.get("predicted"),
                confidence=meta.get("conf"),
            )
        )
    return rows


def load_authored(path: Path | None = None) -> list[TrainRow]:
    """Bộ 320 câu tự biên soạn. Mặc định dùng bản gán lại 11 lớp nếu có.

    Bản gốc (``intent_dataset.jsonl``) viết theo bộ 6 lớp, khi ``khac`` còn ôm
    cả chào hỏi / khen / hỏi sản phẩm. 60 dòng ``khac`` của nó **mâu thuẫn**
    với guideline 11 lớp; train trên đó là dạy mô hình đúng sự lẫn lộn mà 5 lớp
    mới sinh ra để dẹp (``docs/benchmarks/intent-classifier.md`` §"Nợ bắt buộc").
    """
    if path is None:
        path = AUTHORED_V2 if AUTHORED_V2.exists() else AUTHORED_V1
    source = "authored_11" if path == AUTHORED_V2 else "authored_6"
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            rows.append(TrainRow(text=item["text"], label=item["label"], source=source))
    return rows


def load_llm_lot(path: Path | None = None) -> list[TrainRow]:
    """Nhãn do LLM sinh trên bình luận thật của buổi live thứ tư (lô 1).

    Trả về danh sách rỗng khi chưa có file — khung đánh giá phải chạy được
    trên máy chưa có lô này (file nằm ngoài git theo chính sách PII).
    """
    path = path or (LLM_LOT_DIR / "train_llm.jsonl")
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            rows.append(
                TrainRow(
                    text=item["text"],
                    label=item["label"],
                    source="llm_lot1",
                    session=item.get("session", "b519f75c"),
                )
            )
    return rows


# ---------------------------------------------------------------------------
# 2. Chỉ số — hàm thuần, không phụ thuộc sklearn
# ---------------------------------------------------------------------------


def confusion(y_true: list[str], y_pred: list[str]) -> dict[str, dict[str, int]]:
    """Ma trận nhầm lẫn dạng ``{nhãn thật: {nhãn đoán: số lượng}}``."""
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for t, p in zip(y_true, y_pred, strict=True):
        matrix[t][p] += 1
    return {t: dict(row) for t, row in matrix.items()}


def per_class_prf(y_true: list[str], y_pred: list[str], labels: list[str]) -> dict[str, dict]:
    """Precision / recall / F1 / support cho từng lớp."""
    out: dict[str, dict] = {}
    for lb in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == lb and p == lb)
        fp = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t != lb and p == lb)
        fn = sum(1 for t, p in zip(y_true, y_pred, strict=True) if t == lb and p != lb)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        out[lb] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
            "n_pred": tp + fp,
        }
    return out


def union_labels(y_true: list[str], y_pred: list[str]) -> list[str]:
    """Hợp của nhãn thật và nhãn dự đoán, theo thứ tự chuẩn của bộ nhãn."""
    present = set(y_true) | set(y_pred)
    ordered = [lb for lb in INTENT_LABELS if lb in present]
    ordered += sorted(present - set(INTENT_LABELS))  # nhãn lạ vẫn phải lộ ra
    return ordered


def macro_f1(y_true: list[str], y_pred: list[str], labels: list[str] | None = None) -> float:
    """macro-F1 trên ``labels``; mặc định là hợp nhãn thật ∪ nhãn dự đoán.

    Mặc định này TRÙNG với ``sklearn.metrics.f1_score(average="macro")`` không
    truyền ``labels`` — và là quy ước đã sinh ra con số 0,271 công bố trong
    ``docs/benchmarks/live-fire-achan.md``. Một lớp bị mô hình bịa ra (dự đoán
    nhưng không tồn tại trong nhãn thật) nhận F1 = 0 và **được tính vào trung
    bình**: bịa lớp phải bị phạt, không được miễn phí.
    """
    labels = labels if labels is not None else union_labels(y_true, y_pred)
    if not labels:
        return 0.0
    stats = per_class_prf(y_true, y_pred, labels)
    return sum(s["f1"] for s in stats.values()) / len(labels)


def accuracy(y_true: list[str], y_pred: list[str]) -> float:
    if not y_true:
        return 0.0
    return sum(t == p for t, p in zip(y_true, y_pred, strict=True)) / len(y_true)


def bootstrap_macro_f1(
    y_true: list[str],
    y_pred: list[str],
    *,
    n: int = N_BOOTSTRAP,
    seed: int = SEED,
    alpha: float = 0.05,
) -> tuple[float, float]:
    """KTC percentile cho macro-F1, lấy lại mẫu theo DÒNG.

    Cảnh báo phải đi kèm mọi lần trích: bất định thật lớn hơn khoảng này, vì
    đơn vị lấy mẫu thật sự là **buổi live** chứ không phải bình luận. Ba buổi
    là quá ít để bootstrap theo cụm, nên báo cáo in thêm macro-F1 từng buổi.
    Mỗi lần lấy lại mẫu, bộ nhãn để tính trung bình được xác định lại trên
    chính mẫu đó — nếu không, quy ước "hợp nhãn" sẽ bị đóng băng theo mẫu gốc.
    """
    rng = random.Random(seed)
    size = len(y_true)
    if size == 0:
        return (0.0, 0.0)
    scores = []
    for _ in range(n):
        idx = [rng.randrange(size) for _ in range(size)]
        bt = [y_true[i] for i in idx]
        bp = [y_pred[i] for i in idx]
        scores.append(macro_f1(bt, bp))
    scores.sort()
    lo = scores[max(0, int(math.floor(alpha / 2 * n)))]
    hi = scores[min(n - 1, int(math.ceil((1 - alpha / 2) * n)) - 1)]
    return (round(lo, 4), round(hi, 4))


def action_precision(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    """Precision gộp trên các nhãn HÀNH ĐỘNG + KTC95 Wilson.

    Đây là chỉ số sát sản phẩm nhất: trong tất cả những lần hệ thống nói "có
    khách đang hỏi giá / chốt đơn", bao nhiêu lần là thật. Wilson chứ không
    Wald vì tỷ lệ quan sát được nằm sát 0 (Wald cho cận dưới âm).
    """
    pairs = [(t, p) for t, p in zip(y_true, y_pred, strict=True) if p in ACTION_LABELS]
    n = len(pairs)
    k = sum(1 for t, p in pairs if t == p)
    if n == 0:
        return {"k": 0, "n": 0, "precision": None, "ci95": None}
    return {"k": k, "n": n, "precision": round(k / n, 4), "ci95": wilson_ci(k, n)}


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """KTC Wilson cho tỷ lệ nhị thức — đúng ở đuôi, không bao giờ ra ngoài [0,1]."""
    if n == 0:
        return (0.0, 1.0)
    phat = k / n
    denom = 1 + z**2 / n
    centre = (phat + z**2 / (2 * n)) / denom
    half = z * math.sqrt(phat * (1 - phat) / n + z**2 / (4 * n**2)) / denom
    return (round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4))


# ---------------------------------------------------------------------------
# 3. Chia dữ liệu theo buổi live
# ---------------------------------------------------------------------------


def leave_one_session_out(rows: list[GoldRow]) -> list[tuple[str, list[GoldRow], list[GoldRow]]]:
    """``[(tên buổi test, dòng train, dòng test)]`` — không buổi nào ở hai phía."""
    sessions = sorted({r.session for r in rows})
    return [
        (s, [r for r in rows if r.session != s], [r for r in rows if r.session == s])
        for s in sessions
    ]


def dedup_key(text: str) -> str:
    """Khoá so trùng: bỏ dấu câu/khoảng trắng/hoa-thường, giữ chữ và số.

    Chia theo buổi live ngăn được rò rỉ *theo phiên*, KHÔNG ngăn được rò rỉ
    *theo văn bản*: cùng một người bán dán cùng một bảng giá ở nhiều buổi, và
    ``chào cả nhà`` xuất hiện ở mọi buổi. Đo được 9/345 văn bản gold duy nhất
    trùng khít một dòng trong lô LLM. Chín dòng không làm đổi kết quả, nhưng
    một khung đánh giá tự nhận là trung thực thì phải LOẠI chúng và ĐẾM chúng
    chứ không phải đoán là chúng vô hại.
    """
    import re as _re
    import unicodedata as _ud

    normalized = _ud.normalize("NFKC", text).lower()
    return _re.sub(r"[^0-9a-zà-ỹ]+", " ", normalized).strip()


# ---------------------------------------------------------------------------
# 4. Các hệ thống được chấm
# ---------------------------------------------------------------------------

Predictor = Callable[[list[str]], list[str]]
#: ``fit_fn(train_gold_rows, extra_train_rows) -> predictor`` — nhận dữ liệu
#: train của ĐÚNG fold hiện tại; hệ thống không học được thì bỏ qua tham số.
SystemFactory = Callable[[list[GoldRow], list[TrainRow]], Predictor]


def system_majority(_g: list[GoldRow], _e: list[TrainRow]) -> Predictor:
    """Baseline tầm thường: luôn đoán lớp đa số (``khac``).

    Không phải trò đùa — trên chat thật nó đạt accuracy 0,995 và đánh bại mô
    hình đã huấn luyện. Mọi hệ thống không vượt được nó là hệ thống âm giá trị.
    """
    return lambda texts: ["khac"] * len(texts)


def system_keyword(_g: list[GoldRow], _e: list[TrainRow]) -> Predictor:
    """Baseline từ khoá tiền đăng ký (``intent.classify_keywords``)."""
    from livelift.nlp.intent import classify_keywords

    return lambda texts: [classify_keywords(t) for t in texts]


def system_shipped(_g: list[GoldRow], _e: list[TrainRow]) -> Predictor:
    """Artifact ĐANG CHẠY trong sản phẩm (``intent_clf.joblib`` + abstain 0,45).

    Đây là con số "TRƯỚC" của bảng trước/sau. Nó không được huấn luyện lại
    theo fold — nó là một file cố định, đúng như trên máy chủ.
    """
    from livelift.nlp.intent import classify

    return lambda texts: [classify(t) for t in texts]


def build_tfidf_pipeline(
    *,
    use_normalize: bool = True,
    use_style: bool = True,
    char_ngrams: tuple[int, int] = (2, 5),
    word_ngrams: tuple[int, int] = (1, 2),
    min_df: int = 2,
    c: float = 4.0,
):
    """TF-IDF char+word (+ đặc trưng phong cách) → hồi quy logistic.

    Giữ nguyên kiến trúc của ``train_intent.build_pipeline`` để phép so sánh
    là **một biến một lần**: khác biệt duy nhất là bước chuẩn hoá và khối đặc
    trưng phong cách, đúng hai thứ mà bảng ablation đo.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import FeatureUnion, Pipeline
    from sklearn.preprocessing import FunctionTransformer, StandardScaler

    text_blocks: list[tuple[str, Any]] = [
        (
            "char",
            TfidfVectorizer(
                analyzer="char_wb", ngram_range=char_ngrams, min_df=min_df, sublinear_tf=True
            ),
        ),
        (
            "word",
            TfidfVectorizer(
                analyzer="word", ngram_range=word_ngrams, min_df=min_df, sublinear_tf=True
            ),
        ),
    ]
    steps: list[tuple[str, Any]] = []
    if use_normalize:
        steps.append(("norm", FunctionTransformer(normalize_batch, validate=False)))
    text_union = FeatureUnion(text_blocks)
    if use_style:
        # Nhánh phong cách đọc văn bản THÔ (trước chuẩn hoá) — caps ratio chết
        # nếu chạy sau lowercase. Vì vậy nó nằm ở nhánh song song của
        # FeatureUnion ngoài cùng, không nối sau bước "norm".
        inner = Pipeline([*steps, ("text", text_union)]) if steps else text_union
        features = FeatureUnion(
            [
                ("text", inner),
                (
                    "style",
                    Pipeline(
                        [
                            ("raw", FunctionTransformer(style_matrix, validate=False)),
                            ("scale", StandardScaler()),
                        ]
                    ),
                ),
            ]
        )
        pipe_steps = [("features", features)]
    else:
        pipe_steps = [*steps, ("features", text_union)]
    pipe_steps.append(
        ("clf", LogisticRegression(max_iter=3000, C=c, class_weight="balanced", random_state=SEED))
    )
    return Pipeline(pipe_steps)


@dataclass
class TfidfSystem:
    """Hệ thống TF-IDF huấn luyện lại trên ĐÚNG fold hiện tại.

    ``use_gold`` / ``use_authored`` / ``use_llm`` bật tắt từng nguồn dữ liệu —
    ba cột của bảng ablation "nguồn dữ liệu huấn luyện".
    """

    use_normalize: bool = True
    use_style: bool = True
    use_gold: bool = True
    use_authored: bool = True
    use_llm: bool = True
    collapse_to_6: bool = False
    #: ``None`` = không từ chối; một số = ngưỡng cố định; ``"auto"`` = chọn
    #: ngưỡng **bên trong tập train của fold** (xem :meth:`pick_threshold`).
    abstain_threshold: float | str | None = None
    target_action_precision: float = 0.70
    extra_pool: list[TrainRow] = field(default_factory=list)
    chosen_thresholds: list[float] = field(default_factory=list)

    def training_rows(self, gold_train: list[GoldRow]) -> list[TrainRow]:
        rows: list[TrainRow] = []
        if self.use_gold:
            rows += [
                TrainRow(r.text, r.label, "gold_human", r.session)
                for r in gold_train
                # Tầng `predicted` được rút theo nhãn model đoán nên lệch về
                # lớp hành động; dùng làm TRAIN thì tốt (đó là chỗ khó), dùng
                # làm ước lượng prevalence thì sai — xem data/labeling/README.
            ]
        pool = self.extra_pool
        if self.use_authored:
            rows += [r for r in pool if r.source.startswith("authored")]
        if self.use_llm:
            rows += [r for r in pool if r.source == "llm_lot1"]
        if self.collapse_to_6:
            rows = [TrainRow(r.text, COLLAPSE_TO_6.get(r.label, r.label), r.source) for r in rows]
        return rows

    THRESHOLD_GRID: tuple[float, ...] = (0.0, 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8)

    def pick_threshold(self, gold_train: list[GoldRow], extra: list[TrainRow]) -> float:
        """Chọn ngưỡng từ chối bằng **leave-one-session-out LỒNG BÊN TRONG** tập
        train của fold hiện tại. Tập test ngoài cùng không được chạm tới.

        Vì sao phải lồng chứ không cross-validate trộn lẫn: ngưỡng cần được
        hiệu chuẩn trên phân phối mà hệ thống sẽ gặp — chat thật của một buổi
        live lạ. Cross-validation trộn cả bộ biên soạn và lô LLM vào tập hiệu
        chuẩn cho ra ngưỡng 0,0 ở cả ba fold (đã đo): trên phân phối train,
        precision nhãn hành động vốn đã cao nên không ngưỡng nào cần thiết.
        Đó là một kết quả sai vì tập hiệu chuẩn sai, không phải vì abstain vô
        dụng. Ở đây tập hiệu chuẩn CHỈ gồm nhãn người gán của một buổi live
        bị giữ lại trong nội bộ tập train.

        Quy tắc định trước: ngưỡng THẤP NHẤT đạt ``target_action_precision``.
        Thấp nhất chứ không phải tốt nhất — giữa hai ngưỡng cùng đạt yêu cầu
        chất lượng thì cái phủ nhiều hơn có ích hơn. Không bao giờ quét ngưỡng
        trên tập test rồi lấy điểm đẹp nhất: đường cong độ phủ ↔ độ chính xác
        vẫn được in đầy đủ, nhưng như một **thực đơn điểm vận hành**, không
        phải như một kết quả đã thẩm định.
        """
        inner = leave_one_session_out(gold_train)
        if len(inner) < 2:
            return 0.45  # không đủ buổi để hiệu chuẩn -> giữ ngưỡng sản phẩm
        scores: list[tuple[float, str, str]] = []  # (độ tự tin, nhãn đoán, nhãn thật)
        for _session, inner_train, inner_test in inner:
            rows = self.training_rows(inner_train)
            pipe = build_tfidf_pipeline(use_normalize=self.use_normalize, use_style=self.use_style)
            pipe.fit([r.text for r in rows], [r.label for r in rows])
            proba = pipe.predict_proba([r.text for r in inner_test])
            classes = list(pipe.classes_)
            for row, gold_row in zip(proba, inner_test, strict=True):
                i = int(row.argmax())
                scores.append((float(row[i]), str(classes[i]), gold_row.label))

        chosen = self.THRESHOLD_GRID[-1]
        for threshold in self.THRESHOLD_GRID:
            hits = [(p, t) for conf, p, t in scores if conf >= threshold and p in ACTION_LABELS]
            if hits and sum(p == t for p, t in hits) / len(hits) >= self.target_action_precision:
                chosen = threshold
                break
        return chosen

    def __call__(self, gold_train: list[GoldRow], extra: list[TrainRow]) -> Predictor:
        self.extra_pool = extra
        rows = self.training_rows(gold_train)
        pipe = build_tfidf_pipeline(use_normalize=self.use_normalize, use_style=self.use_style)
        pipe.fit([r.text for r in rows], [r.label for r in rows])
        threshold: float | None
        if self.abstain_threshold == "auto":
            threshold = self.pick_threshold(gold_train, extra)
            self.chosen_thresholds.append(threshold)
        else:
            threshold = self.abstain_threshold  # type: ignore[assignment]

        def predict(texts: list[str]) -> list[str]:
            if threshold is None:
                return [str(x) for x in pipe.predict(texts)]
            proba = pipe.predict_proba(texts)
            classes = list(pipe.classes_)
            out = []
            for row in proba:
                i = int(row.argmax())
                out.append(str(classes[i]) if float(row[i]) >= threshold else "khac")
            return out

        return predict


# ---------------------------------------------------------------------------
# 5. Bộ chạy
# ---------------------------------------------------------------------------


def evaluate_system(
    name: str,
    factory: SystemFactory,
    gold: list[GoldRow],
    extra: list[TrainRow],
    *,
    collapse_gold_to_6: bool = False,
    stratum: str | None = None,
) -> dict[str, Any]:
    """Chạy leave-one-session-out và gộp dự đoán ngoài-fold lại để chấm.

    ``stratum`` lọc tập TEST (không lọc train): ``"random"`` cho câu hỏi
    "prevalence thật bao nhiêu", ``None`` cho toàn bộ 393 dòng.
    """
    y_true: list[str] = []
    y_pred: list[str] = []
    sessions: list[str] = []
    strata: list[str] = []
    per_session: dict[str, dict[str, Any]] = {}
    n_leaked = 0

    for session, train_rows, test_rows in leave_one_session_out(gold):
        if stratum:
            test_rows = [r for r in test_rows if r.stratum == stratum]
        if not test_rows:
            continue
        # Rào chắn rò rỉ theo VĂN BẢN, chạy trước mỗi lần huấn luyện: bất kỳ
        # dòng train nào (gold buổi khác hay lô LLM) trùng khít một dòng test
        # đều bị loại khỏi fold này và được đếm lại trong báo cáo.
        blocked = {dedup_key(r.text) for r in test_rows}
        kept_train = [r for r in train_rows if dedup_key(r.text) not in blocked]
        kept_extra = [r for r in extra if dedup_key(r.text) not in blocked]
        n_leaked += (len(train_rows) - len(kept_train)) + (len(extra) - len(kept_extra))
        predictor = factory(kept_train, kept_extra)
        preds = predictor([r.text for r in test_rows])
        truths = [r.label for r in test_rows]
        if collapse_gold_to_6:
            truths = [COLLAPSE_TO_6.get(t, t) for t in truths]
            preds = [COLLAPSE_TO_6.get(p, p) for p in preds]
        per_session[session] = {
            "n": len(test_rows),
            "macro_f1": round(macro_f1(truths, preds), 4),
            "accuracy": round(accuracy(truths, preds), 4),
            "action_precision": action_precision(truths, preds),
        }
        y_true += truths
        y_pred += preds
        sessions += [session] * len(truths)
        strata += [r.stratum for r in test_rows]

    labels_union = union_labels(y_true, y_pred)
    labels_support = [lb for lb in labels_union if any(t == lb for t in y_true)]
    lo, hi = bootstrap_macro_f1(y_true, y_pred)
    # Tầng `random` là 200 dòng lấy NGẪU NHIÊN ĐƠN GIẢN — đúng phân phối mà hệ
    # thống gặp khi chạy thật. Tầng `predicted` được rút theo nhãn model đoán
    # nên giàu lớp hành động một cách nhân tạo: nó đo precision tốt, nhưng
    # accuracy/macro-F1 trên nó KHÔNG phải con số vận hành.
    rand_idx = [i for i, s in enumerate(strata) if s == "random"]
    rt = [y_true[i] for i in rand_idx]
    rp = [y_pred[i] for i in rand_idx]
    rlo, rhi = bootstrap_macro_f1(rt, rp)
    return {
        "name": name,
        "n_test": len(y_true),
        "macro_f1": round(macro_f1(y_true, y_pred, labels_union), 4),
        "macro_f1_ci95": [lo, hi],
        "macro_f1_support_only": round(macro_f1(y_true, y_pred, labels_support), 4),
        "accuracy": round(accuracy(y_true, y_pred), 4),
        "action_precision": action_precision(y_true, y_pred),
        "n_labels_scored": len(labels_union),
        "phantom_labels": sorted(set(labels_union) - set(labels_support)),
        "per_class": per_class_prf(y_true, y_pred, labels_union),
        "confusion": confusion(y_true, y_pred),
        "per_session": per_session,
        "n_train_rows_dropped_as_leak": n_leaked,
        "chosen_thresholds": list(getattr(factory, "chosen_thresholds", []) or []),
        "random_stratum": {
            "n": len(rt),
            "macro_f1": round(macro_f1(rt, rp), 4),
            "macro_f1_ci95": [rlo, rhi],
            "accuracy": round(accuracy(rt, rp), 4),
            "action_precision": action_precision(rt, rp),
        },
        "predictions": list(zip(sessions, strata, y_true, y_pred, strict=True)),
    }


def error_examples(
    gold: list[GoldRow],
    extra: list[TrainRow],
    system: SystemFactory,
    *,
    per_cell: int = 4,
) -> dict[str, list[dict[str, Any]]]:
    """Ví dụ THẬT cho từng ô nhầm lẫn ``nhãn thật -> nhãn đoán``.

    Phân tích lỗi không đọc được từ ma trận số: "mô hình nhầm 12 dòng
    ``cam_on_khen`` thành ``che_dat``" không nói cho ai biết phải sửa gì, còn
    "``Xoài rẻ quá ạ`` bị gắn ``che_dat`` vì thấy chữ *rẻ*" thì nói ngay.
    Văn bản trả về đã qua bộ lọc PII ở tầng ingest.
    """
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for session, train_rows, test_rows in leave_one_session_out(gold):
        blocked = {dedup_key(r.text) for r in test_rows}
        predictor = system(
            [r for r in train_rows if dedup_key(r.text) not in blocked],
            [r for r in extra if dedup_key(r.text) not in blocked],
        )
        for row, pred in zip(test_rows, predictor([r.text for r in test_rows]), strict=True):
            if pred == row.label:
                continue
            cell = f"{row.label} -> {pred}"
            if len(buckets[cell]) < per_cell:
                buckets[cell].append({"text": row.text, "session": session, "uid": row.uid})
    return dict(sorted(buckets.items(), key=lambda kv: -len(kv[1])))


def coverage_curve(
    gold: list[GoldRow], extra: list[TrainRow], thresholds: list[float]
) -> list[dict[str, Any]]:
    """Đường đánh đổi ĐỘ PHỦ ↔ ĐỘ CHÍNH XÁC của tuỳ chọn từ chối trả lời.

    Ở mỗi ngưỡng: bao nhiêu phần trăm bình luận vẫn được gắn một nhãn hành
    động (độ phủ), và trong số đó bao nhiêu đúng (precision). Đây là bảng mà
    trọng tâm 8 "phương án kiểm soát đầu ra" cần: hệ thống được phép im lặng,
    và cái giá của việc im lặng đo được bằng số.
    """
    out = []
    for th in thresholds:
        system = TfidfSystem(abstain_threshold=th)
        res = evaluate_system(f"abstain@{th:.2f}", system, gold, extra)
        n_action = res["action_precision"]["n"]
        out.append(
            {
                "threshold": th,
                "macro_f1": res["macro_f1"],
                "accuracy": res["accuracy"],
                "action_coverage": round(n_action / max(res["n_test"], 1), 4),
                "action_precision": res["action_precision"]["precision"],
                "action_ci95": res["action_precision"]["ci95"],
            }
        )
    return out


# ---------------------------------------------------------------------------
# 6. Báo cáo
# ---------------------------------------------------------------------------


def _fmt(value: Any, digits: int = 3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}".replace(".", ",")
    return str(value)


def _ci(pair: Any) -> str:
    if not pair:
        return "—"
    return f"[{_fmt(pair[0])}; {_fmt(pair[1])}]"


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Kết quả đánh giá bộ phân loại ý định — sinh tự động")
    add("")
    add(f"*Sinh bởi `python -m livelift.nlp.eval_intent` · {report['generated_at']}*")
    add("")
    add("> Mọi con số dưới đây đo trên **chat livestream THẬT đã gán nhãn tay**,")
    add("> chia **leave-one-session-out theo buổi live** (không buổi nào nằm cả")
    add("> train lẫn test). Nhãn test do người gán; nhãn train bổ sung do LLM gán")
    add("> được kê khai riêng.")
    add("")
    inv = report["inventory"]
    add("## 1. Kiểm kê dữ liệu")
    add("")
    add("| Nguồn | Số dòng | Ghi chú |")
    add("|---|---:|---|")
    for item in inv["sources"]:
        add(f"| {item['name']} | {item['n']} | {item['note']} |")
    add("")
    add("Phân bố nhãn của tập test (người gán):")
    add("")
    add("| Lớp | Số dòng | Tỷ lệ |")
    add("|---|---:|---:|")
    total = sum(inv["gold_label_counts"].values())
    for lb, n in sorted(inv["gold_label_counts"].items(), key=lambda kv: -kv[1]):
        add(f"| `{lb}` | {n} | {n / total:.1%} |".replace(".", ",").replace(",1%", ",1%"))
    add("")
    add("| Buổi live | Dòng gán nhãn | Tỷ lệ ý định hành động THẬT (tầng ngẫu nhiên) |")
    add("|---|---:|---:|")
    for s, d in sorted(inv["per_session"].items()):
        add(f"| `{s}` | {d['n']} | {d['action_prevalence_random']} |")
    add("")

    for block in report["tables"]:
        add(f"## {block['title']}")
        add("")
        if block.get("note"):
            add(block["note"])
            add("")
        add(
            "| Hệ thống | macro-F1 (393 dòng) | KTC95 (bootstrap dòng) | macro-F1 "
            "(chỉ lớp có nhãn thật) | Accuracy | Precision nhãn hành động | "
            "macro-F1 tầng NGẪU NHIÊN (200) |"
        )
        add("|---|---:|---|---:|---:|---:|---:|")
        for r in block["rows"]:
            ap = r["action_precision"]
            ap_txt = (
                f"{_fmt(ap['precision'])} ({ap['k']}/{ap['n']})" if ap["n"] else "— (0 dự đoán)"
            )
            rnd = r.get("random_stratum", {})
            add(
                f"| {r['name']} | **{_fmt(r['macro_f1'])}** | {_ci(r['macro_f1_ci95'])} | "
                f"{_fmt(r['macro_f1_support_only'])} | {_fmt(r['accuracy'])} | "
                f"{ap_txt} | {_fmt(rnd.get('macro_f1'))} {_ci(rnd.get('macro_f1_ci95'))} |"
            )
        add("")
        add("macro-F1 từng buổi live (bất định thật nằm ở đây, không ở KTC bootstrap):")
        add("")
        sessions = sorted({s for r in block["rows"] for s in r["per_session"]})
        add("| Hệ thống | " + " | ".join(f"`{s}`" for s in sessions) + " |")
        add("|---" * (len(sessions) + 1) + "|")
        for r in block["rows"]:
            cells = [_fmt(r["per_session"].get(s, {}).get("macro_f1")) for s in sessions]
            add(f"| {r['name']} | " + " | ".join(cells) + " |")
        add("")

    if report.get("coverage"):
        add("## Đường đánh đổi độ phủ ↔ độ chính xác (tuỳ chọn từ chối trả lời)")
        add("")
        add("| Ngưỡng | macro-F1 | Accuracy | Độ phủ nhãn hành động | Precision | KTC95 |")
        add("|---:|---:|---:|---:|---:|---|")
        for r in report["coverage"]:
            add(
                f"| {_fmt(r['threshold'], 2)} | {_fmt(r['macro_f1'])} | {_fmt(r['accuracy'])} | "
                f"{_fmt(r['action_coverage'])} | {_fmt(r['action_precision'])} | "
                f"{_ci(r['action_ci95'])} |"
            )
        add("")

    best = report.get("best")
    if best:
        add("## F1 từng lớp — hệ thống tốt nhất")
        add("")
        add(f"Hệ thống: **{best['name']}**")
        add("")
        add("| Lớp | P | R | F1 | Nhãn thật | Lần dự đoán |")
        add("|---|---:|---:|---:|---:|---:|")
        for lb, s in best["per_class"].items():
            add(
                f"| `{lb}` | {_fmt(s['precision'])} | {_fmt(s['recall'])} | "
                f"**{_fmt(s['f1'])}** | {s['support']} | {s['n_pred']} |"
            )
        add("")
        add("Ma trận nhầm lẫn (hàng = nhãn thật, cột = nhãn đoán):")
        add("")
        cols = list(best["per_class"].keys())
        add("| thật \\ đoán | " + " | ".join(f"`{c}`" for c in cols) + " |")
        add("|---" * (len(cols) + 1) + "|")
        for t in cols:
            row = best["confusion"].get(t, {})
            if not row:
                continue
            cells = [str(row.get(c, 0)) if row.get(c) else "·" for c in cols]
            add(f"| `{t}` | " + " | ".join(cells) + " |")
        add("")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 7. CLI
# ---------------------------------------------------------------------------


def build_inventory(gold: list[GoldRow], extra: list[TrainRow]) -> dict[str, Any]:
    per_session: dict[str, Any] = {}
    for s in sorted({r.session for r in gold}):
        rows = [r for r in gold if r.session == s]
        rand = [r for r in rows if r.stratum == "random"]
        k = sum(1 for r in rand if r.label in ACTION_LABELS)
        per_session[s] = {
            "n": len(rows),
            "n_random": len(rand),
            "action_prevalence_random": (
                f"{k}/{len(rand)} = {k / len(rand):.1%}".replace(".", ",") if rand else "—"
            ),
        }
    sources = [
        {
            "name": "`data/labeling/lot2-da-nguon-10-09` — gán nhãn TAY, mù, 11 lớp",
            "n": len(gold),
            "note": f"{len({r.session for r in gold})} buổi live · CHỈ dùng làm TEST",
        }
    ]
    by_source = Counter(r.source for r in extra)
    note = {
        "authored_6": "tự biên soạn, bộ 6 lớp gốc — CHỈ train",
        "authored_11": "tự biên soạn, đã gán lại theo 11 lớp — CHỈ train",
        "llm_lot1": "bình luận thật buổi thứ tư, nhãn do LLM sinh — CHỈ train",
    }
    for src, n in by_source.items():
        sources.append({"name": f"`{src}`", "n": n, "note": note.get(src, "")})
    return {
        "sources": sources,
        "gold_label_counts": dict(Counter(r.label for r in gold)),
        "gold_sessions": sorted({r.session for r in gold}),
        "per_session": per_session,
        "extra_label_counts": dict(Counter(r.label for r in extra)),
    }


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    parser = argparse.ArgumentParser(prog="python -m livelift.nlp.eval_intent", description=__doc__)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    parser.add_argument("--ablation", action="store_true", help="chạy thêm bảng ablation")
    parser.add_argument("--coverage", action="store_true", help="quét ngưỡng abstain")
    parser.add_argument("--save-model", action="store_true", help="đóng gói model 11 lớp")
    parser.add_argument(
        "--errors",
        metavar="FILE",
        help="ghi ví dụ lỗi THẬT ra file (mặc định tắt — file chứa bình luận người dùng)",
    )
    parser.add_argument("--bootstrap", type=int, default=N_BOOTSTRAP)
    args = parser.parse_args(argv)

    gold = load_gold_lot2()
    extra = load_authored() + load_llm_lot()
    inventory = build_inventory(gold, extra)

    print(f"gold (người gán): {len(gold)} dòng · {len(inventory['gold_sessions'])} buổi live")
    print(f"train bổ sung   : {len(extra)} dòng · {dict(Counter(r.source for r in extra))}")

    tables: list[dict[str, Any]] = []

    baselines: list[tuple[str, SystemFactory]] = [
        ("B0 · luôn đoán lớp đa số `khac`", system_majority),
        ("B1 · từ khoá (tiền đăng ký)", system_keyword),
        ("B2 · TF-IDF+LogReg ĐANG CHẠY (`intent_clf.joblib`, abstain 0,45)", system_shipped),
        (
            "B3 · TF-IDF+LogReg train lại trên 320 câu biên soạn (6 lớp, không abstain)",
            # ``collapse_to_6`` áp lên NHÃN TRAIN dựng lại đúng bộ 6 lớp gốc
            # (5 lớp mới gộp ngược về ``khac`` = chính nhãn của
            # ``intent_dataset.jsonl``). Nhãn TEST vẫn là 11 lớp — đây là phép
            # đo "mô hình cũ gặp thế giới thật", không phải phép đo đã gọt sân.
            TfidfSystem(
                use_gold=False,
                use_llm=False,
                use_normalize=False,
                use_style=False,
                use_authored=True,
                collapse_to_6=True,
            ),
        ),
    ]
    rows = [evaluate_system(n, f, gold, extra) for n, f in baselines]
    tables.append(
        {
            "title": "2. Baseline trên chat thật (test = buổi live mô hình chưa từng thấy)",
            "note": (
                "Ba baseline bắt buộc + artifact đang chạy. Cột `n test` = 393 dòng "
                "gán nhãn tay, gộp từ ba fold leave-one-session-out."
            ),
            "rows": rows,
        }
    )

    improved: list[tuple[str, SystemFactory]] = [
        ("C1 · TF-IDF 11 lớp, train = biên soạn(11) + gold 2 buổi", TfidfSystem(use_llm=False)),
        ("C2 · C1 + nhãn LLM trên buổi thứ tư", TfidfSystem()),
        (
            "C3 · C2 + từ chối trả lời, ngưỡng chọn TRONG tập train",
            TfidfSystem(abstain_threshold="auto"),
        ),
    ]
    rows_improved = [evaluate_system(n, f, gold, extra) for n, f in improved]
    tables.append(
        {
            "title": "3. Sau cải tiến",
            "note": "Cùng tập test, cùng cách chia. Chỉ dữ liệu train và đặc trưng thay đổi.",
            "rows": rows_improved,
        }
    )

    report: dict[str, Any] = {
        "generated_at": __import__("datetime")
        .datetime.now()
        .astimezone()
        .isoformat(timespec="seconds"),
        "seed": SEED,
        "n_bootstrap": args.bootstrap,
        "inventory": inventory,
        "tables": tables,
    }

    if args.ablation:
        report["tables"].append({"title": "4. Ablation", "rows": run_ablation(gold, extra)})
    if args.coverage:
        report["coverage"] = coverage_curve(gold, extra, [0.0, 0.3, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8])

    all_rows = [r for t in report["tables"] for r in t["rows"]]
    report["best"] = max(all_rows, key=lambda r: r["macro_f1"])

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # `predictions` chứa văn bản-suy-ra-được của bình luận thật; giữ trong JSON
    # cho phân tích lỗi nhưng KHÔNG in ra Markdown công khai.
    (out_dir / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "results.md").write_text(render_markdown(report), encoding="utf-8")
    print(f"\nđã ghi: {out_dir / 'results.json'}")
    print(f"đã ghi: {out_dir / 'results.md'}")

    print("\n== Tóm tắt ==")
    for t in report["tables"]:
        print(f"\n{t['title']}")
        for r in t["rows"]:
            ap = r["action_precision"]
            print(
                f"  {r['name']:<62} macro-F1 {r['macro_f1']:.3f} "
                f"[{r['macro_f1_ci95'][0]:.3f};{r['macro_f1_ci95'][1]:.3f}] "
                f"acc {r['accuracy']:.3f} "
                f"P(action) {ap['precision'] if ap['n'] else '—'} ({ap['k']}/{ap['n']})"
            )

    if args.errors:
        cells = error_examples(gold, extra, TfidfSystem())
        lines = ["# Ví dụ lỗi thật — sinh bởi `eval_intent --errors`", ""]
        for cell, items in cells.items():
            lines.append(f"## {cell} ({len(items)} ví dụ in ra)")
            lines += [f"- `{i['session']}` `{i['uid']}` — {i['text']}" for i in items]
            lines.append("")
        Path(args.errors).write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"đã ghi ví dụ lỗi: {args.errors}")

    if args.save_model:
        save_best_model(gold, extra)
    return 0


def run_ablation(gold: list[GoldRow], extra: list[TrainRow]) -> list[dict[str, Any]]:
    """Bảng đóng góp từng thành phần — MẪU 3 mục 9 bắt buộc có bảng này.

    Mỗi dòng tắt ĐÚNG MỘT thành phần so với cấu hình đầy đủ, trừ hai dòng bộ
    nhãn (chúng đổi cả không gian nhãn nên phải chấm trên nhãn thật đã gộp về
    6 lớp — ghi rõ trong tên dòng).
    """
    full = TfidfSystem()
    variants: list[tuple[str, SystemFactory, dict[str, Any]]] = [
        ("A0 · đầy đủ (chuẩn hoá + phong cách + 11 lớp + mọi nguồn)", full, {}),
        ("A1 · − chuẩn hoá văn bản (NFKC/teencode/emoji)", TfidfSystem(use_normalize=False), {}),
        (
            "A2 · − đặc trưng phong cách (caps/giá/‖ → mô hình người nói)",
            TfidfSystem(use_style=False),
            {},
        ),
        ("A3 · − nhãn LLM buổi thứ tư", TfidfSystem(use_llm=False), {}),
        ("A4 · − bộ biên soạn (chỉ dữ liệu thật)", TfidfSystem(use_authored=False), {}),
        ("A5 · − gold 2 buổi train (chỉ biên soạn + LLM)", TfidfSystem(use_gold=False), {}),
        (
            "A6 · + từ chối trả lời (ngưỡng chọn trong train)",
            TfidfSystem(abstain_threshold="auto"),
            {},
        ),
    ]
    rows = [evaluate_system(n, f, gold, extra, **kw) for n, f, kw in variants]
    # Bộ nhãn 6 vs 11: chấm trên cùng KHÔNG GIAN NHÃN 6 lớp, nếu không thì so
    # một macro-F1 trên 6 lớp với một macro-F1 trên 10 lớp — hai thang khác nhau.
    rows.append(
        evaluate_system(
            "A7 · bộ nhãn 6 lớp (chấm trên không gian 6 lớp)",
            TfidfSystem(collapse_to_6=True),
            gold,
            extra,
            collapse_gold_to_6=True,
        )
    )
    rows.append(
        evaluate_system(
            "A8 · bộ nhãn 11 lớp, gộp về 6 khi chấm (cùng thang với A7)",
            TfidfSystem(),
            gold,
            extra,
            collapse_gold_to_6=True,
        )
    )
    return rows


def save_best_model(gold: list[GoldRow], extra: list[TrainRow]) -> Path:
    """Huấn luyện lại trên TOÀN BỘ dữ liệu rồi đóng gói ``intent_clf_v2.joblib``.

    Huấn luyện cuối dùng cả ba buổi gold — hợp lệ vì mọi con số công bố đã đo
    xong bằng leave-one-session-out trước đó; artifact giao hàng thì không có
    lý do gì phải bỏ phí một buổi dữ liệu.
    """
    import joblib
    import sklearn

    system = TfidfSystem()
    system.extra_pool = extra
    rows = system.training_rows(
        [GoldRow(r.uid, r.text, r.label, r.session, r.stratum) for r in gold]
    )
    pipe = build_tfidf_pipeline()
    pipe.fit([r.text for r in rows], [r.label for r in rows])
    MODEL_V2.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipe, MODEL_V2, compress=9)
    meta = {
        "sklearn_version": sklearn.__version__,
        "trained_at_utc": __import__("datetime")
        .datetime.now(__import__("datetime").UTC)
        .isoformat(timespec="seconds"),
        "n_samples": len(rows),
        "labels": sorted({r.label for r in rows}, key=INTENT_LABELS.index),
        "sources": dict(Counter(r.source for r in rows)),
        "seed": SEED,
        "style_features": list(STYLE_FEATURE_NAMES),
        "eval": "leave-one-session-out trên data/labeling/lot2-da-nguon-10-09",
    }
    MODEL_V2.with_suffix(".meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nđã lưu: {MODEL_V2.name} ({MODEL_V2.stat().st_size / 1024:.0f} KB) · {len(rows)} mẫu")
    return MODEL_V2


if __name__ == "__main__":
    # Gọi qua tên module đầy đủ, KHÔNG dùng ``main`` của bản sao ``__main__``:
    # artifact joblib lưu tham chiếu hàm theo ``__module__``, nên chạy trực
    # tiếp bản ``__main__`` sẽ đóng gói một model không tiến trình nào khác
    # nạp lại được (sự cố 14/09). Hai hàm biến đổi đã chuyển sang
    # ``livelift.nlp.normalize``; dòng này là lớp phòng thủ thứ hai.
    from livelift.nlp.eval_intent import main as _main

    raise SystemExit(_main())
