"""Khung đánh giá ý định: chuẩn hoá, chỉ số, chia theo buổi live, rào rò rỉ.

Vì sao những test này tồn tại: bộ phân loại từng công bố macro-F1 0,870 trên 320
câu mẫu do AI (Claude) soạn rồi rơi xuống 0,271 trên chat thật (con số 08/09 không
tái lập được; số đo lại là 0,211). Nguyên nhân không nằm ở mô hình mà ở **cách
đo**. Nên phần được khoá bằng test ở đây là chính cái khung đo: công thức macro-F1
(đúng quy ước đã công bố), phép chia không cho một buổi live nằm cả hai phía, rào
chắn loại dòng train trùng khít dòng test — và từ 25/09, **câu kê khai nguồn nhãn**
(nhãn tham chiếu do tác tử AI gán, chưa có nhãn người) cùng bộ công cụ gán mù cho
người: lọc lại PII, sinh bảng gán mù, tính Cohen κ.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from livelift.nlp import eval_intent as ev
from livelift.nlp.labels import INTENT_LABELS
from livelift.nlp.normalize import (
    STYLE_FEATURE_NAMES,
    TEENCODE,
    collapse_elongation,
    normalize_text,
    style_features,
)

REPO = Path(ev.__file__).resolve().parents[3]
GOLD_AVAILABLE = (ev.GOLD_DIR / "gold.txt").exists()
gold_only = pytest.mark.skipif(
    not GOLD_AVAILABLE,
    reason="lô nhãn thật ngoài git (chính sách PII) — sinh lại: data/labeling/README.md",
)


# ---------------------------------------------------------------------------
# Chuẩn hoá văn bản
# ---------------------------------------------------------------------------


def test_nfkc_folds_fullwidth_characters():
    """Chat dán từ điện thoại hay lẫn ký tự full-width; không gấp về dạng chuẩn
    thì ``ｇｉá`` và ``giá`` thành hai từ vựng khác nhau."""
    assert "gia" in normalize_text("ＧＩＡ bao nhiêu")


def test_teencode_expands_only_whole_tokens():
    out = normalize_text("gia bn v shop")
    assert "bao nhiêu" in out
    # "shop" không nằm trong từ điển và phải giữ nguyên
    assert "shop" in out


def test_teencode_can_be_switched_off_for_ablation():
    """Bảng ablation cần tắt được từng bước — nếu không thì con số đóng góp của
    bước đó là con số bịa."""
    assert "bao nhiêu" not in normalize_text("gia bn v", teencode=False)


def test_teencode_table_has_no_single_ambiguous_pronouns():
    """``m``/``e``/``t``/``s`` là đại từ đa nghĩa cao tần — giãn sai một token
    như vậy hại hơn không giãn. Khoá lại bằng test để không ai thêm vào."""
    assert not ({"m", "e", "t", "s", "a", "c"} & set(TEENCODE))


def test_elongation_collapses_to_two_characters():
    assert collapse_elongation("đẹppppp") == "đẹpp"
    assert collapse_elongation("kkkkkkk") == "kk"
    assert collapse_elongation("hay!!!!!") == "hay!!"


def test_pii_placeholder_survives_as_one_token():
    """``[ĐỊA CHỈ]`` là tín hiệu mạnh cho hoi_daily/van_chuyen. Nếu chuẩn hoá
    tách nó thành "địa" + "chỉ" thì char n-gram trộn nó với chữ thường."""
    out = normalize_text("mở đại lý ở [ĐỊA CHỈ] được không")
    assert "piiđịachỉ" in out
    assert "[" not in out


def test_normalize_is_idempotent_enough_to_be_a_pipeline_step():
    once = normalize_text("KOOOO   BIẾTTT 😅😅")
    assert normalize_text(once) == once


def test_normalize_never_returns_none_or_crashes_on_junk():
    for junk in ("", "   ", "🤣🤣🤣", "[SĐT]", "0909090909", "||||"):
        assert isinstance(normalize_text(junk), str)


# ---------------------------------------------------------------------------
# Đặc trưng phong cách — mô hình người nói rẻ tiền
# ---------------------------------------------------------------------------


def test_style_feature_vector_matches_declared_names():
    assert len(style_features("gì đó")) == len(STYLE_FEATURE_NAMES)


def test_shop_price_sheet_is_flagged_and_customer_question_is_not():
    """Cơ chế sai (c) của live-fire 08/09: bảng giá mod dán bị tính là khách
    hỏi giá. Đặc trưng này là chỗ duy nhất trong pipeline phân biệt được."""
    i = STYLE_FEATURE_NAMES.index("is_shouted_pricesheet")
    sheet = "TRÀ SÂM NGỌC LINH || GIÁ 500K (HỘP 15 GÓI) || GIÁ 639K (HỘP 20 GÓI)"
    assert style_features(sheet)[i] == 1.0
    assert style_features("trà bao nhiêu tiền một hộp em ơi")[i] == 0.0
    assert style_features("chốt cho em 1 hộp nha")[i] == 0.0


def test_caps_ratio_separates_shouting_from_normal_text():
    i = STYLE_FEATURE_NAMES.index("caps_ratio")
    assert style_features("EM CHAO CA NHA")[i] > 0.9
    assert style_features("em chào cả nhà")[i] == 0.0


# ---------------------------------------------------------------------------
# Chỉ số
# ---------------------------------------------------------------------------


def test_macro_f1_matches_sklearn_default_convention():
    """Quy ước công bố (0,271 trong live-fire 08/09) = macro trên HỢP của nhãn
    thật và nhãn dự đoán, tức mặc định của sklearn. Nếu công thức ở đây lệch
    khỏi mặc định đó thì mọi so sánh với con số cũ trở nên vô nghĩa."""
    sk = pytest.importorskip("sklearn.metrics")
    y_true = ["khac"] * 8 + ["hoi_gia", "chot_don"]
    y_pred = ["khac"] * 6 + ["che_dat", "van_chuyen", "hoi_gia", "khac"]
    assert ev.macro_f1(y_true, y_pred) == pytest.approx(
        sk.f1_score(y_true, y_pred, average="macro", zero_division=0), abs=1e-9
    )


def test_macro_f1_punishes_invented_classes():
    """Bịa một lớp không hề có trong nhãn thật phải bị phạt, không được miễn
    phí — đó chính là cái mô hình cũ làm trên chat thật."""
    y_true = ["khac"] * 10
    clean = ev.macro_f1(y_true, ["khac"] * 10)
    invented = ev.macro_f1(y_true, ["khac"] * 9 + ["chot_don"])
    assert clean == 1.0
    assert invented < clean


def test_macro_f1_support_only_is_the_gentler_convention():
    y_true = ["khac"] * 10
    y_pred = ["khac"] * 9 + ["chot_don"]
    labels_support = ["khac"]
    assert ev.macro_f1(y_true, y_pred, labels_support) > ev.macro_f1(y_true, y_pred)


def test_per_class_prf_counts_support_and_predictions():
    stats = ev.per_class_prf(["a", "a", "b"], ["a", "b", "b"], ["a", "b"])
    assert stats["a"]["support"] == 2
    assert stats["a"]["n_pred"] == 1
    assert stats["a"]["precision"] == 1.0
    assert stats["a"]["recall"] == 0.5


def test_confusion_matrix_rows_sum_to_support():
    matrix = ev.confusion(["a", "a", "b"], ["a", "b", "b"])
    assert sum(matrix["a"].values()) == 2
    assert matrix["a"] == {"a": 1, "b": 1}


def test_wilson_interval_stays_inside_zero_one_at_the_extremes():
    """Wald cho cận âm khi tỷ lệ sát 0 — đúng tình huống của bộ này (1/200)."""
    lo, hi = ev.wilson_ci(0, 200)
    assert lo == 0.0
    assert 0.0 < hi < 0.05
    lo, hi = ev.wilson_ci(200, 200)
    assert hi == 1.0


def test_bootstrap_interval_brackets_the_point_estimate():
    y_true = ["khac"] * 150 + ["hoi_gia"] * 30 + ["chot_don"] * 20
    y_pred = ["khac"] * 140 + ["hoi_gia"] * 40 + ["chot_don"] * 20
    point = ev.macro_f1(y_true, y_pred)
    lo, hi = ev.bootstrap_macro_f1(y_true, y_pred, n=400, seed=1)
    assert lo <= point <= hi


def test_bootstrap_is_deterministic_for_a_given_seed():
    y_true = ["khac"] * 40 + ["hoi_gia"] * 10
    y_pred = ["khac"] * 45 + ["hoi_gia"] * 5
    first = ev.bootstrap_macro_f1(y_true, y_pred, n=200, seed=7)
    assert first == ev.bootstrap_macro_f1(y_true, y_pred, n=200, seed=7)


def test_action_precision_only_counts_action_predictions():
    y_true = ["khac", "hoi_gia", "cam_on_khen"]
    y_pred = ["chot_don", "hoi_gia", "chao_hoi"]
    result = ev.action_precision(y_true, y_pred)
    assert result["n"] == 2  # chao_hoi KHÔNG phải nhãn hành động
    assert result["k"] == 1


# ---------------------------------------------------------------------------
# Chia theo buổi live + rào chắn rò rỉ
# ---------------------------------------------------------------------------


def _row(uid: str, text: str, label: str, session: str, stratum: str = "random") -> ev.GoldRow:
    return ev.GoldRow(uid=uid, text=text, label=label, session=session, stratum=stratum)


def test_leave_one_session_out_never_puts_a_session_on_both_sides():
    rows = [
        _row("1", "a", "khac", "S1"),
        _row("2", "b", "khac", "S2"),
        _row("3", "c", "hoi_gia", "S2"),
        _row("4", "d", "khac", "S3"),
    ]
    folds = ev.leave_one_session_out(rows)
    assert len(folds) == 3
    for session, train, test in folds:
        assert {r.session for r in test} == {session}
        assert session not in {r.session for r in train}
    assert sum(len(test) for _, _, test in folds) == len(rows)


def test_dedup_key_ignores_case_punctuation_and_spacing():
    assert ev.dedup_key("Chào cả nhà!!!") == ev.dedup_key("chào   cả nhà")
    assert ev.dedup_key("GIÁ 500K!!") == ev.dedup_key("giá  500k")
    # …nhưng KHÔNG gộp hai câu khác nhau: rào chắn rò rỉ mà quá tay thì nó xoá
    # mất dữ liệu train hợp lệ.
    assert ev.dedup_key("giá 500k") != ev.dedup_key("giá 600k")


def test_training_rows_that_duplicate_a_test_row_are_dropped_and_counted():
    """Chia theo buổi live chặn rò rỉ theo phiên, KHÔNG chặn rò rỉ theo văn bản:
    cùng người bán dán cùng bảng giá ở nhiều buổi. Rào chắn phải loại và ĐẾM."""
    pytest.importorskip("sklearn")
    gold = [
        _row("1", "chào cả nhà", "chao_hoi", "S1"),
        _row("2", "giá bao nhiêu", "hoi_gia", "S1"),
        _row("3", "chào cả nhà!!!", "chao_hoi", "S2"),
        _row("4", "chốt 1 cái", "chot_don", "S2"),
    ]
    extra = [
        ev.TrainRow("Chào cả nhà", "chao_hoi", "llm_lot1"),
        ev.TrainRow("ship bao lâu", "van_chuyen", "llm_lot1"),
    ]
    result = ev.evaluate_system("majority", ev.system_majority, gold, extra)
    # "chào cả nhà" xuất hiện ở CẢ HAI buổi + trong lô extra -> bị loại ở cả 2 fold
    assert result["n_train_rows_dropped_as_leak"] >= 2


def test_evaluate_system_reports_the_random_stratum_separately():
    """Tầng `predicted` được rút theo nhãn model đoán nên giàu lớp hành động một
    cách nhân tạo; con số vận hành phải đọc ở tầng `random`."""
    gold = [
        _row("1", "a", "khac", "S1", "random"),
        _row("2", "b", "hoi_gia", "S1", "predicted"),
        _row("3", "c", "khac", "S2", "random"),
        _row("4", "d", "chot_don", "S2", "predicted"),
    ]
    result = ev.evaluate_system("majority", ev.system_majority, gold, [])
    assert result["n_test"] == 4
    assert result["random_stratum"]["n"] == 2
    assert result["random_stratum"]["accuracy"] == 1.0


def test_collapse_to_six_maps_every_new_class_back_to_khac():
    """Và bảng ablation phải chấm cả bản đang chạy (v1, B2) trên thang 6 lớp gộp.

    Hội đồng thử 25/09: con số tiêu đề 0,211 → 0,542 chấm trên thang 11 lớp, trong
    đó v1 không thể đoán năm lớp mới (bốn lớp có trong tập kiểm tra, 171/393 dòng).
    Không có dòng B2 cùng thang 6 lớp thì hồ sơ không tách được phần "mở rộng bộ
    nhãn" khỏi phần "mô hình tốt hơn".
    """
    assert set(ev.COLLAPSE_TO_6) == {
        "chao_hoi",
        "cam_on_khen",
        "hoi_sanpham",
        "hoi_daily",
        "bao_gia_shop",
    }
    assert set(ev.COLLAPSE_TO_6.values()) == {"khac"}

    specs = ev.ablation_specs()
    thang_6 = [(ten, he) for ten, he, kw in specs if kw.get("collapse_gold_to_6")]
    assert any(he is ev.system_shipped for _, he in thang_6), (
        "bảng ablation thiếu dòng v1 đang chạy (B2) chấm trên thang 6 lớp gộp"
    )
    for ten, _ in thang_6:
        assert "6" in ten, f"dòng chấm trên thang 6 lớp phải ghi rõ thang trong tên: {ten!r}"
    ma = [ten.split(" · ")[0] for ten, _, _ in specs]
    assert len(ma) == len(set(ma)), f"trùng mã dòng ablation: {ma}"


def test_action_labels_exclude_the_social_classes():
    """Nhầm ``chao_hoi`` thành ``cam_on_khen`` không làm ai mất đơn; gắn nhầm
    ``chot_don`` thì trung control đuổi theo một khách không tồn tại."""
    assert set(ev.ACTION_LABELS).isdisjoint(ev.COLLAPSE_TO_6)
    assert "khac" not in ev.ACTION_LABELS


# ---------------------------------------------------------------------------
# Món nợ nhãn đã trả: bộ biên soạn gán lại theo 11 lớp
# ---------------------------------------------------------------------------


def _load(path: Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


def test_relabelled_authored_dataset_exists_and_has_the_same_texts():
    assert ev.AUTHORED_V2.exists(), "chạy: python scripts/gan_lai_nhan_11.py"
    v1, v2 = _load(ev.AUTHORED_V1), _load(ev.AUTHORED_V2)
    assert len(v1) == len(v2)
    assert [r["text"] for r in v1] == [r["text"] for r in v2]


def test_relabelled_dataset_uses_only_guideline_labels():
    for row in _load(ev.AUTHORED_V2):
        assert row["label"] in INTENT_LABELS


def test_the_label_debt_is_actually_paid():
    """Ba dòng này được nêu đích danh trong ``docs/benchmarks/intent-classifier.md``
    §"Nợ bắt buộc trả trước khi huấn luyện lại" như bằng chứng bộ 6 lớp mâu
    thuẫn với guideline 11 lớp. Nếu chúng còn mang nhãn ``khac`` thì món nợ
    chưa trả, bất kể file mới đã tồn tại hay chưa."""
    by_text = {r["text"]: r["label"] for r in _load(ev.AUTHORED_V2)}
    assert by_text["chào shop buổi tối"] == "chao_hoi"
    assert by_text["chị chủ xinh quá"] == "cam_on_khen"
    assert by_text["hạn sử dụng tới khi nào ạ"] == "hoi_sanpham"


def test_relabel_table_is_reproducible_from_the_script():
    """File dữ liệu phải là kết quả của bảng trong script, không phải file chép
    tay: ai sửa nhãn thì phải sửa bảng, và bảng thì review được."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "gan_lai_nhan_11", REPO / "scripts" / "gan_lai_nhan_11.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected, _ = module.relabel(_load(ev.AUTHORED_V1))
    assert expected == _load(ev.AUTHORED_V2)


