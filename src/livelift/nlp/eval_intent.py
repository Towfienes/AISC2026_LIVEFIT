"""Khung đánh giá TRUNG THỰC cho bộ phân loại ý định — chạy lại bằng MỘT lệnh.

    python -m livelift.nlp.eval_intent                       # baseline + trước/sau
    python -m livelift.nlp.eval_intent --ablation --coverage # đủ bộ bảng đã công bố
    python -m livelift.nlp.eval_intent --save-model          # đóng gói model 11 lớp
    python -m livelift.nlp.eval_intent --ablation --coverage \
        --du-lieu <bản sao data/labeling> --out-dir <thư mục tạm>  # đo đối chiếu

Đầu ra: ``docs/benchmarks/intent-eval/results.json`` + ``results.md`` +
``chi-tiet-hinh.json`` (số liệu cho hình minh hoạ, không chứa văn bản bình luận).

VÌ SAO KHUNG NÀY TỒN TẠI
------------------------
Con số 0,870 của ``train_intent.py`` đo bằng 5-fold CV trên 320 câu mẫu **do AI
(Claude) soạn** ngày 01/09 — train và test cùng một nguồn, cùng một ngày, cùng
một phân phối. Nó không trả lời được câu hỏi duy nhất đáng hỏi: *trên chat của
một buổi live mà mô hình chưa từng thấy, nó đúng bao nhiêu?* Lần đo 08/09 trả
lời **0,271**, nhưng con số đó **không tái lập được** (tệp nhãn 200 dòng không
được lưu). Khung này đo lại trên lô 393 dòng còn nguyên và công bố **0,211** làm
số "trước" chính thức — một quy trình chạy lại được, thay vì một con số chép
tay trong tài liệu.

NGUỒN NHÃN — ĐỌC TRƯỚC KHI TRÍCH SỐ
-----------------------------------
Nhãn tham chiếu của 393 dòng test do **một tác tử AI (Claude) gán** ngày 09/09
(đính chính 15/09, đối chiếu transcript). **Chưa có nhãn người.** Mọi con số
khung này sinh ra vì vậy là **mức đồng thuận với nhãn tham chiếu do AI gán**,
chưa phải độ chính xác so với con người. Bảng gán mù cho hai người và phép tính
Cohen κ nằm ở ``scripts/gan_mu/`` và ``scripts/tinh_kappa.py``.

BỐN QUYẾT ĐỊNH THIẾT KẾ, VÀ LÝ DO
---------------------------------
1. **Chia theo BUỔI LIVE, không theo dòng.** Bình luận trong một buổi không
   độc lập: cùng người bán, cùng mặt hàng, cùng bảng giá dán lặp lại hàng
   chục lần. Chia ngẫu nhiên theo dòng sẽ để bản sao gần-trùng của cùng một
   câu nằm cả hai bên và thổi phồng điểm. Ở đây dùng **leave-one-session-out**:
   mỗi buổi lần lượt làm tập test, hai buổi kia làm train — không có buổi nào
   xuất hiện ở cả hai phía.
2. **Tách lô test khỏi lô train, và kê khai ai gán.** Lô ``lot2`` (3 buổi,
   nhãn tham chiếu do tác tử AI gán trên bảng xáo trộn không kèm dự đoán) là
   tập test: mỗi fold chấm một buổi, hai buổi còn lại được dùng làm train cho
   C1–C3. Lô ``lot1`` (buổi thứ tư, nhãn do LLM gán) **chỉ dùng để train**.
   Hai lô tách buổi và tách lượt gán nhưng **cùng một họ mô hình (Claude)**,
   nên điểm đo được là "mức đồng ý với nhãn AI", không phải độ chính xác so
   với người — cho tới khi có nhãn người (``scripts/tinh_kappa.py``).
3. **macro-F1 lấy trung bình trên hợp của nhãn tham chiếu và nhãn dự đoán.** Đây là
   mặc định của ``sklearn.f1_score(average="macro")`` và là quy ước đã dùng để
   công bố con số 0,271 (không tái lập được): một lớp mà mô hình bịa ra nhưng
   không hề tồn tại trong nhãn tham chiếu vẫn bị tính F1 = 0 và kéo trung bình
   xuống. Đó chính là cái sai cần phạt. Cột ``macro_f1_support`` (chỉ lấy lớp
   có trong nhãn tham chiếu) được in kèm để người đọc thấy khoảng cách giữa
   hai quy ước.
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

#: Nhãn nguồn của các dòng lô 2 khi chúng được dùng làm TRAIN (C1–C3, v2).
GOLD_SOURCE = "gold_ai"

#: Câu kê khai nguồn nhãn — MỘT chỗ duy nhất, mọi đầu ra (Markdown, JSON, dòng
#: in) lấy từ đây. Sự cố 15/09: câu khai nhãn AI thành nhãn của con người được
#: chép qua nhiều tầng báo cáo mà không tầng nào đối chiếu với transcript.
#: Nghiệm thu K-03 (``09-PHAN-CONG.md``): grep cụm khai sai trên tệp này = 0.
LABEL_PROVENANCE: dict[str, str] = {
    "test": (
        "Nhãn tham chiếu của 393 dòng test do một tác tử AI (Claude) gán ngày "
        "09/09/2026 trên bảng xáo trộn — chưa có nhãn người"
    ),
    "meaning": (
        "mọi con số là mức đồng thuận với nhãn tham chiếu do AI gán, chưa phải "
        "độ chính xác so với con người"
    ),
    "train_llm": "1.800 nhãn train buổi thứ tư do LLM (Claude) gán, không có người duyệt",
    "authored": "320 câu mẫu do AI (Claude) soạn ngày 01/09/2026",
    "data": (
        "Bình luận công khai của các buổi live phát lại (VOD YouTube), lấy qua yt-dlp (dữ liệu "
        "quan sát, không phải API chính thức), đã lọc PII; lọc lại bằng bộ lọc "
        "hiện hành ngày 25/09/2026"
    ),
}

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
    """Một dòng của tập test lô 2, kèm xuất xứ đầy đủ.

    ``label`` là nhãn THAM CHIẾU do tác tử AI (Claude) gán ngày 09/09 — chưa
    có nhãn người (đính chính 15/09). Tên ``GoldRow`` giữ vì tương thích mã.
    """

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
    """Đọc lô 2 (393 dòng, 3 buổi live, bộ 11 lớp) — nhãn do tác tử AI gán.

    Bảng ``to_label.txt`` được xáo trộn và không kèm dự đoán, lớp hay tên phiên
    trước khi gán; người (máy) gán là một tác tử Claude ngày 09/09, **không
    phải người** (đính chính 15/09). Văn bản đã lọc lại PII bằng bộ lọc hiện
    hành ngày 25/09 (``scripts/gan_mu/loc_lai_pii.py``).

    Ba file phải khớp nhau từng ``uid``: ``to_label.txt`` (văn bản đã lọc PII),
    ``gold.txt`` (nhãn tham chiếu do AI gán) và ``key.json`` (buổi live + nhãn
    model dự đoán).
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
    """Bộ 320 câu mẫu do AI (Claude) soạn 01/09. Mặc định dùng bản gán lại 11 lớp.

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
    """Nhãn do LLM (Claude, một mô hình, không người duyệt) sinh trên bình luận
    thật của buổi live thứ tư (lô 1).

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
    """Ma trận nhầm lẫn dạng ``{nhãn tham chiếu: {nhãn đoán: số lượng}}``."""
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
    """Hợp của nhãn tham chiếu và nhãn dự đoán, theo thứ tự chuẩn của bộ nhãn."""
    present = set(y_true) | set(y_pred)
    ordered = [lb for lb in INTENT_LABELS if lb in present]
    ordered += sorted(present - set(INTENT_LABELS))  # nhãn lạ vẫn phải lộ ra
    return ordered


