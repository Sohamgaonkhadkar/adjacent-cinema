# Adjacent. Every target works without a Qloo API key except probe-live / probe-live-unverified,
# which require QLOO_API_KEY and fail with exit 2 if it is missing (they never mock).

PY ?= python3
BACKEND := backend
PROBE := scripts/qloo_probe.py

.PHONY: help setup test lint fmt ci probe probe-live probe-unverified run health params \
        mock-run mock-run-insufficient milestone-1 milestone-1-sparse \
        probe-live-unverified demo-live clean

help:
	@echo "Adjacent — available targets:"
	@echo "  make setup                install dependencies (see pyproject.toml)"
	@echo "  make test                 run the test suite (no API key needed)"
	@echo "  make lint                 ruff check"
	@echo "  make fmt                  ruff format + ruff check --fix"
	@echo "  make ci                   exactly what CI runs"
	@echo "  make probe                Qloo probe, DRY-RUN (fixture-backed, no key needed)"
	@echo "  make probe-live           REAL Qloo probe. Exits 2 if QLOO_API_KEY is missing"
	@echo "  make probe-unverified     UNVERIFIED-parameter probes, DRY-RUN (always mock)"
	@echo "  make probe-live-unverified  REAL Qloo + the UNVERIFIED-parameter probes"
	@echo "  make run                  start the FastAPI dev server on :8000"
	@echo "  make health               curl /health"
	@echo "  make params               curl /debug/params (the allowlist)"
	@echo "  make mock-run             end-to-end fixture run (strong scenario)"
	@echo "  make mock-run-insufficient end-to-end fixture run (insufficient evidence)"
	@echo "  make milestone-1          CLI fixture spine, strong scenario (no API key needed)"
	@echo "  make milestone-1-sparse   CLI fixture spine, insufficiency scenario (no API key needed)"

setup:
	$(PY) -m pip install -e ".[dev]"

test:
	$(PY) -m pytest

lint:
	$(PY) -m ruff check .

fmt:
	$(PY) -m ruff format .
	$(PY) -m ruff check --fix .

ci: lint test

probe:
	$(PY) $(PROBE)

probe-live:
	$(PY) $(PROBE) --live

probe-unverified:
	@echo "NOTE: --unverified without --live is a DRY-RUN (mock) probe, even with a key set."
	$(PY) $(PROBE) --unverified

probe-live-unverified:
	$(PY) $(PROBE) --live --unverified

run:
	cd $(BACKEND) && $(PY) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

health:
	curl -s localhost:8000/health | $(PY) -m json.tool

params:
	curl -s localhost:8000/debug/params | $(PY) -m json.tool

mock-run:
	curl -s "localhost:8000/debug/mock/run?fixture=portland_strong" | $(PY) -m json.tool

mock-run-insufficient:
	curl -s "localhost:8000/debug/mock/run?fixture=insufficient_evidence" | $(PY) -m json.tool

milestone-1:
	cd $(BACKEND) && $(PY) -m app.cli run --fixture fixtures/portland_strong.json --mock

milestone-1-sparse:
	cd $(BACKEND) && $(PY) -m app.cli run --fixture fixtures/insufficient_evidence.json --mock

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	find . -type d -name .pytest_cache -prune -exec rm -rf {} +
	find . -type d -name .ruff_cache -prune -exec rm -rf {} +

demo-live:
	cd $(BACKEND) && $(PY) -m app.cli demo-live
