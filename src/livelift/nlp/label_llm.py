"""Pipeline nhãn LLM cho bộ phân loại ý định — chuẩn bị batch & gộp kết quả.

Biến kế hoạch active learning (docs/benchmarks/intent-classifier.md, mục
"Đường nâng cấp") thành code chạy được. Module này KHÔNG gọi API LLM nào —
nó chỉ chuẩn bị batch để nhóm tự gửi đi 2 LLM bất kỳ (batch API), rồi gộp
kết quả theo quy tắc đồng thuận 2 model + người duyệt bất đồng:

    python -m livelift.nlp.label_llm export --out-dir lot1 --limit 500 \
        --uncertain-first                     # -> batch.jsonl + prompt.txt
    # ... nhóm gửi batch.jsonl + prompt.txt đi 2 LLM, nhận về 2 file {id, label}
    python -m livelift.nlp.label_llm merge --model-a a.jsonl --model-b b.jsonl \
        --batch lot1/batch.jsonl --out-dir lot1
    # ... người duyệt xử lý lot1/disagreements.jsonl thành reviewed.jsonl
    python -m livelift.nlp.label_llm finalize --consensus lot1/consensus.jsonl \
        --reviewed lot1/reviewed.jsonl --out lot1/train_extra.jsonl

Văn liệu: quy trình LLM-as-annotator hai model độc lập, chỉ giữ nhãn khi hai
model đồng thuận và đưa bất đồng cho người duyệt (ACL 2024 Workshop NLP+CSS;
ViGoEmotions 2026 áp dụng cho tiếng Việt). Quy trình đầy đủ + chi phí ước
tính: docs/benchmarks/llm-labeling.md.

Toàn bộ logic quyết định là hàm thuần (HARNESS.md §1): nhận dữ liệu, trả dữ
liệu; I/O (đọc/ghi file, store) nằm ở các hàm ``_cmd_*`` mỏng bên ngoài.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from livelift.console import configure as _configure_console
from livelift.nlp.intent import INTENT_LABELS
from livelift.nlp.train_intent import DATA as DATASET_PATH


class LabelPipelineError(ValueError):
    """Input data violates the pipeline contract — reported in Vietnamese."""


# ---------------------------------------------------------------------------
# JSONL I/O (thin edge)
# ---------------------------------------------------------------------------


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise LabelPipelineError(f"Không tìm thấy file: {path}")
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise LabelPipelineError(
                    f"{path.name} dòng {line_no}: không phải JSON hợp lệ"
                ) from exc
            if not isinstance(row, dict):
                raise LabelPipelineError(
                    f"{path.name} dòng {line_no}: mỗi dòng phải là một object JSON"
                )
            rows.append(row)
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# export — pure core
# ---------------------------------------------------------------------------


def collect_from_store(store: Any) -> list[dict[str, Any]]:
    """Pull every stored comment (all sessions) into export items.

    Comments are already scrubbed at ingest (hard rule 1) — ``text_scrubbed``
    is the only text the store has, so the export can never leak PII.
    """
    items: list[dict[str, Any]] = []
    for session in store.list_sessions():
        for c in store.list_comments(session["session_id"]):
            items.append(
                {
                    "id": str(c["comment_id"]),
                    "text": str(c.get("text_scrubbed") or ""),
                    "confidence": c.get("intent_confidence"),
                }
            )
    return items


def normalize_input_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Accept both export-item and store-row field names from a JSONL file."""
    items = []
    for i, row in enumerate(rows):
        rid = row.get("id") or row.get("comment_id") or f"row-{i + 1}"
        text = row.get("text")
        if text is None:
            text = row.get("text_scrubbed", "")
        conf = row.get("confidence")
        if conf is None:
            conf = row.get("intent_confidence")
        items.append({"id": str(rid), "text": str(text), "confidence": conf})
    return items


@dataclass
class BatchStats:
    n_input: int = 0
    n_empty: int = 0
    n_duplicate: int = 0
    n_exported: int = 0


