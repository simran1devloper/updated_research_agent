FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared_pkg
RUN pip install -e /app/shared_pkg

COPY synthesis-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY synthesis-service/src/synthesis_service /app/synthesis_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "synthesis_service.main:app", "--host", "0.0.0.0", "--port", "8004"]
