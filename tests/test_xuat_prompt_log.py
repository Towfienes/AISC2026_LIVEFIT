"""scripts/xuat_prompt_log.py — phân vai đúng, không cắt ngầm, có log tác tử con, lọc sạch.

Mọi nhật ký ở đây là dữ liệu TỔNG HỢP dựng theo đúng cấu trúc bản ghi của Claude
Code (``type``/``origin``/``isMeta``/``message.content``), không đọc nhật ký thật.

Lỗi gốc (kiểm toán 25/09/2026, dossier-audit-C §9): bộ xuất cũ gán nhãn "NGƯỜI
DÙNG" cho MỌI bản ghi ``type == "user"`` — mà Claude Code lưu kết quả công cụ và
thông báo tác vụ dưới đúng loại đó. Số "1.297 câu lệnh của đội" vì thế bị thổi
phồng khoảng 20 lần (1.297 so với 66 ở cùng 3 phiên), và đầu ra của máy đứng tên
người. Bộ xuất cũ còn cắt ngầm đầu vào công cụ (chính là mã do AI viết) ở 800 ký
tự mà không đánh dấu, và không
xuất nhật ký tác tử con nếu không bật cờ.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter
from pathlib import Path

import pytest

_GOC = Path(__file__).resolve().parent.parent
_SCRIPT = _GOC / "scripts" / "xuat_prompt_log.py"
_spec = importlib.util.spec_from_file_location("xuat_prompt_log", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
xpl = importlib.util.module_from_spec(_spec)
sys.modules["xuat_prompt_log"] = xpl
_spec.loader.exec_module(xpl)

PHIEN = "11111111-2222-3333-4444-555555555555"
PHIEN8 = PHIEN[:8]


# --------------------------------------------------------------------------
# Dựng bản ghi tổng hợp
# --------------------------------------------------------------------------
def _ts(phut: int) -> str:
    return f"2026-09-01T01:{phut:02d}:00.000Z"


def _nguoi(text, phut, *, noi_dung=None):
    return {
        "type": "user",
        "origin": {"kind": "human"},
        "promptId": f"prompt-{phut}",
        "promptSource": "sdk",
        "isSidechain": False,
        "version": "2.1.251",
        "timestamp": _ts(phut),
        "message": {"role": "user", "content": noi_dung if noi_dung is not None else text},
    }


def _ai(phut, *khoi, model="claude-opus-5"):
    return {
        "type": "assistant",
        "isSidechain": False,
        "version": "2.1.251",
        "timestamp": _ts(phut),
        "message": {"role": "assistant", "model": model, "content": list(khoi)},
    }


def _ket_qua(tool_id, noi_dung, phut):
    return {
        "type": "user",
        "isSidechain": False,
        "version": "2.1.251",
        "timestamp": _ts(phut),
        "sourceToolAssistantUUID": "x",
        "toolUseResult": {"stdout": "..."},
        "message": {
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": tool_id, "content": noi_dung}],
        },
    }


def _user_tho(text, phut, **them):
    rec = {
        "type": "user",
        "isSidechain": False,
        "version": "2.1.251",
        "timestamp": _ts(phut),
        "message": {"role": "user", "content": text},
    }
    rec.update(them)
    return rec


def _ghi(tep: Path, recs) -> None:
    tep.parent.mkdir(parents=True, exist_ok=True)
    tep.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in recs) + "\n", "utf-8")


NOI_DUNG_WRITE = (
    "from fastapi import APIRouter\n"
    "router = APIRouter()\n\n"
    '@router.post("/phien")\n'
    "def tao(): ...\n\n"
    "@pytest.mark.slow\n"
    "def test_cham(): ...\n"
    "# nhap: import type from '@types/react'\n"
    "# Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>\n"
    + ("x = 1  # dong dem\n" * 400)
    + "# DUOI-TEP-XYZ\n"
)
KET_QUA_DAI = ("dong ket qua cong cu " * 300) + "DUOI-KET-QUA-ABC"


def _dung_phien(goc: Path) -> Path:
    """Một phiên chính: 2 câu người gõ, 1 lệnh gạch chéo, 1 lần bấm dừng,
    3 kết quả công cụ, 1 thông báo tác vụ, 1 bản ghi meta, 1 tác tử con."""
    thu_muc = goc / "d--AISC2026"
    recs = [
        {
            "type": "attachment",
            "timestamp": _ts(0),
            "attachment": {
                "type": "prompt_snapshot",
                "systemPrompt": ["You are an interactive agent. CHI-DAN-HE-THONG-01", "Phần 2"],
            },
        },
        _user_tho(
            "<command-name>/model</command-name>\n<command-message>model</command-message>\n"
            "<command-args></command-args>",
            1,
        ),
        _user_tho("<local-command-stdout>Set model to claude-opus-5</local-command-stdout>", 1),
        _nguoi("CAU-LENH-NGUOI-1: dựng API phiên, gửi báo cáo cho ban.a@gmail.com", 2),
        _ai(
            3,
            {"type": "thinking", "thinking": "BI-MAT-SUY-LUAN", "signature": "sig"},
            {"type": "text", "text": "Được, tôi viết `router` trước."},
            {
                "type": "tool_use",
                "id": "toolu_1",
                "name": "Write",
                "input": {"file_path": "D:/x/api.py", "content": NOI_DUNG_WRITE},
            },
        ),
        _ket_qua("toolu_1", "KET-QUA-CONG-CU-1: đã ghi tệp", 4),
        _ai(5, {"type": "tool_use", "id": "toolu_2", "name": "Bash", "input": {"command": "ls"}}),
        _ket_qua("toolu_2", KET_QUA_DAI, 6),
        _user_tho(
            "<task-notification>\n<task-id>abc</task-id>\n<status>completed</status>\n"
            "</task-notification>",
            7,
            origin={"kind": "task-notification"},
        ),
        _user_tho("Continue from where you left off.", 8, isMeta=True),
        _user_tho([{"type": "text", "text": "[Request interrupted by user]"}], 9),
        _nguoi(
            "",
            10,
            noi_dung=[
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": "iVBORw0KGgoAAAA",
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "CAU-LENH-NGUOI-2 gọi 090 123 4567 hoặc @Cường-123, khoá "
                        "AIzaSyA1234567890abcdefghijklmnopqrstuv, YOUTUBE_API_KEY=abc123def456, "
                        "mã nội bộ SO-BI-MAT-DOI-42\n```\nkhối mã\n```"
                    ),
                },
            ],
        ),
        _ai(11, {"type": "tool_use", "id": "toolu_3", "name": "Read", "input": {"file_path": "a"}}),
        _ket_qua("toolu_3", [{"type": "text", "text": "noi dung tep"}], 12),
    ]
    _ghi(thu_muc / f"{PHIEN}.jsonl", recs)

    con = thu_muc / PHIEN / "subagents" / "workflows" / "wf_abc" / "agent-a0001.jsonl"
    _ghi(
        con,
        [
            {
                "type": "user",
                "isSidechain": True,
                "version": "2.1.251",
                "timestamp": _ts(20),
                "message": {"role": "user", "content": "GIAO-VIEC-TAC-TU-CON: kiểm thử toàn bộ"},
            },
            _ai(21, {"type": "text", "text": "TRA-LOI-TAC-TU-CON"}, model="claude-fable-5"),
            _ai(
                22, {"type": "tool_use", "id": "toolu_9", "name": "Grep", "input": {"pattern": "x"}}
            ),
            _ket_qua("toolu_9", "khong co", 23),
        ],
    )
    (con.parent / "agent-a0001.meta.json").write_text(
        json.dumps({"agentType": "workflow-subagent", "description": "Kiểm thử"}), "utf-8"
    )
    # kịch bản điều phối (workflow script) do AI viết
    js = goc / "D--AISC2026-livelift" / PHIEN / "workflows" / "scripts" / "kiem-thu-wf_abc.js"
    js.parent.mkdir(parents=True, exist_ok=True)
    js.write_text("export const meta = { name: 'kiem-thu' }\n", "utf-8")
    return thu_muc


@pytest.fixture
def goc(tmp_path, monkeypatch):
    projects = tmp_path / "projects"
    _dung_phien(projects)
    monkeypatch.setattr(xpl, "PROJECTS_ROOT", projects)
    monkeypatch.setattr(xpl, "DENYLIST", {"SO-BI-MAT-DOI-42": "[THONG-TIN-DOI]"})
    return projects


@pytest.fixture
def ra(goc, tmp_path):
    out = tmp_path / "ra"
    assert xpl.main(["--ra", str(out), "--cat-ket-qua", "1000"]) == 0
    return out


def _tep_phien(ra: Path) -> str:
    ds = sorted((ra / "phien").glob(f"*{PHIEN8}*.md"))
    assert len(ds) == 1, ds
    return ds[0].read_text("utf-8")


def _cac_muc(md: str) -> list[tuple[str, str]]:
    """Tách tệp phiên thành (dòng tiêu đề, thân) theo tiêu đề cấp 3."""
    phan = re.split(r"^### ", md, flags=re.M)[1:]
    return [(p.split("\n", 1)[0], p.split("\n", 1)[1] if "\n" in p else "") for p in phan]


# --------------------------------------------------------------------------
# 1. Phân vai
# --------------------------------------------------------------------------
def test_ket_qua_cong_cu_khong_duoc_tinh_la_cau_lenh_nguoi(ra):
    so = json.loads((ra / "SO-DEM.json").read_text("utf-8"))
    p = so["phien"][PHIEN]
    assert p["cau_lenh_nguoi"] == 2
    assert p["lenh_gach_cheo"] == 1
    assert p["bam_dung"] == 1
    assert p["ket_qua_cong_cu"] == 3
    assert p["goi_cong_cu"] == 3
    assert so["tong"]["cau_lenh_nguoi"] == 2

    muc = _cac_muc(_tep_phien(ra))
    nguoi = [t for t, _ in muc if "NGƯỜI — thành viên đội gõ" in t]
    assert len(nguoi) == 2
    # đầu ra của máy KHÔNG bao giờ đứng tên người
    for tieu_de, than in muc:
        if "KET-QUA-CONG-CU-1" in than or "task-notification" in than:
            assert "NGƯỜI" not in tieu_de, tieu_de
    kq = [t for t, b in muc if "KET-QUA-CONG-CU-1" in b]
    assert kq
    assert "CÔNG CỤ" in kq[0]


def test_lenh_gach_cheo_va_thong_bao_he_thong_duoc_dan_nhan_rieng(ra):
    muc = _cac_muc(_tep_phien(ra))
    lenh = [t for t, b in muc if "/model" in b and "<command-name>" in b]
    assert lenh
    assert "lệnh gạch chéo" in lenh[0]
    meta = [t for t, b in muc if "Continue from where you left off." in b]
    assert meta
    assert "HỆ THỐNG" in meta[0]


# --------------------------------------------------------------------------
# 2. Không cắt ngầm
# --------------------------------------------------------------------------
def test_dau_vao_cong_cu_giu_nguyen_ket_qua_cat_co_dau(ra):
    md = _tep_phien(ra)
    assert "DUOI-TEP-XYZ" in md, "đầu vào Write (mã do AI viết) bị cắt ngầm"
    assert md.count("x = 1  # dong dem") == 400
    assert "DUOI-KET-QUA-ABC" not in md
    m = re.search(r"\(cắt bớt (\d+) ký tự\)", md)
    assert m, "kết quả công cụ bị cắt mà không có dấu"
    bot = int(m.group(1))
    assert len(KET_QUA_DAI) - 1000 - 300 <= bot <= len(KET_QUA_DAI) - 1000


def test_moi_cho_cat_deu_co_dau(ra):
    so = json.loads((ra / "SO-DEM.json").read_text("utf-8"))
    tong_cat = so["tong"]["so_cho_cat"]
    dau = sum(
        len(re.findall(r"\(cắt bớt \d+ ký tự\)", f.read_text("utf-8"))) for f in ra.rglob("*.md")
    )
    assert tong_cat >= 1
    assert dau == tong_cat


# --------------------------------------------------------------------------
# 3. Log tác tử con
# --------------------------------------------------------------------------
def test_log_tac_tu_con_duoc_xuat_mac_dinh_va_khong_dung_ten_nguoi(ra):
    tep = list((ra / "tac-tu-con").rglob("*a0001*.md"))
    assert len(tep) == 1
    md = tep[0].read_text("utf-8")
    muc = _cac_muc(md)
    giao = [t for t, b in muc if "GIAO-VIEC-TAC-TU-CON" in b]
    assert giao
    assert "TÁC TỬ ĐIỀU PHỐI" in giao[0]
    assert "NGƯỜI" not in giao[0]
    assert "TRA-LOI-TAC-TU-CON" in md
    so = json.loads((ra / "SO-DEM.json").read_text("utf-8"))
    assert so["phien"][PHIEN]["tac_tu_con"] == 1
    assert so["phien"][PHIEN]["cau_lenh_nguoi"] == 2  # tác tử con không cộng vào số người
    assert "claude-fable-5" in so["tong"]["mo_hinh"]
    # kịch bản điều phối do AI viết cũng được xuất
    assert list((ra / "kich-ban-dieu-phoi").rglob("kiem-thu-wf_abc.js"))


def test_bo_tac_tu_con_khi_duoc_yeu_cau(goc, tmp_path):
    out = tmp_path / "ra2"
    assert xpl.main(["--ra", str(out), "--bo-tac-tu-con"]) == 0
    assert not list(out.rglob("*a0001*.md"))


# --------------------------------------------------------------------------
# 4. Lọc bí mật + dữ liệu cá nhân (bộ lọc sản phẩm) mà không phá mã
# --------------------------------------------------------------------------
def test_che_pii_va_bi_mat_nhung_giu_nguyen_decorator(ra):
    toan_bo = "\n".join(f.read_text("utf-8") for f in ra.rglob("*.md"))
    for tho in (
        "ban.a@gmail.com",
        "090 123 4567",
        "@Cường-123",
        "AIzaSyA1234567890abcdefghijklmnopqrstuv",
        "abc123def456",
        "SO-BI-MAT-DOI-42",
    ):
        assert tho not in toan_bo, tho
    for token in ("[EMAIL]", "[SĐT]", "[MXH]", "[GOOGLE-API-KEY]", "[THONG-TIN-DOI]"):
        assert token in toan_bo, token
    # mã do AI viết không bị bộ lọc handle làm hỏng
    assert '@router.post("/phien")' in toan_bo
    assert "@pytest.mark.slow" in toan_bo
    assert "@types/react" in toan_bo
    assert "noreply@anthropic.com" in toan_bo


def test_anh_va_suy_luan_khong_xuat_nhung_co_ghi_nhan(ra):
    md = _tep_phien(ra)
    assert "iVBORw0KGgo" not in md
    assert "BI-MAT-SUY-LUAN" not in md
    assert "[ảnh đính kèm" in md
    so = json.loads((ra / "SO-DEM.json").read_text("utf-8"))
    assert so["phien"][PHIEN]["anh_khong_xuat"] == 1
    assert so["phien"][PHIEN]["khoi_suy_luan_khong_xuat"] == 1


def test_rao_markdown_dai_hon_moi_chuoi_backtick_ben_trong():
    khoi = xpl._rao("a\n```\nb\n````\n", "text")
    dau = khoi.split("\n", 1)[0]
    assert dau.startswith("`````")
    assert khoi.rstrip().endswith("`````")


# --------------------------------------------------------------------------
# 5. Quét lại bản xuất, manifest, system prompt
# --------------------------------------------------------------------------
def test_quet_lai_ban_xuat_bang_khong_va_bat_duoc_cai_lot(ra):
    kq = xpl.quet_thu_muc(ra)
    assert sum(kq.values()) == 0, kq
    (ra / "phien" / "lot.md").write_text("gọi 0901234567 nhé", "utf-8")
    kq2 = xpl.quet_thu_muc(ra)
    assert sum(kq2.values()) >= 1
    assert xpl.main(["--quet", str(ra)]) == 1


def test_manifest_sha256_khop_tung_tep(ra):
    dong = (ra / "MANIFEST-SHA256.txt").read_text("utf-8").strip().splitlines()
    assert dong
    da_kiem = 0
    for d in dong:
        h, ten = d.split(" *", 1)
        tep = ra / ten
        assert hashlib.sha256(tep.read_bytes()).hexdigest() == h, ten
        da_kiem += 1
    xuat = [f for f in ra.rglob("*") if f.is_file() and f.name != "MANIFEST-SHA256.txt"]
    assert da_kiem == len(xuat)
    nguon = (ra / "MANIFEST-NGUON-SHA256.txt").read_text("utf-8")
    assert f"{PHIEN}.jsonl" in nguon


def test_system_prompt_trong_nhat_ky_duoc_xuat(ra):
    tep = list((ra / "system-prompt").glob(f"*{PHIEN8}*.md"))
    assert len(tep) == 1
    assert "CHI-DAN-HE-THONG-01" in tep[0].read_text("utf-8")


def test_kiem_tra_chi_dem_khong_ghi_tep(goc, tmp_path, capsys, monkeypatch):
    monkeypatch.chdir(tmp_path)
    truoc = set(tmp_path.rglob("*"))
    assert xpl.main(["--kiem-tra"]) == 0
    out = capsys.readouterr().out
    assert "câu lệnh người gõ" in out.lower() or "Câu lệnh người gõ" in out
    assert set(tmp_path.rglob("*")) == truoc


def test_sao_luu_bo_sung_tep_da_mat_va_kiem_tien_to(goc, tmp_path):
    sl = tmp_path / "sao-luu" / "2026-09-15"
    # bản sao cũ của phiên sống: phải là tiền tố byte của bản sống
    song = goc / "d--AISC2026" / f"{PHIEN}.jsonl"
    cu = sl / "d--AISC2026" / f"{PHIEN}.jsonl"
    cu.parent.mkdir(parents=True)
    cu.write_bytes(song.read_bytes()[:200])
    # một phiên chỉ còn trong bản sao (bản sống đã bị Claude Code dọn)
    mat = "99999999-0000-0000-0000-000000000000"
    _ghi(sl / "d--AISC2026" / f"{mat}.jsonl", [_nguoi("CAU-LENH-TU-SAO-LUU", 30)])
    out = tmp_path / "ra3"
    assert xpl.main(["--ra", str(out), "--sao-luu", str(sl)]) == 0
    so = json.loads((out / "SO-DEM.json").read_text("utf-8"))
    assert so["sao_luu"]["tep_bo_sung"] == 1
    assert so["sao_luu"]["tep_la_tien_to_ban_song"] == 1
    assert so["sao_luu"]["tep_lech"] == 0
    assert so["phien"][mat]["cau_lenh_nguoi"] == 1
    assert so["tong"]["cau_lenh_nguoi"] == 3


def test_chay_nhu_script_that_tu_dau_den_cuoi(tmp_path):
    """Sự cố 25/09: ``_readme`` được định nghĩa SAU khối ``if __name__ == "__main__"``,
    nên gọi qua import (mọi test ở trên) thì xanh mà chạy thật bằng dòng lệnh thì
    NameError sau 5 phút xuất. Test này chạy đúng cách người dùng chạy."""
    import os
    import subprocess

    projects = tmp_path / "projects"
    _dung_phien(projects)
    out = tmp_path / "ra-cli"
    env = dict(os.environ, XUAT_PROMPT_LOG_GOC=str(projects), PYTHONIOENCODING="utf-8")
    kq = subprocess.run(
        [sys.executable, str(_SCRIPT), "--ra", str(out)],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=300,
    )
    assert kq.returncode == 0, kq.stderr[-2000:]
    assert (out / "README.md").exists()
    assert (out / "MANIFEST-SHA256.txt").exists()
    so = json.loads((out / "SO-DEM.json").read_text("utf-8"))
    assert so["tong"]["cau_lenh_nguoi"] == 2


def test_bo_loc_day_du_cho_du_lieu_ngoai_chi_dinh_danh_cho_van_ban_ai(goc, tmp_path):
    """Xuất thật 25/09 lần đầu: bộ lọc sản phẩm (viết cho bình luận chat) che 17.881 cụm
    "địa chỉ" trong văn bản AI và mã — "liên quan", "đường dẫn", "tinh chỉnh" thành
    [ĐỊA CHỈ] — làm hỏng Prompt Log. Dữ liệu cá nhân của người ngoài chỉ đi vào log qua
    kết quả công cụ và câu người gõ: ở đó dùng ĐỦ 7 loại của bộ lọc sản phẩm. Văn bản AI,
    đầu vào công cụ, lời giao việc: chỉ các loại định danh trực tiếp (SĐT, email, mạng xã
    hội, số tài khoản) + danh sách chặn + khoá."""
    thu_muc = goc / "d--AISC2026"
    rec = [
        _nguoi("chị Hương ơi xem giúp", 40),
        _ai(41, {"type": "text", "text": "Phần này liên quan tới đường dẫn tệp và tinh chỉnh."}),
        _ai(42, {"type": "tool_use", "id": "t9", "name": "Bash", "input": {"command": "ls"}}),
        _ket_qua("t9", "binh luan: ship về 12 đường Lê Lợi nha, gọi 0901234567", 43),
    ]
    _ghi(thu_muc / "22222222-0000-0000-0000-000000000000.jsonl", rec)
    out = tmp_path / "ra-loai"
    assert xpl.main(["--ra", str(out)]) == 0
    md = next((out / "phien").glob("*22222222*.md")).read_text("utf-8")
    assert "liên quan tới đường dẫn tệp và tinh chỉnh" in md
    assert "Hương" not in md
    assert "Lê Lợi" not in md
    assert "0901234567" not in md
    assert sum(xpl.quet_thu_muc(out).values()) == 0


def test_danh_sach_chan_che_ca_phan_ten_email_va_tien_to_mssv(monkeypatch):
    """Xuất thật 25/09: lệnh grep của Claude đi tìm dữ liệu đội còn nguyên phần tên của
    email thành viên và tiền tố MSSV (dạng ``grep -nE "<tên email>|<tiền tố MSSV>(…)"``),
    vì danh sách chặn chỉ chứa giá trị ĐẦY ĐỦ. KHÔNG ghi giá trị thật vào tệp này (kho công
    khai) — chỉ dùng giá trị giả như bên dưới."""
    ds = xpl._mo_rong_danh_sach_chan(["nguyenvana2006@gmail.com", "999X0123", "0912345678"])
    for tu in ("nguyenvana2006@gmail.com", "nguyenvana2006", "nguyenvana", "999X0123", "999X0"):
        assert tu in ds, tu
    monkeypatch.setattr(xpl, "DENYLIST", ds)
    ra = xpl.lam_sach('grep -nE "nguyenvana|999X0(123|456)" f', __import__("collections").Counter())
    assert "nguyenvana" not in ra
    assert "999X0" not in ra


# --------------------------------------------------------------------------
# 6. Phản biện độc lập 25/09/2026 (Pha 2): ba lỗi trên bản xuất thật
# --------------------------------------------------------------------------
def test_manifest_ghi_xuong_dong_lf_de_sha256sum_c_doc_duoc(ra):
    """Bản xuất thật: ``sha256sum -c MANIFEST-SHA256.txt`` báo 608/608 tệp "could not be
    read" (EXIT 1) vì ``write_text`` trên Windows ghi CRLF, tên tệp dính ``\\r``."""
    for ten in ("MANIFEST-SHA256.txt", "MANIFEST-NGUON-SHA256.txt"):
        assert b"\r" not in (ra / ten).read_bytes(), ten


