"""Dựng cây thư mục gói Google Drive minh chứng (mục 13 MẪU 3) — ngoài kho mã.

    .venv/Scripts/python docs/competition/sang-tao-tre-2026/ke_khai/dung_goi_drive.py
    ... --goc D:/AISC2026/GOI-DRIVE-SANG-TAO-TRE

Tạo (hoặc làm mới) các tệp SINH RA TỪ KHO MÃ; không đụng tới tệp người thêm tay:

    00-DOC-TRUOC.md                     bản đồ thư mục cho Ban Giám khảo
    HUONG-DAN-TAI-LEN.md                cho đội: tải lên, mở quyền, kiểm bằng cửa sổ ẩn danh
    01-Prompt-Log/                      do scripts/xuat_prompt_log.py sinh (chạy riêng)
      ngoai-claude-code/GHI-CHU.md      chỗ để nhật ký Google Antigravity / OpenAI Codex của Tiến
    02-Minh-chung-tien-trinh/
      tien-trinh.md                     mốc commit theo thời gian, sinh từ git log (không có email)
      anh/DOC-TRUOC.md                  quy ước đặt ảnh chụp theo mốc (ảnh thêm sau)
    03-Tai-lieu-ky-thuat/DANH-SACH-TEP.md   danh sách tệp cần chép từ kho mã + lệnh chép
    04-Ma-nguon/LINK-KHO-MA.md          đường dẫn kho, commit, cách tải
    05-Ban-ke-khai/                     bản kê khai .docx/.pdf (chép từ bộ dựng) + DOC-TRUOC.md

Chỉ dùng thư viện chuẩn và ``git``.
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

DAY = Path(__file__).resolve().parent
REPO = DAY.parents[3]
GOC_MAC_DINH = Path("D:/AISC2026/GOI-DRIVE-SANG-TAO-TRE")
KE_KHAI_MAC_DINH = Path("D:/AISC2026/AI2026_Ban_Ke_Khai_LiveLift.docx")
KHO = "https://github.com/bminhnemhoi/AISC2026_LIVEFIT"

TAI_LIEU_KY_THUAT = [
    ("README.md", "Tổng quan sản phẩm, cách chạy, bộ số công bố"),
    ("HARNESS.md", "Quy trình phát triển và cổng chất lượng áp cho cả người lẫn AI"),
    ("PREREGISTRATION.md", "Tiền đăng ký phân tích thí nghiệm"),
    ("docs/competition/FACT-SHEET.md", "Bộ số chuẩn duy nhất của dự án, kèm nguồn"),
    ("docs/incident-log.md", "Sổ sự cố: triệu chứng, nguyên nhân gốc, cách sửa, cổng mới"),
    ("docs/benchmarks/so-hieu-chuan.json", "Số hiệu chuẩn A/A và thu hồi tác động (máy đo)"),
    ("docs/benchmarks/intent-eval/results.json", "Kết quả đánh giá bộ phân loại ý định"),
    ("docs/benchmarks/intent-classifier.md", "Mô tả và giới hạn bộ phân loại ý định"),
    ("docs/benchmarks/live-fire-da-nguon.md", "Báo cáo nạp 19.126 bình luận VOD (quan sát)"),
    ("docs/benchmarks/kuailive-calibration.md", "Hiệu chỉnh mô phỏng theo KuaiLive"),
    ("docs/competition/sang-tao-tre-2026/05-BAN-KE-KHAI.md", "Nguồn Markdown của bản kê khai"),
    (
        "docs/competition/sang-tao-tre-2026/hinh/NGUON.md",
        "Nguồn và lệnh sinh lại các hình của hồ sơ",
    ),
]
NHANH_HO_SO = "hoan-thien/ho-so-2509"
"""Nhánh hoàn thiện hồ sơ 25/09/2026: chờ trưởng nhóm duyệt. Chưa hợp nhất thì liệt kê riêng."""


def _git(*args: str) -> str:
    kq = subprocess.run(  # noqa: S603 — lệnh git cố định
        ["git", "-C", str(REPO), *args],  # noqa: S607
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return kq.stdout


def _ghi(tep: Path, noi_dung: str) -> None:
    tep.parent.mkdir(parents=True, exist_ok=True)
    tep.write_text(noi_dung.rstrip() + "\n", encoding="utf-8")


def _so(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def _nhanh_chua_hop_nhat(nhanh: str, goc: str, fmt: str) -> str:
    """Commit của ``nhanh`` chưa có trong ``goc``; rỗng nếu nhánh không tồn tại."""
    try:
        return _git(
            "log",
            nhanh,
            "--not",
            goc,
            "--reverse",
            "--date=format:%Y-%m-%d %H:%M",
            f"--format={fmt}",
        )
    except subprocess.CalledProcessError:
        return ""


def tien_trinh(
    nhanh: str = "main",
    nhanh_pr: str = "origin/tien/aisc-round2",
    nhanh_ho_so: str = NHANH_HO_SO,
) -> str:
    """Mốc commit theo ngày từ git log — chỉ tên tác giả, không email."""
    sep = "\x1f"
    fmt = sep.join(
        ["%h", "%ad", "%an", "%s", "%(trailers:key=Co-Authored-By,valueonly,separator=; )"]
    )
    dong = _git("log", nhanh, "--reverse", "--date=format:%Y-%m-%d %H:%M", f"--format={fmt}")
    theo_ngay: dict[str, list[list[str]]] = defaultdict(list)
    for d in dong.splitlines():
        if d.strip():
            h, ts, ten, tieu_de, trailer = (d.split(sep) + [""] * 5)[:5]
            theo_ngay[ts[:10]].append([h, ts[11:], ten, tieu_de, trailer.split("<")[0].strip()])
    stat = _git("log", nhanh, "--shortstat", "--format=")
    them = sum(int(x.split()[0]) for x in stat.split(",") if "insertion" in x)
    xoa = sum(int(x.split()[0]) for x in stat.split(",") if "deletion" in x)
    tong = sum(len(v) for v in theo_ngay.values())
    ra = [
        "# Tiến trình phát triển LiveLift — mốc commit theo thời gian",
        "",
        f"Sinh từ `git log {nhanh}` của kho {KHO} bằng",
        "`docs/competition/sang-tao-tre-2026/ke_khai/dung_goi_drive.py` "
        f"lúc {datetime.now().strftime('%Y-%m-%d %H:%M')} (giờ máy). Giờ commit theo múi +07.",
        "",
        f"- {tong} commit trong {len(theo_ngay)} ngày, +{_so(them)} / −{_so(xoa)} dòng.",
        '- Cột "Đồng tác giả AI" là dòng `Co-Authored-By` trong thông điệp commit: mô hình Claude',
        "  (Anthropic) đã viết mã hoặc tài liệu của commit đó qua Claude Code.",
        '- Tác giả git "LiveLift Team" là một danh tính chung của đội trên máy trạm của đội',
        "  trưởng; git không ghi thành viên nào ngồi máy.",
        "- Ảnh chụp giao diện theo từng mốc đặt ở `anh/` (xem `anh/DOC-TRUOC.md`).",
        "",
    ]
    for ngay in sorted(theo_ngay):
        ra += [
            f"## {ngay}",
            "",
            "| Giờ | Commit | Tác giả | Nội dung (thông điệp commit) | Đồng tác giả AI |",
            "|---|---|---|---|---|",
        ]
        for h, gio, ten, tieu_de, ai in theo_ngay[ngay]:
            ra.append(f"| {gio} | `{h}` | {ten} | {tieu_de.replace('|', '/')} | {ai or '—'} |")
        ra.append("")
    hs = _nhanh_chua_hop_nhat(nhanh_ho_so, nhanh, fmt)
    if hs.strip():
        ra += [
            f"## Nhánh `{nhanh_ho_so}` (hoàn thiện hồ sơ, chưa hợp nhất vào `{nhanh}`)",
            "",
            "Nhánh chờ trưởng nhóm duyệt; hợp nhất xong thì các commit này nằm trong phần trên.",
            "",
            "| Thời điểm | Commit | Tác giả | Nội dung | Đồng tác giả AI |",
            "|---|---|---|---|---|",
        ]
        for d in hs.splitlines():
            if d.strip():
                h, ts, ten, tieu_de, trailer = (d.split(sep) + [""] * 5)[:5]
                ai = trailer.split("<")[0].strip() or "—"
                ra.append(f"| {ts} | `{h}` | {ten} | {tieu_de.replace('|', '/')} | {ai} |")
        ra.append("")
    pr = _nhanh_chua_hop_nhat(nhanh_pr, nhanh, fmt)
    if pr.strip():
        ra += [
            f"## Nhánh `{nhanh_pr.split('/', 1)[-1]}` (PR số 1, chưa hợp nhất vào `{nhanh}`)",
            "",
            "Hai commit này không có dòng khai báo AI; tài liệu trong chính các commit ghi do",
            "Google Antigravity và OpenAI Codex tạo (xem bản kê khai, mục I).",
            "",
            "| Thời điểm | Commit | Tác giả | Nội dung |",
            "|---|---|---|---|",
        ]
        for d in pr.splitlines():
            if d.strip():
                h, ts, ten, tieu_de = (d.split(sep) + [""] * 4)[:4]
                ra.append(f"| {ts} | `{h}` | {ten} | {tieu_de.replace('|', '/')} |")
        ra.append("")
    return "\n".join(ra)


def doc_truoc() -> str:
    return f"""# ĐỌC TRƯỚC — Minh chứng quá trình phát triển LiveLift

