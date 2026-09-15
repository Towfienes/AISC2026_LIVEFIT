"""Xuất Prompt Log Claude Code thành Markdown đọc được, ĐÃ LÀM SẠCH, để nộp thi.

Mục 13 MẪU 3 (thể lệ Sáng tạo trẻ QG 2026) bắt buộc nộp "lịch sử câu lệnh
(Prompt Log)" gồm System Prompt và toàn bộ conversation history, qua một link
Google Drive **mở quyền**. Nhật ký phiên Claude Code nằm ở
``%USERPROFILE%\\.claude\\projects\\<slug-thu-muc>\\*.jsonl``.

Nhật ký thô KHÔNG được công bố nguyên trạng. Đã kiểm bằng máy (14/09/2026):
nó chứa email + số điện thoại thật của thành viên đội, và 2 file nhật ký
subagent còn chứa **handle YouTube thật của người xem** — dữ liệu cá nhân theo
Luật Bảo vệ dữ liệu cá nhân 91/2025/QH15 và Nghị định 356/2025/NĐ-CP (thay Nghị
định 13/2023). Script này lọc trước khi xuất.

    # xem trước: đếm số lần thay thế, KHÔNG ghi file
    python scripts/xuat_prompt_log.py --kiem-tra

    # xuất thật
    python scripts/xuat_prompt_log.py --ra D:/AISC2026/prompt-log-cong-bo

    # xuất cả nhật ký subagent (dung lượng lớn, ~191 MB thô)
    python scripts/xuat_prompt_log.py --ra <thu-muc> --kem-subagent

Sau khi chạy PHẢI tự đọc lại vài file bất kỳ trước khi tải lên Drive. Bộ lọc
thiên về recall nhưng không phải bộ lọc hoàn hảo — xem ``BAO-CAO-LAM-SACH.md``
trong thư mục kết quả để biết đã thay những gì.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

# --------------------------------------------------------------------------
# Nguồn nhật ký — sửa nếu chạy trên máy khác
# --------------------------------------------------------------------------
PROJECTS_ROOT = Path(os.path.expanduser("~")) / ".claude" / "projects"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from livelift.console import configure  # noqa: E402

SESSION_DIRS = ["d--AISC2026", "D--AISC2026-livelift", "D--AISC2026-livelift-docs-research"]

# --------------------------------------------------------------------------
# Bộ lọc làm sạch — thứ tự có ý nghĩa (cụ thể trước, tổng quát sau)
# --------------------------------------------------------------------------

# 1) Danh sách chặn tường minh: email, SĐT, MSSV của đội. Đọc từ tệp cục bộ
#    docs/competition/thong-tin-doi.local.json (đã gitignore) — đến 15/09/2026
#    chúng bị chép cứng ở đây, tức chính script làm sạch dữ liệu cá nhân lại
#    mang dữ liệu cá nhân vào kho mã. Thiếu tệp cục bộ thì danh sách này rỗng,
#    nhưng email và SĐT vẫn bị bắt bởi luật tổng quát bên dưới, và MSSV bởi
#    luật "mssv".
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "docs" / "competition"))
import thong_tin_doi  # noqa: E402

DENYLIST = dict.fromkeys(thong_tin_doi.gia_tri_nhay_cam(), "[THONG-TIN-DOI]")

SUBS: list[tuple[str, re.Pattern[str], str]] = [
    # --- Bí mật / khoá ----------------------------------------------------
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_\-]{30,}"), "[GOOGLE-API-KEY]"),
    ("fb_token", re.compile(r"\bEAA[A-Za-z0-9]{60,}\b"), "[FB-ACCESS-TOKEN]"),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{30,}\b"), "[API-KEY]"),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{30,}\b"), "[API-KEY]"),
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "[GITHUB-TOKEN]"),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWS-KEY]"),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "[PRIVATE-KEY]"),
    # Gán giá trị cho biến môi trường nhạy cảm: giữ tên biến, bỏ giá trị.
    (
        "env_assign",
        re.compile(
            r"((?:YOUTUBE_API_KEY|FACEBOOK_PAGE_ACCESS_TOKEN|FACEBOOK_APP_SECRET"
            r"|FACEBOOK_APP_ID|SHOPEE_PARTNER_KEY|SHOPEE_ACCESS_TOKEN|POSTGRES_PASSWORD"
            r"|DATABASE_URL|REDIS_URL|ANTHROPIC_API_KEY)\s*[=:]\s*)"
            r"[^\s\"',}\]]+"
        ),
        r"\1[DA-XOA]",
    ),
    # --- Mã số sinh viên dạng TDTU (3 số + 1 chữ hoa + 4 số, ví dụ 5xxH0xxx) --
    ("mssv", re.compile(r"\b\d{3}[A-Z]\d{4}\b"), "[MSSV]"),
    # --- Dữ liệu cá nhân người xem ---------------------------------------
    # Handle mạng xã hội, CÓ hỗ trợ dấu tiếng Việt và dấu gạch ngang. Bộ lọc PII
    # trong sản phẩm cũng đã bắt được dạng này từ 15/09/2026 (patterns.py).
    (
        "social_handle",
        re.compile(r"(?<![\w.@/])@[A-Za-z0-9À-ỹĐđ][A-Za-z0-9À-ỹĐđ._\-]{2,31}"),
        "[MXH]",
    ),
    ("email", re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    # Điện thoại VN: 10 số đầu 0 (03/05/07/08/09) hoặc +84.
    ("phone", re.compile(r"(?<!\d)(?:\+?84|0)(?:3|5|7|8|9)\d{8}(?!\d)"), "[SDT]"),
    # Số tài khoản có ngữ cảnh
    (
        "bank",
        re.compile(r"((?:stk|STK|số\s*tài\s*khoản)\s*:?\s*)\d[\d\s.\-]{5,18}"),
        r"\1[STK]",
    ),
]


def lam_sach(text: str, dem: Counter) -> str:
    """Áp mọi luật lọc; cộng dồn số lần thay vào ``dem``."""
    for tu_khoa, thay in DENYLIST.items():
        if tu_khoa in text:
            dem["denylist:" + thay] += text.count(tu_khoa)
            text = text.replace(tu_khoa, thay)
    for ten, rx, thay in SUBS:
        text, n = rx.subn(thay, text)
        if n:
            dem[ten] += n
    return text


# --------------------------------------------------------------------------
# Đọc JSONL của Claude Code
# --------------------------------------------------------------------------

MAX_TOOL_OUT = 800  # ký tự giữ lại của mỗi kết quả tool (log thô lên tới hàng MB)


def _text_of(content) -> str:
    """Gộp phần văn bản của một message; tool output bị cắt ngắn."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for blk in content:
        if not isinstance(blk, dict):
            continue
        kind = blk.get("type")
        if kind == "text":
            parts.append(blk.get("text", ""))
        elif kind == "thinking":
            continue  # suy luận nội bộ — không thuộc Prompt Log
        elif kind == "tool_use":
            ten = blk.get("name", "?")
            inp = json.dumps(blk.get("input", {}), ensure_ascii=False)
            parts.append(f"\n> **[gọi công cụ `{ten}`]** `{inp[:MAX_TOOL_OUT]}`\n")
        elif kind == "tool_result":
            raw = blk.get("content")
            s = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
            cut = " …(cắt bớt)" if len(s) > MAX_TOOL_OUT else ""
            parts.append(f"\n> **[kết quả công cụ]** `{s[:MAX_TOOL_OUT]}{cut}`\n")
    return "\n".join(p for p in parts if p.strip())


