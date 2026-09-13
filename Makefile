# LiveLift — developer entry points.
#
# Windows note: `make` is not present in a stock Windows shell. Either run the
# underlying commands directly (they are all plain pip/pytest/ruff/docker calls,
# copy them from this file), or run `make` from Git Bash / WSL where GNU make is
# available. CI runs the same commands (see .github/workflows/ci.yml).
#
# Variables (override on the command line):
#   make qc SESSION=<session_id>
#   make schedule SESSION=<session_id> DURATION=90 BLOCK=5
#   make simulate SESSIONS=30 EFFECT=0.15

SESSION  ?=
DURATION ?= 90
BLOCK    ?= 5
SESSIONS ?= 30
EFFECT   ?= 0.15

.PHONY: install test test-fast test-slow lint fmt up down logs qc simulate sim-grid sim-icc schedule isolation chay-local gate-css

install:            ## editable install with dev + server + ml extras
	pip install -e ".[dev,server,ml]"

test:               ## full test suite (fast + slow)
	pytest

test-fast:          ## fast suite — the per-PR CI gate
	pytest -m "not slow" --cov=src/livelift --cov-report=term

test-slow:          ## slow statistical validation (nightly CI gate)
	pytest -m slow

lint:               ## ruff lint + format check (CI gate, no changes)
	ruff check src tests
	ruff format --check src tests

fmt:                ## apply ruff autofixes + formatting
	ruff check --fix src tests
	ruff format src tests

up:                 ## start the full stack (db + redis + migrate + api + web + backup)
	docker compose up -d --build

down:               ## stop the stack (volumes are kept)
	docker compose down

logs:               ## follow logs of all services
	docker compose logs -f --tail=100

qc:                 ## post-session data quality checks: make qc SESSION=<session_id>
	livelift-qc --session-id "$(SESSION)"

simulate:           ## simulate a session series to validate estimators
	livelift-simulate --sessions $(SESSIONS) --effect $(EFFECT)

sim-grid:           ## SBC skeleton grid -> docs/benchmarks/sim-validation-report.md (~3 min)
	python -m livelift.sim.cli --grid --grid-reps 100 --effect 0.30 --seed 2026

sim-icc:            ## measured knob -> ICC map -> docs/benchmarks/sim-icc-map.md (~5 min)
	python analysis/calibration/bang_icc_mo_phong.py

schedule:           ## generate a block assignment schedule BEFORE the session
	livelift-schedule --duration $(DURATION) --block $(BLOCK) --washout 0 --jitter 30 \
		--out "schedule-$(SESSION).json"

isolation:          ## src/ <-> collectors/ import isolation gate (same as CI)
	python scripts/check_isolation.py

chay-local:         ## MỘT lệnh: dọn cổng + rác build, chọn kho, bật API + web, kiểm CSS
	python scripts/chay_local.py

gate-css:           ## cổng chống "trang vỡ vì thiếu CSS": next build thật rồi cân tệp CSS
	python scripts/gate_css_web.py
