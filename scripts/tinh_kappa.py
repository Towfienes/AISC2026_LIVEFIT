"""Độ đồng thuận Cohen κ của gán mù bằng người + chấm lại B0…C2 theo nhãn người.

    .venv/Scripts/python scripts/tinh_kappa.py \
        --bang1 D:/AISC2026/gan-mu-2509/da-gan/bang-nguoi-gan-1.csv \
        --bang2 D:/AISC2026/gan-mu-2509/da-gan/bang-nguoi-gan-2.csv \
        --khoa  D:/AISC2026/gan-mu-2509/khoa/khoa-gan-mu.csv \
        --cham-lai                       # + chấm lại B0–C2 (huấn luyện lại, vài phút)

Đầu ra (mặc định ``docs/benchmarks/intent-eval/``): ``kappa.json`` + ``kappa.md``.
Không tệp nào chứa văn bản bình luận — chỉ mã dòng lô 2, nhãn và số đếm.

Viết TRƯỚC khi có nhãn người (25/09/2026)
-----------------------------------------
Quy tắc đọc kết quả được chốt ở đây và trong
``docs/benchmarks/intent-eval/gan-mu/README.md`` TRƯỚC khi ai nhìn thấy nhãn
người, để không ai chọn cách tính sau khi đã biết số:

1. κ người–người trên toàn bộ dòng cả hai cùng gán hợp lệ — con số chính.
2. κ người–AI cho TỪNG người (nhãn AI = ``gold.txt`` của lô 2), không gộp.
3. Chấm lại: tham chiếu CHÍNH là tập dòng hai người ĐỒNG Ý với nhau; kèm điểm
   theo từng người và điểm theo nhãn AI trên ĐÚNG tập dòng đó để so cặp.
4. Mặc định ``--nhan-train ai``: dự đoán y hệt lần chạy công bố (mô hình học
   nhãn AI như artifact v2 thật sự học), chỉ đổi nhãn dùng để CHẤM.
   ``--nhan-train nguoi`` thay nhãn train lô 2 bằng nhãn của CHÍNH tham chiếu
   đang chấm và chỉ giữ các dòng có trong tham chiếu đó (tham chiếu người →
   nhãn người; hai tham chiếu "AI, …" → vẫn là nhãn AI trên đúng tập dòng ấy).
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import random
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from livelift.nlp import eval_intent as ev  # noqa: E402
from livelift.nlp.labels import INTENT_LABELS  # noqa: E402

OUT_DIR = REPO_ROOT / "docs" / "benchmarks" / "intent-eval"
SEED = 2026
N_BOOTSTRAP = 2000

#: Thang đọc κ của Landis & Koch (1977) — chỉ để diễn giải, không phải ngưỡng đạt.
KAPPA_SCALE: tuple[tuple[float, str], ...] = (
    (0.0, "kém hơn ngẫu nhiên"),
    (0.20, "rất thấp"),
    (0.40, "thấp"),
    (0.60, "trung bình"),
    (0.80, "khá"),
    (1.01, "rất cao"),
)


class TableError(ValueError):
    """Bảng đã gán không dùng được — thông báo nêu đúng dòng, không nêu văn bản."""


# ---------------------------------------------------------------------------
# 1. Đọc bảng
# ---------------------------------------------------------------------------


def _decode(raw: bytes) -> str:
    """Excel lưu "CSV UTF-8" có BOM; "CSV (Comma delimited)" trên máy Việt là cp1258."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1258")


def _delimiter(text: str) -> str:
    """Dấu phân cách đọc từ DÒNG TIÊU ĐỀ, không đoán trên cả mẫu.

    Excel lưu "CSV" bằng dấu phân cách danh sách của cài đặt vùng: máy dùng dấu
    phẩy thập phân thường ra ``;``, máy khác ra ``,``. ``csv.Sniffer`` đoán
    trên nội dung nên dễ sai khi bình luận chứa nhiều dấu phẩy/chấm phẩy; dòng
    tiêu đề thì chỉ gồm tên cột ASCII nên đọc chắc chắn.
    """
    header = text.lstrip("\ufeff").splitlines()[0] if text.strip() else ""
    for delim in (",", ";", "\t"):
        names = {c.strip().strip('"').lower() for c in header.split(delim)}
        if "ma_dong" in names:
            return delim
    return ","


