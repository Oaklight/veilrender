## ── shared base ──────────────────────────────────────────
FROM python:3.12-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libcups2 \
        libxcb1 \
        libxkbcommon0 \
        libatspi2.0-0 \
        libx11-6 \
        libxcomposite1 \
        libxdamage1 \
        libxext6 \
        libxfixes3 \
        libxrandr2 \
        libcairo2 \
        libpango-1.0-0 \
        libnss3 \
        libnspr4 \
        libasound2t64 \
        libdbus-1-3 \
        fonts-liberation \
        fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user || true
WORKDIR /app
COPY pyproject.toml .
COPY src/ src/
COPY scripts/ scripts/
RUN pip install --no-cache-dir .

## ── gateway (no browser, ~350MB) ─────────────────────────
## docker build --target gateway -t oaklight/veilrender:gateway .
FROM base AS gateway

USER 1000
EXPOSE 7860
CMD ["python", "-m", "veilrender"]

## ── libgbm donor (avoids pulling mesa/llvm ~200MB) ───────
FROM python:3.12-slim AS gbm-donor

RUN apt-get update && apt-get install -y --no-install-recommends libgbm1 \
    && rm -rf /var/lib/apt/lists/*
RUN mkdir /gbm-libs && \
    for lib in libgbm libdrm libwayland-server; do \
        cp -a /usr/lib/x86_64-linux-gnu/${lib}.so* /gbm-libs/ 2>/dev/null || true; \
    done

## ── full (CloakBrowser binary downloaded directly) ───────
## docker build -t oaklight/veilrender:latest .
FROM base AS full

COPY --from=gbm-donor /gbm-libs/* /usr/lib/x86_64-linux-gnu/
USER 1000
RUN python scripts/download-cloakbrowser.py
EXPOSE 7860
CMD ["python", "-m", "veilrender"]
