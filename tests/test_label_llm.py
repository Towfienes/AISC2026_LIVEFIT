"""LLM labeling pipeline (gói F): export -> merge -> finalize, no API calls.

Every subcommand runs on tiny hand-made data in tmp_path; the pipeline is
pure logic (HARNESS.md §1) so nothing here needs a network, a model, or a DB.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from livelift.api.store import InMemoryStore
from livelift.nlp.intent import INTENT_LABELS
from livelift.nlp.label_llm import (
    build_prompt,
    collect_from_store,
    load_seed_examples,
    main,
    prepare_batch,
)

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
    # ví dụ được trích thật từ dataset 320 mẫu, đúng số lượng yêu cầu
    examples = load_seed_examples(per_class=6)
    for label in INTENT_LABELS:
        assert len(examples[label]) == 6
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


def test_merge_rejects_label_outside_six_classes(tmp_path, capsys):
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
    assert "không thuộc 6 lớp" in capsys.readouterr().err
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
    assert "không thuộc 6 lớp" in capsys.readouterr().err

    _write_jsonl(consensus, [{"id": "c1", "label": "hoi_gia"}])  # thiếu text
    rc = main(["finalize", "--consensus", str(consensus), "--out", str(out)])
    assert rc == 2
    assert "thiếu trường 'text'" in capsys.readouterr().err
    assert not out.exists()
