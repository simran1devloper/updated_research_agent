FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared_pkg
RUN pip install -e /app/shared_pkg

COPY research-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY research-service/src/research_service /app/research_service

RUN mkdir -p /data/output

ENV PYTHONPATH=/app

CMD ["uvicorn", "research_service.main:app", "--host", "0.0.0.0", "--port", "8005"]
