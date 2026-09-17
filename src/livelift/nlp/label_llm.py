"""Pipeline nhãn LLM cho bộ phân loại ý định — chuẩn bị batch & gộp kết quả.

Biến kế hoạch active learning (docs/benchmarks/intent-classifier.md, mục
"Đường nâng cấp") thành code chạy được. Module này KHÔNG gọi API LLM nào —
nó chỉ chuẩn bị batch để nhóm tự gửi đi 2 LLM bất kỳ (batch API), rồi gộp
kết quả theo quy tắc đồng thuận 2 model + người duyệt bất đồng:

    python -m livelift.nlp.label_llm export --out-dir lot1 --limit 500 \
        --uncertain-first                     # -> batch.jsonl + prompt.txt
    # ... hoặc theo PROTOCOL HAI TẦNG (khuyến nghị, xem prepare_batch):
    python -m livelift.nlp.label_llm export --out-dir lot1 --session <id> \
        --limit 1500 --random-fraction 0.10 --seed 2026 --uncertain-first
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
import random
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from livelift.console import configure as _configure_console
from livelift.ingest.mo_phong import PLATFORM_SIM
from livelift.nlp.labels import INTENT_LABELS, LABEL_EXAMPLES_REAL, LABEL_GUIDELINE
from livelift.nlp.train_intent import DATA as DATASET_PATH

# Hai tầng lấy mẫu của một lô gán nhãn (ghi vào strata.jsonl để phân tích sau)
STRATUM_RANDOM = "random"
STRATUM_UNCERTAIN = "uncertain"


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


NEN_TANG_TONG_HOP: frozenset[str] = frozenset({PLATFORM_SIM})
"""Giá trị ``platform`` của bình luận TỔNG HỢP — không bao giờ vào lô gán nhãn.

``sim`` (:data:`livelift.ingest.mo_phong.PLATFORM_SIM`) là câu do AI soạn sẵn mà
nguồn mô phỏng phát lại để chạy thử Bàn trợ live. Kịch bản ghi rõ
``cam_dung: KHÔNG dùng làm dữ liệu huấn luyện, dữ liệu đánh giá mô hình``. Nguồn
này được bật trên phiên CHẠY THỬ (``dry_run``), mà phiên chạy thử lại là phiên
THẬT (``is_demo=False``) — nên cổng demo bên dưới KHÔNG chặn được nó. Kiểm toán
17/09/2026 đo được: một lượt mô phỏng trên phiên chạy thử đưa nguyên 27 câu tổng
hợp vào ``batch.jsonl`` của lệnh ``export`` quét toàn kho, chỉ còn id/text nên
không còn dấu vết nguồn gốc."""


def _la_binh_luan_tong_hop(row: dict[str, Any]) -> bool:
    return str(row.get("platform") or "") in NEN_TANG_TONG_HOP


def collect_from_store(store: Any, session_id: str | None = None) -> list[dict[str, Any]]:
    """Pull stored comments into export items — one session, or all of them.

    Comments are already scrubbed at ingest (hard rule 1) — ``text_scrubbed``
    is the only text the store has, so the export can never leak PII.

    ``session_id`` scopes the lot to a single observed session, which is what a
    labeling lot must do: prevalence estimated from a mix of sessions belongs
    to no session in particular.

    DEMO GATE (gói DEMO-THẬT): sessions flagged ``is_demo`` are refused —
    skipped in the all-sessions sweep, and a hard error when named explicitly.
    Their "comments" are our own template strings (``DEMO_COMMENTS``); labeling
    them would teach the classifier its own demo script and quietly poison the
    training set — the exact demo-into-science leak the critique rounds vetoed.

    SYNTHETIC GATE (kiểm toán 17/09/2026): rows whose ``platform`` is in
    :data:`NEN_TANG_TONG_HOP` are skipped in BOTH modes, whatever the session
    flags say — a dry-run session may hold real comments and simulated ones
    side by side, and only the real ones may be labeled.
    """
    if session_id is not None:
        session = store.get_session(session_id)
        if session is None:
            raise LabelPipelineError(f"Không tìm thấy phiên: {session_id}")
        if session.get("is_demo"):
            raise LabelPipelineError(
                f"Phiên {session_id} là DỮ LIỆU MẪU (is_demo) — bình luận của nó là "
                "văn mẫu do máy sinh, không được đưa vào lô gán nhãn/huấn luyện "
                "(tiền đăng ký §8.2: demo không vào bất kỳ đầu ra khoa học nào)."
            )
        session_ids = [session_id]
    else:
        session_ids = [s["session_id"] for s in store.list_sessions() if not s.get("is_demo")]
    items: list[dict[str, Any]] = []
    for sid in session_ids:
        for c in store.list_comments(sid):
            if _la_binh_luan_tong_hop(c):
                continue
            items.append(
                {
                    "id": str(c["comment_id"]),
                    "text": str(c.get("text_scrubbed") or ""),
                    "confidence": c.get("intent_confidence"),
                }
            )
    return items


def normalize_input_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Accept both export-item and store-row field names from a JSONL file.

    A store-row dump carries ``platform``: synthetic rows (:data:`NEN_TANG_TONG_HOP`)
    are dropped here too, so ``--input`` is not a way around the store gate.
    """
    items = []
    for i, row in enumerate(rows):
        if _la_binh_luan_tong_hop(row):
            continue
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
    n_random: int = 0
    n_uncertain: int = 0
    strata: dict[str, str] = field(default_factory=dict)
    """id -> ``STRATUM_RANDOM`` / ``STRATUM_UNCERTAIN``. Không đi kèm batch gửi
    LLM (tránh gợi ý cho model), ghi riêng ra ``strata.jsonl``."""


