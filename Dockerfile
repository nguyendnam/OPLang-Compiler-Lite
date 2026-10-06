# =========================================================
# Stage 1 — Generate ANTLR Python sources
# =========================================================

FROM python:3.12-slim AS antlr-builder

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-jre-headless \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/build_antlr.py ./scripts/build_antlr.py
COPY src/grammar ./src/grammar

RUN python scripts/build_antlr.py


# =========================================================
# Stage 2 — Production FastAPI runtime
# =========================================================

FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app
ENV PORT=10000

COPY requirements.txt ./

RUN pip install \
    --no-cache-dir \
    --disable-pip-version-check \
    -r requirements.txt

COPY backend ./backend
COPY compiler_core ./compiler_core
COPY src ./src

COPY --from=antlr-builder \
    /app/build \
    ./build

RUN useradd \
    --create-home \
    --uid 10001 \
    appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 10000

HEALTHCHECK \
    --interval=30s \
    --timeout=5s \
    --start-period=15s \
    --retries=3 \
    CMD python -c \
    "import urllib.request; urllib.request.urlopen('http://127.0.0.1:10000/api/v1/health', timeout=3)"

CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
