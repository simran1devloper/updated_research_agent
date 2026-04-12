FROM python:3.11-slim

WORKDIR /app

# Install shared package first
COPY shared /app/shared_pkg
RUN pip install -e /app/shared_pkg

# Install service dependencies
COPY intent-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy service source
COPY intent-service/src/intent_service /app/intent_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "intent_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
