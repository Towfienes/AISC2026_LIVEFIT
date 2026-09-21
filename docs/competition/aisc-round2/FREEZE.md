# AISC Round 2 — Claim & demo freeze

*Freeze draft ngày 21/09/2026. Chỉ claim có evidence dưới đây được dùng.*

## Claim freeze

| Claim | Trạng thái | Evidence |
|---|---|---|
| 1.811 fast · 17 slow/Monte-Carlo · 10 browser collected | VERIFIED; current public surfaces đồng bộ 1.811 ngày 21/09/2026; đây không phải claim 1.811 PASS | pytest collect + `dong_bo_so_test.py --xem-truoc`; 5 lỗi NLP có sẵn ghi riêng ở quality gates |
| 60 incidents có root cause | VERIFIED | đếm 60 data rows trong `docs/incident-log.md` |
| Python code coverage 88% | OBSERVED, GATE FAIL | pytest-cov chạy hết nhưng fast suite có NLP failures |
| A/A 3,50% · statistical CI coverage 96,50% | VERIFIED | calibration `--kiem` khớp `so-hieu-chuan.json` |
| Known-effect bias −0,84% · statistical CI coverage 92,50% | VERIFIED | cùng calibration |
| 19.126 comments · 16 replay sessions | ARCHIVED EVIDENCE; RERUN BLOCKED | benchmark 10/09; API sạch `:8010` connection refused |
| 0 real randomized sessions | DISCLOSED | không có evidence pilot thật mới; runtime external store chưa audit |

## Quality gates trên revision cuối

| Gate | Trạng thái hiện tại |
|---|---|
| Targeted Round 2/web regression tests | PASS — 75 tests |
| Fast pytest + Python code coverage | FAIL — 5 NLP artifact/dependency failures ngoài P0 còn lại; regression `console.configure()` của checker đã sửa và targeted test PASS; 88% code coverage observed |
| Slow pytest | PASS — 23 passed, 4 skipped |
| Calibration `--kiem` | PASS |
| Browser tests | PASS — 10 passed |
| Ruff repository + targeted new script | PASS |
| Next.js production build | PASS; npm audit báo 1 high + 1 critical dependency vulnerability, không auto-upgrade ngoài scope |
| Docker Compose config | NOT RUN — `docker: command not found` |
| PostgreSQL contract | NOT RUN — không có Postgres/DATABASE_URL; marker command deselect 13 tests |
| Round 2 live preflight | FAIL-CLOSED — API/web chưa chạy, 0 PASS · 2 FAIL |
| Manual rehearsal | HUMAN-DEPENDENT / NOT RUN |

## Những câu bị cấm

- “Đã có causal result từ phiên thật.”
- “Demo Vàng là dữ liệu thật.”
- “Autopilot đã ghim production trên mọi nền tảng.”
- “Snapshot memory tương đương Postgres durability.”
- “Tất cả test đang xanh” khi fast/browser/build chưa PASS.
- Dùng Python code coverage thay cho statistical CI coverage.

Không sửa statistical core, estimator, switchback hay preregistration để làm
đẹp gate. Nếu evidence thay đổi, cập nhật fact sheet trước rồi mới cập nhật
pitch/Q&A/freeze.
