# AISC Round 2 — Fact Sheet

*Cập nhật 21/09/2026 · nhánh `tien/aisc-round2` · baseline HEAD `08be6ae`.*

Hai khái niệm không được trộn:

- **Statistical CI coverage** đo tỷ lệ khoảng tin cậy chứa hiệu ứng thật trong
  calibration Monte-Carlo. Nguồn là calibration executable.
- **Python code coverage** đo dòng mã Python được test chạy qua. Nguồn là
  `pytest --cov`; nó không chứng minh statistical CI coverage.

## Metrics có bằng chứng

| Metric | Value | Nguồn | Lệnh tái lập | Ngày xác minh |
|---|---:|---|---|---|
| Fast tests collected | **1.811** | pytest collector; `scripts/dong_bo_so_test.py` (authoritative). README/homepage đã đồng bộ 1.811 ngày 21/09/2026; đây là số thu thập, không phải số PASS. 5 lỗi NLP có sẵn được ghi riêng bên dưới | `.venv/bin/python scripts/dong_bo_so_test.py --xem-truoc` | 21/09/2026 |
| Slow/Monte-Carlo gates collected | **17** | cùng pytest collector, loại browser | `.venv/bin/python -m pytest -m "slow and not browser" --collect-only -q` | 21/09/2026 |
| Browser tests collected | **10** | `tests/test_web_desk_trinh_duyet.py` | `.venv/bin/python -m pytest -m browser --collect-only -q` | 21/09/2026 |
| Incidents có root cause | **60** | từng data row trong `docs/incident-log.md` | `awk -F'|' 'BEGIN{n=0} /^\| [0-9][0-9]\/[0-9][0-9]\/[0-9][0-9][0-9][0-9] / {n++} END{print n}' docs/incident-log.md` | 21/09/2026 |
| Python code coverage | **88% observed; command FAIL** | pytest-cov trên fast suite; run có 5 NLP failures do artifact sklearn 1.9.0 nhưng project cài `<1.8`/1.7.2, cùng 2 assertion P0 đang được sửa lúc run và đã PASS khi rerun targeted | `.venv/bin/python -m pytest -m "not slow" --cov=src/livelift --cov-report=term-missing` | 21/09/2026 |
| A/A rejection rate | **3,50% (7/200)** | `docs/benchmarks/so-hieu-chuan.json`; calibration `--kiem` PASS | `.venv/bin/python scripts/do_lai_so_hieu_chuan.py --kiem` | 21/09/2026 |
| Statistical CI coverage — A/A | **96,50% (193/200)** | calibration, không phải pytest-cov | `.venv/bin/python scripts/do_lai_so_hieu_chuan.py --kiem` | 21/09/2026 |
| Known-effect recovery bias | **−0,84%** | calibration known effect 0,3; 40 replications | `.venv/bin/python scripts/do_lai_so_hieu_chuan.py --kiem` | 21/09/2026 |
| Statistical CI coverage — known effect | **92,50% (37/40)** | calibration known effect | `.venv/bin/python scripts/do_lai_so_hieu_chuan.py --kiem` | 21/09/2026 |
| Live-fire observational replay | **19.126 comments · 16 sessions** | `docs/benchmarks/live-fire-da-nguon.md`, đo 10/09; corpus/API sạch không có trong environment hiện tại để rerun | `.venv/bin/python scripts/live_fire_da_nguon.py --api <API-sạch> bang` | Provenance 10/09/2026; rerun BLOCKED 21/09/2026 (connection refused) |
| Real randomized sessions | **0** | trạng thái dự án đã công bố; runtime service hiện không chạy nên chưa thể audit external store | `python scripts/round2_demo_check.py --base http://localhost` và kiểm store real đã được đội bật | 21/09/2026: 0 được công bố; runtime NOT RUN |

## Diễn giải bắt buộc

- 19.126 bình luận là dữ liệu thật nhưng **quan sát hồi cứu**, không phải 19.126
  quan sát randomized và không chứng minh causal lift.
- Demo Vàng là mô phỏng seed cố định. Mọi con số demo phải mang nhãn
  `DEMO/MÔ PHỎNG`.
- Fast suite hiện chưa PASS vì mismatch artifact/dependency NLP ngoài P0 Round
  2. Không suy từ “1.811 tests collected” thành “1.811 tests xanh”.
- Calibration `--kiem` đã khớp đúng `so-hieu-chuan.json`; không có benchmark
  hay statistical methodology nào được sửa để đạt kết quả này.