Đội LiveLift · Cuộc thi Sáng tạo trẻ Quốc gia về Trí tuệ nhân tạo 2026 · Bảng C.
Kho mã nguồn công khai: {KHO}

| Thư mục | Nội dung |
|---|---|
| `01-Prompt-Log/` | Hội thoại Claude Code (đã che dữ liệu cá nhân). Đọc `README.md` trước |
| `02-Minh-chung-tien-trinh/` | Mốc commit theo thời gian, ảnh từ bản nháp tới bản hiện tại |
| `03-Tai-lieu-ky-thuat/` | Tiền đăng ký, sổ sự cố, số hiệu chuẩn, đánh giá NLP |
| `04-Ma-nguon/` | Đường dẫn kho mã và commit nộp |
| `05-Ban-ke-khai/` | Bản kê khai công cụ AI, dữ liệu, API, thư viện (có chữ ký) |

`01-Prompt-Log/` gồm: hội thoại từng phiên, system prompt có trong nhật ký, nhật ký tác tử
con, kịch bản điều phối, bảng băm SHA-256 của bản xuất và của nhật ký gốc.

Ba điều đội tự khai ngay từ đầu: (1) chưa chạy phiên thí nghiệm ngẫu nhiên thật nào;
(2) 19.126 bình luận dùng để đánh giá là dữ liệu quan sát thu bằng yt-dlp, không qua API
chính thức; (3) nhãn dữ liệu và phần lớn mã, tài liệu do AI tạo ra — xem bản kê khai.
"""


def huong_dan() -> str:
    return """# HƯỚNG DẪN TẢI GÓI MINH CHỨNG LÊN GOOGLE DRIVE (cho đội, không cần tải tệp này lên)