def prepare_batch(
    items: list[dict[str, Any]],
    *,
    uncertain_first: bool = False,
    limit: int | None = None,
) -> tuple[list[dict[str, Any]], BatchStats]:
    """Filter empty texts, drop duplicates (same id or same stripped text),
    optionally order least-confident first, and cap at ``limit``.

    Uncertain-first ordering: rows with confidence ``None`` (keyword baseline
    — the model never scored them) come FIRST, then ascending confidence —
    the classic active-learning priority (least information first).
    """
    stats = BatchStats(n_input=len(items))
    seen_ids: set[str] = set()
    seen_texts: set[str] = set()
    kept: list[dict[str, Any]] = []
    for item in items:
        text = str(item.get("text", "")).strip()
        if not text:
            stats.n_empty += 1
            continue
        rid = str(item.get("id", ""))
        if rid in seen_ids or text in seen_texts:
            stats.n_duplicate += 1
            continue
        seen_ids.add(rid)
        seen_texts.add(text)
        kept.append({"id": rid, "text": text, "confidence": item.get("confidence")})
    if uncertain_first:
        kept.sort(key=lambda r: (r["confidence"] is not None, r["confidence"] or 0.0))
    if limit is not None:
        kept = kept[:limit]
    stats.n_exported = len(kept)
    batch = [{"id": r["id"], "text": r["text"]} for r in kept]
    return batch, stats


# ---------------------------------------------------------------------------
# export — prompt template (guideline + examples from the authored dataset)
# ---------------------------------------------------------------------------

# One-line Vietnamese definition per label, condensed from the labeling
# guideline in docs/benchmarks/intent-classifier.md and the keyword semantics
# in livelift.nlp.intent.
LABEL_GUIDELINE: dict[str, str] = {
    "hoi_gia": "hỏi giá sản phẩm (giá bao nhiêu, nhiêu tiền, bn, combo giá sao...)",
    "hoi_size": "hỏi size / cân nặng / chiều cao / form dáng để chọn cỡ",
    "che_dat": "chê giá đắt / mắc / cao (phàn nàn về giá, KHÔNG phải hỏi giá)",
    "chot_don": "chốt đơn, đặt mua, order (hành động mua: 'chốt', 'lấy 1', 'đặt hàng'...)",
    "van_chuyen": "hỏi giao hàng / phí ship / COD / thời gian nhận hàng",
    "khac": "mọi bình luận không thuộc 5 ý định trên (chào hỏi, khen chê chung, spam...)",
}


def load_seed_examples(
    dataset_path: Path | None = None, per_class: int = 8
) -> dict[str, list[str]]:
    """First ``per_class`` examples per label from the authored 320-sample
    dataset (deterministic — the prompt is reproducible run-to-run)."""
    path = dataset_path or DATASET_PATH
    examples: dict[str, list[str]] = {label: [] for label in INTENT_LABELS}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            label, text = row.get("label"), row.get("text")
            if label in examples and text and len(examples[label]) < per_class:
                examples[label].append(text)
    return examples