def test_authored_dataset_cannot_teach_two_classes_and_says_so():
    """``hoi_daily`` và ``bao_gia_shop`` không có mẫu biên soạn nào — chúng chỉ
    học được từ dữ liệu thật. Test này khoá sự thật đó lại để tài liệu không
    lặng lẽ tuyên bố 11 lớp đều được bộ biên soạn dạy."""
    labels = {r["label"] for r in _load(ev.AUTHORED_V2)}
    assert "hoi_daily" not in labels
    assert "bao_gia_shop" not in labels


# ---------------------------------------------------------------------------
# Dữ liệu thật (ngoài git — bỏ qua khi vắng)
# ---------------------------------------------------------------------------


@gold_only
def test_real_gold_lot_loads_with_full_provenance():
    rows = ev.load_gold_lot2()
    assert len(rows) == 393
    assert len({r.session for r in rows}) == 3
    assert sum(r.stratum == "random" for r in rows) == 200
    for r in rows:
        assert r.label in INTENT_LABELS
        assert r.text.strip()


@gold_only
def test_every_gold_session_appears_exactly_once_as_a_test_fold():
    rows = ev.load_gold_lot2()
    folds = ev.leave_one_session_out(rows)
    assert len(folds) == 3
    assert sum(len(test) for _, _, test in folds) == len(rows)


