"""Cổng "số công bố phải khớp nguồn" — sinh từ kiểm toán rubric 14/09/2026.

Vì sao tệp này tồn tại. Kho mã đã có ``scripts/dong_bo_so_test.py`` để hợp nhất
SỐ TEST về một nguồn, nhưng không có gì canh các con số công bố CÒN LẠI trong
README — thứ đầu tiên một giám khảo mở ra. Kiểm toán ngày 14/09/2026 đếm thật và
tìm ra README đang lệch với chính ``docs/competition/FACT-SHEET.md`` (tệp mà
hồ sơ tuyên bố là nguồn sự thật duy nhất) ở ba chỗ:

* "18 sự cố" ở hai nơi, trong khi ``docs/incident-log.md`` có **41** hàng;
* "14.903 bình luận" — lô đo 06/09 đã bị lô 10/09 (**19.126**) thay thế;
* macro-F1 **0.870** nêu MỘT MÌNH, đúng thứ mà
  ``docs/benchmarks/intent-classifier.md`` in đậm cấm: *"Không được nêu 0.870
  một mình"* — vì trên chat bán hàng thật cùng mô hình chỉ đạt **0.271**.

Ba con số ấy sửa tay được trong hai phút; cái không sửa được bằng tay là việc
chúng sẽ lệch lại sau lô đo tới. Nên: gate.

Nguyên tắc của tệp: **không hằng số chép tay**. Mỗi kiểm tra so README với
NGUỒN của con số (đếm hàng sổ sự cố, đọc tiêu đề báo cáo live-fire), để khi lô
đo mới về, sửa nguồn là gate tự đòi sửa README.

Kiểm tra thứ tư canh một lớp lỗi khác cùng gốc: sự cố 27/08 (console Windows
cp1252 làm mọi CLI in tiếng Việt chết bằng ``UnicodeEncodeError``). Kho mã đã có
``livelift.console.configure``, nhưng 14/09 vẫn còn 4 script quên gọi — trong đó
có đúng bước (2) của checklist 15 phút trước hội đồng.

Không mạng, không tiến trình con, không server.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

GOC = Path(__file__).resolve().parents[1]
README = GOC / "README.md"
SO_SU_CO = GOC / "docs" / "incident-log.md"
LIVE_FIRE = GOC / "docs" / "benchmarks" / "live-fire-da-nguon.md"

# Một hàng sự cố bắt đầu bằng "| dd/mm/yyyy |" — đúng định nghĩa mà FACT-SHEET
# dùng để ra con số 41 ("đếm số hàng bảng trong docs/incident-log.md").
HANG_SU_CO_RE = re.compile(r"^\| \d{2}/\d{2}/\d{4} \|", re.M)


@pytest.fixture(scope="module")
def readme() -> str:
    return README.read_text(encoding="utf-8")


def test_so_su_co_trong_readme_khop_so_hang_cua_so_su_co(readme: str) -> None:
    """README trích số sự cố; nguồn là số hàng bảng trong sổ sự cố."""
    that = len(HANG_SU_CO_RE.findall(SO_SU_CO.read_text(encoding="utf-8")))
    assert that > 0, "không đọc được hàng nào từ docs/incident-log.md"

    trich = {int(m) for m in re.findall(r"\*?\*?(\d+)\*?\*? sự cố", readme)}
    assert trich, "README không còn trích số sự cố nào — nếu cố ý, sửa test này"
    assert trich == {that}, (
        f"README ghi {sorted(trich)} sự cố nhưng docs/incident-log.md có {that} hàng. "
        f"Sổ sự cố là nguồn; sửa README (mọi chỗ), đừng sửa con số ở đây."
    )


def test_so_binh_luan_live_fire_trong_readme_khop_bao_cao_lo_do(readme: str) -> None:
    """Số bình luận live-fire phải là lô ĐANG hiệu lực, không phải lô cũ."""
    tieu_de = LIVE_FIRE.read_text(encoding="utf-8")[:600]
    m = re.search(r"\*\*([\d.]+) bình luận thật\*\*", tieu_de)
    assert m, "không đọc được số bình luận ở đầu docs/benchmarks/live-fire-da-nguon.md"
    hien_hanh = m.group(1)

    dong_co_so = [d for d in readme.splitlines() if re.search(r"\d{1,3}\.\d{3} bình luận", d)]
    assert dong_co_so, "README không còn trích số bình luận live-fire nào"
    # Số của lô CŨ chỉ được xuất hiện kèm chữ "cũ" (câu giải thích lô nào thay
    # lô nào); đứng một mình là công bố một con số đã bị thay thế.
    vi_pham = [
        f"dòng {i}: {d.strip()[:110]}"
        for i, d in enumerate(readme.splitlines(), 1)
        if (so := set(re.findall(r"(\d{1,3}\.\d{3}) bình luận", d)))
        and so - {hien_hanh}
        and "cũ" not in d
    ]
    assert not vi_pham, (
        f"README trích số bình luận không phải lô đang hiệu lực ({hien_hanh}) "
        f"và không nói rõ đó là lô cũ: " + " | ".join(vi_pham)
    )


F1_BIEN_SOAN_RE = re.compile(r"0[.,]870?\b")
# Số trên chat thật. 0,211 là số "trước" CHÍNH THỨC, chạy lại được
# (``python -m livelift.nlp.eval_intent``, 393 dòng nhãn do tác tử AI gán); 0,271
# (live-fire 08/09) KHÔNG tái lập được. Phản biện 25/09/2026: gate cũ chỉ nhận
# 0,271, tức là ép README trích lại đúng con số không tái lập được — nay nhận cả hai.
F1_CHAT_THAT_RE = re.compile(r"0[.,](?:211|271)\b")


def _dong_neu_f1_bien_soan_mot_minh(text: str) -> list[str]:
    return [
        f"dòng {i}: {d.strip()[:110]}"
        for i, d in enumerate(text.splitlines(), 1)
        if F1_BIEN_SOAN_RE.search(d) and not F1_CHAT_THAT_RE.search(d)
    ]


def test_readme_khong_bao_gio_neu_f1_bo_bien_soan_mot_minh(readme: str) -> None:
    """Quy tắc của chính docs/benchmarks/intent-classifier.md, nâng lên thành gate.

    Con số đẹp (bộ biên soạn) và con số thật (chat bán hàng) phải đi CẶP trên
    cùng một dòng — một giám khảo đọc lướt chỉ thấy dòng đó.
    """
    vi_pham = _dong_neu_f1_bien_soan_mot_minh(readme)
    assert not vi_pham, (
        "README nêu macro-F1 bộ biên soạn (0,870) mà không kèm số trên chat thật "
        "(0,211 chính thức; 0,271 cũ, không tái lập được) trên cùng dòng — đúng điều "
        "docs/benchmarks/intent-classifier.md in đậm cấm ('Không được nêu 0.870 một "
        "mình'):\n  " + "\n  ".join(vi_pham)
    )


def test_gate_f1_nhan_so_chinh_thuc_0_211_khong_ep_trich_0_271() -> None:
    """Dòng chỉ ghép 0,870 với số chính thức 0,211 là HỢP LỆ; 0,870 một mình vẫn đỏ."""
    assert not _dong_neu_f1_bien_soan_mot_minh(
        "macro-F1 0,870 trên 320 câu do AI soạn, nhưng trên 393 bình luận thật chỉ 0,211"
    )
    assert _dong_neu_f1_bien_soan_mot_minh("macro-F1 0,870 trên 320 câu do AI soạn")


def _ten_configure(cay: ast.Module) -> set[str]:
    """Tên cục bộ mà ``livelift.console.configure`` được nhập vào (kể cả alias)."""
    ten = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.ImportFrom) and n.module == "livelift.console":
            ten |= {a.asname or a.name for a in n.names if a.name == "configure"}
    return ten


def _da_lo_encoding(duong_dan: Path) -> bool:
    """Tệp có đặt lại encoding của stdout không — qua helper chung hoặc tay."""
    cay = ast.parse(duong_dan.read_text(encoding="utf-8"))
    ten = _ten_configure(cay)
    for n in ast.walk(cay):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        if isinstance(f, ast.Name) and f.id in ten:
            return True
        # `sys.stdout.reconfigure(encoding=...)` — cách làm tay, cũng chấp nhận
        if isinstance(f, ast.Attribute) and f.attr == "reconfigure":
            return True
    return False


CO_DAU_RE = re.compile(
    r"[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩị"
    r"òóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]",
    re.I,
)


def _in_tieng_viet(duong_dan: Path) -> bool:
    """Tệp có thể ĐẨY RA stdout chữ tiếng Việt có dấu không.

    Docstring module được loại trừ — nó chỉ ra màn hình khi argparse dùng
    ``description=__doc__``; trường hợp đó bắt riêng ở dưới. Nhờ vậy một script
    có chú thích tiếng Việt nhưng in toàn tiếng Anh (``check_isolation.py``)
    không bị báo oan.
    """
    cay = ast.parse(duong_dan.read_text(encoding="utf-8"))
    doc = ast.get_docstring(cay)
    # Chính NÚT docstring, không phải chuỗi đã được get_docstring làm sạch —
    # so bằng giá trị sẽ trượt vì get_docstring đã dedent/strip.
    nut_doc = None
    if cay.body and isinstance(cay.body[0], ast.Expr):
        gt = cay.body[0].value
        if isinstance(gt, ast.Constant) and isinstance(gt.value, str):
            nut_doc = gt
    for n in ast.walk(cay):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            if n is nut_doc:
                continue
            if CO_DAU_RE.search(n.value):
                return True
    # argparse in chính docstring module ra khi gặp `--help`
    dung_doc = any(isinstance(n, ast.Name) and n.id == "__doc__" for n in ast.walk(cay))
    return bool(dung_doc and doc and CO_DAU_RE.search(doc))


@pytest.mark.parametrize(
    "script",
    sorted(p for p in (GOC / "scripts").glob("*.py") if p.name != "__init__.py"),
    ids=lambda p: p.name,
)
def test_moi_script_in_tieng_viet_deu_goi_console_configure(script: Path) -> None:
    """Sự cố 27/08: console Windows cp1252 giết mọi CLI in tiếng Việt.

    ``livelift.console.configure`` là cách sửa đã chốt của kho mã. Script nào
    còn chữ tiếng Việt trong chuỗi thì phải gọi nó — nếu không, trên máy giám
    khảo (Windows, code page mặc định) script chết bằng ``UnicodeEncodeError``
    thay vì làm việc của nó.
    """
    if not _in_tieng_viet(script):
        pytest.skip("script không in tiếng Việt")
    assert _da_lo_encoding(script), (
        f"{script.name} có chuỗi tiếng Việt nhưng không gọi configure() — "
        f"trên console cp1252 nó sẽ chết bằng UnicodeEncodeError (sự cố 27/08). "
        f"Thêm `from livelift.console import configure` và gọi configure() ở "
        f"dòng đầu main(), TRƯỚC parse_args (xem scripts/chay_local.py)."
    )


def test_readme_khong_con_bo_so_hieu_chuan_cu_khong_tai_lap_duoc(readme: str) -> None:
    """Kiểm toán 17/09/2026: bộ số A/A của 30/08 (4,5% · p=0,872 · phủ 95,5% ·
    lệch −0,3%) đã được xác nhận KHÔNG tái lập được từ 14/09 và thay ở FACT-SHEET,
    nhưng README vẫn công bố nó ở hai chỗ. ``do_lai_so_hieu_chuan.py --kiem`` chỉ
    đối chiếu tệp JSON, không quét tài liệu, nên không cổng nào bắt được."""
    cu = ("4.5%", "4,5%", "0.872", "0,872", "95.5%", "95,5%", "−0.3%", "−0,3%")
    con_lai = [
        (i, d.strip()[:120])
        for i, d in enumerate(readme.splitlines(), 1)
        for so in cu
        if so in d and "cũ" not in d and "không tái lập" not in d
    ]
    assert not con_lai, f"README còn trích bộ số hiệu chuẩn cũ: {con_lai}"


# ---------------------------------------------------------------------------
# Tích hợp 25/09/2026 tối: tài liệu nộp phải khớp NGUỒN, không chỉ README
# ---------------------------------------------------------------------------
FACT_SHEET = GOC / "docs" / "competition" / "FACT-SHEET.md"
HO_SO = GOC / "docs" / "competition" / "sang-tao-tre-2026" / "noi-dung.md"
NLP_NANG_CAP = GOC / "docs" / "competition" / "sang-tao-tre-2026" / "03-NLP-NANG-CAP.md"
MO_HINH = GOC / "src" / "livelift" / "nlp" / "model"


def _dong_bang(van_ban: str, dau: str) -> str:
    dong = [d for d in van_ban.splitlines() if d.startswith(dau)]
    assert len(dong) == 1, f"phải có đúng một dòng bảng bắt đầu bằng {dau!r}, có {len(dong)}"
    return dong[0]


def test_so_su_co_o_fact_sheet_va_ho_so_khop_so_hang_cua_so_su_co() -> None:
    """Gate README ở trên không quét FACT-SHEET hay hồ sơ: tối 25/09/2026 sổ thêm hàng mà
    hai tệp nộp này vẫn có thể ghi số cũ."""
    so = SO_SU_CO.read_text(encoding="utf-8")
    that = len(HANG_SU_CO_RE.findall(so))
    ngay_25 = len(re.findall(r"^\| 25/09/2026 \|", so, re.M))
    dong = _dong_bang(FACT_SHEET.read_text(encoding="utf-8"), "| Sổ sự cố |")
    assert f"**{that} sự cố có nguyên nhân gốc**" in dong, dong[:160]
    assert f"{that} hàng, trong đó {ngay_25} hàng ngày 25/09" in dong, dong[:220]
    trich = {int(m) for m in re.findall(r"\*\*(\d+)\*\* sự cố", HO_SO.read_text("utf-8"))}
    assert trich == {that}, f"hồ sơ ghi {sorted(trich)} sự cố, sổ có {that} hàng"


def test_fact_sheet_hieu_chuan_trich_dung_lan_do_ghi_trong_json() -> None:
    """V3 (25/09/2026) đo lại hiệu chuẩn trên 17c3ee1 và ghi ``ban_git``/``ngay_do`` vào
    JSON, nhưng dòng A/A của FACT-SHEET vẫn nói "đo 14/09 … chạy lại trên 390027b" — không
    script đồng bộ nào chạm phần chữ của dòng này."""
    import json

    so = json.loads((GOC / "docs" / "benchmarks" / "so-hieu-chuan.json").read_text("utf-8"))
    dong = _dong_bang(FACT_SHEET.read_text(encoding="utf-8"), "| Hiệu chuẩn A/A")
    assert so["ban_git"] in dong, f"dòng A/A không nêu bản git của lần đo ({so['ban_git']})"
    ngay = "/".join(reversed(so["ngay_do"].split("-")))
    assert ngay in dong, f"dòng A/A không nêu ngày đo {ngay}"


def test_kich_thuoc_artifact_trong_03_nlp_khop_tep_that() -> None:
    """03-NLP ghi "Tăng gấp đôi kích thước artifact … ≈ 921 KB so với 86 KB": 921 là KiB,
    86 là kB, và tỷ lệ thật khoảng 10,9 lần chứ không phải gấp đôi."""
    v2 = (MO_HINH / "intent_clf_v2.joblib").stat().st_size
    v1 = (MO_HINH / "intent_clf.joblib").stat().st_size
    t = NLP_NANG_CAP.read_text(encoding="utf-8")
    assert "gấp đôi kích thước" not in t.lower()
    for n in (v1, v2):
        assert f"{n:,} byte".replace(",", ".") in t, f"thiếu kích thước thật {n} byte"
        assert f"≈ {round(n / 1024)} KiB" in t, f"thiếu {round(n / 1024)} KiB"
    ti_le = f"{v2 / v1:.1f}".replace(".", ",")
    assert f"{ti_le} lần" in t, f"tỷ lệ v2/v1 thật là {ti_le} lần"


def test_ho_so_khong_con_noi_ten_dinh_lien_lot_bo_loc() -> None:
    """Hồ sơ §3.2 ghi "Còn mở: … ``chữ@tên`` vẫn lọt bộ lọc" và §3.3 "lọc nốt 6 dòng" sau
    khi bộ lọc đã vá (b331076, 16 dòng, 8 tên). Câu chữ phải theo hành vi thật của mã."""
    from livelift.ingest.pii import scrub

    for tho in ("cảm ơn bạn@minhthu8106 nhiều", "đẹp quá@@kimchi_88"):  # tên BỊA
        assert scrub(tho).counts.get("social", 0) == 1, "tiền đề: bộ lọc bắt dạng dính liền"
    t = re.sub(r"\s+", " ", HO_SO.read_text(encoding="utf-8"))
    assert "vẫn lọt bộ lọc" not in t, "hồ sơ còn nói tên dính liền lọt bộ lọc"
    assert "lọc nốt 6 dòng" not in t
    assert "16 dòng" in t
    assert "8 tên" in t