def _reader(text: str) -> csv.DictReader:
    text = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(text, newline=""), delimiter=_delimiter(text))
    if reader.fieldnames:
        reader.fieldnames = [f.strip().lower().lstrip("\ufeff") for f in reader.fieldnames]
    return reader


def parse_label(value: str) -> str | None:
    """Mã nhãn (``hoi_gia``) hoặc số 1–11 theo thứ tự ``INTENT_LABELS``; sai → ``None``."""
    v = (value or "").strip().lower()
    if v in INTENT_LABELS:
        return v
    if v.isdigit() and 1 <= int(v) <= len(INTENT_LABELS):
        return INTENT_LABELS[int(v) - 1]
    return None


def read_labeled_table(path: Path) -> tuple[dict[str, str], dict[str, Any]]:
    """``{ma_dong: nhãn}`` + chẩn đoán (dòng trống, nhãn sai, mã trùng)."""
    reader = _reader(_decode(Path(path).read_bytes()))
    fields = set(reader.fieldnames or [])
    if not {"ma_dong", "nhan"} <= fields:
        raise TableError(f"{path}: thiếu cột ma_dong/nhan (có: {sorted(fields)})")
    labels: dict[str, str] = {}
    blank: list[str] = []
    invalid: list[tuple[str, str]] = []
    duplicate: list[str] = []
    for row in reader:
        code = (row.get("ma_dong") or "").strip()
        if not code:
            continue
        if code in labels or code in blank:
            duplicate.append(code)
            continue
        raw = (row.get("nhan") or "").strip()
        if not raw:
            blank.append(code)
            continue
        label = parse_label(raw)
        if label is None:
            invalid.append((code, raw[:40]))
            continue
        labels[code] = label
    return labels, {"blank": blank, "invalid": invalid, "duplicate": duplicate}


def read_key(path: Path) -> dict[str, str]:
    reader = _reader(_decode(Path(path).read_bytes()))
    if not {"ma_dong", "uid_lo2"} <= set(reader.fieldnames or []):
        raise TableError(f"{path}: khoá thiếu cột ma_dong/uid_lo2")
    key = {r["ma_dong"].strip(): r["uid_lo2"].strip() for r in reader if r.get("ma_dong")}
    if len(set(key.values())) != len(key):
        raise TableError(f"{path}: khoá có uid lô 2 trùng")
    return key


def read_ai_labels(gold_dir: Path) -> dict[str, str]:
    out = {}
    for line in (gold_dir / "gold.txt").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) == 2:
            out[parts[0]] = parts[1]
    return out


def check_table(
    labels: dict[str, str], diag: dict[str, Any], key: dict[str, str], name: str
) -> list[str]:
    """Danh sách lỗi chặn (rỗng = dùng được)."""
    problems = []
    unknown = sorted(set(labels) - set(key))
    missing = sorted(set(key) - set(labels) - set(diag["blank"]))
    if unknown:
        problems.append(f"{name}: {len(unknown)} mã dòng không có trong khoá, ví dụ {unknown[:3]}")
    if missing:
        problems.append(f"{name}: thiếu {len(missing)} mã dòng của khoá, ví dụ {missing[:3]}")
    if diag["blank"]:
        problems.append(f"{name}: {len(diag['blank'])} dòng chưa gán, ví dụ {diag['blank'][:3]}")
    if diag["invalid"]:
        problems.append(
            f"{name}: {len(diag['invalid'])} nhãn không hợp lệ, ví dụ {diag['invalid'][:3]}"
        )
    if diag["duplicate"]:
        problems.append(f"{name}: mã dòng lặp {diag['duplicate'][:3]}")
    return problems


# ---------------------------------------------------------------------------
# 2. Cohen κ
# ---------------------------------------------------------------------------


def cohen_kappa(a: list[str], b: list[str]) -> float:
    """κ = (p_o − p_e) / (1 − p_e). Hai người cùng dùng MỘT lớp duy nhất và
    đồng ý hết thì p_e = 1: trả 1,0 (đồng ý hoàn toàn) thay vì chia cho 0."""
    if len(a) != len(b):
        raise ValueError("hai dãy nhãn khác độ dài")
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    pe = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return (po - pe) / (1 - pe)


