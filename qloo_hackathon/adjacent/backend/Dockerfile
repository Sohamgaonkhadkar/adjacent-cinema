FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    PYTHONPATH=/srv/adjacent/backend

WORKDIR /srv/adjacent
COPY pyproject.toml README.md ./
COPY backend ./backend

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir . \
    && groupadd --gid 10001 adjacent \
    && useradd --uid 10001 --gid adjacent --create-home --shell /usr/sbin/nologin adjacent \
    && mkdir -p /data \
    && chown adjacent:adjacent /data

ENV ADJACENT_EXPERIMENTS_DB=/data/experiments.db
USER adjacent

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=2).read()'

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
