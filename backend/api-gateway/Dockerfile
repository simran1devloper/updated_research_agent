FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared_pkg
RUN pip install -e /app/shared_pkg

COPY api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api-gateway/src/api_gateway /app/api_gateway

ENV PYTHONPATH=/app

CMD ["uvicorn", "api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