def prepare_batch(
    items: list[dict[str, Any]],
    *,
    uncertain_first: bool = False,
    limit: int | None = None,
    random_fraction: float = 0.0,
    seed: int | None = None,
) -> tuple[list[dict[str, Any]], BatchStats]:
    """Filter empty texts, drop duplicates (same id or same stripped text), then
    pick the lot in TWO STRATA and cap at ``limit``.

    Uncertain-first ordering: rows with confidence ``None`` (keyword baseline
    — the model never scored them) come FIRST, then ascending confidence —
    the classic active-learning priority (least information first).

    WHY TWO STRATA (live-fire 08/09/2026, docs/benchmarks/live-fire-achan.md).
    A pure uncertain-first lot is the right way to *teach* the model but the
    wrong way to *measure* it: it over-samples exactly the comments the model
    is worst at, so the label mix it produces cannot estimate how common each
    intent really is. ``random_fraction`` carves out a simple random sample of
    ALL de-duplicated comments — an unbiased prevalence estimator — while the
    rest stays uncertain-first for learning value. Both strata are recorded in
    ``stats.strata`` so the analysis can use the right subset for the right
    question and never silently pool them.

    Draws use ``random.Random(seed)`` only — an explicit seed is required
    whenever ``random_fraction > 0`` (HARNESS.md §6: mọi RNG nhận seed tường
    minh). With ``random_fraction == 0`` the function is byte-identical to its
    pre-live-fire behaviour, including the deterministic uncertain-first order.
    """
    if not 0.0 <= random_fraction <= 1.0:
        raise LabelPipelineError("--random-fraction phải nằm trong khoảng 0.0–1.0")
    if random_fraction > 0 and seed is None:
        raise LabelPipelineError("Lấy mẫu ngẫu nhiên bắt buộc có --seed để tái lập được")

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

    target = len(kept) if limit is None else min(limit, len(kept))
    rng = random.Random(seed)
    n_random = round(target * random_fraction)
    random_rows = rng.sample(kept, n_random) if n_random else []
    drawn = {r["id"] for r in random_rows}

    rest = [r for r in kept if r["id"] not in drawn]
    if uncertain_first:
        rest.sort(key=lambda r: (r["confidence"] is not None, r["confidence"] or 0.0))
    uncertain_rows = rest[: target - n_random]

    chosen = random_rows + uncertain_rows
    if n_random:
        # Trộn lại để thứ tự dòng trong batch không tiết lộ tầng nào cho LLM
        # (tầng ngẫu nhiên phần lớn là "khac" — xếp thành khối dễ gây mỏ neo).
        rng.shuffle(chosen)

    for row in random_rows:
        stats.strata[row["id"]] = STRATUM_RANDOM
    for row in uncertain_rows:
        stats.strata[row["id"]] = STRATUM_UNCERTAIN
    stats.n_random = len(random_rows)
    stats.n_uncertain = len(uncertain_rows)
    stats.n_exported = len(chosen)
    batch = [{"id": r["id"], "text": r["text"]} for r in chosen]
    return batch, stats


