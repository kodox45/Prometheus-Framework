FROM python:3.11-slim

ENV POETRY_VIRTUALENVS_CREATE=false \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN pip install --upgrade pip && pip install "poetry==1.7.1" \
    && poetry install --no-interaction --no-ansi --only main

COPY prometheus ./prometheus
COPY services/relation-finder/entrypoint.py ./entrypoint.py

CMD ["python", "entrypoint.py", "--top-k", "5", "--min-similarity", "0.8", "--min-confidence", "0.85"]


