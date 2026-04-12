#!/bin/bash
set -e

cd "$(dirname "$0")"

[ -f .env ] && export $(grep -v '^#' .env | xargs)

# Regenerate gRPC stubs if missing
if [ ! -f ../shared/shared/proto/auth_pb2.py ]; then
  echo "[auth-service] gRPC stubs missing — regenerating..."
  bash ../shared/generate_grpc.sh
fi

[ ! -d .venv ] && uv venv .venv

uv pip install --python .venv/bin/python -r requirements.txt -q
uv pip install --python .venv/bin/python -e ../shared -q

PYTHONPATH=src exec .venv/bin/uvicorn auth_service.main:app --host 0.0.0.0 --port 8007 --reload