def test_readme_ghi_ket_qua_quet_lai_that_khong_phai_chua_chay(ra):
    """Bản xuất thật: README ghi "Quét lại bản xuất …: **chưa chạy** chỗ còn khớp" vì README
    được ghi TRƯỚC khi quét lại."""
    readme = (ra / "README.md").read_text("utf-8")
    assert "chưa chạy" not in readme
    assert "**0** chỗ còn khớp" in readme
    assert "bản ghi đính kèm" in readme  # phần không xuất phải được nói ra
    # kiểm chéo promptId phải được TÍNH, không viết cứng "cho cùng kết quả"
    assert "2 mã riêng biệt so với 2 câu — khớp." in readme
    # README đổi sau khi quét thì manifest vẫn phải khớp
    for d in (ra / "MANIFEST-SHA256.txt").read_text("utf-8").strip().splitlines():
        h, ten = d.split(" *", 1)
        assert hashlib.sha256((ra / ten).read_bytes()).hexdigest() == h, ten


def test_quet_giu_muc_day_du_khi_ket_qua_cong_cu_co_tieu_de_markdown(tmp_path):
    """Kết quả công cụ (mức ĐẦY ĐỦ) chứa dòng ``### …`` của tệp Markdown được đọc: bộ quét
    cũ coi đó là tiêu đề vai, hạ xuống mức ĐỊNH DANH cho phần còn lại của khối (bản xuất
    thật: 1.573 dòng như vậy, 6.634 dòng bị quét sai mức)."""
    tep = tmp_path / "phien" / "a.md"
    tep.parent.mkdir(parents=True)
    tep.write_text(
        "\n".join(
            [
                f"### 2026-09-01 08:00:00 — {xpl.VAI['KQ']}",
                "",
                "```text",
                "### Mục trong tệp Markdown mà công cụ đọc ra",
                "binh luan: ship về 12 đường Lê Lợi nha",
                "```",
                "",
                f"### 2026-09-01 08:01:00 — {xpl.VAI['AI']}",
                "",
                "Phần này liên quan tới đường dẫn tệp và tinh chỉnh.",
                "",
            ]
        ),
        "utf-8",
    )
    kq = xpl.quet_thu_muc(tmp_path)
    assert sum(kq.values()) >= 1, "dòng địa chỉ trong kết quả công cụ bị quét ở mức ĐỊNH DANH"
    # và tiêu đề vai thật vẫn chuyển mức: văn xuôi AI sau đó quét ở mức ĐỊNH DANH (không
    # cộng thêm "địa chỉ" cho "liên quan", "đường dẫn")
    mong_doi = xpl.dem_con_sot("### Mục trong tệp Markdown mà công cụ đọc ra", xpl.DAY_DU)
    mong_doi += xpl.dem_con_sot("binh luan: ship về 12 đường Lê Lợi nha", xpl.DAY_DU)
    assert kq == mong_doi, (kq, mong_doi)


