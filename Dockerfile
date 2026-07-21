# syntax=docker/dockerfile:1

FROM python:3.14-slim-bookworm AS builder

# asyncpg ships C extensions; a wheel may not exist yet for every
# Python 3.14 platform, so keep a compiler around for the build stage.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

COPY pyproject.toml uv.lock ./
COPY src ./src
COPY db ./db

RUN uv sync --frozen --no-dev && uv cache prune --ci


FROM python:3.14-slim-bookworm AS runtime

RUN groupadd --system app && useradd --system --gid app --home-dir /app app

WORKDIR /app

COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app/src" \
    PYTHONUNBUFFERED=1 \
    PICCOLO_CONF=piccolo_conf

USER app

EXPOSE 8000

CMD ["python", "src/main.py"]
