FROM python:3.11-slim

# Playwright needs system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY shared /app/shared_pkg
RUN pip install -e /app/shared_pkg

COPY search-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser (optional — only needed for JS-heavy pages)
RUN playwright install chromium --with-deps || true

COPY search-service/src/search_service /app/search_service

ENV PYTHONPATH=/app

CMD ["uvicorn", "search_service.main:app", "--host", "0.0.0.0", "--port", "8003"]