def test_loi_xep_hang_khong_mang_dau_may_duoc_dem_de_canh_bao():
    """Bản ghi ``attachment/queued_command`` (lời xếp hàng khi Claude đang chạy) không vào
    Prompt Log. Nhật ký tới 25/09 chỉ có báo cáo trả về của tác tử con ở dạng này; lời nào
    không mang dấu của máy phải được đếm để README cảnh báo, không được lặng lẽ bỏ."""
    nk = xpl.NhatKy(Path("x.jsonl"), "x.jsonl", PHIEN, False)
    for prompt in ('<agent-message from="a1">[Subagent hand-back] …', "anh xem giúp phần này"):
        xpl._nap_ban_ghi(
            nk,
            {
                "type": "attachment",
                "timestamp": _ts(1),
                "attachment": {"type": "queued_command", "commandMode": "prompt", "prompt": prompt},
            },
        )
    assert nk.dem["dinh_kem_bo_qua"] == 2
    assert nk.dem["dinh_kem_xep_hang_khong_ro_nguon"] == 1


# --------------------------------------------------------------------------
# 6. Tên tài khoản dính liền + đối chiếu ĐỘC LẬP (25/09/2026)
# --------------------------------------------------------------------------
# Sự cố: bản xuất "đã làm sạch" còn 2 tên tài khoản thật dạng ``chữ@tên`` trong khi
# ``--quet`` báo 0 — vì ``--quet`` chạy lại đúng bộ lọc đã lọt. Mọi tên dưới đây là BỊA.
TEN_BIA = ("minhthu8106", "TrầnThịMai-k3x", "kimchi_88", "lan.anh99")


