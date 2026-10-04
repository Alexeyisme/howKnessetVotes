# API + ingestion image (hkv package). Build context: repository root.
# The same image runs the API (default command), migrations and the scheduled updater (infra/compose.prod.yaml).
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.8.14 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY db ./db
RUN uv sync --frozen --no-dev

RUN useradd --system --uid 10001 hkv && install -d -o hkv /data/raw
USER hkv
ENV PATH=/app/.venv/bin:$PATH HKV_RAW_DIR=/data/raw

EXPOSE 8000
CMD ["uvicorn", "hkv.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--proxy-headers", "--forwarded-allow-ips", "*"]