@pytest.mark.slow
@gold_only
def test_upgraded_model_beats_the_shipped_one_on_real_chat():
    """Cổng hồi quy của bản nâng cấp. Ngưỡng đặt ở +0,20 macro-F1 so với
    artifact đang chạy: khoảng cách đo được là ~+0,35, nên một bản sụt nhẹ vẫn
    qua cổng còn một bản hỏng thật thì trượt."""
    pytest.importorskip("sklearn")
    gold = ev.load_gold_lot2()
    extra = ev.load_authored() + ev.load_llm_lot()
    shipped = ev.evaluate_system("shipped", ev.system_shipped, gold, extra)
    upgraded = ev.evaluate_system("v2", ev.TfidfSystem(), gold, extra)
    assert upgraded["macro_f1"] >= shipped["macro_f1"] + 0.20
    assert (
        upgraded["macro_f1"]
        > ev.evaluate_system("majority", ev.system_majority, gold, extra)["macro_f1"]
    )


# ---------------------------------------------------------------------------
# Artifact nâng cấp: đóng gói được, nạp lại được, bật được bằng biến môi trường
# ---------------------------------------------------------------------------

V2_AVAILABLE = ev.MODEL_V2.exists()
v2_only = pytest.mark.skipif(
    not V2_AVAILABLE,
    reason="chưa có artifact v2 — chạy: python -m livelift.nlp.eval_intent --save-model",
)


@v2_only
def test_v2_artifact_loads_in_a_clean_process():
    """Sự cố 14/09: artifact đầu tiên được đóng gói khi script chạy dưới tên
    ``__main__``, nên joblib ghi tham chiếu ``__main__._normalize_all`` và
    KHÔNG tiến trình nào khác nạp lại được. Lỗi này không lộ ra trong chính
    tiến trình huấn luyện — chỉ một lần nạp từ ngoài mới bắt được nó."""
    joblib = pytest.importorskip("joblib")
    pipe = joblib.load(ev.MODEL_V2)
    assert set(map(str, pipe.classes_)) <= set(INTENT_LABELS)