def test_lam_sach_bat_ten_tai_khoan_dinh_lien_o_ca_hai_muc():
    for muc in (xpl.DAY_DU, xpl.DINH_DANH):
        for tho, ten in (
            ("cảm ơn bạn@minhthu8106 nhiều", "minhthu8106"),
            ("hay quá@lan.anh99 ơi", "lan.anh99"),
            ("đẹp@@kimchi_88", "kimchi_88"),
        ):
            assert sum(xpl.dem_con_sot(tho, muc).values()) >= 1, "--quet phải thấy dạng này"
            sach = xpl.lam_sach(tho, Counter(), muc)
            assert ten not in sach, sach
            assert "[MXH]" in sach, sach
    # giá dùng "@" vẫn giữ nguyên
    assert xpl.lam_sach("3 cái@50k, 2@99k", Counter(), xpl.DAY_DU) == "3 cái@50k, 2@99k"


def _nguon_goc(thu_muc: Path) -> Path:
    """Dữ liệu gốc tổng hợp: JSONL (một dòng ghi ``ensure_ascii`` để có ``\\uXXXX``) + TSV."""
    thu_muc.mkdir(parents=True, exist_ok=True)
    dong = [
        json.dumps({"text": "cảm ơn bạn@minhthu8106 nhiều"}, ensure_ascii=False),
        json.dumps({"text": "@TrầnThịMai-k3x chốt 2 cái"}, ensure_ascii=True),
        json.dumps({"text": "đẹp@@kimchi_88", "khac": ["3 cái@50k", "size@2XL"]}),
        json.dumps({"text": "mail hoa.nguyen89@gmail.com, npm i next@14.2.3, hẹn@7h30"}),
    ]
    (thu_muc / "binh_luan.jsonl").write_text("\n".join(dong) + "\n", "utf-8")
    (thu_muc / "to_label.txt").write_text("u1\tchào ạ@lan.anh99 nha\n", "utf-8")
    return thu_muc


