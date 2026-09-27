"""Phiên CHẠY THỬ và phiên ĐÃ HUỶ không được hiện như dữ liệu thí nghiệm thật.

Hai lỗ còn mở sau phản biện làn web 25/09/2026, kiểm ở CẢ HAI phía hợp đồng:

1. ``/ket-qua?phien=<id của phiên CHẠY THỬ>`` có KTC loại 0 vẫn đóng con dấu
   "TÁC ĐỘNG THẬT" — vì ``/sessions/{id}/bao-cao`` không mang cờ ``dry_run`` (chỉ
   có ``is_demo``, mà phiên chạy thử là phiên thật: ``is_demo=false``). Phiên chạy
   thử bị loại khỏi kết quả gộp (PREREGISTRATION §8.2), nên con số của nó không
   được mang chữ "THẬT". Sửa: máy chủ THÊM trường ``dry_run`` (không đổi trường
   nào khác); trang dùng nhãn trung thực "HIỆU ỨNG RÕ · CHẠY THỬ".

2. ``/health`` đếm phiên ĐÃ HUỶ vào ``mode_counts.real``; ModeChip trừ phiên chạy
   thử nhưng không trừ phiên huỷ, nên một bản nháp đã huỷ đủ làm chip in
   "KHO: DỮ LIỆU THẬT" (runtime.md 3.2: real=3 = 2 chạy thử + 1 huỷ, 0 phiên thí
   nghiệm thật). Sửa: THÊM khoá ``mode_counts.da_huy`` (nằm TRONG ``real`` như
   ``dry_run``, rời với ``dry_run``); chip trừ cả hai, chịu được máy chủ cũ.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from livelift.api.main import create_app
from livelift.api.store import InMemoryStore

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "web" / "src"
KET_QUA = SRC / "app" / "ket-qua" / "page.tsx"
MODECHIP = SRC / "components" / "ModeChip.tsx"
TYPES = SRC / "lib" / "types.ts"

CON_DAU_THAT = "TÁC ĐỘNG THẬT · KTC 95% không chứa 0"


@pytest.fixture
def client():
    with TestClient(create_app(store=InMemoryStore())) as c:
        yield c


def _tao(client, **kw) -> str:
    body = {"platform": "youtube", "mode": "auto", "planned_duration_min": 30, **kw}
    r = client.post("/sessions", json=body)
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def _huy(client, sid: str) -> None:
    assert client.post(f"/sessions/{sid}/cancel").status_code == 200


# ---------------------------------------------------------------------------
# Phía máy chủ
# ---------------------------------------------------------------------------

#: Trường của BaoCaoOut trước 25/09 — hợp đồng "chỉ THÊM": không trường nào mất.
TRUONG_BAO_CAO_CU = {
    "session_id",
    "tieu_de",
    "platform",
    "loai_phien",
    "nhan",
    "is_demo",
    "binh_luan_tong_hop",
    "tong_quan",
    "tin_hieu",
    "nang_luc",
    "khoanh_khac",
    "khoanh_khac_ghi_chu",
    "phan_bo_y_dinh",
    "pii_da_che",
    "ket_qua_thi_nghiem",
    "tom_tat_3_cau",
    "goi_y_chien_thuat",
}


def test_bao_cao_mang_co_dry_run_cua_phien(client):
    thu = client.get(f"/sessions/{_tao(client, dry_run=True)}/bao-cao")
    that = client.get(f"/sessions/{_tao(client)}/bao-cao")
    assert thu.status_code == 200
    assert that.status_code == 200
    assert thu.json()["dry_run"] is True, "báo cáo phiên CHẠY THỬ phải nói nó là chạy thử"
    assert that.json()["dry_run"] is False
    assert thu.json()["is_demo"] is False, "chạy thử là phiên thật, không phải dữ liệu mẫu"


def test_bao_cao_chi_them_truong_khong_bot(client):
    body = client.get(f"/sessions/{_tao(client, dry_run=True)}/bao-cao").json()
    assert set(body) >= TRUONG_BAO_CAO_CU, sorted(TRUONG_BAO_CAO_CU - set(body))
    assert set(body) - TRUONG_BAO_CAO_CU == {"dry_run"}


def test_bao_cao_phien_demo_khong_phai_chay_thu(client):
    ids = client.post("/demo/seed", json={"n_sessions": 1, "duration_min": 40}).json()
    body = client.get(f"/sessions/{ids['session_ids'][0]}/bao-cao").json()
    assert body["is_demo"] is True
    assert body["dry_run"] is False


def test_health_dem_phien_da_huy_rieng_ben_trong_real(client):
    """Đúng tình huống runtime.md 3.2: tập dượt hai lần, huỷ một nháp."""
    _tao(client, dry_run=True)
    _tao(client, dry_run=True)
    _huy(client, _tao(client))

    body = client.get("/health").json()
    mc = body["mode_counts"]
    assert mc == {"demo": 0, "real": 3, "dry_run": 2, "da_huy": 1}
    assert mc["real"] - mc["dry_run"] - mc["da_huy"] == 0, "0 phiên thí nghiệm thật"
    assert "đã huỷ" in body["mode_note"], "câu giải thích phải nói có phiên đã huỷ"


def test_health_phien_chay_thu_da_huy_chi_dem_o_dry_run(client):
    """Ba nhóm trong ``real`` RỜI nhau — nếu không, chip trừ một phiên hai lần."""
    _huy(client, _tao(client, dry_run=True))
    _tao(client)
    mc = client.get("/health").json()["mode_counts"]
    assert mc == {"demo": 0, "real": 2, "dry_run": 1, "da_huy": 0}
    assert mc["dry_run"] + mc["da_huy"] <= mc["real"]


def test_health_phien_da_ket_thuc_khong_phai_da_huy(client):
    """Chỉ trạng thái ``cancelled`` là huỷ; phiên thật còn lại vẫn là THẬT."""
    _tao(client)
    _huy(client, _tao(client))
    mc = client.get("/health").json()["mode_counts"]
    assert mc["real"] - mc["dry_run"] - mc["da_huy"] == 1


# ---------------------------------------------------------------------------
# Phía web — chạy THẬT hàm thuần bằng node
# ---------------------------------------------------------------------------


def _tach(src: str, ten: str) -> str:
    lines = src.replace("\r\n", "\n").split("\n")
    head = re.compile(rf"^(?:export )?(?:function|const) {re.escape(ten)}\b")
    for i, line in enumerate(lines):
        if not head.match(line):
            continue
        la_const = line.startswith(("const ", "export const "))
        if la_const and line.rstrip().endswith(";"):
            return line
        for j in range(i + 1, len(lines)):
            cuoi = lines[j].rstrip()
            if la_const and cuoi.endswith(";"):
                return "\n".join(lines[i : j + 1])
            if not la_const and cuoi == "}":
                return "\n".join(lines[i : j + 1])
        break
    raise AssertionError(f"không tách được khai báo {ten!r}")


def _node(tmp_path: Path, khai_bao: list[tuple[Path, str]], bieu_thuc: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("không có node — bỏ qua phần chạy thử hàm thuần")
    src = {p: p.read_text(encoding="utf-8") for p, _ in khai_bao}
    mo_dun = "\n\n".join(_tach(src[p], ten) for p, ten in khai_bao)
    tep = tmp_path / "thuan.mts"
    tep.write_text(mo_dun + f"\nconsole.log(JSON.stringify({bieu_thuc}));\n", encoding="utf-8")
    out = subprocess.run(
        [node, "--experimental-strip-types", "--no-warnings", str(tep)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    if out.returncode != 0 and "bad option" in out.stderr:
        pytest.skip("node quá cũ, chưa bỏ được chú thích kiểu")
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def _render(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)
    return re.sub(r"(?m)(?<![:\w])//.*$", " ", src)


def test_con_dau_phien_chay_thu_khong_goi_la_tac_dong_that(tmp_path):
    ra = _node(
        tmp_path,
        [(KET_QUA, "chuConDau")],
        "[chuConDau({isDemo: false, isDryRun: false}),"
        " chuConDau({isDemo: false, isDryRun: true}),"
        " chuConDau({isDemo: true, isDryRun: false}),"
        " chuConDau({isDemo: true, isDryRun: true})]",
    )
    that, chay_thu, demo, demo_chay_thu = ra
    assert that == CON_DAU_THAT, "phiên thật đủ điều kiện vẫn đóng đúng con dấu cũ"
    for nhan in (chay_thu, demo, demo_chay_thu):
        assert "THẬT" not in nhan, nhan
        assert "HIỆU ỨNG RÕ" in nhan, nhan
        assert "KTC 95% không chứa 0" in nhan, nhan
    assert "CHẠY THỬ" in chay_thu, chay_thu


def test_verdict_mot_phien_mang_co_chay_thu(tmp_path):
    kq = {
        "estimable": True,
        "estimate": 0.4,
        "ci_low": 0.1,
        "ci_high": 0.7,
        "p_value": 0.01,
        "n_draws": 999,
        "n_blocks": 6,
        "n_on": 3,
        "n_off": 3,
        "khoa": False,
        "ly_do_khoa": None,
        "message": None,
    }
    gop = {**kq, "env": "real", "n_sessions": 2}
    for k in ("khoa", "ly_do_khoa"):
        gop.pop(k)
    src = KET_QUA.read_text(encoding="utf-8")
    ten = [*re.findall(r"(?m)^const (KTC_\w+)\b", src)]
    ten += ["verdictState", "verdictFromSummary", "verdictFromKetQua"]
    ra = _node(
        tmp_path,
        [(KET_QUA, t) for t in ten],
        f"[verdictFromKetQua({json.dumps(kq)}, false, null, true),"
        f" verdictFromKetQua({json.dumps(kq)}, false, null),"
        f" verdictFromSummary({json.dumps(gop)})]",
    )
    assert [v["state"] for v in ra] == ["duong", "duong", "duong"]
    assert ra[0]["isDryRun"] is True
    assert ra[1]["isDryRun"] is False, "gọi kiểu cũ (3 đối số) thì mặc định không phải chạy thử"
    assert ra[2]["isDryRun"] is False, "bản gộp đã loại phiên chạy thử phía server"


def test_trang_ket_qua_truyen_co_dry_run_tu_bao_cao_va_chiu_may_chu_cu():
    src = _render(KET_QUA.read_text(encoding="utf-8"))
    assert re.search(
        r"verdictFromKetQua\(\s*baoCao\.ket_qua_thi_nghiem,\s*baoCao\.is_demo,\s*"
        r"baoCao\.tong_quan,\s*baoCao\.dry_run === true,?\s*\)",
        src,
    ), "trang phải truyền baoCao.dry_run (=== true: máy chủ cũ không gửi ⇒ không phải chạy thử)"
    body = src.split("function VerdictCoTacDong")[1].split("\nfunction ")[0]
    assert "chuConDau(v)" in body, "con dấu phải lấy chữ từ chuConDau"
    assert re.search(r"v\.isDryRun\s*\?\s*<Badge", body), "phiên chạy thử phải đeo huy hiệu"


def test_types_khai_truong_moi_la_tuy_chon():
    types = TYPES.read_text(encoding="utf-8")
    bao_cao = types.split("export interface BaoCao {")[1].split("\n}")[0]
    assert re.search(r"^\s*dry_run\?: boolean;", bao_cao, re.M), "BaoCao phải khai dry_run?"
    health = types.split("export interface HealthInfo")[1].split("\n}")[0]
    assert "da_huy?: number" in health, "HealthInfo.mode_counts phải khai da_huy?"


def test_chip_kho_tru_ca_phien_da_huy(tmp_path):
    ca = [
        # máy chủ mới — đúng tình huống runtime.md 3.2
        ("real", {"demo": 0, "real": 3, "dry_run": 2, "da_huy": 1}, "chay-thu"),
        ("real", {"demo": 0, "real": 1, "dry_run": 0, "da_huy": 1}, "trong"),
        ("mixed", {"demo": 2, "real": 1, "dry_run": 0, "da_huy": 1}, "mau"),
        ("mixed", {"demo": 2, "real": 2, "dry_run": 1, "da_huy": 1}, "mau-chay-thu"),
        ("real", {"demo": 0, "real": 2, "dry_run": 0, "da_huy": 1}, "that"),
        ("mixed", {"demo": 1, "real": 3, "dry_run": 1, "da_huy": 1}, "ca-hai"),
        # máy chủ có da_huy mà thiếu dry_run (không có thật, nhưng phải chịu được)
        ("real", {"demo": 0, "real": 1, "da_huy": 1}, "trong"),
        # máy chủ cũ — không có da_huy: luật trước giữ nguyên
        ("real", {"demo": 0, "real": 2, "dry_run": 1}, "that"),
        ("real", {"demo": 0, "real": 2, "dry_run": 2}, "chay-thu"),
        ("real", {"demo": 0, "real": 2}, "that"),
        ("real", {"demo": 0, "real": 0}, "trong"),
        ("mixed", {"demo": 1, "real": 1}, "ca-hai"),
        # da_huy hỏng kiểu thì bỏ qua, không đoán
        ("real", {"demo": 0, "real": 2, "dry_run": 1, "da_huy": "1"}, "that"),
    ]
    ra = _node(
        tmp_path,
        [(MODECHIP, "khoTu")],
        "[" + ",".join(f"khoTu({json.dumps(m)}, {json.dumps(c)})" for m, c, _ in ca) + "]",
    )
    assert ra == [k for _, _, k in ca]


def test_tooltip_chip_noi_ro_phien_da_huy(tmp_path):
    ra = _node(
        tmp_path,
        [(MODECHIP, "ghiChuKho")],
        '[ghiChuKho("Kho chứa 1 phiên dữ liệu thật.", {"demo": 0, "real": 1, "dry_run": 0,'
        ' "da_huy": 1}),'
        ' ghiChuKho("Kho — trong đó 1 phiên đã huỷ (chưa lên sóng).", {"demo": 0, "real": 1,'
        ' "da_huy": 1}),'
        ' ghiChuKho("Kho chứa 2 phiên.", {"demo": 0, "real": 2, "dry_run": 2}),'
        ' ghiChuKho("Kho chứa 2 phiên.", {"demo": 0, "real": 2})]',
    )
    assert "ĐÃ HUỶ" in ra[0]
    assert "1 phiên" in ra[0]
    assert ra[1].count("huỷ") == 1, "câu máy chủ đã nói thì không nói lại"
    assert "CHẠY THỬ" in ra[2]
    assert ra[3] == "Kho chứa 2 phiên."