# ---------------------------------------------------------------------------
# export — prompt template (guideline + examples from the authored dataset)
# ---------------------------------------------------------------------------


def load_seed_examples(
    dataset_path: Path | None = None, per_class: int = 8
) -> dict[str, list[str]]:
    """Up to ``per_class`` examples per label, deterministic run-to-run.

    Default source is the authored bootstrap dataset (in file order). Any class
    listed in ``labels.LABEL_EXAMPLES_REAL`` OVERRIDES that with verbatim real
    comments — not merely fills a gap.

    The override matters for ``khac`` specifically. Its 60 authored rows were
    written when ``khac`` still absorbed greetings, praise and product
    questions, so today they contradict ``chao_hoi`` / ``cam_on_khen`` /
    ``hoi_sanpham`` ("chào shop buổi tối" carries label ``khac`` in that file).
    Feeding them to an annotator LLM alongside the new guideline would teach it
    the exact confusion the new classes exist to remove. The dataset itself
    still needs re-labeling before any retrain — see
    docs/benchmarks/live-fire-achan.md.

    A class may end up with fewer than ``per_class`` examples; that is honest
    and fine, the prompt simply shows what actually exists.
    """
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
    for label, real in LABEL_EXAMPLES_REAL.items():
        if label in examples:
            examples[label] = list(real[:per_class])
    return examples


