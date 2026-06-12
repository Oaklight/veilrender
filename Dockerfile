FROM mcr.microsoft.com/playwright/python:v1.60.0-noble

# HF Spaces runs as non-root user with UID 1000
RUN useradd -m -u 1000 user || true

WORKDIR /app

# Install Python package
COPY pyproject.toml .
COPY src/ src/
RUN pip install --no-cache-dir .

# Playwright browsers are pre-installed in the base image

USER 1000
EXPOSE 7860

CMD ["python", "-m", "veilrender"]