@v2_only
def test_v2_meta_declares_provenance_and_matches_the_artifact():
    joblib = pytest.importorskip("joblib")
    sklearn = pytest.importorskip("sklearn")
    meta = json.loads(ev.MODEL_V2.with_suffix(".meta.json").read_text(encoding="utf-8"))
    assert meta["sklearn_version"] == sklearn.__version__
    assert meta["labels"] == [
        str(c) for c in sorted(joblib.load(ev.MODEL_V2).classes_, key=INTENT_LABELS.index)
    ]
    # Xuất xứ từng nguồn dữ liệu phải nằm trong sidecar — Điều 5 §5–6 buộc kê
    # khai phần nào do AI tạo ra, và artifact là chỗ con số ấy sống lâu nhất.
    # "gold_ai" là tên nguồn đúng (nhãn lô 2 do tác tử AI gán). "gold_human" của
    # artifact đóng gói 14/09 là SAI nguồn; đóng gói lại 25/09/2026 nên từ nay
    # KHÔNG còn được chấp nhận (cổng siết lại sau khi được nới tạm).
    assert set(meta["sources"]) <= {"gold_ai", "authored_11", "authored_6", "llm_lot1"}
    assert "gold_human" not in json.dumps(meta, ensure_ascii=False)
    assert meta["sources"].get("gold_ai", 0) > 0, "v2 phải kê khai nguồn nhãn lô 2 là gold_ai"
    assert meta["n_samples"] == sum(meta["sources"].values())
    # Câu kê khai nguồn nhãn đi cùng artifact phải là ĐÚNG câu của khung đánh giá
    # (một nguồn duy nhất), và nói rõ tác tử AI gán, chưa có nhãn người.
    assert meta["label_provenance"] == ev.LABEL_PROVENANCE
    assert "tác tử AI" in meta["label_provenance"]["test"]
    assert "chưa có nhãn người" in meta["label_provenance"]["test"]
    assert "chưa có nhãn người" in meta["eval"]
    # Phiên bản: đủ để dựng lại đúng môi trường đã đóng gói.
    for key in ("sklearn_version", "joblib_version", "numpy_version", "python_version"):
        assert meta.get(key), f"meta v2 thiếu {key}"
    assert meta["packaged_by"] == "python -m livelift.nlp.eval_intent --save-model"
    assert re.fullmatch(r"[0-9a-f]{64}", meta["du_lieu_train_sha256"])


@v2_only
def test_v2_keeps_every_behaviour_the_shipped_model_is_gated_on():
    """Bản nâng cấp không được đánh đổi các bất biến đã có cổng khoá ở
    ``tests/test_intent_classifier.py``: teencode/mất dấu vẫn đúng lớp, và văn
    bản ngoài miền (tiếng Anh) vẫn phải về ``khac``."""
    joblib = pytest.importorskip("joblib")
    pipe = joblib.load(ev.MODEL_V2)

    def predict(text: str) -> str:
        return str(pipe.predict([text])[0])

    assert predict("gia bn v shop") == "hoi_gia"
    assert predict("chot 1 don di shop") == "chot_don"
    assert predict("ship cod duoc khong") == "van_chuyen"
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
    khac_share = sum(predict(t) == "khac" for t in english) / len(english)
    assert khac_share >= 0.7, f"chỉ {khac_share:.0%} tiếng Anh về 'khac'"


@v2_only
def test_v2_can_predict_the_five_classes_the_old_model_could_not():
    """Năm lớp thêm sau live-fire 08/09 chiếm > 40% chat thật. Bộ nhãn mở rộng
    mà artifact không phát ra được thì mở rộng chỉ nằm trên giấy."""
    joblib = pytest.importorskip("joblib")
    pipe = joblib.load(ev.MODEL_V2)
    cases = {
        "chào shop buổi tối": "chao_hoi",
        "LỤC TRÀ MĂNG ĐEN ACHAN TEA (HỘP 200G) GIÁ 400K": "bao_gia_shop",
        "mở đại lý ở [ĐỊA CHỈ] được không": "hoi_daily",
        "còn sốt muối tắc chưa B": "hoi_sanpham",
    }
    for text, expected in cases.items():
        assert str(pipe.predict([text])[0]) == expected, text


def test_default_artifact_is_still_the_pre_registered_one():
    """Mặc định KHÔNG được đổi lặng lẽ: mọi con số đã công bố đo trên v1, và
    đổi mặc định kéo theo đổi ``TRAINED_LABELS`` — đó là một lần thăng cấp có
    chủ ý, không phải tác dụng phụ của việc thêm một file."""
    from livelift.nlp import intent as intent_mod

    assert intent_mod._MODEL_PATH.name == "intent_clf.joblib"


@v2_only
def test_env_var_switches_the_served_artifact_to_v2(monkeypatch):
    import importlib

    from livelift.nlp import intent as intent_mod

    monkeypatch.setenv(intent_mod.INTENT_MODEL_ENV, "v2")
    reloaded = importlib.reload(intent_mod)
    try:
        assert reloaded._MODEL_PATH.name == "intent_clf_v2.joblib"
        assert reloaded.classify("mở đại lý ở [ĐỊA CHỈ] được không") == "hoi_daily"
        assert reloaded.classifier_info()["model_file"] == "intent_clf_v2.joblib"
    finally:
        monkeypatch.delenv(intent_mod.INTENT_MODEL_ENV, raising=False)
        importlib.reload(intent_mod)


# ---------------------------------------------------------------------------
# Nguồn nhãn: nhãn tham chiếu do tác tử AI gán — không bao giờ khai là của người
# (sự cố 15/09; kiểm toán 25/09 thấy results.md vẫn in "Nhãn test do người gán")
# ---------------------------------------------------------------------------

#: Cụm khai sai nguồn nhãn từng nằm trong results.md tự sinh. So khớp KHÔNG phân
#: biệt hoa thường.
FORBIDDEN_PROVENANCE = ("người gán", "gán nhãn tay", "nhãn tay", "do người", "gold_human")


