"""Gate cho gói H — wizard "Chuẩn bị phiên" (/chay-phien) bản 3.

Đánh giá UI 17/09 (luồng B) đi hết 4 bước bằng trình duyệt thật và thấy năm
lỗi không phải lỗi kiểu dữ liệu — tsc không bắt được cái nào:

H1  Đoạn dẫn 3 dòng "Bốn bước nhỏ…" lặp ở cả 4 bước (~230 px chữ đã đọc).
H2  Sản phẩm mẫu không có link: bước 1 báo "chưa có link" ×3, bước 4 báo cùng
    một thiếu sót 3 lần (callout, dòng checklist, dòng ma trận tín hiệu).
H3  Bước 3 tự mâu thuẫn độ dài khối (~5 phút / ~10 phút / 2 phút) và là tường
    thuật ngữ (khối/nhánh, carryover, CRT, hai mã khác nhau cạnh nhau).
H4  Bước 4 không có chỗ bật bộ thu bình luận; link màn người dẫn là /host
    trơn (mở nhầm phiên); chuỗi dev "parser đã có, vòng ingest chưa nối";
    nút viết HOA TOÀN BỘ; không nói còn bao nhiêu việc.
H5  Phiên không đặt tên → nơi khác chỉ in UUID.

Hai kiểu kiểm tra, như các gate web khác:
- ĐỌC MÃ NGUỒN để giữ bất biến bố cục (cảnh báo nằm MỘT chỗ, chi tiết kỹ thuật
  nằm sau <details>, link mang ?session=…);
- CHẠY THẬT các hàm thuần của trang bằng node (tách nguyên văn khỏi page.tsx,
  node ≥ 22 tự bỏ chú thích kiểu), cấp cho chúng DỮ LIỆU THẬT của máy chủ:
  lịch sinh bởi chính `generate_schedule` và lý do tín hiệu sinh bởi chính
  `signals.assess`. Nhờ vậy câu tóm tắt được chứng minh khớp số của lịch thật,
  không chỉ khớp một mảng tự bịa trong test.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
SRC = WEB / "src"
PAGE = SRC / "app" / "chay-phien" / "page.tsx"
BLOCK_STRIP = SRC / "components" / "BlockStrip.tsx"
INGEST_PANEL = SRC / "components" / "IngestPanel.tsx"
TYPES_TS = SRC / "lib" / "types.ts"
SESSIONS_ROUTE = ROOT / "src" / "livelift" / "api" / "routes" / "sessions.py"


# ---------------------------------------------------------------------------
# tiện ích đọc nguồn
# ---------------------------------------------------------------------------
def raw() -> str:
    return PAGE.read_text(encoding="utf-8")


def code(src: str) -> str:
    """Nguồn đã bỏ chú thích — comment được phép nhắc phản-mẫu bị cấm."""
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    src = re.sub(r"\{/\*.*?\*/\}", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<!:)//.*$", " ", src)


def step_section(src: str, n: int) -> str:
    """Khối JSX của bước n — từ `step === n ?` tới `step === n+1 ?` (hoặc hết)."""
    start = src.index(f"{{step === {n} ? (")
    nxt = src.find(f"{{step === {n + 1} ? (", start)
    return src[start : nxt if nxt != -1 else len(src)]


def opening_tag(src: str, start: int) -> str:
    depth = 0
    for j in range(start, len(src)):
        ch = src[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif ch == ">" and depth == 0:
            return src[start : j + 1]
    return src[start:]


def body_of(src: str, pattern: str, what: str) -> str:
    m = re.search(pattern, src, re.S)
    assert m, f"không tìm thấy {what} trong page.tsx"
    return m.group(1)


def cancel_and_edit_body(src: str) -> str:
    return body_of(
        src, r"const cancelAndEdit = \(minutes\?: string\) =>(.*?)\n    \}\);", "cancelAndEdit"
    )


def clear_session_bits_body(src: str) -> str:
    return body_of(src, r"const clearSessionBits = \(\) => \{(.*?)\n    \};", "clearSessionBits")


def ensure_links_body(src: str) -> str:
    return body_of(
        src, r"const ensureLinks = useCallback\(async \(\) => \{(.*?)\n  \}, \[", "ensureLinks"
    )


def enclosing_details(src: str, marker: str) -> str:
    """Nội dung <details>…</details> bao quanh chuỗi `marker`."""
    at = src.index(marker)
    start = src.rindex("<details", 0, at)
    end = src.index("</details>", at)
    return src[start:end]


# ---------------------------------------------------------------------------
# chạy hàm thuần của trang bằng node
# ---------------------------------------------------------------------------
PURE = [
    "isValidProductUrl",
    "isSampleUrl",
    "sampleUrlFor",
    "TEN_NEN_TANG",
    "tenNenTang",
    "choPhepMoPhong",
    "tenPhienMacDinh",
    "laTenMacDinh",
    "seedHienThi",
    "trungVi",
    "tomTatLich",
    "TIN_HIEU_THUONG",
    "lyDoThuong",
    "daMoDungPhien",
    "canTaoLaiLink",
    "keHoachLinkDo",
    "ganLinkMoi",
    "dongNguonBinhLuan",
]


def extract(src: str, name: str) -> str:
    m = re.search(rf"(?m)^function {name}\(", src)
    if m:
        return src[m.start() : src.index("\n}\n", m.start()) + 2]
    m = re.search(rf"(?m)^const {name}\b", src)
    assert m, f"page.tsx không còn khai báo {name}"
    return src[m.start() : src.index("\n};\n", m.start()) + 3]


def node_eval(tmp_path: Path, expr: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("không có node — bỏ qua phần chạy thử hàm thuần")
    module = "\n".join(extract(raw(), n) for n in PURE)
    script = tmp_path / "wizard_pure.mts"
    script.write_text(
        module + f"\nconsole.log(JSON.stringify({expr}));\n",
        encoding="utf-8",
    )
    out = subprocess.run(
        [node, "--experimental-strip-types", "--no-warnings", str(script)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if out.returncode != 0 and "strip-types" in out.stderr and "bad option" in out.stderr:
        pytest.skip("node quá cũ, chưa bỏ được chú thích kiểu")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def real_blocks(duration_min: int, seed: int) -> list[dict]:
    """Lịch THẬT theo đúng tham số wizard gửi máy chủ (block 5, washout 0, jitter 30)."""
    from livelift.core.assigner.outer import DesignParams, generate_schedule

    params = DesignParams(block_min=5, washout_min=0, jitter_s=30)
    return generate_schedule(duration_min, params, seed).to_rows()


# ===========================================================================
# H1 — đoạn dẫn chỉ ở bước 1
# ===========================================================================
def test_h1_doan_dan_bon_buoc_chi_hien_o_buoc_1():
    src = code(raw())
    start = src.index("<PageHeader")
    header = src[start : src.index("/>", src.index("lead={", start))]
    assert "Bốn bước nhỏ" in header, "đoạn dẫn phải nằm trong lead của PageHeader"
    assert re.search(r"lead=\{\s*hydrated && step === 1 \?", header), (
        "lead chỉ được hiện ở bước 1 — các bước sau người bán đã đọc rồi"
    )
    assert raw().count("Bốn bước nhỏ") == 1, "đoạn dẫn bị lặp lại ở chỗ khác"


# ===========================================================================
# H2 — cảnh báo thiếu link: MỘT chỗ mỗi bước; link mẫu không bịa cửa hàng thật
# ===========================================================================
def test_h2_buoc_1_gop_canh_bao_thieu_link_thanh_mot_callout():
    s1 = step_section(code(raw()), 1)
    loop_start = s1.index("products.map((p) =>")
    loop = s1[loop_start : s1.index("</ul>", loop_start)]
    for bad in ("⚠", "không đo được", "Chưa có link —"):
        assert bad not in loop, (
            f"{bad!r} nằm trong vòng lặp sản phẩm — cảnh báo sẽ lặp N lần; "
            "gộp về callout duy nhất phía trên danh sách"
        )
    assert "○ chưa có link" in loop, "mỗi sản phẩm vẫn cần trạng thái HÌNH + CHỮ, trung tính"
    before = s1[:loop_start]
    callouts = [m.start() for m in re.finditer(r"<Callout", before)]
    assert len(callouts) == 1, "bước 1 phải có đúng một callout thiếu link, trước danh sách"
    body = before[callouts[0] :]
    assert "missingLinkProducts.length" in body
    assert "không đo được lượt bấm" in body
    assert "chép địa chỉ trên thanh trình duyệt" in body, "thiếu gợi ý cách lấy link thật"
    assert s1.count("không đo được lượt bấm") == 1


def test_h2_san_pham_mau_dung_link_mau_example_com_va_ghi_ro():
    src = raw()
    assert "shopee.vn" not in src, "không bịa URL của một cửa hàng có thật"
    fill = extract(code(src), "isSampleUrl")
    assert "example.com" in fill
    body = code(src)
    m = re.search(r"const fillSample = \(\) =>(.*?)\n    \}\);", body, re.S)
    assert m, "không tìm thấy fillSample"
    assert "sampleUrlFor(" in m.group(1), "sản phẩm mẫu phải dùng link mẫu example.com"
    assert "Đây là link mẫu để xem thử" in src, "link mẫu phải được ghi rõ là link mẫu"
    assert "Điền link mẫu để chạy thử" in src
    assert "◐ link mẫu" in src, "sản phẩm đang dùng link mẫu phải có nhãn riêng"


def test_h2_link_mau_va_link_hop_le_chay_that(tmp_path):
    got = node_eval(
        tmp_path,
        "[isSampleUrl(sampleUrlFor('ao-khoac')), sampleUrlFor('ao-khoac'),"
        " isSampleUrl('https://shop.example.com/x'), isSampleUrl('https://shopee.vn/x'),"
        " isSampleUrl('khong phai url'), isValidProductUrl('https://example.com/a'),"
        " isValidProductUrl('shopee.vn/abc'), isValidProductUrl('ftp://a.b/c')]",
    )
    assert got == [True, "https://example.com/ao-khoac", True, False, False, True, False, False]


def test_h2_buoc_4_bao_thieu_link_dung_mot_lan():
    s4 = step_section(code(raw()), 4)
    assert "linkNote" not in code(raw()), "callout link đầu bước 4 là lần báo thứ nhất trong ba"
    assert s4.count("không đo được lượt bấm") == 1, (
        "bước 4 chỉ được nói thiếu link ở MỘT chỗ — dòng Link đo"
    )
    assert "Chưa có link đo cho phiên này" not in s4
    m = re.search(r"const TIN_HIEU_CO_DONG_RIENG = \[([^\]]*)\]", code(raw()))
    assert m, "thiếu danh sách nguồn đã có dòng checklist riêng"
    for name in ('"clicks"', '"comments"', '"schedule"'):
        assert name in m.group(1), f"{name} phải bị loại khỏi mục dữ liệu (đã có dòng riêng)"
    assert "!TIN_HIEU_CO_DONG_RIENG.includes(s.name)" in code(raw())


# ===========================================================================
# H3 — bước 3: một câu thường ngày từ lịch thật + chi tiết kỹ thuật sau <details>
# ===========================================================================
def test_h3_tom_tat_khop_lich_that_30_phut(tmp_path):
    """Phiên 30 phút, khối 5: máy chủ xếp [10, 5, 5, 10] (khối biên gấp đôi).
    Bản cũ in "phần lớn ~10 phút" (trung vị lệch) cạnh câu "~5 phút"."""
    blocks = real_blocks(30, seed=4146685020918767000)
    meas = [b for b in blocks if not b["is_washout"]]
    n_on = sum(b["assignment"] == "ON" for b in meas)
    n_off = sum(b["assignment"] == "OFF" for b in meas)
    got = node_eval(tmp_path, f"tomTatLich({json.dumps(blocks)}, 30)")
    assert got.startswith(f"Buổi live 30 phút được chia thành {len(meas)} khối")
    assert f"({n_on} khối BẬT, {n_off} khối TẮT)" in got
    assert "khối đầu và khối cuối dài khoảng 10 phút" in got
    assert "các khối còn lại khoảng 5 phút" in got
    assert "~" not in got
    assert "phần lớn" not in got


@pytest.mark.parametrize("seed", [1, 7, 42, 2026])
def test_h3_tom_tat_khop_lich_that_90_phut_moi_seed(tmp_path, seed):
    blocks = real_blocks(90, seed=seed)
    meas = [b for b in blocks if not b["is_washout"]]
    got = node_eval(tmp_path, f"tomTatLich({json.dumps(blocks)}, 90)")
    assert f"chia thành {len(meas)} khối" in got
    assert "khối đầu và khối cuối dài khoảng 10 phút" in got, got
    assert "các khối còn lại khoảng 5 phút" in got, got


def test_h3_tom_tat_khoi_deu_va_lich_rong(tmp_path):
    even = [
        {
            "block_index": i,
            "is_washout": False,
            "assignment": a,
            "start_offset_s": i * 300,
            "end_offset_s": (i + 1) * 300,
        }
        for i, a in enumerate(["ON", "OFF", "OFF"])
    ]
    got = node_eval(tmp_path, f"[tomTatLich({json.dumps(even)}, 15), tomTatLich([], 30)]")
    assert got[0] == (
        "Buổi live 15 phút được chia thành 3 khối (1 khối BẬT, 2 khối TẮT), mỗi khối khoảng 5 phút."
    )
    assert got[1] == "Lịch chưa có khối nào."


def test_h3_buoc_3_mot_cau_tom_tat_va_khuyen_nghi_doi_thoi_luong():
    s3 = step_section(code(raw()), 3)
    assert "tomTatLich(schedule.blocks, plannedMin)" in s3, "câu tóm tắt phải lấy từ lịch thật"
    assert "phần lớn ~" not in s3
    assert "blockLenMin" not in code(raw())
    # câu chuẩn "~5 phút" chỉ hiện TRƯỚC khi bốc; bốc xong thì số thật thay chỗ
    cau_chuan = s3.index("CAU_MOT_DONG.batTat")
    assert s3.index("{!schedule ? (") < cau_chuan < s3.index("tomTatLich("), (
        "câu chuẩn '~5 phút' không được đứng cạnh số thật của lịch đã bốc"
    )
    # khuyến nghị hành động: phiên ngắn → một nút đổi thời lượng
    assert "phienNgan" in s3
    assert "Đổi thời lượng" in s3
    assert "cancelAndEdit(String(PHUT_KHUYEN_DUNG))" in s3
    assert re.search(r"const PHUT_KHUYEN_DUNG = 90;", code(raw()))
    assert "(từ 90 phút)" in SESSIONS_ROUTE.read_text(encoding="utf-8"), (
        "mốc 90 phút của wizard phải cùng mốc với lưu ý cân bằng của máy chủ"
    )
    # "Đổi thời lượng" chọn sẵn thời lượng mới + bỏ tên mặc định có giờ cũ
    m = re.search(
        r"const cancelAndEdit = \(minutes\?: string\) =>(.*?)\n    \}\);", code(raw()), re.S
    )
    assert m, "cancelAndEdit phải nhận thời lượng chọn sẵn"
    assert "minutes: minutes ?? f.minutes" in m.group(1)
    assert "laTenMacDinh(f.title)" in m.group(1)


def test_h3_chi_tiet_ky_thuat_nam_sau_details():
    s3 = step_section(raw(), 3)
    details = enclosing_details(s3, "Chi tiết kỹ thuật")
    for must in (
        "Mã bằng chứng:",
        "không ai sửa lịch giữa chừng",
        "Mã bốc thăm (seed):",
        "{schedWarning}",
        "Bốc lại lịch khác",
        "lưu vết",
    ):
        assert must in details, f"{must!r} phải nằm trong <details> Chi tiết kỹ thuật"
    outside = s3.replace(details, "")
    assert "{schedWarning}" not in outside, "lưu ý cân bằng nguyên văn chỉ được ở chi tiết kỹ thuật"
    assert "Bốc lại lịch khác" not in outside
    assert "Mã kiểm chứng lịch" not in raw(), "hai tên cho hai mã khác nhau gây nhầm — bỏ tên cũ"
    for jargon in ("carryover", "CRT", "khối/nhánh", "τ̂"):
        assert jargon not in raw(), f"thuật ngữ {jargon!r} không được nằm trên trang"


def test_h3_boc_lai_la_boc_ngau_nhien_moi_khong_giu_seed_da_go():
    """ "Bốc lại lịch khác" gửi lại seed đã gõ ở tuỳ chọn nâng cao thì máy chủ
    sinh y hệt lịch cũ — nút nói "khác" mà ra giống hệt."""
    src = code(raw())
    m = re.search(r"const drawSchedule = \(boLai = false\) =>(.*?)\n    \}\);", src, re.S)
    assert m, "drawSchedule phải phân biệt lần bốc đầu với bốc lại"
    body = m.group(1)
    assert 'const seedGo = boLai ? "" : seed.trim();' in body
    assert "seed: seedGo ? Number(seedGo) : undefined" in body
    s3 = step_section(src, 3)
    details = enclosing_details(s3, "Chi tiết kỹ thuật")
    assert "onClick={() => drawSchedule(true)}" in details
    # nút bốc lần đầu KHÔNG được truyền sự kiện click làm cờ boLai (truthy)
    assert "onClick={drawSchedule}" not in src
    assert "onClick={() => drawSchedule()}" in s3


def test_h3_seed_that_cua_may_chu_khong_bi_in_sau_khi_lam_tron(tmp_path):
    """Máy chủ bốc seed bằng `secrets.randbits(63)`. Cho JSON do chính Python
    sinh đi qua JSON.parse của node (đúng đường api.ts đọc): seed lớn bị làm
    tròn nên trang KHÔNG được in nó kèm lời hứa sinh lại được lịch."""
    big = 2**62 + 12345
    small = 42
    payload = json.dumps({"big": big, "small": small})
    got = node_eval(
        tmp_path,
        f"(() => {{ const o = JSON.parse({json.dumps(payload)});"
        " return [String(o.big) === "
        f"{json.dumps(str(big))}, seedHienThi(o.big), seedHienThi(o.small),"
        " seedHienThi(null), seedHienThi(0)]; })()",
    )
    assert got == [False, None, "42", None, "0"]
    s3 = step_section(code(raw()), 3)
    details = enclosing_details(s3, "Chi tiết kỹ thuật")
    assert "{schedule.seed}" not in details, "seed thô có thể đã bị làm tròn"
    assert "seedHienThi(schedule.seed)" in details
    assert "không sinh lại được lịch" in details, "seed dài phải nói vì sao không in"


def test_h3_lich_boc_tham_khong_con_chu_giai_vi_tri_hien_tai():
    s3 = code(step_section(raw(), 3))
    m = re.search(r"<BlockStrip(.*?)/>", s3, re.S)
    assert m, "bước 3 phải vẽ lịch bằng BlockStrip"
    assert "positionS={null}" in m.group(1), "bước 3 vẽ lịch không có vị trí"
    assert "Vị trí hiện tại" not in code(raw()), "wizard không tự vẽ chú giải vị trí"


def test_h3_blockstrip_bo_chu_giai_vi_tri_khi_chua_co_vi_tri():
    """Nửa còn lại của H3 nằm ở BlockStrip.tsx (tệp dùng chung, KHÔNG thuộc
    gói H): chú giải "Vị trí hiện tại" chỉ được vẽ khi có vị trí. Gate này giữ
    để wizard không in lại chú giải cho một vạch không tồn tại."""
    strip = BLOCK_STRIP.read_text(encoding="utf-8")
    # lần xuất hiện CUỐI là chú giải (lần đầu là aria-label khi đang có vị trí)
    at = strip.rindex("Vị trí hiện tại")
    assert "positionS != null" in strip[max(0, at - 300) : at], (
        "BlockStrip phải bỏ chú giải 'Vị trí hiện tại' khi chưa có vị trí (positionS null)"
    )


# ===========================================================================
# H4 — bước 4: nguồn bình luận, link đúng phiên, lời thường, nút + bộ đếm
# ===========================================================================
def test_h4_nguon_binh_luan_nam_trong_checklist():
    s4 = code(step_section(raw(), 4))
    assert 'import IngestPanel from "@/components/IngestPanel"' in raw()
    m = re.search(r"<IngestPanel(.*?)/>", s4, re.S)
    assert m, "bước 4 phải đặt IngestPanel trong checklist"
    for prop in (
        "sessionId={session.session_id}",
        "sessionPlatform={session.platform}",
        "sessionStatus={session.status}",
    ):
        assert prop in m.group(1), f"IngestPanel thiếu {prop}"
    row = s4[s4.rindex("<CheckRow", 0, m.start()) : m.start()]
    # Tiêu đề dòng lấy từ dongNguonBinhLuan() — mọi nhánh của hàm đều mở đầu
    # bằng "Nguồn bình luận" (chạy thật ở test_h4_dong_nguon_binh_luan_*).
    assert "title={dongNguon.title}" in row, (
        "IngestPanel phải là mục 'Nguồn bình luận' của checklist"
    )
    assert "const dongNguon = dongNguonBinhLuan(ingest)" in code(raw())
    assert "getIngestStatus(" in code(raw()), "dòng Nguồn bình luận phải biết bộ thu có chạy"
    assert INGEST_PANEL.exists()
    # Nguồn mô phỏng chỉ mở cho phiên chạy thử / dữ liệu mẫu — không bao giờ
    # hằng true (trộn bình luận giả vào phiên thật), không được bỏ trống.
    assert "allowSimulated={choPhepMoPhong(session)}" in m.group(1), (
        "IngestPanel phải nhận allowSimulated = dry_run || is_demo của phiên"
    )
    assert "allowSimulated?: boolean" in INGEST_PANEL.read_text(encoding="utf-8")


def test_h4_nguon_mo_phong_chi_mo_cho_phien_chay_thu_hoac_du_lieu_mau(tmp_path):
    """Chạy thật: phiên THẬT (kể cả bản máy chủ cũ không gửi `dry_run`) không
    được thấy nguồn mô phỏng; phiên dry_run hoặc is_demo thì được."""
    got = node_eval(
        tmp_path,
        "[choPhepMoPhong({is_demo: false, dry_run: false}),"
        " choPhepMoPhong({is_demo: false}),"
        " choPhepMoPhong({is_demo: false, dry_run: true}),"
        " choPhepMoPhong({is_demo: true, dry_run: false}),"
        " choPhepMoPhong({is_demo: true, dry_run: true})]",
    )
    assert got == [False, False, True, True, True]


def test_h4_link_man_nguoi_dan_mang_session():
    src = code(raw())
    assert 'href="/host"' not in src, "link /host trơn mở nhầm phiên live khác trong kho"
    assert (
        "const hostHref = session ? `/host?session=${encodeURIComponent(session.session_id)}`"
        in src
    )
    s4 = step_section(src, 4)
    host_links = [
        opening_tag(s4, m.start())
        for m in re.finditer(r"<Link\s", s4)
        if "Mở màn hình người dẫn" in s4[m.start() : s4.index("</Link>", m.start())]
    ]
    assert len(host_links) == 2, "hai nút mở màn người dẫn (trước và sau lên sóng)"
    for tag in host_links:
        assert "href={hostHref}" in tag


def test_h4_khong_con_chuoi_dev_tren_trang():
    src = raw()
    for bad in ("parser đã có", "vòng ingest chưa nối", "ma trận tín hiệu", "SIGNAL_LABEL"):
        assert bad not in src, f"chuỗi nội bộ {bad!r} còn trên /chay-phien"
    s4 = code(step_section(src, 4))
    assert "lyDoThuong(s)" in s4, "lý do tín hiệu phải qua lời thường trước khi hiện"
    assert "Dữ liệu hệ thống sẽ ghi lại" in s4


def test_h4_ly_do_tin_hieu_that_cua_may_chu_thanh_loi_thuong(tmp_path):
    """Chạy `signals.assess` thật cho một phiên YouTube trước giờ phát rồi cho
    từng dòng đi qua lyDoThuong: không dòng nào còn thuật ngữ nội bộ, và dòng
    THIẾU vẫn nói là thiếu (không bịa là có)."""
    from livelift.core.signals import assess

    cov = assess(
        has_schedule=True,
        n_ticks=0,
        n_ticks_with_viewers=0,
        tick_coverage_share=0.0,
        n_comments=0,
        n_clicks_valid=0,
        n_clicks_raw=0,
        n_orders=0,
        n_reactions=0,
        platform="youtube",
    )
    items = [{"name": s.name, "status": s.status, "detail": s.detail} for s in cov.signals]
    assert any("parser" in i["detail"] for i in items), "dữ liệu mẫu của test đã đổi — xem lại"
    got = node_eval(tmp_path, f"{json.dumps(items)}.map((s) => lyDoThuong(s))")
    for item, text in zip(items, got, strict=True):
        for jargon in ("parser", "ingest", "GIVT", "§", "telemetry"):
            assert jargon not in text, f"{item['name']}: {text!r} còn {jargon!r}"
        if item["status"] == "missing":
            assert re.search(r"chưa|THIẾU|không", text), f"{item['name']} THIẾU mà không nói thiếu"
    by = dict(zip([i["name"] for i in items], got, strict=True))
    assert "THIẾU" in by["reactions"]
    assert "không hiện số 0" in by["reactions"]


def test_h4_ly_do_la_giu_nguyen_van_chi_bo_ngoac_ky_thuat(tmp_path):
    got = node_eval(
        tmp_path,
        "[lyDoThuong({name: 'la', status: 'degraded',"
        " detail: 'thu được một phần (parser đã có, vòng ingest chưa nối) — xem lại'}),"
        " lyDoThuong({name: 'orders', status: 'ok', detail: '3 đơn ghi nhận'}),"
        " lyDoThuong({name: 'ticks', status: 'degraded',"
        " detail: 'telemetry chỉ phủ 60% thời gian phát'})]",
    )
    assert got == [
        "thu được một phần — xem lại",
        "3 đơn ghi nhận",
        "dữ liệu đo chỉ phủ 60% thời gian phát",
    ]


def test_h4_nut_len_song_viet_thuong_va_dem_viec_con_lai_khong_chan():
    s4 = code(step_section(raw(), 4))
    m = re.search(r"<Button\s+onClick=\{goLive\}", s4)
    assert m, "không tìm thấy nút Bắt đầu phát sóng"
    tag = opening_tag(s4, m.start())
    assert "uppercase" not in tag, "nút lên sóng viết hoa thường như mọi nút khác"
    assert "viecChuaXong" not in tag, "bộ đếm việc KHÔNG được chặn nút lên sóng"
    assert "Bắt đầu phát sóng" in s4[m.start() : s4.index("</Button>", m.start())]
    near = s4[max(0, m.start() - 900) : m.start()]
    assert "việc chưa xong" in near, "cạnh nút phải nói 'Còn N việc chưa xong'"
    assert "{viecChuaXong}" in near, "N phải là số đếm thật, không phải chữ cố định"
    decl = re.search(r"const viecChuaXong = \[(.*?)\]", code(raw()), re.S)
    assert decl, "thiếu phép đếm việc còn lại"
    for flag in ("!schedule", "!linkXong", "ingestRunning !== true", "!daMoHost"):
        assert flag in decl.group(1), f"bộ đếm việc thiếu cờ {flag}"


# ===========================================================================
# H5 — tên phiên mặc định thay UUID
# ===========================================================================
def test_h5_ten_phien_mac_dinh_theo_gio_viet_nam(tmp_path):
    got = node_eval(
        tmp_path,
        "[tenPhienMacDinh(new Date('2026-09-17T00:38:00Z'), 'youtube', 30),"
        " tenPhienMacDinh(new Date('2026-09-16T17:05:00Z'), 'facebook', 90),"
        " tenPhienMacDinh(new Date('2026-12-31T16:59:00Z'), 'nen_la', 120),"
        " laTenMacDinh('Live 17/09 07:38 · YouTube · 30 phút'),"
        " laTenMacDinh('Phiên live tối thứ Bảy')]",
    )
    assert got == [
        "Live 17/09 07:38 · YouTube · 30 phút",
        "Live 17/09 00:05 · Facebook · 90 phút",
        "Live 31/12 23:59 · nen_la · 120 phút",
        True,
        False,
    ]


def test_h5_de_trong_ten_thi_gui_ten_mac_dinh():
    src = code(raw())
    m = re.search(r"const makeSession = \(\) =>(.*?)\n    \}\);", src, re.S)
    assert m, "không tìm thấy makeSession"
    body = m.group(1)
    assert "form.title.trim() || tenPhienMacDinh(new Date(), form.platform, minutes)" in body
    assert "|| undefined" not in body, "để trống tên không được gửi undefined (nơi khác in UUID)"


# ===========================================================================
# Phản biện gói H — cờ theo phiên, đích thật của link đo, không chạy chồng,
# dòng Nguồn bình luận theo trạng thái thật của bộ thu
# ===========================================================================
def test_man_nguoi_dan_da_mo_chi_tinh_cho_dung_phien(tmp_path):
    """Link màn người dẫn ghim ?session=<id> (useHost không bao giờ đổi phiên),
    nên tab đã mở cho phiên A KHÔNG phục vụ phiên B. Kịch bản phản biện: mở màn
    người dẫn cho A → "Đổi thời lượng" (huỷ A, tạo B) → dòng checklist vẫn ✓."""
    got = node_eval(
        tmp_path,
        "[daMoDungPhien('A', 'A'), daMoDungPhien('A', 'B'), daMoDungPhien(null, 'B'),"
        " daMoDungPhien('A', null), daMoDungPhien(null, null), daMoDungPhien(null, undefined)]",
    )
    assert got == [True, False, False, False, False, False]


def test_huy_hoac_xoa_phien_reset_co_man_nguoi_dan():
    src = code(raw())
    assert "setDaMoHost(" not in src, "cờ true/false chung cho mọi phiên đã bị thay"
    assert "const daMoHost = daMoDungPhien(daMoHostFor, session?.session_id);" in src
    for what, body in (
        ("cancelAndEdit", cancel_and_edit_body(src)),
        ("clearSessionBits", clear_session_bits_body(src)),
    ):
        assert "setDaMoHostFor(null)" in body, f"{what} phải xoá dấu đã mở màn người dẫn"
        assert "setDaDanLink(false)" in body
    # mở màn người dẫn ghi ĐÚNG mã phiên đang chuẩn bị (cả hai nút)
    s4 = step_section(src, 4)
    assert s4.count("onClick={() => setDaMoHostFor(session?.session_id ?? null)}") == 2
    # localStorage: dấu đã-làm + link đo chỉ khôi phục cho CÙNG phiên
    marker = "if (sid != null && saved.sessionId === sid) {"
    assert marker in src
    restore = src[src.index(marker) :]
    restore = restore[: restore.index("\n      }\n")]
    for setter in ("setLinks(", "setDaDanLink(", "setDaMoHostFor("):
        assert setter in restore, f"{setter} phải nằm trong nhánh cùng phiên"
    assert "saved.daMoHost)" not in src, "cờ cũ không gắn phiên không được đọc lại"


def test_link_do_so_dich_that_khong_so_url_hien_tai(tmp_path):
    """Kịch bản phản biện chạy thật bằng các hàm thuần của trang: link đo tạo từ
    link mẫu → người bán dán link thật ở bước 1 → quay lại bước 4. Bản cũ tính
    cảnh báo bằng URL hiện tại (tắt cảnh báo) và không tạo lại link (khách bấm
    vẫn tới example.com)."""
    expr = """(() => {
      const mau = 'https://example.com/ao';
      const that = 'https://shop-cua-toi.vn/ao';
      let links = [{code: 'c1', product_id: 'ao', target_url: mau}];
      const demMau = (xs) =>
        xs.filter((l) => l.target_url != null && isSampleUrl(l.target_url)).length;
      const truoc = demMau(links);
      const kh = keHoachLinkDo(links, [{product_id: 'ao', url: that}], 5);
      const created = kh.map((v, i) =>
        ({code: 'n' + i, product_id: v.product_id, target_url: v.url}));
      links = ganLinkMoi(links, created);
      const lech = links.filter((l) => canTaoLaiLink(l, that)).length;
      return {truoc, kh, links, sau: demMau(links), lech};
    })()"""
    got = node_eval(tmp_path, expr)
    assert got["truoc"] == 1
    assert got["kh"] == [{"product_id": "ao", "url": "https://shop-cua-toi.vn/ao", "thay": True}]
    assert got["links"] == [
        {"code": "n0", "product_id": "ao", "target_url": "https://shop-cua-toi.vn/ao"}
    ], "link đo mới phải THAY link cũ, không nhân đôi"
    assert got["sau"] == 0
    assert got["lech"] == 0


def test_can_tao_lai_link_va_ke_hoach_link_do(tmp_path):
    got = node_eval(
        tmp_path,
        """[
          canTaoLaiLink({code: 'a', product_id: 'p', target_url: 'https://example.com/p'},
                        'https://that.vn/p'),
          canTaoLaiLink({code: 'a', product_id: 'p', target_url: 'https://that.vn/p'},
                        'https://that.vn/p'),
          canTaoLaiLink({code: 'a', product_id: 'p', target_url: 'https://that.vn/p'}, ''),
          canTaoLaiLink({code: 'a', product_id: 'p', target_url: 'https://that.vn/p'},
                        'that.vn/moi'),
          canTaoLaiLink({code: 'a', product_id: 'p', target_url: null}, 'https://that.vn/p'),
          keHoachLinkDo(
            [{code: 'a', product_id: 'p1', target_url: 'https://that.vn/p1'}],
            [{product_id: 'p1', url: 'https://that.vn/p1'},
             {product_id: 'p2', url: 'https://that.vn/p2'},
             {product_id: 'p3', url: ''}],
            5),
          keHoachLinkDo(
            [1, 2, 3, 4, 5].map((i) => ({code: 'c' + i, product_id: 'p' + i,
                                          target_url: 'https://that.vn/p' + i})),
            [{product_id: 'p2', url: 'https://that.vn/p2-moi'},
             {product_id: 'p6', url: 'https://that.vn/p6'}],
            5),
        ]""",
    )
    assert got[:5] == [True, False, False, False, True]
    assert got[5] == [{"product_id": "p2", "url": "https://that.vn/p2", "thay": False}], (
        "link khớp đích thì giữ; sản phẩm chưa có link thì tạo; không URL thì thôi"
    )
    assert got[6] == [{"product_id": "p2", "url": "https://that.vn/p2-moi", "thay": True}], (
        "đã chạm trần: không tạo link mới, nhưng link lệch đích vẫn phải tạo lại"
    )


def test_buoc_4_luu_va_doc_dich_that_cua_link_do():
    src = code(raw())
    body = ensure_links_body(src)
    assert "keHoachLinkDo(" in body
    assert "target_url: l.target_url" in body, "phải giữ đích THẬT máy chủ trả về"
    assert "setDaDanLink(false)" in body, "link đã thay thì dấu 'đã dán' không còn đúng"
    assert "setLinkThay(thay)" in body
    assert "isSampleUrl(urlOf(l.product_id))" not in src, (
        "cảnh báo link mẫu phải đọc đích thật của link đo, không đọc URL hiện tại"
    )
    assert "isSampleUrl(l.target_url)" in src
    assert "canTaoLaiLink(l, urlOf(l.product_id))" in src, "phải đếm link còn lệch đích"
    assert "linkLechDich === 0" in src, "link lệch đích thì dòng Link đo chưa xong"
    s4 = step_section(raw(), 4)
    assert "Link đo cũ vẫn dẫn tới địa chỉ cũ" in s4, "phải báo người bán link cũ vẫn trỏ đích cũ"


def test_ensure_links_khong_chay_chong_va_khong_ghi_de(tmp_path):
    """Ra rồi vào lại bước 4 nhanh: bản cũ chạy hai ensureLinks song song với
    cùng closure `links=[]` → máy chủ giữ hai bộ mã, trang chỉ hiện một bộ."""
    src = code(raw())
    body = ensure_links_body(src)
    assert body.lstrip().startswith("if (!session || linksInFlight.current) return;"), (
        "ensureLinks phải bỏ qua khi lời gọi trước chưa xong"
    )
    assert "linksInFlight.current = true;" in body
    fin = body[body.index("} finally {") :]
    assert "linksInFlight.current = false;" in fin, "khoá phải được mở cả khi lỗi"
    assert "setLinksBusy(false);" in fin
    assert "setLinks((prev) => ganLinkMoi(prev, created));" in body, (
        "cập nhật danh sách link phải dựa trên prev, không ghi đè bằng closure cũ"
    )
    assert "setLinks([...links" not in src
    assert "if (sessionIdRef.current !== sid) return;" in body, (
        "link tạo cho phiên đã bị huỷ không được lọt vào phiên mới"
    )
    effect = src[src.index("linksEnsured.current = false;\n      return;") :]
    effect = effect[: effect.index("]);") + 3]
    assert "if (!session || productsLoading || linksBusy) return;" in effect
    assert effect.endswith("[step, session?.session_id, productsLoading, linksBusy]);"), (
        "khi lời gọi trước xong, hiệu ứng phải chạy lại (linksBusy trong deps)"
    )
    got = node_eval(
        tmp_path,
        "(() => { const a = [{code: 'a1', product_id: 'p1', target_url: 'https://x.vn/1'}];"
        " const b = [{code: 'b1', product_id: 'p1', target_url: 'https://x.vn/1'},"
        "            {code: 'b2', product_id: 'p2', target_url: 'https://x.vn/2'}];"
        " return ganLinkMoi(ganLinkMoi([], a), b).map((l) => l.code); })()",
    )
    assert got == ["b1", "b2"], "cùng sản phẩm phải thay, không nhân đôi dòng"


def ingest_states() -> list[str]:
    m = re.search(r"export type IngestState =([^;]*);", TYPES_TS.read_text(encoding="utf-8"))
    assert m, "types.ts không còn khai IngestState"
    return re.findall(r'"(\w+)"', m.group(1))


def test_h4_dong_nguon_binh_luan_theo_trang_thai_that_cua_bo_thu(tmp_path):
    """Bộ thu dừng vì lỗi (running=false) mà dòng checklist ghi "chưa bật" là
    trái với IngestPanel ngay bên dưới. Mỗi trạng thái của vòng đời bộ thu
    (types.ts, cùng tập với máy chủ) có tiêu đề riêng; chỉ `chua_bat` nói
    "chưa bật"; trạng thái cuối của máy chủ không bao giờ hiện ✓."""
    from livelift.api.ingest_jobs import TRANG_THAI_CUOI

    states = ingest_states()
    assert set(TRANG_THAI_CUOI) <= set(states)
    inputs = [{"state": s, "running": s not in TRANG_THAI_CUOI} for s in states]
    got = node_eval(
        tmp_path,
        f"[dongNguonBinhLuan(null), ...{json.dumps(inputs)}.map((x) => dongNguonBinhLuan(x)),"
        " dongNguonBinhLuan({state: 'trang_thai_moi', running: false})]",
    )
    hoi, la = got[0], got[-1]
    rows = dict(zip(states, got[1:-1], strict=True))
    assert hoi == {"state": "todo", "title": "Nguồn bình luận: đang hỏi máy chủ…"}
    for s, row in rows.items():
        assert row["title"].startswith("Nguồn bình luận: "), s
        assert row["state"] in ("ok", "warn", "todo", "info"), s
        if s != "chua_bat":
            assert "chưa bật" not in row["title"], f"{s}: chỉ chua_bat mới được nói 'chưa bật'"
        if s in TRANG_THAI_CUOI:
            assert row["state"] != "ok", f"{s}: bộ thu đã dừng thì không được ✓"
    assert rows["chua_bat"] == {
        "state": "todo",
        "title": "Nguồn bình luận: chưa bật Bộ thu bình luận",
    }
    assert rows["loi"]["state"] == "warn"
    assert "dừng vì lỗi" in rows["loi"]["title"]
    assert "đã tắt" in rows["da_dung"]["title"]
    assert rows["dang_thu"]["state"] == "ok"
    assert rows["cho_len_song"]["state"] == "ok", "bật trước giờ phát là trạng thái đúng"
    assert la["state"] == "todo"
    assert "chưa bật" not in la["title"]
    # mọi trạng thái đều có nhánh riêng, và IngestPanel có nhãn cho cùng tập đó
    panel = INGEST_PANEL.read_text(encoding="utf-8")
    fn = extract(code(raw()), "dongNguonBinhLuan")
    for s in states:
        assert f"  {s}: {{" in panel, f"IngestPanel không còn nhãn cho {s}"
        assert f'case "{s}":' in fn, f"dongNguonBinhLuan thiếu nhánh {s}"


def test_poll_bo_thu_giu_ca_trang_thai():
    src = code(raw())
    assert "setIngest({ state: st.state, running: st.running })" in src, (
        "poll phải giữ st.state — chỉ giữ running thì lỗi và đã tắt đều thành 'chưa bật'"
    )
    assert "const ingestRunning = ingest?.running ?? null;" in src
