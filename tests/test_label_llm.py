"""LLM labeling pipeline (gói F): export -> merge -> finalize, no API calls.

Every subcommand runs on tiny hand-made data in tmp_path; the pipeline is
pure logic (HARNESS.md §1) so nothing here needs a network, a model, or a DB.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from livelift.api.store import InMemoryStore
from livelift.nlp.label_llm import (
    STRATUM_RANDOM,
    STRATUM_UNCERTAIN,
    build_prompt,
    collect_from_store,
    load_seed_examples,
    main,
    prepare_batch,
)
from livelift.nlp.labels import INTENT_LABELS, LABEL_EXAMPLES_REAL, LABEL_GUIDELINE

NOW = datetime.now(UTC)


def _write_jsonl(path, rows):
    path.write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
    )


def _read_jsonl(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------


def test_export_filters_empty_and_duplicate_comments(tmp_path, capsys):
    src = tmp_path / "in.jsonl"
    _write_jsonl(
        src,
        [
            {"id": "c1", "text": "giá bao nhiêu vậy shop"},
            {"id": "c2", "text": ""},  # rỗng -> loại
            {"id": "c3", "text": "   "},  # chỉ khoảng trắng -> loại
            {"id": "c4", "text": "giá bao nhiêu vậy shop"},  # trùng text -> loại
            {"id": "c5", "text": "chốt 1 đơn nha"},
        ],
    )
    out_dir = tmp_path / "lot"
    rc = main(["export", "--input", str(src), "--out-dir", str(out_dir)])
    assert rc == 0

    batch = _read_jsonl(out_dir / "batch.jsonl")
    assert [r["id"] for r in batch] == ["c1", "c5"]
    assert all(set(r.keys()) == {"id", "text"} for r in batch)
    printed = capsys.readouterr().out
    assert "2 rỗng" in printed
    assert "1 trùng" in printed
    assert "đã xuất: 2" in printed


def test_export_uncertain_first_orders_by_confidence_then_limits(tmp_path):
    src = tmp_path / "in.jsonl"
    _write_jsonl(
        src,
        [
            {"id": "hi", "text": "câu rất chắc chắn", "intent_confidence": 0.95},
            {"id": "mid", "text": "câu lưng chừng", "intent_confidence": 0.61},
            {"id": "none", "text": "câu chưa từng được chấm"},  # None -> bất định nhất
            {"id": "low", "text": "câu mơ hồ", "intent_confidence": 0.31},
        ],
    )
    out_dir = tmp_path / "lot"
    rc = main(
        [
            "export",
            "--input",
            str(src),
            "--out-dir",
            str(out_dir),
            "--uncertain-first",
            "--limit",
            "3",
        ]
    )
    assert rc == 0
    batch = _read_jsonl(out_dir / "batch.jsonl")
    # None đứng đầu, sau đó confidence tăng dần; --limit cắt câu chắc nhất
    assert [r["id"] for r in batch] == ["none", "low", "mid"]


def test_export_prompt_contains_guideline_and_examples_per_class(tmp_path):
    src = tmp_path / "in.jsonl"
    _write_jsonl(src, [{"id": "c1", "text": "ship về Gò Vấp bao nhiêu"}])
    out_dir = tmp_path / "lot"
    rc = main(
        ["export", "--input", str(src), "--out-dir", str(out_dir), "--examples-per-class", "6"]
    )
    assert rc == 0
    prompt = (out_dir / "prompt.txt").read_text(encoding="utf-8")
    for label in INTENT_LABELS:
        assert f"- {label}:" in prompt, f"guideline thiếu lớp {label}"
        assert f"### {label}" in prompt, f"prompt thiếu mục ví dụ cho {label}"
    # mỗi lớp có ví dụ thật (dataset biên soạn, hoặc mẫu thật cho lớp mới)
    examples = load_seed_examples(per_class=6)
    for label in INTENT_LABELS:
        assert examples[label], f"lớp {label} không có ví dụ nào trong prompt"
        assert len(examples[label]) <= 6
        assert f'- "{examples[label][0]}"' in prompt
    # quy ước đa ý định từ docs/benchmarks/intent-classifier.md phải có mặt
    assert "gần nhất với chốt đơn" in prompt


def test_build_prompt_rejects_example_count_outside_5_10():
    import pytest

    from livelift.nlp.label_llm import LabelPipelineError

    with pytest.raises(LabelPipelineError):
        build_prompt(examples_per_class=3)
    with pytest.raises(LabelPipelineError):
        build_prompt(examples_per_class=11)


def test_collect_from_store_reads_scrubbed_text_and_confidence():
    store = InMemoryStore()
    sid = store.create_session(
        {
            "session_id": str(uuid.uuid4()),
            "platform": "youtube",
            "title": "quan sát",
            "mode": "auto",
            "status": "ended",
            "planned_duration_min": 60,
            "host_id": None,
            "created_at": NOW,
        }
    )["session_id"]
    store.add_comment(
        sid,
        {
            "comment_id": "cmt-1",
            "session_id": sid,
            "block_id": None,
            "ts": NOW,
            "platform": None,
            "ext_id": None,
            "text_scrubbed": "chốt đơn [SĐT]",
            "pii_kinds": ["phone"],
            "intent_label": "chot_don",
            "intent_confidence": 0.42,
            "sentiment": None,
        },
    )
    items = collect_from_store(store)
    assert items == [{"id": "cmt-1", "text": "chốt đơn [SĐT]", "confidence": 0.42}]
    batch, stats = prepare_batch(items, uncertain_first=True)
    assert stats.n_exported == 1
    assert batch[0] == {"id": "cmt-1", "text": "chốt đơn [SĐT]"}


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------


def _merge_fixture(tmp_path):
    batch = tmp_path / "batch.jsonl"
    _write_jsonl(
        batch,
        [
            {"id": "c1", "text": "giá nhiêu shop"},
            {"id": "c2", "text": "chốt 1 đơn"},
            {"id": "c3", "text": "đắt quá shop ơi"},
            {"id": "c4", "text": "ship cod không"},
        ],
    )
    a = tmp_path / "a.jsonl"
    b = tmp_path / "b.jsonl"
    _write_jsonl(
        a,
        [
            {"id": "c1", "label": "hoi_gia"},
            {"id": "c2", "label": "chot_don"},
            {"id": "c3", "label": "che_dat"},
            {"id": "c4", "label": "van_chuyen"},  # model B bỏ sót id này
        ],
    )
    _write_jsonl(
        b,
        [
            {"id": "c1", "label": "hoi_gia"},
            {"id": "c2", "label": "chot_don"},
            {"id": "c3", "label": "khac"},  # bất đồng với model A
        ],
    )
    return batch, a, b


def test_merge_routes_consensus_and_disagreements(tmp_path, capsys):
    batch, a, b = _merge_fixture(tmp_path)
    out_dir = tmp_path / "merged"
    rc = main(
        [
            "merge",
            "--model-a",
            str(a),
            "--model-b",
            str(b),
            "--batch",
            str(batch),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 0

    consensus = _read_jsonl(out_dir / "consensus.jsonl")
    assert [(r["id"], r["label"]) for r in consensus] == [("c1", "hoi_gia"), ("c2", "chot_don")]
    # consensus mang text để finalize không phải tra ngược
    assert consensus[0]["text"] == "giá nhiêu shop"

    disagreements = _read_jsonl(out_dir / "disagreements.jsonl")
    assert {r["id"] for r in disagreements} == {"c3", "c4"}
    by_id = {r["id"]: r for r in disagreements}
    # bất đồng thực sự: cả hai nhãn + text cho người duyệt
    assert by_id["c3"] == {
        "id": "c3",
        "text": "đắt quá shop ơi",
        "label_a": "che_dat",
        "label_b": "khac",
    }
    # id bị một model bỏ sót cũng KHÔNG được vào consensus
    assert by_id["c4"]["label_a"] == "van_chuyen"
    assert by_id["c4"]["label_b"] is None

    printed = capsys.readouterr().out
    assert "đồng thuận 2" in printed
    assert "bất đồng 2" in printed
    assert "hoi_gia" in printed  # phân phối nhãn


def test_merge_rejects_label_outside_the_declared_class_set(tmp_path, capsys):
    batch, a, b = _merge_fixture(tmp_path)
    _write_jsonl(b, [{"id": "c1", "label": "spam"}])  # nhãn ngoài 6 lớp
    out_dir = tmp_path / "merged"
    rc = main(
        [
            "merge",
            "--model-a",
            str(a),
            "--model-b",
            str(b),
            "--batch",
            str(batch),
            "--out-dir",
            str(out_dir),
        ]
    )
    assert rc == 2
    assert f"không thuộc {len(INTENT_LABELS)} lớp" in capsys.readouterr().err
    assert not (out_dir / "consensus.jsonl").exists(), "nhãn sai không được ghi ra file nào"


# ---------------------------------------------------------------------------
# finalize
# ---------------------------------------------------------------------------


def test_finalize_outputs_train_format_with_source(tmp_path, monkeypatch):
    consensus = tmp_path / "consensus.jsonl"
    reviewed = tmp_path / "reviewed.jsonl"
    out = tmp_path / "train_extra.jsonl"
    _write_jsonl(
        consensus,
        [
            {"id": "c1", "text": "giá nhiêu shop", "label": "hoi_gia"},
            {"id": "c3", "text": "đắt quá shop ơi", "label": "khac"},
        ],
    )
    _write_jsonl(
        reviewed,
        [
            # người duyệt sửa lại c3 (ghi đè consensus) và thêm c4
            {"id": "c3", "text": "đắt quá shop ơi", "label": "che_dat"},
            {"id": "c4", "text": "ship cod không", "label": "van_chuyen"},
        ],
    )
    rc = main(
        ["finalize", "--consensus", str(consensus), "--reviewed", str(reviewed), "--out", str(out)]
    )
    assert rc == 0

    rows = _read_jsonl(out)
    assert all(set(r.keys()) == {"text", "label", "source"} for r in rows)
    by_text = {r["text"]: r for r in rows}
    assert by_text["giá nhiêu shop"]["source"] == "llm-consensus"
    # phán quyết của người duyệt thắng nhãn consensus cùng id
    assert by_text["đắt quá shop ơi"] == {
        "text": "đắt quá shop ơi",
        "label": "che_dat",
        "source": "human",
    }
    assert by_text["ship cod không"]["source"] == "human"

    # đúng format train_intent.py đang đọc (trường source thừa được bỏ qua)
    from livelift.nlp import train_intent

    monkeypatch.setattr(train_intent, "DATA", out)
    texts, labels = train_intent.load_dataset()
    assert len(texts) == 3
    assert set(labels) <= set(INTENT_LABELS)


def test_finalize_rejects_bad_label_and_missing_text(tmp_path, capsys):
    consensus = tmp_path / "consensus.jsonl"
    out = tmp_path / "train.jsonl"

    _write_jsonl(consensus, [{"id": "c1", "text": "giá nhiêu", "label": "vip_khach"}])
    rc = main(["finalize", "--consensus", str(consensus), "--out", str(out)])
    assert rc == 2
    assert f"không thuộc {len(INTENT_LABELS)} lớp" in capsys.readouterr().err

    _write_jsonl(consensus, [{"id": "c1", "label": "hoi_gia"}])  # thiếu text
    rc = main(["finalize", "--consensus", str(consensus), "--out", str(out)])
    assert rc == 2
    assert "thiếu trường 'text'" in capsys.readouterr().err
    assert not out.exists()


# ---------------------------------------------------------------------------
# bộ nhãn — MỘT nguồn duy nhất (live-fire 08/09/2026)
# ---------------------------------------------------------------------------


def test_label_set_comes_from_exactly_one_module():
    """Chống tái diễn lỗi 08/09: bộ nhãn từng bị chép ở 4 chỗ nên thêm một lớp
    là quên một chỗ. Dùng kiểm tra ĐỒNG NHẤT THỂ (``is``) — hai đối tượng khác
    nhau không thể lệch nhau nếu chúng là cùng một đối tượng."""
    from livelift import nlp
    from livelift.nlp import intent as intent_mod
    from livelift.nlp import label_llm as label_mod
    from livelift.nlp import labels as labels_mod
    from livelift.nlp import train_intent as train_mod

    assert intent_mod.INTENT_LABELS is labels_mod.INTENT_LABELS
    assert label_mod.INTENT_LABELS is labels_mod.INTENT_LABELS
    assert label_mod.LABEL_GUIDELINE is labels_mod.LABEL_GUIDELINE
    assert nlp.INTENT_LABELS is labels_mod.INTENT_LABELS
    assert list(labels_mod.TRAINED_LABELS) == train_mod.LABELS


def test_class_count_in_prompt_is_computed_not_hardcoded():
    """Prompt phải nói đúng số lớp hiện có; chuỗi cứng '6 lớp' đã gây lệch giữa
    guideline và validator, không được quay lại."""
    prompt = build_prompt()
    assert f"đúng {len(INTENT_LABELS)} lớp sau" in prompt
    assert f"đúng {len(INTENT_LABELS)} lớp trên" in prompt
    if len(INTENT_LABELS) != 6:
        assert "6 lớp" not in prompt


def test_trained_labels_match_the_shipped_artifact():
    """``TRAINED_LABELS`` phải khớp lớp của artifact đang đóng gói — bộ nhãn
    gán nhãn được phép rộng hơn, nhưng model thì không được bịa."""
    import json as _json
    from pathlib import Path as _Path

    from livelift.nlp import intent as intent_mod
    from livelift.nlp.labels import TRAINED_LABELS

    meta = _json.loads(
        (_Path(intent_mod.__file__).parent / "model" / "intent_clf.meta.json").read_text(
            encoding="utf-8"
        )
    )
    assert list(TRAINED_LABELS) == meta["labels"]
    assert set(TRAINED_LABELS) <= set(INTENT_LABELS)


def test_live_fire_classes_are_declared_with_guideline_and_real_examples():
    """Các lớp phát hiện qua chat bán hàng thật (docs/benchmarks/live-fire-achan.md)
    phải có mặt đủ ba phần: trong bộ nhãn, có định nghĩa, có ví dụ THẬT."""
    for label in ("chao_hoi", "cam_on_khen", "hoi_sanpham", "hoi_daily", "bao_gia_shop"):
        assert label in INTENT_LABELS, f"thiếu lớp {label} trong bộ nhãn"
        assert LABEL_GUIDELINE[label].strip(), f"lớp {label} chưa có định nghĩa"
        assert len(LABEL_EXAMPLES_REAL[label]) >= 5, f"lớp {label} cần ≥5 ví dụ thật"
    assert all(label in LABEL_GUIDELINE for label in INTENT_LABELS)


def test_khac_examples_do_not_contradict_the_new_classes():
    """Hồi quy cho lỗi phát hiện lúc dựng lô đầu tiên: 60 dòng ``khac`` của bộ
    biên soạn được viết khi chưa có chao_hoi/cam_on_khen/hoi_sanpham, nên dùng
    chúng làm ví dụ ``khac`` là dạy NGƯỢC cho bộ gán nhãn ("chào shop buổi tối"
    xuất hiện dưới nhãn khac ngay cạnh định nghĩa chao_hoi)."""
    import json as _json

    from livelift.nlp.train_intent import DATA

    authored_khac = {
        _json.loads(line)["text"]
        for line in DATA.read_text(encoding="utf-8").splitlines()
        if line.strip() and _json.loads(line)["label"] == "khac"
    }
    examples = load_seed_examples(per_class=8)
    assert not (set(examples["khac"]) & authored_khac), (
        "ví dụ khac phải là mẫu THẬT đã soi lại, không lấy từ bộ biên soạn cũ"
    )
    prompt = build_prompt()
    for greeting in ("chào shop buổi tối", "hello mọi người", "chị chủ xinh quá"):
        assert greeting not in prompt, f"prompt còn dạy '{greeting}' là khac"


def test_pipeline_accepts_a_new_class_end_to_end(tmp_path):
    """Lớp mới phải đi được suốt merge -> finalize mà không phải sửa code."""
    batch = tmp_path / "batch.jsonl"
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    _write_jsonl(batch, [{"id": "c1", "text": "Chao A Chan ! Chao Ca Nha !"}])
    _write_jsonl(a, [{"id": "c1", "label": "chao_hoi"}])
    _write_jsonl(b, [{"id": "c1", "label": "chao_hoi"}])
    out_dir = tmp_path / "merged"
    assert (
        main(
            [
                "merge",
                "--model-a",
                str(a),
                "--model-b",
                str(b),
                "--batch",
                str(batch),
                "--out-dir",
                str(out_dir),
            ]
        )
        == 0
    )
    consensus = _read_jsonl(out_dir / "consensus.jsonl")
    assert consensus == [{"id": "c1", "text": "Chao A Chan ! Chao Ca Nha !", "label": "chao_hoi"}]
    out = tmp_path / "train_extra.jsonl"
    assert (
        main(["finalize", "--consensus", str(out_dir / "consensus.jsonl"), "--out", str(out)]) == 0
    )
    assert _read_jsonl(out)[0]["label"] == "chao_hoi"


# ---------------------------------------------------------------------------
# export hai tầng: mẫu ngẫu nhiên (prevalence) + uncertain-first (học)
# ---------------------------------------------------------------------------


def _confidence_rows(n: int) -> list[dict]:
    # confidence trải đều 0.10..0.99 để tầng bất định có thứ tự rõ ràng
    return [
        {"id": f"c{i}", "text": f"bình luận số {i}", "confidence": 0.1 + i * 0.009}
        for i in range(n)
    ]


def test_prepare_batch_splits_into_random_and_uncertain_strata():
    items = _confidence_rows(100)
    batch, stats = prepare_batch(
        items, uncertain_first=True, limit=50, random_fraction=0.10, seed=2026
    )
    assert stats.n_exported == 50
    assert stats.n_random == 5, "10% của 50 dòng phải là 5 dòng mẫu ngẫu nhiên"
    assert stats.n_uncertain == 45
    assert len(stats.strata) == 50
    assert {r["id"] for r in batch} == set(stats.strata)
    # batch gửi LLM KHÔNG mang thông tin tầng (tránh gợi ý cho model)
    assert all(set(r) == {"id", "text"} for r in batch)

    random_ids = {i for i, s in stats.strata.items() if s == STRATUM_RANDOM}
    uncertain_ids = {i for i, s in stats.strata.items() if s == STRATUM_UNCERTAIN}
    assert not (random_ids & uncertain_ids), "một id không được nằm ở hai tầng"
    # tầng bất định là 45 câu ÍT CHẮC CHẮN NHẤT trong phần chưa bị bốc ngẫu nhiên
    by_id = {r["id"]: r["confidence"] for r in items}
    rest = sorted((c for i, c in by_id.items() if i not in random_ids))
    assert sorted(by_id[i] for i in uncertain_ids) == rest[:45]


def test_random_stratum_is_reproducible_from_the_seed():
    items = _confidence_rows(100)
    kw = {"uncertain_first": True, "limit": 40, "random_fraction": 0.25}
    _, s1 = prepare_batch(items, seed=2026, **kw)
    _, s2 = prepare_batch(items, seed=2026, **kw)
    _, s3 = prepare_batch(items, seed=99, **kw)
    assert s1.strata == s2.strata, "cùng seed phải cho cùng lô — điều kiện tái lập"
    assert s1.strata != s3.strata, "seed khác phải bốc khác, nếu không seed vô nghĩa"


def test_random_stratum_requires_an_explicit_seed_and_valid_fraction():
    import pytest

    from livelift.nlp.label_llm import LabelPipelineError

    items = _confidence_rows(20)
    with pytest.raises(LabelPipelineError, match="seed"):
        prepare_batch(items, limit=10, random_fraction=0.1, seed=None)
    with pytest.raises(LabelPipelineError, match="0.0–1.0"):
        prepare_batch(items, limit=10, random_fraction=1.5, seed=1)


def test_zero_random_fraction_keeps_the_old_deterministic_order():
    """Hành vi cũ không được đổi: không có tầng ngẫu nhiên thì thứ tự batch VẪN
    là thứ tự ưu tiên active learning."""
    items = _confidence_rows(10)
    batch, stats = prepare_batch(items, uncertain_first=True, limit=3)
    assert [r["id"] for r in batch] == ["c0", "c1", "c2"]
    assert stats.n_random == 0
    assert set(stats.strata.values()) == {STRATUM_UNCERTAIN}


def test_export_writes_strata_file_matching_the_batch(tmp_path, capsys):
    src = tmp_path / "in.jsonl"
    _write_jsonl(src, _confidence_rows(200))
    out_dir = tmp_path / "lot"
    rc = main(
        [
            "export",
            "--input",
            str(src),
            "--out-dir",
            str(out_dir),
            "--limit",
            "100",
            "--random-fraction",
            "0.10",
            "--seed",
            "2026",
            "--uncertain-first",
        ]
    )
    assert rc == 0
    batch = _read_jsonl(out_dir / "batch.jsonl")
    strata = _read_jsonl(out_dir / "strata.jsonl")
    assert len(batch) == len(strata) == 100
    assert [r["id"] for r in batch] == [r["id"] for r in strata], "strata phải cùng thứ tự batch"
    counts = {}
    for r in strata:
        counts[r["stratum"]] = counts.get(r["stratum"], 0) + 1
    assert counts == {STRATUM_RANDOM: 10, STRATUM_UNCERTAIN: 90}
    printed = capsys.readouterr().out
    assert "tầng ngẫu nhiên" in printed
    assert "seed 2026" in printed


# ---------------------------------------------------------------------------
# export theo phiên
# ---------------------------------------------------------------------------


def _store_with_two_sessions():
    store = InMemoryStore()
    ids = []
    for n, title in ((2, "phiên A"), (3, "phiên B")):
        sid = store.create_session(
            {
                "session_id": str(uuid.uuid4()),
                "platform": "youtube",
                "title": title,
                "mode": "auto",
                "status": "ended",
                "planned_duration_min": 60,
                "host_id": None,
                "created_at": NOW,
            }
        )["session_id"]
        ids.append(sid)
        for i in range(n):
            store.add_comment(
                sid,
                {
                    "comment_id": f"{title}-{i}",
                    "session_id": sid,
                    "block_id": None,
                    "ts": NOW,
                    "platform": None,
                    "ext_id": None,
                    "text_scrubbed": f"{title} bình luận {i}",
                    "pii_kinds": [],
                    "intent_label": "khac",
                    "intent_confidence": 0.4,
                    "sentiment": None,
                },
            )
    return store, ids


def test_collect_from_store_can_scope_to_one_session():
    store, (sid_a, sid_b) = _store_with_two_sessions()
    assert len(collect_from_store(store)) == 5
    only_b = collect_from_store(store, session_id=sid_b)
    assert len(only_b) == 3
    assert all(r["text"].startswith("phiên B") for r in only_b)


def test_collect_from_store_rejects_an_unknown_session():
    import pytest

    from livelift.nlp.label_llm import LabelPipelineError

    store, _ = _store_with_two_sessions()
    with pytest.raises(LabelPipelineError, match="Không tìm thấy phiên"):
        collect_from_store(store, session_id="khong-co-that")


def test_export_rejects_session_together_with_input(tmp_path, capsys):
    src = tmp_path / "in.jsonl"
    _write_jsonl(src, [{"id": "c1", "text": "giá nhiêu"}])
    rc = main(
        ["export", "--input", str(src), "--session", "abc", "--out-dir", str(tmp_path / "lot")]
    )
    assert rc == 2
    assert "--session chỉ dùng khi đọc từ store" in capsys.readouterr().err
