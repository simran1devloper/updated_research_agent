FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared_pkg
RUN pip install -e /app/shared_pkg

COPY conversation-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY conversation-service/src/conversation_service /app/conversation_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "conversation_service.main:app", "--host", "0.0.0.0", "--port", "8008"]
