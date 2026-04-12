FROM python:3.11-slim

WORKDIR /app

COPY shared /app/shared_pkg
RUN pip install -e /app/shared_pkg

COPY auth-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY auth-service/src/auth_service /app/auth_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "auth_service.main:app", "--host", "0.0.0.0", "--port", "8007"]
