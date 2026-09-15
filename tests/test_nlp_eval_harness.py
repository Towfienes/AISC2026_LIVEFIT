"""Khung đánh giá ý định: chuẩn hoá, chỉ số, chia theo buổi live, rào rò rỉ.

Vì sao những test này tồn tại: bộ phân loại từng công bố macro-F1 0,870 trên bộ
tự biên soạn rồi rơi xuống 0,271 trên chat thật. Nguyên nhân không nằm ở mô hình
mà ở **cách đo**. Nên phần được khoá bằng test ở đây là chính cái khung đo:
công thức macro-F1 (đúng quy ước đã công bố), phép chia không cho một buổi live
nằm cả hai phía, và rào chắn loại dòng train trùng khít dòng test.
"""

from __future__ import annotations

import json
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
    assert set(ev.COLLAPSE_TO_6) == {
        "chao_hoi",
        "cam_on_khen",
        "hoi_sanpham",
        "hoi_daily",
        "bao_gia_shop",
    }
    assert set(ev.COLLAPSE_TO_6.values()) == {"khac"}


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
    assert set(meta["sources"]) <= {"gold_human", "authored_11", "authored_6", "llm_lot1"}
    assert meta["n_samples"] == sum(meta["sources"].values())


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