def build_prompt(examples_per_class: int = 8, dataset_path: Path | None = None) -> str:
    """System prompt for the two annotator LLMs: guideline + examples per class.

    The class list, the one-line definitions and the fallback examples all come
    from :mod:`livelift.nlp.labels` — adding a class there is the ONLY edit
    needed for it to appear here, in the validator and in the docs.

    ``examples_per_class`` must be 5..10 — fewer under-specifies the open
    ``khac`` class, more bloats every batch request for no measured gain.
    """
    if not 5 <= examples_per_class <= 10:
        raise LabelPipelineError("Số ví dụ mỗi lớp phải nằm trong khoảng 5–10")
    examples = load_seed_examples(dataset_path, per_class=examples_per_class)
    n = len(INTENT_LABELS)
    lines = [
        "Bạn là bộ gán nhãn Ý ĐỊNH cho bình luận livestream bán hàng TIẾNG VIỆT.",
        f"Gán đúng MỘT nhãn cho mỗi bình luận, thuộc đúng {n} lớp sau",
        "(guideline gốc: docs/benchmarks/intent-classifier.md):",
        "",
    ]
    lines.extend(f"- {label}: {LABEL_GUIDELINE[label]}" for label in INTENT_LABELS)
    lines.extend(
        [
            "",
            "Quy ước câu đa ý định (ví dụ 'size M giá nhiêu'): lấy ý định *hành động",
            "gần nhất với chốt đơn* làm nhãn chính.",
            "AI ĐANG NÓI cũng quyết định nhãn: shop/mod dán bảng giá là bao_gia_shop,",
            "shop hô 'cả nhà chốt đơn nha' là khac — chỉ ý định của KHÁCH mới tính.",
            "Chào hỏi, cảm ơn, khen, cổ vũ KHÔNG phải ý định mua: dùng chao_hoi /",
            "cam_on_khen, tuyệt đối không gán chot_don cho một lời chào.",
            "Bình luận đã qua lọc PII — các placeholder như [SĐT], [ĐỊA CHỈ], [TÊN]",
            "là bình thường, không ảnh hưởng đến nhãn.",
            "Văn bản có thể mất dấu / teencode / viết tắt / emoji — vẫn gán như thường.",
            "",
            f"VÍ DỤ THEO LỚP (tối đa {examples_per_class} ví dụ/lớp; lớp mới lấy ví dụ",
            "nguyên văn từ phiên live thật, xem docs/benchmarks/live-fire-achan.md):",
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
            f"đúng {n} lớp trên, không thêm trường khác, không giải thích.",
        ]
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# merge — pure core
# ---------------------------------------------------------------------------


def validate_labels(rows: list[dict[str, Any]], source_name: str) -> None:
    """Reject any row whose label is outside the declared class set.

    The set (and its size) comes from :data:`livelift.nlp.labels.INTENT_LABELS`
    — never spelled out here, so adding a class needs no edit in this function.
    """
    bad = [(str(r.get("id")), r.get("label")) for r in rows if r.get("label") not in INTENT_LABELS]
    if bad:
        shown = ", ".join(f"id={i}: {label!r}" for i, label in bad[:5])
        more = f" (+{len(bad) - 5} dòng nữa)" if len(bad) > 5 else ""
        raise LabelPipelineError(
            f"{source_name}: {len(bad)} nhãn không thuộc {len(INTENT_LABELS)} lớp "
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
        if args.session:
            raise LabelPipelineError("--session chỉ dùng khi đọc từ store, không đi cùng --input")
        items = normalize_input_rows(read_jsonl(Path(args.input)))
        origin = args.input
    else:
        from livelift.api.store import build_store

        store = build_store()
        try:
            items = collect_from_store(store, session_id=args.session)
        finally:
            store.close()
        origin = f"store ({store.backend})"
        if args.session:
            origin += f", phiên {args.session}"
    batch, stats = prepare_batch(
        items,
        uncertain_first=args.uncertain_first,
        limit=args.limit,
        random_fraction=args.random_fraction,
        seed=args.seed,
    )
    out_dir = Path(args.out_dir)
    write_jsonl(out_dir / "batch.jsonl", batch)
    write_jsonl(
        out_dir / "strata.jsonl",
        [{"id": r["id"], "stratum": stats.strata[r["id"]]} for r in batch],
    )
    prompt = build_prompt(args.examples_per_class)
    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    print(f"nguồn: {origin} — {stats.n_input} bình luận vào")
    print(f"đã lọc: {stats.n_empty} rỗng, {stats.n_duplicate} trùng")
    print(f"đã xuất: {stats.n_exported} bình luận -> {out_dir / 'batch.jsonl'}")
    print(
        f"  tầng ngẫu nhiên (ước lượng prevalence không chệch): {stats.n_random}"
        f" · tầng bất định (giá trị học): {stats.n_uncertain}"
        f" · seed {args.seed}"
    )
    print(f"tầng của từng id -> {out_dir / 'strata.jsonl'}")
    print(
        f"prompt ({len(INTENT_LABELS)} lớp, {args.examples_per_class} ví dụ/lớp) "
        f"-> {out_dir / 'prompt.txt'}"
    )
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
    p_export.add_argument(
        "--session", default=None, help="chỉ lấy bình luận của MỘT phiên (session_id)"
    )
    p_export.add_argument("--out-dir", required=True)
    p_export.add_argument("--limit", type=int, default=None)
    p_export.add_argument(
        "--uncertain-first",
        action="store_true",
        help="sắp theo confidence tăng dần (None = bất định nhất, đứng đầu)",
    )
    p_export.add_argument(
        "--random-fraction",
        type=float,
        default=0.0,
        help="tỷ lệ lô dành cho mẫu ngẫu nhiên đơn giản (vd 0.10) để ước lượng "
        "prevalence không chệch; phần còn lại theo --uncertain-first",
    )
    p_export.add_argument(
        "--seed", type=int, default=2026, help="seed RNG cho tầng ngẫu nhiên (tái lập được)"
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
