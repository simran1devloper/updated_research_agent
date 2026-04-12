#!/bin/bash
set -e

cd "$(dirname "$0")"

[ -f .env ] && export $(grep -v '^#' .env | xargs)

[ ! -d .venv ] && uv venv .venv

uv pip install --python .venv/bin/python -r requirements.txt -q
uv pip install --python .venv/bin/python -e ../shared -q

PYTHONPATH=src exec .venv/bin/uvicorn synthesis_service.main:app --host 0.0.0.0 --port 8004 --reload