## 1. Ngay trước khi tải lên — làm mới nội dung

```
# Git Bash, tại thư mục kho mã
cd D:/AISC2026/livelift
# xuất lại Prompt Log (phiên đang chạy vẫn ghi thêm), rồi quét: phải ra 0
PL=D:/AISC2026/GOI-DRIVE-SANG-TAO-TRE/01-Prompt-Log
.venv/Scripts/python scripts/xuat_prompt_log.py --ra $PL \
    --sao-luu D:/AISC2026/prompt-log-goc/2026-09-15
.venv/Scripts/python scripts/xuat_prompt_log.py --quet $PL
# dựng lại bản kê khai và cây thư mục
.venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/ke_khai/dung_ke_khai.py
.venv/Scripts/python docs/competition/sang-tao-tre-2026/ke_khai/dung_goi_drive.py
```

## 2. Việc của từng người trước khi tải

- **Tiến:** xuất nhật ký Google Antigravity và OpenAI Codex ngày 21/09/2026 từ máy của mình,
  che email, số điện thoại, khoá API, đặt vào `01-Prompt-Log/ngoai-claude-code/antigravity/` và
  `.../codex/`. Không xuất được thì ghi lý do vào `01-Prompt-Log/ngoai-claude-code/GHI-CHU.md`.
  Sau đó chạy lại `--quet` (phải ra 0) và `--lap-manifest` cho thư mục `01-Prompt-Log`.
- **Khánh, Tiến, Minh:** chép các tệp trong `03-Tai-lieu-ky-thuat/DANH-SACH-TEP.md` (lệnh chép có
  sẵn trong tệp đó) từ commit nộp cuối cùng.
- **Cả ba:** in bản kê khai, ghi cột tự khai, ký; scan thành
  `05-Ban-ke-khai/AI2026_Ban_Ke_Khai_LiveLift_da-ky.pdf`.
- Chụp ảnh giao diện theo mốc vào `02-Minh-chung-tien-trinh/anh/` (quy ước trong
  `anh/DOC-TRUOC.md`).

## 3. KHÔNG được đưa lên thư mục mở quyền

- Nhật ký gốc `.jsonl` của Claude Code (chứa dữ liệu cá nhân chưa che).
- `docs/competition/thong-tin-doi.local.json`, giấy xác nhận sinh viên, bản hồ sơ có số điện
  thoại hoặc ngày sinh — nộp Ban Tổ chức qua kênh riêng.
