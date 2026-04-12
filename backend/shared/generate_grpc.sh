#!/usr/bin/env bash
# Run from repo root: bash backend/shared/generate_grpc.sh
set -e

PROTO_DIR="backend/shared/shared/proto"
OUT_DIR="backend/shared/shared/proto"

pip install grpcio-tools -q || python3 -m pip install grpcio-tools -q

for proto in intent memory search synthesis; do
  python -m grpc_tools.protoc \
    -I "$PROTO_DIR" \
    --python_out="$OUT_DIR" \
    --grpc_python_out="$OUT_DIR" \
    "$PROTO_DIR/${proto}.proto"
done

# Fix relative imports in generated files
for f in "$OUT_DIR"/*_pb2_grpc.py; do
  sed -i '' 's/^import \(.*_pb2\)/from . import \1/' "$f" 2>/dev/null || \
  sed -i  's/^import \(.*_pb2\)/from . import \1/' "$f"
done

echo "gRPC stubs generated in $OUT_DIR"
