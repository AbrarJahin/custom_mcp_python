.PHONY: help install update status run dev test-client lint format clean

# -----------------------------
# Config (versions come from these files)
# -----------------------------
ENV_FILE := environment.yaml
ENV_PATH := .conda/env
CONDA ?= conda

# Quote ENV_PATH to avoid issues on Windows paths/spaces
RUN := $(CONDA) run -p "$(ENV_PATH)"

# Use system Python for small cross-platform helper commands (copy/delete).
# This does NOT pin versions; it just runs tiny utilities.
PY ?= python

help:
	@echo ------------------------------------------------------------
	@echo Targets:
	@echo   make install      - Create/update conda env + pip install -e .
	@echo   make update       - Update env (prune) + reinstall editable package
	@echo   make status       - Show python/pip versions inside env
	@echo   make run          - Run MCP server (uvicorn)
	@echo   make dev          - Run MCP server with auto-reload
	@echo   make test-client  - Run local MCP client against http://localhost:8000/mcp
	@echo   make lint         - Ruff lint (expects ruff in environment.yaml)
	@echo   make format       - Ruff format (expects ruff in environment.yaml)
	@echo   make clean        - Remove build/test caches (cross-platform)
	@echo ------------------------------------------------------------

# -----------------------------
# Environment lifecycle
# -----------------------------
install:
	@echo [1/3] Creating or updating conda env from $(ENV_FILE)...
	@$(CONDA) env create -f "$(ENV_FILE)" -p "$(ENV_PATH)" || $(CONDA) env update -f "$(ENV_FILE)" -p "$(ENV_PATH)" --prune
	@echo [2/3] Installing package in editable mode...
	@$(RUN) python -m pip install -e .
	@echo [3/3] Ensuring .env exists (copy from .env.example if missing)...
	@$(RUN) python -c "import pathlib, shutil; src=pathlib.Path('.env.example'); dst=pathlib.Path('.env'); \
		(dst.exists() or (src.exists() and (shutil.copyfile(src, dst) or True)) or True)"

update:
	@echo Updating conda env from $(ENV_FILE)...
	@$(CONDA) env update -f "$(ENV_FILE)" -p "$(ENV_PATH)" --prune
	@echo Re-installing editable package...
	@$(RUN) python -m pip install -e .

status:
	@$(RUN) python -V
	@$(RUN) python -m pip -V
	@$(RUN) python -m pip show mcp || true

# -----------------------------
# Run server
# -----------------------------
run:
	@$(RUN) uvicorn mcp_tool_gateway.app:app --host 0.0.0.0 --port 8000

dev:
	@$(RUN) uvicorn mcp_tool_gateway.app:app --host 0.0.0.0 --port 8000 --reload

test-client:
	@$(RUN) python scripts/test_client.py

# -----------------------------
# Code quality (managed by env file, not Makefile)
# NOTE: Add ruff to environment.yaml under pip: if you want these targets to work.
# -----------------------------
lint:
	@$(RUN) python -c "import importlib.util, sys; \
		sys.exit(0) if importlib.util.find_spec('ruff') else (print('ruff is not installed. Add it to environment.yaml (pip section) to use make lint/format.'), sys.exit(2))"
	@$(RUN) ruff check .

format:
	@$(RUN) python -c "import importlib.util, sys; \
		sys.exit(0) if importlib.util.find_spec('ruff') else (print('ruff is not installed. Add it to environment.yaml (pip section) to use make lint/format.'), sys.exit(2))"
	@$(RUN) ruff format .

# -----------------------------
# Cleanup (cross-platform)
# -----------------------------
clean:
	@$(PY) -c "import shutil, pathlib; \
		paths=['dist','build','.pytest_cache','.ruff_cache']; \
		[shutil.rmtree(p, ignore_errors=True) for p in paths]; \
		[shutil.rmtree(str(p), ignore_errors=True) for p in pathlib.Path('.').glob('*.egg-info')]"