- Dữ liệu bình luận thật trong `data/labeling/`, bản sao lưu `D:/AISC2026/backup-labeling-2509/`
  (còn tên tài khoản người bình luận), khoá gán mù `D:/AISC2026/gan-mu-2509/khoa/`, và thư mục
  nhật ký gốc `D:/AISC2026/prompt-log-goc/`. Xem hồ sơ mục 3.3 về phương án lưu, xoá.

## 4. Tải lên và mở quyền

1. Vào https://drive.google.com bằng tài khoản của đội trưởng → **Mới** → **Tải thư mục lên** →
   chọn `D:/AISC2026/GOI-DRIVE-SANG-TAO-TRE` (bỏ tệp `HUONG-DAN-TAI-LEN.md` này nếu muốn).
2. Nhấp chuột phải vào thư mục vừa tải → **Chia sẻ** → **Chia sẻ**.
3. Mục **Quyền truy cập chung**: đổi "Bị hạn chế" thành **"Bất kỳ ai có đường liên kết"**;
   vai trò **Người xem**. Bấm **Sao chép đường liên kết** → **Xong**.
4. Kiểm: mở một **cửa sổ ẩn danh** (Chrome: Ctrl+Shift+N), KHÔNG đăng nhập, dán đường liên kết.
   Phải thấy đủ 5 thư mục; mở thử một tệp trong mỗi thư mục. Nếu trang đòi đăng nhập hoặc
   "Bạn cần quyền truy cập" là mở quyền chưa đúng — làm lại bước 3 cho chính thư mục gốc.
5. Dán đường liên kết vào mục 13 của hồ sơ (noi-dung.md), dựng lại hồ sơ, và kiểm lại một lần
   nữa bằng cửa sổ ẩn danh sau khi tải xong mọi tệp.

## 5. Bảng kiểm cuối

- [ ] `--quet` trên `01-Prompt-Log` ra 0 (sau khi thêm nhật ký của Tiến)
- [ ] Prompt Log đã xuất lại SAU khi bộ lọc bắt được tên tài khoản dính liền `chữ@tên`
  (kiểm kê 25/09/2026 thấy 2 tên thật dạng này lọt trong 2 tệp `tac-tu-con/`, mà `--quet`
  vẫn ra 0 vì dùng cùng bộ lọc)
- [ ] `01-Prompt-Log/ngoai-claude-code/` có nhật ký Antigravity, Codex hoặc GHI-CHU.md có lý do
- [ ] `05-Ban-ke-khai/` có bản PDF đã ký của cả ba thành viên
- [ ] `03-Tai-lieu-ky-thuat/` đã chép đủ danh sách
- [ ] Mở được bằng cửa sổ ẩn danh, không đăng nhập
- [ ] Đường liên kết đã dán vào hồ sơ mục 13
"""


def ghi_chu_ngoai_claude_code() -> str:
    return """# Nhật ký công cụ AI khác ngoài Claude Code

Thư mục này dành cho nhật ký của các công cụ AI khác mà thành viên đã dùng cho LiveLift.

Theo kiểm toán ngày 2026-09-25, thành viên Tiến (làn giao diện) đã dùng **Google Antigravity**
và **OpenAI Codex** ngày 2026-09-21 trên nhánh `tien/aisc-round2` (PR số 1). Nhật ký nằm trên
máy của Tiến và CHƯA có ở đây.

Trạng thái: CHƯA BỔ SUNG. (Tiến thay dòng này bằng danh sách tệp đã thêm, hoặc lý do không
xuất được.)

GitHub Copilot được gọi trên PR số 1 nhưng không chạy (GitHub báo tài khoản bị khoá vì thanh
toán), nên không có nhật ký.
"""


def danh_sach_tep() -> str:
    ra = [
        "# Tài liệu kỹ thuật cần chép vào thư mục này",
        "",
        f"Chép từ kho mã {KHO} tại commit nộp cuối cùng (không chép bản đang sửa dở).",
        "",
        "| Tệp trong kho | Nội dung | Có trong kho lúc dựng? |",
        "|---|---|---|",
    ]
    for tep, mo_ta in TAI_LIEU_KY_THUAT:
        co = "có" if (REPO / tep).exists() else "**CHƯA CÓ**"
        ra.append(f"| `{tep}` | {mo_ta} | {co} |")
    ra += [
        "",
        "Lệnh chép (PowerShell, chạy tại thư mục kho mã):",
        "",
        "```powershell",
        "$dich = 'D:/AISC2026/GOI-DRIVE-SANG-TAO-TRE/03-Tai-lieu-ky-thuat'",
    ]
    for tep, _ in TAI_LIEU_KY_THUAT:
        ra.append(f"Copy-Item '{tep}' $dich")
    ra += ["```", ""]
    return "\n".join(ra)


def link_kho() -> str:
    head = _git("rev-parse", "--short", "HEAD").strip()
    main = _git("rev-parse", "--short", "main").strip()
    n = _git("rev-list", "--count", "main").strip()
    return f"""# Mã nguồn