def bootstrap_kappa(
    a: list[str], b: list[str], *, n: int = N_BOOTSTRAP, seed: int = SEED
) -> tuple[float, float]:
    """KTC95 percentile, lấy lại mẫu theo DÒNG (cùng cảnh báo như macro-F1: bất
    định thật ở cấp buổi live lớn hơn)."""
    if not a:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)
    size = len(a)
    scores = []
    for _ in range(n):
        idx = [rng.randrange(size) for _ in range(size)]
        scores.append(cohen_kappa([a[i] for i in idx], [b[i] for i in idx]))
    scores.sort()
    lo = scores[max(0, int(0.025 * n))]
    hi = scores[min(n - 1, int(0.975 * n + 0.999999) - 1)]
    return (round(lo, 4), round(hi, 4))


def kappa_band(k: float) -> str:
    if k != k:  # NaN
        return "không xác định"
    if k < 0:
        return KAPPA_SCALE[0][1]
    for upper, text in KAPPA_SCALE[1:]:
        if k <= upper:
            return text
    return KAPPA_SCALE[-1][1]


def agreement(a: dict[str, str], b: dict[str, str], *, n_boot: int = N_BOOTSTRAP) -> dict:
    """Đồng thuận trên các khoá có ở CẢ HAI phía (thứ tự khoá cố định)."""
    common = sorted(set(a) & set(b))
    xa = [a[k] for k in common]
    xb = [b[k] for k in common]
    k = cohen_kappa(xa, xb)
    act_a = ["hanh_dong" if x in ev.ACTION_LABELS else "khac" for x in xa]
    act_b = ["hanh_dong" if x in ev.ACTION_LABELS else "khac" for x in xb]
    return {
        "n": len(common),
        "ty_le_dong_y": round(sum(x == y for x, y in zip(xa, xb, strict=True)) / len(common), 4)
        if common
        else None,
        "kappa": round(k, 4),
        "kappa_ktc95_bootstrap": list(bootstrap_kappa(xa, xb, n=n_boot)),
        "dien_giai_landis_koch": kappa_band(k),
        "kappa_nhi_phan_hanh_dong": round(cohen_kappa(act_a, act_b), 4),
        "ma_tran": {
            t: dict(Counter(y for x, y in zip(xa, xb, strict=True) if x == t))
            for t in sorted(set(xa))
        },
    }


# ---------------------------------------------------------------------------
# 3. Chấm lại B0…C2 theo nhãn người
# ---------------------------------------------------------------------------


def predict_loso(
    factory: ev.SystemFactory, gold: list[ev.GoldRow], extra: list[ev.TrainRow]
) -> dict[str, str]:
    """Dự đoán ngoài-fold cho từng uid — gọi CHÍNH ``ev.predict_out_of_fold``
    mà ``evaluate_system`` dùng (leave-one-session-out + rào chắn trùng văn
    bản), nên ở chế độ ``ai`` dự đoán trùng khít lần chạy công bố."""
    folds, _n_leaked = ev.predict_out_of_fold(factory, gold, extra)
    out: dict[str, str] = {}
    for _session, rows, preds in folds:
        out.update((row.uid, pred) for row, pred in zip(rows, preds, strict=True))
    return out


def score(
    reference: dict[str, str], preds: dict[str, str], strata: dict[str, str]
) -> dict[str, Any]:
    uids = sorted(set(reference) & set(preds))
    yt = [reference[u] for u in uids]
    yp = [preds[u] for u in uids]
    rand = [i for i, u in enumerate(uids) if strata.get(u) == "random"]
    rt = [yt[i] for i in rand]
    rp = [yp[i] for i in rand]
    return {
        "n": len(uids),
        "macro_f1": round(ev.macro_f1(yt, yp), 4),
        "macro_f1_ktc95": list(ev.bootstrap_macro_f1(yt, yp)),
        "accuracy": round(ev.accuracy(yt, yp), 4),
        "action_precision": ev.action_precision(yt, yp),
        "action_recall": ev.action_recall(yt, yp),
        "tang_ngau_nhien": {
            "n": len(rt),
            "macro_f1": round(ev.macro_f1(rt, rp), 4) if rt else None,
            "action_precision": ev.action_precision(rt, rp),
            "action_recall": ev.action_recall(rt, rp),
        },
    }


