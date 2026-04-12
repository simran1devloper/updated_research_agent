FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared_pkg
RUN pip install -e /app/shared_pkg

COPY memory-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY memory-service/src/memory_service /app/memory_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "memory_service.main:app", "--host", "0.0.0.0", "--port", "8002"]
