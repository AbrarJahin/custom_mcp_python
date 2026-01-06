.PHONY: help install update status run dev test-client lint format clean

ENV_FILE := environment.yaml
ENV_PATH := .conda/env
CONDA := conda
RUN := $(CONDA) run -p $(ENV_PATH)

help:
	@echo ------------------------------------------------------------
	@echo Targets:
	@echo   make install      - Create env in .conda/env + pip install -e .
	@echo   make update       - Update env + reinstall editable package
	@echo   make status       - Show python/pip versions inside env
	@echo   make run          - Run MCP server (uvicorn)
	@echo   make dev          - Run MCP server with auto-reload
	@echo   make test-client  - Run local MCP client against http://localhost:8000/mcp
	@echo   make lint         - Ruff lint
	@echo   make format       - Ruff format
	@echo   make clean        - Remove build artifacts
	@echo ------------------------------------------------------------

install:
	@mkdir -p .conda
	$(CONDA) env create -f $(ENV_FILE) -p $(ENV_PATH) || $(CONDA) env update -f $(ENV_FILE) -p $(ENV_PATH)
	$(RUN) python -m pip install -e .
	@if not exist .env copy .env.example .env

update:
	$(CONDA) env update -f $(ENV_FILE) -p $(ENV_PATH)
	$(RUN) python -m pip install -e .

status:
	$(RUN) python -V
	$(RUN) python -m pip -V
	$(RUN) python -m pip show mcp || true

run:
	$(RUN) uvicorn mcp_tool_gateway.app:app --host 0.0.0.0 --port 8000

dev:
	$(RUN) uvicorn mcp_tool_gateway.app:app --host 0.0.0.0 --port 8000 --reload

test-client:
	$(RUN) python scripts/test_client.py

lint:
	$(RUN) python -m pip install -q "ruff>=0.5.0"
	$(RUN) ruff check .

format:
	$(RUN) python -m pip install -q "ruff>=0.5.0"
	$(RUN) ruff format .

clean:
	@rm -rf dist build *.egg-info .pytest_cache .ruff_cache