def doc_phien(path: Path) -> list[dict]:
    """Trả về danh sách lượt hội thoại theo thứ tự thời gian."""
    luot: list[dict] = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("type") not in ("user", "assistant"):
                continue
            msg = rec.get("message")
            if not isinstance(msg, dict):
                continue
            noi_dung = _text_of(msg.get("content"))
            if not noi_dung.strip():
                continue
            luot.append(
                {
                    "vai": "NGƯỜI DÙNG" if rec["type"] == "user" else "CLAUDE",
                    "ts": rec.get("timestamp", ""),
                    "text": noi_dung,
                    "meta": rec.get("version", ""),
                }
            )
    return luot


def viet_markdown(path: Path, luot: list[dict], dem: Counter, nguon: Path) -> str:
    ts = [t["ts"] for t in luot if t["ts"]]
    ver = next((t["meta"] for t in luot if t["meta"]), "?")
    n_user = sum(1 for t in luot if t["vai"] == "NGƯỜI DÙNG")
    head = [
        f"# Prompt Log — phiên `{nguon.stem}`",
        "",
        "| | |",
        "|---|---|",
        f"| Công cụ | Claude Code (Anthropic), phiên bản `{ver}` |",
        f"| File nguồn | `{nguon.name}` |",
        f"| Khoảng thời gian | {ts[0][:19] if ts else '?'} → {ts[-1][:19] if ts else '?'} (UTC) |",
        f"| Số lượt | {len(luot)} ({n_user} câu lệnh của đội) |",
        f"| Xuất lúc | {datetime.now(UTC).isoformat(timespec='seconds')} |",
        "",
        "> Đã lọc dữ liệu cá nhân và bí mật bằng `scripts/xuat_prompt_log.py`.",
        "> Khối suy luận nội bộ của mô hình được lược bỏ; kết quả công cụ cắt còn",
        f"> {MAX_TOOL_OUT} ký tự để file đọc được. Nội dung câu lệnh giữ NGUYÊN VĂN.",
        "",
        "---",
        "",
    ]
    body: list[str] = []
    for i, t in enumerate(luot, 1):
        body.append(f"### {i}. {t['vai']} — {t['ts'][:19]}")
        body.append("")
        body.append(lam_sach(t["text"], dem))
        body.append("")
    return "\n".join(head + body)