def _synthetic_gold() -> list[ev.GoldRow]:
    """Ba buổi, đủ hai tầng, có cả nhãn hành động — không cần dữ liệu thật."""
    rows = []
    plan = {
        "S1": ["khac", "chao_hoi", "hoi_gia", "khac", "cam_on_khen", "chot_don"],
        "S2": ["khac", "hoi_gia", "chot_don", "van_chuyen", "khac", "chao_hoi"],
        "S3": ["cam_on_khen", "khac", "hoi_size", "khac", "bao_gia_shop", "che_dat"],
    }
    texts = {
        "khac": "hôm nay trời đẹp",
        "chao_hoi": "chào cả nhà",
        "hoi_gia": "giá bao nhiêu shop",
        "cam_on_khen": "đẹp quá shop ơi",
        "chot_don": "chốt 1 cái",
        "van_chuyen": "ship cod được không",
        "hoi_size": "size L hay XL",
        "bao_gia_shop": "ÁO THUN GIÁ 99K",
        "che_dat": "đắt quá shop",
    }
    for session, labels in plan.items():
        for i, label in enumerate(labels):
            rows.append(
                ev.GoldRow(
                    uid=f"{session}-{i}",
                    text=f"{texts[label]} {session} {i}",
                    label=label,
                    session=session,
                    stratum="random" if i % 2 == 0 else "predicted",
                )
            )
    return rows


def _synthetic_report() -> dict:
    gold = _synthetic_gold()
    rows_b = [ev.evaluate_system(n, f, gold, []) for n, f in ev.baseline_systems()[:2]]
    rows_c = [ev.evaluate_system("C2 · giả lập", ev.system_keyword, gold, [])]
    rows_c[0]["packaged_as"] = ev.MODEL_V2.name
    tables = [
        {"title": "2. Baseline", "note": "n", "rows": rows_b},
        {"title": "3. Sau cải tiến", "note": "n", "rows": rows_c},
    ]
    report = {
        "generated_at": "2026-09-25T00:00:00+07:00",
        "seed": ev.SEED,
        "n_bootstrap": ev.N_BOOTSTRAP,
        "label_provenance": ev.LABEL_PROVENANCE,
        "inventory": ev.build_inventory(gold, []),
        "tables": tables,
    }
    report["best"] = ev.select_reported_system([r for t in tables for r in t["rows"]])
    report["best_rule"] = ev.BEST_RULE
    return report


def test_generated_report_never_claims_human_labels():
    """Đỏ trên mã trước 25/09: ``render_markdown`` in cứng "Nhãn test do người gán"
    và "gán nhãn TAY, mù" cho lô 393 dòng mà transcript cho thấy do Claude gán."""
    md = ev.render_markdown(_synthetic_report())
    lowered = md.lower()
    for phrase in FORBIDDEN_PROVENANCE:
        assert phrase not in lowered, f"results.md còn cụm khai sai nguồn: {phrase!r}"
    assert "tác tử AI" in md
    assert "chưa có nhãn người" in md
    assert "yt-dlp" in md  # nguồn dữ liệu: quan sát, không phải API chính thức


def test_provenance_constant_is_the_single_source_and_says_ai():
    prov = ev.LABEL_PROVENANCE
    assert "tác tử AI" in prov["test"]
    assert "chưa có nhãn người" in prov["test"]
    assert "đồng thuận" in prov["meaning"]
    assert "yt-dlp" in prov["data"]
    assert "không phải API chính thức" in prov["data"]
    for text in prov.values():
        for phrase in FORBIDDEN_PROVENANCE:
            assert phrase not in text.lower()
    assert ev.GOLD_SOURCE == "gold_ai"


def test_inventory_and_training_rows_name_the_ai_source():
    gold = _synthetic_gold()
    inv = ev.build_inventory(gold, [ev.TrainRow("x", "khac", "llm_lot1")])
    names = " ".join(s["name"] + " " + s["note"] for s in inv["sources"]).lower()
    assert "tác tử ai" in names
    for phrase in FORBIDDEN_PROVENANCE:
        assert phrase not in names
    rows = ev.TfidfSystem(use_authored=False, use_llm=False).training_rows(gold)
    assert {r.source for r in rows} == {"gold_ai"}


def test_eval_source_has_no_human_label_claim():
    """Nghiệm thu K-03 (``09-PHAN-CONG.md``) viết thành test: tệp nguồn không còn
    cụm "gán nhãn TAY" hay "người gán" ở bất kỳ đâu, kể cả chú thích."""
    source = Path(ev.__file__).read_text(encoding="utf-8")
    assert "gán nhãn TAY" not in source
    assert "người gán" not in source


# ---------------------------------------------------------------------------
# Chọn hệ thống trình bày chi tiết: không lấy "tốt nhất" lẫn giữa hai thang
# ---------------------------------------------------------------------------


def test_reported_system_is_the_packaged_one_not_the_best_score_on_another_scale():
    """Đỏ trên mã trước 25/09: ``max(macro_f1)`` trên mọi dòng chọn A8 (0,609 trên
    thang 6 lớp gộp) làm "hệ thống tốt nhất" trong khi tài liệu trích F1 của C2."""
    rows = [
        {"name": "C1", "macro_f1": 0.55, "scale": "11_lop"},
        {"name": "C2", "macro_f1": 0.56, "scale": "11_lop", "packaged_as": "v2"},
        {"name": "A2", "macro_f1": 0.58, "scale": "11_lop"},
        {"name": "A8", "macro_f1": 0.61, "scale": "6_lop_gop"},
    ]
    assert ev.select_reported_system(rows)["name"] == "C2"
    unpackaged = [dict(r, packaged_as=None) for r in rows]
    assert ev.select_reported_system(unpackaged)["name"] == "A2"  # cùng thang 11 lớp


# ---------------------------------------------------------------------------
# Recall nhãn hành động + số liệu cho hình
# ---------------------------------------------------------------------------


def test_action_recall_counts_every_true_action_row():
    y_true = ["hoi_gia", "chot_don", "chot_don", "khac", "chao_hoi"]
    y_pred = ["hoi_gia", "khac", "chot_don", "chot_don", "chao_hoi"]
    rec = ev.action_recall(y_true, y_pred)
    prec = ev.action_precision(y_true, y_pred)
    assert (rec["k"], rec["n"]) == (2, 3)
    assert (prec["k"], prec["n"]) == (2, 3)
    assert rec["k"] == prec["k"]  # cùng định nghĩa "đúng lớp"
    assert ev.action_recall(["khac"], ["hoi_gia"])["recall"] is None


def test_silent_model_has_zero_recall_not_a_flattering_precision():
    y_true = ["hoi_gia", "chot_don", "khac"]
    y_pred = ["khac", "khac", "khac"]
    assert ev.action_precision(y_true, y_pred)["n"] == 0
    assert ev.action_recall(y_true, y_pred)["recall"] == 0.0


