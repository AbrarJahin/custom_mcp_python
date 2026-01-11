.PHONY: help install update status run dev dev-run test-client lint format clean test

# -----------------------------
# Config
# -----------------------------
ENV_FILE := environment.yaml
ENV_PATH := .conda/env
CONDA ?= conda

# --- Logging for tests ---
LOG_DIR  := logs
TEST_LOG := $(LOG_DIR)/test.log

# Run commands inside the conda env (works on Windows)
# IMPORTANT: --no-capture-output is required so uvicorn logs show up on Windows.
RUN := $(CONDA) run --no-capture-output -p "$(ENV_PATH)"

# -----------------------------
# Load values from .env (cross-platform)
# - Uses python-dotenv inside the conda env (already in your env)
# - CLI overrides still win: make dev HOST=0.0.0.0 PORT=9000
# -----------------------------
ENV_DOTFILE ?= .env

# Usage: $(call env,KEY,default)
env = $(shell $(RUN) python -c "import os; from dotenv import dotenv_values; v=dotenv_values('$(ENV_DOTFILE)'); print(os.getenv('$(1)', v.get('$(1)', '$(2)')))" )

APP_NAME ?= $(call env,APP_NAME,mcp-tool-gateway)
HOST ?= $(call env,HOST,127.0.0.1)
PORT ?= $(call env,PORT,8000)
MCP_MOUNT_PATH ?= $(call env,MCP_MOUNT_PATH,/mcp)
PUBLIC_BASE_URL ?= $(call env,PUBLIC_BASE_URL,http://$(HOST):$(PORT))

MCP_BASE_URL := http://$(HOST):$(PORT)
MCP_SERVER_URL := $(MCP_BASE_URL)$(MCP_MOUNT_PATH)

help:
	@echo ------------------------------------------------------------
	@echo Targets:
	@echo   make install      - Create/update conda env + pip install -e .
	@echo   make update       - Update env (prune) + reinstall editable package
	@echo   make status       - Show python/pip versions inside env
	@echo   make run          - Run MCP server (uvicorn) on $(HOST):$(PORT)
	@echo   make dev          - Run MCP server with auto-reload on $(HOST):$(PORT)
	@echo   make dev-run      - Run MCP server with debug logging on log file
	@echo   make test-client  - Run local MCP client against $(MCP_SERVER_URL)
	@echo   make lint         - Ruff lint (expects ruff in environment.yaml)
	@echo   make format       - Ruff format (expects ruff in environment.yaml)
	@echo   make clean        - Remove build/test caches (cross-platform)
	@echo   make test         - Run all tests (ensure server is running first with `make run`)
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
	@$(RUN) python -u -m uvicorn mcp_tool_gateway.app:app --host $(HOST) --port $(PORT) --log-level debug

dev:
	@$(RUN) python -u -m uvicorn mcp_tool_gateway.app:app --host $(HOST) --port $(PORT) --reload --log-level debug

dev-run:
	@if not exist "logs" mkdir "logs"
	@powershell -NoProfile -Command "$(RUN) python -u -m uvicorn mcp_tool_gateway.app:app --host $(HOST) --port $(PORT) --log-level debug *> logs/run.log"

test-client:
	@$(RUN) python scripts/test_client.py

# -----------------------------
# Code quality (managed by env file, not Makefile)
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
	@$(RUN) python -c "import shutil, pathlib; \
		paths=['dist','build','.pytest_cache','.ruff_cache']; \
		[shutil.rmtree(p, ignore_errors=True) for p in paths]; \
		[shutil.rmtree(str(p), ignore_errors=True) for p in pathlib.Path('.').glob('*.egg-info')]"

test:
	@if not exist "$(LOG_DIR)" mkdir "$(LOG_DIR)"
	@echo Please ensure MCP server is running. Running all integration tests...
	@echo Running tests... (live output + saving to $(TEST_LOG))
	@powershell -NoProfile -Command "$(RUN) python -u -m pytest -q 2>&1 | Tee-Object -FilePath '$(TEST_LOG)'; exit $$LASTEXITCODE"