# --------------------------------------------------------------------------
def thu_thap(kem_subagent: bool) -> list[Path]:
    ds: list[Path] = []
    for d in SESSION_DIRS:
        root = PROJECTS_ROOT / d
        if not root.exists():
            continue
        for dp, _dn, fn in os.walk(root):
            la_sub = f"{os.sep}subagents{os.sep}" in dp + os.sep
            if la_sub and not kem_subagent:
                continue
            ds.extend(Path(dp) / f for f in fn if f.endswith(".jsonl"))
    return sorted(ds)


def main(argv: list[str] | None = None) -> int:
    # Sự cố 27/08 (sổ sự cố): console Windows mặc định cp1252, mọi dòng
    # tiếng Việt bên dưới — kể cả `--help` và thông báo lỗi của argparse —
    # ném UnicodeEncodeError và script chết. Gọi TRƯỚC parse_args, đúng quy
    # ước của scripts/chay_local.py.
    configure()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--ra", type=Path, help="thư mục kết quả")
    ap.add_argument("--kem-subagent", action="store_true", help="xuất cả nhật ký subagent")
    ap.add_argument("--kiem-tra", action="store_true", help="chỉ đếm, không ghi file")
    a = ap.parse_args(argv)

    if not a.kiem_tra and not a.ra:
        ap.error("cần --ra <thư mục> (hoặc --kiem-tra để xem trước)")

    files = thu_thap(a.kem_subagent)
    if not files:
        print(f"Không tìm thấy nhật ký trong {PROJECTS_ROOT}", file=sys.stderr)
        return 1

    dem: Counter = Counter()
    muc_luc: list[str] = []
    tong_luot = 0

    if a.ra:
        a.ra.mkdir(parents=True, exist_ok=True)

    for f in files:
        luot = doc_phien(f)
        if not luot:
            continue
        tong_luot += len(luot)
        md = viet_markdown(f, luot, dem, f)
        la_sub = f"{os.sep}subagents{os.sep}" in str(f)
        ten = ("subagent--" if la_sub else "phien--") + f.stem[:16] + ".md"
        if a.ra:
            (a.ra / ten).write_text(md, encoding="utf-8")
        n_user = sum(1 for t in luot if t["vai"] == "NGƯỜI DÙNG")
        muc_luc.append(f"| [`{ten}`]({ten}) | {luot[0]['ts'][:10]} | {len(luot)} | {n_user} |")

    bao_cao = [
        "# Báo cáo làm sạch Prompt Log",
        "",
        f"Chạy lúc {datetime.now(UTC).isoformat(timespec='seconds')} · "
        f"{len(files)} file nhật ký · {tong_luot} lượt hội thoại.",
        "",
        "## Số lần thay thế theo loại",
        "",
        "| Loại dữ liệu | Số lần thay |",
        "|---|---:|",
    ]
    for k, v in sorted(dem.items(), key=lambda kv: -kv[1]):
        bao_cao.append(f"| `{k}` | {v} |")
    bao_cao += [
        "",
        "## Giới hạn — phải đọc trước khi công bố",
        "",
        "- Bộ lọc là regex, KHÔNG phải NER. Tên người viết thường không có tiền tố",
        '  ("chào chị hương") có thể lọt. Nếu Prompt Log có trích bình luận thật,',
        "  đọc lại tay các file `subagent--*` trước khi tải lên.",
        "- Kết quả công cụ bị cắt còn "
        f"{MAX_TOOL_OUT} ký tự — không phải biện pháp bảo mật, chỉ để file đọc được.",
        "- Script không đụng vào nhật ký gốc. Bản gốc KHÔNG được tải lên Drive.",
        "",
        "## Mục lục phiên",
        "",
        "| File | Ngày bắt đầu | Lượt | Câu lệnh của đội |",
        "|---|---|---:|---:|",
        *muc_luc,
        "",
    ]
    noi_dung = "\n".join(bao_cao)

    if a.ra:
        (a.ra / "BAO-CAO-LAM-SACH.md").write_text(noi_dung, encoding="utf-8")
        print(f"Đã xuất {len(muc_luc)} file vào {a.ra}")
    if a.kiem_tra:
        print(noi_dung)
    else:
        print(f"Tổng thay thế: {sum(dem.values())} — chi tiết trong BAO-CAO-LAM-SACH.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