def build_prompt(examples_per_class: int = 8, dataset_path: Path | None = None) -> str:
    """System prompt for the two annotator LLMs: 6-class guideline + examples.

    ``examples_per_class`` must be 5..10 — fewer under-specifies the open
    ``khac`` class, more bloats every batch request for no measured gain.
    """
    if not 5 <= examples_per_class <= 10:
        raise LabelPipelineError("Số ví dụ mỗi lớp phải nằm trong khoảng 5–10")
    examples = load_seed_examples(dataset_path, per_class=examples_per_class)
    lines = [
        "Bạn là bộ gán nhãn Ý ĐỊNH cho bình luận livestream bán hàng TIẾNG VIỆT.",
        "Gán đúng MỘT nhãn cho mỗi bình luận, thuộc đúng 6 lớp sau",
        "(guideline gốc: docs/benchmarks/intent-classifier.md):",
        "",
    ]
    lines.extend(f"- {label}: {LABEL_GUIDELINE[label]}" for label in INTENT_LABELS)
    lines.extend(
        [
            "",
            "Quy ước câu đa ý định (ví dụ 'size M giá nhiêu'): lấy ý định *hành động",
            "gần nhất với chốt đơn* làm nhãn chính.",
            "Bình luận đã qua lọc PII — các placeholder như [SĐT], [ĐỊA CHỈ], [EMAIL]",
            "là bình thường, không ảnh hưởng đến nhãn.",
            "Văn bản có thể mất dấu / teencode / viết tắt / emoji — vẫn gán như thường.",
            "",
            f"VÍ DỤ THEO LỚP ({examples_per_class} ví dụ/lớp, trích từ bộ dữ liệu biên soạn):",
        ]
    )
    for label in INTENT_LABELS:
        lines.append(f"\n### {label}")
        lines.extend(f'- "{text}"' for text in examples[label])
    lines.extend(
        [
            "",
            'ĐẦU VÀO: mỗi dòng một JSON {"id": ..., "text": ...}.',
            'ĐẦU RA: mỗi dòng một JSON {"id": ..., "label": ...} — label phải thuộc',
            "đúng 6 lớp trên, không thêm trường khác, không giải thích.",
        ]
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# merge — pure core
# ---------------------------------------------------------------------------


def validate_labels(rows: list[dict[str, Any]], source_name: str) -> None:
    """Reject any row whose label is outside the 6 pre-registered classes."""
    bad = [(str(r.get("id")), r.get("label")) for r in rows if r.get("label") not in INTENT_LABELS]
    if bad:
        shown = ", ".join(f"id={i}: {label!r}" for i, label in bad[:5])
        more = f" (+{len(bad) - 5} dòng nữa)" if len(bad) > 5 else ""
        raise LabelPipelineError(
            f"{source_name}: {len(bad)} nhãn không thuộc 6 lớp "
            f"{list(INTENT_LABELS)} — bị từ chối: {shown}{more}"
        )


@dataclass
class MergeResult:
    consensus: list[dict[str, Any]] = field(default_factory=list)
    disagreements: list[dict[str, Any]] = field(default_factory=list)
    n_total: int = 0
    agreement_rate: float = 0.0
    label_distribution: dict[str, int] = field(default_factory=dict)


def merge_labels(
    rows_a: list[dict[str, Any]],
    rows_b: list[dict[str, Any]],
    id_to_text: dict[str, str],
) -> MergeResult:
    """Consensus rule: keep a label only when BOTH models agree; everything
    else (different labels, or an id one model skipped) goes to the human
    reviewer WITH the text — the reviewer must never have to look ids up."""
    validate_labels(rows_a, "model-a")
    validate_labels(rows_b, "model-b")
    labels_a = {str(r["id"]): r["label"] for r in rows_a if "id" in r}
    labels_b = {str(r["id"]): r["label"] for r in rows_b if "id" in r}
    ordered_ids = list(labels_a)
    ordered_ids.extend(i for i in labels_b if i not in labels_a)

    result = MergeResult(n_total=len(ordered_ids))
    for rid in ordered_ids:
        la, lb = labels_a.get(rid), labels_b.get(rid)
        text = id_to_text.get(rid)
        if la is not None and la == lb:
            result.consensus.append({"id": rid, "text": text, "label": la})
        else:
            result.disagreements.append({"id": rid, "text": text, "label_a": la, "label_b": lb})
    if result.n_total:
        result.agreement_rate = len(result.consensus) / result.n_total
    result.label_distribution = dict(Counter(r["label"] for r in result.consensus))
    return result


# ---------------------------------------------------------------------------
# finalize — pure core
# ---------------------------------------------------------------------------

SOURCE_CONSENSUS = "llm-consensus"
SOURCE_HUMAN = "human"


def finalize_rows(
    consensus_rows: list[dict[str, Any]],
    reviewed_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Consensus + human-reviewed rows -> training rows for train_intent.py.

    Output format is exactly what ``train_intent.load_dataset`` reads
    ({"text", "label"}) plus a ``source`` field for provenance tracing.
    A reviewed row with the same id OVERRIDES the consensus row (the human
    verdict wins); ids only in the reviewed file are appended.
    """
    reviewed_rows = reviewed_rows or []
    validate_labels(consensus_rows, "consensus")
    validate_labels(reviewed_rows, "người-duyệt")
    merged: dict[str, dict[str, Any]] = {}
    for rows, source in ((consensus_rows, SOURCE_CONSENSUS), (reviewed_rows, SOURCE_HUMAN)):
        for i, row in enumerate(rows):
            text = str(row.get("text") or "").strip()
            if not text:
                raise LabelPipelineError(
                    f"Dòng {i + 1} ({source}): thiếu trường 'text' — file train cần text"
                )
            rid = str(row.get("id") or f"{source}-{i + 1}")
            merged[rid] = {"text": text, "label": row["label"], "source": source}
    return list(merged.values())


# ---------------------------------------------------------------------------
# CLI (thin edge)
# ---------------------------------------------------------------------------


def _cmd_export(args: argparse.Namespace) -> int:
    if args.input:
        items = normalize_input_rows(read_jsonl(Path(args.input)))
        origin = args.input
    else:
        from livelift.api.store import build_store

        store = build_store()
        try:
            items = collect_from_store(store)
        finally:
            store.close()
        origin = f"store ({store.backend})"
    batch, stats = prepare_batch(items, uncertain_first=args.uncertain_first, limit=args.limit)
    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / "batch.jsonl", batch)
    prompt = build_prompt(args.examples_per_class)
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    print(f"nguồn: {origin} — {stats.n_input} bình luận vào")
    print(f"đã lọc: {stats.n_empty} rỗng, {stats.n_duplicate} trùng")
    print(f"đã xuất: {stats.n_exported} bình luận -> {out_dir / 'batch.jsonl'}")
    print(f"prompt ({args.examples_per_class} ví dụ/lớp) -> {out_dir / 'prompt.txt'}")
    if not batch:
        print("CHÚ Ý: không có bình luận nào để gán nhãn — kiểm tra lại nguồn dữ liệu.")
    return 0


def _cmd_merge(args: argparse.Namespace) -> int:
    rows_a = read_jsonl(Path(args.model_a))
    rows_b = read_jsonl(Path(args.model_b))
    batch = read_jsonl(Path(args.batch))
    id_to_text = {str(r["id"]): str(r.get("text", "")) for r in batch if "id" in r}
    result = merge_labels(rows_a, rows_b, id_to_text)
    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / "consensus.jsonl", result.consensus)
    write_jsonl(out_dir / "disagreements.jsonl", result.disagreements)
    print(
        f"tổng {result.n_total} id — đồng thuận {len(result.consensus)} "
        f"({result.agreement_rate:.1%}), bất đồng {len(result.disagreements)}"
    )
    print(f"phân phối nhãn đồng thuận: {result.label_distribution}")
    print(f"-> {out_dir / 'consensus.jsonl'}")
    print(f"-> {out_dir / 'disagreements.jsonl'} (kèm text cho người duyệt)")
    return 0


def _cmd_finalize(args: argparse.Namespace) -> int:
    consensus = read_jsonl(Path(args.consensus))
    reviewed = read_jsonl(Path(args.reviewed)) if args.reviewed else []
    rows = finalize_rows(consensus, reviewed)
    write_jsonl(Path(args.out), rows)
    dist = Counter(r["source"] for r in rows)
    print(
        f"đã ghi {len(rows)} mẫu train -> {args.out} "
        f"({dist.get(SOURCE_CONSENSUS, 0)} {SOURCE_CONSENSUS}, "
        f"{dist.get(SOURCE_HUMAN, 0)} {SOURCE_HUMAN})"
    )
    print("dùng file này để bổ sung dataset rồi chạy: python -m livelift.nlp.train_intent")
    return 0


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    parser = argparse.ArgumentParser(prog="python -m livelift.nlp.label_llm", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_export = sub.add_parser("export", help="xuất batch JSONL + prompt template cho 2 LLM")
    p_export.add_argument("--input", default=None, help="file JSONL vào (mặc định: đọc từ store)")
    p_export.add_argument("--out-dir", required=True)
    p_export.add_argument("--limit", type=int, default=None)
    p_export.add_argument(
        "--uncertain-first",
        action="store_true",
        help="sắp theo confidence tăng dần (None = bất định nhất, đứng đầu)",
    )
    p_export.add_argument("--examples-per-class", type=int, default=8, help="5–10 ví dụ/lớp")

    p_merge = sub.add_parser("merge", help="gộp 2 file nhãn LLM -> consensus + disagreements")
    p_merge.add_argument("--model-a", required=True)
    p_merge.add_argument("--model-b", required=True)
    p_merge.add_argument("--batch", required=True, help="batch.jsonl đã export (để lấy text)")
    p_merge.add_argument("--out-dir", required=True)

    p_final = sub.add_parser("finalize", help="consensus + người duyệt -> file train JSONL")
    p_final.add_argument("--consensus", required=True)
    p_final.add_argument("--reviewed", default=None, help="file người duyệt (cùng format)")
    p_final.add_argument("--out", required=True)

    args = parser.parse_args(argv)
    handlers = {"export": _cmd_export, "merge": _cmd_merge, "finalize": _cmd_finalize}
    try:
        return handlers[args.command](args)
    except LabelPipelineError as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