def rescore(
    gold: list[ev.GoldRow],
    extra: list[ev.TrainRow],
    references: dict[str, dict[str, str]],
    systems: list[tuple[str, ev.SystemFactory]],
    *,
    train_labels: str = "ai",
) -> list[dict[str, Any]]:
    """Mỗi hệ thống × mỗi tham chiếu. ``references`` = ``{tên: {uid lô 2: nhãn}}``."""
    strata = {r.uid: r.stratum for r in gold}
    results = []
    for name, factory in systems:
        entry: dict[str, Any] = {"he_thong": name, "ma": name.split(" ", 1)[0], "tham_chieu": {}}
        if train_labels == "ai":
            preds = predict_loso(factory, gold, extra)
            for ref_name, ref in references.items():
                entry["tham_chieu"][ref_name] = score(ref, preds, strata)
        else:
            for ref_name, ref in references.items():
                gold_ref = [replace(r, label=ref[r.uid]) for r in gold if r.uid in ref]
                preds = predict_loso(factory, gold_ref, extra)
                entry["tham_chieu"][ref_name] = score(ref, preds, strata)
        results.append(entry)
    return results


def pick_systems(codes: list[str] | None) -> list[tuple[str, ev.SystemFactory]]:
    """B0…C2 (C3 bỏ: ngưỡng tự chọn đã bị loại, xem 03-NLP §6.2)."""
    systems = ev.baseline_systems() + ev.improved_systems()[:2]
    if codes:
        wanted = {c.strip().upper() for c in codes}
        systems = [s for s in systems if s[0].split(" ", 1)[0].upper() in wanted]
    return systems


# ---------------------------------------------------------------------------
# 4. Báo cáo
# ---------------------------------------------------------------------------


def render_markdown(report: dict[str, Any]) -> str:
    f = ev._fmt  # noqa: SLF001 — cùng định dạng số với results.md
    lines = [
        "# Gán mù bằng người — Cohen κ và chấm lại theo nhãn người",
        "",
        f"*Sinh bởi `scripts/tinh_kappa.py` · {report['generated_at']}*",
        "",
        "> Nhãn AI = nhãn tham chiếu do tác tử AI gán ngày 09/09/2026 (`gold.txt` lô 2).",
        "> Hai người gán độc lập trên bảng xáo trộn không kèm nhãn AI (seed xáo trộn",
        "> giữ bí mật trong `khoa/seed-gan-mu.json` tới khi công bố tệp này).",
        "> KTC95 bootstrap theo dòng, 2.000 lần, seed 2026.",
        "",
        "## Độ đồng thuận",
        "",
        "| Cặp | n | Tỷ lệ đồng ý | κ | KTC95 | Diễn giải | κ nhị phân hành động |",
        "|---|---:|---:|---:|---|---|---:|",
    ]
    for pair, a in report["dong_thuan"].items():
        lines.append(
            f"| {pair} | {a['n']} | {f(a['ty_le_dong_y'])} | **{f(a['kappa'])}** | "
            f"{ev._ci(a['kappa_ktc95_bootstrap'])} | {a['dien_giai_landis_koch']} | "  # noqa: SLF001
            f"{f(a['kappa_nhi_phan_hanh_dong'])} |"
        )
    lines.append("")
    if report.get("cham_lai"):
        lines += [
            f"## Chấm lại B0–C2 (nhãn train lô 2: `{report['nhan_train']}`)",
            "",
            "| Hệ thống | Tham chiếu | n | macro-F1 | KTC95 | Accuracy | Precision hành động "
            "| Recall hành động |",
            "|---|---|---:|---:|---|---:|---|---|",
        ]
        for e in report["cham_lai"]:
            for ref_name, s in e["tham_chieu"].items():
                lines.append(
                    f"| {e['ma']} | {ref_name} | {s['n']} | **{f(s['macro_f1'])}** | "
                    f"{ev._ci(s['macro_f1_ktc95'])} | {f(s['accuracy'])} | "  # noqa: SLF001
                    f"{ev._rate(s['action_precision'], 'precision')} | "  # noqa: SLF001
                    f"{ev._rate(s['action_recall'], 'recall')} |"  # noqa: SLF001
                )
        lines.append("")
    return "\n".join(lines) + "\n"