def test_figure_details_are_consistent_and_contain_no_comment_text():
    report = _synthetic_report()
    fig = ev.figure_details(report)
    blob = json.dumps(fig, ensure_ascii=False)
    for row in _synthetic_gold():
        assert row.text not in blob, "chi-tiet-hinh.json không được chứa văn bản bình luận"
    assert "tác tử AI" in fig["nguon_nhan"]["test"]
    cm = fig["ma_tran_nham_lan"]
    assert cm["nhan"] == list(INTENT_LABELS)
    assert len(cm["ma_tran"]) == len(INTENT_LABELS)
    counts = report["inventory"]["gold_label_counts"]
    for label, total in zip(cm["nhan"], cm["tong_hang"], strict=True):
        assert total == counts.get(label, 0)
    assert sum(cm["tong_cot"]) == len(_synthetic_gold())
    codes = {r["ma"] for r in fig["macro_f1"]}
    assert {"B0", "B1", "C2"} <= codes
    for r in fig["macro_f1"]:
        lo, hi = r["macro_f1_ktc95_bootstrap"]
        assert lo <= r["macro_f1"] <= hi
    for s in fig["precision_theo_buoi_va_ty_le_nen"]:
        base = s["ty_le_nen_nhan_hanh_dong_tang_ngau_nhien"]
        assert base["n"] == sum(
            1 for r in _synthetic_gold() if r.session == s["buoi"] and r.stratum == "random"
        )
        assert {"B0", "B1", "C2"} <= set(s["he_thong"])


def test_out_of_fold_predictions_are_exactly_what_evaluate_system_scores():
    """``tinh_kappa`` chấm lại bằng ``predict_out_of_fold``; nếu hàm này lệch khỏi
    ``evaluate_system`` thì "chấm lại theo nhãn người" so hai mô hình khác nhau."""
    gold = _synthetic_gold()
    folds, n_leaked = ev.predict_out_of_fold(ev.system_keyword, gold, [])
    flat = [
        (s, r.stratum, r.label, p)
        for s, rows, preds in folds
        for r, p in zip(rows, preds, strict=True)
    ]
    result = ev.evaluate_system("kw", ev.system_keyword, gold, [])
    assert [tuple(x) for x in result["predictions"]] == flat
    assert result["n_train_rows_dropped_as_leak"] == n_leaked


def test_alternate_data_root_cannot_overwrite_published_results():
    with pytest.raises(SystemExit):
        ev.main(["--du-lieu", "khong-ton-tai"])
    with pytest.raises(SystemExit):
        ev.main(["--du-lieu", "khong-ton-tai", "--out-dir", "x", "--save-model"])


# ---------------------------------------------------------------------------
# Công cụ gán mù (scripts/gan_mu/, scripts/tinh_kappa.py) — dữ liệu tổng hợp
# ---------------------------------------------------------------------------


def _load_script(relpath: str, name: str):
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def loc_pii():
    return _load_script("scripts/gan_mu/loc_lai_pii.py", "loc_lai_pii")


@pytest.fixture(scope="module")
def gan_mu():
    return _load_script("scripts/gan_mu/tao_bang_gan_mu.py", "tao_bang_gan_mu")


@pytest.fixture(scope="module")
def kappa():
    return _load_script("scripts/tinh_kappa.py", "tinh_kappa")


#: Tên tài khoản BỊA (không phải người thật) — đúng dạng bộ lọc cũ bỏ sót (có dấu).
FAKE_HANDLE = "@Trần.Thị_Bịa99"


def _write_fake_labeling(root: Path, newline: str = "\n") -> None:
    lot1 = root / "lot1-achan-b519f75c"
    lot2 = root / "lot2-da-nguon-10-09"
    lot1.mkdir(parents=True)
    lot2.mkdir(parents=True)
    llm = [
        {
            "id": "u1",
            "text": f"{FAKE_HANDLE} ơi giá bao nhiêu",
            "label": "hoi_gia",
            "stratum": "random",
        },
        {"id": "u2", "text": "chào cả nhà", "label": "chao_hoi", "stratum": "uncertain"},
    ]
    body = newline.join(json.dumps(r, ensure_ascii=False) for r in llm) + newline
    (lot1 / "train_llm.jsonl").write_bytes(body.encode("utf-8"))
    (lot1 / "batch.jsonl").write_bytes(
        (
            newline.join(
                json.dumps({"id": r["id"], "text": r["text"]}, ensure_ascii=False) for r in llm
            )
            + newline
        ).encode("utf-8")
    )
    tsv = (
        newline.join(["A0001\tchốt 1 cái", f"B0002\tcảm ơn {FAKE_HANDLE}", "B0003\t=))"]) + newline
    )
    (lot2 / "to_label.txt").write_bytes(tsv.encode("utf-8"))