def macro_f1(y_true: list[str], y_pred: list[str], labels: list[str] | None = None) -> float:
    """macro-F1 trên ``labels``; mặc định là hợp nhãn tham chiếu ∪ nhãn dự đoán.

    Mặc định này TRÙNG với ``sklearn.metrics.f1_score(average="macro")`` không
    truyền ``labels`` — và là quy ước đã sinh ra con số 0,271 công bố trong
    ``docs/benchmarks/live-fire-achan.md`` (con số đó không tái lập được). Một
    lớp bị mô hình bịa ra (dự đoán nhưng không tồn tại trong nhãn tham chiếu)
    nhận F1 = 0 và **được tính vào trung bình**: bịa lớp phải bị phạt, không
    được miễn phí.
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


def action_recall(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    """Recall gộp trên các nhãn HÀNH ĐỘNG + KTC95 Wilson.

    Mẫu số là mọi dòng có nhãn tham chiếu thuộc nhóm hành động; tử số là số
    dòng trong đó được đoán ĐÚNG lớp (cùng định nghĩa "đúng" với
    :func:`action_precision`, nên tử số của hai chỉ số luôn bằng nhau).
    Precision một mình che mất cái giá của việc im lặng: một mô hình không bao
    giờ phát cảnh báo có precision "—" và recall 0.
    """
    pairs = [(t, p) for t, p in zip(y_true, y_pred, strict=True) if t in ACTION_LABELS]
    n = len(pairs)
    k = sum(1 for t, p in pairs if t == p)
    if n == 0:
        return {"k": 0, "n": 0, "recall": None, "ci95": None}
    return {"k": k, "n": n, "recall": round(k / n, 4), "ci95": wilson_ci(k, n)}


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

    Không phải trò đùa — trên lô 2 nó đạt accuracy 0,389, CAO HƠN artifact
    đang chạy (B2, 0,338), dù macro-F1 chỉ 0,056 so với 0,211 của B2. Mọi hệ
    thống không vượt được nó trên CẢ HAI chỉ số là hệ thống âm giá trị.
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
                # Nguồn "gold_ai": nhãn tham chiếu lô 2 do tác tử AI gán. Tên cũ
                # "gold_human" (còn trong intent_clf_v2.meta.json) là SAI nguồn.
                TrainRow(r.text, r.label, GOLD_SOURCE, r.session)
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
        dụng. Ở đây tập hiệu chuẩn CHỈ gồm nhãn tham chiếu lô 2 (tác tử AI
        gán) của một buổi live bị giữ lại trong nội bộ tập train.

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
        scores: list[tuple[float, str, str]] = []  # (độ tự tin, nhãn đoán, nhãn tham chiếu)
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


def baseline_systems() -> list[tuple[str, SystemFactory]]:
    """B0–B3: ba baseline bắt buộc + artifact đang chạy.

    Dùng chung với ``scripts/tinh_kappa.py`` để chấm lại theo nhãn người.
    """
    return [
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


def improved_systems() -> list[tuple[str, SystemFactory]]:
    """C1–C3. C2 là đúng cấu hình ``save_best_model`` đóng gói thành v2."""
    return [
        ("C1 · TF-IDF 11 lớp, train = biên soạn(11) + gold 2 buổi", TfidfSystem(use_llm=False)),
        ("C2 · C1 + nhãn LLM trên buổi thứ tư", TfidfSystem()),
        (
            "C3 · C2 + từ chối trả lời, ngưỡng chọn TRONG tập train",
            TfidfSystem(abstain_threshold="auto"),
        ),
    ]


# ---------------------------------------------------------------------------
# 5. Bộ chạy
# ---------------------------------------------------------------------------


def predict_out_of_fold(
    factory: SystemFactory,
    gold: list[GoldRow],
    extra: list[TrainRow],
    *,
    stratum: str | None = None,
) -> tuple[list[tuple[str, list[GoldRow], list[str]]], int]:
    """Dự đoán ngoài-fold: ``([(buổi test, dòng test, dự đoán)], số dòng train bị loại)``.

    MỘT giao thức duy nhất cho mọi phép chấm — ``evaluate_system`` và
    ``scripts/tinh_kappa.py`` (chấm lại theo nhãn người) cùng gọi hàm này, nên
    dự đoán của hai nơi trùng khít nhau; chỉ nhãn dùng để CHẤM là khác.
    """
    folds: list[tuple[str, list[GoldRow], list[str]]] = []
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
        preds = [str(p) for p in predictor([r.text for r in test_rows])]
        folds.append((session, test_rows, preds))
    return folds, n_leaked


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

    folds, n_leaked = predict_out_of_fold(factory, gold, extra, stratum=stratum)
    for session, test_rows, preds in folds:
        truths = [r.label for r in test_rows]
        if collapse_gold_to_6:
            truths = [COLLAPSE_TO_6.get(t, t) for t in truths]
            preds = [COLLAPSE_TO_6.get(p, p) for p in preds]
        per_session[session] = {
            "n": len(test_rows),
            "macro_f1": round(macro_f1(truths, preds), 4),
            "accuracy": round(accuracy(truths, preds), 4),
            "action_precision": action_precision(truths, preds),
            "action_recall": action_recall(truths, preds),
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
        "action_recall": action_recall(y_true, y_pred),
        #: Thang chấm: macro-F1 trên 11 lớp và trên 6 lớp gộp là HAI thang khác
        #: nhau, không được so trực tiếp hay chọn "tốt nhất" lẫn giữa hai thang.
        "scale": "6_lop_gop" if collapse_gold_to_6 else "11_lop",
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
            "action_recall": action_recall(rt, rp),
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
    """Ví dụ THẬT cho từng ô nhầm lẫn ``nhãn tham chiếu -> nhãn đoán``.

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


