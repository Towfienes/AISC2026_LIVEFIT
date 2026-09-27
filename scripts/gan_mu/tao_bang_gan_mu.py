"""Sinh bảng gán nhãn MÙ cho hai người gán — 393 dòng tập test lô 2.

    .venv/Scripts/python scripts/gan_mu/tao_bang_gan_mu.py \
        --ra D:/AISC2026/gan-mu-2509 \
        --bam docs/benchmarks/intent-eval/gan-mu
    # sinh lại đúng từng byte: thêm --seed <seed trong khoa/seed-gan-mu.json>

Vì sao
------
Nhãn tham chiếu hiện có của 393 dòng test do một tác tử AI gán (đính chính
15/09). Mọi con số NLP vì vậy là mức đồng thuận với nhãn AI. Muốn nói "đúng so
với người" thì phải có nhãn người, gán ĐỘC LẬP, KHÔNG nhìn nhãn AI. Script này
chuẩn bị đúng việc đó (việc M-04 trong kế hoạch nộp hồ sơ).

Thiết kế
--------
- Mỗi dòng nhận một mã mù ``GM`` + 6 ký tự hex rút từ ``random.Random(seed)``.
  Mã cũ (``A0019``/``B0304``) lộ tầng rút mẫu (A = theo dự đoán của mô hình,
  B = ngẫu nhiên) nên KHÔNG được xuất hiện trong bảng phát.
- Hai bảng cùng tập mã nhưng XÁO TRỘN KHÁC NHAU (seed+1, seed+2) để hai người
  không chịu cùng một hiệu ứng thứ tự.
- **Seed BÍ MẬT cho tới khi công bố κ.** Danh sách được xáo trộn đi ra từ
  ``to_label.txt`` sắp theo uid, mà mọi uid ``A…`` đứng trước ``B…``. Nếu seed
  công khai (bản đầu dùng seed cố định 20260925 ghi trong mã), ai có repo cũng
  tính ngược được vị trí của từng dòng trong bảng → tầng A/B mà không cần dữ
  liệu nào (phản biện 25/09 kiểm: đúng 393/393 dòng ở cả hai bảng). Vì vậy mặc
  định seed rút từ ``secrets`` và chỉ ghi vào ``khoa/seed-gan-mu.json`` (không
  phát, không commit); băm SHA-256 của bảng/khoá vẫn được commit TRƯỚC khi phát.
- Bảng chỉ có ``stt, ma_dong, binh_luan, nhan, ghi_chu``: không nhãn AI, không
  dự đoán, không tên buổi, không tầng.
- Khoá ``ma_dong -> uid lô 2`` ghi ra tệp RIÊNG trong thư mục ``khoa/``, không
  phát cho người gán.
- CSV UTF-8 có BOM, xuống dòng CRLF — Excel trên Windows mở đúng tiếng Việt.
- Băm SHA-256 của hai bảng, khoá và hướng dẫn được ghi vào repo TRƯỚC khi
  phát, để sau này ai cũng kiểm được bảng không bị sửa sau khi thấy kết quả.
- Tất định: cùng seed + cùng ``to_label.txt`` ⇒ cùng từng byte (``--seed``).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import random
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))

from livelift.nlp.labels import INTENT_LABELS, LABEL_DISPLAY, LABEL_GUIDELINE  # noqa: E402

GOLD_DIR = REPO_ROOT / "data" / "labeling" / "lot2-da-nguon-10-09"
HASH_DIR = REPO_ROOT / "docs" / "benchmarks" / "intent-eval" / "gan-mu"

#: Tệp giữ seed bí mật, nằm trong ``khoa/`` cạnh khoá — không phát, không commit.
SEED_NAME = "seed-gan-mu.json"


def secret_seed() -> int:
    """Seed mặc định: rút từ ``secrets``, KHÔNG suy ra được từ mã nguồn công khai."""
    return secrets.randbits(63)


COLUMNS = ("stt", "ma_dong", "binh_luan", "nhan", "ghi_chu")
KEY_COLUMNS = ("ma_dong", "uid_lo2")

TABLE_NAMES = ("bang-nguoi-gan-1.csv", "bang-nguoi-gan-2.csv")
KEY_NAME = "khoa-gan-mu.csv"
GUIDE_NAME = "huong-dan-gan-nhan.md"


def load_rows(directory: Path = GOLD_DIR) -> list[tuple[str, str]]:
    """``[(uid lô 2, văn bản đã lọc PII)]`` theo thứ tự uid — KHÔNG đọc nhãn."""
    rows = []
    for line in (directory / "to_label.txt").read_text(encoding="utf-8").splitlines():
        if "\t" in line:
            uid, text = line.split("\t", 1)
            rows.append((uid.strip(), text))
    uids = [u for u, _ in rows]
    if len(set(uids)) != len(uids):
        raise ValueError("to_label.txt có uid trùng")
    return sorted(rows)


def assign_blind_ids(uids: list[str], seed: int) -> dict[str, str]:
    """``uid lô 2 -> mã mù``; mã không suy ra được uid, tầng hay buổi — CHỈ khi
    ``seed`` được giữ bí mật (mã rút theo thứ tự uid, nên seed lộ là lộ tầng)."""
    rng = random.Random(seed)
    out: dict[str, str] = {}
    used: set[str] = set()
    for uid in uids:
        while True:
            code = f"GM{rng.randrange(16**6):06x}"
            if code not in used:
                used.add(code)
                out[uid] = code
                break
    return out


#: Ký tự đầu làm Excel hiểu ô là CÔNG THỨC (``=))`` là biểu tượng cười rất phổ
#: biến trong chat Việt). Thêm một dấu cách ở đầu để Excel giữ nguyên là chữ.
FORMULA_TRIGGERS = ("=", "+", "-", "@")


def excel_safe(text: str) -> str:
    return " " + text if text.startswith(FORMULA_TRIGGERS) else text


def _csv_bytes(header: tuple[str, ...], rows: list[tuple]) -> bytes:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\r\n", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(header)
    writer.writerows(rows)
    return b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")


def build_tables(rows: list[tuple[str, str]], seed: int) -> dict[str, bytes]:
    """Nội dung (bytes) của hai bảng + khoá. Hàm thuần — test được không cần đĩa."""
    blind = assign_blind_ids([u for u, _ in rows], seed)
    out: dict[str, bytes] = {}
    for i, name in enumerate(TABLE_NAMES, start=1):
        order = list(rows)
        random.Random(seed + i).shuffle(order)
        out[name] = _csv_bytes(
            COLUMNS,
            [
                (stt, blind[uid], excel_safe(text), "", "")
                for stt, (uid, text) in enumerate(order, start=1)
            ],
        )
    key_rows = sorted((blind[uid], uid) for uid, _ in rows)
    out[KEY_NAME] = _csv_bytes(KEY_COLUMNS, key_rows)
    return out


def guide_text(n_rows: int) -> str:
    """Hướng dẫn gán 11 lớp — định nghĩa lấy NGUYÊN từ ``livelift.nlp.labels``.

    Không in seed: hướng dẫn được phát cho người gán và có bản sao trong repo.
    """
    lines = [
        "# Hướng dẫn gán nhãn ý định — bảng gán mù 25/09/2026",
        "",
        f"Bảng có **{n_rows} bình luận** livestream bán hàng thật, đã lọc thông tin cá nhân",
        "(`[TÊN]`, `[SĐT]`, `[ĐỊA CHỈ]`, `[MXH]`, `[MÃ ĐƠN]`, `[STK]`, `[EMAIL]` là chỗ đã che).",
        "",
        "## Quy tắc bắt buộc",
        "",
        "1. **Gán độc lập.** Không trao đổi với người gán còn lại cho tới khi cả hai đã nộp.",
        "2. **Không dùng AI** (ChatGPT, Claude, Gemini…) và không tra nhãn cũ. Mục đích của",
        "   bảng này là đo xem nhãn do AI gán trước đây có khớp với người hay không.",
        "3. Mỗi dòng **đúng một nhãn**. Không chắc vẫn phải chọn một nhãn, rồi ghi lý do vào",
        "   cột `ghi_chu`.",
        "4. Điền cột `nhan` bằng **mã nhãn** (ví dụ `hoi_gia`) hoặc **số thứ tự 1–11** trong",
        "   bảng dưới. Không sửa cột `ma_dong` và `binh_luan`, không xoá hay sắp xếp lại dòng.",
        "5. Lưu lại dạng **CSV UTF-8** (Excel: *File → Save As → CSV UTF-8 (Comma delimited)*).",
        "   Nếu Excel dồn mọi thứ vào một cột: *Data → From Text/CSV*, chọn mã hoá UTF-8,",
        "   dấu phân cách là dấu phẩy.",
        "6. **Dữ liệu người dùng:** không đăng lên mạng, không gửi qua kênh công khai; xoá bản",
        "   trên máy cá nhân sau khi nộp.",
        "7. Bình luận bắt đầu bằng `=`, `+`, `-`, `@` có thêm một dấu cách ở đầu để Excel không",
        "   hiểu nhầm là công thức. Bình luận chỉ gồm chữ số có thể bị Excel hiển thị khác (mất",
        "   số 0 ở đầu, dạng `7,8E+07`); cần xem nguyên văn thì mở tệp bằng Notepad.",
        "",
        "## 11 nhãn",
        "",
        "| Số | Mã nhãn | Tên | Định nghĩa |",
        "|---:|---|---|---|",
    ]
    for i, lb in enumerate(INTENT_LABELS, start=1):
        definition = LABEL_GUIDELINE[lb].replace("|", "/")
        lines.append(f"| {i} | `{lb}` | {LABEL_DISPLAY[lb]} | {definition} |")
    lines += [
        "",
        "## Quy ước cho ca khó",
        "",
        "Quy tắc 1–5 tóm tắt từ mục *Quy ước gán nhãn* của",
        "`docs/benchmarks/intent-classifier.md` (cũng là phần quy ước trong prompt của",
        "`livelift.nlp.label_llm`); quy tắc 6 là quy tắc định trước của lô 2 — để người và AI",
        "được so trên cùng một luật.",
        "",
        '1. **Câu đa ý định** ("size M giá nhiêu"): chọn ý định hành động gần với chốt đơn nhất.',
        "2. **Ai đang nói quyết định nhãn.** Shop dán bảng giá → `bao_gia_shop`; shop hô",
        '   "cả nhà chốt đơn nha" → `khac`. Chỉ ý định của **khách** mới tính là ý định mua.',
        "3. **Chào hỏi, khen không bao giờ là ý định mua.** Không gán `chot_don` cho lời chào.",
        '4. **`che_dat` chỉ nói về GIÁ.** "bán đắt" (bán chạy) hay "cao" (chiều cao) không',
        "   phải chê giá; khen rẻ là `cam_on_khen`.",
        "5. Mất dấu, teencode, viết tắt, emoji: vẫn gán như thường.",
        "6. **Ca mơ hồ giữa một lớp hành động và một lớp khác: chọn lớp hành động** (quy tắc",
        "   định trước của lô này). Lớp hành động: `hoi_gia`, `hoi_size`, `che_dat`,",
        "   `chot_don`, `van_chuyen`.",
        "",
        "## Nộp bài",
        "",
        "Gửi lại tệp CSV đã điền cho trưởng nhóm. Tính độ đồng thuận:",
        "",
        "```",
        ".venv/Scripts/python scripts/tinh_kappa.py --bang1 <bảng người 1> \\",
        "    --bang2 <bảng người 2> --khoa <thư mục gán mù>/khoa/khoa-gan-mu.csv",
        "```",
        "",
        "*Sinh bởi `scripts/gan_mu/tao_bang_gan_mu.py`.*",
        "",
    ]
    return "\n".join(lines)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_all(
    out_dir: Path, hash_dir: Path | None, seed: int, gold_dir: Path = GOLD_DIR
) -> dict[str, str]:
    rows = load_rows(gold_dir)
    files = build_tables(rows, seed)
    guide = guide_text(len(rows)).encode("utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "khoa").mkdir(exist_ok=True)
    digests: dict[str, str] = {}
    for name, data in files.items():
        target = out_dir / "khoa" / name if name == KEY_NAME else out_dir / name
        target.write_bytes(data)
        digests[name] = sha256_bytes(data)
    (out_dir / GUIDE_NAME).write_bytes(guide)
    digests[GUIDE_NAME] = sha256_bytes(guide)
    # Seed chỉ nằm trong khoa/ (không phát): seed lộ = tính ngược được tầng A/B.
    (out_dir / "khoa" / SEED_NAME).write_text(
        json.dumps(
            {
                "seed_ma_mu": seed,
                "seed_thu_tu_bang": {TABLE_NAMES[0]: seed + 1, TABLE_NAMES[1]: seed + 2},
                "ghi_chu": "BÍ MẬT tới khi công bố kappa.json — không phát, không commit.",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    manifest = {
        "seed": f"bí mật — khoa/{SEED_NAME}",
        "n_dong": len(rows),
        "bang": list(TABLE_NAMES),
        "khoa": f"khoa/{KEY_NAME}",
        "huong_dan": GUIDE_NAME,
        "sha256": digests,
        "nguon_van_ban": "data/labeling/lot2-da-nguon-10-09/to_label.txt (đã lọc lại PII 25/09)",
        "ghi_chu": "Bảng KHÔNG chứa nhãn AI, dự đoán, tên buổi hay tầng rút mẫu.",
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if hash_dir is not None:
        hash_dir.mkdir(parents=True, exist_ok=True)
        for name, digest in digests.items():
            (hash_dir / f"{name}.sha256").write_text(f"{digest}  {name}\n", encoding="utf-8")
        # Hướng dẫn không chứa bình luận nào — lưu bản sao trong repo để review được.
        (hash_dir / GUIDE_NAME).write_bytes(guide)
    return digests


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):  # console Windows mặc định cp1252
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ra", required=True, help="thư mục ra (NGOÀI repo: có bình luận)")
    parser.add_argument("--bam", default=str(HASH_DIR), help="thư mục ghi *.sha256 trong repo")
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help=f"chỉ để sinh lại đúng từng byte (lấy trong khoa/{SEED_NAME}); mặc định: seed bí mật",
    )
    parser.add_argument("--goc-lo2", default=str(GOLD_DIR), help="thư mục lô 2 (có to_label.txt)")
    args = parser.parse_args(argv)
    out_dir = Path(args.ra).resolve()
    if REPO_ROOT.resolve() in out_dir.parents or out_dir == REPO_ROOT.resolve():
        parser.error("--ra phải nằm NGOÀI repo: bảng chứa văn bản bình luận người dùng")
    seed = args.seed if args.seed is not None else secret_seed()
    digests = write_all(out_dir, Path(args.bam), seed, Path(args.goc_lo2))
    for name, digest in digests.items():
        print(f"{digest}  {name}")
    print(f"seed (bí mật, KHÔNG phát): {out_dir / 'khoa' / SEED_NAME}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