def test_rescrub_removes_handles_keeps_labels_and_is_idempotent(tmp_path, loc_pii):
    root = tmp_path / "labeling"
    _write_fake_labeling(root, newline="\r\n")
    before = {p.name: p.read_bytes() for p in root.rglob("*") if p.is_file()}

    first = loc_pii.run(root, write=True)
    assert sum(r.n_rows_changed for r in first) == 3
    assert sum(r.pii_before["social"] for r in first) == 3
    assert all(not r.pii_after for r in first)

    llm_rows = [
        json.loads(x)
        for x in (root / "lot1-achan-b519f75c/train_llm.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert [(r["id"], r["label"], r["stratum"]) for r in llm_rows] == [
        ("u1", "hoi_gia", "random"),
        ("u2", "chao_hoi", "uncertain"),
    ]
    assert "Bịa" not in llm_rows[0]["text"]
    assert "[MXH]" in llm_rows[0]["text"]
    tsv = (root / "lot2-da-nguon-10-09/to_label.txt").read_bytes()
    assert tsv.count(b"\r\n") == 3  # kiểu xuống dòng giữ nguyên
    assert tsv.startswith("A0001\tchốt 1 cái\r\n".encode())  # dòng sạch giữ từng byte

    snapshot = {p.name: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    second = loc_pii.run(root, write=True)
    assert sum(r.n_rows_changed for r in second) == 0
    assert snapshot == {p.name: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    assert before != snapshot


def test_rescrub_check_mode_is_a_gate_and_prints_no_comment_text(tmp_path, loc_pii, capsys):
    root = tmp_path / "labeling"
    _write_fake_labeling(root)
    assert loc_pii.main(["--goc", str(root), "--kiem-tra"]) == 1  # còn PII -> mã 1
    out = capsys.readouterr().out
    assert "Bịa" not in out
    assert "giá bao nhiêu" not in out
    assert loc_pii.main(["--goc", str(root)]) == 0
    assert loc_pii.main(["--goc", str(root), "--kiem-tra"]) == 0


def _fake_lot2(root: Path) -> list[ev.GoldRow]:
    """Lô 2 tổng hợp: to_label.txt + gold.txt + key.json, đúng định dạng thật."""
    gold = _synthetic_gold()
    root.mkdir(parents=True, exist_ok=True)
    (root / "to_label.txt").write_text(
        "".join(f"{r.uid}\t{r.text}\n" for r in gold), encoding="utf-8"
    )
    (root / "gold.txt").write_text("".join(f"{r.uid} {r.label}\n" for r in gold), encoding="utf-8")
    key = {r.uid: {"set": "B" if r.stratum == "random" else "A", "video": r.session} for r in gold}
    (root / "key.json").write_text(json.dumps(key), encoding="utf-8")
    return gold


def test_blind_tables_hide_ai_labels_and_strata_and_are_deterministic(tmp_path, gan_mu):
    gold = _fake_lot2(tmp_path / "lot2")
    rows = gan_mu.load_rows(tmp_path / "lot2")
    files = gan_mu.build_tables(rows, seed=123)
    assert files == gan_mu.build_tables(rows, seed=123)  # tất định
    assert files != gan_mu.build_tables(rows, seed=124)
    t1, t2 = (files[n] for n in gan_mu.TABLE_NAMES)
    bom = bytes([0xEF, 0xBB, 0xBF])
    for table in (t1, t2):
        assert table.startswith(bom)
        assert b"\r\n" in table
        text = table[3:].decode("utf-8")
        assert text.splitlines()[0] == ",".join(gan_mu.COLUMNS)
        stripped = text
        for r in gold:
            assert r.uid not in text  # uid lộ tầng A/B
            stripped = stripped.replace(r.text, "")
        for session in {r.session for r in gold}:
            assert session not in stripped  # không có cột tên buổi
        assert not (set(INTENT_LABELS) & {line.split(",")[3] for line in text.splitlines()[1:]})
    import csv
    import io

    def codes(table: bytes) -> list[str]:
        return [row["ma_dong"] for row in csv.DictReader(io.StringIO(table[3:].decode("utf-8")))]

    assert sorted(codes(t1)) == sorted(codes(t2))
    assert codes(t1) != codes(t2)  # hai thứ tự xáo trộn khác nhau
    key = list(csv.DictReader(io.StringIO(files[gan_mu.KEY_NAME][3:].decode("utf-8"))))
    assert sorted(k["uid_lo2"] for k in key) == sorted(r.uid for r in gold)
    assert sorted(k["ma_dong"] for k in key) == sorted(codes(t1))


def test_blind_table_cells_cannot_become_excel_formulas(gan_mu):
    assert gan_mu.excel_safe("=))") == " =))"
    assert gan_mu.excel_safe("@shop") == " @shop"
    assert gan_mu.excel_safe("giá bn") == "giá bn"


def test_blind_guide_uses_the_label_module_definitions(gan_mu):
    from livelift.nlp.labels import LABEL_GUIDELINE

    guide = gan_mu.guide_text(393)
    for label in INTENT_LABELS:
        assert f"`{label}`" in guide
        assert LABEL_GUIDELINE[label].replace("|", "/") in guide
    assert "Không dùng AI" in guide


def test_blind_hashes_match_the_files_written(tmp_path, gan_mu):
    import hashlib

    _fake_lot2(tmp_path / "lot2")
    out, hashes = tmp_path / "ra", tmp_path / "bam"
    digests = gan_mu.write_all(out, hashes, seed=7, gold_dir=tmp_path / "lot2")
    for name, digest in digests.items():
        target = out / "khoa" / name if name == gan_mu.KEY_NAME else out / name
        assert hashlib.sha256(target.read_bytes()).hexdigest() == digest
        assert (hashes / f"{name}.sha256").read_text(encoding="utf-8").split()[0] == digest
    assert not (hashes / gan_mu.KEY_NAME).exists()  # khoá không vào repo
    with pytest.raises(SystemExit):
        gan_mu.main(["--ra", str(REPO / "khong-duoc-ghi-trong-repo")])


def test_default_blind_seed_is_secret_so_row_positions_do_not_reveal_the_stratum(tmp_path, gan_mu):
    """Đỏ trên bản đầu (seed cố định 20260925 trong mã): uid ``A…`` đứng trước ``B…``
    trong danh sách được xáo trộn, nên seed công khai + script công khai cho phép tính
    ngược tầng của TỪNG dòng trong bảng phát (phản biện 25/09: 393/393). Mặc định seed
    phải bí mật, chỉ nằm trong ``khoa/``, và vẫn sinh lại đúng từng byte khi biết seed."""
    _fake_lot2(tmp_path / "lot2")
    runs = []
    for i in (1, 2):
        out, bam = tmp_path / f"ra{i}", tmp_path / f"bam{i}"
        gan_mu.main(["--ra", str(out), "--bam", str(bam), "--goc-lo2", str(tmp_path / "lot2")])
        runs.append((out, bam))
    (out1, bam1), (out2, _bam2) = runs
    table = gan_mu.TABLE_NAMES[0]
    assert (out1 / table).read_bytes() != (out2 / table).read_bytes()  # không seed cố định

    secret = json.loads((out1 / "khoa" / gan_mu.SEED_NAME).read_text(encoding="utf-8"))
    seed = secret["seed_ma_mu"]
    rebuilt = gan_mu.build_tables(gan_mu.load_rows(tmp_path / "lot2"), seed)
    assert rebuilt[table] == (out1 / table).read_bytes()  # biết seed thì tái lập được

    distributed = [out1 / n for n in (*gan_mu.TABLE_NAMES, gan_mu.GUIDE_NAME, "manifest.json")]
    distributed += list(bam1.iterdir())
    for path in distributed:
        assert str(seed) not in path.read_text(encoding="utf-8-sig"), path.name


def test_cohen_kappa_matches_sklearn_and_edge_cases(kappa):
    import random

    metrics = pytest.importorskip("sklearn.metrics")
    rng = random.Random(3)
    labels = list(INTENT_LABELS)
    a = [rng.choice(labels[:4]) for _ in range(200)]
    b = [x if rng.random() < 0.7 else rng.choice(labels[:4]) for x in a]
    assert kappa.cohen_kappa(a, b) == pytest.approx(metrics.cohen_kappa_score(a, b), abs=1e-12)
    assert kappa.cohen_kappa(["khac"] * 5, ["khac"] * 5) == 1.0
    assert kappa.cohen_kappa(["a", "b"], ["b", "a"]) < 0
    lo, hi = kappa.bootstrap_kappa(a, b, n=200)
    assert lo <= kappa.cohen_kappa(a, b) <= hi
    assert kappa.kappa_band(0.5) == "trung bình"


def test_kappa_reads_excel_semicolon_and_cp1258_tables(tmp_path, kappa):
    semicolon = (
        "stt;ma_dong;binh_luan;nhan;ghi_chu\r\n1;GM000001;chào;chao_hoi;\r\n2;GM000002;x;3;\r\n"
    )
    p1 = tmp_path / "a.csv"
    p1.write_bytes(bytes([0xEF, 0xBB, 0xBF]) + semicolon.encode("utf-8"))
    labels, diag = kappa.read_labeled_table(p1)
    assert labels == {"GM000001": "chao_hoi", "GM000002": "che_dat"}
    p2 = tmp_path / "b.csv"
    cp1258_csv = (
        "stt,ma_dong,binh_luan,nhan,ghi_chu\n"
        '1,GM000001,"chào, b; c",Khac,\n'
        "2,GM000002,y,,\n"
        "3,GM000003,z,sai_nhan,\n"
    )
    p2.write_bytes(cp1258_csv.encode("cp1258"))  # "CSV (Comma delimited)" của Excel cũ
    labels, diag = kappa.read_labeled_table(p2)
    assert labels == {"GM000001": "khac"}
    assert diag["blank"] == ["GM000002"]
    assert diag["invalid"][0][0] == "GM000003"
    problems = kappa.check_table(labels, diag, {"GM000002": "u2", "GM000009": "u9"}, "bảng")
    assert any("chưa gán" in p for p in problems)  # GM000002 để trống
    assert any("không có trong khoá" in p for p in problems)  # GM000001 lạ
    assert any("thiếu 1 mã dòng" in p for p in problems)  # GM000009 không ai gán


def _fill(table: bytes, labels_by_code: dict[str, str]) -> bytes:
    import csv
    import io

    rows = list(csv.DictReader(io.StringIO(table[3:].decode("utf-8"))))
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\r\n")
    writer.writeheader()
    for row in rows:
        row["nhan"] = labels_by_code[row["ma_dong"]]
        writer.writerow(row)
    return bytes([0xEF, 0xBB, 0xBF]) + buf.getvalue().encode("utf-8")


def test_kappa_end_to_end_on_synthetic_blind_labels(tmp_path, gan_mu, kappa):
    """Người 1 chép đúng nhãn AI, người 2 sửa 3 dòng: κ(người 1–AI) = 1, κ người–người
    < 1, và chấm lại B0/B1 theo nhãn AI trùng khít số ``evaluate_system``."""
    import csv
    import io

    gold = _fake_lot2(tmp_path / "lot2")
    ai = {r.uid: r.label for r in gold}
    files = gan_mu.build_tables(gan_mu.load_rows(tmp_path / "lot2"), seed=11)
    key = {
        k["ma_dong"]: k["uid_lo2"]
        for k in csv.DictReader(io.StringIO(files[gan_mu.KEY_NAME][3:].decode("utf-8")))
    }
    h1 = {code: ai[uid] for code, uid in key.items()}
    changed = sorted(key)[:3]
    h2 = {
        code: ("khac" if ai[key[code]] != "khac" else "chao_hoi") if code in changed else lb
        for code, lb in h1.items()
    }
    (tmp_path / "k.csv").write_bytes(files[gan_mu.KEY_NAME])
    (tmp_path / "1.csv").write_bytes(_fill(files[gan_mu.TABLE_NAMES[0]], h1))
    (tmp_path / "2.csv").write_bytes(_fill(files[gan_mu.TABLE_NAMES[1]], h2))

    report = kappa.run(
        tmp_path / "1.csv",
        tmp_path / "2.csv",
        tmp_path / "k.csv",
        gold_dir=tmp_path / "lot2",
        cham_lai=True,
        systems=["B0", "B1"],
        extra=[],
        n_boot=50,
    )
    pairs = report["dong_thuan"]
    assert pairs["người 1 – AI"]["kappa"] == 1.0
    assert pairs["người 1 – người 2"]["kappa"] < 1.0
    assert pairs["người 1 – người 2"]["n"] == len(gold)
    assert report["n_dong_thuan_hai_nguoi"] == len(gold) - 3
    for entry in report["cham_lai"]:
        factory = {n.split(" ", 1)[0]: f for n, f in ev.baseline_systems()}[entry["ma"]]
        published = ev.evaluate_system(entry["ma"], factory, gold, [])
        assert entry["tham_chieu"]["AI, toàn bộ"]["macro_f1"] == published["macro_f1"]
        assert entry["tham_chieu"]["AI, toàn bộ"]["accuracy"] == published["accuracy"]
    md = kappa.render_markdown(report)
    assert "κ" in md
    for r in gold:
        assert r.text not in md
        assert r.text not in json.dumps(report, ensure_ascii=False)


def test_kappa_refuses_incomplete_tables(tmp_path, gan_mu, kappa, capsys):
    import csv
    import io

    _fake_lot2(tmp_path / "lot2")
    files = gan_mu.build_tables(gan_mu.load_rows(tmp_path / "lot2"), seed=5)
    codes = [
        k["ma_dong"]
        for k in csv.DictReader(io.StringIO(files[gan_mu.KEY_NAME][3:].decode("utf-8")))
    ]
    full = dict.fromkeys(codes, "khac")
    partial = dict(full, **{codes[0]: ""})
    (tmp_path / "k.csv").write_bytes(files[gan_mu.KEY_NAME])
    (tmp_path / "1.csv").write_bytes(_fill(files[gan_mu.TABLE_NAMES[0]], full))
    (tmp_path / "2.csv").write_bytes(_fill(files[gan_mu.TABLE_NAMES[1]], partial))
    code = kappa.main(
        [
            "--bang1",
            str(tmp_path / "1.csv"),
            "--bang2",
            str(tmp_path / "2.csv"),
            "--khoa",
            str(tmp_path / "k.csv"),
            "--goc-lo2",
            str(tmp_path / "lot2"),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    assert code == 2
    assert "chưa gán" in capsys.readouterr().err
    assert not (tmp_path / "out").exists()