def test_lap_tap_bam_chi_ghi_bam_cua_ten_tai_khoan(tmp_path, capsys):
    tep = tmp_path / "ngoai-kho" / "dinh-danh.sha256"
    tep.parent.mkdir()
    goc = _nguon_goc(tmp_path / "goc")
    assert xpl.main(["--lap-doi-chieu", str(tep), "--nguon", str(goc)]) == 0
    noi_dung = tep.read_text("utf-8")
    assert xpl.doc_tap_bam(tep) == {xpl.bam_dinh_danh(t) for t in TEN_BIA}
    for tho in (*TEN_BIA, "minhthu", "kimchi", "Trần"):
        assert tho.casefold() not in noi_dung.casefold(), "tệp băm không được chứa chuỗi gốc"
    for khong in ("50k", "2XL", "gmail.com", "14.2.3", "7h30"):
        assert xpl.bam_dinh_danh(khong) not in noi_dung
    out = capsys.readouterr().out
    assert "4 băm định danh" in out
    assert not any(t.casefold() in out.casefold() for t in TEN_BIA)


def test_lap_tap_bam_loai_tu_thong_dung_co_trong_kho_va_ghi_ro(tmp_path, capsys):
    """Lần lập thật: 4/37 "tên" là từ thông dụng có trong hàng chục tệp của kho mã, làm
    đối chiếu báo 8.283 chỗ giả. ``--tru-tu-trong`` loại chúng NHƯNG ghi băm + số tệp."""
    goc = tmp_path / "goc"
    goc.mkdir()
    (goc / "bl.jsonl").write_text(
        json.dumps({"text": "cảm ơn @chaocanha và bạn@minhthu8106"}) + "\n", "utf-8"
    )
    kho = tmp_path / "kho"
    (kho / "docs").mkdir(parents=True)
    (kho / "docs" / "a.md").write_text("mở đầu: chaocanha mọi người\n", "utf-8")
    (kho / "b.py").write_text("X = 'chaocanha'\n", "utf-8")
    tep = tmp_path / "da-biet.sha256"
    lenh = ["--lap-doi-chieu", str(tep), "--nguon", str(goc), "--tru-tu-trong", str(kho)]
    assert xpl.main(lenh) == 0
    assert xpl.doc_tap_bam(tep) == {xpl.bam_dinh_danh("minhthu8106")}
    noi_dung = tep.read_text("utf-8")
    assert f"{xpl.bam_dinh_danh('chaocanha')[:12]}×2" in noi_dung
    assert "chaocanha" not in noi_dung
    assert "chaocanha" not in capsys.readouterr().out


