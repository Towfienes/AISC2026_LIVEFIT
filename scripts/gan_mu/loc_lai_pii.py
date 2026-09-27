"""Lọc lại PII trong dữ liệu gán nhãn đã lưu, bằng ĐÚNG hàm ``scrub`` của sản phẩm.

    .venv/Scripts/python scripts/gan_mu/loc_lai_pii.py --kiem-tra   # chỉ đếm, không ghi
    .venv/Scripts/python scripts/gan_mu/loc_lai_pii.py              # lọc và ghi đè tại chỗ

Vì sao có script này
--------------------
Bộ lọc PII được sửa ngày 15/09 để bắt tên tài khoản có dấu (``@Nguyễn…``). Dữ
liệu gán nhãn trong ``data/labeling/`` được lưu TRƯỚC ngày đó (08–14/09), nên
quét lại bằng bộ lọc hiện tại còn 57 tên tài khoản (kiểm toán 25/09). Đây là
bước 0 của việc gán mù bằng người: bảng phát cho người gán phải là văn bản đã
lọc bằng bộ lọc hiện hành.

Bất biến script giữ
-------------------
- Chỉ trường văn bản bị thay; mọi trường khác (``id``, ``label``, ``stratum``,
  ``uid``…) và thứ tự dòng giữ nguyên. Script tự kiểm lại điều này sau khi ghi.
- Dòng không có PII giữ nguyên TỪNG BYTE (``scrub`` trả lại văn bản gốc khi
  không tìm thấy gì). Kiểu xuống dòng (CRLF/LF) của tệp được giữ.
- Chạy lần hai không đổi gì (idempotent) — có test khoá.
- Báo cáo chỉ có SỐ ĐẾM theo loại PII, không bao giờ in văn bản bình luận.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from livelift.ingest.pii import scrub  # noqa: E402

LABELING_DIR = REPO_ROOT / "data" / "labeling"

#: (đường dẫn tương đối, định dạng, trường văn bản). Định dạng ``jsonl`` = một
#: đối tượng JSON mỗi dòng; ``tsv`` = ``uid<TAB>văn bản``.
TARGETS: tuple[tuple[str, str, str], ...] = (
    ("lot1-achan-b519f75c/comments_b519f75c.jsonl", "jsonl", "text_scrubbed"),
    ("lot1-achan-b519f75c/batch.jsonl", "jsonl", "text"),
    ("lot1-achan-b519f75c/train_llm.jsonl", "jsonl", "text"),
    ("lot2-da-nguon-10-09/to_label.txt", "tsv", ""),
)


@dataclass
class FileReport:
    path: str
    n_rows: int = 0
    n_rows_changed: int = 0
    pii_before: Counter = field(default_factory=Counter)
    pii_after: Counter = field(default_factory=Counter)

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "n_rows": self.n_rows,
            "n_rows_changed": self.n_rows_changed,
            "pii_before": dict(sorted(self.pii_before.items())),
            "pii_after": dict(sorted(self.pii_after.items())),
        }


def _split_lines(raw: str) -> tuple[list[str], str]:
    """Tách dòng, trả về (dòng không kèm ký tự xuống dòng, kiểu xuống dòng)."""
    newline = "\r\n" if "\r\n" in raw else "\n"
    body = raw[: -len(newline)] if raw.endswith(newline) else raw
    return (body.split(newline) if body else []), newline


def _scrub_text(text: str) -> tuple[str, Counter]:
    result = scrub(text)
    return result.text, Counter(result.counts)


def _process_line(line: str, fmt: str, text_field: str) -> tuple[str, Counter, Counter]:
    """Lọc một dòng. Trả (dòng mới, PII trước, PII sau)."""
    if fmt == "tsv":
        if "\t" not in line:
            return line, Counter(), Counter()
        uid, text = line.split("\t", 1)
        new_text, before = _scrub_text(text)
        after = Counter(scrub(new_text).counts)
        return (line if new_text == text else f"{uid}\t{new_text}"), before, after
    if not line.strip():
        return line, Counter(), Counter()
    obj = json.loads(line)
    text = obj.get(text_field)
    if not isinstance(text, str):
        return line, Counter(), Counter()
    new_text, before = _scrub_text(text)
    after = Counter(scrub(new_text).counts)
    if new_text == text:
        return line, before, after
    obj[text_field] = new_text
    return json.dumps(obj, ensure_ascii=False), before, after


def _non_text_signature(lines: list[str], fmt: str, text_field: str) -> list:
    """Mọi thứ TRỪ trường văn bản — phải trùng khít trước và sau khi lọc."""
    sig = []
    for line in lines:
        if fmt == "tsv":
            sig.append(line.split("\t", 1)[0] if "\t" in line else line)
        elif line.strip():
            obj = json.loads(line)
            obj.pop(text_field, None)
            sig.append(obj)
        else:
            sig.append(None)
    return sig


def process_file(
    path: Path, fmt: str, text_field: str, *, write: bool, rel: str | None = None
) -> FileReport:
    raw = path.read_bytes().decode("utf-8")
    lines, newline = _split_lines(raw)
    report = FileReport(path=rel or path.name, n_rows=len(lines))
    new_lines = []
    for line in lines:
        new_line, before, after = _process_line(line, fmt, text_field)
        report.pii_before.update(before)
        report.pii_after.update(after)
        if new_line != line:
            report.n_rows_changed += 1
        new_lines.append(new_line)
    if _non_text_signature(new_lines, fmt, text_field) != _non_text_signature(
        lines, fmt, text_field
    ):
        raise RuntimeError(f"{path}: lọc làm đổi trường ngoài văn bản — dừng, không ghi")
    if write and report.n_rows_changed:
        out = newline.join(new_lines) + (newline if raw.endswith(newline) else "")
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(out.encode("utf-8"))
        tmp.replace(path)
    return report


def run(root: Path = LABELING_DIR, *, write: bool) -> list[FileReport]:
    reports = []
    for rel, fmt, text_field in TARGETS:
        path = root / rel
        if path.exists():
            reports.append(process_file(path, fmt, text_field, write=write, rel=rel))
    return reports


def _utf8_console() -> None:
    """Console Windows mặc định cp1252: in tên tệp/nhãn tiếng Việt sẽ ném
    ``UnicodeEncodeError`` giữa chừng (đã gặp 25/09 khi chạy ``--kiem-tra``)."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    _utf8_console()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--goc", default=str(LABELING_DIR), help="thư mục data/labeling")
    parser.add_argument("--kiem-tra", action="store_true", help="chỉ đếm, không ghi")
    parser.add_argument("--json", metavar="FILE", help="ghi số đếm (không có văn bản) ra FILE")
    args = parser.parse_args(argv)

    reports = run(Path(args.goc), write=not args.kiem_tra)
    total_before: Counter = Counter()
    total_changed = 0
    for r in reports:
        total_before.update(r.pii_before)
        total_changed += r.n_rows_changed
        print(
            f"{r.path}: {r.n_rows} dòng · PII tìm thấy {dict(r.pii_before) or 0}"
            f" · dòng {'cần sửa' if args.kiem_tra else 'đã sửa'} {r.n_rows_changed}"
        )
    print(f"TỔNG: PII {dict(total_before) or 0} · dòng đổi {total_changed}")
    if args.json:
        Path(args.json).write_text(
            json.dumps(
                {
                    "che_do": "kiem_tra" if args.kiem_tra else "ghi",
                    "tep": [r.as_dict() for r in reports],
                    "tong_pii": dict(total_before),
                    "tong_dong_doi": total_changed,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    # --kiem-tra dùng được như một cổng: còn PII là mã thoát 1.
    return 1 if (args.kiem_tra and total_changed) else 0


if __name__ == "__main__":
    raise SystemExit(main())