- Kho mã công khai: {KHO}
- Nhánh chính `main` lúc dựng gói: commit `{main}` ({n} commit). Commit nộp chính thức sẽ được
  gắn thẻ (tag) và ghi lại ở đây ngay trước khi nộp.
- Lịch sử commit thật, không viết lại; mọi commit trên `main` có dòng đồng tác giả AI.
- Nhánh `tien/aisc-round2` (PR số 1) và nhánh hoàn thiện hồ sơ `hoan-thien/ho-so-2509` chưa
  hợp nhất tại lúc dựng gói (xem `02-Minh-chung-tien-trinh/tien-trinh.md`).
- Tải mã: `git clone {KHO}.git` hoặc nút **Code → Download ZIP** trên GitHub.

(Dựng từ cây làm việc ở commit `{head}`.)
"""


def ban_ke_khai_doc_truoc() -> str:
    return """# Bản kê khai

- `AI2026_Ban_Ke_Khai_LiveLift.pdf` / `.docx`: bản dựng từ `05-BAN-KE-KHAI.md` trong kho mã.
- `AI2026_Ban_Ke_Khai_LiveLift_da-ky.pdf`: bản in có chữ ký tay của ba thành viên (đội thêm sau
  khi ký). Bản có chữ ký là bản chính thức.
"""


def anh_doc_truoc() -> str:
    return """# Ảnh minh chứng tiến trình

Đặt tên: `YYYY-MM-DD_<commit>_<man-hinh>.png`, ví dụ `2026-09-13_14e93ac_desk.png`.
Chụp lại từ chính các commit cũ (git checkout vào thư mục riêng, chạy dữ liệu DEMO), không
dùng ảnh chỉnh sửa. Không để dữ liệu cá nhân (số điện thoại, tên người xem) trong ảnh.
"""


def main(argv: list[str] | None = None) -> int:
    for s in (sys.stdout, sys.stderr):
        with contextlib.suppress(AttributeError, ValueError):
            s.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--goc", type=Path, default=GOC_MAC_DINH)
    ap.add_argument("--ke-khai", type=Path, default=KE_KHAI_MAC_DINH)
    a = ap.parse_args(argv)
    g = a.goc
    _ghi(g / "00-DOC-TRUOC.md", doc_truoc())
    _ghi(g / "HUONG-DAN-TAI-LEN.md", huong_dan())
    ghi_chu = g / "01-Prompt-Log" / "ngoai-claude-code" / "GHI-CHU.md"
    if not ghi_chu.exists():  # không ghi đè phần Tiến đã điền
        _ghi(ghi_chu, ghi_chu_ngoai_claude_code())
    _ghi(g / "02-Minh-chung-tien-trinh" / "tien-trinh.md", tien_trinh())
    _ghi(g / "02-Minh-chung-tien-trinh" / "anh" / "DOC-TRUOC.md", anh_doc_truoc())
    _ghi(g / "03-Tai-lieu-ky-thuat" / "DANH-SACH-TEP.md", danh_sach_tep())
    _ghi(g / "04-Ma-nguon" / "LINK-KHO-MA.md", link_kho())
    _ghi(g / "05-Ban-ke-khai" / "DOC-TRUOC.md", ban_ke_khai_doc_truoc())
    da_chep = []
    for duoi in (".docx", ".pdf"):
        nguon = a.ke_khai.with_suffix(duoi)
        if nguon.exists():
            shutil.copy2(nguon, g / "05-Ban-ke-khai" / nguon.name)
            da_chep.append(nguon.name)
    print(f"Đã dựng cây thư mục tại {g}")
    print(f"  bản kê khai đã chép: {', '.join(da_chep) or 'CHƯA CÓ — chạy dung_ke_khai.py trước'}")
    if not (g / "01-Prompt-Log" / "SO-DEM.json").exists():
        print("  01-Prompt-Log chưa có bản xuất — chạy scripts/xuat_prompt_log.py --ra ...")
    else:
        print("  Nhớ chạy lại --lap-manifest cho 01-Prompt-Log nếu vừa thêm ngoai-claude-code/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