def run(
    bang1: Path,
    bang2: Path,
    khoa: Path,
    *,
    gold_dir: Path = ev.GOLD_DIR,
    cham_lai: bool = False,
    systems: list[str] | None = None,
    train_labels: str = "ai",
    extra: list[ev.TrainRow] | None = None,
    n_boot: int = N_BOOTSTRAP,
) -> dict[str, Any]:
    key = read_key(khoa)
    l1, d1 = read_labeled_table(bang1)
    l2, d2 = read_labeled_table(bang2)
    problems = check_table(l1, d1, key, "bảng 1") + check_table(l2, d2, key, "bảng 2")
    if problems:
        raise TableError("\n".join(problems))
    ai = read_ai_labels(gold_dir)
    h1 = {key[c]: lb for c, lb in l1.items()}
    h2 = {key[c]: lb for c, lb in l2.items()}
    ai_rows = {u: ai[u] for u in h1 if u in ai}
    consensus = {u: lb for u, lb in h1.items() if h2.get(u) == lb}
    report: dict[str, Any] = {
        "generated_at": __import__("datetime")
        .datetime.now()
        .astimezone()
        .isoformat(timespec="seconds"),
        "nhan_ai": "gold.txt lô 2 — tác tử AI gán 09/09/2026",
        "n_khoa": len(key),
        "n_dong_thuan_hai_nguoi": len(consensus),
        "dong_thuan": {
            "người 1 – người 2": agreement(h1, h2, n_boot=n_boot),
            "người 1 – AI": agreement(h1, ai_rows, n_boot=n_boot),
            "người 2 – AI": agreement(h2, ai_rows, n_boot=n_boot),
            "đồng thuận 2 người – AI": agreement(consensus, ai_rows, n_boot=n_boot),
        },
        "nhan_train": train_labels,
    }
    if cham_lai:
        gold = ev.load_gold_lot2(gold_dir)
        if extra is None:
            extra = ev.load_authored() + ev.load_llm_lot()
        references = {
            "đồng thuận 2 người (CHÍNH)": consensus,
            "AI, cùng tập dòng đồng thuận": {u: ai[u] for u in consensus if u in ai},
            "người 1": h1,
            "người 2": h2,
            "AI, toàn bộ": {u: ai[u] for u in h1 if u in ai},
        }
        report["cham_lai"] = rescore(
            gold, extra, references, pick_systems(systems), train_labels=train_labels
        )
    return report


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # console Windows mặc định cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--bang1", required=True, type=Path)
    parser.add_argument("--bang2", required=True, type=Path)
    parser.add_argument("--khoa", required=True, type=Path)
    parser.add_argument("--goc-lo2", type=Path, default=ev.GOLD_DIR, help="thư mục lô 2")
    parser.add_argument("--cham-lai", action="store_true", help="chấm lại B0–C2")
    parser.add_argument("--he-thong", help="mã hệ thống, ví dụ B0,B2,C2 (mặc định B0–C2)")
    parser.add_argument("--nhan-train", choices=("ai", "nguoi"), default="ai")
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)
    try:
        report = run(
            args.bang1,
            args.bang2,
            args.khoa,
            gold_dir=args.goc_lo2,
            cham_lai=args.cham_lai,
            systems=args.he_thong.split(",") if args.he_thong else None,
            train_labels=args.nhan_train,
        )
    except TableError as exc:
        print(f"BẢNG CHƯA DÙNG ĐƯỢC:\n{exc}", file=sys.stderr)
        return 2
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "kappa.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out_dir / "kappa.md").write_text(render_markdown(report), encoding="utf-8")
    for pair, a in report["dong_thuan"].items():
        print(f"{pair:<26} n={a['n']:<4} κ={a['kappa']:.3f} {a['kappa_ktc95_bootstrap']}")
    print(f"đã ghi: {args.out_dir / 'kappa.json'} · {args.out_dir / 'kappa.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