def test_doc_tap_bam_tu_choi_tep_hong_hoac_rong(tmp_path):
    hong = tmp_path / "hong.sha256"
    hong.write_text("# chú thích\nkhong-phai-bam\n", "utf-8")
    with pytest.raises(ValueError, match="64 ký tự hex"):
        xpl.doc_tap_bam(hong)
    rong = tmp_path / "rong.sha256"
    rong.write_text("# chỉ có chú thích\n", "utf-8")
    with pytest.raises(ValueError, match="rỗng"):
        xpl.doc_tap_bam(rong)


def _tep_bam(tmp_path: Path, *ten: str) -> Path:
    tep = tmp_path / "da-biet.sha256"
    tep.write_text("# tổng hợp\n" + "\n".join(xpl.bam_dinh_danh(t) for t in ten) + "\n", "utf-8")
    return tep


def test_doi_chieu_bat_cho_ma_quet_mu_va_chi_in_bam(ra, tmp_path, capsys):
    """Tên thật đứng TRẦN (không ``@``) hay nằm trong một chuỗi chấm-gạch: bộ lọc không bắt
    (``--quet`` = 0) nhưng đối chiếu độc lập bắt, và chỉ in băm."""
    tep = _tep_bam(tmp_path, *TEN_BIA, "Cường-123")
    capsys.readouterr()
    # bản xuất sạch (handle tổng hợp "@Cường-123" đã thành [MXH]) → 0
    assert xpl.main(["--quet", str(ra), "--doi-chieu", str(tep)]) == 0
    assert "0 chỗ trùng" in capsys.readouterr().out
    lot = ra / "phien" / "lot.md"
    lot.write_text("khách minhthu8106 hỏi giá\nxem lan.anh99.vlog và TRẦNTHỊMAI-K3X\n", "utf-8")
    assert sum(xpl.quet_thu_muc(ra).values()) == 0, "tiền đề: bộ lọc không thấy dạng trần"
    trung = xpl.doi_chieu_thu_muc(ra, xpl.doc_tap_bam(tep))
    assert {(t, d) for t, d, _ in trung} == {("phien/lot.md", 1), ("phien/lot.md", 2)}
    assert len(trung) == 3
    assert xpl.main(["--quet", str(ra), "--doi-chieu", str(tep)]) == 1
    out = capsys.readouterr().out
    assert "3 chỗ trùng" in out
    assert "phien/lot.md:1" in out
    assert xpl.bam_dinh_danh("minhthu8106")[:12] in out
    assert not any(t.casefold() in out.casefold() for t in TEN_BIA)


