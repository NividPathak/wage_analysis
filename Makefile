# Causal extension pipeline. `make all` runs everything from a clean clone.
PYTHON ?= python3.11
VENV := .venv
PY := $(VENV)/bin/python

.PHONY: all setup data panel analysis report test lint

all: setup data panel analysis report test

$(PY):
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -r requirements-causal.txt

setup: $(PY)

data: setup
	$(PY) -m causal.audit
	$(PY) -m causal.download_minwage

panel: setup
	$(PY) -m causal.build_panel
	$(PY) -m causal.treatment

analysis: setup
	$(PY) -m causal.eda
	$(PY) -m causal.did
	$(PY) -m causal.synth
	$(PY) -m causal.power

report: setup
	$(PY) -m causal.report

test: setup
	$(PY) -m pytest -q

lint: setup
	$(PY) -m ruff check causal tests pages