def _rate(stat: dict[str, Any] | None, key: str) -> str:
    """``0,667 (40/60) [0,541; 0,773]`` hoặc ``—`` khi mẫu số bằng 0."""
    if not stat or not stat.get("n"):
        return "— (0)"
    return f"{_fmt(stat[key])} ({stat['k']}/{stat['n']}) {_ci(stat['ci95'])}"


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Kết quả đánh giá bộ phân loại ý định — sinh tự động")
    add("")
    add(f"*Sinh bởi `python -m livelift.nlp.eval_intent` · {report['generated_at']}*")
    add("")
    prov = LABEL_PROVENANCE
    add(f"> **Nguồn nhãn.** {prov['test']}. Vì vậy {prov['meaning']}.")
    add(f"> Nhãn train bổ sung kê khai riêng ở mục 1: {prov['authored']}; {prov['train_llm']}.")
    add(">")
    add(f"> **Nguồn dữ liệu.** {prov['data']}.")
    if report.get("du_lieu", "data/labeling") != "data/labeling":
        add(">")
        add(
            f"> ⚠️ **Lần chạy ĐỐI CHIẾU trên bản sao `{report['du_lieu']}`** — không phải số "
            "công bố; câu về lọc lại PII ở trên có thể không đúng với bản sao này."
        )
    add(">")
    add("> Chia **leave-one-session-out theo buổi live** (không buổi nào nằm cả")
    add("> train lẫn test).")
    b2 = report.get("b2_classifier_info")
    if b2:
        add(">")
        add(
            f"> B2 (artifact đang chạy) được chấm với bộ `{b2.get('backend', '?')}`"
            f" (`{b2.get('model_file') or '—'}`), scikit-learn {b2.get('sklearn_version') or '?'}."
        )
    add("")
    inv = report["inventory"]
    add("## 1. Kiểm kê dữ liệu")
    add("")
    add("| Nguồn | Số dòng | Ghi chú |")
    add("|---|---:|---|")
    for item in inv["sources"]:
        add(f"| {item['name']} | {item['n']} | {item['note']} |")
    add("")
    add("Phân bố nhãn của tập test (nhãn tham chiếu do tác tử AI gán):")
    add("")
    add("| Lớp | Số dòng | Tỷ lệ |")
    add("|---|---:|---:|")
    total = sum(inv["gold_label_counts"].values())
    for lb, n in sorted(inv["gold_label_counts"].items(), key=lambda kv: -kv[1]):
        add(f"| `{lb}` | {n} | {n / total:.1%} |".replace(".", ",").replace(",1%", ",1%"))
    add("")
    add("| Buổi live | Dòng có nhãn | Tỷ lệ nền nhãn hành động (tầng ngẫu nhiên, nhãn AI) |")
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
            "(chỉ lớp có trong nhãn tham chiếu) | Accuracy | Precision nhãn hành động | "
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

    action_rows = [r for t in report["tables"][:2] for r in t["rows"]]
    if action_rows:
        add("## Nhãn hành động: precision VÀ recall")
        add("")
        add(
            "Nhãn hành động = `" + "`, `".join(ACTION_LABELS) + "`. Precision: trong các lần "
            "hệ thống gắn nhãn hành động, bao nhiêu lần đúng lớp. Recall: trong các dòng có "
            "nhãn tham chiếu thuộc nhóm hành động, bao nhiêu dòng được đoán đúng lớp. KTC95 "
            "Wilson. Tầng `predicted` (193 dòng) được rút theo nhãn v1 dự đoán nên số trên "
            "393 dòng KHÔNG phải con số vận hành — đọc cột tầng ngẫu nhiên."
        )
        add("")
        add(
            "| Hệ thống | Precision (393) | Recall (393) | Precision tầng ngẫu nhiên (200) "
            "| Recall tầng ngẫu nhiên (200) |"
        )
        add("|---|---|---|---|---|")
        for r in action_rows:
            rnd = r.get("random_stratum", {})
            add(
                f"| {r['name']} | {_rate(r['action_precision'], 'precision')} | "
                f"{_rate(r.get('action_recall'), 'recall')} | "
                f"{_rate(rnd.get('action_precision'), 'precision')} | "
                f"{_rate(rnd.get('action_recall'), 'recall')} |"
            )
        add("")

    best = report.get("best")
    if best:
        add("## F1 từng lớp và ma trận nhầm lẫn — cấu hình đóng gói thành v2")
        add("")
        add(f"Hệ thống: **{best['name']}**")
        add("")
        add(report.get("best_rule", ""))
        add("")
        add("| Lớp | P | R | F1 | Nhãn tham chiếu | Lần dự đoán |")
        add("|---|---:|---:|---:|---:|---:|")
        for lb, s in best["per_class"].items():
            add(
                f"| `{lb}` | {_fmt(s['precision'])} | {_fmt(s['recall'])} | "
                f"**{_fmt(s['f1'])}** | {s['support']} | {s['n_pred']} |"
            )
        add("")
        add("Ma trận nhầm lẫn (hàng = nhãn tham chiếu do tác tử AI gán, cột = nhãn đoán):")
        add("")
        cols = list(best["per_class"].keys())
        add("| tham chiếu \\ đoán | " + " | ".join(f"`{c}`" for c in cols) + " |")
        add("|---" * (len(cols) + 1) + "|")
        for t in cols:
            row = best["confusion"].get(t, {})
            if not row:
                continue
            cells = [str(row.get(c, 0)) if row.get(c) else "·" for c in cols]
            add(f"| `{t}` | " + " | ".join(cells) + " |")
        add("")
    return "\n".join(lines) + "\n"


