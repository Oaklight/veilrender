FROM python:3.12-slim

# System libraries required by headless Chromium
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
        libgbm1 \
        libcairo2 \
        libpango-1.0-0 \
        libnss3 \
        libnspr4 \
        libasound2t64 \
        libdbus-1-3 \
        fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces runs as non-root user with UID 1000
RUN useradd -m -u 1000 user || true

WORKDIR /app

# Install Python package (includes cloakbrowser + playwright)
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Pre-download CloakBrowser Chromium binary so the image is self-contained
RUN python -c "from cloakbrowser import ensure_binary; ensure_binary()"

USER 1000
EXPOSE 7860

CMD ["python", "-m", "veilrender"]
