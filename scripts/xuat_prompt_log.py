"""Xuất Prompt Log Claude Code thành Markdown đọc được, ĐÃ LÀM SẠCH, để nộp thi.

Mục 13 MẪU 3 (thể lệ Sáng tạo trẻ QG 2026) bắt buộc nộp "lịch sử câu lệnh
(Prompt Log)" gồm System Prompt và toàn bộ conversation history, qua một link
Google Drive mở quyền. Nhật ký phiên Claude Code nằm ở
``%USERPROFILE%\\.claude\\projects\\<thư-mục-dự-án>\\*.jsonl``; nhật ký tác tử
con nằm trong ``<phiên>/subagents/**/agent-*.jsonl``.

    # xem trước: chỉ ĐẾM theo từng phiên, KHÔNG ghi tệp
    python scripts/xuat_prompt_log.py --kiem-tra

    # xuất thật (mặc định kèm log tác tử con); thêm bản sao lưu cũ nếu có
    python scripts/xuat_prompt_log.py --ra D:/AISC2026/GOI-DRIVE-SANG-TAO-TRE/01-Prompt-Log \\
        --sao-luu D:/AISC2026/prompt-log-goc/2026-09-15

    # quét lại một thư mục đã xuất: còn dữ liệu cá nhân / bí mật nào không
    python scripts/xuat_prompt_log.py --quet D:/AISC2026/GOI-DRIVE-SANG-TAO-TRE/01-Prompt-Log

PHÂN VAI (sửa 25/09/2026). Claude Code lưu cả kết quả công cụ, thông báo tác vụ
và chỉ dẫn nạp tự động dưới ``type == "user"``. Bản trước gán nhãn "NGƯỜI DÙNG"
cho tất cả, nên "câu lệnh của đội" bị thổi phồng khoảng 20 lần (1.297 so với 66
câu người gõ ở cùng 3 phiên) và đầu ra của máy đứng tên người. Nay mỗi khối được
xếp vào đúng một vai:

- NGƯỜI — thành viên đội gõ: bản ghi có ``origin.kind == "human"``. Chỉ vai này
  được đếm là câu lệnh người gõ. Lệnh gạch chéo (``/model``…) và lần bấm dừng
  đếm riêng.
- CLAUDE (AI): khối văn bản trả lời và lời gọi công cụ.
- CÔNG CỤ: khối ``tool_result``.
- HỆ THỐNG: thông báo tác vụ, chỉ dẫn nạp tự động (``isMeta``), kết quả lệnh cục
  bộ, tóm tắt nén ngữ cảnh, lỗi API.
- TÁC TỬ ĐIỀU PHỐI (AI): lời giao việc trong nhật ký tác tử con. Tác tử con do
  Claude (hoặc kịch bản điều phối Claude viết) sinh ra, không phải người.

CẮT BỚT. Đầu vào công cụ (mã và văn bản AI viết qua Write/Edit/Bash…) và lời
giao việc cho tác tử con được giữ NGUYÊN VẸN. Chỉ kết quả công cụ và thông báo
hệ thống bị cắt, và MỌI chỗ cắt đều ghi "(cắt bớt N ký tự)". Khối suy luận nội
bộ của mô hình và ảnh không được xuất — số lượng ghi trong đầu mỗi tệp.

LÀM SẠCH. Nhật ký thô chứa email + số điện thoại thật của thành viên và handle
của người xem (kiểm 14/09/2026) — dữ liệu cá nhân theo Luật Bảo vệ dữ liệu cá
nhân 91/2025/QH15 và Nghị định 356/2025/NĐ-CP. Mỗi đoạn văn bản đi qua: (1)
danh sách chặn của đội đọc từ tệp cục bộ, (2) bộ lọc khoá/bí mật, (3) CHÍNH bộ
khử PII của sản phẩm ``livelift.ingest.pii`` theo hai mức: ĐẦY ĐỦ 7 loại (SĐT kể cả
có dấu cách, email, handle/liên kết mạng xã hội, số tài khoản, mã đơn, địa chỉ, tên) cho
kết quả công cụ, câu người gõ, thông báo hệ thống — nơi dữ liệu người ngoài đi vào; và
ĐỊNH DANH (SĐT, email, mạng xã hội, số tài khoản) cho văn bản AI viết, vì luật địa chỉ và
tên viết cho bình luận chat che nhầm hàng chục nghìn cụm văn xuôi kỹ thuật. Decorator Python,
scope npm, at-rule CSS và vài email công khai (``noreply@anthropic.com``) được
giữ nguyên để mã trong log không bị phá. Sau khi xuất, ``--quet`` chạy lại toàn
bộ bộ lọc trên từng dòng của bản xuất và phải ra 0.

Sau khi chạy vẫn PHẢI đọc lại vài tệp bất kỳ trước khi tải lên Drive: bộ lọc là
regex, không phải NER.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Nguồn nhật ký — sửa nếu chạy trên máy khác
# --------------------------------------------------------------------------
# Biến môi trường XUAT_PROMPT_LOG_GOC ghi đè (dùng cho test chạy script như dòng lệnh thật).
PROJECTS_ROOT = Path(
    os.environ.get("XUAT_PROMPT_LOG_GOC") or Path(os.path.expanduser("~")) / ".claude" / "projects"
)
# Mọi thư mục dự án có tên bắt đầu bằng tiền tố này (không phân biệt hoa thường):
# d--AISC2026 (nhật ký phiên + tác tử con), D--AISC2026-livelift (kịch bản điều phối)…
TIEN_TO_THU_MUC = "d--aisc2026"

_GOC_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_GOC_REPO / "src"))
from livelift.console import configure  # noqa: E402
from livelift.ingest.pii import filter as _pii  # noqa: E402

GIO_VN = timezone(timedelta(hours=7))
CAT_KET_QUA_MAC_DINH = 2000  # ký tự giữ lại của mỗi kết quả công cụ
CAT_HE_THONG = 1500  # ký tự giữ lại của mỗi thông báo hệ thống
BIEN_TIM_CHO_NGAT = 300  # cắt ở khoảng trắng gần nhất để không xẻ đôi một token

# --------------------------------------------------------------------------
# Bộ lọc làm sạch — thứ tự có ý nghĩa (cụ thể trước, tổng quát sau)
# --------------------------------------------------------------------------

# 1) Danh sách chặn tường minh: email, SĐT, MSSV, ngày sinh, nơi ở của đội. Đọc từ
#    docs/competition/thong-tin-doi.local.json (đã gitignore). Thiếu tệp cục bộ thì
#    danh sách rỗng, nhưng email và SĐT vẫn bị bắt bởi luật tổng quát bên dưới.
sys.path.insert(0, str(_GOC_REPO / "docs" / "competition"))
import thong_tin_doi  # noqa: E402


def _mo_rong_danh_sach_chan(gia_tri: list[str]) -> dict[str, str]:
    """Giá trị đầy đủ + các MẢNH vẫn định danh được: phần tên của email (và phần chữ đứng
    trước dãy số ở cuối), tiền tố 5 ký tự của MSSV. Xuất thật 25/09/2026: lệnh grep của
    Claude đi tìm dữ liệu đội còn nguyên các mảnh này
    (``grep -nE "<tên email>|<tiền tố MSSV>(…)"``)."""
    ra = set()
    for v in gia_tri:
        v = v.strip()
        if not v:
            continue
        ra.add(v)
        if "@" in v:
            ten = v.split("@", 1)[0]
            if len(ten) >= 5:
                ra.add(ten)
            chu = re.match(r"[A-Za-z._]+", ten)
            if chu and len(chu.group(0).strip("._")) >= 6:
                ra.add(chu.group(0).strip("._"))
        if re.fullmatch(r"\d{3}[A-Z]\d{4}", v):
            ra.add(v[:5])
    return dict.fromkeys(sorted(ra, key=len, reverse=True), "[THONG-TIN-DOI]")


def _danh_sach_chan() -> dict[str, str]:
    gia_tri = list(thong_tin_doi.gia_tri_nhay_cam())
    try:
        for tv in thong_tin_doi.doc().get("thanh_vien", []):
            for khoa in ("ngay_sinh", "noi_o"):
                v = (tv.get(khoa) or "").strip()
                if v and thong_tin_doi.CHO_TRONG not in v and len(v) >= 6:
                    gia_tri.append(v)
    except (OSError, ValueError):
        pass
    return _mo_rong_danh_sach_chan(gia_tri)


DENYLIST: dict[str, str] = _danh_sach_chan()

_TEN_BIEN_NHAY_CAM = (
    r"YOUTUBE_API_KEY|FACEBOOK_PAGE_ACCESS_TOKEN|FACEBOOK_APP_SECRET|FACEBOOK_APP_ID"
    r"|SHOPEE_PARTNER_KEY|SHOPEE_PARTNER_ID|SHOPEE_ACCESS_TOKEN|SHOPEE_REFRESH_TOKEN"
    r"|TIKTOK_SHOP_APP_KEY|TIKTOK_SHOP_APP_SECRET|TIKTOK_SHOP_ACCESS_TOKEN"
    r"|INGEST_TOKEN|POSTGRES_PASSWORD|DATABASE_URL|REDIS_URL|ANTHROPIC_API_KEY|OPENAI_API_KEY"
)

SUBS: list[tuple[str, re.Pattern[str], str]] = [
    # --- Bí mật / khoá ----------------------------------------------------
    ("google_api_key", re.compile(r"AIza[0-9A-Za-z_\-]{30,}"), "[GOOGLE-API-KEY]"),
    ("fb_token", re.compile(r"\bEAA[A-Za-z0-9]{60,}\b"), "[FB-ACCESS-TOKEN]"),
    ("anthropic_key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{30,}\b"), "[API-KEY]"),
    ("openai_key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{30,}\b"), "[API-KEY]"),
    ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"), "[GITHUB-TOKEN]"),
    ("github_pat2", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"), "[GITHUB-TOKEN]"),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[AWS-KEY]"),
    ("slack_token", re.compile(r"\bxox[abprs]-[A-Za-z0-9\-]{20,}\b"), "[SLACK-TOKEN]"),
    (
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
        "[JWT]",
    ),
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "[PRIVATE-KEY]"),
    # Mật khẩu trong chuỗi kết nối: postgres://user:MẬT-KHẨU@host
    (
        "url_password",
        re.compile(r"((?:postgres(?:ql)?|redis|mysql|amqp)://[^:\s/@]+:)(?!\[)([^@\s]+)(@)"),
        r"\1[DA-XOA]\3",
    ),
    # Gán giá trị cho biến môi trường nhạy cảm: giữ tên biến, bỏ giá trị.
    (
        "env_assign",
        re.compile(rf"((?:{_TEN_BIEN_NHAY_CAM})\s*[=:]\s*[\"']?)(?![\[$<{{])[^\s\"',}}\]]+"),
        r"\1[DA-XOA]",
    ),
    # Biến kiểu MÔI_TRƯỜNG có chữ SECRET/TOKEN/PASSWORD… gán chuỗi dài ≥ 20 ký tự.
    (
        "secret_assign",
        re.compile(
            r"(\b[A-Z0-9_]*(?:SECRET|TOKEN|PASSWORD|PASSWD|API_KEY|ACCESS_KEY)[A-Z0-9_]*"
            r"\s*[=:]\s*[\"']?)(?![\[$<{])[A-Za-z0-9_\-+/=.]{20,}"
        ),
        r"\1[DA-XOA]",
    ),
    # --- Mã số sinh viên dạng TDTU (3 số + 1 chữ hoa + 4 số) -----------------
    ("mssv", re.compile(r"\b\d{3}[A-Z]\d{4}\b"), "[MSSV]"),
    # --- Lưới an toàn sau bộ lọc sản phẩm ------------------------------------
    ("phone_vn", re.compile(r"(?<!\d)(?:\+?84|0)(?:3|5|7|8|9)\d{8}(?!\d)"), "[SĐT]"),
]

# Chuỗi trông như handle/email nhưng là MÃ hoặc địa chỉ công khai — giữ nguyên để
# log không bị phá (kiểm toán 25/09: bộ lọc cũ biến `@router.post` thành `[MXH]`).
_DECORATOR = (
    "pytest|router|app|api|dataclass|dataclasses|property|staticmethod|classmethod|functools"
    "|lru_cache|cache|cached_property|override|abstractmethod|field_validator|model_validator"
    "|validator|root_validator|contextmanager|asynccontextmanager|wraps|overload|final"
    "|runtime_checkable|computed_field|field_serializer|model_serializer|given|settings"
    "|example|mock|patch|typing|unittest|pytest_asyncio|hypothesis|total_ordering"
    "|singledispatch|atexit|abc|njit|jit|click|typer|asynccontextmanager|lifespan"
)
_NPM_SCOPE = (
    "types|anthropic-ai|next|babel|eslint|testing-library|playwright|vercel|swc|tailwindcss"
    "|radix-ui|typescript-eslint|jridgewell|nodelib|img|emnapi|napi-rs|pkgjs|isaacs|rtsao"
    "|rushstack|humanwhocodes|ungap|alloc|esbuild|floating-ui|tanstack|vitest|sentry|microsoft"
    "|google|octokit|actions|mdx-js|shikijs|modelcontextprotocol|remix-run|emotion|mui"
    "|headlessui|heroicons|reduxjs|opentelemetry|vitejs|rollup|parcel|csstools|polka"
)
_AT_RULE = (
    "media|import|tailwind|apply|layer|keyframes|font-face|supports|container|theme|utility"
    "|plugin|config|source|variant|custom-variant|param|returns?|type|typedef|deprecated"
    "|see|ts-expect-error|ts-ignore|ts-nocheck|jsx|throws|echo|charset|page|property"
)
_BAO_VE = re.compile(
    rf"@(?:{_DECORATOR})\b(?:\.[A-Za-z_]\w*)*"
    rf"|@(?:{_NPM_SCOPE})/[\w.\-]+"
    r"|(?<![\w.@])@[A-Za-z_][A-Za-z0-9_.]*(?=\()"
    rf"|(?<![\w.@])@(?:{_AT_RULE})\b"
    # băm SHA/MD5, UUID, mã lời gọi công cụ: dãy chữ số bên trong không phải SĐT
    r"|\b(?=[0-9a-f]*[a-f])[0-9a-f]{16,128}\b"
    r"|\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
    r"|\b(?:toolu|srvtoolu|msg|req)_[A-Za-z0-9]{10,}\b"
    r"|\b(?:noreply@anthropic\.com|noreply@github\.com|git@github\.com"
    r"|[A-Za-z0-9._+\-]+@users\.noreply\.github\.com"
    r"|[A-Za-z0-9._+\-]+@example\.(?:com|org|net))\b"
)
_GIU_CHO = "\U000f0000"  # vùng dùng riêng: không phải \w, NFKC giữ nguyên


def _bao_ve(text: str) -> tuple[str, list[str]]:
    giu: list[str] = []

    def _thay(m: re.Match[str]) -> str:
        if len(giu) >= 60000:  # hết ký tự đánh dấu: để bộ lọc xử lý (an toàn hơn)
            return m.group(0)
        giu.append(m.group(0))
        return _GIU_CHO + chr(0xF0100 + len(giu) - 1) + _GIU_CHO

    return _BAO_VE.sub(_thay, text), giu


def _tra_lai(text: str, giu: list[str]) -> str:
    if not giu:
        return text
    return re.sub(
        _GIU_CHO + r"(.)" + _GIU_CHO, lambda m: giu[ord(m.group(1)) - 0xF0100], text, flags=re.S
    )


# Mức lọc. ĐẦY ĐỦ = cả 7 loại của bộ lọc sản phẩm (SĐT, email, mạng xã hội, số tài khoản,
# mã đơn, địa chỉ, tên) — cho nơi dữ liệu của người ngoài đi vào log: kết quả công cụ, câu
# người gõ, thông báo hệ thống. ĐỊNH DANH = 4 loại định danh trực tiếp — cho văn bản do AI
# viết (trả lời, đầu vào công cụ, lời giao việc, kịch bản, system prompt): bộ lọc địa chỉ và
# tên của sản phẩm viết cho bình luận chat, chạy trên văn xuôi kỹ thuật thì che nhầm hàng
# chục nghìn cụm ("liên quan", "đường dẫn", "tinh chỉnh" thành [ĐỊA CHỈ]).
DAY_DU: frozenset[str] | None = None
DINH_DANH: frozenset[str] = frozenset({"email", "phone", "social", "bank"})


def _span_san_pham(text: str, loai: frozenset[str] | None):
    """Chạy các bộ dò của ``livelift.ingest.pii`` rồi chỉ giữ các loại được yêu cầu.

    Lọc loại TRƯỚC khi giải chồng lấn: nếu không, một span "mã đơn" (ưu tiên cao hơn)
    có thể nuốt span SĐT rồi bị bỏ, và SĐT lọt.
    """
    chuan = _pii._normalize_for_scan(text)
    span = [x for x in _pii._find_spans(chuan) if loai is None or x.kind in loai]
    return chuan, _pii._resolve_overlaps(span)


def _scrub_loai(text: str, loai: frozenset[str] | None, dem: Counter) -> str:
    """Như ``scrub`` của sản phẩm nhưng theo mức lọc, lặp tới khi không còn gì để che
    (bộ lọc sản phẩm không lũy đẳng: "PQ5" → "[ĐỊA CHỈ]Q5" lại khớp luật quận)."""
    for _ in range(4):
        chuan, span = _span_san_pham(text, loai)
        if not span:
            return text
        phan: list[str] = []
        con_tro = 0
        for x in span:
            phan.append(chuan[con_tro : x.start])
            phan.append(_pii.REPLACEMENT[x.kind])
            con_tro = x.end
            dem["pii_san_pham:" + x.kind] += 1
        phan.append(chuan[con_tro:])
        text = "".join(phan)
    return text


def lam_sach(text: str, dem: Counter, loai: frozenset[str] | None = DAY_DU) -> str:
    """Áp mọi luật lọc theo mức ``loai``; cộng dồn số lần thay vào ``dem``."""
    if not text:
        return text
    for tu_khoa, thay in DENYLIST.items():
        if tu_khoa and tu_khoa in text:
            dem["danh_sach_chan_doi"] += text.count(tu_khoa)
            text = text.replace(tu_khoa, thay)
    for ten, rx, thay in SUBS[:-1]:  # mọi luật bí mật + MSSV
        text, n = rx.subn(thay, text)
        if n:
            dem[ten] += n
    text, giu = _bao_ve(text)
    text = _scrub_loai(text, loai, dem)
    ten, rx, thay = SUBS[-1]
    text, n = rx.subn(thay, text)
    if n:
        dem[ten] += n
    return _tra_lai(text, giu)


def dem_con_sot(text: str, loai: frozenset[str] | None = DAY_DU) -> Counter:
    """Chạy lại bộ lọc (cùng mức ``loai``) nhưng chỉ đếm — dùng để quét bản đã xuất."""
    kq: Counter = Counter()
    for tu_khoa in DENYLIST:
        if tu_khoa and tu_khoa in text:
            kq["danh_sach_chan_doi"] += text.count(tu_khoa)
    for ten, rx, _thay in SUBS[:-1]:
        n = len(rx.findall(text))
        if n:
            kq[ten] += n
    bv, _giu = _bao_ve(text)
    for x in _span_san_pham(bv, loai)[1]:
        kq["pii_san_pham:" + x.kind] += 1
    ten, rx, _thay = SUBS[-1]
    n = len(rx.findall(bv))
    if n:
        kq[ten] += n
    return kq


# Vai nào dùng mức ĐẦY ĐỦ — đọc lại từ tiêu đề mục trong tệp đã xuất.
_VAI_DAY_DU = ("NGUOI", "LENH", "NGAT", "KQ", "HT", "LOI")
# Tiêu đề mục do _ghi_khoi sinh: "### <giờ theo _gio_vn> — <nhãn vai>…"
_TIEU_DE_VAI = re.compile(r"### ([^—\n]{1,20}) — (.+)$")


def _muc_theo_dong(duong_dan: Path, dong: list[str]):
    """Sinh (dòng, mức lọc) cho từng dòng của một tệp đã xuất.

    Tệp hội thoại (``phien/``, ``tac-tu-con/``): mức theo vai của mục đang đứng (tiêu đề
    ``### <giờ> — <vai>``); dòng tiêu đề và phần đầu tệp dùng mức ĐỊNH DANH. Nhật ký công
    cụ khác do thành viên thêm (``ngoai-claude-code/``): ĐẦY ĐỦ. Còn lại: ĐỊNH DANH.
    """
    phan = set(duong_dan.parts)
    if "ngoai-claude-code" in phan:
        for d in dong:
            yield d, DAY_DU
        return
    hoi_thoai = bool(phan & {"phien", "tac-tu-con"}) and duong_dan.suffix == ".md"
    muc: frozenset[str] | None = DINH_DANH
    nhan_day_du = tuple(VAI[v] for v in _VAI_DAY_DU)
    for d in dong:
        # Chỉ tiêu đề vai do _ghi_khoi sinh mới đổi mức. Một dòng "### …" bất kỳ (tệp
        # Markdown mà công cụ đọc ra, tiêu đề trong câu trả lời của AI) KHÔNG đổi mức —
        # phản biện 25/09: 1.573 dòng như vậy làm 6.634 dòng kết quả công cụ bị quét ở mức
        # ĐỊNH DANH thay vì ĐẦY ĐỦ.
        m = _TIEU_DE_VAI.match(d) if hoi_thoai else None
        if m and m.group(2).startswith(tuple(VAI.values())):
            muc = DAY_DU if m.group(2).startswith(nhan_day_du) else DINH_DANH
            yield d, DINH_DANH
            continue
        yield d, muc if hoi_thoai else DINH_DANH


_XUONG_DONG = chr(10)


def lam_sach_tep(duong_dan: Path, noi_dung: str, dem: Counter) -> str:
    """Lượt cuối trên từng DÒNG của tệp sắp ghi, cùng cách chia mức với ``quet_thu_muc``:
    bắt những gì chỉ lộ ra khi đoạn đã lọc đứng cạnh chữ khác (ô bảng, tiêu đề)."""
    dong = noi_dung.split(_XUONG_DONG)
    ra = [
        lam_sach(d, dem, m) if sum(dem_con_sot(d, m).values()) else d
        for d, m in _muc_theo_dong(duong_dan, dong)
    ]
    return _XUONG_DONG.join(ra)


def quet_thu_muc(thu_muc: Path) -> Counter:
    """Quét từng dòng của mọi tệp văn bản trong thư mục đã xuất."""
    kq: Counter = Counter()
    for f in sorted(Path(thu_muc).rglob("*")):
        if not f.is_file() or f.suffix.lower() not in (".md", ".txt", ".json", ".js", ".html"):
            continue
        with open(f, encoding="utf-8", errors="replace") as fh:
            dong = fh.read().split(_XUONG_DONG)
        for d, m in _muc_theo_dong(f.relative_to(thu_muc), dong):
            kq.update(dem_con_sot(d, m))
    return kq


# --------------------------------------------------------------------------
# Tiện ích định dạng
# --------------------------------------------------------------------------
def _rao(noi_dung: str, ngon_ngu: str = "") -> str:
    """Khối mã Markdown với hàng rào DÀI HƠN mọi chuỗi backtick bên trong."""
    dai = max((len(m) for m in re.findall(r"`+", noi_dung)), default=0)
    rao = "`" * max(3, dai + 1)
    return f"{rao}{ngon_ngu}\n{noi_dung}\n{rao}"


def _cat(s: str, gioi_han: int) -> tuple[str, int]:
    """Cắt ở ``gioi_han`` ký tự (lùi tới khoảng trắng kế tiếp); trả (phần giữ, số ký tự bỏ)."""
    if len(s) <= gioi_han:
        return s, 0
    cho = gioi_han
    m = re.search(r"\s", s[gioi_han : gioi_han + BIEN_TIM_CHO_NGAT])
    if m:
        cho = gioi_han + m.start()
    if cho >= len(s):
        return s, 0
    return s[:cho], len(s) - cho


def _gio_vn(ts: str) -> str:
    if not ts:
        return "?"
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return ts[:19]
    # ISO, không dùng dd/mm/yyyy: "01/09/2026 08:00" khớp luật SĐT của bộ lọc sản phẩm
    return t.astimezone(GIO_VN).strftime("%Y-%m-%d %H:%M:%S")


def _ngay_vn(ts: str) -> str:
    try:
        return (
            datetime.fromisoformat(ts.replace("Z", "+00:00"))
            .astimezone(GIO_VN)
            .strftime("%Y-%m-%d")
        )
    except (ValueError, AttributeError):
        return "khong-ro-ngay"


_NGON_NGU = {
    ".py": "python",
    ".ts": "ts",
    ".tsx": "tsx",
    ".js": "javascript",
    ".mjs": "javascript",
    ".md": "markdown",
    ".json": "json",
    ".jsonl": "json",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".sh": "bash",
    ".ps1": "powershell",
    ".css": "css",
    ".html": "html",
    ".sql": "sql",
}


def _ngon_ngu_cho(ten_cong_cu: str, inp: dict) -> str:
    if ten_cong_cu == "Bash":
        return "bash"
    if ten_cong_cu == "PowerShell":
        return "powershell"
    duong = str(inp.get("file_path") or inp.get("path") or "")
    return _NGON_NGU.get(Path(duong).suffix.lower(), "text")


# --------------------------------------------------------------------------
# Đọc JSONL của Claude Code và phân vai
# --------------------------------------------------------------------------
VAI = {
    "NGUOI": "NGƯỜI — thành viên đội gõ",
    "LENH": "NGƯỜI — lệnh gạch chéo",
    "NGAT": "HỆ THỐNG — ghi nhận người dùng bấm dừng",
    "AI": "CLAUDE (AI) — trả lời",
    "GOI": "CLAUDE (AI) — gọi công cụ",
    "KQ": "CÔNG CỤ — kết quả trả về",
    "HT": "HỆ THỐNG — thông báo tự động",
    "LOI": "HỆ THỐNG — lỗi API (tin nhắn tổng hợp, không phải mô hình trả lời)",
    "DP": "TÁC TỬ ĐIỀU PHỐI (AI) — giao việc cho tác tử con",
}

_TIEN_TO_HE_THONG = (
    "<local-command-",
    "<task-notification",
    "<agent-message",
    "<system-reminder",
    "[Workflow harness",
    "<user-prompt-submit-hook",
    "<bash-stdout",
    "<bash-stderr",
    "Caveat: The messages below",
)


@dataclass
class Khoi:
    vai: str
    ts: str
    noi_dung: str = ""
    cong_cu: str = ""
    dau_vao: object = None
    loi: bool = False
    so_thu_tu_nguoi: int = 0


@dataclass
class NhatKy:
    duong_dan: Path
    tuong_doi: str
    phien: str
    la_tac_tu_con: bool
    khoi: list[Khoi] = field(default_factory=list)
    dem: Counter = field(default_factory=Counter)
    mo_hinh: Counter = field(default_factory=Counter)
    phien_ban: set = field(default_factory=set)
    diem_vao: set = field(default_factory=set)
    ts_dau: str = ""
    ts_cuoi: str = ""
    system_prompt: list = field(default_factory=list)
    tieu_de: str = ""
    nguoi_theo_ngay: Counter = field(default_factory=Counter)
    prompt_id: set = field(default_factory=set)  # promptId của các câu người gõ
    meta: dict = field(default_factory=dict)


def _vai_van_ban(rec: dict, text: str, la_con: bool) -> str:
    t = text.lstrip()
    goc = (rec.get("origin") or {}).get("kind")
    if t.startswith("[Request interrupted by user"):
        return "NGAT"
    if rec.get("isMeta"):
        return "HT"
    if rec.get("isCompactSummary") or t.startswith(
        "This session is being continued from a previous conversation"
    ):
        return "HT"
    if goc == "human":
        return "LENH" if t.startswith(("<command-name>", "<command-message>")) else "NGUOI"
    if goc:
        return "HT"  # task-notification, peer, … : do máy sinh
    if t.startswith(("<command-name>", "<command-message>")):
        return "LENH"
    if t.startswith(_TIEN_TO_HE_THONG):
        return "HT"
    if la_con or rec.get("isSidechain"):
        return "DP"
    return "NGUOI"  # phiên chính, bản Claude Code cũ chưa ghi origin


def _chu_ket_qua(noi_dung) -> tuple[str, int]:
    """Gộp kết quả công cụ thành chữ; ảnh thay bằng ghi chú. Trả (chữ, số ảnh)."""
    if isinstance(noi_dung, str):
        return noi_dung, 0
    if not isinstance(noi_dung, list):
        return json.dumps(noi_dung, ensure_ascii=False), 0
    phan: list[str] = []
    anh = 0
    for b in noi_dung:
        if not isinstance(b, dict):
            phan.append(str(b))
        elif b.get("type") == "text":
            phan.append(b.get("text", ""))
        elif b.get("type") == "image":
            anh += 1
            phan.append("[ảnh — không xuất]")
        elif b.get("type") == "tool_reference":
            phan.append(f"[công cụ được nạp: {b.get('tool_name', '?')}]")
        else:
            phan.append(json.dumps(b, ensure_ascii=False))
    return "\n".join(phan), anh


def doc_nhat_ky(path: Path, tuong_doi: str, phien: str, la_con: bool) -> NhatKy:
    nk = NhatKy(path, tuong_doi, phien, la_con)
    meta = path.with_name(path.stem + ".meta.json")
    if meta.exists():
        try:
            nk.meta = json.loads(meta.read_text("utf-8"))
        except (OSError, ValueError):
            nk.meta = {}
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                nk.dem["dong_hong"] += 1
                continue
            _nap_ban_ghi(nk, rec)
    return nk


def _nap_ban_ghi(nk: NhatKy, rec: dict) -> None:
    loai = rec.get("type")
    ts = rec.get("timestamp") or ""
    if ts:
        nk.ts_dau = min(nk.ts_dau or ts, ts)
        nk.ts_cuoi = max(nk.ts_cuoi or ts, ts)
    if rec.get("version"):
        nk.phien_ban.add(rec["version"])
    if rec.get("entrypoint"):
        nk.diem_vao.add(rec["entrypoint"])
    if loai == "ai-title" and rec.get("aiTitle"):
        nk.tieu_de = rec["aiTitle"]
        return
    if loai == "attachment":
        a = rec.get("attachment") or {}
        if a.get("type") == "prompt_snapshot" and a.get("systemPrompt"):
            nk.system_prompt.append({"ts": ts, **a})
        elif a.get("type") == "instructions":
            nk.system_prompt.append({"ts": ts, "instructions": a.get("files", [])})
        elif a.get("type") == "queued_command" and a.get("commandMode") == "prompt":
            # Lời xếp hàng khi Claude đang chạy. Nhật ký tới 25/09 chỉ có báo cáo trả về của
            # tác tử con (<agent-message …>); lời nào KHÔNG mang dấu của máy thì đếm riêng để
            # README cảnh báo, vì có thể là người gõ mà không vào Prompt Log.
            p = a.get("prompt")
            p = p if isinstance(p, str) else json.dumps(p, ensure_ascii=False)
            if not p.lstrip().startswith(_TIEN_TO_HE_THONG):
                nk.dem["dinh_kem_xep_hang_khong_ro_nguon"] += 1
        nk.dem["dinh_kem_bo_qua"] += 1
        return
    if loai == "system":
        if rec.get("subtype") == "compact_boundary":
            nk.khoi.append(Khoi("HT", ts, "— Claude Code nén ngữ cảnh tại đây —"))
            nk.dem["he_thong"] += 1
        else:
            nk.dem["ban_ghi_he_thong_bo_qua"] += 1
        return
    if loai not in ("user", "assistant"):
        return
    msg = rec.get("message")
    if not isinstance(msg, dict):
        return
    content = msg.get("content")
    if loai == "assistant":
        _nap_tro_ly(nk, rec, msg, ts)
    else:
        _nap_nguoi_dung(nk, rec, content, ts)


def _nap_tro_ly(nk: NhatKy, rec: dict, msg: dict, ts: str) -> None:
    model = msg.get("model") or ""
    tong_hop = model == "<synthetic>" or rec.get("isApiErrorMessage")
    if model and not tong_hop:
        nk.mo_hinh[model] += 1
    content = msg.get("content")
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    if not isinstance(content, list):
        return
    for b in content:
        if not isinstance(b, dict):
            continue
        kind = b.get("type")
        if kind == "text" and b.get("text", "").strip():
            vai = "LOI" if tong_hop else "AI"
            nk.khoi.append(Khoi(vai, ts, b["text"]))
            nk.dem["loi_api" if tong_hop else "ai_tra_loi"] += 1
        elif kind in ("thinking", "redacted_thinking"):
            nk.dem["khoi_suy_luan_khong_xuat"] += 1
            if (b.get("thinking") or "").strip():
                nk.dem["khoi_suy_luan_co_chu"] += 1
        elif kind == "tool_use":
            nk.khoi.append(Khoi("GOI", ts, cong_cu=b.get("name", "?"), dau_vao=b.get("input", {})))
            nk.dem["goi_cong_cu"] += 1
            nk.dem["cong_cu:" + str(b.get("name", "?"))] += 1


def _nap_nguoi_dung(nk: NhatKy, rec: dict, content, ts: str) -> None:
    if isinstance(content, str):
        content = [{"type": "text", "text": content}]
    if not isinstance(content, list):
        return
    anh = 0
    van_ban: list[str] = []
    for b in content:
        if not isinstance(b, dict):
            continue
        kind = b.get("type")
        if kind == "tool_result":
            chu, n_anh = _chu_ket_qua(b.get("content"))
            nk.dem["anh_khong_xuat"] += n_anh
            nk.khoi.append(Khoi("KQ", ts, chu, loi=bool(b.get("is_error"))))
            nk.dem["ket_qua_cong_cu"] += 1
        elif kind == "text":
            van_ban.append(b.get("text", ""))
        elif kind == "image":
            anh += 1
        elif kind == "document":
            van_ban.append("[tài liệu đính kèm — không xuất]")
    if not van_ban and not anh:
        return
    text = "\n".join(van_ban)
    vai = _vai_van_ban(rec, text, nk.la_tac_tu_con)
    if anh:
        nk.dem["anh_khong_xuat"] += anh
        text = f"[ảnh đính kèm: {anh} ảnh — không xuất trong Prompt Log]\n" + text
    k = Khoi(vai, ts, text)
    if vai == "NGUOI":
        nk.dem["cau_lenh_nguoi"] += 1
        k.so_thu_tu_nguoi = nk.dem["cau_lenh_nguoi"]
        nk.nguoi_theo_ngay[_ngay_vn(ts)] += 1
        if rec.get("promptId"):
            nk.prompt_id.add(rec["promptId"])
        if not (rec.get("origin") or {}).get("kind"):
            nk.dem["nguoi_khong_co_origin"] += 1
    elif vai == "LENH":
        nk.dem["lenh_gach_cheo"] += 1
    elif vai == "NGAT":
        nk.dem["bam_dung"] += 1
    elif vai == "DP":
        nk.dem["giao_viec_dieu_phoi"] += 1
    else:
        nk.dem["he_thong"] += 1
    nk.khoi.append(k)


# --------------------------------------------------------------------------
# Viết Markdown
# --------------------------------------------------------------------------
@dataclass
class BoDem:
    thay: Counter = field(default_factory=Counter)
    so_cho_cat: int = 0
    ky_tu_cat: int = 0


def _ghi_khoi(k: Khoi, cat_kq: int, bd: BoDem) -> list[str]:
    # giờ đứng TRƯỚC vai: "chéo · 2026-09-01 08" khớp luật SĐT của bộ lọc sản phẩm (đầu "o")
    tieu = f"### {_gio_vn(k.ts)} — {VAI[k.vai]}"
    if k.so_thu_tu_nguoi:
        tieu += f" · câu lệnh #{k.so_thu_tu_nguoi}"
    ra = [tieu, ""]
    if k.vai == "GOI":
        ra.append(f"**Công cụ `{k.cong_cu}`**")
        ra.append("")
        inp = k.dau_vao
        if isinstance(inp, dict):
            ngan = {}
            for khoa, v in inp.items():
                if isinstance(v, str) and ("\n" in v or len(v) > 160):
                    ra.append(f"- `{khoa}` (nguyên văn, {len(v)} ký tự):")
                    ra.append("")
                    ra.append(_rao(lam_sach(v, bd.thay, DINH_DANH), _ngon_ngu_cho(k.cong_cu, inp)))
                    ra.append("")
                else:
                    ngan[khoa] = v
            if ngan:
                s = json.dumps(ngan, ensure_ascii=False, indent=1)
                ra.append(_rao(lam_sach(s, bd.thay, DINH_DANH), "json"))
        else:
            ra.append(
                _rao(lam_sach(json.dumps(inp, ensure_ascii=False), bd.thay, DINH_DANH), "json")
            )
    elif k.vai in ("KQ", "HT"):
        gioi_han = cat_kq if k.vai == "KQ" else CAT_HE_THONG
        giu, bot = _cat(k.noi_dung, gioi_han)
        if k.loi:
            ra.append("*(công cụ báo lỗi)*")
            ra.append("")
        ra.append(_rao(lam_sach(giu, bd.thay), "text"))
        if bot:
            bd.so_cho_cat += 1
            bd.ky_tu_cat += bot
            ra.append(f"*(cắt bớt {bot} ký tự)*")
    elif k.vai in ("NGUOI", "LENH", "NGAT", "LOI"):
        ra.append(_rao(lam_sach(k.noi_dung, bd.thay), "text"))
    elif k.vai == "DP":  # lời giao việc do AI soạn
        ra.append(_rao(lam_sach(k.noi_dung, bd.thay, DINH_DANH), "text"))
    else:  # AI — văn bản Markdown do Claude viết
        ra.append(lam_sach(k.noi_dung, bd.thay, DINH_DANH))
    ra.append("")
    return ra


def _dong_mo_hinh(c: Counter) -> str:
    return ", ".join(f"`{m}` ({n})" for m, n in c.most_common()) or "—"


def viet_markdown(nk: NhatKy, cat_kq: int, bd: BoDem, sha: str, kich_thuoc: int) -> str:
    d = nk.dem
    ban = sorted(nk.phien_ban, key=lambda v: [int(x) if x.isdigit() else x for x in v.split(".")])
    vai_tro = "Tác tử con" if nk.la_tac_tu_con else "Phiên chính"
    dau = [
        f"# Prompt Log — {vai_tro.lower()} `{nk.duong_dan.stem}`",
        "",
        "| | |",
        "|---|---|",
        f"| Công cụ | Claude Code (Anthropic), phiên bản {', '.join(ban) or '?'}"
        f"; điểm vào {', '.join(sorted(nk.diem_vao)) or '?'} |",
        f"| Mô hình ghi trong nhật ký | {_dong_mo_hinh(nk.mo_hinh)} |",
        f"| Tệp nguồn | `{nk.tuong_doi}` · {kich_thuoc} byte · SHA-256 `{sha}` |",
        f"| Thời gian (giờ Việt Nam) | {_gio_vn(nk.ts_dau)} → {_gio_vn(nk.ts_cuoi)} |",
    ]
    if nk.tieu_de:
        dau.append(
            f"| Tiêu đề phiên (Claude Code tự đặt) | {lam_sach(nk.tieu_de, bd.thay, DINH_DANH)} |"
        )
    if nk.meta:
        mo_ta = lam_sach(str(nk.meta.get("description", "")), bd.thay, DINH_DANH).replace("|", "/")
        dau.append(f"| Loại tác tử / mô tả | `{nk.meta.get('agentType', '?')}` · {mo_ta} |")
    dau += [
        f"| Câu lệnh người gõ | {d['cau_lenh_nguoi']} (lệnh gạch chéo {d['lenh_gach_cheo']}"
        f", bấm dừng {d['bam_dung']}) |",
        f"| Lời giao việc của tác tử điều phối | {d['giao_viec_dieu_phoi']} |",
        f"| Claude trả lời / gọi công cụ | {d['ai_tra_loi']} / {d['goi_cong_cu']} |",
        f"| Kết quả công cụ / thông báo hệ thống | {d['ket_qua_cong_cu']} / {d['he_thong']} |",
        f"| Không xuất | {d['khoi_suy_luan_khong_xuat']} khối suy luận nội bộ"
        f" · {d['anh_khong_xuat']} ảnh |",
        "",
        "> Vai: NGƯỜI = thành viên đội gõ; CLAUDE (AI) = mô hình trả lời hoặc gọi công cụ;",
        "> CÔNG CỤ = kết quả máy trả về; HỆ THỐNG = thông báo tự động; TÁC TỬ ĐIỀU PHỐI (AI) =",
        "> lời giao việc do Claude hoặc kịch bản điều phối Claude viết. Đầu vào công cụ và lời",
        f"> giao việc giữ nguyên vẹn; kết quả công cụ cắt ở {cat_kq} ký tự, thông báo hệ thống ở",
        f'> {CAT_HE_THONG} ký tự, mỗi chỗ cắt ghi "(cắt bớt N ký tự)". Đã che dữ liệu cá nhân và',
        "> bí mật bằng `scripts/xuat_prompt_log.py` (bộ lọc PII của sản phẩm + bộ lọc khoá).",
        "",
        "---",
        "",
    ]
    than: list[str] = []
    for k in nk.khoi:
        than.extend(_ghi_khoi(k, cat_kq, bd))
    return "\n".join(dau + than)


def viet_system_prompt(nk: NhatKy, bd: BoDem) -> str:
    ra = [
        f"# System prompt ghi trong nhật ký phiên `{nk.phien}`",
        "",
        "Claude Code lưu ảnh chụp chỉ dẫn hệ thống (bản ghi `attachment` loại",
        "`prompt_snapshot`) và các tệp chỉ dẫn nạp kèm (loại `instructions`: bộ nhớ dự án,",
        "CLAUDE.md) vào nhật ký từ các bản 2.1.270 trở đi. Dưới đây là NGUYÊN VĂN các ảnh chụp",
        "đó, đã qua bộ lọc dữ liệu cá nhân và bí mật. Định nghĩa công cụ (JSON schema) nằm",
        "ở tệp `.cong-cu.json` cùng tên nếu nhật ký có ghi.",
        "",
    ]
    for i, sp in enumerate(nk.system_prompt, 1):
        ra.append(f"## Ảnh chụp {i} · {_gio_vn(sp.get('ts', ''))}")
        ra.append("")
        if "instructions" in sp:
            for tep in sp["instructions"]:
                duong = lam_sach(str(tep.get("path", "")), bd.thay, DINH_DANH)
                ra.append(f"### Tệp chỉ dẫn nạp kèm: `{duong}`")
                ra.append("")
                ra.append(
                    _rao(lam_sach(str(tep.get("content", "")), bd.thay, DINH_DANH), "markdown")
                )
                ra.append("")
            continue
        if sp.get("cliPrefix"):
            ra.append(f"Tiền tố CLI: {lam_sach(sp['cliPrefix'], bd.thay, DINH_DANH)}")
            ra.append("")
        for j, phan in enumerate(sp.get("systemPrompt") or [], 1):
            ra.append(f"### Phần {j}")
            ra.append("")
            ra.append(_rao(lam_sach(str(phan), bd.thay, DINH_DANH), "text"))
            ra.append("")
        if sp.get("tools"):
            ten = [t.get("name", "?") for t in sp["tools"] if isinstance(t, dict)]
            ra.append(f"Công cụ khai báo ({len(ten)}): " + ", ".join(f"`{t}`" for t in ten))
            ra.append("")
    return "\n".join(ra)


# --------------------------------------------------------------------------
# Thu thập tệp
# --------------------------------------------------------------------------
@dataclass
class Nguon:
    duong_dan: Path
    tuong_doi: str  # đường dẫn tương đối kiểu "d--AISC2026/<phiên>.jsonl"
    tu_sao_luu: bool = False


def _thu_muc_du_an(goc: Path) -> list[Path]:
    if not goc.exists():
        return []
    return sorted(
        p for p in goc.iterdir() if p.is_dir() and p.name.lower().startswith(TIEN_TO_THU_MUC)
    )


def _liet_ke(goc: Path) -> dict[str, Path]:
    ra: dict[str, Path] = {}
    for du_an in _thu_muc_du_an(goc):
        for dp, _dn, fn in os.walk(du_an):
            for f in fn:
                if f.endswith((".jsonl", ".js")):
                    p = Path(dp) / f
                    ra[p.relative_to(goc).as_posix()] = p
    return ra


def thu_thap(sao_luu: list[Path]) -> tuple[list[Nguon], dict]:
    song = _liet_ke(PROJECTS_ROOT)
    nguon = {k: Nguon(v, k) for k, v in song.items()}
    bc = {
        "thu_muc": [str(p) for p in sao_luu],
        "tep_bo_sung": 0,
        "tep_la_tien_to_ban_song": 0,
        "tep_lech": 0,
        "tep_lech_ds": [],
    }
    for sl in sao_luu:
        for rel, p in _liet_ke(sl).items():
            if rel in nguon and not nguon[rel].tu_sao_luu:
                ban_song = nguon[rel].duong_dan
                n = p.stat().st_size
                with open(p, "rb") as a, open(ban_song, "rb") as b:
                    if n <= ban_song.stat().st_size and a.read() == b.read(n):
                        bc["tep_la_tien_to_ban_song"] += 1
                    else:
                        bc["tep_lech"] += 1
                        bc["tep_lech_ds"].append(rel)
            elif rel not in nguon:
                nguon[rel] = Nguon(p, rel, tu_sao_luu=True)
                bc["tep_bo_sung"] += 1
    return sorted(nguon.values(), key=lambda n: n.tuong_doi), bc


_UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _phien_cua(rel: str) -> str:
    m = _UUID.search(rel)
    return m.group(0) if m else rel.split("/")[0]


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# Chạy
# --------------------------------------------------------------------------
_KHOA_DEM = (
    "cau_lenh_nguoi",
    "lenh_gach_cheo",
    "bam_dung",
    "ai_tra_loi",
    "goi_cong_cu",
    "ket_qua_cong_cu",
    "he_thong",
    "loi_api",
    "giao_viec_dieu_phoi",
    "khoi_suy_luan_khong_xuat",
    "anh_khong_xuat",
    "nguoi_khong_co_origin",
)


def _bang_dem(so: dict) -> list[str]:
    ra = [
        "| Phiên | Thời gian (giờ VN) | Câu lệnh người gõ | Lệnh gạch chéo | Bấm dừng "
        "| Claude trả lời | Gọi công cụ | Kết quả công cụ | Thông báo hệ thống | Tác tử con |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for pid, p in so["phien"].items():
        ra.append(
            f"| `{pid[:8]}` | {p['bat_dau_vn'][:10]} → {p['ket_thuc_vn'][:10]} "
            f"| {p['cau_lenh_nguoi']} | {p['lenh_gach_cheo']} | {p['bam_dung']} "
            f"| {p['ai_tra_loi']} | {p['goi_cong_cu']} | {p['ket_qua_cong_cu']} "
            f"| {p['he_thong']} | {p['tac_tu_con']} |"
        )
    t = so["tong"]
    ra.append(
        f"| **Tổng ({t['so_phien_chinh']} phiên)** | | **{t['cau_lenh_nguoi']}** "
        f"| **{t['lenh_gach_cheo']}** | **{t['bam_dung']}** | {t['ai_tra_loi']} "
        f"| {t['goi_cong_cu']} | {t['ket_qua_cong_cu']} | {t['he_thong']} | {t['tac_tu_con']} |"
    )
    return ra


def main(argv: list[str] | None = None) -> int:
    # Sự cố 27/08: console Windows mặc định cp1252 — gọi TRƯỚC parse_args.
    configure()
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--ra", type=Path, help="thư mục kết quả")
    ap.add_argument("--kiem-tra", action="store_true", help="chỉ đếm, không ghi tệp")
    ap.add_argument("--quet", type=Path, help="quét lại một thư mục đã xuất; còn sót thì mã 1")
    ap.add_argument(
        "--lap-manifest",
        type=Path,
        help="tính lại MANIFEST-SHA256.txt cho một thư mục (sau khi thêm log công cụ khác)",
    )
    ap.add_argument(
        "--sao-luu",
        type=Path,
        action="append",
        default=[],
        help="thư mục sao lưu nhật ký cũ (lặp lại được)",
    )
    ap.add_argument("--bo-tac-tu-con", action="store_true", help="không xuất log tác tử con")
    ap.add_argument(
        "--kem-subagent",
        action="store_true",
        help="(giữ để tương thích — nay mặc định đã kèm tác tử con)",
    )
    ap.add_argument(
        "--cat-ket-qua",
        type=int,
        default=CAT_KET_QUA_MAC_DINH,
        help=f"số ký tự giữ lại của mỗi kết quả công cụ (mặc định {CAT_KET_QUA_MAC_DINH})",
    )
    a = ap.parse_args(argv)

    if a.lap_manifest:
        _ghi_manifest(a.lap_manifest)
        print(f"Đã lập lại {a.lap_manifest / 'MANIFEST-SHA256.txt'}")
        return 0
    if a.quet:
        kq = quet_thu_muc(a.quet)
        tong = sum(kq.values())
        print(f"Quét {a.quet}: {tong} chỗ còn khớp bộ lọc")
        for k, v in kq.most_common():
            print(f"  {k}: {v}")
        return 1 if tong else 0
    if not a.kiem_tra and not a.ra:
        ap.error("cần --ra <thư mục> (hoặc --kiem-tra để xem trước, --quet để quét)")

    nguon, bc_sao_luu = thu_thap(a.sao_luu)
    nhat_ky = [n for n in nguon if n.tuong_doi.endswith(".jsonl")]
    kich_ban = [n for n in nguon if n.tuong_doi.endswith(".js")]
    if not nhat_ky:
        print(f"Không tìm thấy nhật ký trong {PROJECTS_ROOT}", file=sys.stderr)
        return 1

    bd = BoDem()
    so: dict = {"phien": {}, "tong": Counter(), "sao_luu": bc_sao_luu}
    mo_hinh_tong: Counter = Counter()
    phien_ban_tong: set = set()
    muc_luc_con: dict[str, list[str]] = {}
    manifest_nguon: list[str] = []
    tong_moi_nhat_ky: Counter = Counter()
    if a.ra:
        a.ra.mkdir(parents=True, exist_ok=True)
        _don_ban_xuat_cu(a.ra)

    # phiên chính trước để tác tử con gắn được vào phiên
    chinh = [n for n in nhat_ky if "/subagents/" not in n.tuong_doi]
    con = [n for n in nhat_ky if "/subagents/" in n.tuong_doi]
    for n in chinh + con:
        la_con = "/subagents/" in n.tuong_doi
        if la_con and a.bo_tac_tu_con and not a.kiem_tra:
            continue
        pid = _phien_cua(n.tuong_doi)
        nk = doc_nhat_ky(n.duong_dan, n.tuong_doi, pid, la_con)
        kt = n.duong_dan.stat().st_size
        sha = _sha256(n.duong_dan) if a.ra else ""
        manifest_nguon.append(
            f"{sha} *{n.tuong_doi}{'  (từ bản sao lưu)' if n.tu_sao_luu else ''}  {kt} byte"
        )
        mo_hinh_tong.update(nk.mo_hinh)
        phien_ban_tong |= nk.phien_ban
        tong_moi_nhat_ky.update(nk.dem)
        p = so["phien"].setdefault(
            pid,
            dict.fromkeys(_KHOA_DEM, 0)
            | {
                "tac_tu_con": 0,
                "bat_dau_vn": "",
                "ket_thuc_vn": "",
                "nguoi_theo_ngay": {},
                "prompt_id_rieng": 0,
                "mo_hinh": {},
                "phien_ban": [],
                "system_prompt": False,
                "tu_sao_luu": False,
            },
        )
        if la_con:
            p["tac_tu_con"] += 1
            p["giao_viec_dieu_phoi"] += nk.dem["giao_viec_dieu_phoi"]
        else:
            for k in _KHOA_DEM:
                p[k] += nk.dem[k]
            p["bat_dau_vn"] = _gio_vn(nk.ts_dau)
            p["ket_thuc_vn"] = _gio_vn(nk.ts_cuoi)
            p["nguoi_theo_ngay"] = dict(sorted(nk.nguoi_theo_ngay.items()))
            p["prompt_id_rieng"] = len(nk.prompt_id)
            p["mo_hinh"] = dict(nk.mo_hinh.most_common())
            p["phien_ban"] = sorted(nk.phien_ban)
            p["system_prompt"] = bool(nk.system_prompt)
            p["tu_sao_luu"] = n.tu_sao_luu
        if not a.ra:
            continue
        md = viet_markdown(nk, a.cat_ket_qua, bd, sha, kt)
        if la_con:
            phan = n.tuong_doi.split("/subagents/", 1)[1].split("/")
            nhom = phan[-2] if len(phan) >= 2 else "truc-tiep"
            ten = Path("tac-tu-con") / pid[:8] / nhom / (n.duong_dan.stem + ".md")
            mo_ta = lam_sach(str(nk.meta.get("description", "")), bd.thay, DINH_DANH).replace(
                "|", "/"
            )
            muc_luc_con.setdefault(pid, []).append(
                f"| [`{nhom}/{n.duong_dan.stem}`]({nhom}/{n.duong_dan.stem}.md) "
                f"| {_gio_vn(nk.ts_dau)} | `{nk.meta.get('agentType', '?')}` | {mo_ta} "
                f"| {_dong_mo_hinh(nk.mo_hinh)} | {nk.dem['goi_cong_cu']} |"
            )
        else:
            ten = Path("phien") / f"{_ngay_vn(nk.ts_dau)}_phien-{pid[:8]}.md"
            if nk.system_prompt:
                sp = Path("system-prompt") / f"{_ngay_vn(nk.ts_dau)}_phien-{pid[:8]}.md"
                (a.ra / sp).parent.mkdir(parents=True, exist_ok=True)
                (a.ra / sp).write_text(
                    lam_sach_tep(sp, viet_system_prompt(nk, bd), bd.thay), encoding="utf-8"
                )
                cong_cu = [t for s in nk.system_prompt for t in (s.get("tools") or [])]
                if cong_cu:
                    js = lam_sach(
                        json.dumps(cong_cu, ensure_ascii=False, indent=1), bd.thay, DINH_DANH
                    )
                    tep_cc = sp.with_suffix(".cong-cu.json")
                    js = lam_sach_tep(tep_cc, js, bd.thay)
                    (a.ra / tep_cc).write_text(js, encoding="utf-8")
        (a.ra / ten).parent.mkdir(parents=True, exist_ok=True)
        (a.ra / ten).write_text(lam_sach_tep(ten, md, bd.thay), encoding="utf-8")

    for n in kich_ban:
        sha = _sha256(n.duong_dan)
        manifest_nguon.append(f"{sha} *{n.tuong_doi}  {n.duong_dan.stat().st_size} byte")
        if a.ra:
            dich = a.ra / "kich-ban-dieu-phoi" / _phien_cua(n.tuong_doi)[:8] / n.duong_dan.name
            dich.parent.mkdir(parents=True, exist_ok=True)
            noi = n.duong_dan.read_text("utf-8", errors="replace")
            noi = lam_sach(noi, bd.thay, DINH_DANH)
            dich.write_text(lam_sach_tep(dich.relative_to(a.ra), noi, bd.thay), encoding="utf-8")

    # tổng hợp
    tong: Counter = Counter()
    for p in so["phien"].values():
        for k in (*_KHOA_DEM, "tac_tu_con"):
            tong[k] += p[k]
    so["tong"] = dict(tong) | {
        "so_phien_chinh": sum(1 for p in so["phien"].values() if p["bat_dau_vn"]),
        "so_nhat_ky_tac_tu_con": tong["tac_tu_con"],
        "so_kich_ban_dieu_phoi": len(kich_ban),
        "mo_hinh": dict(mo_hinh_tong.most_common()),
        "phien_ban_claude_code": sorted(
            phien_ban_tong, key=lambda v: [int(x) if x.isdigit() else x for x in v.split(".")]
        ),
        "so_cho_cat": bd.so_cho_cat,
        "ky_tu_da_cat": bd.ky_tu_cat,
        "so_lan_thay_the": dict(bd.thay.most_common()),
        "cat_ket_qua_cong_cu": a.cat_ket_qua,
        "cat_thong_bao_he_thong": CAT_HE_THONG,
    }
    so["tong_ke_ca_tac_tu_con"] = dict(sorted(tong_moi_nhat_ky.items()))
    so["xuat_luc"] = datetime.now(UTC).isoformat(timespec="seconds")
    so["phien"] = dict(sorted(so["phien"].items(), key=lambda kv: kv[1]["bat_dau_vn"]))

    bang = _bang_dem(so)
    if a.kiem_tra and not a.ra:
        print("Câu lệnh người gõ theo từng phiên (chỉ đếm, không ghi tệp):")
        print("\n".join(bang))
        print(f"Nhật ký tác tử con: {tong['tac_tu_con']} · kịch bản điều phối: {len(kich_ban)}")
        print(f"Mô hình: {_dong_mo_hinh(mo_hinh_tong)}")
        sl = so["sao_luu"]
        if sl["thu_muc"]:
            print(
                f"Sao lưu: bổ sung {sl['tep_bo_sung']} tệp, {sl['tep_la_tien_to_ban_song']} "
                f"tệp là tiền tố bản sống, {sl['tep_lech']} tệp lệch"
            )
        return 0

    assert a.ra is not None
    for pid, dong in muc_luc_con.items():
        tep = Path("tac-tu-con") / pid[:8] / "MUC-LUC.md"
        muc_luc = "\n".join(
            [
                f"# Tác tử con của phiên `{pid}` ({len(dong)} nhật ký)",
                "",
                "Mỗi tác tử con được Claude (hoặc một kịch bản điều phối do Claude viết,",
                "xem `kich-ban-dieu-phoi/`) sinh ra để làm một việc; lời giao việc là của AI,",
                "không phải của người.",
                "",
                "| Nhật ký | Bắt đầu (giờ VN) | Loại | Mô tả | Mô hình | Gọi công cụ |",
                "|---|---|---|---|---|---:|",
                *sorted(dong, key=lambda d: d.split("|")[2]),
                "",
            ]
        )
        (a.ra / tep).write_text(lam_sach_tep(tep, muc_luc, bd.thay), encoding="utf-8")
    _ghi_lf(
        a.ra / "MANIFEST-NGUON-SHA256.txt",
        "# SHA-256 của nhật ký GỐC (không tải lên) — để đối chiếu khi Ban Giám khảo yêu cầu\n"
        + "\n".join(manifest_nguon)
        + "\n",
    )
    (a.ra / "SO-DEM.json").write_text(json.dumps(so, ensure_ascii=False, indent=1), "utf-8")
    (a.ra / "BAO-CAO-LAM-SACH.md").write_text(_bao_cao(so, bd), encoding="utf-8")
    (a.ra / "README.md").write_text(_readme(so), encoding="utf-8")

    kq_quet = quet_thu_muc(a.ra)
    so["quet_lai"] = {"tong": sum(kq_quet.values()), "chi_tiet": dict(kq_quet)}
    (a.ra / "SO-DEM.json").write_text(json.dumps(so, ensure_ascii=False, indent=1), "utf-8")
    # README ghi lần đầu TRƯỚC khi quét (để chính nó cũng được quét); ghi lại với kết quả
    # quét thật — phản biện 25/09: bản xuất thật in "**chưa chạy** chỗ còn khớp".
    (a.ra / "README.md").write_text(_readme(so), encoding="utf-8")
    with open(a.ra / "BAO-CAO-LAM-SACH.md", "a", encoding="utf-8") as f:
        f.write(
            "\n## Quét lại bản xuất\n\n"
            f"`python scripts/xuat_prompt_log.py --quet <thư mục>` trên mọi dòng của mọi tệp: "
            f"**{sum(kq_quet.values())}** chỗ còn khớp bộ lọc"
            + (" — " + ", ".join(f"{k}: {v}" for k, v in kq_quet.most_common()) if kq_quet else "")
            + ".\n"
        )
    _ghi_manifest(a.ra)
    print("\n".join(bang))
    print(
        f"Đã xuất vào {a.ra} · thay thế {sum(bd.thay.values())} chỗ · "
        f"cắt {bd.so_cho_cat} chỗ (đều có dấu) · quét lại: {sum(kq_quet.values())}"
    )
    return 0 if not kq_quet else 1


_TEP_SINH_RA = (
    "README.md",
    "BAO-CAO-LAM-SACH.md",
    "SO-DEM.json",
    "MANIFEST-SHA256.txt",
    "MANIFEST-NGUON-SHA256.txt",
)
_THU_MUC_SINH_RA = ("phien", "tac-tu-con", "system-prompt", "kich-ban-dieu-phoi")


def _don_ban_xuat_cu(thu_muc: Path) -> None:
    """Xoá đúng những gì lần xuất trước sinh ra (để tệp đổi tên không còn sót lại).

    Không đụng tới thứ khác trong thư mục — ví dụ ``ngoai-claude-code/`` chứa nhật ký
    công cụ AI khác do thành viên tự thêm.
    """
    for ten in _TEP_SINH_RA:
        (thu_muc / ten).unlink(missing_ok=True)
    for con in _THU_MUC_SINH_RA:
        goc = thu_muc / con
        if not goc.is_dir():
            continue
        for f in sorted(goc.rglob("*"), reverse=True):
            if f.is_file() and f.suffix in (".md", ".json", ".js"):
                f.unlink()
            elif f.is_dir() and not any(f.iterdir()):
                f.rmdir()
        if not any(goc.iterdir()):
            goc.rmdir()


def _ghi_manifest(thu_muc: Path) -> None:
    dong = []
    for f in sorted(thu_muc.rglob("*")):
        if f.is_file() and f.name != "MANIFEST-SHA256.txt":
            dong.append(f"{_sha256(f)} *{f.relative_to(thu_muc).as_posix()}")
    _ghi_lf(thu_muc / "MANIFEST-SHA256.txt", "\n".join(dong) + "\n")


def _ghi_lf(tep: Path, noi_dung: str) -> None:
    """Ghi với xuống dòng LF trên mọi hệ điều hành. ``write_text`` trên Windows ghi CRLF, và
    ``sha256sum -c`` đọc tên tệp dính ``\\r`` → 608/608 tệp "could not be read", EXIT 1
    (phản biện 25/09/2026 trên bản xuất thật)."""
    with open(tep, "w", encoding="utf-8", newline="\n") as f:
        f.write(noi_dung)


def _bao_cao(so: dict, bd: BoDem) -> str:
    t = so["tong"]
    ra = [
        "# Báo cáo làm sạch Prompt Log",
        "",
        f"Xuất lúc {so['xuat_luc']} (UTC) bằng `scripts/xuat_prompt_log.py`.",
        "",
        "## Số đếm theo phiên",
        "",
        *_bang_dem(so),
        "",
        f"Nhật ký tác tử con: {t['so_nhat_ky_tac_tu_con']} · kịch bản điều phối: "
        f"{t['so_kich_ban_dieu_phoi']} · mô hình: {_dong_mo_hinh(Counter(t['mo_hinh']))}.",
        "",
        "## Số lần thay thế theo loại",
        "",
        "| Loại | Số lần thay |",
        "|---|---:|",
    ]
    for k, v in bd.thay.most_common():
        ra.append(f"| `{k}` | {v} |")
    ra += [
        "",
        "## Cắt bớt",
        "",
        f'{bd.so_cho_cat} chỗ cắt, tổng {bd.ky_tu_cat} ký tự; mỗi chỗ đều ghi "(cắt bớt N ký tự)".',
        "Chỉ cắt kết quả công cụ và thông báo hệ thống. Đầu vào công cụ và lời giao việc",
        "cho tác tử con giữ nguyên vẹn.",
        "",
        "## Giới hạn — phải đọc trước khi công bố",
        "",
        "- Bộ lọc là regex, không phải NER. Tên người viết thường không có tiền tố có thể lọt;",
        "  bộ lọc tên của sản phẩm cũng che nhầm một số cụm viết hoa (ví dụ tên địa danh).",
        "- Văn bản có dữ liệu cá nhân được chuẩn hoá NFKC trước khi che (ví dụ dấu ba chấm",
        "  một ký tự thành ba dấu chấm) — cùng cách làm của bộ lọc sản phẩm.",
        "- Script không sửa nhật ký gốc. Bản gốc KHÔNG tải lên Drive; băm SHA-256 của bản gốc",
        "  nằm ở `MANIFEST-NGUON-SHA256.txt`.",
    ]
    return "\n".join(ra) + "\n"


def _readme(so: dict) -> str:
    """README cho thư mục Prompt Log — sinh từ chính số đếm, không gõ tay."""
    t = so["tong"]
    tc = so.get("tong_ke_ca_tac_tu_con", {})
    sl = so["sao_luu"]
    co_sp = [pid[:8] for pid, p in so["phien"].items() if p.get("system_prompt")]
    khong_sp = [
        pid[:8] for pid, p in so["phien"].items() if p["bat_dau_vn"] and not p.get("system_prompt")
    ]
    quet = so.get("quet_lai", {}).get("tong", "chưa chạy")
    pid_rieng = sum(p.get("prompt_id_rieng", 0) for p in so["phien"].values())
    ra = [
        "# Prompt Log — LiveLift (Claude Code)",
        "",
        f"Xuất lúc {so['xuat_luc']} (UTC) bằng `scripts/xuat_prompt_log.py` trong kho mã",
        "https://github.com/bminhnemhoi/AISC2026_LIVEFIT. Nguồn: nhật ký phiên của Claude Code",
        "(Anthropic, chạy dưới dạng tiện ích VS Code) trên máy trạm của đội, thư mục dự án",
        "`d--AISC2026*` và `D--AISC2026*`.",
        "",
        "## Số đếm theo phiên",
        "",
        *_bang_dem(so),
        "",
        "- **Câu lệnh người gõ** = bản ghi Claude Code đánh dấu `origin.kind = human`. Kiểm chéo",
        f"  bằng trường `promptId` của cùng các bản ghi: {pid_rieng} mã riêng biệt so với"
        f" {t['cau_lenh_nguoi']} câu — "
        + ("khớp." if pid_rieng == t["cau_lenh_nguoi"] else "LỆCH, phải kiểm tay trước khi nộp.")
        + " Lệnh gạch chéo (`/model`) và lần bấm dừng đếm riêng.",
        "- Kết quả công cụ, thông báo tác vụ, chỉ dẫn nạp tự động KHÔNG được tính là câu lệnh",
        "  của người. Bản xuất trước ngày 2026-09-25 tính nhầm chúng nên ra con số 1.297.",
        f"- Nhật ký tác tử con: {t['so_nhat_ky_tac_tu_con']} tệp; lời giao việc cho tác tử con",
        "  do Claude hoặc kịch bản điều phối (do Claude viết) soạn — vai TÁC TỬ ĐIỀU PHỐI (AI).",
        f"- Kịch bản điều phối (JavaScript do Claude viết): {t['so_kich_ban_dieu_phoi']} tệp.",
        f"- Mô hình ghi trong nhật ký: {_dong_mo_hinh(Counter(t['mo_hinh']))}.",
        f"- Phiên bản Claude Code: {', '.join(t['phien_ban_claude_code'])}.",
        "",
        "## Cấu trúc thư mục",
        "",
        "| Tệp / thư mục | Nội dung |",
        "|---|---|",
        "| `phien/<ngày>_phien-<mã>.md` | Hội thoại của từng phiên chính, theo thời gian |",
        "| `tac-tu-con/<mã phiên>/MUC-LUC.md` | Mục lục tác tử con: mô tả, loại, mô hình |",
        "| `tac-tu-con/<mã phiên>/<nhóm>/agent-*.md` | Hội thoại của từng tác tử con |",
        "| `kich-ban-dieu-phoi/<mã phiên>/*.js` | Kịch bản điều phối nhiều tác tử do Claude viết |",
        "| `system-prompt/<ngày>_phien-<mã>.md` | System prompt ghi trong nhật ký (nếu có) |",
        "| `system-prompt/*.cong-cu.json` | Định nghĩa công cụ đi kèm system prompt |",
        "| `SO-DEM.json` | Mọi số đếm ở trên, dạng máy đọc được |",
        "| `BAO-CAO-LAM-SACH.md` | Đã che gì, bao nhiêu lần; kết quả quét lại |",
        "| `MANIFEST-SHA256.txt` | SHA-256 của từng tệp trong thư mục này |",
        "| `MANIFEST-NGUON-SHA256.txt` | SHA-256 của nhật ký GỐC (bản gốc không tải lên) |",
        "| `ngoai-claude-code/` | Nhật ký công cụ AI khác do thành viên tự xuất bổ sung |",
        "",
        "## Cách đọc một tệp hội thoại",
        "",
        "Mỗi mục bắt đầu bằng giờ Việt Nam và vai:",
        "",
        "| Vai | Là ai |",
        "|---|---|",
        "| NGƯỜI — thành viên đội gõ | Câu lệnh thành viên gõ, nguyên văn (đã che PII) |",
        "| NGƯỜI — lệnh gạch chéo | Lệnh cục bộ như `/model` (đổi mô hình) |",
        "| CLAUDE (AI) — trả lời | Văn bản mô hình viết |",
        "| CLAUDE (AI) — gọi công cụ | Mô hình gọi công cụ; đầu vào (mã, lệnh) giữ NGUYÊN VẸN |",
        "| CÔNG CỤ — kết quả trả về | Đầu ra của công cụ; có thể bị cắt, có ghi số ký tự cắt |",
        "| HỆ THỐNG — … | Thông báo tự động của Claude Code, lỗi API, nén ngữ cảnh |",
        "| TÁC TỬ ĐIỀU PHỐI (AI) | Lời giao việc cho tác tử con (do AI soạn, không phải người) |",
        "",
        "## Những gì KHÔNG có trong thư mục này — và vì sao",
        "",
        "- **System prompt:** Claude Code chỉ ghi ảnh chụp system prompt vào nhật ký từ bản"
        f" 2.1.270. Có ở {len(co_sp)} phiên ({', '.join(co_sp) or '—'}), xuất nguyên văn ở"
        f" `system-prompt/`. {len(khong_sp)} phiên chạy bản cũ hơn ({', '.join(khong_sp) or '—'})"
        " không có trong nhật ký; đội không lấy lại được và không dựng bản thay thế.",
        f"- **Khối suy luận nội bộ của mô hình:** {tc.get('khoi_suy_luan_khong_xuat', 0)} khối,"
        f" trong đó chỉ {tc.get('khoi_suy_luan_co_chu', 0)} khối có chữ (còn lại nhật ký chỉ lưu"
        " chữ ký mã hoá). Không xuất vì là suy luận nội bộ, không phải hội thoại.",
        f"- **Bản ghi đính kèm tự động của Claude Code:** {tc.get('dinh_kem_bo_qua', 0)} bản ghi"
        " đính kèm (nhắc số token, thông báo tệp vừa được sửa, thông tin môi trường, danh sách"
        " công cụ và kỹ năng, thông báo tác vụ nền và báo cáo trả về của tác tử con được xếp"
        " hàng khi Claude đang chạy…) không xuất thành mục hội thoại. Ảnh chụp system prompt"
        " trong số đó được xuất riêng ở `system-prompt/`. "
        + (
            "Mọi lời xếp hàng trong nhóm này đều mang dấu của máy (thông báo tác vụ, báo cáo"
            " của tác tử con), nên không có câu lệnh người gõ nào bị bỏ sót ở đây."
            if not tc.get("dinh_kem_xep_hang_khong_ro_nguon", 0)
            else f"CẢNH BÁO: {tc['dinh_kem_xep_hang_khong_ro_nguon']} lời xếp hàng KHÔNG mang"
            " dấu của máy — có thể là người gõ; phải kiểm tay trước khi nộp."
        ),
        f"- **Ảnh:** {tc.get('anh_khong_xuat', 0)} ảnh (ảnh chụp màn hình người dán vào, ảnh công"
        " cụ trả về) không xuất vì có thể chứa dữ liệu cá nhân; vị trí từng ảnh có ghi chú.",
        f"- **Phần cắt bớt:** {t['so_cho_cat']} kết quả công cụ / thông báo hệ thống bị cắt, tổng"
        f' {t["ky_tu_da_cat"]} ký tự; mỗi chỗ ghi "(cắt bớt N ký tự)". Kết quả công cụ giữ'
        f" {t['cat_ket_qua_cong_cu']} ký tự đầu, thông báo hệ thống {t['cat_thong_bao_he_thong']}.",
        "- **Nhật ký gốc (.jsonl):** không tải lên vì chứa dữ liệu cá nhân chưa che. Băm SHA-256",
        "  từng tệp gốc ở `MANIFEST-NGUON-SHA256.txt` để đối chiếu khi Ban Giám khảo yêu cầu.",
        "",
        "## Bản sao lưu",
        "",
        "Claude Code tự xoá nhật ký cũ sau một thời gian. Bản sao lưu cục bộ đã đối chiếu:"
        f" {len(sl['thu_muc'])} thư mục; {sl['tep_la_tien_to_ban_song']} tệp trùng khớp từng byte"
        " với phần đầu của bản đang có (bản đang có dài hơn vì phiên chạy tiếp),"
        f" {sl['tep_lech']} tệp lệch, {sl['tep_bo_sung']} tệp chỉ còn trong bản sao lưu và đã"
        " được đưa vào.",
        "",
        "## Làm sạch dữ liệu cá nhân và bí mật",
        "",
        "Mọi đoạn văn bản đi qua: (1) danh sách chặn thông tin của đội (tệp cục bộ, không vào",
        "git), (2) bộ lọc khoá và bí mật (khoá API, token, mật khẩu trong chuỗi kết nối, biến",
        "môi trường nhạy cảm), (3) bộ khử dữ liệu cá nhân của CHÍNH sản phẩm LiveLift",
        "(`livelift.ingest.pii`), theo hai mức:",
        "",
        "| Mức | Áp cho | Loại che |",
        "|---|---|---|",
        "| Đầy đủ | Kết quả công cụ, câu người gõ, thông báo hệ thống, nhật ký công cụ khác"
        " — nơi dữ liệu của người ngoài đi vào | Cả 7 loại: số điện thoại (kể cả viết cách),"
        " email, handle và liên kết Facebook/TikTok/Zalo, số tài khoản, mã đơn, nơi ở, tên |",
        "| Định danh trực tiếp | Văn bản AI viết: trả lời, đầu vào công cụ (mã), lời giao việc,"
        " kịch bản, system prompt | Số điện thoại, email, handle và liên kết mạng xã hội, số"
        " tài khoản |",
        "",
        "Vì sao hai mức: bộ lọc sản phẩm viết cho bình luận chat; chạy đủ 7 loại trên văn xuôi",
        'kỹ thuật thì các cụm như "liên quan", "đường dẫn", "tinh chỉnh" bị che thành',
        "`[ĐỊA CHỈ]` hàng chục nghìn lần, log không còn đọc được. Bình luận thật lưu trong kho",
        "dữ liệu đã được chính bộ lọc này khử khi nạp. Ở mức đầy đủ bộ lọc vẫn thiên về che",
        "nhiều: một số dãy số trong kết quả kiểm thử có thể thành `[SĐT]`, tên địa danh viết hoa",
        "có thể thành `[TÊN]`. Số lần che theo loại ở `BAO-CAO-LAM-SACH.md`.",
        "",
        f"Quét lại bản xuất (chạy lại bộ lọc, đúng mức, trên từng dòng): **{quet}** chỗ còn khớp.",
        "",
        "## Công cụ AI khác — PHẢI bổ sung trước khi nộp",
        "",
        "Thư mục này chỉ có nhật ký Claude Code trên máy trạm của đội. Theo kiểm toán ngày",
        "2026-09-25, thành viên Tiến (làn giao diện) đã dùng thêm **Google Antigravity**",
        "(rà soát) và **OpenAI Codex** (lập kế hoạch, viết mã) ngày 2026-09-21 trên nhánh",
        "`tien/aisc-round2` (PR số 1). Nhật ký của hai công cụ này nằm trên máy của Tiến. Tiến",
        "tự xuất và đặt vào `ngoai-claude-code/antigravity/` và `ngoai-claude-code/codex/`, che",
        "dữ liệu cá nhân, rồi chạy lại:",
        "",
        "```",
        "python scripts/xuat_prompt_log.py --quet <thư mục này>",
        "python scripts/xuat_prompt_log.py --lap-manifest <thư mục này>",
        "```",
        "",
        "Nếu không xuất được thì ghi rõ lý do vào `ngoai-claude-code/GHI-CHU.md` — không để",
        "trống. GitHub Copilot được gọi trên PR số 1 nhưng không chạy (GitHub báo tài khoản bị",
        "khoá vì thanh toán), nên không có nhật ký. Thành viên nào dùng công cụ AI khác cũng",
        "làm như trên.",
        "",
        "## Tái lập",
        "",
        "```",
        "python scripts/xuat_prompt_log.py --kiem-tra --sao-luu <thư mục sao lưu>  # chỉ đếm",
        "python scripts/xuat_prompt_log.py --ra <thư mục> --sao-luu <thư mục sao lưu>",
        "python scripts/xuat_prompt_log.py --quet <thư mục>                         # phải ra 0",
        "```",
        "",
        "Phiên đang chạy lúc xuất vẫn tiếp tục ghi nhật ký; chạy lại lệnh xuất ngay trước khi",
        "tải lên để có bản đầy đủ nhất.",
    ]
    return "\n".join(ra) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