BEST_RULE = (
    "Chọn TRƯỚC, không chọn theo điểm trên tập test: mục này trình bày C2 — đúng cấu "
    "hình được đóng gói thành `intent_clf_v2.joblib`. Dòng ablation nào có điểm cao "
    'hơn thì đọc kèm khoảng tin cậy ở mục 4; lấy nó làm "tốt nhất" là chọn trên '
    "chính tập test. A7/A8 chấm trên thang 6 lớp gộp, không so được với thang 11 lớp."
)


def select_reported_system(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Hệ thống được trình bày chi tiết (F1 từng lớp, ma trận nhầm lẫn).

    Trước 25/09 chỗ này là ``max(macro_f1)`` trên MỌI dòng, kể cả A8 — dòng chấm
    trên thang 6 lớp gộp. Kết quả: mục "hệ thống tốt nhất" của ``results.md``
    trình bày A8 (0,609 trên thang 6 lớp) trong khi tài liệu trích F1 từng lớp
    của C2. Quy tắc mới: ưu tiên dòng được đánh dấu ``packaged_as`` (cấu hình
    thật sự đóng gói); không có thì lấy điểm cao nhất trong CÙNG thang 11 lớp.
    """
    if not rows:
        raise ValueError("không có dòng kết quả nào để chọn")
    packaged = [r for r in rows if r.get("packaged_as")]
    if packaged:
        return packaged[0]
    same_scale = [r for r in rows if r.get("scale", "11_lop") == "11_lop"]
    return max(same_scale or rows, key=lambda r: r["macro_f1"])


def _shipped_classifier_info() -> dict[str, Any]:
    """``intent.classifier_info()`` + bản scikit-learn đang chạy, không bao giờ ném lỗi."""
    info: dict[str, Any] = {}
    try:
        from livelift.nlp.intent import classifier_info

        info.update(classifier_info())
    except Exception as exc:  # noqa: BLE001 — chỉ là thông tin xuất xứ
        info["error"] = type(exc).__name__
    try:
        import sklearn

        info["sklearn_version"] = sklearn.__version__
    except Exception:  # noqa: BLE001
        info["sklearn_version"] = None
    return info


def _row_code(name: str) -> str:
    """``"C2 · C1 + nhãn LLM…"`` -> ``"C2"``."""
    return name.split(" ", 1)[0]


def _action_stats_subset(
    predictions: list[Any], *, session: str | None = None, stratum: str | None = None
) -> dict[str, Any]:
    """Precision + recall nhãn hành động trên một lát của ``predictions``."""
    picked = [
        (t, p)
        for s, st, t, p in predictions
        if (session is None or s == session) and (stratum is None or st == stratum)
    ]
    y_true = [t for t, _ in picked]
    y_pred = [p for _, p in picked]
    return {
        "n": len(picked),
        "precision": action_precision(y_true, y_pred),
        "recall": action_recall(y_true, y_pred),
    }


def figure_details(report: dict[str, Any]) -> dict[str, Any]:
    """Số liệu cho hình minh hoạ — KHÔNG chứa văn bản bình luận nào.

    Gồm: ma trận nhầm lẫn 11×11 của hệ thống được trình bày (C2/v2) theo nhãn
    tham chiếu; macro-F1 + KTC bootstrap của mọi dòng (B0…C3, A0…A8); precision
    VÀ recall nhãn hành động; precision theo từng buổi so với tỷ lệ nền nhãn
    hành động của buổi. Mọi số đọc lại từ ``report`` — cùng một lần chạy.
    """
    best = report.get("best") or select_reported_system(
        [r for t in report["tables"] for r in t["rows"]]
    )
    labels = list(INTENT_LABELS)
    conf = best["confusion"]
    matrix = [[int(conf.get(t, {}).get(p, 0)) for p in labels] for t in labels]

    rows_out = []
    action_out = []
    for table in report["tables"]:
        for r in table["rows"]:
            rnd = r.get("random_stratum", {})
            rows_out.append(
                {
                    "ma": _row_code(r["name"]),
                    "ten": r["name"],
                    "bang": table["title"],
                    "thang": r.get("scale", "11_lop"),
                    "n_test": r["n_test"],
                    "macro_f1": r["macro_f1"],
                    "macro_f1_ktc95_bootstrap": r["macro_f1_ci95"],
                    "macro_f1_chi_lop_co_trong_nhan_tham_chieu": r["macro_f1_support_only"],
                    "accuracy": r["accuracy"],
                    "tang_ngau_nhien": {
                        "n": rnd.get("n"),
                        "macro_f1": rnd.get("macro_f1"),
                        "macro_f1_ktc95_bootstrap": rnd.get("macro_f1_ci95"),
                    },
                    "macro_f1_theo_buoi": {
                        s: d["macro_f1"] for s, d in sorted(r["per_session"].items())
                    },
                }
            )
            action_out.append(
                {
                    "ma": _row_code(r["name"]),
                    "thang": r.get("scale", "11_lop"),
                    "precision": r["action_precision"],
                    "recall": r.get("action_recall"),
                    "tang_ngau_nhien": {
                        "precision": rnd.get("action_precision"),
                        "recall": rnd.get("action_recall"),
                    },
                }
            )

    # Precision theo buổi: chỉ bảng baseline + sau cải tiến (cùng thang 11 lớp).
    compare = [r for t in report["tables"][:2] for r in t["rows"]]
    per_session = []
    for s, inv in sorted(report["inventory"]["per_session"].items()):
        systems = {}
        for r in compare:
            preds = r.get("predictions", [])
            systems[_row_code(r["name"])] = {
                "toan_bo_dong_cua_buoi": _action_stats_subset(preds, session=s),
                "tang_ngau_nhien": _action_stats_subset(preds, session=s, stratum="random"),
            }
        per_session.append(
            {
                "buoi": s,
                "n_dong": inv["n"],
                "ty_le_nen_nhan_hanh_dong_tang_ngau_nhien": {
                    "k": inv.get("action_k_random"),
                    "n": inv.get("n_random"),
                    "ty_le": inv.get("action_rate_random"),
                    "ktc95_wilson": inv.get("action_rate_random_ci95"),
                },
                "he_thong": systems,
            }
        )

    return {
        "mo_ta": (
            "Số liệu cho hình minh hoạ bộ phân loại ý định. Sinh tự động cùng results.json; "
            "không chứa văn bản bình luận."
        ),
        "lenh_tai_lap": "python -m livelift.nlp.eval_intent --ablation --coverage",
        "generated_at": report.get("generated_at"),
        "seed": report.get("seed"),
        "n_bootstrap": report.get("n_bootstrap"),
        "nguon_nhan": dict(LABEL_PROVENANCE),
        "nhan_hanh_dong": list(ACTION_LABELS),
        "dinh_nghia": {
            "precision_nhan_hanh_dong": (
                "trong các dòng được đoán là một nhãn hành động, tỷ lệ đoán đúng lớp"
            ),
            "recall_nhan_hanh_dong": (
                "trong các dòng có nhãn tham chiếu thuộc nhóm hành động, tỷ lệ đoán đúng lớp"
            ),
            "ty_le_nen": (
                "tỷ lệ dòng có nhãn tham chiếu thuộc nhóm hành động trên tầng mẫu ngẫu nhiên "
                "của buổi (ước lượng không chệch cho buổi đó, theo nhãn AI)"
            ),
            "tang_ngau_nhien": (
                "200 dòng rút ngẫu nhiên đơn giản; 193 dòng còn lại rút theo nhãn v1 dự đoán "
                "nên giàu nhãn hành động một cách nhân tạo"
            ),
        },
        "ma_tran_nham_lan": {
            "he_thong": best["name"],
            "quy_tac_chon": report.get("best_rule", BEST_RULE),
            "hang": "nhãn tham chiếu (tác tử AI gán)",
            "cot": "nhãn mô hình đoán",
            "nhan": labels,
            "ma_tran": matrix,
            "tong_hang": [sum(row) for row in matrix],
            "tong_cot": [sum(col) for col in zip(*matrix, strict=True)],
        },
        "macro_f1": rows_out,
        "nhan_hanh_dong_precision_recall": action_out,
        "precision_theo_buoi_va_ty_le_nen": per_session,
        "duong_do_phu": report.get("coverage"),
    }


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
            # Dạng số của cùng tỷ lệ nền — cho hình "precision theo buổi".
            "action_k_random": k,
            "action_rate_random": round(k / len(rand), 4) if rand else None,
            "action_rate_random_ci95": wilson_ci(k, len(rand)) if rand else None,
        }
    sources = [
        {
            "name": (
                "`data/labeling/lot2-da-nguon-10-09` — nhãn do tác tử AI gán, "
                "bảng xáo trộn, 11 lớp (chưa có nhãn người)"
            ),
            "n": len(gold),
            "note": (
                f"{len({r.session for r in gold})} buổi live · TEST theo leave-one-session-out; "
                "C1–C3 dùng hai buổi còn lại của mỗi fold làm train"
            ),
        }
    ]
    by_source = Counter(r.source for r in extra)
    note = {
        "authored_6": "câu mẫu do AI (Claude) soạn 01/09, bộ 6 lớp gốc — CHỈ train",
        "authored_11": (
            "câu mẫu do AI (Claude) soạn 01/09, gán lại 11 lớp bằng bảng trong mã — CHỈ train"
        ),
        "llm_lot1": (
            "bình luận thật buổi thứ tư, nhãn do LLM (Claude) gán, không người duyệt — CHỈ train"
        ),
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
    parser.add_argument(
        "--du-lieu",
        metavar="DIR",
        help=(
            "thư mục gốc chứa lot2-da-nguon-10-09/ và lot1-achan-b519f75c/ (mặc định "
            "data/labeling). Dùng để đo lại trên một bản sao, ví dụ bản sao lưu TRƯỚC "
            "khi lọc lại PII 25/09 — tách phần số đổi do dữ liệu khỏi phần do mã"
        ),
    )
    args = parser.parse_args(argv)

    if args.du_lieu:
        # Kết quả đo trên bản sao KHÔNG được đè số công bố, và không được đóng
        # gói thành artifact — nó chỉ để đối chiếu.
        if Path(args.out_dir).resolve() == OUT_DIR.resolve():
            parser.error("--du-lieu cần --out-dir riêng (không ghi đè kết quả công bố)")
        if args.save_model:
            parser.error("--du-lieu không đi cùng --save-model")
        root = Path(args.du_lieu)
        gold = load_gold_lot2(root / GOLD_DIR.name)
        extra = load_authored() + load_llm_lot(root / LLM_LOT_DIR.name / "train_llm.jsonl")
    else:
        gold = load_gold_lot2()
        extra = load_authored() + load_llm_lot()
    inventory = build_inventory(gold, extra)

    print(
        f"test lô 2 (nhãn tác tử AI gán, chưa có nhãn người): {len(gold)} dòng · "
        f"{len(inventory['gold_sessions'])} buổi live"
    )
    print(f"train bổ sung   : {len(extra)} dòng · {dict(Counter(r.source for r in extra))}")

    tables: list[dict[str, Any]] = []

    baselines = baseline_systems()
    rows = [evaluate_system(n, f, gold, extra) for n, f in baselines]
    tables.append(
        {
            "title": "2. Baseline trên chat thật (test = buổi live mô hình chưa từng thấy)",
            "note": (
                "Ba baseline bắt buộc + artifact đang chạy. Tập test = 393 dòng có nhãn "
                "tham chiếu do tác tử AI gán, gộp từ ba fold leave-one-session-out."
            ),
            "rows": rows,
        }
    )

    improved = improved_systems()
    rows_improved = [evaluate_system(n, f, gold, extra) for n, f in improved]
    # C2 là ĐÚNG cấu hình mà ``save_best_model`` đóng gói thành v2
    # (``TfidfSystem()`` mặc định, mọi nguồn dữ liệu, không abstain).
    rows_improved[1]["packaged_as"] = MODEL_V2.name
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
        "label_provenance": LABEL_PROVENANCE,
        "du_lieu": str(Path(args.du_lieu)) if args.du_lieu else "data/labeling",
        # B2 chấm "artifact đang chạy" — phải ghi lại bộ nào THẬT SỰ trả lời
        # (lệch sklearn làm artifact rơi âm thầm về bộ từ khoá, kiểm toán 25/09).
        "b2_classifier_info": _shipped_classifier_info(),
        "inventory": inventory,
        "tables": tables,
    }

    if args.ablation:
        report["tables"].append({"title": "4. Ablation", "rows": run_ablation(gold, extra)})
    if args.coverage:
        report["coverage"] = coverage_curve(gold, extra, [0.0, 0.3, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8])

    all_rows = [r for t in report["tables"] for r in t["rows"]]
    report["best"] = select_reported_system(all_rows)
    report["best_rule"] = BEST_RULE

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # `predictions` chứa văn bản-suy-ra-được của bình luận thật; giữ trong JSON
    # cho phân tích lỗi nhưng KHÔNG in ra Markdown công khai.
    (out_dir / "results.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "results.md").write_text(render_markdown(report), encoding="utf-8")
    (out_dir / "chi-tiet-hinh.json").write_text(
        json.dumps(figure_details(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"\nđã ghi: {out_dir / 'results.json'}")
    print(f"đã ghi: {out_dir / 'results.md'}")
    print(f"đã ghi: {out_dir / 'chi-tiet-hinh.json'}")

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
    nhãn (chúng đổi cả không gian nhãn nên phải chấm trên nhãn tham chiếu đã gộp về
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
        "eval": (
            "leave-one-session-out trên data/labeling/lot2-da-nguon-10-09 "
            "(nhãn tham chiếu do tác tử AI gán, chưa có nhãn người)"
        ),
        "label_provenance": dict(LABEL_PROVENANCE),
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