def test_ra_kem_doi_chieu_ghi_so_dem_khong_ghi_vi_tri(goc, tmp_path):
    tep = _tep_bam(tmp_path, *TEN_BIA, "Cường-123")
    out = tmp_path / "ra-doi-chieu"
    assert xpl.main(["--ra", str(out), "--doi-chieu", str(tep)]) == 0
    so = json.loads((out / "SO-DEM.json").read_text("utf-8"))
    assert so["doi_chieu_doc_lap"] == {"so_bam_da_biet": 5, "trung": 0}
    assert "Đối chiếu độc lập" in (out / "README.md").read_text("utf-8")
    assert "**0** chỗ trùng" in (out / "BAO-CAO-LAM-SACH.md").read_text("utf-8")


def test_ra_kem_doi_chieu_co_trung_thi_ma_1_va_vi_tri_chi_in_man_hinh(goc, tmp_path, capsys):
    """Ca CÓ trùng (ca 0 trùng ở trên không kiểm được gì về vị trí): mã thoát 1, tệp tải lên
    chỉ có số đếm; ``tệp:dòng`` và băm chỉ in ra màn hình."""
    tep = _tep_bam(tmp_path, "DUOI-TEP-XYZ")  # chuỗi có thật trong đầu vào công cụ tổng hợp
    bam12 = xpl.bam_dinh_danh("DUOI-TEP-XYZ")[:12]
    out = tmp_path / "ra-co-trung"
    capsys.readouterr()
    assert xpl.main(["--ra", str(out), "--doi-chieu", str(tep)]) == 1
    so = json.loads((out / "SO-DEM.json").read_text("utf-8"))
    n = so["doi_chieu_doc_lap"]["trung"]
    assert n >= 1
    assert f"**{n}** chỗ trùng" in (out / "BAO-CAO-LAM-SACH.md").read_text("utf-8")
    for f in out.rglob("*"):
        if f.is_file():
            assert bam12 not in f.read_text("utf-8", errors="replace"), f"lộ băm ở {f.name}"
    man_hinh = capsys.readouterr().out
    assert f"{n} chỗ trùng" in man_hinh
    assert bam12 in man_hinh


def test_doi_chieu_can_quet_hoac_ra(tmp_path):
    tep = _tep_bam(tmp_path, "minhthu8106")
    with pytest.raises(SystemExit):
        xpl.main(["--doi-chieu", str(tep), "--kiem-tra"])
